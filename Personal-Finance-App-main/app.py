from flask import Flask, redirect, url_for, session, request, render_template, flash, g, jsonify
from authlib.integrations.flask_client import OAuth
from werkzeug.utils import secure_filename
import os

# Load local .env file if it exists
if os.path.exists('.env'):
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip() and not line.startswith('#') and '=' in line:
                key, val = line.strip().split('=', 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")
from flask_sqlalchemy import SQLAlchemy
from models import db, get_user_by_username, create_user, get_expenses_by_user_id, create_expense, get_goals_by_user_id, create_goal, get_user_by_id, update_user_profile, create_income, get_income_by_user_id, get_income_by_id, update_income, delete_income, get_expenses_fortbl_by_user_id, get_expense_by_id, update_expense, delete_expense, generate_sample_expenses, get_goal_by_id, update_goal, update_goal_amount, delete_goal
import logging
import sqlite3
from ml_model import train_lstm_model,\
    predict_next_month_lstm, detect_anomalies, cluster_expenses, recommend_savings_plan, fetch_expense_data, detect_anomalies_autoencoder, train_autoencoder
from flask_bcrypt import Bcrypt
import pandas as pd
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_secret_key_123')
bcrypt = Bcrypt(app)
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'personal_finance.db').replace('\\', '/')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import db and initialize it
from models import db, get_user_by_username, create_user, get_expenses_by_user_id, create_expense, get_goals_by_user_id, create_goal, get_user_by_id, update_user_profile, create_income, get_income_by_user_id, get_income_by_id, update_income, delete_income, get_expenses_fortbl_by_user_id, get_expense_by_id, update_expense, delete_expense, generate_sample_expenses, get_goal_by_id, update_goal, update_goal_amount, delete_goal

db.init_app(app)
with app.app_context():
    db.create_all()
# Configure upload folder
app.config['UPLOAD_FOLDER'] = 'static/profile_images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
# Configure OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID', 'YOUR_GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', 'YOUR_GOOGLE_CLIENT_SECRET'),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'},
)
@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_authorized', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/authorized')
def google_authorized():
    token = google.authorize_access_token()
    user_info = google.parse_id_token(token)

    session['google_token'] = token
    session['user_id'] = user_info['sub']
    session['username'] = user_info['name']
    session['email'] = user_info['email']
    return redirect(url_for('home'))



# Function to run before every request
@app.before_request
def load_user():
    user_id = session.get('user_id')
    if user_id:
        g.user = get_user_by_id(user_id)
    else:
        g.user = None

def create_connection():
    conn = None
    try:
        conn = sqlite3.connect('personal_finance.db')
    except sqlite3.Error as e:
        print(e)
    return conn
def get_leftover_salary_history(user_id):
    # Fetch all incomes
    incomes = get_income_by_user_id(user_id)
    # Fetch all expenses
    expenses = get_expenses_fortbl_by_user_id(user_id)
    
    income_by_month = {}
    for inc in incomes:
        dt = inc[4]
        if not dt:
            continue
        ym = dt[:7]
        income_by_month[ym] = income_by_month.get(ym, 0.0) + inc[3]
        
    expense_by_month = {}
    for exp in expenses:
        dt = exp[4]
        if not dt:
            continue
        ym = dt[:7]
        expense_by_month[ym] = expense_by_month.get(ym, 0.0) + exp[3]
        
    all_months = sorted(list(set(list(income_by_month.keys()) + list(expense_by_month.keys()))))
    
    leftovers = []
    total_leftover = 0.0
    
    import calendar
    for ym in all_months:
        inc = income_by_month.get(ym, 0.0)
        exp = expense_by_month.get(ym, 0.0)
        left = inc - exp
        if left > 0:
            try:
                yr, mn = map(int, ym.split('-'))
                month_name = f"{calendar.month_name[mn]} {yr}"
            except Exception:
                month_name = ym
            leftovers.append({
                'month': month_name,
                'amount': left
            })
            total_leftover += left
            
    return leftovers, total_leftover

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
            
    # Pass session filters so they sync on page load
    filters = {
        'range_type': session.get('range_type', 'this_month'),
        'month_val': session.get('month_val', ''),
        'start_date_val': session.get('start_date_val', ''),
        'end_date_val': session.get('end_date_val', '')
    }
    return render_template('home.html', goals=goals, filters=filters, total_leftovers=total_leftovers)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)
        if user and bcrypt.check_password_hash(user[2], password):
            session['user_id'] = user[0]
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        if create_user(username, hashed_password):
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Registration failed. Username may already be taken.', 'danger')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        category = request.form['category']
        amount = request.form['amount']
        date = request.form['date']
        description = request.form.get('description', '')
        create_expense(session['user_id'], category, amount, date, description)
        flash('Expense added!', 'success')
        return redirect(url_for('view_expenses'))
    return render_template('add_expense.html')

