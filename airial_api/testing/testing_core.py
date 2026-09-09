from contextlib import contextmanager
from typing import Any
from unittest.mock import patch
from moto import mock_aws
import pytest
from app import create_app
from app.extensions import base

import io
from PIL import Image as PILImage


class APITester:

    @staticmethod
    def _generate_jpeg_bytes(
        width: int = 500, height: int = 500, color: str = "red"
    ) -> bytes:
        """Generate fresh in-memory JPEG bytes."""
        buf = io.BytesIO()
        PILImage.new("RGB", (width, height), color=color).save(buf, format="JPEG")
        return buf.getvalue()

    @pytest.fixture
    def app(self, monkeypatch):
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
                s3_client: Any = getattr(app, "s3")
                bucket_name = app.config.get("BUCKET_NAME", "airial-bucket")
                s3_client.create_bucket(Bucket=bucket_name)

                self.s3 = s3_client
                self.bucket_name = bucket_name

            yield app

            base.close_pool()

    @pytest.fixture
    def client(self, app):
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def auth_client(self, client, app):
        res = client.post(
            "/api/v1/authenticate",
            json={"email": "tester@local.host", "password": "Learning2Count"},
            follow_redirects=True,
        )
        assert res.status_code == 200, f"Authentication failed: {res.get_json()}"
        yield client

    @pytest.fixture
    def runner(self, app):
        return app.test_cli_runner()

    @pytest.fixture(scope="function", autouse=True)
    def rollback_db_transaction(self, app):
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
