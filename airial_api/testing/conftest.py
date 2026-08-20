import pytest
from dotenv import load_dotenv

load_dotenv(".env.test", override=True)


@pytest.fixture(scope="session", autouse=True)
def global_env():
    # This just ensures the env is locked in
    return True
