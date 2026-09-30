# Endpoints for the survey map in the API
# Author: Owen Martin

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID

from flask import Blueprint, Response
from flask_login import login_required
from flask_pydantic import validate
from pydantic import BaseModel

from app import detection_crops, overlays, proposal_store
from app.decorators import permission_required
from app.extensions import base
from database.errors import ObjectNotFound
from database.modules import activemeasurement, surveymap
from database.object_models.base import Keyring
from database.object_models.core.images import Image
from database.object_models.project_management.surveys import Survey

surveyMapBp = Blueprint("survey_maps", __name__, url_prefix="/api/v1/survey-maps")

# ---------------------------------------------------------------------------------------------------------------------------


class SurveyMapQuery(BaseModel):
    survey_id: UUID


class OverlayReq(BaseModel):
    image_id: UUID


class DetectionCropReq(BaseModel):
    image_id: UUID
    box: list[int]  # tx, ty, bx, by in image pixels
    kind: str = "estimated"


# ---------------------------------------------------------------------------------------------------------------------------
# GET


@surveyMapBp.get("/footprints")
@login_required
@permission_required("access")
@validate()
def get_footprints(query: SurveyMapQuery):
    """
    Retrieve the footprints of a survey's images as GeoJSON.
    ---
    parameters:
      - name: survey_id
        in: query
        required: true
        type: string
        format: uuid
        description: Survey whose footprints are drawn.
    responses:
      200:
        description: >
          GeoJSON FeatureCollection. Each feature carries its image, its area, the box its overlay
          covers, and its tiles reviewed.
      401:
        description: Unauthorized.
      404:
        description: Survey not found.
      500:
        description: Database error.
    """
    survey = base.get(Survey, query.survey_id)
    survey_ids = Keyring(survey.survey_id, survey.uuid)

    return base.execute(surveymap.get_footprints, survey_ids), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@surveyMapBp.get("/detections")
@login_required
@permission_required("access")
@validate()
def get_detections(query: SurveyMapQuery):
    """
    Retrieve the detections a survey's map shows, placed on the ground.
    ---
    parameters:
      - name: survey_id
        in: query
        required: true
        type: string
        format: uuid
        description: Survey whose detections are drawn.
    responses:
      200:
        description: >
          The annotated and estimated detections with the image each is on, its score and its
          position. Empty until tiles of the survey have been reviewed.
      401:
        description: Unauthorized.
      404:
        description: Survey not found.
      500:
        description: Database error.
    """
    survey = base.get(Survey, query.survey_id)
    survey_ids = Keyring(survey.survey_id, survey.uuid)
    nothing = {"annotated": 0, "estimated": 0, "unplaced": 0, "detections": []}

    try:
        measurement = base.execute(activemeasurement.get_active_measurement, survey_ids)
    except ObjectNotFound:
        return nothing, 200

    if (state := proposal_store.load(measurement)) is None:
        return nothing, 200

    estimate = base.execute(
        activemeasurement.live_estimate,
        measurement,
        state,
        lambda: proposal_store.vectors(measurement, state),
    )
    expected = dict(zip(state.reviewed_area_ids, map(float, state.raw)))

    detections = base.execute(
        surveymap.get_detections, measurement, expected, estimate["count"]
    )
    return detections, 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@surveyMapBp.post("/detection-crop")
@login_required
@permission_required("access")
@validate()
def create_detection_crop(body: DetectionCropReq):
    """
    Retrieve the image around a detection with its box drawn, as WebP.
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: DetectionCropReq
        description: The image, the box in image pixels and whether it is annotated or estimated.
    responses:
      200:
        description: A WebP crop centered on the box.
      400:
        description: Validation error.
      401:
        description: Unauthorized.
      404:
        description: Image not found.
      500:
        description: Database error.
    """
    if len(body.box) != 4:
        return {"message": "box must be tx, ty, bx, by"}, 400

    image = base.get(Image, body.image_id)
    crop = detection_crops.detection_crop(image, body.box, body.kind)
    return Response(crop, mimetype="image/webp")


@surveyMapBp.post("/overlay")
@login_required
@permission_required("access")
@validate()
def create_overlay(body: OverlayReq):
    """
    Retrieve an image drawn onto the ground, building it the first time it is asked for.
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: OverlayReq
        description: The image to draw.
    responses:
      201:
        description: A temporary URL of the overlay and the bounds it covers.
      401:
        description: Unauthorized.
      404:
        description: Image not found, or it has no footprint to draw it on.
      500:
        description: Storage or database error.
    """
    image = base.get(Image, body.image_id)

    return overlays.get_overlay(image), 201
