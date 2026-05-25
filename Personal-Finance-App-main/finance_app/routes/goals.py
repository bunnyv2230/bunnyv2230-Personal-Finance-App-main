from flask import render_template, redirect, url_for, session, request, flash
from ..models import (
    get_goals_by_user_id, create_goal, get_goal_by_id,
    update_goal, update_goal_amount, delete_goal
)
from ..helpers import get_leftover_salary_history

def register_goals_routes(app):
    
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
