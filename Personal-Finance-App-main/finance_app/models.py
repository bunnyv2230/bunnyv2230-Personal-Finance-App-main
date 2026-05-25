import os
from .extensions import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    profile_image = db.Column(db.String(255))
    expenses = db.relationship('Expense', backref='user', lazy=True)
    goals = db.relationship('Goal', backref='user', lazy=True)
    incomes = db.relationship('Income', backref='user', lazy=True)

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))

class Goal(db.Model):
    __tablename__ = 'goals'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    goal = db.Column(db.String(255), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, nullable=False)

class Income(db.Model):
    __tablename__ = 'income'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    source = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(50), nullable=False)

class RecurringExpense(db.Model):
    __tablename__ = 'recurring_expenses'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(50), nullable=False)
    next_due_date = db.Column(db.String(50), nullable=False)

# Helper functions to keep app.py mostly intact for now
def get_user_by_username(username):
    user = User.query.filter_by(username=username).first()
    if user:
        return (user.id, user.username, user.password, user.profile_image)
    return None

def create_user(username, password):
    if User.query.filter_by(username=username).first():
        return False
    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()
    return True

def create_income(user_id, source, amount, date):
    new_income = Income(user_id=user_id, source=source, amount=amount, date=date)
    db.session.add(new_income)
    db.session.commit()

def get_income_by_user_id(user_id):
    incomes = Income.query.filter_by(user_id=user_id).all()
    return [(inc.id, inc.user_id, inc.source, inc.amount, inc.date) for inc in incomes]

def get_income_by_id(income_id, user_id):
    income = Income.query.filter_by(id=income_id, user_id=user_id).first()
    if income:
        return {
            'id': income.id,
            'user_id': income.user_id,
            'source': income.source,
            'amount': income.amount,
            'date': income.date
        }
    return None

def update_income(income_id, user_id, source, amount, date):
    income = Income.query.filter_by(id=income_id, user_id=user_id).first()
    if income:
        income.source = source
        income.amount = float(amount)
        income.date = date
        db.session.commit()
        return True
    return False

def delete_income(income_id, user_id):
    income = Income.query.filter_by(id=income_id, user_id=user_id).first()
    if income:
        db.session.delete(income)
        db.session.commit()
        return True
    return False

def get_expenses_fortbl_by_user_id(user_id):
    expenses = Expense.query.filter_by(user_id=user_id).all()
    return [(exp.id, exp.user_id, exp.category, exp.amount, exp.date, exp.description) for exp in expenses]

def create_expense(user_id, category, amount, date, description=None):
    new_expense = Expense(user_id=user_id, category=category, amount=amount, date=date, description=description)
    db.session.add(new_expense)
    db.session.commit()

def get_goals_by_user_id(user_id):
    goals = Goal.query.filter_by(user_id=user_id).all()
    return [(g.id, g.user_id, g.goal, g.target_amount, g.current_amount) for g in goals]

def create_goal(user_id, goal, target_amount, current_amount):
    new_goal = Goal(user_id=user_id, goal=goal, target_amount=target_amount, current_amount=current_amount)
    db.session.add(new_goal)
    db.session.commit()

def get_goal_by_id(goal_id, user_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()
    if goal:
        return {
            'id': goal.id,
            'user_id': goal.user_id,
            'goal': goal.goal,
            'target_amount': goal.target_amount,
            'current_amount': goal.current_amount
        }
    return None

def update_goal(goal_id, user_id, goal_name, target_amount, current_amount):
    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()
    if goal:
        goal.goal = goal_name
        goal.target_amount = float(target_amount)
        goal.current_amount = float(current_amount)
        db.session.commit()
        return True
    return False

def update_goal_amount(goal_id, user_id, add_amount):
    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()
    if goal:
        goal.current_amount += float(add_amount)
        db.session.commit()
        return True
    return False

def delete_goal(goal_id, user_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()
    if goal:
        db.session.delete(goal)
        db.session.commit()
        return True
    return False

def get_user_by_id(user_id):
    user = db.session.get(User, user_id)
    if user:
        return {'id': user.id, 'username': user.username, 'profile_image': user.profile_image}
    return None

def update_user_profile(user_id, username, password=None, profile_image=None):
    user = db.session.get(User, user_id)
    if user:
        user.username = username
        if password:
            user.password = password
        if profile_image:
            user.profile_image = profile_image
        db.session.commit()

def get_expenses_by_user_id(user_id):
    expenses = Expense.query.filter_by(user_id=user_id).order_by(Expense.date).all()
    return [{'date': exp.date, 'amount': exp.amount} for exp in expenses]

def get_expense_by_id(expense_id, user_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
    if expense:
        return {
            'id': expense.id,
            'user_id': expense.user_id,
            'category': expense.category,
            'amount': expense.amount,
            'date': expense.date,
            'description': expense.description
        }
    return None

def update_expense(expense_id, user_id, category, amount, date, description=None):
    expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
    if expense:
        expense.category = category
        expense.amount = amount
        expense.date = date
        expense.description = description
        db.session.commit()
        return True
    return False

def delete_expense(expense_id, user_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
    if expense:
        db.session.delete(expense)
        db.session.commit()
        return True
    return False

def generate_sample_expenses(user_id):
    """Generate realistic sample expenses across multiple months for testing prediction models."""
    import random
    from datetime import datetime, timedelta
    
    categories = ['Groceries', 'Utilities', 'Gas', 'Dining', 'Shopping', 'Entertainment', 'Transportation', 'Healthcare']
    
    # Generate expenses for the past 6 months
    today = datetime.now()
    start_date = today - timedelta(days=180)
    
    # Create 40-60 random expenses across 6 months
    num_expenses = random.randint(40, 60)
    
    for _ in range(num_expenses):
        random_days = random.randint(0, 180)
        expense_date = start_date + timedelta(days=random_days)
        date_str = expense_date.strftime('%Y-%m-%d')
        
        category = random.choice(categories)
        
        # Amount varies by category
        if category == 'Groceries':
            amount = round(random.uniform(30, 100), 2)
        elif category == 'Utilities':
            amount = round(random.uniform(50, 150), 2)
        elif category == 'Gas':
            amount = round(random.uniform(40, 80), 2)
        elif category == 'Dining':
            amount = round(random.uniform(15, 60), 2)
        elif category == 'Shopping':
            amount = round(random.uniform(20, 150), 2)
        elif category == 'Entertainment':
            amount = round(random.uniform(10, 50), 2)
        elif category == 'Transportation':
            amount = round(random.uniform(5, 30), 2)
        else:  # Healthcare
            amount = round(random.uniform(25, 200), 2)
        
        description = f"{category} purchase on {date_str}"
        create_expense(user_id, category, amount, date_str, description)
    
    return num_expenses
