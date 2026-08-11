"""Item generation is where a flip-rate measurement gets silently corrupted.

If a pair's options differ, or its answer does not actually flip, the harness measures
something other than reasoning and reports it in the same units. These tests are the guard.
"""

from __future__ import annotations

import pytest

from geomreason import items as item_gen


@pytest.mark.parametrize("seed", range(20))
def test_all_pairs_validate_across_seeds(seed: int) -> None:
    """Structural invariants must hold for every generated pair, not just typical ones."""
    for pair in item_gen.generate(n_per_family=25, seed=seed):
        pair.validate()  # raises on any violation


def test_options_identical_within_pair() -> None:
    """The control that removes option-string effects by construction."""
    for pair in item_gen.generate(n_per_family=40, seed=1):
        assert pair.canonical.options == pair.perturbed.options


def test_answer_actually_flips() -> None:
    """A perturbation that does not flip the answer is not load-bearing."""
    for pair in item_gen.generate(n_per_family=40, seed=2):
        assert pair.canonical.correct_index != pair.perturbed.correct_index


def test_correct_answers_balanced_per_family() -> None:
    """Answer priors must not be able to score above chance.

    Each pair contributes exactly one correct answer at each index, so the balance is exact
    by construction — this test fails loudly if a future family breaks that.
    """
    pairs = item_gen.generate(n_per_family=50, seed=3)
    by_family: dict[str, list[int]] = {}
    for pair in pairs:
        for member in (pair.canonical, pair.perturbed):
            by_family.setdefault(member.family, []).append(member.correct_index)

    for family, indices in by_family.items():
        zeros = indices.count(0)
        assert zeros == len(indices) / 2, f"{family} is answer-imbalanced: {zeros}/{len(indices)}"


def test_correct_answers_balanced_within_each_variant() -> None:
    """The subtler balance, and the one a template-based generator breaks by default.

    Each family template fixes which option is correct for its canonical member. Without the
    random option-order swap in ``generate``, every canonical item in a family would share
    the same correct index, and canonical accuracy would measure option bias rather than
    reasoning — invisible in the pooled balance check above.
    """
    pairs = item_gen.generate(n_per_family=200, seed=4)
    by_key: dict[tuple[str, str], list[int]] = {}
    for pair in pairs:
        for member in (pair.canonical, pair.perturbed):
            by_key.setdefault((member.family, member.variant), []).append(member.correct_index)

    for (family, variant), indices in by_key.items():
        share = indices.count(0) / len(indices)
        assert 0.4 < share < 0.6, f"{family}/{variant} option-biased: index0 share {share:.2f}"


def test_generation_is_deterministic() -> None:
    """Same seed, same items — otherwise a run record cannot be reproduced."""
    a = item_gen.generate(n_per_family=10, seed=7)
    b = item_gen.generate(n_per_family=10, seed=7)
    assert [p.canonical.prompt for p in a] == [p.canonical.prompt for p in b]
    assert [p.perturbed.prompt for p in a] == [p.perturbed.prompt for p in b]


def test_different_seeds_give_different_items() -> None:
    """Fresh generation is the contamination defence — it must actually be fresh."""
    a = {p.canonical.prompt for p in item_gen.generate(n_per_family=20, seed=0)}
    b = {p.canonical.prompt for p in item_gen.generate(n_per_family=20, seed=1)}
    assert len(a & b) < len(a) * 0.5


def test_arithmetic_results_are_positive_and_distinct() -> None:
    """A negative or duplicated result would make the item ambiguous or trivially wrong."""
    for pair in item_gen.generate(n_per_family=100, seed=5, families=["arithmetic"]):
        values = [int(o.strip()) for o in pair.canonical.options]
        assert all(v > 0 for v in values)
        assert values[0] != values[1]


def test_unknown_family_rejected() -> None:
    with pytest.raises(ValueError, match="unknown families"):
        item_gen.generate(families=["not_a_family"])


def test_flatten_preserves_pairing() -> None:
    pairs = item_gen.generate(n_per_family=5, seed=0)
    flat = item_gen.flatten(pairs)
    assert len(flat) == 2 * len(pairs)
    for pair_id in {item.pair_id for item in flat}:
        variants = {i.variant for i in flat if i.pair_id == pair_id}
        assert variants == {"canonical", "perturbed"}
