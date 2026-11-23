"""Pytest configuration and session-wide fixtures for Airial API testing."""

import os
from collections.abc import Generator

import pytest
from dotenv import load_dotenv

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

    base.create_pool()
    yield
    base.close_pool()
