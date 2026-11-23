# The active-measurement estimator, replayable from the review log
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
#
# A estimator is the AIS estimator over one survey's tiles. Its state is a pure function of the
# review log: for every reviewed tile, the proposal vector in force at the draw and the human
# count. That is what makes it serve a web application, where the estimator cannot live in
# memory across a user's annotation estimator; the server stores the log and rebuilds the estimator
# from it on every request.
#
#     estimator = Estimator(unit_ids, g0, seed=6)
#     unit = estimator.next_unit()                 # the tile to review, drawn ∝ max(g, ε)
#     estimator.record(unit, human_count=2)        # append; the estimate updates
#     est = estimator.estimate()                   # Estimate(count, ci95_half, n_reviewed, ...)
#     estimator.set_proposal(g1)                   # after a refit; generation 1 from here on
#     ...
#     log = estimator.log()                        # the rows the server stores
#     Estimator.replay(unit_ids, proposals, log)   # identical state, from storage
#
# Sampling is without replacement. The proposal is floored at ε so no tile has zero mass. The
# estimate is the sqrt-weighted LURE combination (the paper's COMB estimator); the arithmetic is
# the vendored active-measurement code, untouched.
# ---------------------------------------------------------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from .ais import AIS
from .importance_sampling_update import ImportanceSamplingUpdate

DEFAULT_EPSILON = 0.001
Z95 = 1.959963985


@dataclass(frozen=True)
class Estimate:
    count: float
    std_error: float
    n_reviewed: int
    generation: int            # proposal generation in force

    @property
    def ci95_half(self) -> float:
        return Z95 * self.std_error

    @property
    def rel_ci(self) -> float:
        return self.ci95_half / self.count if self.count > 0 else float("inf")


@dataclass(frozen=True)
class LogRow:
    """One reviewed unit, in review order. `generation` is the proposal in force at the draw."""
    step: int
    unit_id: str
    generation: int
    human_count: float
    model_count: float          # the proposal for this unit at the draw
    count: float                # running estimate after this unit
    ci95_half: float


class _Model:
    """The adapter the vendored AIS expects: g, f, N, sample_index. f is filled as counts arrive."""

    def __init__(self, g: np.ndarray, seed: int, epsilon: float):
        self.g = np.asarray(g, dtype=float)
        self.N = len(self.g)
        self.f = np.full(self.N, np.nan)
        self.epsilon = float(epsilon)
        self.random_state = np.random.RandomState(seed)
        self._forced: Optional[int] = None  # the unit `step` must return (drawn or replayed)

    def probs(self, mask, epsilon=None) -> np.ndarray:
        eps = self.epsilon if epsilon is None else float(epsilon)
        p = np.asarray(mask, dtype=float) * np.maximum(self.g, eps)
        return p / p.sum()

    def draw(self, mask) -> int:
        return int(self.random_state.choice(np.arange(self.N), p=self.probs(mask)))

    def sample_index(self, mask, epsilon=None):
        """Called by the vendored AIS.step. The unit was fixed by `draw` or `replay`; the proposal
        vector returned here is what the estimator records for this step."""
        probs = self.probs(mask, epsilon)
        if self._forced is None:
            raise RuntimeError("sample_index called without a pending unit")
        index, self._forced = self._forced, None
        return index, probs, self.f[index]

    def train(self, mask=None):
        return False


