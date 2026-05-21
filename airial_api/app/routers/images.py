# Endpoints for managing images in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID

import cv2
from flask import Blueprint, Response, abort, current_app
from flask_login import current_user, login_required
from flask_pydantic import validate
from app.decorators import permission_required, roles_required

from app.extensions import base, cache, s3
from crop_generator import create_subcrop
from database.errors import ObjectNotFound
from database.object_models.core import (
    CreateImageReq,
    CreatePredictionCropReq,
    CreatePresignedPutReq,
    PredictionQuery,
    UpdateImageReq,
)
from database.object_models.core.images import (
    AbortMulitPartUploadReq,
    CompleteMultiPartUploadReq,
    CreateImageMultiPartUploadReq,
    PresignedImageGetReq,
)

imageBp = Blueprint("images", __name__, url_prefix="/api/v1/images")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@imageBp.get("/<string:image_id>")
@login_required
@permission_required("access")
def get_by_id(image_id: str):
    """
    Request an image object from the database using its UUID.
    ---
    parameters:
      - name: image_id
            in: path
            type: string
            required: true
    responses:
      200:
            description: The requested image was found.
      400:
            description: Invalid UUID format provided.
      404:
            description: No image record found for the provided ID.
    """
    return base.get_image(UUID(image_id)).to_dict(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@permission_required("access")
@imageBp.get("/prediction_crops/<string:prediction_id>")
def get_prediction_crop(prediction_id: str):
    """ """
    crop = cache.get(prediction_id)
    if crop is None:
        raise ObjectNotFound("prediction_crop", prediction_id)

    _, encoded_image = cv2.imencode(".webp", crop)
    return Response(encoded_image.tobytes(), mimetype="image/webp"), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.get("/<string:image_id>/crops")
@login_required
def get_crops(image_id: str):
    """
    Retrieve crops for a specific image
    ---
    responses:
      200:
            description: List of crops.
      404:
            description: No crops found.
      500:
            description: Database error.
    """

    crops = base.get_image_crops(UUID(image_id))

    return [crop.to_dict() for crop in crops], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.get("/<string:image_id>/predictions")
@login_required
@permission_required("access")
def get_predictions(image_id: str):
    """
    Retrieve all predictions associated with an image.
    ---
    parameters:
            - name: image_id
            in: path
            type: string
            required: true
    responses:
            200:
                    description: List of predictions.
            400:
                    description: Invalid UUID format.
            404:
                    description: No predictions found.
            500:
                    description: Database error.
    """

    predictions = base.get_image_predictions(UUID(image_id))

    return [pred.to_dict() for pred in predictions], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.get("/<string:image_id>/annotations")
@login_required
@permission_required("access")
def get_annotations(image_id: str):
    """
    Retrieve all annotations associated with an image.
    ---
    parameters:
            - name: image_id
              in: path
              type: string
              required: true
    responses:
            200:
                    description: Annotations belonging to a given image.
            401:
                    description: User not authorized to perform this action.
            400:
                    description: Malformed request.
            404:
                    description: Image not found.
            500:
                    description: Unexpected error.

    """

    annotations = base.get_image_annotations(UUID(image_id))

    return [annot.to_dict() for annot in annotations], 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@imageBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateImageReq):
    """
    Create a new image object.
    ---
    parameters:
            - name: create image request
            in: body
            type: CreateImageReq
            required: true
    responses:
            201:
                    description: Created successfully.
            409:
                    description: Image already exists (Unique Violation).
            400:
            500:
                    description: Database error.
    """
    return base.create_image(body).to_dict(), 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.post("/presigned-get-url")
@login_required
@permission_required("access")
@validate()
def create_presigned_get(body: PresignedImageGetReq):
    """
    Generate a presigned GET URL for an image.
    ---
    responses:
            201:
                    description: Presigned URL generated.
            400:
                    description: Invalid ID format.
            404:
                    description: Image record not found.
            500:
                    description: Storage or database error.
    """

    image = base.get_image(body.image_id)

    if not image:
        raise ObjectNotFound("image", str(body.image_id))

    response = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": current_app.config["BUCKET_NAME"], "Key": image.img_key},
        ExpiresIn=body.image_id,
    )

    return response, 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.post("/presigned-put-url")
