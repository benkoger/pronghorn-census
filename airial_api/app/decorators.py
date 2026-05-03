from functools import wraps
from typing import cast
from flask import abort, current_app
from flask_login import current_user
from app.extensions import base
from database.errors import AuthorizationFailure, ObjectNotFound
from database.object_models.user_management.users import User
from authzed.api.v1 import CheckPermissionResponse
from pydantic import BaseModel

getters = {
    "image": base.get_image,
    "label": base.get_label,
    "herd_unit": base.get_herd_unit,
    "org": base.get_organization,
    "organization": base.get_organization,
}


def roles_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return abort(401)

            if not any(current_user.has_role(r) for r in roles):
                return abort(403)

            return f(*args, **kwargs)

        return decorated_view

    return wrapper


def permission_required(permission: str):
    def wrapper(f):
        @wraps(f)
        def decorated_view(*args, **kwargs):
            user = cast(User, current_user)
            check_items = []
            targets = []

            req_body = next((arg for arg in args if isinstance(arg, BaseModel)), None)
            if not req_body:
                req_body = next(
                    (v for v in kwargs.values() if isinstance(v, BaseModel)), None
                )

            resources = req_body.model_dump() if req_body else {}
            resources.update(kwargs)

            for field_name, value in resources.items():
                if field_name.endswith("_id") and value is not None:
                    obj_type = field_name.rsplit("_id", 1)[0]

                    if isinstance(value, int):
                        try:
                            obj_id = str(getters[obj_type](value))
                        except (ObjectNotFound, KeyError) as e:
                            current_app.logger.exception(e)
                            abort(404, str(e))
                    else:
                        obj_id = str(value)

                    item = base.create_bulk_check_request(
                        object_type=obj_type,
                        object_id=obj_id,
                        subject_id=user.id,
                        permission=permission,
                    )
                    check_items.append(item)
                    targets.append((obj_type, obj_id))

            if check_items:
                bulk_res = base.bulk_check_permission(check_items)

                for i, pair in enumerate(bulk_res.pairs):
                    if (
                        pair.item.permissionship
                        != CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
                    ):
                        obj_type, obj_id = targets[i]
                        raise AuthorizationFailure(
                            user.id, permission, obj_type, obj_id
                        )

            return f(*args, **kwargs)

        return decorated_view

    return wrapper
