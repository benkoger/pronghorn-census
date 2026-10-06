# Overall abundance for active measurement: count over surveyed area, scaled to the habitable area
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# abundance = (overlap factor x estimated count / surveyed area) x habitable area
#
# Three sources of uncertainty are reported, each alone and then together:
#   count           the sampler's choice of which units were reviewed
#   area            the surveyed area, from the georeferencing of the images
#   representation  the flown transects being a sample of the habitable area
#
# The survey's terms are set when the survey is prepared. The area's do not change. The overlap
# factor and the representation start from the proposal's expected counts and are taken from the
# review once units have been reviewed.
# ---------------------------------------------------------------------------------------------------------------------------

import io
from dataclasses import dataclass, field
from statistics import NormalDist
from typing import Any, Optional

import numpy as np

# ---------------------------------------------------------------------------------------------------------------------------

Z95 = 1.959963985
SEED = 0
MIN_DRAWS = 2

_normal = NormalDist()

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class SurveyTerms:
    """The terms of a survey's abundance.

    surveyed_area_m2 is the ground covered by the survey's images and transect_areas_m2 the
    ground covered by each of `transects`. area_sigma_m2 is the standard deviation of the
    surveyed area and area_draws are draws of it, when the georeferencing produced them.
    overlap_factor scales the estimated count to animals, correcting for animals seen in more
    than one image. representation_sigma is the relative standard deviation of the density
    between transects, representation_draws are the relative draws of it (mean near 1), and
    n_units is the number of units the draws were taken from.
    """

    habitable_area_m2: float
    surveyed_area_m2: float
    area_sigma_m2: float = 0.0
    area_draws: np.ndarray = field(default_factory=lambda: np.zeros(0))
    transects: list[str] = field(default_factory=list)
    transect_areas_m2: np.ndarray = field(default_factory=lambda: np.zeros(0))
    overlap_factor: float = 1.0
    representation_sigma: float = 0.0
    representation_draws: np.ndarray = field(default_factory=lambda: np.zeros(0))
    n_units: int = 0

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __post_init__(self):
        self.area_draws = np.asarray(self.area_draws, dtype=float)
        self.representation_draws = np.asarray(self.representation_draws, dtype=float)
        self.transect_areas_m2 = np.asarray(self.transect_areas_m2, dtype=float)
        self.transects = [str(transect) for transect in self.transects]

        if not self.habitable_area_m2 > 0:
            raise ValueError("habitable_area_m2 must be positive")
        if not self.surveyed_area_m2 > 0:
            raise ValueError("surveyed_area_m2 must be positive")
        if len(self.transects) != len(self.transect_areas_m2):
            raise ValueError("transects and transect_areas_m2 must be the same length")
        if not 0 < self.overlap_factor <= 1:
            raise ValueError("overlap_factor must be above 0 and at most 1")
        if self.area_sigma_m2 < 0 or self.representation_sigma < 0:
            raise ValueError("area_sigma_m2 and representation_sigma must not be negative")
        for draws in (self.area_draws, self.representation_draws):
            if not np.isfinite(draws).all() or (draws <= 0).any():
                raise ValueError("draws must be finite and positive")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def to_bytes(self) -> bytes:
        """Serializes the terms as an .npz archive."""
        buffer = io.BytesIO()
        np.savez_compressed(
            buffer,
            habitable_area_m2=self.habitable_area_m2,
            surveyed_area_m2=self.surveyed_area_m2,
            area_sigma_m2=self.area_sigma_m2,
            area_draws=self.area_draws,
            transects=np.asarray(self.transects, dtype=str),
            transect_areas_m2=self.transect_areas_m2,
            overlap_factor=self.overlap_factor,
            representation_sigma=self.representation_sigma,
            representation_draws=self.representation_draws,
            n_units=self.n_units,
        )
        return buffer.getvalue()

    @classmethod
    def from_bytes(cls, data: bytes) -> "SurveyTerms":
        with np.load(io.BytesIO(data), allow_pickle=False) as archive:
            return cls(
                habitable_area_m2=float(archive["habitable_area_m2"]),
                surveyed_area_m2=float(archive["surveyed_area_m2"]),
                area_sigma_m2=float(archive["area_sigma_m2"]),
                area_draws=archive["area_draws"],
                transects=archive["transects"].tolist(),
                transect_areas_m2=archive["transect_areas_m2"],
                overlap_factor=float(archive["overlap_factor"]),
                representation_sigma=float(archive["representation_sigma"]),
                representation_draws=archive["representation_draws"],
                n_units=int(archive["n_units"]),
            )


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class PlacedBoxes:
    """The detector's boxes of a survey placed on the ground, highest score first.

    image_ids and reviewed_area_ids are the image and the unit each box is on, east_m and
    north_m its position in meters. The boxes and their positions do not change during a
    measurement, so they are placed once, when the survey is prepared.
    """

    image_ids: np.ndarray
    reviewed_area_ids: np.ndarray
    scores: np.ndarray
    east_m: np.ndarray
    north_m: np.ndarray

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __post_init__(self):
        self.image_ids = np.asarray(self.image_ids, dtype=np.int64)
        self.reviewed_area_ids = np.asarray(self.reviewed_area_ids, dtype=np.int64)
        self.scores = np.asarray(self.scores, dtype=float)
        self.east_m = np.asarray(self.east_m, dtype=float)
        self.north_m = np.asarray(self.north_m, dtype=float)

        fields = (self.image_ids, self.reviewed_area_ids, self.scores, self.east_m, self.north_m)
        if {len(v) for v in fields} != {len(self.image_ids)}:
            raise ValueError("every field of the placed boxes must be the same length")

    def __len__(self) -> int:
        return len(self.image_ids)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def to_bytes(self) -> bytes:
        """Serializes the boxes as an .npz archive."""
        buffer = io.BytesIO()
        np.savez_compressed(
            buffer,
            image_ids=self.image_ids,
            reviewed_area_ids=self.reviewed_area_ids,
            scores=self.scores,
            east_m=self.east_m,
            north_m=self.north_m,
        )
        return buffer.getvalue()

    @classmethod
    def from_bytes(cls, data: bytes) -> "PlacedBoxes":
        with np.load(io.BytesIO(data), allow_pickle=False) as archive:
            return cls(**{name: archive[name] for name in archive.files})


