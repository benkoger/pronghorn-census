"""Test harness core infrastructure for the Airial API test suite."""

import gc
import io
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

import pytest
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner
from PIL import Image as PILImage


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
    def app(self, shared_app: Flask) -> Generator[Flask]:
        """Provides the shared Flask application instance for the test.

        Args:
            shared_app (Flask): The session-scoped Flask application fixture.

        Yields:
            Flask: The configured Flask application instance.
        """
        self.s3 = shared_app.s3
        self.bucket_name = shared_app.config.get("BUCKET_NAME", "airial-bucket")
        yield shared_app

    @pytest.fixture(scope="function", autouse=True)
    def isolate_s3_and_gc(self, app: Flask) -> Generator[None]:
        """Bind mocked S3 helpers and purge test artifacts after each test.

        Clears any objects or multipart uploads written to the session-scoped
        mocked S3 bucket and runs garbage collection so large image/NumPy buffers
        are released promptly on low-memory hosts.

        Args:
            app (Flask): Session-scoped Flask application fixture.

        Yields:
            None: Per-test execution context with isolated S3 state.
        """
        s3_client: Any = app.s3
        bucket_name = app.config.get("BUCKET_NAME", "airial-bucket")
        self.s3 = s3_client
        self.bucket_name = bucket_name

        yield

        listed = s3_client.list_objects_v2(Bucket=bucket_name)
        contents = listed.get("Contents") or []
        if contents:
            s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={"Objects": [{"Key": obj["Key"]} for obj in contents]},
            )

        uploads = s3_client.list_multipart_uploads(Bucket=bucket_name)
        for upload in uploads.get("Uploads") or []:
            s3_client.abort_multipart_upload(
                Bucket=bucket_name,
                Key=upload["Key"],
                UploadId=upload["UploadId"],
            )

        gc.collect()

    @pytest.fixture
    def client(self, app: Flask) -> Generator[FlaskClient]:
        """Provides an unauthenticated Flask test client.

        Args:
            app (Flask): The Flask application fixture.

        Yields:
            FlaskClient: The test client for issuing HTTP requests against the application.
        """
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def auth_client(self, client: FlaskClient) -> Generator[FlaskClient]:
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
    def rollback_db_transaction(self, app: Flask) -> Generator[None]:
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
