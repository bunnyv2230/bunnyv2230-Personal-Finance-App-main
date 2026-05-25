import logging
import sqlite3
import pandas as pd
import collections
from flask import render_template, redirect, url_for, session, request, flash, current_app
from ml_model import (
    train_lstm_model, predict_next_month_lstm, detect_anomalies,
    cluster_expenses, recommend_savings_plan, fetch_expense_data,
    detect_anomalies_autoencoder, train_autoencoder
)
from ..models import get_expenses_fortbl_by_user_id

def register_ml_routes(app):
    
    @app.route('/predict_expenses')
    def predict_expenses():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        user_id = session['user_id']

        expenses = fetch_expense_data(user_id)
        if expenses.empty or expenses.shape[0] < 2:  # Check for sufficient historical data
            logging.warning(f"Not enough data available for user {user_id} to make a prediction.")
            return render_template('predict_expenses.html', error="Not enough data available to make a prediction.")

        model, scaler = train_lstm_model(user_id)
        if not model or not scaler:
            logging.error(f"Model training failed for user {user_id} due to insufficient data.")
            return render_template('predict_expenses.html', error="Not enough data to train the model.")

        next_month_prediction = predict_next_month_lstm(user_id, model, scaler)
        if next_month_prediction is None:
            logging.error(f"Prediction could not be made for user {user_id}")
            return render_template('predict_expenses.html', error="Not enough data to make a prediction.")

        next_month_prediction = float(next_month_prediction)

        # Compute category breakdown forecasts
        conn = sqlite3.connect(current_app.config['DB_PATH'])
        cursor = conn.cursor()
        cursor.execute("SELECT category, amount, date FROM expenses WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()

        category_monthly = collections.defaultdict(lambda: collections.defaultdict(float))
        for cat, amt, dt in rows:
            if not dt:
                continue
            month_str = dt[:7]  # YYYY-MM
            category_monthly[cat][month_str] += amt

        unique_months = sorted(list({dt[:7] for cat, amt, dt in rows if dt}))
        category_forecasts = {}
        for cat, monthly_data in category_monthly.items():
            values = [monthly_data[m] for m in unique_months]
            if not values:
                category_forecasts[cat] = 0.0
                continue
            if len(values) >= 3:
                raw_forecast = 0.5 * values[-1] + 0.3 * values[-2] + 0.2 * values[-3]
            elif len(values) == 2:
                raw_forecast = 0.6 * values[-1] + 0.4 * values[-2]
            else:
                raw_forecast = values[-1]
            category_forecasts[cat] = max(0.0, raw_forecast)

        total_cat_forecast = sum(category_forecasts.values())
        category_breakdown = []
        if total_cat_forecast > 0:
            normalization_factor = next_month_prediction / total_cat_forecast
            for cat, raw_f in category_forecasts.items():
                norm_f = raw_f * normalization_factor
                percentage = (norm_f / next_month_prediction) * 100 if next_month_prediction > 0 else 0
                category_breakdown.append({
                    'category': cat,
                    'forecasted_amount': norm_f,
                    'percentage': percentage
                })
        else:
            for cat in category_monthly.keys():
                category_breakdown.append({
                    'category': cat,
                    'forecasted_amount': next_month_prediction / len(category_monthly) if category_monthly else 0,
                    'percentage': 100 / len(category_monthly) if category_monthly else 0
                })

        category_breakdown = sorted(category_breakdown, key=lambda x: x['forecasted_amount'], reverse=True)

        expenses['date'] = pd.to_datetime(expenses['date'])
        expenses.set_index('date', inplace=True)
        expenses = expenses.resample('ME').sum()
        dates = expenses.index.strftime('%Y-%m').tolist()
        amounts = expenses['amount'].tolist()

        labels = dates + ['Next Month']
        actual_expenses = amounts + [None]
        predicted_expenses = [None] * (len(amounts) - 1) + [amounts[-1]] + [next_month_prediction] if amounts else [next_month_prediction]

        return render_template('predict_expenses.html', prediction=next_month_prediction,
                               labels=labels, actual_expenses=actual_expenses, predicted_expenses=predicted_expenses,
                               category_breakdown=category_breakdown)

    @app.route('/view_anomalies')
    def view_anomalies():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        user_id = session['user_id']
        anomalies = detect_anomalies(user_id)

        return render_template('view_anomalies.html', anomalies=anomalies)

    @app.route('/detect_anomalies')
    def detect_anomalies_route():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        user_id = session['user_id']
        anomalies = detect_anomalies(user_id)

        if anomalies is None:
            logging.error(f"Anomalies could not be detected for user {user_id}")
            return render_template('detect_anomalies.html', error="Not enough data to detect anomalies.")

        return render_template('detect_anomalies.html', anomalies=anomalies)

    @app.route('/detect_anomalies_autoencoder')
    def detect_anomalies_autoencoder_route():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        user_id = session['user_id']
        
        # Train the model first
        model_data = train_autoencoder(user_id)
        if not model_data:
            logging.error(f"Autoencoder training failed due to insufficient data for user {user_id}")
            return render_template('detect_anomalies_autoencoder.html', error="Not enough data to train autoencoder.")
            
        model, scaler = model_data
        anomalies_autoencoder = detect_anomalies_autoencoder(user_id, model, scaler)

        if anomalies_autoencoder is None or anomalies_autoencoder.empty:
            logging.error(f"Anomalies could not be detected using autoencoder for user {user_id}")
            return render_template('detect_anomalies_autoencoder.html', error="Not enough data to detect anomalies using autoencoder.")

        return render_template('detect_anomalies_autoencoder.html', anomalies=anomalies_autoencoder)

    @app.route('/expense_clusters')
    def view_expense_clusters():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        user_id = session['user_id']
        try:
            clustered_data = cluster_expenses(user_id)
            if clustered_data is not None:
                clustered_data = clustered_data.to_dict(orient='records')  # Convert DataFrame to list of dictionaries
            else:
                clustered_data = []
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(url_for('home'))

        return render_template('view_clusters.html', clustered_data=clustered_data)

    @app.route('/recommend_savings')
    def recommend_savings():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        user_id = session['user_id']
        recommended_amount = recommend_savings_plan(user_id)

        return render_template('recommend_savings.html', recommended_amount=recommended_amount)

    @app.route('/expenses/clusters')
    def expense_clusters():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        user_id = session['user_id']
        expenses = get_expenses_fortbl_by_user_id(user_id)

        if not expenses:
            flash('No expenses recorded yet. Please add some expenses first.', 'info')
            return redirect(url_for('view_expenses'))

        range_type = request.args.get('range')
        if range_type is not None:
            month_val = request.args.get('month')
            start_date_val = request.args.get('start_date')
            end_date_val = request.args.get('end_date')
            session['range_type'] = range_type
            session['month_val'] = month_val
            session['start_date_val'] = start_date_val
            session['end_date_val'] = end_date_val
        else:
            range_type = session.get('range_type', 'this_month')
            month_val = session.get('month_val')
            start_date_val = session.get('start_date_val')
            end_date_val = session.get('end_date_val')

        def get_start_date_of_months_ago(n):
            from datetime import datetime
            today = datetime.today()
            year = today.year
            month = today.month - (n - 1)
            while month <= 0:
                month += 12
                year -= 1
            return f"{year:04d}-{month:02d}-01"

        if range_type == 'this_month':
            from datetime import datetime
            curr_month = datetime.today().strftime('%Y-%m')
            expenses = [exp for exp in expenses if exp[4] and exp[4].startswith(curr_month)]
        elif range_type == 'last_2_months':
            start_date = get_start_date_of_months_ago(2)
            expenses = [exp for exp in expenses if exp[4] and exp[4] >= start_date]
        elif range_type == 'last_3_months':
            start_date = get_start_date_of_months_ago(3)
            expenses = [exp for exp in expenses if exp[4] and exp[4] >= start_date]
        elif range_type == 'last_4_months':
            start_date = get_start_date_of_months_ago(4)
            expenses = [exp for exp in expenses if exp[4] and exp[4] >= start_date]
        elif range_type == 'last_6_months':
            start_date = get_start_date_of_months_ago(6)
            expenses = [exp for exp in expenses if exp[4] and exp[4] >= start_date]
        elif range_type == 'custom_month' and month_val:
            expenses = [exp for exp in expenses if exp[4] and exp[4].startswith(month_val)]
        elif range_type == 'custom_range':
            if start_date_val:
                expenses = [exp for exp in expenses if exp[4] and exp[4] >= start_date_val]
            if end_date_val:
                expenses = [exp for exp in expenses if exp[4] and exp[4] <= end_date_val]

        by_date = {}
        for exp in expenses:
            date = exp[4]
            by_date.setdefault(date, []).append({
                'id': exp[0],
                'category': exp[2],
                'amount': exp[3],
                'description': exp[5] if len(exp) > 5 else ''
            })
        sorted_dates = sorted(by_date.keys(), reverse=True)
        by_date_sorted = {date: by_date[date] for date in sorted_dates}

        by_category = {}
        for exp in expenses:
            cat = exp[2]
            by_category.setdefault(cat, []).append({
                'id': exp[0],
                'date': exp[4],
                'amount': exp[3],
                'description': exp[5] if len(exp) > 5 else ''
            })
        sorted_cats = sorted(by_category.keys())
        by_category_sorted = {cat: by_category[cat] for cat in sorted_cats}

        filter_label = "This Month"
        if range_type == 'last_2_months':
            filter_label = "Last 2 Months"
        elif range_type == 'last_3_months':
            filter_label = "Last 3 Months"
        elif range_type == 'last_4_months':
            filter_label = "Last 4 Months"
        elif range_type == 'last_6_months':
            filter_label = "Last 6 Months"
        elif range_type == 'all_time':
            filter_label = "All Time"
        elif range_type == 'custom_month' and month_val:
            filter_label = f"Month ({month_val})"
        elif range_type == 'custom_range':
            filter_label = f"Range ({start_date_val} to {end_date_val})"

        current_filters = {
            'range_type': range_type,
            'month_val': month_val or '',
            'start_date_val': start_date_val or '',
            'end_date_val': end_date_val or ''
        }

        return render_template('expense_clusters.html', by_date=by_date_sorted, by_category=by_category_sorted, filter_label=filter_label, current_filters=current_filters)
