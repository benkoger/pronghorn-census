from flask_login import LoginManager 
from flask_caching import Cache
from flask_session import Session
from database import Database as db
from config import db_config

login_manager = LoginManager()
cache = Cache()
session_manager = Session()

# Initialized post_fork by gunicorn
base = db(db_config) # pyright: ignore