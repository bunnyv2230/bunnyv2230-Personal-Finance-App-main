from flask import render_template, redirect, url_for, session, request, flash
from ..models import (
    create_income, get_income_by_user_id, get_income_by_id,
    update_income, delete_income
)

def register_income_routes(app):
    
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
