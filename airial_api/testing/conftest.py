"""Pytest configuration and session-wide fixtures for Airial API testing."""

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
from dotenv import load_dotenv
from flask import Flask
from moto import mock_aws

load_dotenv(".env.test")


@pytest.fixture(scope="session", autouse=True)
def global_env() -> bool:
    """Ensures test environment variables are loaded and locked for the session.

    This autouse fixture runs once per test session to guarantee that all
    environment variables defined in `.env.test` (when present) are set before
    any test modules or app instances are initialized, without overriding
    container or CI environment variables.

    Returns:
        bool: True indicating the environment configuration has been locked in.
    """
    return True


@pytest.fixture(scope="session", autouse=True)
def database_pool() -> Generator[None]:
    """Open the database connection pool once for the entire test session.

    Opening and closing a pool for every test adds overhead and retains extra
    resources; every test rolls its transaction back, so one pool is shared.

    Yields:
        None: Active session connection pool lifetime.
    """
    from app.extensions import base

    base.create_pool()
    yield
    base.close_pool()


@pytest.fixture(scope="session")
def app(database_pool: None) -> Generator[Flask]:
    """Create and configure a single Flask application instance per session.

    Configures mock AWS S3 credentials and endpoint overrides, instantiates the
    application once under a session-wide moto S3 mock, and creates the test
    bucket so individual tests do not repeatedly allocate app/S3 state.

    Args:
        database_pool (None): Ensures the session DB pool is initialized first.

    Yields:
        Flask: The configured Flask application instance.
    """
    from app import create_app

    with pytest.MonkeyPatch.context() as mp:
        mp.delenv("AWS_ENDPOINT_URL_S3", raising=False)
        mp.setenv("AWS_ACCESS_KEY_ID", "foobar_key")
        mp.setenv("AWS_SECRET_ACCESS_KEY", "foobar_secret")
        mp.setenv("AWS_SECURITY_TOKEN", "foobar_token")
        mp.setenv("AWS_SESSION_TOKEN", "foobar_token")

        with mock_aws():
            with patch("config.s3_config", None):
                flask_app = create_app()

            flask_app.config.update(
                {
                    "TESTING": True,
                    "SESSION_COOKIE_SECURE": False,
                    "SESSION_COOKIE_DOMAIN": None,
                    "SESSION_COOKIE_HTTPONLY": False,
                    "SERVER_NAME": "localhost",
                }
            )

            with flask_app.app_context():
                s3_client: Any = flask_app.s3
                bucket_name = flask_app.config.get("BUCKET_NAME", "airial-bucket")
                s3_client.create_bucket(Bucket=bucket_name)

            yield flask_app
