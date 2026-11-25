"""Pytest configuration and session-wide fixtures for Airial API testing."""

import os
from collections.abc import Generator
from typing import Any
from unittest.mock import patch
from uuid import UUID

import fakeredis
import pytest
import redis
from authzed.api.v1 import (
    BulkCheckPermissionPair,
    BulkCheckPermissionResponse,
    BulkCheckPermissionResponseItem,
    CheckPermissionResponse,
    WriteRelationshipsResponse,
)
from dotenv import load_dotenv
from flask import Flask
from moto import mock_aws

# Patch redis.from_url to in-memory fakeredis instances so Valkey is not needed
_fake_server = fakeredis.FakeServer()
_fake_redis_instances: dict[str, fakeredis.FakeRedis] = {}


def _fake_from_url(url: str, **kwargs):
    if url not in _fake_redis_instances:
        _fake_redis_instances[url] = fakeredis.FakeRedis(server=_fake_server)
    return _fake_redis_instances[url]


redis.from_url = _fake_from_url


class MockSpiceClient:
    """Mock SpiceDB client providing in-memory authorized responses."""

    def CheckPermission(self, request):
        """Checks if a subject has permission on a resource.

        Args:
            request: CheckPermissionRequest containing subject and resource.

        Returns:
            CheckPermissionResponse with PERMISSIONSHIP_HAS_PERMISSION.
        """
        return CheckPermissionResponse(
            permissionship=CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
        )

    def BulkCheckPermission(self, request):
        """Performs bulk permission checks for multiple resource-subject pairs.

        Args:
            request: BulkCheckPermissionRequest containing items to verify.

        Returns:
            BulkCheckPermissionResponse containing granted permissions for all items.
        """
        pairs = [
            BulkCheckPermissionPair(
                request=item,
                item=BulkCheckPermissionResponseItem(
                    permissionship=CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
                ),
            )
            for item in request.items
        ]
        return BulkCheckPermissionResponse(pairs=pairs)

    def WriteRelationships(self, request):
        """Simulates writing relationships to SpiceDB.

        Args:
            request: WriteRelationshipsRequest containing relationship updates.

        Returns:
            WriteRelationshipsResponse indicating success.
        """
        return WriteRelationshipsResponse()

    def LookupResources(self, request):
        """Simulates looking up resources accessible by a subject.

        Args:
            request: LookupResourcesRequest specifying permissions and subjects.

        Returns:
            list: Empty list of matching resource IDs.
        """
        return []


# support running on runner or locally with .env.test
if not os.getenv("CI"):
    load_dotenv(".env.test", override=True)


@pytest.fixture(scope="session", autouse=True)
def global_env() -> bool:
    """Ensures test environment variables are loaded and locked for the session.

    This autouse fixture runs once per test session to guarantee that all
    environment variables defined in `.env.test` are properly set before any
    test modules or app instances are initialized.

    Returns:
        bool: True indicating the environment configuration has been locked in.
    """
    # This just ensures the env is locked in
    return True


@pytest.fixture(scope="session", autouse=True)
def database_pool() -> Generator[None]:
    """Opens the database connection pool once for the session.

    Opening and closing a pool for each test costs about a second; every test
    rolls its transaction back, so they can share one.

    Yields:
        None: The session's tests, run on the open pool.
    """
    # Imported here so the environment above is loaded before the app reads it.
    from app.extensions import base

    base._spice_client = MockSpiceClient()
    base.create_pool()
    yield
    base.close_pool()


@pytest.fixture(scope="session")
def shared_app(database_pool: None) -> Generator[Flask]:
    """Instantiates and configures a shared Flask application for the test session.

    Creates the application once per worker session, pre-authenticates the test
    user, initializes mock S3 buckets, and sets up session defaults.

    Args:
        database_pool: The session database connection pool fixture.

    Yields:
        Flask: The configured Flask application instance.
    """
    os.environ["AWS_ACCESS_KEY_ID"] = "foobar_key"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "foobar_secret"
    os.environ["AWS_SECURITY_TOKEN"] = "foobar_token"
    os.environ["AWS_SESSION_TOKEN"] = "foobar_token"
    os.environ.pop("AWS_ENDPOINT_URL_S3", None)

    with mock_aws(), patch("config.s3_config", None):
        from app import create_app
        from app.extensions import base, login_manager
        from database.object_models.user_management import User

        app = create_app()

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
            base._spice_client = MockSpiceClient()

            test_users = base.where(User, {"email": "tester@local.host"})
            if test_users:
                test_user = test_users[0]
                test_user.roles = ["admin", "root", "annotator"]
                test_user.active_org_uuid = UUID("f383aa1c-1bdf-46fb-87f5-ed37effe17bd")
                login_manager.request_loader(lambda req: test_user)

            @app.before_request
            def set_test_session():
                from flask import session

                if "active_org_uuid" not in session:
                    session["active_org_uuid"] = "f383aa1c-1bdf-46fb-87f5-ed37effe17bd"

            s3_client: Any = app.s3
            bucket_name = app.config.get("BUCKET_NAME", "airial-bucket")
            s3_client.create_bucket(Bucket=bucket_name)

            yield app
