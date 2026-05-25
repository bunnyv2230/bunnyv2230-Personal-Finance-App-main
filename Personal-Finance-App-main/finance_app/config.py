import os

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev_secret_key_123')
    
    # Database configuration
    # Ensure personal_finance.db is created at the project root
    BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    DB_PATH = os.path.join(BASEDIR, 'personal_finance.db').replace('\\', '/')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + DB_PATH
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload configuration
    UPLOAD_FOLDER = os.path.join(BASEDIR, 'static', 'profile_images').replace('\\', '/')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit
    
    # OAuth configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'YOUR_GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', 'YOUR_GOOGLE_CLIENT_SECRET')
