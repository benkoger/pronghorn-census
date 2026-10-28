# Endpoints for managing models in the API
# Author: Michael B. Lance

"""Endpoints for managing models and their artifacts in the API."""

# ---------------------------------------------------------------------------------------------------------------------------#
from uuid import UUID

from flask import Blueprint
from flask_login import login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base
from database.object_models.project_management import CreateModelReq
from database.object_models.project_management.models import Model, UpdateModelReq
from database.object_models.project_management.schemas import Schema

modelBp = Blueprint("models", __name__, url_prefix="/api/v1/models")

# TODO: These endpoints require propper organizational and project checking

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@modelBp.get("/<int:model_id>")
@modelBp.get("/<uuid:model_id>")
@login_required
@permission_required("access")
def get_by_id(model_id: int | UUID):
    """Request a model object from the database using its integer PK or UUID.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the model (integer ID or UUID).
    responses:
      200:
        description: The requested model was found.
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this model.
      404:
        description: No model record found for the provided ID.
      500:
        description: Database error.
    """
    return base.get(Model, model_id).serialize(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.get("/<string:model_id>/json")
@login_required
@permission_required("access")
def get_json_all():
    """Retrieve all dataset JSON configurations for a specific model from S3.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        type: string
        description: Model identifier or UUID.
    responses:
      200:
        description: Dataset JSON retrieved successfully.
      401:
        description: User not authorized.
      404:
        description: Model or dataset files not found.
      500:
        description: Storage or server error.
    """
    return "", 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.get("/<string:model_id>/json/train")
@login_required
@permission_required("access")
def get_json_train():
    """Retrieve train dataset JSON for a specific model from S3.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        type: string
        description: Model identifier or UUID.
    responses:
      200:
        description: Training dataset JSON retrieved.
      401:
        description: User not authorized.
      404:
        description: Training dataset not found.
      500:
        description: Storage error.
    """
    return "", 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.get("/<string:model_id>/json/val")
@login_required
@permission_required("access")
def get_json_test():
    """Retrieve validation dataset JSON for a specific model from S3.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        type: string
        description: Model identifier or UUID.
    responses:
      200:
        description: Validation dataset JSON retrieved.
      401:
        description: User not authorized.
      404:
        description: Validation dataset not found.
      500:
        description: Storage error.
    """
    return "", 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.get("/<string:model_id>/weights")
@login_required
@permission_required("access")
def get_weights():
    """Retrieve weights artifact file for a specific model from S3.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        type: string
        description: Model identifier or UUID.
    responses:
      200:
        description: Model weights retrieved.
      401:
        description: User not authorized.
      404:
        description: Weights artifact not found.
      500:
        description: Storage error.
    """
    return "", 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.get("/<string:model_id>/config")
@login_required
@permission_required("access")
def get_config():
    """Retrieve architecture configuration file for a specific model from S3.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        type: string
        description: Model identifier or UUID.
    responses:
      200:
        description: Model configuration file retrieved.
      401:
        description: User not authorized.
      404:
        description: Configuration file not found.
      500:
        description: Storage error.
    """
    return "", 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.get("/<string:model_id>/readme")
@login_required
@permission_required("access")
def get_readme():
    """Retrieve documentation/readme artifact for a specific model from S3.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        type: string
        description: Model identifier or UUID.
    responses:
      200:
        description: Readme file retrieved.
      401:
        description: User not authorized.
      404:
        description: Readme file not found.
      500:
        description: Storage error.
    """
    return "", 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.get("/<int:model_id>/schema")
@modelBp.get("/<uuid:model_id>/schema")
@login_required
@permission_required("access")
def get_schema(model_id: int | UUID):
    """Retrieve the label schema definition associated with a specific model.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the model.
    responses:
      200:
        description: The model's schema was found and returned.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized.
      404:
        description: No model or schema found.
      500:
        description: Database error.
    """
    model = base.get(Model, model_id)

    return base.get(Schema, model.schema_id).serialize(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# TODO: Rework
# @modelBp.get("/training")
# @login_required
# @permission_required("access")
# def get_training_set():
#     """ """
#     date_range = request.args.get("date_range", None)
#     surveys = request.args.getlist("survey", type=int)
#     labels = request.args.getlist("labels", type=int)
#     herd_units = request.args.getlist("herd_unit", type=int)
#     format_pattern = "%m/%d/%Y %H:%M:%S"
#
#     if date_range is not None:
#         date_range = (
#             datetime.strptime(date_range[0], format_pattern),
#             datetime.strptime(date_range[1], format_pattern),
#         )
#
#     return base.get_model_training_data(labels, date_range, surveys, herd_units), 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@modelBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateModelReq):
    """Create a new model record in the database.

    ---
    parameters:
      - name: body
        in: body
        required: true
        type: CreateModelReq
        description: Model creation payload including name, project_ids, and schema_ids.
    responses:
      201:
        description: Model created successfully.
      400:
        description: Validation error or invalid payload.
      401:
        description: User not authorized to create models.
      409:
        description: Conflict or unique constraint violation.
      500:
        description: Database error.
    """
    return base.insert(Model, body).serialize(), 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.post("/<string:model_id>/train")
@login_required
@permission_required("access")
def create_train_json(model_id: str):
    """Upload or initialize training dataset JSON on S3 for a model.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        type: string
        description: Model identifier.
    responses:
      200:
        description: Training JSON created.
      401:
        description: User not authorized.
      500:
        description: Storage error.
    """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.post("/<string:model_id>/val")
@login_required
@permission_required("access")
def create_val_json(mdoel_id: str):
    """Upload or initialize validation dataset JSON on S3 for a model.

    ---
    parameters:
      - name: mdoel_id
        in: path
        required: true
        type: string
        description: Model identifier.
    responses:
      200:
        description: Validation JSON created.
      401:
        description: User not authorized.
      500:
        description: Storage error.
    """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.post("/<string:model_id>/weights")
@login_required
@permission_required("access")
def create_weights(mdoel_id: str):
    """Upload model weights file to S3.

    ---
    parameters:
      - name: mdoel_id
        in: path
        required: true
        type: string
        description: Model identifier.
    responses:
      200:
        description: Weights uploaded.
      401:
        description: User not authorized.
      500:
        description: Storage error.
    """
    return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.post("/<string:model_id>/config")
@login_required
def create_config(model_id: str):
    """Upload model architecture config to S3.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        type: string
        description: Model identifier.
    responses:
      200:
        description: Config uploaded.
      401:
        description: User not authenticated.
      500:
        description: Storage error.
    """
    return "", 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@modelBp.post("/<string:model_id>/readme")
@login_required
@permission_required("access")
def create_readme(model_id: str):
    """Upload documentation/readme for a model to S3.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        type: string
        description: Model identifier.
    responses:
      200:
        description: Readme uploaded.
      401:
        description: User not authorized.
      500:
        description: Storage error.
    """
    return "", 200


# ---------------------------------------------------------------------------------------------------------------------------
# PUT


@modelBp.put("/<string:model_id>")
@login_required
@permission_required("access")
def replace(model_id: str):
    """Replace complete model artifacts and definition.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        type: string
        description: Model identifier.
    responses:
      200:
        description: Model replaced successfully.
      401:
        description: User not authorized.
      500:
        description: Server error.
    """
    return "", 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.put("/<string:model_id>/train")
@login_required
@permission_required("access")
def replace_train_json(model_id: str):
    """Replace the train.json file on S3 under the model's base key.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        type: string
        description: Model identifier.
    responses:
      200:
        description: Training JSON replaced.
      401:
        description: User not authorized.
      500:
        description: Storage error.
    """
    return "", 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.put("/<string:model_id>/val")
@login_required
@permission_required("access")
def replace_val_json(model_id: str):
    """Replace the val.json file on S3 under the model's base key.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        type: string
        description: Model identifier.
    responses:
      200:
        description: Validation JSON replaced.
      401:
        description: User not authorized.
      500:
        description: Storage error.
    """
    return "", 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.post("/<string:model_id>/weights")
@login_required
@permission_required("access")
def replace_weights(mdoel_id: str):
    """Replace weights artifact on S3.

    ---
    parameters:
      - name: mdoel_id
        in: path
        required: true
        type: string
        description: Model identifier.
    responses:
      200:
        description: Weights replaced.
      401:
        description: User not authorized.
      500:
        description: Storage error.
    """
    return "", 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.post("/<string:model_id>/config")
@login_required
@permission_required("access")
def replace_config(mdoel_id: str):
    """Replace configuration artifact on S3.

    ---
    parameters:
      - name: mdoel_id
        in: path
        required: true
        type: string
        description: Model identifier.
    responses:
      200:
        description: Config replaced.
      401:
        description: User not authorized.
      500:
        description: Storage error.
    """
    return "", 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@modelBp.post("/<string:model_id>/readme")
@login_required
@permission_required("access")
def replace_readme(model_id: str):
    """Replace documentation/readme artifact on S3.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        type: string
        description: Model identifier.
    responses:
      200:
        description: Readme replaced.
      401:
        description: User not authorized.
      500:
        description: Storage error.
    """
    return "", 200


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH (since json files are stored on s3 they are not patchable in the same way a database object is)


@modelBp.patch("/<int:model_id>")
@modelBp.patch("/<uuid:model_id>")
@login_required
@permission_required("access")
@validate()
def update(body: UpdateModelReq, model_id: int | UUID):
    """Update model metadata in the database.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the model to update.
      - name: body
        in: body
        required: true
        type: UpdateModelReq
        description: Model update payload containing updated name.
    responses:
      200:
        description: Model updated successfully.
      400:
        description: Validation error or invalid ID format.
      401:
        description: User not authorized to update this model.
      404:
        description: Model not found.
      500:
        description: Database error.
    """
    return base.update(Model, model_id, body).serialize(), 200


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@modelBp.delete("/<int:model_id>")
@modelBp.delete("/<uuid:model_id>")
@login_required
@permission_required("access")
def delete_model(model_id: int | UUID):
    """Delete a model by its integer ID or UUID.

    ---
    parameters:
      - name: model_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the model to delete.
    responses:
      204:
        description: Model deleted successfully.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized to delete this model.
      404:
        description: Model not found.
      500:
        description: Database error.
    """
    base.delete(Model, model_id)

    return "", 204
