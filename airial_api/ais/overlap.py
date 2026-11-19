# Animals seen in more than one image: a weight per placed animal
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# An animal is down-weighted by the number of images covering where it stands: placed on the
# ground from one image and inside the footprints of n other images, it has weight 1 / (1 + n),
# so an animal seen by every image covering it adds up to 1 (Koger et al. 2026). No matching
# between images and no radius.
#
# Ported from the active-measurement research code (abundance.viewshed_cli_integration,
# _footprint_cover_factors); do not change its arithmetic.
# ---------------------------------------------------------------------------------------------------------------------------

import numpy as np

# ---------------------------------------------------------------------------------------------------------------------------


def coverage_weights(other_images: np.ndarray) -> np.ndarray:
    """
    Returns the weight of each placed animal. `other_images` is the number of images, other than
    the one it was placed from, whose footprint contains it.
    """
    return 1.0 / (1.0 + np.asarray(other_images, dtype=float))
