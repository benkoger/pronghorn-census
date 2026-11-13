"""Endpoints for the automated crop generator utility."""

import io
from typing import cast

from crop_generator import auto_crop
from database.object_models import (
    AutoCropperBatchQuery,
    AutoCropReq,
)
from database.object_models.base import BulkRequest, Keyring
from database.object_models.core import UpdateImageReq
from database.object_models.core.annotations import Annotation
from database.object_models.core.images import Image, ReviewedArea
from database.object_models.core.predictions import Prediction, UpdatePredictionReq
from database.object_models.project_management.herd_units import HerdUnit
from database.object_models.project_management.labels import Label
from database.object_models.user_management import User
from flask import Blueprint, current_app
from flask_login import current_user, login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base, cache, s3

cropBp = Blueprint("autocropper", __name__, url_prefix="/api/v1/autocropper")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@cropBp.get("/batch")
@login_required
@permission_required("access")
@validate()
def fetch_batch(query: AutoCropperBatchQuery):
    """Fetch a candidate batch of images and predictions for auto-cropping.

    Args:
        query: Query parameters specifying survey, herd unit, model, labels, and batch size.

    Returns:
        Tuple containing list of batch image and prediction payloads and HTTP status 200.

    ---
    parameters:
      - name: survey_id
        in: query
        required: false
        type: array
        items:
          type: string
          format: uuid
        description: Survey ID filter.
      - name: herd_unit_id
        in: query
        required: false
        type: array
        items:
          type: string
          format: uuid
        description: Herd unit ID filter.
      - name: model_id
        in: query
        required: false
        type: array
        items:
          type: string
          format: uuid
        description: Model ID filter.
      - name: label_id
        in: query
        required: false
        type: array
        items:
          type: integer
        description: Label ID filter.
      - name: batch_size
        in: query
        required: false
        type: integer
        description: Number of candidate items to fetch.
    responses:
      200:
        description: Batch of images and predictions for auto-cropping.
      400:
        description: Invalid query parameters.
      401:
        description: User not authorized.
      500:
        description: Database error.
    """
    batch = base.get_auto_crop_batch(query, cast(User, current_user))

    return batch, 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@cropBp.post("")
@login_required
@permission_required("access")
@validate()
def auto_crop_image(body: AutoCropReq):
    """Generate spatial crops and draft annotations for an image using KMeans clustering.

    Args:
        body: Request containing image ID, candidate predictions, and taxonomy label IDs.

    Returns:
        Tuple containing empty string and HTTP status 201.

    ---
    parameters:
      - name: body
        in: body
        required: true
        type: AutoCropReq
        description: Request containing image ID, candidate predictions, and taxonomy label IDs.
    responses:
      201:
        description: Crops and draft annotations generated successfully.
      400:
        description: Invalid request payload or validation failure.
      401:
        description: User not authorized.
      500:
        description: Image processing or database error.
    """
    image = base.get(Image, body.image_id)
    predictions = body.predictions

    herd_unit = base.get(HerdUnit, image.herd_unit_id)

    h_key = Keyring(herd_unit.herd_unit_id, herd_unit.uuid)
    u_key = Keyring(current_user.user_id, current_user.uuid)

    labels = base.bulk_get(Label, BulkRequest(object_ids=body.label_ids))

    image_data = cache.get(image.uuid)

    if not image_data:
        image_data = s3.get_object(
            Bucket=current_app.config["BUCKET_NAME"], Key=image.img_key
        )["Body"].read()
        cache.set(image.uuid, image_data, 500)

    image.set_image(image_data)

    crops = auto_crop(image, predictions, labels)

    for crop_group in crops:
        crop_req, annotation_reqs = crop_group

        crop_req.ra_key = f"images/{image.uuid}/reviewed_area/{crop_req.name}"
        crop = base.insert(ReviewedArea, crop_req)

        for annotation_req in annotation_reqs:
            annotation_req.reviewed_area_ids = Keyring(
                pkey=crop.reviewed_area_id, uuid=crop.uuid
            )

            base.insert(Annotation, annotation_req, u_key, h_key)

        s3.put_object(
            Bucket=current_app.config["BUCKET_NAME"],
            Key=crop_req.ra_key,
            Body=io.BytesIO(crop_req.serve(".JPG")),
            ContentType="image/jpeg",
        )

    for pred in predictions:
        req = UpdatePredictionReq(reviewed_by_user_id=current_user.user_id)
        base.update(Prediction, pred.pred_id, req)

    base.update(
        Image,
        image.uuid,
        UpdateImageReq(opened_by_user_id=0),
    )
    return "", 201
