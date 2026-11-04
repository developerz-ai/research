"""Trivial-heuristic baselines.

An item family is only a reasoning test if no cheap heuristic passes it. That is not
something to assert in a docstring — it is something to measure, on the same item set, every
run.

This module exists because E001 seed 0 caught a broken family the hard way: ``role_swap``
perturbed by swapping two names, which also swapped their positions, so "answer the
last-named entity" scored a **0.98 flip rate**. It inflated the headline number and looked
like a small model reasoning well. Running these baselines alongside every evaluation makes
that class of mistake visible immediately rather than after a writeup.

Read the output as a ceiling on triviality: **any family where a heuristic scores well above
chance (0.25) is not measuring reasoning**, and a model's score there says nothing.

That contract is enforced, not remembered: ``geom eval`` and ``geom sweep`` refuse to score a
population where any family's best heuristic exceeds ``ADMISSIBLE_CEILING`` — nonzero exit,
no model load, no run record. ``geom baselines`` prints the full table on demand and
itself exits nonzero when a family crosses the ceiling — it is how you read the numbers
behind a refusal.
"""

from __future__ import annotations

from collections.abc import Callable

from .items import Item
from .metrics import FlipRateResult, score_pairs

# The preregistered admissibility line (E001, 2026-08-11): a family whose best
# trivial-heuristic flip rate exceeds this is not measuring reasoning, and every number
# taken on it is discarded. Defined here ONCE — `geom baselines`, `geom eval`, `geom sweep`
# and the tests import it; there is no second literal.
ADMISSIBLE_CEILING = 0.40

# A heuristic returns a chosen option index, or None if it does not apply to this item.
Heuristic = Callable[[Item], int | None]


def always_first(item: Item) -> int:
    """Constant answer. Scores exactly 0 by construction — the sanity anchor."""
    return 0


def last_mentioned_entity(item: Item) -> int | None:
    """Pick whichever option string appears latest in the prompt.

    The single most powerful shortcut on entity-based items, and the one small LMs default
    to. Does not apply to yes/no families, where neither option appears in the prompt.
    """
    positions = [item.prompt.rfind(option.strip()) for option in item.options]
    if min(positions) < 0 or positions[0] == positions[1]:
        return None
    return int(max(range(2), key=lambda i: positions[i]))


def first_mentioned_entity(item: Item) -> int | None:
    """Primacy, the mirror of recency. Included so neither position is left unchecked."""
    positions = [item.prompt.find(option.strip()) for option in item.options]
    if min(positions) < 0 or positions[0] == positions[1]:
        return None
    return int(min(range(2), key=lambda i: positions[i]))


def always_yes(item: Item) -> int | None:
    """Affirmation bias on yes/no families."""
    for index, option in enumerate(item.options):
        if option.strip().lower() == "yes":
            return index
    return None


def largest_number(item: Item) -> int | None:
    """Pick the numerically larger option, for arithmetic items."""
    try:
        values = [float(option.strip()) for option in item.options]
    except ValueError:
        return None
    return int(max(range(2), key=lambda i: values[i]))


HEURISTICS: dict[str, Heuristic] = {
    "always_first_option": always_first,
    "last_mentioned_entity": last_mentioned_entity,
    "first_mentioned_entity": first_mentioned_entity,
    "always_yes": always_yes,
    "largest_number": largest_number,
}


def score_heuristic(items: list[Item], heuristic: Heuristic) -> FlipRateResult | None:
    """Score one heuristic over the items it applies to.

    A heuristic is scored only on **complete pairs** where it applies to both members —
    scoring half a pair would understate the shortcut.
    """
    choices: dict[str, dict[str, int]] = {}
    for item in items:
        chosen = heuristic(item)
        if chosen is None:
            continue
        choices.setdefault(item.pair_id, {})[item.variant] = chosen

    records = []
    by_id = {item.pair_id: [] for item in items}
    for item in items:
        by_id[item.pair_id].append(item)

    for pair_id, per_variant in choices.items():
        if len(per_variant) != 2:
            continue
        for item in by_id[pair_id]:
            records.append(
                {
                    "pair_id": pair_id,
                    "family": item.family,
                    "variant": item.variant,
                    "chosen_index": per_variant[item.variant],
                    "correct_index": item.correct_index,
                }
            )
    return score_pairs(records) if records else None


def score_all(items: list[Item]) -> dict[str, FlipRateResult]:
    """Score every heuristic. Names that do not apply anywhere are omitted."""
    results = {}
    for name, heuristic in HEURISTICS.items():
        result = score_heuristic(items, heuristic)
        if result is not None:
            results[name] = result
    return results


def worst_case_per_family(items: list[Item]) -> dict[str, tuple[str, float]]:
    """For each family, the best-scoring heuristic and its flip rate.

    This is the number that decides whether a family is admissible. Well above chance
    (0.25) means the family is solvable without reasoning and its results must be
    discarded, not merely caveated.
    """
    per_family: dict[str, tuple[str, float]] = {}
    for name, result in score_all(items).items():
        for family, sub in result.per_family.items():
            best = per_family.get(family)
            if best is None or sub.flip_rate > best[1]:
                per_family[family] = (name, sub.flip_rate)
    return per_family


def admissibility_violations(items: list[Item]) -> dict[str, tuple[str, float]]:
    """Families whose best-heuristic flip rate exceeds ``ADMISSIBLE_CEILING``.

    The enforced form of :func:`worst_case_per_family`: ``geom eval`` and ``geom sweep``
    call this on the exact population about to be measured and refuse to run when it is
    non-empty, so a family a heuristic can ace never reaches a run record.
    """
    return {
        family: worst
        for family, worst in worst_case_per_family(items).items()
        if worst[1] > ADMISSIBLE_CEILING
    }
