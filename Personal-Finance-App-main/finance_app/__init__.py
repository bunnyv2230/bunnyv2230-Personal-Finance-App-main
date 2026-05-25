import os
from flask import Flask, session, g
from .config import Config
from .extensions import db, bcrypt, oauth

# Load local .env file if it exists
# We look for it at the root folder level
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
env_path = os.path.join(root_dir, '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip() and not line.startswith('#') and '=' in line:
                key, val = line.strip().split('=', 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

from .models import get_user_by_id

def create_app():
    # Configure Flask templates and static folder relative to this file
    template_dir = os.path.join(root_dir, 'templates')
    static_dir = os.path.join(root_dir, 'static')
    
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    oauth.init_app(app)

    # Register OAuth clients
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        access_token_url='https://accounts.google.com/o/oauth2/token',
        access_token_params=None,
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        authorize_params=None,
        userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
        client_kwargs={'scope': 'openid email profile'},
    )

    # Ensure tables are created inside the database
    with app.app_context():
        db.create_all()

    # Request hooks
    @app.before_request
    def load_user():
        user_id = session.get('user_id')
        if user_id:
            g.user = get_user_by_id(user_id)
        else:
            g.user = None

    # Register route modules directly on the app (maintaining global url_for targets)
    from .routes.auth import register_auth_routes
    from .routes.expenses import register_expenses_routes
    from .routes.goals import register_goals_routes
    from .routes.income import register_income_routes
    from .routes.ml import register_ml_routes
    from .routes.main import register_main_routes

    register_auth_routes(app)
    register_expenses_routes(app)
    register_goals_routes(app)
    register_income_routes(app)
    register_ml_routes(app)
    register_main_routes(app)

    return app
