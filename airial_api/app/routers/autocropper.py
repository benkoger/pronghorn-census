# Endpoints for the autocropper utility
# Author: Michael B. Lance

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
from database.object_models.core import UpdateImageReq
from database.object_models.project_management import LabelQuery
from database.object_models.user_management import User

cropBp = Blueprint("autocropper", __name__, url_prefix="/api/v1/autocropper")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@cropBp.get("/batch")
@login_required
@permission_required("access")
@validate()
def fetch_batch(query: AutoCropperBatchQuery):
    """ """
    batch = base.get_auto_crop_batch(query, cast(User, current_user))

    return batch, 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@cropBp.post("")
@login_required
@permission_required("access")
@validate()
def auto_crop_image(body: AutoCropReq):
    """ """

    image = base.get_image(body.image_id)
    predictions = body.predictions

    labels = base.get_labels(LabelQuery(label_id=body.label_ids))

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
        crop = base.create_reviewed_area(crop_req)

        for annotation_req in annotation_reqs:
            annotation_req.reviewed_area_id = crop.uuid
            base.create_annotation(annotation_req, cast(User, current_user))
        s3.put_object(
            Bucket=current_app.config["BUCKET_NAME"],
            Key=crop_req.ra_key,
            Body=io.BytesIO(crop_req.serve(".JPG")),
            ContentType="image/jpeg",
        )

    base.set_predictions_reviewed(
        [pred.uuid for pred in predictions], cast(User, current_user)
    )
    base.update_image(
        image.uuid,
        UpdateImageReq(opened_by_user_id=0),
    )
    return "", 201
