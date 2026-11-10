"""Test harness core infrastructure for the Airial API test suite."""

import io
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

import pytest
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner
from moto import mock_aws
from PIL import Image as PILImage

from app import create_app
from app.extensions import base


class APITester:
    """Base test harness class providing fixtures and helpers for API testing.

    Attributes:
        s3 (Any): Boto3 S3 client instance connected to the mocked AWS environment.
        bucket_name (str): Name of the mock S3 bucket created for test uploads.
    """

    @staticmethod
    def _generate_jpeg_bytes(
        width: int = 500, height: int = 500, color: str = "red"
    ) -> bytes:
        """Generates fresh in-memory JPEG image bytes.

        Args:
            width (int): Width of the generated image in pixels. Defaults to 500.
            height (int): Height of the generated image in pixels. Defaults to 500.
            color (str): Fill color for the image. Defaults to "red".

        Returns:
            bytes: Binary content of the encoded JPEG image.
        """
        buf = io.BytesIO()
        PILImage.new("RGB", (width, height), color=color).save(buf, format="JPEG")
        return buf.getvalue()

    @pytest.fixture
    def app(self, monkeypatch: pytest.MonkeyPatch) -> Generator[Flask, None, None]:
        """Creates and configures a Flask application instance for testing.

        Configures mock AWS S3 credentials and endpoint overrides, instantiates the
        application with mocked S3 configurations, establishes a PostgreSQL connection
        pool, creates the designated test bucket, and tears down the pool after tests.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest fixture used to override AWS
                environment variables.

        Yields:
            Flask: The configured Flask application instance.
        """
        monkeypatch.delenv("AWS_ENDPOINT_URL_S3", raising=False)
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "foobar_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "foobar_secret")
        monkeypatch.setenv("AWS_SECURITY_TOKEN", "foobar_token")
        monkeypatch.setenv("AWS_SESSION_TOKEN", "foobar_token")

        with mock_aws():
            with patch("config.s3_config", None):
                app = create_app()

            base._config["host"] = "localhost"
            base.create_pool()

            app.config.update(
                {
                    "TESTING": True,
                    "SESSION_COOKIE_SECURE": False,
                    "SESSION_COOKIE_DOMAIN": None,
                    "SESSION_COOKIE_HTTPONLY": False,
                    "SERVER_NAME": "localhost",
                }
            )

            with app.app_context():
                s3_client: Any = app.s3
                bucket_name = app.config.get("BUCKET_NAME", "airial-bucket")
                s3_client.create_bucket(Bucket=bucket_name)

                self.s3 = s3_client
                self.bucket_name = bucket_name

            yield app

            base.close_pool()

    @pytest.fixture
    def client(self, app: Flask) -> Generator[FlaskClient, None, None]:
        """Provides an unauthenticated Flask test client.

        Args:
            app (Flask): The Flask application fixture.

        Yields:
            FlaskClient: The test client for issuing HTTP requests against the application.
        """
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def auth_client(self, client: FlaskClient) -> Generator[FlaskClient, None, None]:
        """Provides an authenticated Flask test client session.

        Logs into the application using predefined test credentials via the
        authentication endpoint prior to yielding the client session.

        Args:
            client (FlaskClient): The unauthenticated Flask test client fixture.

        Yields:
            FlaskClient: The authenticated test client carrying valid session cookies.
        """
        client.post(
            "/api/v1/authenticate",
            json={"email": "tester@local.host", "password": "Learning2Count"},
            follow_redirects=True,
        )
        yield client

    @pytest.fixture
    def runner(self, app: Flask) -> FlaskCliRunner:
        """Provides a test CLI runner for invoking Click-based application commands.

        Args:
            app (Flask): The Flask application fixture.

        Returns:
            FlaskCliRunner: A test runner configured for the application's CLI.
        """
        return app.test_cli_runner()

    @pytest.fixture(scope="function", autouse=True)
    def rollback_db_transaction(self, app: Flask) -> Generator[None, None, None]:
        """Enforces database transaction isolation across individual test runs.

        Checks out a connection from the pool, disables autocommit, intercepts
        and nullifies commit calls, and executes an explicit rollback upon test
        completion to ensure tests do not persist side effects to the database.

        Args:
            app (Flask): The Flask application fixture providing access to the base
                database extension.

        Yields:
            None: Context during test execution with mocked transaction control.
        """
        db_instance = app.extensions["base"]

        if not db_instance._pool:
            db_instance.create_pool()

        conn = db_instance._pool.getconn()
        conn.autocommit = False

        real_commit = conn.commit
        conn.commit = lambda: None

        @contextmanager
        def mock_connection():
            yield conn

        with patch.object(db_instance._pool, "connection", side_effect=mock_connection):
            yield

            conn.rollback()

        conn.commit = real_commit
        db_instance._pool.putconn(conn)
