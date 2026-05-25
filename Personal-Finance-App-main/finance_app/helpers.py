import sqlite3
import calendar
from .config import Config
from .models import get_income_by_user_id, get_expenses_fortbl_by_user_id

def create_connection():
    conn = None
    try:
        conn = sqlite3.connect(Config.DB_PATH)
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
