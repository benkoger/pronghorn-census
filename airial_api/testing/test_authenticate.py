"""Integration and unit tests for the Authentication API endpoints."""

from typing import Any
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from flask.testing import FlaskClient
from testing_core import APITester

from app.extensions import base
from database.object_models.core.images import Image, UpdateImageReq
from database.object_models.user_management.users import UpdateUserReq, User

AUTHORIZE_URL = "/api/v1/authorize"
CALLBACK_URL = "/api/v1/callback"
AUTHENTICATE_URL = "/api/v1/authenticate"
DEAUTHENTICATE_URL = "/api/v1/deauthenticate"
OAUTH_USER_EMAIL = "michaelbraydenlance@gmail.com"
OAUTH_USER_ID = 3
LOCKED_IMAGE_ID = 1047


def _mock_response(status_code: int, payload: dict[str, Any]) -> MagicMock:
    """Create a mock HTTP response object for requests calls.

    Args:
        status_code (int): HTTP status code returned by the mock response.
        payload (dict[str, Any]): JSON dictionary returned by `.json()`.

    Returns:
        MagicMock: Configured mock response instance.
    """
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    return resp


class TestAuthenticate(APITester):
    """Test suite covering OAuth2 and legacy password authentication endpoints.

    Inherits from `APITester` to provide Flask test clients and automatic
    database transaction rollbacks for isolation.
    """

    # -------------------------------------------------------------------------
    # 1. GET OAuth2 Authorize
    # -------------------------------------------------------------------------

    def test_oauth2_authorize_google_redirects(self, client: FlaskClient) -> None:
        """Verify GET /authorize/google redirects to Google OAuth and sets state.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.get(f"{AUTHORIZE_URL}/google")
        assert response.status_code == 302

        location = response.headers["Location"]
        parsed = urlparse(location)
        assert parsed.netloc == "accounts.google.com"

        params = parse_qs(parsed.query)
        assert params["response_type"] == ["code"]
        assert "state" in params

        with client.session_transaction() as sess:
            assert sess["oauth2_state"] == params["state"][0]

    def test_oauth2_authorize_unknown_provider(self, client: FlaskClient) -> None:
        """Verify 404 response for an unconfigured OAuth2 provider.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.get(f"{AUTHORIZE_URL}/unknown-provider")
        assert response.status_code == 404

    # -------------------------------------------------------------------------
    # 2. GET OAuth2 Callback
    # -------------------------------------------------------------------------

    def test_oauth2_callback_unknown_provider(self, client: FlaskClient) -> None:
        """Verify 404 response when callback provider does not exist.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.get(f"{CALLBACK_URL}/unknown-provider")
        assert response.status_code == 404

    def test_oauth2_callback_provider_error(self, client: FlaskClient) -> None:
        """Verify 500 response when OAuth provider returns an error query param.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.get(
            f"{CALLBACK_URL}/google", query_string={"error": "access_denied"}
        )
        assert response.status_code == 500

    def test_oauth2_callback_invalid_state(self, client: FlaskClient) -> None:
        """Verify 401 response when callback state does not match session state.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        with client.session_transaction() as sess:
            sess["oauth2_state"] = "expected-state"

        response = client.get(
            f"{CALLBACK_URL}/google",
            query_string={"state": "wrong-state", "code": "auth-code"},
        )
        assert response.status_code == 401

    def test_oauth2_callback_missing_code(self, client: FlaskClient) -> None:
        """Verify 401 response when authorization code is missing.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        with client.session_transaction() as sess:
            sess["oauth2_state"] = "valid-state"

        response = client.get(
            f"{CALLBACK_URL}/google", query_string={"state": "valid-state"}
        )
        assert response.status_code == 401

    def test_oauth2_callback_token_exchange_failure(
        self, client: FlaskClient
    ) -> None:
        """Verify 401 response when token exchange fails or omits access token.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        with client.session_transaction() as sess:
            sess["oauth2_state"] = "valid-state"

        with patch(
            "app.routers.authenticate.requests.post",
            return_value=_mock_response(400, {}),
        ):
            res_bad_status = client.get(
                f"{CALLBACK_URL}/google",
                query_string={"state": "valid-state", "code": "abc"},
            )
            assert res_bad_status.status_code == 401

        with patch(
            "app.routers.authenticate.requests.post",
            return_value=_mock_response(200, {}),
        ):
            res_no_token = client.get(
                f"{CALLBACK_URL}/google",
                query_string={"state": "valid-state", "code": "abc"},
            )
            assert res_no_token.status_code == 401

    def test_oauth2_callback_userinfo_failure_and_user_not_found(
        self, client: FlaskClient
    ) -> None:
        """Verify 401 on userinfo error and 404 when user email is unknown.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        with client.session_transaction() as sess:
            sess["oauth2_state"] = "valid-state"

        with (
            patch(
                "app.routers.authenticate.requests.post",
                return_value=_mock_response(200, {"access_token": "tok"}),
            ),
            patch(
                "app.routers.authenticate.requests.get",
                return_value=_mock_response(401, {}),
            ),
        ):
            res_userinfo_fail = client.get(
                f"{CALLBACK_URL}/google",
                query_string={"state": "valid-state", "code": "abc"},
            )
            assert res_userinfo_fail.status_code == 401

        with (
            patch(
                "app.routers.authenticate.requests.post",
                return_value=_mock_response(200, {"access_token": "tok"}),
            ),
            patch(
                "app.routers.authenticate.requests.get",
                return_value=_mock_response(
                    200, {"email": "nonexistent@example.com", "sub": "999"}
                ),
            ),
        ):
            res_no_user = client.get(
                f"{CALLBACK_URL}/google",
                query_string={"state": "valid-state", "code": "abc"},
            )
            assert res_no_user.status_code == 404

    def test_oauth2_callback_success_active_and_invited(
        self, client: FlaskClient
    ) -> None:
        """Verify OAuth2 callback logs in existing active and invited users.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        with client.session_transaction() as sess:
            sess["oauth2_state"] = "valid-state"

        with (
            patch(
                "app.routers.authenticate.requests.post",
                return_value=_mock_response(200, {"access_token": "tok"}),
            ),
            patch(
                "app.routers.authenticate.requests.get",
                return_value=_mock_response(
                    200, {"email": OAUTH_USER_EMAIL, "sub": "google-sub-123"}
                ),
            ),
        ):
            response = client.get(
                f"{CALLBACK_URL}/google",
                query_string={"state": "valid-state", "code": "abc"},
            )
            assert response.status_code == 302
            assert client.get("/api/v1/users/check-auth").data == b"true"

        # Reset user to invited state to exercise invited activation branch.
        base.update(User, OAUTH_USER_ID, UpdateUserReq(status="invited"))
        with client.session_transaction() as sess:
            sess["oauth2_state"] = "valid-state-2"

        with (
            patch(
                "app.routers.authenticate.requests.post",
                return_value=_mock_response(200, {"access_token": "tok"}),
            ),
            patch(
                "app.routers.authenticate.requests.get",
                return_value=_mock_response(
                    200, {"email": OAUTH_USER_EMAIL, "sub": "new-sub-456"}
                ),
            ),
        ):
            invited_res = client.get(
                f"{CALLBACK_URL}/google",
                query_string={"state": "valid-state-2", "code": "xyz"},
            )
            assert invited_res.status_code == 302
            updated_user = base.get(User, OAUTH_USER_ID)
            assert updated_user.status == "active"
            assert updated_user.external_auth_id == "new-sub-456"

    # -------------------------------------------------------------------------
    # 3. POST Legacy Email/Password Authentication
    # -------------------------------------------------------------------------

    def test_authenticate_success(self, client: FlaskClient) -> None:
        """Verify valid email and password login succeeds and sets active org.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.post(
            AUTHENTICATE_URL,
            json={"email": "tester@local.host", "password": "Learning2Count"},
        )
        assert response.status_code == 200
        assert response.data == b""
        assert client.get("/api/v1/users/check-auth").data == b"true"

        with client.session_transaction() as sess:
            assert "active_org_uuid" in sess

    def test_authenticate_invalid_credentials(self, client: FlaskClient) -> None:
        """Verify 401 response for unknown email or incorrect password.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        bad_email = client.post(
            AUTHENTICATE_URL,
            json={"email": "nobody@local.host", "password": "Learning2Count"},
        )
        assert bad_email.status_code == 401

        bad_password = client.post(
            AUTHENTICATE_URL,
            json={"email": "tester@local.host", "password": "WrongPassword!"},
        )
        assert bad_password.status_code == 401

    def test_authenticate_without_password_hash(self, client: FlaskClient) -> None:
        """Verify 400 response when user lacks password hash configuration.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.post(
            AUTHENTICATE_URL,
            json={"email": OAUTH_USER_EMAIL, "password": "any-password"},
        )
        assert response.status_code == 400

    def test_authenticate_invalid_payload(self, client: FlaskClient) -> None:
        """Verify 400 validation error for malformed authentication requests.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert client.post(AUTHENTICATE_URL, json={}).status_code == 400
        assert (
            client.post(
                AUTHENTICATE_URL, json={"email": "tester@local.host"}
            ).status_code
            == 400
        )

    # -------------------------------------------------------------------------
    # 4. POST Deauthenticate (Logout)
    # -------------------------------------------------------------------------

    def test_deauthenticate_success_and_releases_locks(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify logout terminates session and releases user image locks.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        current_user_id = auth_client.get("/api/v1/users/current-user").get_json()[
            "user_id"
        ]
        base.update(
            Image,
            LOCKED_IMAGE_ID,
            UpdateImageReq(opened_by_user_id=current_user_id),
        )
        assert base.get(Image, LOCKED_IMAGE_ID).opened_by_user_id == current_user_id

        response = auth_client.post(DEAUTHENTICATE_URL)
        assert response.status_code == 200
        assert response.data == b""
        assert auth_client.get("/api/v1/users/check-auth").data == b"false"
        assert base.get(Image, LOCKED_IMAGE_ID).opened_by_user_id == 0

    def test_deauthenticate_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 response when logging out without an active session.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.post(DEAUTHENTICATE_URL)
        assert response.status_code == 401
