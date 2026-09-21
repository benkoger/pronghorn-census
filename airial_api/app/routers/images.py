# Endpoints for managing images in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID

import cv2
from flask import Blueprint, Response, current_app
from flask_login import current_user, login_required
from flask_pydantic import validate
from app.decorators import permission_required, roles_required

from app.extensions import base, cache, s3
from crop_generator import create_subcrop
from database.errors import ObjectNotFound
from database.object_models.base import BulkRequest
from database.object_models.core import (
    Image,
    ImageMetadata,
    ImageFootprint,
    Prediction,
    Annotation,
    ReviewedArea,
    CreateImageReq,
    CreatePredictionCropReq,
    CreatePresignedPutReq,
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


@imageBp.get("/<int:image_id>")
@imageBp.get("/<uuid:image_id>")
@login_required
@permission_required("access")
def get_by_id(image_id: int | UUID):
    """
    Request an image object from the database using its integer PK or UUID.
    ---
    parameters:
      - name: image_i
        in: path
        type: string
        required: true
    responses:
      200:
        description: The requested image was found.
      400:
        description: Invalid id format provided.
      404:
        description: No image record found for the provided ID.
    """

    return base.get(Image, image_id).serialize(), 200


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


@imageBp.get("/<int:image_id>/crops")
@imageBp.get("/<uuid:image_id>/crops")
@login_required
def get_crops(image_id: int | UUID):
    """
    Retrieve crops for a specific image
    ---
    responses:
      200:
        description: List of crops (returns [] if parent exists but has no crops).
      404:
        description: Parent image not found.
      500:
        description: Database error.
    """
    crops = base.get_children(
        ReviewedArea,
        Image,
        image_id,
    )

    return [crop.serialize() for crop in crops], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.get("/<int:image_id>/predictions")
@imageBp.get("/<uuid:image_id>/predictions")
@login_required
@permission_required("access")
def get_predictions(image_id: int | UUID):
    """
    Retrieve all predictions for a specific image.
    ---
    parameters:
      - name: image_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 42
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the image (integer ID or UUID).
    responses:
      200:
        description: List of predictions.
      400:
        description: Invalid id format.
      404:
        description: Parent image not found.
      500:
        description: Database error.
    """
    predictions = base.get_children(Prediction, Image, image_id)

    return [pred.serialize() for pred in predictions], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.get("/<int:image_id>/metadata")
@imageBp.get("/<uuid:image_id>/metadata")
@login_required
@permission_required("access")
def get_metadata(image_id: int | UUID):
    """
    Retrieve metadata associated with a specific image.
    ---
    parameters:
      - name: image_id
        in: path
        required: true
        description: Primary key of the image (integer ID or UUID).
    responses:
      200:
        description: List of metadata records.
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this image.
      404:
        description: Image not found.
      500:
        description: Database error.
    """
    metadata = base.get_children(ImageMetadata, Image, image_id)
    return [m.serialize() for m in metadata], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.get("/<int:image_id>/footprints")
@imageBp.get("/<uuid:image_id>/footprints")
@login_required
@permission_required("access")
def get_footprints(image_id: int | UUID):
    """
    Retrieve footprints associated with a specific image.
    ---
    parameters:
      - name: image_id
        in: path
        required: true
        description: Primary key of the image (integer ID or UUID).
    responses:
      200:
        description: List of footprint records.
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this image.
      404:
        description: Image not found.
      500:
        description: Database error.
    """
    footprints = base.get_children(ImageFootprint, Image, image_id)
    return [fp.serialize() for fp in footprints], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.get("/<int:image_id>/annotations")
@imageBp.get("/<uuid:image_id>/annotations")
@login_required
@permission_required("access")
def get_annotations(image_id: int | UUID):
    """
    Retrieve all annotations for a specific image.
    ---
    parameters:
      - name: image_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 42
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the image (integer ID or UUID).
    responses:
      200:
        description: List of annotations.
      400:
        description: Invalid id format.
      404:
        description: Parent image not found.
      500:
        description: Database error.
    """

    annotations = base.get_children(Annotation, Image, image_id)

    return [annot.serialize() for annot in annotations], 200


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
    return base.insert(Image, body).serialize(), 201


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

    image = base.get(Image, body.image_id)

    response = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": current_app.config["BUCKET_NAME"], "Key": image.img_key},
        ExpiresIn=3600,
    )

    return response, 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.post("/presigned-put-url")
@login_required
@roles_required("admin")
@permission_required("access")
@validate()
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

    image = base.get(Image, body.image_id)

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
            200:
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

    return response, 200


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
@permission_required("access")
@validate()
def get_prediciton(body: CreatePredictionCropReq):
    """"""
    image = base.get(Image, body.image_id)
    req = BulkRequest(object_ids=body.prediction_id) #pyright: ignore
    predictions = base.bulk_get(Prediction, req)

    image_data = cache.get(image.uuid)

    if not image_data:
        image_data = s3.get_object(
            Bucket=current_app.config["BUCKET_NAME"], Key=image.img_key
        )["Body"].read()

        cache.set(image.uuid, image_data, 500)

    image.set_image(image_data)
    pred_crops = create_subcrop(image, predictions)

    [cache.set(crop.uuid, crop.get_image(), 3600) for crop in pred_crops]

    return [crop.serialize() for crop in pred_crops]


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@imageBp.patch("/<int:image_id>")
@imageBp.patch("/<uuid:image_id>")
@login_required
@permission_required("access")
@validate()
def update(body: UpdateImageReq, image_id: int | UUID):
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
    return base.update(Image, image_id, body).serialize(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@imageBp.patch("/close-user-images")
@login_required
@permission_required("access")
def close_user_images():
    """Close all images currently opened by the authenticated user."""
    req = UpdateImageReq(opened_by_user_id=0)

    rows_affected = base.bulk_update(
        Image,
        req,
        {"opened_by_user_id": current_user.user_id},
    )

    return {"rows_affected": rows_affected}, 200


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@imageBp.delete("/<int:image_id>")
@imageBp.delete("/<uuid:image_id>")
@login_required
@permission_required("access")
def delete_image(image_id: int | UUID):
    """ """

    image = base.get(Image, image_id)

    s3.delete_object(Bucket=current_app.config["BUCKET_NAME"], Key=image.img_key)

    base.delete(Image, image_id)

    return "", 204
