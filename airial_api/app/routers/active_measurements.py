"""Endpoints for managing active measurements in the API."""

from typing import cast
from uuid import UUID

from flask import Blueprint
from flask_login import current_user, login_required
from flask_pydantic import validate

from ais import MeasurementState, Proposal
from app import proposal_store, tile_crops
from app.decorators import permission_required
from app.extensions import base
from database.errors import MeasurementBlocked, ObjectNotFound
from database.modules import activemeasurement
from database.object_models.base import Keyring
from database.object_models.core.am_units import AmUnit
from database.object_models.core.images import ReviewedArea
from database.object_models.project_management.active_measurements import (
    ActiveMeasurement,
    ActiveMeasurementQuery,
    CreateActiveMeasurement,
    CreateProposalReq,
    CreateTilesReq,
    UpdateActiveMeasurement,
)
from database.object_models.project_management.surveys import Survey
from database.object_models.user_management import User

activeMeasBp = Blueprint(
    "active_measurements", __name__, url_prefix="/api/v1/active-measurements"
)


# ---------------------------------------------------------------------------------------------------------------------------
# GET


@activeMeasBp.get("/next-unit")
@login_required
@permission_required("access")
@validate()
def get_next_unit(query: ActiveMeasurementQuery):
    """
    Retrieve the next reviewed area to annotate for a survey's measurement.
    ---
    parameters:
      - name: survey_id
        in: query
        required: true
        type: string
        format: uuid
        description: Survey whose active measurement is being reviewed.
    responses:
      200:
        description: >
          The reviewed area to annotate next, with the detector's expected
          count of it (the sum of its boxes' scores above the draft threshold),
          the number of those boxes and the threshold. Repeats until it is
          marked reviewed.
      204:
        description: The active measurement is finished.
      401:
        description: Unauthorized.
      404:
        description: Survey or active measurement not found.
      409:
        description: No proposal posted yet, or a proposal refit is pending.
      500:
        description: Database error.
    """
    survey = base.get(Survey, query.survey_id)
    survey_ids = Keyring(survey.survey_id, survey.uuid)

    measurement = base.execute(activemeasurement.get_recent_measurement, survey_ids)
    state = proposal_store.load(measurement)
    # The score boxes are drafted at: where the detector's box count over the
    # units meets the regressor's expected total. Nothing is drafted without
    # a proposal, which next_unit refuses anyway.
    threshold = (
        proposal_store.load_threshold(measurement, state)
        if state is not None
        else activemeasurement.NO_DRAFTS
    )

    reviewed_area_ids = base.execute(
        activemeasurement.next_unit,
        measurement,
        state,
        cast(User, current_user),
        lambda: proposal_store.vectors(measurement, cast(MeasurementState, state)),
        threshold,
    )

    if reviewed_area_ids is None:
        proposal_store.release(measurement)
        return "", 204

    reviewed_area = base.get(ReviewedArea, reviewed_area_ids.pkey)
    tile_crops.ensure_crop(reviewed_area)

    # With the detector's expected count of the unit (the sum of its boxes'
    # scores above the draft threshold) and the number of boxes, for the
    # reviewer. The regressor's own output is relative, not a count.
    expected, n_boxes = base.execute(
        activemeasurement.detector_expectation,
        measurement,
        reviewed_area.reviewed_area_id,
        threshold,
    )
    return {
        **reviewed_area.serialize(),
        "expected_count": expected,
        "n_boxes": n_boxes,
        "draft_threshold": threshold,
    }, 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@activeMeasBp.get("/estimate")
