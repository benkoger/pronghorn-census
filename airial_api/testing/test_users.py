"""Integration and unit tests for the Users API endpoints."""

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID, uuid4

from authzed.api.v1 import CheckPermissionResponse
from flask import Flask
from flask.testing import FlaskClient
from testing_core import APITester

from app.extensions import base, cache
from app.routers.users import load as load_user
from database.object_models.user_management.organizations import Organization
from database.object_models.user_management.roles import Role
from database.object_models.user_management.users import User, UserStatus

USERS_URL = "/api/v1/users"
TESTER_USER_ID = 1
TESTER_USER_UUID = "c1b7cceb-56ab-49a3-aac4-196ac278bdf3"
ORG_UUID = "f383aa1c-1bdf-46fb-87f5-ed37effe17bd"


def _make_stub_user(
    username: str = "StubUser", email: str = "stub@local.host"
) -> User:
    """Construct a synthetic User dataclass instance for mocked insert tests.

    Args:
        username (str): Username for the stub user.
        email (str): Email address for the stub user.

    Returns:
        User: Populated User model instance.
    """
    now = datetime.now(UTC)
    return User(
        user_id=999,
        username=username,
        email=email,
        external_auth_id="",
        external_auth_provider="",
        status=UserStatus.ACTIVE,
        created=now,
        modified=now,
        last_login=now,
        uuid=uuid4(),
        default_org_id=1,
        password_hash="hashed",
        roles=["admin"],
        locale="en/us",
    )


