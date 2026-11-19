"""Endpoints for the survey map in the API."""

from typing import cast

from ais import MeasurementState
from database.errors import ObjectNotFound
from database.modules import activemeasurement, surveymap
from database.object_models.base import Keyring
from database.object_models.core.images import Image
from database.object_models.core.survey_maps import OverlayQuery, SurveyMapQuery
from database.object_models.project_management.surveys import Survey
from flask import Blueprint
from flask_login import login_required
from flask_pydantic import validate

from app import overlays, proposal_store
from app.decorators import permission_required
from app.extensions import base

surveyMapBp = Blueprint("survey_maps", __name__, url_prefix="/api/v1/survey-maps")

# A survey with no measurement, or none with a proposal, shows no detection.
NO_DETECTIONS = {
    "annotated": 0,
    "estimated": 0,
    "unplaced": 0,
    "threshold": None,
    "detections": [],
}


# ---------------------------------------------------------------------------------------------------------------------------
# GET


@surveyMapBp.get("/footprints")
@login_required
@permission_required("access")
@validate()
def get_footprints(query: SurveyMapQuery):
    """Retrieve the footprints of a survey's images as GeoJSON.

    Args:
        query: The survey.

    Returns:
        Tuple of the FeatureCollection and HTTP status 200.

    ---
    parameters:
      - name: survey_id
        in: query
        required: true
        schema:
          type: string
          format: uuid
        description: Survey whose footprints are drawn.
    responses:
      200:
        description: >
          GeoJSON FeatureCollection. Each feature carries its image, its area,
          the box its overlay covers, and its tiles and tiles reviewed.
      401:
        description: Unauthorized.
      404:
        description: Survey not found.
      500:
        description: Database error.
    """
    survey = base.get(Survey, query.survey_id)
    return base.execute(surveymap.get_footprints, survey.survey_id), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@surveyMapBp.get("/detections")
@login_required
@permission_required("access")
@validate()
def get_detections(query: SurveyMapQuery):
    """Retrieve the detections a survey's map shows, placed on the ground.

    The annotations on the reviewed tiles, and the detector's boxes at the
    draft threshold standing in for the animals the running estimate expects
    on the tiles not reviewed.

    Args:
        query: The survey.

    Returns:
        Tuple of the detections and HTTP status 200.

    ---
    parameters:
      - name: survey_id
        in: query
        required: true
        schema:
          type: string
          format: uuid
        description: Survey whose detections are drawn.
    responses:
      200:
        description: >
          How many detections are annotated, estimated and left unplaced, the
          draft threshold, and each detection with its image, kind, score and
          prediction (estimated only), box in image pixels and position. Empty
          without a measurement or a proposal.
      401:
        description: Unauthorized.
      404:
        description: Survey not found.
      500:
        description: Database error.
    """
    survey = base.get(Survey, query.survey_id)
    survey_ids = Keyring(survey.survey_id, survey.uuid)

    try:
        measurement = base.execute(activemeasurement.get_recent_measurement, survey_ids)
    except ObjectNotFound:
        return NO_DETECTIONS, 200

    if (state := proposal_store.load(measurement)) is None:
        return NO_DETECTIONS, 200

    estimate = base.execute(
        activemeasurement.live_estimate,
        measurement,
        state,
        lambda: proposal_store.vectors(measurement, cast(MeasurementState, state)),
        proposal_store.load_surveyed_area(measurement, state),
    )
    detections = base.execute(
        surveymap.get_detections,
        measurement,
        state,
        proposal_store.load_boxes(measurement, state),
        proposal_store.load_threshold(measurement, state),
        estimate["count"],
    )
    return detections, 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@surveyMapBp.get("/overlay")
@login_required
@permission_required("access")
@validate()
def get_overlay(query: OverlayQuery):
    """Retrieve an image drawn onto the ground, drawing it on first request.

    Args:
        query: The image.

    Returns:
        Tuple of the overlay's temporary URL with its bounds and HTTP status
        200.

    ---
    parameters:
      - name: image_id
        in: query
        required: true
        schema:
          type: string
          format: uuid
        description: Image to draw.
    responses:
      200:
        description: >
          A temporary URL of the overlay, a WebP with transparency, and the
          bounds it covers as [[south, west], [north, east]].
      401:
        description: Unauthorized.
      404:
        description: Image not found, or it has no footprint to draw it on.
      500:
        description: Storage or database error.
    """
    image = base.get(Image, query.image_id)
    return overlays.get_overlay(image), 200