@login_required
@permission_required("access")
@validate()
def get_estimate(query: ActiveMeasurementQuery):
    """
    Retrieve the live estimate for a survey's active measurement.
    ---
    parameters:
      - name: survey_id
        in: query
        required: true
        type: string
        format: uuid
        description: Survey whose active measurement is being estimated.
    responses:
      200:
        description: >
          Running count, 95% interval, progress, and density over the measured
          area. A survey without a measurement answers with status
          'not prepared' and null figures.
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
        return activemeasurement.empty_estimate(survey.survey_id), 200

    state = proposal_store.load(measurement)
    terms = proposal_store.load_terms(measurement)

    # The surveyed area from the terms when the survey map has produced
    # them, else the cached union of the units' footprints.
    if terms:
        area = terms.surveyed_area_m2
    elif state is not None:
        area = proposal_store.load_area(measurement, state)
    else:
        area = None

    estimate = base.execute(
        activemeasurement.live_estimate,
        measurement,
        state,
        lambda: proposal_store.vectors(measurement, cast(MeasurementState, state)),
        area,
    )
    return estimate, 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@activeMeasBp.get("/status")
@login_required
@permission_required("access")
@validate()
def get_status(query: ActiveMeasurementQuery):
    """
    Retrieve how far a survey's preparation for abundance estimation has come.
    ---
    parameters:
      - name: survey_id
        in: query
        required: true
        type: string
        format: uuid
        description: Survey whose preparation is reported.
    responses:
      200:
        description: >
          Counts of images, predictions, footprints and tiles, the measurement
          if one exists with its label, the detector, the proposal's
          generations and expected total, and the steps with their state and
          provenance.
      401:
        description: Unauthorized.
      404:
        description: Survey not found.
      500:
        description: Database error.
    """
    survey = base.get(Survey, query.survey_id)
    survey_ids = Keyring(survey.survey_id, survey.uuid)

    status = base.execute(activemeasurement.get_preparation, survey_ids)

    status["detector"] = None
    if status["images_with_predictions"] > 0:
        model = base.execute(activemeasurement.get_detection_model, survey.survey_id)
        boxes, images = base.execute(
            activemeasurement.count_detections, survey.survey_id, model.model_id
        )
        status["detector"] = {
            "name": model.name,
            "uuid": str(model.uuid),
            "boxes": boxes,
            "images": images,
        }

    state = None
    if status["measurement"]:
        measurement = base.get(
            ActiveMeasurement, status["measurement"]["active_measurement_id"]
        )
        state = proposal_store.load(measurement)

    status["proposal"] = None
    if state is not None and state.generations:
        latest = state.generations[-1]
        status["proposal"] = {
            "generations": len(state.generations),
            "n_units": len(state.reviewed_area_ids),
            "expected_total": float(state.raw.sum()),
            "first_alpha": state.generations[0].alpha,
            "alpha": latest.alpha,
            "n_labels": latest.n_labels,
        }
    status["proposal_generations"] = len(state.generations) if state else 0
    status["steps"] = activemeasurement.preparation_steps(status)
    status["ready"] = all(step["done"] for step in status["steps"])

    return status, 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@activeMeasBp.get("/tiles")
@login_required
@permission_required("access")
@validate()
def get_tiles(query: ActiveMeasurementQuery):
    """
    Retrieve the active measurement reviewed areas (tiles) of a survey.
    ---
    parameters:
      - name: survey_id
        in: query
        required: true
        type: string
        format: uuid
        description: Survey whose tiles are listed.
    responses:
      200:
        description: List of tiles with reviewed_area_id, uuid, image_id and name.
      401:
        description: Unauthorized.
      404:
        description: Survey not found.
      500:
        description: Database error.
    """
    survey = base.get(Survey, query.survey_id)
    survey_ids = Keyring(survey.survey_id, survey.uuid)

    return base.execute(activemeasurement.get_tiles, survey_ids), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@activeMeasBp.get("/<int:active_measurement_id>/proposals")
@activeMeasBp.get("/<uuid:active_measurement_id>/proposals")
@login_required
@permission_required("access")
def get_proposals(active_measurement_id: int | UUID):
    """
    Retrieve the proposal generations of an active measurement, oldest first.
    ---
    parameters:
      - name: active_measurement_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the active measurement (integer ID or UUID).
    responses:
      200:
        description: >
          List of generations with their label counts (empty if none exist).
      401:
        description: Unauthorized.
      404:
        description: Active measurement not found.
      500:
        description: Database error.
    """
    measurement = base.get(ActiveMeasurement, active_measurement_id)

    if (state := proposal_store.load(measurement)) is None:
        return [], 200

    return [
        {
            "generation": generation.generation,
            "n_labels": generation.n_labels,
            "n_units": state.n_units,
            "model_id": generation.model_id,
            "alpha": generation.alpha,
        }
        for generation in state.generations
    ], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@activeMeasBp.get("/<int:active_measurement_id>")
@activeMeasBp.get("/<uuid:active_measurement_id>")
@login_required
@permission_required("access")
def get_by_id(active_measurement_id: int | UUID):
    """Retrieve an active measurement by its integer ID or UUID.

    Args:
        active_measurement_id: Primary key of the active measurement (integer ID or UUID).

    Returns:
        Tuple containing the serialized active measurement and HTTP status 200.

    ---
    parameters:
      - name: active_measurement_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the active measurement (integer ID or UUID).
    responses:
      200:
        description: Active measurement found and returned.
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this active measurement.
      404:
        description: No active measurement found for the provided ID.
      500:
        description: Database error.
    """
    return base.get(ActiveMeasurement, active_measurement_id).serialize(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@activeMeasBp.get("/<int:active_measurement_id>/am-units")
@activeMeasBp.get("/<uuid:active_measurement_id>/am-units")
@login_required
@permission_required("access")
def get_am_units(active_measurement_id: int | UUID):
    """Retrieve all AM units associated with an active measurement.

    Args:
        active_measurement_id: Primary key of the parent active measurement (integer ID or UUID).

    Returns:
        Tuple containing list of serialized AM units and HTTP status 200.

    ---
    parameters:
      - name: active_measurement_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the parent active measurement (integer ID or UUID).
    responses:
      200:
        description: List of AM units (returns empty list if none exist).
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this active measurement.
      404:
        description: Parent active measurement not found.
      500:
        description: Database error.
    """
    am_units = base.get_children(AmUnit, ActiveMeasurement, active_measurement_id)
    return [unit.serialize() for unit in am_units], 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@activeMeasBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateActiveMeasurement):
    """Create a new active measurement.

    Args:
        body: Active measurement creation payload.

    Returns:
        Tuple containing the serialized created active measurement and HTTP status 201.

    ---
    parameters:
      - name: body
        in: body
        required: true
        type: CreateActiveMeasurement
        description: >
          Active measurement creation payload including survey_ids, label_ids,
          random_seed, and retraining_cadence.
    responses:
      201:
        description: Active measurement created successfully.
      400:
        description: Validation error or invalid payload.
      401:
        description: User not authorized to perform this action.
      409:
        description: Conflict or constraint violation.
      500:
        description: Database error.
    """
    return base.insert(ActiveMeasurement, body).serialize(), 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@activeMeasBp.post("/tiles")
@login_required
@permission_required("access")
@validate()
def create_tiles(body: CreateTilesReq):
    """
    Cut a survey's images into active measurement reviewed areas (tiles).
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: CreateTilesReq
        description: >
          The survey to cut and, optionally, which of its images. Images that
          already have tiles are skipped.
    responses:
      201:
        description: >
          List of the survey's tiles with reviewed_area_id, uuid, image_id and
          name.
      401:
        description: Unauthorized.
      404:
        description: Survey not found.
      500:
        description: Database error.
    """
    survey = base.get(Survey, body.survey_id)
    survey_ids = Keyring(survey.survey_id, survey.uuid)

    tiles = base.execute(activemeasurement.create_tiles, survey_ids, body.image_ids)
    return tiles, 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@activeMeasBp.post("/<int:active_measurement_id>/proposals")
@activeMeasBp.post("/<uuid:active_measurement_id>/proposals")
@login_required
@permission_required("access")
@validate()
def create_proposal(body: CreateProposalReq, active_measurement_id: int | UUID):
    """
    Store the next proposal generation for an active measurement.
    ---
    parameters:
      - name: active_measurement_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the active measurement (integer ID or UUID).
      - name: body
        in: body
        required: true
        type: CreateProposalReq
        description: >
          Unit order, raw and shaped proposal vectors, the exponent that shaped
          it, and the labels it was fitted on.
    responses:
      201:
        description: Proposal stored.
      400:
        description: Validation error or invalid payload.
      401:
        description: Unauthorized.
      404:
        description: Active measurement not found.
      409:
        description: >
          Unit order or label count conflicts with the stored generations, or
          the generation is stored already.
      500:
        description: Database error.
    """
    measurement = base.get(ActiveMeasurement, active_measurement_id)
    state = proposal_store.load(measurement)
    generation = len(state.generations) if state else 0

    try:
        proposal = Proposal(generation=generation, **body.model_dump())
    except ValueError as error:
        raise MeasurementBlocked(str(error))

    proposal_store.save(measurement, proposal)
    return {
        "generation": proposal.generation,
        "n_labels": proposal.n_labels,
    }, 201


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@activeMeasBp.patch("/<int:active_measurement_id>")
@activeMeasBp.patch("/<uuid:active_measurement_id>")
@login_required
@permission_required("access")
@validate()
def update(body: UpdateActiveMeasurement, active_measurement_id: int | UUID):
    """
    Update an active measurement by integer ID or UUID (e.g. the cadence).
    ---
    parameters:
      - name: active_measurement_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the active measurement to update.
      - name: body
        in: body
        required: true
        type: UpdateActiveMeasurement
        description: Active measurement update payload.
    responses:
      200:
        description: Active measurement updated successfully.
      400:
        description: Validation error or invalid ID format.
      401:
        description: User not authorized to modify this active measurement.
      404:
        description: Active measurement record not found.
      500:
        description: Database error.
    """
    updated = base.update(ActiveMeasurement, active_measurement_id, body)
    return updated.serialize(), 200


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@activeMeasBp.delete("/<int:active_measurement_id>")
@activeMeasBp.delete("/<uuid:active_measurement_id>")
@login_required
@permission_required("access")
def delete(active_measurement_id: int | UUID):
    """Delete an active measurement by integer ID or UUID.

    Args:
        active_measurement_id: Primary key of the active measurement to delete.

    Returns:
        Tuple containing empty string and HTTP status 204.

    ---
    parameters:
      - name: active_measurement_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the active measurement to delete.
    responses:
      204:
        description: Active measurement deleted successfully.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized to delete this active measurement.
      404:
        description: Active measurement not found.
      500:
        description: Database error.
    """
    measurement = base.get(ActiveMeasurement, active_measurement_id)
    base.delete(ActiveMeasurement, active_measurement_id)
    proposal_store.release(measurement)
    return "", 204
