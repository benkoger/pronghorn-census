# Finishing an active measurement: its final count stored as animals
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------

from app import proposal_store
from app.extensions import base
from database.modules import abundance, activemeasurement
from database.object_models.project_management.active_measurements import (
    ActiveMeasurement,
    UpdateActiveMeasurement,
)

# ---------------------------------------------------------------------------------------------------------------------------


def store_final_animals(measurement: ActiveMeasurement, state) -> None:
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
