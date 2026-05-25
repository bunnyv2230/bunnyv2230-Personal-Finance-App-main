from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
bcrypt = Bcrypt()
oauth = OAuth()
