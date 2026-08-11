"""Metric behaviour on models whose answers we control exactly.

Each test pins down what a specific failure mode *should* look like in the numbers, so that
a real measurement can be read rather than guessed at.
"""

from __future__ import annotations

import pytest

from geomreason import items as item_gen
from geomreason.metrics import score_pairs, wilson_interval


def _records(chooser) -> list[dict]:
    """Build scoring records from a function (item -> chosen_index).

    50 pairs per family keeps the per-variant answer balance (which is randomised, see
    ``items.generate``) tight enough that the tolerances below are ~3 sigma. The seed is
    fixed, so these tests are deterministic despite that randomisation.
    """
    flat = item_gen.flatten(item_gen.generate(n_per_family=50, seed=0))
    return [
        {
            "pair_id": item.pair_id,
            "family": item.family,
            "variant": item.variant,
            "chosen_index": chooser(item),
            "correct_index": item.correct_index,
        }
        for item in flat
    ]


def test_perfect_model() -> None:
    result = score_pairs(_records(lambda i: i.correct_index))
    assert result.flip_rate == 1.0
    assert result.shortcut_gap == 0.0
    assert result.stickiness == 0.0


def test_constant_answer_model_scores_zero_not_chance() -> None:
    """The key property: a model ignoring the perturbation gets 0, not 50%.

    On a conventional benchmark the same model scores ~50%. That difference is the entire
    reason for the paired design.
    """
    result = score_pairs(_records(lambda i: 0))
    # Exact, by construction: one correct answer at each index per pair.
    assert result.flip_rate == 0.0
    assert result.stickiness == 1.0
    # Approximate: per-variant balance is randomised (see items.generate).
    assert result.canonical_accuracy == pytest.approx(0.5, abs=0.08)
    assert result.perturbed_accuracy == pytest.approx(0.5, abs=0.08)
    # Independent errors would predict ~0.25; observing 0.0 is the shortcut signature.
    assert result.expected_flip_rate_if_independent == pytest.approx(0.25, abs=0.05)
    assert result.shortcut_gap == pytest.approx(0.25, abs=0.05)


def test_canonical_only_model_is_caught() -> None:
    """High canonical accuracy with chance perturbed accuracy — the memorisation signature."""
    result = score_pairs(
        _records(lambda i: i.correct_index if i.variant == "canonical" else 0)
    )
    assert result.canonical_accuracy == 1.0
    assert result.perturbed_accuracy == pytest.approx(0.5, abs=0.08)
    assert result.flip_rate == pytest.approx(0.5, abs=0.08)


def test_incomplete_pair_rejected() -> None:
    """Half a pair is not a measurement — fail loudly rather than average over it."""
    records = _records(lambda i: i.correct_index)
    with pytest.raises(ValueError, match="incomplete"):
        score_pairs([r for r in records if r["variant"] == "canonical"])


def test_per_family_breakdown_covers_all_families() -> None:
    result = score_pairs(_records(lambda i: i.correct_index))
    assert set(result.per_family) == set(item_gen.FAMILIES)
    assert sum(f.n_pairs for f in result.per_family.values()) == result.n_pairs


def test_wilson_interval_bounds() -> None:
    """Wilson stays inside [0, 1] at the extremes, where the normal approximation does not."""
    assert wilson_interval(0, 100).lo == 0.0
    assert wilson_interval(100, 100).hi == 1.0
    for successes in (0, 1, 50, 99, 100):
        interval = wilson_interval(successes, 100)
        assert 0.0 <= interval.lo <= interval.hi <= 1.0

    wide, narrow = wilson_interval(5, 10), wilson_interval(500, 1000)
    assert (wide.hi - wide.lo) > (narrow.hi - narrow.lo)


def test_wilson_interval_empty() -> None:
    interval = wilson_interval(0, 0)
    assert (interval.lo, interval.hi) == (0.0, 1.0)


def test_serialisation_round_trips() -> None:
    import json

    result = score_pairs(_records(lambda i: i.correct_index))
    payload = json.loads(json.dumps(result.as_dict()))
    assert payload["flip_rate"] == 1.0
    assert payload["chance_flip_rate"] == 0.25
    assert set(payload["per_family"]) == set(item_gen.FAMILIES)
