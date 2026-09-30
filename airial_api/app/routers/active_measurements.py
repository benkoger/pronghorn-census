# Endpoints for managing active measurements in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from typing import cast
from uuid import UUID

from flask import Blueprint
from flask_login import current_user, login_required
from flask_pydantic import validate

from ais import MeasurementState, Proposal
from app import proposal_store, tile_crops
from app.decorators import permission_required
from app.extensions import base
from database.errors import MeasurementBlocked
from database.modules import abundance, activemeasurement
from database.object_models.base import Keyring
from database.object_models.core.am_units import AmUnit
from database.object_models.core.images import ReviewedArea
from database.object_models.project_management.active_measurements import (
    ActiveMeasurement,
    ActiveMeasurementQuery,
    CreateActiveMeasurement,
    CreateProposalReq,
    CreateTermsReq,
    CreateTilesReq,
    UpdateActiveMeasurement,
)
from database.object_models.project_management.surveys import Survey
from database.object_models.user_management import User

activeMeasBp = Blueprint("active_measurements", __name__, url_prefix="/api/v1/active-measurements")

# ---------------------------------------------------------------------------------------------------------------------------


def _preparation_steps(status: dict) -> list[dict]:
    """The preparation steps of a survey, each with whether it is done and a sentence saying so.

    A step is done when its process has run; the sentences do not say how many images succeeded.
    """
    steps = [
        ("detections", "Detections", status["images_with_predictions"] > 0,
         "Predictions generated", "Predictions have not been generated yet"),
        ("footprints", "Footprints", status["images_with_footprints"] > 0,
         "Images georeferenced", "Images have not been georeferenced yet"),
        ("tiles", "Tiles",
         status["tiles"] > 0 and status["georeferenced_images_without_tiles"] == 0,
         "Tiles cut", "Tiles have not been cut yet"),
        ("measurement", "Measurement", status["measurement"] is not None,
         "Measurement created", "Measurement has not been created yet"),
        ("proposal", "Sampling proposal", status["proposal_generations"] > 0,
         "Sampling proposal ready", "Waiting for the sampling proposal"),
    ]

    return [
        {"key": key, "label": label, "done": done, "detail": said if done else unsaid}
        for key, label, done, said, unsaid in steps
    ]


def _store_final_animals(measurement: ActiveMeasurement, state) -> None:
    """Rewrites a finished measurement's final count and interval as animals (overlap applied)."""
    terms = proposal_store.load_terms(measurement)
    if terms is None:
        return

    estimate = base.execute(
        activemeasurement.live_estimate,
        measurement,
        state,
        lambda: proposal_store.vectors(measurement, state),
        terms.surveyed_area_m2,
    )
    live = base.execute(
        abundance.live_abundance,
        measurement,
        state,
        estimate,
        terms,
        proposal_store.load_boxes(measurement),
    )
    if live is None:
        return

    corrected = abundance.apply_overlap(estimate, live)
    base.update(
        ActiveMeasurement,
        measurement.active_measurement_id,
        UpdateActiveMeasurement(
            final_count=corrected["count"],
            final_ci_lower=corrected["ci_lower"],
            final_ci_upper=corrected["ci_upper"],
        ),
    )


# ---------------------------------------------------------------------------------------------------------------------------
# GET


@activeMeasBp.get("/next-unit")
@login_required
@permission_required("access")
@validate()
def get_next_unit(query: ActiveMeasurementQuery):
    """
    Retrieve the next reviewed area to annotate for a survey's active measurement.
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
        description: The reviewed area to annotate next. Repeats until it is marked reviewed.
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

    measurement = base.execute(activemeasurement.get_active_measurement, survey_ids)
    state = proposal_store.load(measurement)

    reviewed_area_ids = base.execute(
        activemeasurement.next_unit,
        measurement,
        state,
        cast(User, current_user),
        lambda: proposal_store.vectors(measurement, cast(MeasurementState, state)),
    )

    if reviewed_area_ids is None:
        _store_final_animals(measurement, state)
        proposal_store.release(measurement)
        return "", 204

    reviewed_area = base.get(ReviewedArea, reviewed_area_ids.pkey)
    tile_crops.ensure_crop(reviewed_area)

    return reviewed_area.serialize(), 200


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
          Running count, 95% interval, progress, density over the measured area, and the abundance
          over the habitable area with its uncertainty by source when the survey terms are stored.
          With the terms, the count, interval and density are animals after the overlap factor;
          count_raw is the estimator's own count.
      401:
        description: Unauthorized.
      404:
        description: Survey or active measurement not found.
      500:
        description: Database error.
    """
    survey = base.get(Survey, query.survey_id)
    survey_ids = Keyring(survey.survey_id, survey.uuid)

    measurement = base.execute(activemeasurement.get_active_measurement, survey_ids)

    state = proposal_store.load(measurement)
    terms = proposal_store.load_terms(measurement)

    estimate = base.execute(
        activemeasurement.live_estimate,
        measurement,
        state,
        lambda: proposal_store.vectors(measurement, cast(MeasurementState, state)),
        terms.surveyed_area_m2 if terms else None,
    )
    estimate["abundance"] = base.execute(
        abundance.live_abundance,
        measurement,
        state,
        estimate,
        terms,
        proposal_store.load_boxes(measurement) if terms else None,
    )
    return abundance.apply_overlap(estimate, estimate["abundance"]), 200


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
          Counts of images, predictions, footprints and tiles, the measurement if one exists, the
          number of proposal generations, and the steps with their state.
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

    generations = 0
    if status["measurement"]:
        measurement = base.get(ActiveMeasurement, status["measurement"]["active_measurement_id"])
        state = proposal_store.load(measurement)
        generations = len(state.generations) if state else 0

    status["proposal_generations"] = generations
    status["steps"] = _preparation_steps(status)
    status["ready"] = all(step["done"] for step in status["steps"])

    return status, 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@activeMeasBp.get("/tiles")
