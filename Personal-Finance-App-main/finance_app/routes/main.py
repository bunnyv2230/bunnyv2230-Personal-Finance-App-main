from flask import render_template, redirect, url_for, session, request, jsonify
from ..models import get_goals_by_user_id, get_expenses_fortbl_by_user_id, get_income_by_user_id
from ..helpers import get_leftover_salary_history

def register_main_routes(app):
    
    @app.route('/')
    def home():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user_id = session['user_id']
        raw_goals = get_goals_by_user_id(user_id)
        
        goals = []
        total_leftovers = 0.0
        if raw_goals:
            _, total_leftovers = get_leftover_salary_history(user_id)
            first_goal = raw_goals[0]
            modified_first = list(first_goal)
            modified_first[4] = float(modified_first[4] or 0.0) + total_leftovers
            goals.append(tuple(modified_first))
            for g in raw_goals[1:]:
                goals.append(g)
                
        filters = {
            'range_type': session.get('range_type', 'this_month'),
            'month_val': session.get('month_val', ''),
            'start_date_val': session.get('start_date_val', ''),
            'end_date_val': session.get('end_date_val', '')
        }
        return render_template('home.html', goals=goals, filters=filters, total_leftovers=total_leftovers)

    @app.route('/api/dashboard_data')
    def dashboard_data():
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        user_id = session['user_id']
        expenses = get_expenses_fortbl_by_user_id(user_id)
        incomes = get_income_by_user_id(user_id)
        
        def get_start_date_of_months_ago(n):
            from datetime import datetime
            today = datetime.today()
            year = today.year
            month = today.month - (n - 1)
            while month <= 0:
                month += 12
                year -= 1
            return f"{year:04d}-{month:02d}-01"

        # Filter by range if provided
        range_type = request.args.get('range', 'this_month')
        month_val = request.args.get('month')
        start_date_val = request.args.get('start_date')
        end_date_val = request.args.get('end_date')

        # Save filters to session
        session['range_type'] = range_type
        session['month_val'] = month_val
        session['start_date_val'] = start_date_val
        session['end_date_val'] = end_date_val
        
        if range_type == 'this_month':
            from datetime import datetime
            curr_month = datetime.today().strftime('%Y-%m')
            expenses = [exp for exp in expenses if exp[4] and exp[4].startswith(curr_month)]
            incomes = [inc for inc in incomes if inc[4] and inc[4].startswith(curr_month)]
        elif range_type == 'last_2_months':
            start_date = get_start_date_of_months_ago(2)
            expenses = [exp for exp in expenses if exp[4] and exp[4] >= start_date]
            incomes = [inc for inc in incomes if inc[4] and inc[4] >= start_date]
        elif range_type == 'last_3_months':
            start_date = get_start_date_of_months_ago(3)
            expenses = [exp for exp in expenses if exp[4] and exp[4] >= start_date]
            incomes = [inc for inc in incomes if inc[4] and inc[4] >= start_date]
        elif range_type == 'last_4_months':
            start_date = get_start_date_of_months_ago(4)
            expenses = [exp for exp in expenses if exp[4] and exp[4] >= start_date]
            incomes = [inc for inc in incomes if inc[4] and inc[4] >= start_date]
        elif range_type == 'last_6_months':
            start_date = get_start_date_of_months_ago(6)
            expenses = [exp for exp in expenses if exp[4] and exp[4] >= start_date]
            incomes = [inc for inc in incomes if inc[4] and inc[4] >= start_date]
        elif range_type == 'custom_month' and month_val:
            expenses = [exp for exp in expenses if exp[4] and exp[4].startswith(month_val)]
            incomes = [inc for inc in incomes if inc[4] and inc[4].startswith(month_val)]
        elif range_type == 'custom_range':
            if start_date_val:
                expenses = [exp for exp in expenses if exp[4] and exp[4] >= start_date_val]
                incomes = [inc for inc in incomes if inc[4] and inc[4] >= start_date_val]
            if end_date_val:
                expenses = [exp for exp in expenses if exp[4] and exp[4] <= end_date_val]
                incomes = [inc for inc in incomes if inc[4] and inc[4] <= end_date_val]
        
        total_income = sum([inc[3] for inc in incomes])
        total_expense = sum([exp[3] for exp in expenses])
        balance = total_income - total_expense
        
        category_totals = {}
        for exp in expenses:
            cat = exp[2]
            category_totals[cat] = category_totals.get(cat, 0) + exp[3]
            
        return jsonify({
            'balance': balance,
            'total_income': total_income,
            'total_expense': total_expense,
            'categories': list(category_totals.keys()),
            'category_amounts': list(category_totals.values())
        })
