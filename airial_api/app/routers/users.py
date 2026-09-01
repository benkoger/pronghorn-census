# Endpoints for managing Users in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID, uuid4

from flask import Blueprint, abort, session
from flask_login import current_user, login_required, login_user
from flask_pydantic import validate
from msgpack import unpackb

from app.decorators import permission_required
from app.extensions import base, cache, login_manager
from authzed.api.v1 import CheckPermissionResponse
from database.object_models.user_management import (
    CreateUserReq,
    Organization,
    Role,
    RoleNameQuery,
    SetActiveOrgReq,
    User,
)

from database.object_models.base import create_spice_update
from database.object_models.user_management.organization_users import OrganizationUser

userBp = Blueprint("users", __name__, url_prefix="/api/v1/users")

# ---------------------------------------------------------------------------------------------------------------------------


@login_manager.user_loader
def load(session_user_id: str):
    user_key = f"user_{session_user_id}"
    cached_user = cache.get(user_key)

    if cached_user:
        return User(**unpackb(cached_user))

    user_obj = base.get(User, pk=UUID(session_user_id))
    if not user_obj:
        return None

    if "active_org_uuid" in session:
        org_id = UUID(session.get("active_org_uuid"))
    else:
        org_id = user_obj.default_org_id

    org = base.get(Organization, org_id)

    # Retrieve active user roles
    user_roles = base.get_related(
        OrganizationUser,
        Role,
        {"user_id": user_obj.user_id, "organization_id": org.organization_id},
        fk_field="role_id",
    )

    user_obj.roles = [role.name for role in user_roles]

    cache.set(user_key, user_obj.to_cache(), timeout=3600)

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
    """Retrieve all users under the active organization"""
    active_org = session.get("active_org_uuid")

    if not active_org:
        abort(400, "No active organization selected.")

    users = base.where(User, {"organization_id": UUID(active_org)})

    return [user.serialize() for user in users], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@userBp.get("/check-auth")
def check_auth():
    if current_user.is_authenticated:
        return "true", 200
    else:
        return "false", 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@userBp.get("/current-user")
@login_required
def get_current_user():
    return current_user.serialize(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@userBp.get("/<uuid:user_id>/organizations")
@userBp.get("/<string:user_id>/organizations")
@login_required
def get_orgs(user_id: int | UUID):
    """Retrieve organizations linked to a specific user"""
    # slower because we have to look up the pk for the fkey relation
    if isinstance(user_id, UUID):
        user = base.get(User, user_id)

        user_id = user.user_id

    orgs = base.where(Organization, {"user_id": user_id})
    return [org.serialize() for org in orgs], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@userBp.get("/role-check")
@login_required
@validate()
def check_role(query: RoleNameQuery):
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
    """Create a standard user using _insert"""
    user = base.insert(User, body)
    return user.serialize(), 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@userBp.post("/super-user")
@permission_required("access")
@validate()
def create_super(body: CreateUserReq):
    """Bootstrap root super user"""
    bootstrapped = base.check_bootstrapped()
    if bootstrapped:
        abort(401, "Database already bootstrapped.")

    roles = base.where(Role, {"name": "root"})
    if not roles:
        abort(500, "Root role missing.")
    body.role_ids = [roles[0].uuid]

    orgs = base.where(Organization, {"name": "Root"})
    if not orgs:
        abort(500, "Root organization missing.")
    body.organization_id = orgs[0].uuid

    user = base.insert(User, body)

    base.write_spice_relationships(
        [create_spice_update("platform", uuid4(), "user", user.uuid, "root")]
    )

    login_user(user)
    return user.serialize(), 200


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@userBp.patch("/set-active-organization")
@login_required
@permission_required("access")
@validate()
def set_org(body: SetActiveOrgReq):
    """Set active organization context in session"""
    organization = base.get(Organization, pk=body.org_id)
    if not organization:
        abort(404, "Organization not found.")

    res = base.check_permission(
        "organization", str(organization.uuid), str(current_user.uuid), "access"
    )

    if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
        session["active_org_uuid"] = str(organization.uuid)

        user_key = f"user_{str(current_user.uuid)}"
        cache.delete(user_key)

        session[f"org_{organization.uuid}"] = organization.to_cache()

        return "", 200
    else:
        abort(401)