@roles_required("admin")
@validate()
@login_required
@permission_required("access")
def create_chunk_presigned_put(body: CreatePresignedPutReq):
    """
    Generates a pre-signed URL for a single file chunk (UploadPart).
    ---
    responses:
            201:
                    description: URL generated.
            400:
                    description: Missing data or invalid UUID.
            404:
                    description: Image not found.
            500:
                    description: Storage/Database error.
    """
    data = body.model_dump()

    image_id = (
        UUID(data["image_id"])
        if isinstance(data["image_id"], str)
        else data["image_id"]
    )
    image = base._get_image(image_id)

    if image is None:
        abort(404, "Image not found")

    response = s3.generate_presigned_url(
        ClientMethod="upload_part",
        Params={
            "Bucket": current_app.config["BUCKET_NAME"],
            "Key": image.img_key,
            "UploadId": data["upload_id"],
            "PartNumber": data["part_number"],
            "ContentLength": data["chunk_size"],
            "ContentMD5": data["chunk_md5"],
        },
        ExpiresIn=3600,
    )

    return response, 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.post("/create-multipart-upload")
@login_required
@permission_required("access")
@validate()
def create_multipart_upload(body: CreateImageMultiPartUploadReq):
    """
    Initiates a new multipart upload.
    ---
    responses:
            201:
                    description: Multipart upload started.
            500:
                    description: system error.
    """
    response = s3.create_multipart_upload(
        Bucket=current_app.config["BUCKET_NAME"],
        Key=body.image_key,
        ContentType="image/jpeg",
    )

    return response["UploadId"], 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.post("/complete-multipart-upload")
@login_required
@permission_required("access")
@validate()
def complete_upload(body: CompleteMultiPartUploadReq):
    """
    Completes a new multipart upload.
    ---
    responses:
            201:
                    description: Multipart upload finished.
            500:
                    description: S3 or system error.
    """

    response = s3.complete_multipart_upload(
        Bucket=current_app.config["BUCKET_NAME"],
        Key=body.image_key,
        MultipartUpload={"Parts": body.parts},
        UploadId=body.upload_id,
    )

    return response, 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.post("/abort-multipart-upload")
@login_required
@permission_required("access")
@validate()
def abort_upload(body: AbortMulitPartUploadReq):
    """
    Aborts a multipart upload.
    ---
    responses:
            200:
                    description: Multipart upload aborted.
            500:
                    description: S3 or system error.
    """

    response = s3.abort_multipart_upload(
        Bucket=current_app.config["BUCKET_NAME"],
        Key=body.image_key,
        UploadId=body.upload_id,
    )

    return response, 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.post("/prediction_crops")
@login_required
@permission_required("acecss")
@validate()
def get_prediciton(body: CreatePredictionCropReq):
    """"""
    image = base.get_image(body.image_id)
    predictions = base.get_predictions(
        PredictionQuery(prediction_id=body.prediction_id)
    )

    image_data = cache.get(image.uuid)

    if not image_data:
        image_data = s3.get_object(
            Bucket=current_app.config["BUCKET_NAME"], Key=image.img_key
        )["Body"].read()

        cache.set(image.uuid, image_data, 500)

    image.set_image(image_data)
    pred_crops = create_subcrop(image, predictions)

    [cache.set(crop.uuid, crop.get_image(), 3600) for crop in pred_crops]

    return [crop.to_dict() for crop in pred_crops]


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@imageBp.patch("/<string:image_id>")
@login_required
@permission_required("acecss")
@validate()
def update(body: UpdateImageReq, image_id: str):
    """
    Update image object in the database.
    ---
    paramete:qrsrs:
            - name: image_id
            in: path
            type: string
            required: true
    responses:
            200:
                    description: Image updated successfully.
            400:
                    description: Invalid UUID.
            404:
                    description: Image not found.
            500:
                    description: Database error.
    """

    return base.update_image(UUID(image_id), body).to_dict(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.patch("/close-user-images")
@login_required
@permission_required("acess")
def close_user_images():
    """ """

    base.close_user_images(current_user.user_id)

    return "", 204


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@imageBp.delete("/<string:image_id>")
@login_required
@permission_required("access")
def delete_image(image_id: str):
    """ """

    image = base.get_image(UUID(image_id))

    s3.delete_object(Bucket=current_app.config["BUCKET_NAME"], Key=image.img_key)

    base.delete_image(UUID(image_id))

    return "", 204
