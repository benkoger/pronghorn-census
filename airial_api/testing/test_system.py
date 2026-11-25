"""Integration and unit tests for the System API endpoints."""

from flask.testing import FlaskClient
from testing_core import APITester

from app.extensions import base

BOOTSTRAPPED_URL = "/api/v1/bootstrapped"


def _set_first_run(value: bool) -> None:
    """Update the database initialization first_run flag inside the test transaction.

    Args:
        value (bool): Target boolean value for usermanagement.initialization.first_run.
    """

    def _run(cursor, _db) -> None:
        cursor.execute(
            "UPDATE usermanagement.initialization SET first_run = %(val)s;",
            {"val": value},
        )

    base.execute(_run)


class TestSystem(APITester):
    """Test suite covering the `/api/v1/bootstrapped` REST endpoints.

    Inherits from `APITester` to provide authenticated and unauthenticated Flask
    test clients along with automatic database transaction rollbacks.
    """

    # -------------------------------------------------------------------------
    # 1. GET Bootstrapped Status
    # -------------------------------------------------------------------------

    def test_check_bootstrapped_true(self, client: FlaskClient) -> None:
        """Verify GET /bootstrapped returns true when system is already initialized.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.get(BOOTSTRAPPED_URL)
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, dict)
        assert data["result"] is True

    def test_check_bootstrapped_false_when_first_run(
        self, client: FlaskClient
    ) -> None:
        """Verify GET /bootstrapped returns false when first_run is true.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        _set_first_run(True)

        response = client.get(BOOTSTRAPPED_URL)
        assert response.status_code == 200

        data = response.get_json()
        assert data == {"result": False}

    # -------------------------------------------------------------------------
    # 2. POST Finish Bootstrap
    # -------------------------------------------------------------------------

    def test_finish_bootstrap_success(self, auth_client: FlaskClient) -> None:
        """Verify POST /bootstrapped sets first_run to false and returns 204.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        _set_first_run(True)
        assert auth_client.get(BOOTSTRAPPED_URL).get_json() == {"result": False}

        response = auth_client.post(BOOTSTRAPPED_URL)
        assert response.status_code == 204
        assert response.data == b""

        check_response = auth_client.get(BOOTSTRAPPED_URL)
        assert check_response.status_code == 200
        assert check_response.get_json() == {"result": True}

    def test_finish_bootstrap_idempotent(self, auth_client: FlaskClient) -> None:
        """Verify POST /bootstrapped succeeds idempotently when already bootstrapped.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.post(BOOTSTRAPPED_URL)
        assert response.status_code == 204
        assert auth_client.get(BOOTSTRAPPED_URL).get_json() == {"result": True}
