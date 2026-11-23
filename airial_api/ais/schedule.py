# The order units are served in, and the state that serving a unit needs
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# A draw depends on the seed, the proposal in force and the units already drawn; never on the
# counts. Between refits the proposal is fixed, so the serving order up to the next refit is
# known as soon as a generation exists and serving a unit is a lookup.
#
# A generation is in force from the unit after its n_labels. That is how a refit takes over,
# and also how a warm-up ends: generation 0 shaped to draw likely units, and a flatter
# generation that takes over after a set number of units, fitted on nothing new.
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np
from msgpack import packb, unpackb

from .estimator import DEFAULT_EPSILON, _Model
from .proposal import Proposal

# ---------------------------------------------------------------------------------------------------------------------------


def generation_at(proposals: Sequence, step: int) -> int:
    """The generation in force when unit number `step` (1-based) is drawn."""
    return max(p.generation for p in proposals if p.n_labels < step)


def horizon(proposals: Sequence[Proposal], cadence: int) -> int:
    """The number of units that can be served before the next refit is needed."""
    n_units = len(proposals[0].reviewed_area_ids)
    if cadence <= 0:
        return n_units
    return min(n_units, proposals[-1].n_labels + cadence)


def draw_order(
    proposals: Sequence[Proposal],
    seed: int,
    cadence: int,
    epsilon: float = DEFAULT_EPSILON,
) -> list[int]:
    """The reviewed areas in serving order, as far as the stored generations determine it."""
    model = _Model(proposals[0].proposal, seed, epsilon)
    mask = np.ones(model.N)
    order = []

    for step in range(1, horizon(proposals, cadence) + 1):
        model.g = proposals[generation_at(proposals, step)].proposal
        index = model.draw(mask)
        mask[index] = 0
        order.append(proposals[0].reviewed_area_ids[index])

    return order


@dataclass
class Generation:
    """A proposal generation without its vectors."""

    generation: int
    n_labels: int
    model_id: int | None = None
    alpha: float | None = None


@dataclass
class MeasurementState:
    """What serving a unit needs, and no more: its size is fixed by the number of units and does
    not grow with the number of generations. The vectors of every generation stay in storage."""

    reviewed_area_ids: list[int]
    generations: list[Generation]
    order: list[int]
    raw: np.ndarray  # the latest generation's regressor counts, in unit order

    @classmethod
    def build(
        cls, proposals: Sequence[Proposal], seed: int, cadence: int
    ) -> "MeasurementState | None":
        if not proposals:
            return None
        return cls(
            reviewed_area_ids=list(proposals[0].reviewed_area_ids),
            generations=[
                Generation(p.generation, p.n_labels, p.model_id, p.alpha) for p in proposals
            ],
            order=draw_order(proposals, seed, cadence),
            raw=np.asarray(proposals[-1].raw, dtype=float),
        )

    @property
    def n_units(self) -> int:
        return len(self.reviewed_area_ids)

    @property
    def switch_at(self) -> int | None:
        """The units served under generation 0's shape before a differently shaped generation
        took over, or None when the shape has not changed (or is not recorded)."""
        first = self.generations[0].alpha
        for generation in self.generations[1:]:
            if first is not None and generation.alpha is not None and generation.alpha != first:
                return generation.n_labels
        return None

    def generation_at(self, step: int) -> Generation:
        return self.generations[generation_at(self.generations, step)]

    def model_count(self, reviewed_area_id: int) -> float:
        """The regressor's count for a unit that has not been served yet."""
        return float(self.raw[self.reviewed_area_ids.index(reviewed_area_id)])

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def to_cache(self) -> bytes:
        """Packs the state with msgpack for the cache.

        Returns:
            The msgpack bytes of a plain dict: generations as dicts, ``raw``
            as a list.
        """
        return packb(
            {
                "reviewed_area_ids": self.reviewed_area_ids,
                "generations": [asdict(g) for g in self.generations],
                "order": self.order,
                "raw": self.raw.tolist(),
            }
        )

    @classmethod
    def from_cache(cls, data: bytes) -> "MeasurementState":
        """Rebuilds the state from the bytes ``to_cache`` produced.

        Args:
            data: Msgpack bytes from ``to_cache``.

        Returns:
            The state, with ``raw`` as an array and generations as
            ``Generation`` instances.
        """
        fields = unpackb(data)
        return cls(
            reviewed_area_ids=[int(i) for i in fields["reviewed_area_ids"]],
            generations=[Generation(**g) for g in fields["generations"]],
            order=[int(i) for i in fields["order"]],
            raw=np.asarray(fields["raw"], dtype=float),
        )
