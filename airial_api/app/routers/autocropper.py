# Endpoints for the autocropper utility
# Author: Michael B. Lance

"""Endpoints for the automated crop generator utility."""

# ---------------------------------------------------------------------------------------------------------------------------

import io
from typing import cast

from flask import Blueprint, current_app
from flask_login import current_user, login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base, cache, s3
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

cropBp = Blueprint("autocropper", __name__, url_prefix="/api/v1/autocropper")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@cropBp.get("/batch")
@login_required
@permission_required("access")
@validate()
def fetch_batch(query: AutoCropperBatchQuery):
    """Fetch a candidate batch of images and predictions for auto-cropping."""
    batch = base.get_auto_crop_batch(query, cast(User, current_user))

    return batch, 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@cropBp.post("")
@login_required
@permission_required("access")
@validate()
def auto_crop_image(body: AutoCropReq):
    """Generate spatial crops and draft annotations for an image using KMeans clustering."""
    image = base.get(Image, body.image_id)
    predictions = body.predictions

    herd_unit = base.get(HerdUnit, image.herd_unit_id)

    h_key = Keyring(herd_unit.herd_unit_id, herd_unit.uuid)
    u_key = Keyring(current_user.user_id, current_user.uuid)

    labels = base.bulk_get(Label, BulkRequest(object_ids=body.label_ids))

    image_data = cache.get(image.uuid)

    if not image_data:
        image_data = s3.get_object(Bucket=current_app.config["BUCKET_NAME"], Key=image.img_key)["Body"].read()
        cache.set(image.uuid, image_data, 500)

    image.set_image(image_data)

    crops = auto_crop(image, predictions, labels)

    for crop_group in crops:
        crop_req, annotation_reqs = crop_group

        crop_req.ra_key = f"images/{image.uuid}/reviewed_area/{crop_req.name}"
        crop = base.insert(ReviewedArea, crop_req)

        for annotation_req in annotation_reqs:
            annotation_req.reviewed_area_ids = Keyring(pkey=crop.reviewed_area_id, uuid=crop.uuid)

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
