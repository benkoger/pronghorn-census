# Proposal generations for active measurement: the vectors the sampler draws from
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------

import io
from dataclasses import dataclass
from typing import Optional

import numpy as np

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Proposal:
    """One generation of the sampling proposal.

    reviewed_area_ids fixes the unit order the sampler indexes and is identical in every
    generation. raw is the regressor's expected count per unit; proposal is the shaped and
    floored vector units are drawn from. n_labels is the number of reviewed units the
    generation was fitted on (0 for generation 0). model_id is the regression model that
    produced it, when one is registered. alpha is the exponent that shaped the proposal from the
    expected counts: 1 draws units in proportion to the expected count, smaller values flatten
    the proposal so that more of the units drawn are unlikely ones.
    """

    generation: int
    n_labels: int
    reviewed_area_ids: list[int]
    raw: np.ndarray
    proposal: np.ndarray
    model_id: Optional[int] = None
    alpha: Optional[float] = None

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __post_init__(self):
        self.reviewed_area_ids = [int(i) for i in self.reviewed_area_ids]
        self.raw = np.asarray(self.raw, dtype=float)
        self.proposal = np.asarray(self.proposal, dtype=float)

        n = len(self.reviewed_area_ids)
        if n == 0 or len(self.raw) != n or len(self.proposal) != n:
            raise ValueError(
                "reviewed_area_ids, raw and proposal must be non-empty and the same length"
            )
        if len(set(self.reviewed_area_ids)) != n:
            raise ValueError("reviewed_area_ids must be unique")
        if not np.isfinite(self.proposal).all() or (self.proposal < 0).any():
            raise ValueError("proposal must be finite and non-negative")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def to_bytes(self) -> bytes:
        """Serializes the generation as an .npz archive."""
        buffer = io.BytesIO()
        np.savez_compressed(
            buffer,
            generation=self.generation,
            n_labels=self.n_labels,
            reviewed_area_ids=np.asarray(self.reviewed_area_ids, dtype=np.int64),
            raw=self.raw,
            proposal=self.proposal,
            model_id=-1 if self.model_id is None else self.model_id,
            alpha=np.nan if self.alpha is None else self.alpha,
        )
        return buffer.getvalue()

    @classmethod
    def from_bytes(cls, data: bytes) -> "Proposal":
        with np.load(io.BytesIO(data), allow_pickle=False) as archive:
            model_id = int(archive["model_id"])
            alpha = float(archive["alpha"]) if "alpha" in archive.files else np.nan
            return cls(
                generation=int(archive["generation"]),
                n_labels=int(archive["n_labels"]),
                reviewed_area_ids=archive["reviewed_area_ids"].tolist(),
                raw=archive["raw"],
                proposal=archive["proposal"],
                model_id=None if model_id < 0 else model_id,
                alpha=None if np.isnan(alpha) else alpha,
            )


# ---------------------------------------------------------------------------------------------------------------------------


def check_next(stored: list[Proposal], new: Proposal) -> None:
    """Raises ValueError unless `new` is a valid next generation after `stored`."""
    if new.generation != len(stored):
        raise ValueError(f"generation must be {len(stored)}, got {new.generation}")
    if not stored:
        if new.n_labels != 0:
            raise ValueError("generation 0 is fitted before any review; n_labels must be 0")
        return
    if new.reviewed_area_ids != stored[0].reviewed_area_ids:
        raise ValueError("reviewed_area_ids must match generation 0, in order")
    if new.n_labels <= stored[-1].n_labels:
        raise ValueError(f"n_labels must exceed the previous generation's ({stored[-1].n_labels})")
    if new.n_labels >= len(new.reviewed_area_ids):
        raise ValueError("n_labels must be fewer than the units")