@login_required
@permission_required("access")
@validate()
def get_tiles(query: ActiveMeasurementQuery):
    """
    Retrieve the active measurement reviewed areas (eighths) of a survey.
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
        description: List of generations with their label counts (returns empty list if none exist).
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
    """
    Retrieve an active measurement by its integer ID or UUID.
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
    """
    Retrieve all AM units associated with an active measurement.
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
    """
    Create a new active measurement.
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: CreateActiveMeasurement
        description: >
          Active measurement creation payload including survey_ids, label_ids, random_seed, and
          retraining_cadence.
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
    Cut a survey's images into active measurement reviewed areas (eighths).
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: CreateTilesReq
        description: >
          The survey to cut and, optionally, which of its images. Images that already have tiles
          are skipped.
    responses:
      201:
        description: List of the survey's tiles with reviewed_area_id, uuid, image_id and name.
      401:
        description: Unauthorized.
      404:
        description: Survey not found.
      500:
        description: Database error.
    """
    survey = base.get(Survey, body.survey_id)
    survey_ids = Keyring(survey.survey_id, survey.uuid)

    return base.execute(activemeasurement.create_tiles, survey_ids, body.image_ids), 201


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
          Unit order, raw and shaped proposal vectors, the exponent that shaped it, the phase of
          the review it opens, and the labels it was fitted on (or, for a generation of the
          prepared schedule, the units served before it takes over).
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
        description: Unit order or label count conflicts with the stored generations.
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
    return {"generation": proposal.generation, "n_labels": proposal.n_labels}, 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@activeMeasBp.post("/<int:active_measurement_id>/terms")
@activeMeasBp.post("/<uuid:active_measurement_id>/terms")
@login_required
@permission_required("access")
@validate()
def create_terms(body: CreateTermsReq, active_measurement_id: int | UUID):
    """
    Compute and store the terms of an active measurement's abundance, replacing any stored before.
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
        type: CreateTermsReq
        description: >
          Habitable area, and the standard deviation and draws of the surveyed area. The surveyed
          area, the area of each transect, the overlap factor and the representation are computed
          from what is stored, before any review.
    responses:
      201:
        description: Terms stored.
      400:
        description: Validation error or invalid payload.
      401:
        description: Unauthorized.
      404:
        description: Active measurement not found.
      409:
        description: No proposal posted yet, the images have no transect, or a term is out of range.
      500:
        description: Database error.
    """
    measurement = base.get(ActiveMeasurement, active_measurement_id)

    if (state := proposal_store.load(measurement)) is None:
        raise MeasurementBlocked("the measurement has no proposal yet")

    boxes = base.execute(abundance.place_boxes, measurement)

    terms = base.execute(
        abundance.prepare_terms,
        measurement,
        state,
        boxes,
        body.habitable_area_m2,
        body.area_sigma_m2,
        body.area_draws,
    )

    proposal_store.save_boxes(measurement, boxes)
    proposal_store.save_terms(measurement, terms)
    return {
        "boxes_placed": len(boxes),
        "habitable_area_m2": terms.habitable_area_m2,
        "surveyed_area_m2": terms.surveyed_area_m2,
        "transects": dict(zip(terms.transects, terms.transect_areas_m2.tolist())),
        "overlap_factor": terms.overlap_factor,
        "representation_sigma": terms.representation_sigma,
        "n_units": terms.n_units,
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
    Update an active measurement by integer ID or UUID (e.g., retraining cadence).
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
    return base.update(ActiveMeasurement, active_measurement_id, body).serialize(), 200


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@activeMeasBp.delete("/<int:active_measurement_id>")
@activeMeasBp.delete("/<uuid:active_measurement_id>")
@login_required
@permission_required("access")
def delete(active_measurement_id: int | UUID):
    """
    Delete an active measurement by integer ID or UUID.
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
    base.delete(ActiveMeasurement, active_measurement_id)
    return "", 204
