# Endpoints for managing models in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------#

from datetime import datetime

from uuid import UUID

from flask import Blueprint, request
from flask_login import login_required, current_user
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base
from typing import cast

from database.object_models.project_management import CreateModelReq
from database.object_models.project_management.models import UpdateModelReq
from database.object_models.user_management import User

modelBp = Blueprint("models", __name__, url_prefix="/api/v1/models")

# TODO: These endpoints require propper organizational and project checking

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@modelBp.get("/<string:model_id>")
@login_required
@permission_required("access")
def get_by_id(model_id: str):
    """ """
    return base.get_model(UUID(model_id)).to_dict(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.get("/<string:model_id>/json")
@login_required
@permission_required("access")
def get_json_all():
    """ """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.get("/<string:model_id>/json/train")
@login_required
@permission_required("accesss")
def get_json_train():
    """ """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.get("/<string:model_id>/json/val")
@login_required
@permission_required("acess")
def get_json_test():
    """ """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.get("/<string:model_id>/weights")
@login_required
@permission_required("access")
def get_weights():
    """ """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.get("/<string:model_id>/config")
@login_required
@permission_required("access")
def get_config():
    """ """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.get("/<string:model_id>/readme")
@login_required
@permission_required("acess")
def get_readme():
    """ """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.get("/<string:model_id>/schema")
@login_required
@permission_required("access")
def get_schema(model_id: str):
    """
    Retrieve the schema for a specific model
    ---
    responses:
      200:
            description: The model's schema.
      404:
            description: No model / schema found.
      500:
            description: Database error.
    """

    return (
        base.get_model_schema(UUID(model_id), cast(User, current_user)).to_dict(),
        200,
    )


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.get("/training")
@login_required
@permission_required("access")
def get_training_set():
    """ """
    date_range = request.args.get("date_range", None)
    surveys = request.args.getlist("survey", type=int)
    labels = request.args.getlist("labels", type=int)
    herd_units = request.args.getlist("herd_unit", type=int)
    format_pattern = "%m/%d/%Y %H:%M:%S"

    if date_range is not None:
        date_range = (
            datetime.strptime(date_range[0], format_pattern),
            datetime.strptime(date_range[1], format_pattern),
        )

    return base.get_model_training_data(labels, date_range, surveys, herd_units), 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@modelBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateModelReq):
    """ """
    return base.create_model(body).to_dict(), 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.post("/<string:model_id>/train")
@login_required
@permission_required("access")
def create_train_json(model_id: str):
    """ """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.post("/<string:model_id>/val")
@login_required
@permission_required("access")
def create_val_json(mdoel_id: str):
    """ """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.post("/<string:model_id>/weights")
@login_required
@permission_required("access")
def create_weights(mdoel_id: str):
    """ """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.post("/<string:model_id>/config")
@login_required
def create_config(model_id: str):
    """ """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@modelBp.post("/<string:model_id>/readme")
@login_required
@permission_required("access")
def create_readme(model_id: str):
    """ """
    return ""


# ---------------------------------------------------------------------------------------------------------------------------
# PUT


@modelBp.put("/<string:model_id>")
@login_required
@permission_required("access")
def replace(model_id: str):
    """ """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.put("/<string:model_id>/train")
@login_required
@permission_required("access")
def replace_train_json(model_id: str):
    """Replace the train.json file to s3 under the model's base key"""
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.put("/<string:model_id>/val")
@login_required
@permission_required("acess")
def replace_val_json(model_id: str):
    """Replace val.json file to s3 under the model's base key"""
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.post("/<string:model_id>/weights")
@login_required
@permission_required("acess")
def replace_weights(mdoel_id: str):
    """ """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.post("/<string:model_id>/config")
@login_required
@permission_required("access")
def replace_config(mdoel_id: str):
    """ """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.post("/<string:model_id>/readme")
@login_required
@permission_required("access")
def replace_readme(model_id: str):
    """ """
    return ""


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH (since json files are stored on s3 they are not patchable in the same way a database object is)


@modelBp.patch("/<string:model_id>")
@login_required
@permission_required("access")
@validate()
def update(body: UpdateModelReq, model_id: str):
    """ """

    return base.update_model(UUID(model_id), body).to_dict(), 200


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@modelBp.delete("/<string:model_id>")
@login_required
@permission_required("access")
def delete_model(model_id: str):
    """ """

    base.delete_model(UUID(model_id))

    return "", 204
