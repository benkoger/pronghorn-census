"""Pytest configuration and global session fixtures."""

import pytest
from dotenv import load_dotenv

load_dotenv(".env.test", override=True)


@pytest.fixture(scope="session", autouse=True)
def global_env():
    """Ensure test environment variables are loaded for the test session.

    Returns:
        True indicating test environment variables were loaded.
    """
    return True
