from flask import current_app
from healthcheck import HealthCheck
from flask_caching import Cache
from flask_login import LoginManager
from flask_session import Session
from werkzeug.local import LocalProxy

from config import db_config, spice_config
from database import Database as db

login_manager = LoginManager()
cache = Cache()
session_manager = Session()
s3 = LocalProxy(lambda: getattr(current_app, "s3"))

health = HealthCheck()

base = db(db_config, spice_config)  # pyright: ignore
