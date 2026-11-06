# Animals seen in more than one image: a weight per placed animal
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# Two animals placed on the ground from different images are the same animal when each is the
# other's nearest in the other image and they lie within the gate set by the two images'
# position accuracy. An animal seen in n other images has weight 1 / (1 + n), so the weights of
# one animal's sightings add up to 1.
#
# Ported from the active-measurement research code (abundance.viewshed_cli_integration,
# _mutual_match_overlap_factors); do not change its arithmetic.
# ---------------------------------------------------------------------------------------------------------------------------

import numpy as np
from scipy.spatial import cKDTree

# ---------------------------------------------------------------------------------------------------------------------------

CONFIDENCE = 0.95  # the gate is the 95% region of the combined position error of two images
CHI2_GATE = -2.0 * np.log(1.0 - CONFIDENCE)
GATE_FLOOR_M = 10.0  # an animal may move this far between two exposures
PRIOR_ONLY_SIGMA_M = 15.0  # position accuracy of an image with none measured

# ---------------------------------------------------------------------------------------------------------------------------


def gate_sigma(gate_m: float) -> float:
    """The position accuracy of two images whose gate is a radius of `gate_m`."""
    return float(gate_m) / float(np.sqrt(2.0 * CHI2_GATE))


def image_sigma(position_sigma_m: np.ndarray) -> np.ndarray:
    """
    Returns the position accuracy the gate uses for each image: the measured one, the prior-only
    value where none was measured, and never below the floor for animal movement.
    """
    sigma = np.asarray(position_sigma_m, dtype=float)
    sigma = np.where(np.isfinite(sigma), sigma, PRIOR_ONLY_SIGMA_M)
    return np.maximum(sigma, gate_sigma(GATE_FLOOR_M))


def overlap_weights(xy_m: np.ndarray, image_of: np.ndarray, sigma_m: np.ndarray) -> np.ndarray:
    """
    Returns the weight of each placed animal. `xy_m` are positions in meters, `image_of` the
    image each was placed from, and `sigma_m` the position accuracy of that image (image_sigma).
    """
    points = np.asarray(xy_m, dtype=float).reshape(-1, 2)
    sigma = np.asarray(sigma_m, dtype=float)
    n = len(points)
    if n == 0:
        return np.zeros(0)

    reach = float(np.sqrt(CHI2_GATE * 2.0) * sigma.max())
    neighbors = cKDTree(points).query_ball_point(points, r=reach)

    # nearest[i] = {image: (j, squared distance)}: the nearest animal to i in each other image
    nearest: list[dict] = [dict() for _ in range(n)]
    for i in range(n):
        for j in neighbors[i]:
            if j == i or image_of[j] == image_of[i]:
                continue
            d2 = float((points[i][0] - points[j][0]) ** 2 + (points[i][1] - points[j][1]) ** 2)
            best = nearest[i].get(image_of[j])
            if best is None or d2 < best[1]:
                nearest[i][image_of[j]] = (j, d2)

    weights = np.ones(n, dtype=float)
    for i in range(n):
        seen_in = 0
        for j, d2 in nearest[i].values():
            if d2 > CHI2_GATE * (sigma[i] ** 2 + sigma[j] ** 2):
                continue
            back = nearest[j].get(image_of[i])
            if back is not None and back[0] == i:
                seen_in += 1
        weights[i] = 1.0 / (1.0 + seen_in)

    return weights
