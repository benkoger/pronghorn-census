"""Route authorization decorators for SpiceDB permissions and role checking."""

from functools import wraps
from typing import cast

from authzed.api.v1 import CheckPermissionResponse, Consistency
from flask import abort, current_app
from flask_login import current_user
from pydantic import BaseModel

from app.extensions import base
from database.errors import AuthorizationFailure, ObjectNotFound
from database.object_models.core.image_footprints import ImageFootprint
from database.object_models.core.image_metadata import ImageMetadata
from database.object_models.core.images import Image
from database.object_models.project_management import HerdUnit
from database.object_models.project_management.labels import Label
from database.object_models.user_management.organizations import Organization
from database.object_models.user_management.users import User

# Model map replacing obsolete base methods
MODEL_MAP = {
    "image": Image,
    "image_metadata": ImageMetadata,
    "image_footprint": ImageFootprint,
    "image_footprints": ImageFootprint,
    "label": Label,
    "herd_unit": HerdUnit,
    "org": Organization,
    "organization": Organization,
}

check_exist = {
    "image": lambda val: base._exists(Image, val),
    "image_metadata": lambda val: base._exists(ImageMetadata, val),
    "image_footprint": lambda val: base._exists(ImageFootprint, val),
    "image_footprints": lambda val: base._exists(ImageFootprint, val),
    "label": lambda val: base._exists(Label, val),
    "herd_unit": lambda val: base._exists(HerdUnit, val),
    "org": lambda val: base._exists(Organization, val),
    "organization": lambda val: base._exists(Organization, val),
}


def roles_required(*roles):
    """Ensure current user has at least one of the specified roles."""

    def wrapper(f):
        @wraps(f)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return abort(401)

            if not any(current_user.hasRole(r) for r in roles):
                return abort(403)

            return f(*args, **kwargs)

        return decorated_view

    return wrapper


def permission_required(permission: str):
    """Enforce SpiceDB permission check on targets extracted from request arguments or body."""

    def wrapper(f):
        @wraps(f)
        def decorated_view(*args, **kwargs):
            user = cast(User, current_user)
            check_items = []
            targets = []

            req_body = next((arg for arg in args if isinstance(arg, BaseModel)), None)
            if not req_body:
                req_body = next((v for v in kwargs.values() if isinstance(v, BaseModel)), None)

            resources = req_body.model_dump() if req_body else {}
            resources.update(kwargs)

            def extract_and_queue_checks(data_dict: dict):
                for field_name, value in data_dict.items():
                    if field_name.endswith("_id") and value is not None:
                        obj_type = field_name.rsplit("_id", 1)[0]

                        if obj_type not in check_exist:
                            continue

                        exists = check_exist[obj_type](value)
                        if not exists:
                            abort(404, f"{obj_type} with id of {value} does not exist!")

                        if isinstance(value, int):
                            try:
                                model_cls = MODEL_MAP[obj_type]
                                db_obj = base._get(model_cls, value)
                                if not db_obj:
                                    abort(404, f"{obj_type} with id of {value} not found.")
                                obj_id = str(getattr(db_obj, "uuid", db_obj))
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

            nested_requests = resources.get("requests")

            if nested_requests and isinstance(nested_requests, list):
                root_ids = {k: v for k, v in resources.items() if k != "requests"}
                extract_and_queue_checks(root_ids)

                for req in nested_requests:
                    req_data = req.model_dump() if isinstance(req, BaseModel) else req
                    if isinstance(req_data, dict):
                        extract_and_queue_checks(req_data)
            else:
                extract_and_queue_checks(resources)

            if check_items:
                consistency = Consistency(fully_consistent=True)
                bulk_res = base.bulk_check_permission(check_items, consistency=consistency)

                for i, pair in enumerate(bulk_res.pairs):
                    if pair.item.permissionship != CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
                        obj_type, obj_id = targets[i]
                        e = AuthorizationFailure(user.id, permission, obj_type, obj_id)
                        abort(401, str(e))

            return f(*args, **kwargs)

        return decorated_view

    return wrapper
