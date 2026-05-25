import os
from flask import render_template, redirect, url_for, session, request, flash, g, jsonify, current_app
from werkzeug.utils import secure_filename
from ..extensions import bcrypt, oauth
from ..models import get_user_by_username, create_user, get_user_by_id, update_user_profile, User

def register_auth_routes(app):
    
    @app.route('/login/google')
    def google_login():
        google = oauth.google
        redirect_uri = url_for('google_authorized', _external=True)
        return google.authorize_redirect(redirect_uri)

    @app.route('/login/google/authorized')
    def google_authorized():
        google = oauth.google
        token = google.authorize_access_token()
        user_info = google.parse_id_token(token)

        session['google_token'] = token
        session['user_id'] = user_info['sub']
        session['username'] = user_info['name']
        session['email'] = user_info['email']
        return redirect(url_for('home'))

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
        
        user_obj = User.query.get(user_id)
        
        if user_obj and bcrypt.check_password_hash(user_obj.password, password):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Incorrect password'})

    @app.route('/profile', methods=['GET', 'POST'])
    def profile():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        user_id = session['user_id']
        user = get_user_by_id(user_id)

        if request.method == 'POST':
            new_username = request.form['username']
            new_password = request.form.get('password', None)

            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8') if new_password else None

            profile_image = None
            if 'profile_image' in request.files:
                file = request.files['profile_image']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    profile_image = filename

            update_user_profile(user_id, new_username, hashed_password, profile_image)
            flash('Profile updated!', 'success')
            return redirect(url_for('profile'))

        return render_template('profile.html', user=user)
