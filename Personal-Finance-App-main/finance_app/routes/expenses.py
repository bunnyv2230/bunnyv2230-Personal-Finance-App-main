from flask import render_template, redirect, url_for, session, request, flash
from ..models import (
    create_expense, get_expenses_fortbl_by_user_id, generate_sample_expenses,
    get_expense_by_id, update_expense, delete_expense
)

def register_expenses_routes(app):
    
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
