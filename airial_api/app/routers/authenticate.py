# Endpoints for integrating oauth2.0
# Special thanks to Miguel Grinberg for the excellent guide
# https://blog.miguelgrinberg.com/post/oauth-authentication-with-flask-in-2023
# Author: Michael B. Lance

"""Endpoints for integrating OAuth2 and legacy password authentication."""

# ---------------------------------------------------------------------------------------------------------------------------#

import secrets
from datetime import UTC, datetime
from urllib.parse import urlencode

import requests
from flask import Blueprint, abort, current_app, redirect, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_pydantic import validate
from werkzeug.security import check_password_hash

from app.extensions import base
from database import AuthenticationFailure
from database.object_models.core import Image, UpdateImageReq
from database.object_models.user_management import (
    LegacyAuthReq,
    Organization,
    UpdateUserReq,
    User,
)

authBp = Blueprint("oauth2", __name__, url_prefix="/api/v1/")

# ---------------------------------------------------------------------------------------------------------------------------#
# Authorization


@authBp.get("/authorize/<string:provider>")
def oauth2_authorize(provider: str):
    """Initiate OAuth2 authorization redirect."""
    provider_data = current_app.config["OAUTH2_PROVIDERS"].get(provider)
    if not provider_data:
        abort(404, "Oauth Provider not found")

    session["oauth2_state"] = secrets.token_urlsafe(16)
    session.modified = True

    query_string = urlencode(
        {
            "client_id": provider_data["client_id"],
            "redirect_uri": url_for(".oauth2_callback", provider=provider, _external=True),
            "response_type": "code",
            "scope": " ".join(provider_data["scopes"]),
            "state": session["oauth2_state"],
        }
    )

    return redirect(provider_data["authorize_url"] + "?" + query_string)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@authBp.get("/callback/<string:provider>")
def oauth2_callback(provider: str):
    """OAuth2 callback handler."""
    provider_data = current_app.config["OAUTH2_PROVIDERS"].get(provider)
    if not provider_data:
        abort(404, "Oauth Provider not found")

    if "error" in request.args:
        for key, value in request.args.items():
            if key.startswith("error"):
                current_app.logger.info(f"key: {key}, value: {value}")
                abort(500)

    if request.args["state"] != session.get("oauth2_state"):
        abort(401)

    if "code" not in request.args:
        abort(401)

    response = requests.post(
        provider_data["token_url"],
        data={
            "client_id": provider_data["client_id"],
            "client_secret": provider_data["client_secret"],
            "code": request.args["code"],
            "grant_type": "authorization_code",
            "redirect_uri": url_for(".oauth2_callback", provider=provider, _external=True),
        },
        headers={"Accept": "application/json"},
    )

    if response.status_code != 200:
        abort(401)

    oauth2_token = response.json().get("access_token")
    if not oauth2_token:
        abort(401)

    response = requests.get(
        provider_data["userinfo"]["url"],
        headers={
            "Authorization": "Bearer " + oauth2_token,
            "Accept": "application/json",
        },
    )
    if response.status_code != 200:
        abort(401)

    email = provider_data["userinfo"]["email"](response.json())
    users = base.where(User, {"email": email})
    if not users:
        abort(404, "User not found.")

    user = users[0]

    if user.status == "invited":
        base.update(
            User,
            user.user_id,
            UpdateUserReq(
                status="active",
                external_auth_provider=provider,
                external_auth_id=response.json().get("sub"),
                last_login=datetime.now(UTC),
            ),
        )
    else:
        base.update(User, user.user_id, UpdateUserReq(last_login=datetime.now(UTC)))

    login_user(user)

    default_org = base.get(Organization, user.default_org_id)
    if default_org:
        session["active_org_uuid"] = str(default_org.uuid)
        session[f"org_{default_org.uuid}"] = default_org.to_cache()

    frontend_url = current_app.config.get("ORIGIN_URL")
    return redirect(f"{frontend_url}/")


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@authBp.post("/authenticate")
@validate()
def authenticate(body: LegacyAuthReq):
    """Basic email/password authentication."""
    users = base.where(User, {"email": body.email})
    if not users:
        raise AuthenticationFailure()

    user = users[0]
    if not user.password_hash:
        abort(400, "User account is not configured for password authentication.")

    if check_password_hash(user.password_hash, body.password):
        base.update(User, user.user_id, UpdateUserReq(last_login=datetime.now(UTC)))
    else:
        raise AuthenticationFailure()

    login_user(user)

    default_org = base.get(Organization, pk=user.default_org_id)
    if default_org:
        session["active_org_uuid"] = str(default_org.uuid)
        session[f"org_{default_org.uuid}"] = default_org.to_cache()

    return "", 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@authBp.post("/deauthenticate")
@login_required
def logout():
    """Logout current user session and release any locked images."""
    base.bulk_update(
        Image,
        UpdateImageReq(opened_by_user_id=0),
        {"opened_by_user_id": current_user.user_id},
    )
    logout_user()
    return "", 200
