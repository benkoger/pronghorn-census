# Representation: how well the flown transects stand for the habitable area
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# The density of a survey is the animals on its transects over the area of its transects. The
# transects are a sample of the habitable area, so another set of transects would have given
# another density. The spread is measured by drawing the transects again, with replacement, and
# taking the density of each draw relative to the observed one.
#
# A survey flown on fewer than MIN_UNITS transects has each transect cut into runs of
# consecutive images, so that enough units are drawn from.
#
# Ported from the active-measurement research code (abundance.tools.representativeness_variance:
# _auto_segment_tracks, _per_psu_area, _ratio_bootstrap); do not change its arithmetic.
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from math import ceil, sqrt
from typing import Hashable, Optional, Sequence

import numpy as np

# ---------------------------------------------------------------------------------------------------------------------------

MIN_UNITS = 10
N_DRAWS = 500
SEED = 0

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Representation:
    """sigma is the relative standard deviation of the density; draws are relative to 1."""

    sigma: float
    draws: np.ndarray
    n_units: int
    coverage: float  # share of the habitable area that was surveyed


# ---------------------------------------------------------------------------------------------------------------------------


def sampling_units(
    transects: Sequence[Hashable],
    image_keys: Sequence[str],
    min_units: int = MIN_UNITS,
) -> list[str]:
    """
    Returns the sampling unit of each image: its transect, or a run of its transect's images
    in key order when the survey has fewer than `min_units` transects.
    """
    labels = [str(t) for t in transects]
    natural = sorted(set(labels))

    if len(natural) >= min_units or not natural:
        return labels

    runs = int(ceil(min_units / len(natural)))
    unit_of: dict[tuple[str, str], str] = {}

    for transect in natural:
        keys = sorted({str(k) for k, t in zip(image_keys, labels) if t == transect})
        if len(keys) <= 1:
            unit_of.update({(transect, key): transect for key in keys})
            continue
        for run, members in enumerate(np.array_split(np.asarray(keys, dtype=object), runs)):
            unit_of.update({(transect, key): f"{transect}__seg{run:02d}" for key in members})

    return [unit_of[(t, str(k))] for t, k in zip(labels, image_keys)]


def unit_totals(units: Sequence[str], values: Sequence[float]) -> tuple[list[str], np.ndarray]:
    """
    Returns the units in label order and the total of `values` over each, summed with
    compensation as the research code's totals are.
    """
    totals: dict[str, float] = {}
    lost: dict[str, float] = {}

    for unit, value in zip(units, values):
        total = totals.get(unit, 0.0)
        step = float(value) - lost.get(unit, 0.0)
        totals[unit] = total + step
        lost[unit] = (totals[unit] - total) - step

    labels = sorted(totals)
    return labels, np.asarray([totals[label] for label in labels], dtype=float)


def unit_areas(labels: Sequence[str], transect_areas: dict[str, float]) -> np.ndarray:
    """
    Returns the area of each unit: its transect's area, shared equally between the runs the
    transect was cut into. NaN for a unit whose transect has no area.
    """
    parents = [label.split("__seg")[0] for label in labels]
    runs = {parent: parents.count(parent) for parent in set(parents)}

    return np.asarray(
        [
            transect_areas[parent] / runs[parent] if parent in transect_areas else np.nan
            for parent in parents
        ],
        dtype=float,
    )


# ---------------------------------------------------------------------------------------------------------------------------


def representation(
    totals: np.ndarray,
    areas: np.ndarray,
    surveyed_area_m2: float,
    habitable_area_m2: float,
    n_draws: int = N_DRAWS,
    seed: int = SEED,
) -> Optional[Representation]:
    """
    Returns the representation of units with `totals` animals on `areas` square meters, or None
    when fewer than two units have an area or no animals are on them. The spread shrinks with
    the share of the habitable area that was surveyed.
    """
    known = np.isfinite(areas)
    totals, areas = np.asarray(totals, dtype=float)[known], np.asarray(areas, dtype=float)[known]
    n = len(totals)

    if n < 2 or not areas.sum() > 0 or not habitable_area_m2 > 0:
        return None

    observed = float(totals.sum()) / float(areas.sum())
    if not np.isfinite(observed) or observed <= 0:
        return None

    coverage = min(1.0, surveyed_area_m2 / habitable_area_m2)
    scale = sqrt(max(0.0, 1.0 - coverage))

    rng = np.random.default_rng(seed)
    draws = np.full(n_draws, np.nan)
    for b in range(n_draws):
        drawn = rng.integers(0, n, size=n)
        area = float(areas[drawn].sum())
        if area > 0 and np.isfinite(area):
            draws[b] = observed + scale * (float(totals[drawn].sum()) / area - observed)

    draws = draws[np.isfinite(draws)] / observed
    if len(draws) < 2:
        return None

    return Representation(
        sigma=float(np.std(draws, ddof=1)),
        draws=draws,
        n_units=n,
        coverage=coverage,
    )