@app.route('/view_expenses')
def view_expenses():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    expenses = get_expenses_fortbl_by_user_id(session['user_id'])
    return render_template('view_expenses.html', expenses=expenses)

@app.route('/generate_sample_expenses')
def generate_sample_expenses_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    num_generated = generate_sample_expenses(user_id)
    flash(f'Generated {num_generated} sample expenses for testing!', 'success')
    return redirect(url_for('view_expenses'))

@app.route('/verify_password', methods=['POST'])
def verify_password():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    
    data = request.get_json()
    password = data.get('password', '')
    
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
    
    # Get user with password hash
    from models import User
    user_obj = User.query.get(user_id)
    
    if user_obj and bcrypt.check_password_hash(user_obj.password, password):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Incorrect password'})

@app.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    if request.method == 'GET':
        expense = get_expense_by_id(expense_id, user_id)
        if not expense:
            flash('Expense not found', 'danger')
            return redirect(url_for('view_expenses'))
        return render_template('edit_expense.html', expense=expense)
    
    elif request.method == 'POST':
        category = request.form['category']
        amount = request.form['amount']
        date = request.form['date']
        description = request.form.get('description', '')
        
        if update_expense(expense_id, user_id, category, amount, date, description):
            flash('Expense updated successfully!', 'success')
            return redirect(url_for('view_expenses'))
        else:
            flash('Expense not found', 'danger')
            return redirect(url_for('view_expenses'))

