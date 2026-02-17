import pytest
import os

os.environ['SESSION_REDIS'] = 'redis://:Zp1dRLnsUKY9CNOW6ukL@localhost:6379'

@pytest.fixture(scope="session", autouse=True)
def global_env():
    # This just ensures the env is locked in
    return True