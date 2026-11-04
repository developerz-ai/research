"""The identical-input guarantee, pinned at the population level.

E002 compares hidden-state geometry against flip rates *as if both came from the same
prompts*. These tests pin what "same prompts" means operationally: populations generated
with the same (n_per_family, seed) are identical across ALL families, and the executed
E002 defect — geometry at 24/family truncated to 288, against a 100/family flip rate —
overlaps the flip-rate population only in the first family. If either property breaks,
matched-run conclusions are void and these tests must fail before any number is trusted.

Pure python under test (geomreason.inputs + geomreason.items): no torch, runs anywhere.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geomreason import inputs
from geomreason.items import FAMILIES, flatten, generate

PROJECT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("n_per_family", [1, 5, 24, 100])
def test_equal_size_populations_are_identical_across_all_families(n_per_family: int) -> None:
    """The property every matched run relies on: same (n, seed) → same prompts, everywhere.

    One family is not enough to establish this — the divergence risk lives in the LATER
    families, where a per-family RNG reset or reordered draw would silently desynchronise
    the two runs.
    """
    a = inputs.from_config(n_per_family=n_per_family, seed=0)
    b = inputs.from_config(n_per_family=n_per_family, seed=0)
    assert len(a.prompts) == len(b.prompts) == 2 * n_per_family * len(FAMILIES)
    assert a.prompts == b.prompts
    assert a.digest == b.digest == inputs.population_digest(a.prompts)

    result = inputs.compare(a, b)
    assert result.identical is True
    assert result.common_prefix == len(a.prompts)
    assert result.n_shared == len(a.prompts)
    assert result.n_only_a == 0
    assert result.n_only_b == 0


def test_executed_defect_overlap_is_confined_to_the_first_family() -> None:
    """The executed E002 mismatch, pinned: 24/family + 288 cap vs 100/family, seed 0.

    One RNG stream, drawn family by family: a shorter run shares its first family with a
    longer one and diverges at the second. Every shared prompt must be a comparison item,
    and the populations must NOT be identical — this is the exact defect the E002 records
    carry, now machine-documented instead of prose-documented.
    """
    behavior = inputs.from_config(n_per_family=100, seed=0)  # E001 as executed: 1200 items
    geometry = inputs.from_config(n_per_family=24, seed=0, max_samples=288)  # E002 as executed
    assert len(behavior.prompts) == 1200
    assert len(geometry.prompts) == 288

    result = inputs.compare(behavior, geometry)
    assert result.identical is False
    assert 24 <= result.n_shared <= 48
    assert set(result.shared_families) == {"comparison"}
    assert result.confined_to_first_family
    for pair_id in result.shared_pair_ids:
        assert pair_id.startswith("comparison-")
    assert result.common_prefix == 48  # diverges exactly at the second family
    assert result.n_only_a == 1200 - result.n_shared
    assert result.n_only_b == 288 - result.n_shared


def test_committed_behavior_record_prompts_are_reproduced_from_config() -> None:
    """results/E001-gpt2-seed0.json: config alone must rebuild the recorded prompts.

    This is what licenses reconstructing the geometry populations — which store no prompt
    list at all — from their configs: the same config shape demonstrably reproduces the
    executed population wherever per-item data can check it. Also pins the trap: the
    stored families are sorted, but generation ran in insertion order.
    """
    path = PROJECT / "results" / "E001-gpt2-seed0.json"
    if not path.exists():  # results/ is committed; skip only protects fresh partial clones
        pytest.skip("committed E001 record not present")

    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["config"]["n_per_family"] == 100
    assert len(record["items"]) == 1200
    assert record["config"]["families"] == sorted(FAMILIES)  # stored sorted …

    pop = inputs.from_behavior_record(record)
    stored = [item["prompt"] for item in record["items"]]
    assert pop.prompts == stored
    assert pop.digest == inputs.population_digest(stored)
    assert pop.families == list(FAMILIES)  # … but resolved to insertion order


def test_sorted_order_run_is_not_silently_rebuilt_from_sorted_config() -> None:
    """The trap, both directions: a record that RAN the sorted family order must not be
    reconstructed as insertion order. If it were, every population comparison downstream
    would silently compare the wrong prompt lists.
    """
    sorted_order = sorted(FAMILIES)
    items = flatten(generate(n_per_family=2, seed=0, families=sorted_order))
    record = {
        "seed": 0,
        "config": {"n_per_family": 2, "families": sorted_order},
        "items": [{"prompt": item.prompt} for item in items],
    }
    with pytest.raises(ValueError, match="does not reproduce"):
        inputs.from_behavior_record(record)


def test_legacy_geometry_record_reconstruction() -> None:
    """E002-geom-* as committed: no families key, no prompt list, config-only rebuild.

    The legacy geometry command called generate() with defaults and truncated inside
    collect_hidden_states, so the executed population is the untruncated 24/family stream
    sliced to max_samples — which is what from_geometry_record must rebuild.
    """
    record = {
        "seed": 0,
        "config": {"model": "x", "n_per_family": 24, "max_samples": 288, "n_prompts": 288},
        "items": [],
    }
    pop = inputs.from_geometry_record(record)
    untruncated = inputs.from_config(n_per_family=24, seed=0)
    assert pop.prompts == untruncated.prompts[:288]
    assert pop.digest == inputs.population_digest(untruncated.prompts[:288])
    assert pop.families == list(FAMILIES)


def test_input_population_block_round_trips_through_both_record_kinds() -> None:
    """New records carry input_population; both readers must rebuild the shown prompts."""
    prompts = [item.prompt for item in flatten(generate(n_per_family=3, seed=7))]
    block = inputs.population_block(
        n_per_family=3, seed=7, families=list(FAMILIES), max_samples=0, prompts=prompts,
    )
    assert block["families"] == sorted(FAMILIES)
    assert block["prompt_digest"] == inputs.population_digest(prompts)

    geometry_record = {"seed": 7, "config": {"input_population": block}, "items": []}
    rebuilt = inputs.from_geometry_record(geometry_record)
    assert rebuilt.prompts == prompts
    assert rebuilt.digest == block["prompt_digest"]

    behavior_record = {
        "seed": 7,
        "config": {"input_population": block},
        "items": [{"prompt": p} for p in prompts],
    }
    assert inputs.from_behavior_record(behavior_record).prompts == prompts


def test_tampered_prompt_digest_is_rejected() -> None:
    """A digest is a claim about what was shown; a record that contradicts its own digest
    must fail loudly rather than pass a premise audit on stale bookkeeping."""
    prompts = [item.prompt for item in flatten(generate(n_per_family=2, seed=3))]
    block = inputs.population_block(
        n_per_family=2, seed=3, families=list(FAMILIES), max_samples=0, prompts=prompts,
    )
    block["prompt_digest"] = "0" * 16
    record = {
        "seed": 3,
        "config": {"input_population": block},
        "items": [{"prompt": p} for p in prompts],
    }
    with pytest.raises(ValueError, match="prompt_digest mismatch"):
        inputs.from_behavior_record(record)


def test_tampered_geometry_prompt_digest_is_rejected() -> None:
    """Mirror of the behavior-record tamper case for geometry records.

    A geometry record stores no prompt list at all (``items=[]``), so the digest in its
    ``input_population`` block is the ONLY verification its config-only reconstruction
    gets. Deleting the check in ``from_geometry_record`` must fail here: a geometry
    record that contradicts its own bookkeeping would otherwise pass a premise audit on
    a population nobody can cross-check against stored prompts.
    """
    prompts = [item.prompt for item in flatten(generate(n_per_family=2, seed=3))]
    block = inputs.population_block(
        n_per_family=2, seed=3, families=list(FAMILIES), max_samples=0, prompts=prompts,
    )
    block["prompt_digest"] = "0" * 16
    record = {"seed": 3, "config": {"input_population": block}, "items": []}
    with pytest.raises(ValueError, match="prompt_digest mismatch"):
        inputs.from_geometry_record(record)


def test_different_seeds_give_different_populations() -> None:
    """Seed is part of a population's identity; same n with different seed is not a match."""
    a = inputs.from_config(n_per_family=5, seed=0)
    b = inputs.from_config(n_per_family=5, seed=1)
    assert a.digest != b.digest
    assert inputs.compare(a, b).identical is False


def test_population_digest_is_order_sensitive() -> None:
    """A population is a sequence: reordering or truncating must change the digest."""
    assert len(inputs.population_digest(["a", "b"])) == 16
    assert inputs.population_digest(["a", "b"]) != inputs.population_digest(["b", "a"])
    assert inputs.population_digest(["a"]) != inputs.population_digest(["a", "a"])