# ---------------------------------------------------------------------------------------------------------------------------


def bias_corrected_interval(draws: np.ndarray, observed: float) -> Optional[tuple[float, float]]:
    """
    Returns the bias-corrected 95% percentile interval of `draws` around `observed`, or None
    with fewer than MIN_DRAWS finite draws.
    """
    draws = draws[np.isfinite(draws)]
    if len(draws) < MIN_DRAWS:
        return None

    below = min(max(float(np.mean(draws < observed)), 1e-6), 1.0 - 1e-6)
    shift = 2.0 * _normal.inv_cdf(below)

    lower = float(np.quantile(draws, _normal.cdf(shift - Z95)))
    upper = float(np.quantile(draws, _normal.cdf(shift + Z95)))
    return lower, upper


def _interval(abundance: float, *relative_sigmas: float) -> list[float]:
    """The symmetric 95% interval of `abundance` for independent relative standard deviations."""
    half = Z95 * float(np.sqrt(sum(s * s for s in relative_sigmas))) * abundance
    return [max(0.0, abundance - half), abundance + half]


def _draws(
    count: float,
    count_sigma: float,
    area_m2: float,
    terms: SurveyTerms,
) -> Optional[np.ndarray]:
    """
    Draws of the abundance with every source varying: the representation draws scale the
    count, the sampler adds to it, and the result is divided by a draw of the surveyed area.
    """
    n = len(terms.representation_draws)
    if n < MIN_DRAWS:
        return None

    rng = np.random.default_rng(SEED)
    sampler = rng.normal(0.0, count_sigma, n) if count_sigma > 0 else np.zeros(n)
    area = (
        rng.normal(area_m2, terms.area_sigma_m2, n)
        if terms.area_sigma_m2 > 0
        else np.full(n, area_m2)
    )

    if len(terms.area_draws) >= MIN_DRAWS:
        scale = area_m2 / max(float(np.median(terms.area_draws)), 1.0)
        area = rng.choice(terms.area_draws, n, replace=True) * scale

    area = np.clip(area, 1.0, None)
    return (count * terms.representation_draws + sampler) / area * terms.habitable_area_m2


# ---------------------------------------------------------------------------------------------------------------------------


def overall_abundance(
    count: float,
    std_error: float,
    terms: SurveyTerms,
    prepared: Optional[SurveyTerms] = None,
) -> Optional[dict[str, Any]]:
    """
    Returns the abundance over the habitable area with its 95% interval, and the count, the
    surveyed area and the representation each with its own uncertainty. `count` and `std_error`
    are the estimator's, before the overlap factor. `prepared` are the terms before any review,
    reported beside those in use. None when the count is not positive.
    """
    if not (count > 0 and np.isfinite(std_error)):
        return None

    prepared = prepared or terms
    area_m2 = terms.surveyed_area_m2

    animals = terms.overlap_factor * count
    animals_sigma = terms.overlap_factor * std_error
    abundance = animals / area_m2 * terms.habitable_area_m2

    relative = {
        "count": animals_sigma / animals,
        "area": terms.area_sigma_m2 / area_m2,
        "representation": terms.representation_sigma,
    }

    interval = _interval(abundance, *relative.values())
    sigma = float(np.sqrt(sum(s * s for s in relative.values()))) * abundance

    if (draws := _draws(animals, animals_sigma, area_m2, terms)) is not None:
        if corrected := bias_corrected_interval(draws, abundance):
            interval = [max(0.0, corrected[0]), corrected[1]]  # an abundance is never negative
            sigma = float(np.std(draws, ddof=1))

    return {
        "abundance": abundance,
        "ci_lower": interval[0],
        "ci_upper": interval[1],
        "sigma": sigma,
        "habitable_area_m2": terms.habitable_area_m2,
        "overlap_factor": terms.overlap_factor,
        "overlap_factor_prepared": prepared.overlap_factor,
        "count": {
            "value": animals,
            "sigma": animals_sigma,
            "relative_sigma": relative["count"],
            "abundance_interval": _interval(abundance, relative["count"]),
        },
        "area": {
            "value_m2": area_m2,
            "sigma_m2": terms.area_sigma_m2,
            "relative_sigma": relative["area"],
            "abundance_interval": _interval(abundance, relative["area"]),
        },
        "representation": {
            "n_transects": len(terms.transects),
            "n_units": terms.n_units,
            "sigma": terms.representation_sigma * animals,
            "relative_sigma": relative["representation"],
            "relative_sigma_prepared": prepared.representation_sigma,
            "abundance_interval": _interval(abundance, relative["representation"]),
        },
    }
