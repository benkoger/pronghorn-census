"""Flask extensions and service clients initialization."""

from flask import current_app
from flask_caching import Cache
from flask_login import LoginManager
from flask_session import Session
from healthcheck import HealthCheck
from werkzeug.local import LocalProxy

from config import db_config, spice_config
from database import Database as db

login_manager = LoginManager()
cache = Cache()
session_manager = Session()
s3 = LocalProxy(lambda: getattr(current_app, "s3"))

base = db(db_config, spice_config)  # pyright: ignore

health = HealthCheck()


def first_run():
    """Check if database has completed bootstrap initialization."""
    return base.check_bootstrapped(), "first_run"


health.add_check(first_run)
