"""Flip rate and the statistics that make it readable.

The headline number is **flip rate**: the fraction of pairs where the model is correct on
*both* members. What makes it informative is not the number itself but its comparison to
what independent errors would predict — that gap is the shortcut signal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Interval:
    lo: float
    hi: float

    def __str__(self) -> str:
        return f"[{self.lo:.3f}, {self.hi:.3f}]"


def wilson_interval(successes: int, n: int, z: float = 1.96) -> Interval:
    """95% CI for a proportion, Wilson score method.

    Wilson rather than normal-approximation because flip rates land near 0 and near 1 often
    enough that the normal interval produces bounds outside [0, 1] — which then get quietly
    clipped and misreported as certainty.
    """
    if n == 0:
        return Interval(0.0, 1.0)
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    lo, hi = centre - half, centre + half
    # Snap float dust at the boundaries: at p=1 the algebra gives 0.9999999999999999, which
    # reads as "not quite certain" when it is exactly the boundary.
    lo = 0.0 if lo < 1e-9 else lo
    hi = 1.0 if hi > 1 - 1e-9 else hi
    return Interval(max(0.0, lo), min(1.0, hi))


@dataclass
class FlipRateResult:
    """Everything needed to read a flip-rate measurement, per family and overall."""

    n_pairs: int
    n_both_correct: int
    canonical_correct: int
    perturbed_correct: int
    n_consistent_same_answer: int  # picked the SAME option on both members — the shortcut signature
    per_family: dict[str, FlipRateResult] = field(default_factory=dict)

    @property
    def flip_rate(self) -> float:
        """Fraction of pairs answered correctly on both members. Chance = 0.25."""
        return self.n_both_correct / self.n_pairs if self.n_pairs else 0.0

    @property
    def canonical_accuracy(self) -> float:
        return self.canonical_correct / self.n_pairs if self.n_pairs else 0.0

    @property
    def perturbed_accuracy(self) -> float:
        return self.perturbed_correct / self.n_pairs if self.n_pairs else 0.0

    @property
    def expected_flip_rate_if_independent(self) -> float:
        """What flip rate would be if the two errors were independent.

        The reference point that makes the headline number mean something: a model whose
        mistakes are unrelated across the pair should hit roughly this value.
        """
        return self.canonical_accuracy * self.perturbed_accuracy

    @property
    def shortcut_gap(self) -> float:
        """Expected minus observed flip rate.

        Large positive gap = the model's two answers are coupled, i.e. it is answering from
        the surface form that both members share rather than from the fact that differs.
        This is the quantity that a plain accuracy benchmark cannot see.
        """
        return self.expected_flip_rate_if_independent - self.flip_rate

    @property
    def stickiness(self) -> float:
        """Fraction of pairs where the model gave the same option to both members.

        A perfectly reasoning model scores 0. A model that ignores the perturbation entirely
        scores 1. Unlike flip rate, this is well defined even when accuracy is at chance.
        """
        return self.n_consistent_same_answer / self.n_pairs if self.n_pairs else 0.0

    def flip_rate_ci(self) -> Interval:
        return wilson_interval(self.n_both_correct, self.n_pairs)

    def as_dict(self) -> dict:
        return {
            "n_pairs": self.n_pairs,
            "flip_rate": round(self.flip_rate, 4),
            "flip_rate_ci": [round(self.flip_rate_ci().lo, 4), round(self.flip_rate_ci().hi, 4)],
            "canonical_accuracy": round(self.canonical_accuracy, 4),
            "perturbed_accuracy": round(self.perturbed_accuracy, 4),
            "expected_flip_rate_if_independent": round(
                self.expected_flip_rate_if_independent, 4
            ),
            "shortcut_gap": round(self.shortcut_gap, 4),
            "stickiness": round(self.stickiness, 4),
            "chance_flip_rate": 0.25,
            "per_family": {k: v.as_dict() for k, v in self.per_family.items()},
        }


def score_pairs(records: list[dict]) -> FlipRateResult:
    """Aggregate per-item scoring records into a flip-rate result.

    Each record must carry: ``pair_id``, ``family``, ``variant``, ``chosen_index``,
    ``correct_index``.
    """
    by_pair: dict[str, dict[str, dict]] = {}
    for rec in records:
        by_pair.setdefault(rec["pair_id"], {})[rec["variant"]] = rec

    families: dict[str, list[tuple[dict, dict]]] = {}
    complete: list[tuple[dict, dict]] = []
    for pair_id, members in by_pair.items():
        if "canonical" not in members or "perturbed" not in members:
            raise ValueError(f"pair {pair_id} is incomplete — both variants must be scored")
        entry = (members["canonical"], members["perturbed"])
        complete.append(entry)
        families.setdefault(members["canonical"]["family"], []).append(entry)

    def tally(entries: list[tuple[dict, dict]]) -> FlipRateResult:
        both = can = per = same = 0
        for c, p in entries:
            c_ok = c["chosen_index"] == c["correct_index"]
            p_ok = p["chosen_index"] == p["correct_index"]
            can += c_ok
            per += p_ok
            both += c_ok and p_ok
            same += c["chosen_index"] == p["chosen_index"]
        return FlipRateResult(
            n_pairs=len(entries),
            n_both_correct=both,
            canonical_correct=can,
            perturbed_correct=per,
            n_consistent_same_answer=same,
        )

    overall = tally(complete)
    overall.per_family = {name: tally(entries) for name, entries in sorted(families.items())}
    return overall