class TestUsers(APITester):
    """Test suite covering the `/api/v1/users` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients and
    automatic database transaction rollbacks for isolation.
    """

    # -------------------------------------------------------------------------
    # 1. GET Auth Status & Current User
    # -------------------------------------------------------------------------

    def test_check_auth_authenticated(self, auth_client: FlaskClient) -> None:
        """Verify /check-auth returns 'true' when logged in.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        auth_res = auth_client.get(f"{USERS_URL}/check-auth")
        assert auth_res.status_code == 200
        assert auth_res.data == b"true"

    def test_get_current_user_success(self, auth_client: FlaskClient) -> None:
        """Verify retrieving the authenticated user's profile and validating schema.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{USERS_URL}/current-user")
        assert response.status_code == 200

        data = response.get_json()
        validated = User.Response.model_validate(data)
        assert validated.user_id == TESTER_USER_ID
        assert str(validated.uuid) == TESTER_USER_UUID
        assert validated.email == "tester@local.host"

    def test_load_user_missing_and_default_org_fallback(
        self, app: Flask, auth_client: FlaskClient
    ) -> None:
        """Verify user_loader returns None when missing and falls back to default_org_id.

        Args:
            app (Flask): Flask application fixture.
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        missing_uuid = str(uuid4())
        cache.delete(f"user_{missing_uuid}")
        with (
            app.test_request_context(),
            patch.object(base, "get", return_value=None),
        ):
            assert load_user(missing_uuid) is None

        cache.delete(f"user_{TESTER_USER_UUID}")
        with auth_client.session_transaction() as sess:
            sess.pop("active_org_uuid", None)

        res = auth_client.get(f"{USERS_URL}/current-user")
        assert res.status_code == 200
        assert res.get_json()["user_id"] == TESTER_USER_ID
        cache.delete(f"user_{TESTER_USER_UUID}")

    # -------------------------------------------------------------------------
    # 2. GET User Organizations (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_get_user_organizations_by_uuid_and_int(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify retrieving organizations linked to a user by UUID and integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        res_uuid = auth_client.get(f"{USERS_URL}/{TESTER_USER_UUID}/organizations")
        assert res_uuid.status_code == 200
        orgs_uuid = res_uuid.get_json()
        assert isinstance(orgs_uuid, list)
        assert len(orgs_uuid) >= 1
        for item in orgs_uuid:
            Organization.Response.model_validate(item)

        res_id = auth_client.get(f"{USERS_URL}/{TESTER_USER_ID}/organizations")
        assert res_id.status_code == 200
        orgs_id = res_id.get_json()
        assert len(orgs_id) == len(orgs_uuid)

    def test_get_user_organizations_not_found(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 response when querying organizations for non-existent user UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert (
            auth_client.get(f"{USERS_URL}/{uuid4()}/organizations").status_code
            == 404
        )

    # -------------------------------------------------------------------------
    # 3. GET Role Check
    # -------------------------------------------------------------------------

    def test_check_role_true_and_false(self, auth_client: FlaskClient) -> None:
        """Verify /role-check returns 'true' for assigned role and 'false' otherwise.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        has_admin = auth_client.get(
            f"{USERS_URL}/role-check", query_string={"role_name": "admin"}
        )
        assert has_admin.status_code == 200
        assert has_admin.data == b"true"

        no_role = auth_client.get(
            f"{USERS_URL}/role-check",
            query_string={"role_name": "nonexistent_role"},
        )
        assert no_role.status_code == 200
        assert no_role.data == b"false"

    def test_check_role_missing_query(self, auth_client: FlaskClient) -> None:
        """Verify 400 when role_name query parameter is omitted.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.get(f"{USERS_URL}/role-check").status_code == 400

    # -------------------------------------------------------------------------
    # 4. PATCH Set Active Organization
    # -------------------------------------------------------------------------

    def test_set_active_organization_success(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify setting active organization updates session state and clears user cache.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.patch(
            f"{USERS_URL}/set-active-organization",
            json={"org_id": ORG_UUID},
        )
        assert response.status_code == 200
        assert response.data == b""

        with auth_client.session_transaction() as sess:
            assert sess["active_org_uuid"] == ORG_UUID
            assert f"org_{ORG_UUID}" in sess

        cache.delete(f"user_{TESTER_USER_UUID}")

    def test_set_active_organization_unauthorized(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 401 response when user lacks permission on target organization.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        mock_perm_res = type(
            "PermRes",
            (),
            {
                "permissionship": (
                    CheckPermissionResponse.PERMISSIONSHIP_NO_PERMISSION
                )
            },
        )()
        with patch.object(base, "check_permission", return_value=mock_perm_res):
            response = auth_client.patch(
                f"{USERS_URL}/set-active-organization",
                json={"org_id": ORG_UUID},
            )
        assert response.status_code == 401

    def test_set_active_organization_not_found_and_invalid(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 for unknown org and 400 for invalid payload.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert (
            auth_client.patch(
                f"{USERS_URL}/set-active-organization",
                json={"org_id": str(uuid4())},
            ).status_code
            == 404
        )
        assert (
            auth_client.patch(
                f"{USERS_URL}/set-active-organization", json={}
            ).status_code
            == 400
        )

    def test_set_active_organization_none_returns_404(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 when base.get returns None for organization lookup.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        with patch.object(base, "get", return_value=None):
            res = auth_client.patch(
                f"{USERS_URL}/set-active-organization",
                json={"org_id": ORG_UUID},
            )
        assert res.status_code == 404

    # -------------------------------------------------------------------------
    # 5. GET All Users in Active Organization
    # -------------------------------------------------------------------------

    def test_get_all_users_no_active_org(self, auth_client: FlaskClient) -> None:
        """Verify 400 response when no active organization is set in session.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        with auth_client.session_transaction() as sess:
            sess.pop("active_org_uuid", None)

        response = auth_client.get(USERS_URL)
        assert response.status_code == 400

    def test_get_all_users_with_mocked_where(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify GET /users serializes results when active_org_uuid is set.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        with auth_client.session_transaction() as sess:
            sess["active_org_uuid"] = ORG_UUID

        stub_user = _make_stub_user()
        with patch.object(base, "where", return_value=[stub_user]) as mock_where:
            response = auth_client.get(USERS_URL)

        assert response.status_code == 200
        mock_where.assert_called_once_with(User, {"organization_id": UUID(ORG_UUID)})
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        User.Response.model_validate(data[0])

    # -------------------------------------------------------------------------
    # 6. POST Create User & Super User
    # -------------------------------------------------------------------------

    def test_create_user_success_with_mocked_insert(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify POST /users validates input and serializes created user with 201.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        stub_user = _make_stub_user(username="NewUser", email="new@local.host")
        with patch.object(base, "insert", return_value=stub_user) as mock_insert:
            response = auth_client.post(
                USERS_URL,
                json={
                    "username": "NewUser",
                    "email": "new@local.host",
                    "password": "StrongPassword123!",
                },
            )

        assert response.status_code == 201
        mock_insert.assert_called_once()
        validated = User.Response.model_validate(response.get_json())
        assert validated.username == "NewUser"
        assert validated.email == "new@local.host"

    def test_create_user_invalid(self, auth_client: FlaskClient) -> None:
        """Verify 400 on invalid user creation payload.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.post(USERS_URL, json={}).status_code == 400

    def test_create_super_user_when_bootstrapped(self, client: FlaskClient) -> None:
        """Verify 401 response when creating super-user after bootstrap is complete.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.post(
            f"{USERS_URL}/super-user",
            json={
                "username": "RootAdmin",
                "email": "root@local.host",
                "password": "RootPassword123!",
            },
        )
        assert response.status_code == 401

    def test_create_super_user_missing_root_role_returns_500(
        self, client: FlaskClient
    ) -> None:
        """Verify 500 response when unbootstrapped DB lacks root role.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """

        def _set_unbootstrapped(cursor, _db) -> None:
            cursor.execute(
                "UPDATE usermanagement.initialization SET first_run = true;"
            )

        base.execute(_set_unbootstrapped)

        response = client.post(
            f"{USERS_URL}/super-user",
            json={
                "username": "RootAdmin",
                "email": "root@local.host",
                "password": "RootPassword123!",
            },
        )
        assert response.status_code == 500

    def test_create_super_user_missing_root_org_returns_500(
        self, client: FlaskClient
    ) -> None:
        """Verify 500 response when unbootstrapped DB lacks Root organization.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        now = datetime.now(UTC)
        root_role = Role(
            role_id=99, name="root", created=now, modified=now, uuid=uuid4()
        )
        with (
            patch.object(base, "check_bootstrapped", return_value=False),
            patch.object(base, "where", side_effect=[[root_role], []]),
        ):
            response = client.post(
                f"{USERS_URL}/super-user",
                json={
                    "username": "RootAdmin",
                    "email": "root@local.host",
                    "password": "RootPassword123!",
                },
            )
        assert response.status_code == 500

    def test_create_super_user_success_with_mocked_insert(
        self, client: FlaskClient
    ) -> None:
        """Verify super-user bootstrap creates user, writes SpiceDB, and logs in.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        now = datetime.now(UTC)
        root_role = Role(
            role_id=99, name="root", created=now, modified=now, uuid=uuid4()
        )
        root_org = Organization(
            organization_id=99, name="Root", created=now, modified=now, uuid=uuid4()
        )
        stub_super = _make_stub_user(
            username="RootAdmin", email="root@local.host"
        )

        with (
            patch.object(base, "check_bootstrapped", return_value=False),
            patch.object(
                base, "where", side_effect=[[root_role], [root_org]]
            ),
            patch.object(base, "insert", return_value=stub_super),
            patch.object(base, "write_spice_relationships"),
        ):
            response = client.post(
                f"{USERS_URL}/super-user",
                json={
                    "username": "RootAdmin",
                    "email": "root@local.host",
                    "password": "RootPassword123!",
                },
            )

        assert response.status_code == 200
        validated = User.Response.model_validate(response.get_json())
        assert validated.username == "RootAdmin"
