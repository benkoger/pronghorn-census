from flask_login import LoginManager 
from flask_caching import Cache
from flask_session import Session
from database import Database as db
from config import db_config
from werkzeug.local import LocalProxy
from flask import current_app

login_manager = LoginManager()
cache = Cache()
session_manager = Session()
s3 = LocalProxy(lambda: getattr(current_app, 's3'))

base = db(db_config) # pyright: ignore