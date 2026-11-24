"""Pytest configuration and session-wide fixtures for Airial API testing."""

import pytest
from dotenv import load_dotenv

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
