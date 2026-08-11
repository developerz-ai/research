"""Admissibility: no trivial heuristic may pass any item family.

This is the guard for the mistake E001 seed 0 caught. The original ``role_swap`` perturbed
by swapping two names, which also swapped their positions — so "answer the last-named
entity" scored a 0.98 flip rate and looked like a 124M model reasoning well.

Any new family must pass these tests before its numbers mean anything.
"""

from __future__ import annotations

import pytest

from geomreason import baselines
from geomreason import items as item_gen

CHANCE = 0.25
# A heuristic at chance is unavoidable; well above it means the family is solvable without
# reasoning. 0.40 is the preregistered line.
ADMISSIBLE_CEILING = 0.40


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_no_heuristic_beats_chance_on_any_family(seed: int) -> None:
    flat = item_gen.flatten(item_gen.generate(n_per_family=100, seed=seed))
    for name, result in baselines.score_all(flat).items():
        for family, sub in result.per_family.items():
            assert sub.flip_rate <= ADMISSIBLE_CEILING, (
                f"{family} is solvable by {name} at flip rate {sub.flip_rate:.3f} — "
                "it is not a reasoning test"
            )


def test_every_family_is_admissible() -> None:
    flat = item_gen.flatten(item_gen.generate(n_per_family=100, seed=0))
    worst = baselines.worst_case_per_family(flat)
    for family in item_gen.FAMILIES:
        if family in worst:
            name, rate = worst[family]
            assert rate <= ADMISSIBLE_CEILING, f"{family} passed by {name} at {rate:.3f}"


def test_constant_heuristic_scores_exactly_zero() -> None:
    """The anchor: per-pair answer balance makes a constant answer score exactly 0."""
    flat = item_gen.flatten(item_gen.generate(n_per_family=50, seed=0))
    result = baselines.score_heuristic(flat, baselines.always_first)
    assert result is not None
    assert result.flip_rate == 0.0
    assert result.stickiness == 1.0


def test_recency_heuristic_applies_to_entity_families_only() -> None:
    """Sanity check on the heuristic itself — it must actually fire where it should.

    A heuristic that silently applies nowhere would pass the admissibility test while
    checking nothing.
    """
    flat = item_gen.flatten(item_gen.generate(n_per_family=20, seed=0))
    result = baselines.score_heuristic(flat, baselines.last_mentioned_entity)
    assert result is not None
    assert set(result.per_family) == {"comparison", "role_swap", "transitive"}
    assert result.n_pairs == 60


def test_recency_would_have_caught_the_old_role_swap() -> None:
    """Regression test reconstructing the broken design.

    Swapping the names (rather than reversing the verb) puts the correct answer in the
    last-mentioned position in *both* members, so recency scores a perfect flip rate. If
    someone reintroduces that pattern, this test documents exactly why it is wrong.
    """
    broken = [
        item_gen.Item(
            prompt="Alice gave the book to Bob. Question: who has the book now? Answer:",
            options=(" Alice", " Bob"), correct_index=1,
            family="role_swap_broken", variant="canonical", pair_id="x-0",
        ),
        item_gen.Item(
            prompt="Bob gave the book to Alice. Question: who has the book now? Answer:",
            options=(" Alice", " Bob"), correct_index=0,
            family="role_swap_broken", variant="perturbed", pair_id="x-0",
        ),
    ]
    result = baselines.score_heuristic(broken, baselines.last_mentioned_entity)
    assert result is not None
    assert result.flip_rate == 1.0, "recency should ace the broken design — that was the bug"

    fixed = item_gen.generate(n_per_family=50, seed=0, families=["role_swap"])
    fixed_result = baselines.score_heuristic(
        item_gen.flatten(fixed), baselines.last_mentioned_entity
    )
    assert fixed_result is not None
    assert fixed_result.flip_rate <= ADMISSIBLE_CEILING
