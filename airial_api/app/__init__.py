"""Airial Flask application factory package."""

import os

from boto3 import client
from flask import Flask
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

import app.errors as errors
from app.extensions import base, cache, health, login_manager, session_manager
from config import FlaskConfig, cache_config, s3_config
from database.errors import AirialError

# ---------------------------------------------------------------------------------------------------------------------------#


def create_app():
    """Create and configure the Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(FlaskConfig)

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [app.config["ORIGIN_URL"]],
                "supports_credentials": True,
            }
        },
    )

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Register s3 service app wide
    setattr(
        app,
        "s3",
        client("s3", config=s3_config, endpoint_url=os.environ.get("AWS_ENDPOINT_URL_S3")),
    )

    cache.init_app(app, cache_config)
    login_manager.init_app(app)
    session_manager.init_app(app)
    base.init_app(app)

    app.errorhandler(HTTPException)(errors.handle_generic_http)
    app.errorhandler(AirialError)(errors.handle_airial_error)
    app.errorhandler(Exception)(errors.internal_service_error)

    app.add_url_rule("/api/v1/healthcheck", "healthcheck", view_func=lambda: health.run())

    from app.routers import bp

    app.register_blueprint(bp)

    return app