class Estimator:
    def __init__(self, unit_ids: Sequence[str], proposal: np.ndarray, *, seed: int = 0,
                 epsilon: float = DEFAULT_EPSILON):
        self.unit_ids = [str(u) for u in unit_ids]
        if len(set(self.unit_ids)) != len(self.unit_ids):
            raise ValueError("unit_ids must be unique")
        if len(proposal) != len(self.unit_ids):
            raise ValueError(f"proposal has {len(proposal)} entries for {len(self.unit_ids)} units")
        self._index = {u: i for i, u in enumerate(self.unit_ids)}
        self._model = _Model(proposal, seed, epsilon)
        self._algo = AIS(
            self._model, ImportanceSamplingUpdate(update_weighting="LURE"), swor=True, m=1
        )
        self._proposals: list[np.ndarray] = [np.asarray(proposal, dtype=float).copy()]
        self._log: list[LogRow] = []
        self._pending: Optional[int] = None

    # ---- the two calls a review loop makes -------------------------------------------------
    @property
    def n_units(self) -> int:
        return self._model.N

    @property
    def n_reviewed(self) -> int:
        return len(self._log)

    @property
    def n_remaining(self) -> int:
        return int(self._algo.mask.sum())

    @property
    def generation(self) -> int:
        return len(self._proposals) - 1

    def next_unit(self) -> str:
        """Draw the next tile to review. Idempotent until `record` is called for it."""
        if self._pending is None:
            if self.n_remaining < 1:
                raise RuntimeError("pool exhausted")
            self._pending = self._model.draw(self._algo.mask)
        return self.unit_ids[self._pending]

    def record(self, unit_id: str, human_count: float) -> Estimate:
        """Record the reviewed count for `unit_id` and update the estimate.

        `unit_id` is normally the one `next_unit` returned. Any unreviewed unit is accepted, so a
        reviewer who skips ahead, or a replay, still yields a valid (if differently weighted)
        estimator step: the proposal recorded for the step is the one in force now.
        """
        idx = self._index[str(unit_id)]
        if self._algo.mask[idx] == 0:
            raise ValueError(f"unit {unit_id} already reviewed")
        self._model.f[idx] = float(human_count)
        self._model._forced = idx
        self._pending = None
        latest = self._algo.e.estimate() if self._algo.e.N > 0 else 0
        self._algo.step(latest_mean=latest)
        est = self.estimate()
        self._log.append(LogRow(step=len(self._log) + 1, unit_id=str(unit_id),
                                generation=self.generation, human_count=float(human_count),
                                model_count=float(self._model.g[idx]),
                                count=est.count, ci95_half=est.ci95_half))
        return est

    def set_proposal(self, proposal: np.ndarray) -> int:
        """Install a refit proposal; returns its generation number."""
        proposal = np.asarray(proposal, dtype=float)
        if proposal.shape != self._model.g.shape:
            raise ValueError(f"proposal shape {proposal.shape} != {self._model.g.shape}")
        self._model.g = proposal.copy()
        self._proposals.append(proposal.copy())
        return self.generation

    def estimate(self) -> Estimate:
        if self._algo.e.N == 0:
            return Estimate(float("nan"), float("nan"), 0, self.generation)
        count, var = self._algo.sqrt_lure_mixer()
        return Estimate(
            float(count), float(np.sqrt(max(var, 0.0))), self.n_reviewed, self.generation
        )

    # ---- storage -----------------------------------------------------------------------------
    def log(self) -> list[LogRow]:
        return list(self._log)

    def proposals(self) -> list[np.ndarray]:
        return [p.copy() for p in self._proposals]

    def reviewed_units(self) -> list[str]:
        return [r.unit_id for r in self._log]

    def advance(self, proposals: Sequence[np.ndarray], log: Sequence[LogRow]) -> "Estimator":
        """Apply the rows of `log` beyond those already recorded, installing each proposal
        generation as the rows call for it. `log` must start with the rows already recorded."""
        for row in log[self.n_reviewed:]:
            while self.generation < row.generation:
                self.set_proposal(proposals[self.generation + 1])
            self._model.draw(self._algo.mask)  # advance the RNG exactly as the live draw did
            self.record(row.unit_id, row.human_count)
        return self

    def extends(self, log: Sequence[LogRow]) -> bool:
        """True when `log` starts with exactly the units and counts this estimator has recorded."""
        if len(log) < self.n_reviewed:
            return False
        return all(mine.unit_id == str(row.unit_id) and mine.human_count == float(row.human_count)
                   and mine.generation == row.generation for mine, row in zip(self._log, log))

    @classmethod
    def replay(cls, unit_ids: Sequence[str], proposals: Sequence[np.ndarray], log: Sequence[LogRow],
               *, seed: int = 0, epsilon: float = DEFAULT_EPSILON) -> "Estimator":
        """Rebuild a estimator from stored proposals and the review log.

        The estimator state after replay is identical to the live estimator's because it depends
        only on (proposal in force, unit, count) per step. The random state is advanced by one
        draw per logged unit, as the live estimator's was, so a replayed estimator and the live
        one also agree on the next unit to review. A logged unit that differs from the draw
        (a reviewer who skipped ahead) is honored as logged.
        """
        s = cls(unit_ids, proposals[0], seed=seed, epsilon=epsilon).advance(proposals, log)
        while s.generation < len(proposals) - 1:
            s.set_proposal(proposals[s.generation + 1])
        return s
