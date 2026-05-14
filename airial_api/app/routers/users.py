# Endpoints for managing Users in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID

from app.decorators import permission_required
from database.object_models.user_management import (
    User,
    RoleNameQuery,
    CreateUserReq,
    SetActiveOrgReq,
    UserQuery,
)
from flask import Blueprint, abort, current_app, session
from flask_login import current_user, login_required, login_user
from flask_pydantic import validate
from msgpack import unpackb
from psycopg.errors import DatabaseError, UniqueViolation

from app.extensions import base, cache, login_manager
from database import UserNotFound

from authzed.api.v1 import CheckPermissionResponse

userBp = Blueprint("users", __name__, url_prefix="/api/v1/users")

# ---------------------------------------------------------------------------------------------------------------------------


@login_manager.user_loader
def load(session_user_id: str):
    user_key = f"user_{session_user_id}"
    cached_user = cache.get(user_key)

    if cached_user:
        user = User(**unpackb(cached_user))
        return user
    try:
        user_obj = base.get_user(UUID(session_user_id))

        if "active_org_uuid" in session:
            org_id = UUID(session.get("active_org_uuid"))
        else:
            org_id = user_obj.default_org_id

        user_obj.roles = [
            role.name for role in base.get_user_roles(user_obj.user_id, org_id)
        ]

        cache.set(user_key, user_obj.to_cache(), timeout=3600)
    except UserNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return user_obj


@login_manager.unauthorized_handler
def unathorizated_callback():
    abort(401, "You are not authorized to access this resource.")


# ---------------------------------------------------------------------------------------------------------------------------
# GET


@userBp.get("")
@login_required
@permission_required("access")
def get_all():
    """ """
    try:
        query = UserQuery(organization_id=session["active_org_uuid"])

        users = base.get_users(query)
    except (DatabaseError, Exception) as e:
        print(e)
        abort(500)

    return [user.to_dict() for user in users], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@userBp.get("/check-auth")
@login_required
def check_auth():
    return "true", 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@userBp.get("/current-user")
@login_required
def get_current_user():
    """ """
    return current_user.to_dict(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@userBp.get("/<string:user_id>/organizations")
@login_required
def get_orgs(user_id: str):
    """ """
    try:
        orgs = base.get_user_organizations(UUID(user_id))
    except (DatabaseError, Exception) as e:
        print(e)
        abort(500)

    return [org.to_dict() for org in orgs]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@userBp.get("/role-check")
@login_required
@validate()
def check_role(query: RoleNameQuery):
    """ """

    if current_user.roles and query.role_name in current_user.roles:
        return "true", 200
    else:
        return "false", 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@userBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateUserReq):
    """ """
    try:
        user = base.create_user(body)
    except UniqueViolation:
        abort(409, "User already exists")
    except (DatabaseError, Exception) as e:
        print(e)
        abort(500)

    return user.to_dict(), 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@userBp.post("/super-user")
@permission_required("access")
@validate()
def create_super(body: CreateUserReq):
    """ """
    try:
        # Disable this endpoint if databae is initialized
        bootstrapped = base.check_bootstrapped()
        if bootstrapped:
            abort(401)

        role = base.get_role("root")
        body.role_ids = [role.uuid]

        org = base.get_organization("Root")
        body.organization_id = org.uuid

        user = base.create_user(body)

        base.write_spice_relationships(
            [base.create_spice_update("platform", "airial", "user", user.id, "root")]
        )

    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    login_user(user)
    return user.to_dict(), 200


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@userBp.patch("/set-active-organization")
@login_required
@permission_required("access")
@validate()
def set_org(body: SetActiveOrgReq):
    """ """
    organization = base.get_organization(body.org_id)

    res = base.check_permission(
        "organization", str(organization.uuid), str(current_user.uuid), "access"
    )

    if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:

        session["active_org_uuid"] = organization.uuid

        # Flush the user from the cache to force admin status to update
        user_key = f"user_{str(current_user.uuid)}"
        cache.delete(user_key)

        # Cache the new organization in the session
        session[f"org_{organization.uuid}"] = organization.to_cache()

        return "", 200

    else:
        abort(401)