@app.route('/delete_expense/<int:expense_id>')
def delete_expense_route(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    if delete_expense(expense_id, user_id):
        flash('Expense deleted successfully!', 'success')
    else:
        flash('Expense not found', 'danger')
    
    return redirect(url_for('view_expenses'))

@app.route('/add_goal', methods=['GET', 'POST'])
def add_goal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        goal = request.form['goal']
        target_amount = request.form['target_amount']
        current_amount = request.form['current_amount']
        create_goal(session['user_id'], goal, target_amount, current_amount)
        flash('Goal added!', 'success')
        return redirect(url_for('view_goals'))
    return render_template('add_goal.html')

@app.route('/view_goals')
def view_goals():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    raw_goals = get_goals_by_user_id(user_id)
    
    goals = []
    leftovers_history = []
    total_leftovers = 0.0
    if raw_goals:
        leftovers_history, total_leftovers = get_leftover_salary_history(user_id)
        first_goal = raw_goals[0]
        modified_first = list(first_goal)
        modified_first[4] = float(modified_first[4] or 0.0) + total_leftovers
        goals.append(tuple(modified_first))
        for g in raw_goals[1:]:
            goals.append(g)
            
    return render_template('view_goals.html', goals=goals, leftovers_history=leftovers_history, total_leftovers=total_leftovers)

@app.route('/edit_goal/<int:goal_id>', methods=['GET', 'POST'])
def edit_goal(goal_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    if request.method == 'GET':
        goal = get_goal_by_id(goal_id, user_id)
        if not goal:
            flash('Goal not found', 'danger')
            return redirect(url_for('view_goals'))
        return render_template('edit_goal.html', goal=goal)
    
    elif request.method == 'POST':
        goal_name = request.form['goal']
        target_amount = request.form['target_amount']
        current_amount = request.form['current_amount']
        
        if update_goal(goal_id, user_id, goal_name, target_amount, current_amount):
            flash('Goal updated successfully!', 'success')
            return redirect(url_for('view_goals'))
        else:
            flash('Goal not found', 'danger')
            return redirect(url_for('view_goals'))

@app.route('/add_goal_funds/<int:goal_id>', methods=['POST'])
def add_goal_funds(goal_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    amount_to_add = request.form.get('amount_to_add', 0)
    
    try:
        amount_to_add = float(amount_to_add)
        if amount_to_add <= 0:
            flash('Please enter a valid positive amount.', 'warning')
            return redirect(url_for('view_goals'))
    except ValueError:
        flash('Invalid amount entered.', 'danger')
        return redirect(url_for('view_goals'))
        
    if update_goal_amount(goal_id, user_id, amount_to_add):
        flash(f'Added ₹{amount_to_add:.2f} to your goal funds!', 'success')
    else:
        flash('Goal not found.', 'danger')
        
    return redirect(url_for('view_goals'))

@app.route('/delete_goal/<int:goal_id>')
def delete_goal_route(goal_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    if delete_goal(goal_id, user_id):
        flash('Goal deleted successfully!', 'success')
    else:
        flash('Goal not found', 'danger')
        
    return redirect(url_for('view_goals'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = get_user_by_id(user_id)

    if request.method == 'POST':
        new_username = request.form['username']
        new_password = request.form.get('password', None)  # Get the new password if provided

        # If a new password is provided, hash it
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8') if new_password else None

        # Handle file upload
        profile_image = None
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                profile_image = filename

        update_user_profile(user_id, new_username, hashed_password, profile_image)
        flash('Profile updated!', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)

@app.route('/add_income', methods=['GET', 'POST'])
def add_income():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        source = request.form['source']
        amount = request.form['amount']
        date = request.form['date']
        create_income(session['user_id'], source, amount, date)
        flash('Income added!', 'success')
        return redirect(url_for('view_income'))

    return render_template('add_income.html')

@app.route('/view_income')
def view_income():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    income = get_income_by_user_id(session['user_id'])
    return render_template('view_income.html', income=income)

@app.route('/edit_income/<int:income_id>', methods=['GET', 'POST'])
def edit_income(income_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    
    if request.method == 'GET':
        income = get_income_by_id(income_id, user_id)
        if not income:
            flash('Income not found', 'danger')
            return redirect(url_for('view_income'))
        return render_template('edit_income.html', income=income)
        
    elif request.method == 'POST':
        source = request.form['source']
        amount = request.form['amount']
        date = request.form['date']
        
        if update_income(income_id, user_id, source, amount, date):
            flash('Income updated successfully!', 'success')
            return redirect(url_for('view_income'))
        else:
            flash('Income not found', 'danger')
            return redirect(url_for('view_income'))

@app.route('/delete_income/<int:income_id>')
def delete_income_route(income_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    
    if delete_income(income_id, user_id):
        flash('Income deleted successfully!', 'success')
    else:
        flash('Income not found', 'danger')
        
    return redirect(url_for('view_income'))


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
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT category, amount, date FROM expenses WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    import collections
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
        clustered_data = clustered_data.to_dict(orient='records')  # Convert DataFrame to list of dictionaries
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

    # Load filter parameters: check request.args first (if changed on this page), then session
    range_type = request.args.get('range')
    if range_type is not None:
        month_val = request.args.get('month')
        start_date_val = request.args.get('start_date')
        end_date_val = request.args.get('end_date')
        # Update session
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

    # Filter expenses according to saved session values
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

    # Group by Date
    by_date = {}
    for exp in expenses:
        date = exp[4]
        by_date.setdefault(date, []).append({
            'id': exp[0],
            'category': exp[2],
            'amount': exp[3],
            'description': exp[5] if len(exp) > 5 else ''
        })
    # Sort dates descending
    sorted_dates = sorted(by_date.keys(), reverse=True)
    by_date_sorted = {date: by_date[date] for date in sorted_dates}

    # Group by Category
    by_category = {}
    for exp in expenses:
        cat = exp[2]
        by_category.setdefault(cat, []).append({
            'id': exp[0],
            'date': exp[4],
            'amount': exp[3],
            'description': exp[5] if len(exp) > 5 else ''
        })
    # Sort categories alphabetically
    sorted_cats = sorted(by_category.keys())
    by_category_sorted = {cat: by_category[cat] for cat in sorted_cats}

    # Determine filter label
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
    # if range_type == 'all_time', do not filter (returns all data)
    
    total_income = sum([inc[3] for inc in incomes])
    total_expense = sum([exp[3] for exp in expenses])
    balance = total_income - total_expense
    
    # Calculate expenses by category
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

if __name__ == '__main__':
    app.run(debug=True)
