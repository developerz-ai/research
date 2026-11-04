"""The CLI branches of the input-population work, pinned end to end.

Every branch here was previously uncovered — nothing failed if it was deleted. The tests
run the real typer app through CliRunner with ``cli.RESULTS`` pointed at tmp_path
fixtures, and with the model-facing seams monkeypatched
(``geomreason.evaluate.load_model``, ``geomreason.geometry.collect_hidden_states``):
no network, no GPU, no checkpoint download.

geosweep gets the closest reading because it is the structural guard against the executed
E001/E002 mismatch: n_per_family and seed must come from each model's own flip-rate
record, and every skip path must actually skip — a geosweep that ran geometry with the
wrong population would silently rebuild the defect these tests exist to prevent.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
from typer.testing import CliRunner

from geomreason import cli, evaluate, inputs
from geomreason import geometry as geom_metrics
from geomreason.evaluate import LoadedModel
from geomreason.items import FAMILIES, flatten, generate

runner = CliRunner()


def behavior_record(model: str, n_per_family: int, seed: int) -> dict:
    """A behavior record whose stored per-item prompts genuinely reproduce from config.

    Carries flip-rate metrics: ``_flip_records_by_model`` must accept only records with
    flip-rate metrics and per-item prompts, so the fixture has to look like the real
    thing or the filter would rightly reject it.
    """
    prompts = [item.prompt for item in flatten(generate(n_per_family=n_per_family, seed=seed))]
    return {
        "seed": seed,
        "config": {
            "model": model,
            "n_per_family": n_per_family,
            "families": sorted(FAMILIES),
            "input_population": inputs.population_block(
                n_per_family=n_per_family, seed=seed, families=list(FAMILIES),
                max_samples=0, prompts=prompts,
            ),
        },
        "metrics": {"n_pairs": len(prompts) // 2, "flip_rate": 0.0},
        "items": [{"prompt": p} for p in prompts],
    }


def geometry_record(
    model: str, n_per_family: int, seed: int, digest: str | None = None,
) -> dict:
    """A geometry record (items=[], config-only rebuild), digest tamperable for tests."""
    prompts = [item.prompt for item in flatten(generate(n_per_family=n_per_family, seed=seed))]
    block = inputs.population_block(
        n_per_family=n_per_family, seed=seed, families=list(FAMILIES),
        max_samples=0, prompts=prompts,
    )
    if digest is not None:
        block["prompt_digest"] = digest
    return {
        "seed": seed,
        "config": {"model": model, "n_per_family": n_per_family, "input_population": block},
        "items": [],
    }


def fake_load_model(name: str) -> LoadedModel:
    """Stand-in for the HF loader: just what the CLI prints and records."""
    return LoadedModel(
        model=None,
        tokenizer=None,
        name=name,
        n_params=124_000_000,
        device_info=SimpleNamespace(backend="cpu"),
    )


def fake_collect_hidden_states(seen: list[str]):
    """Record the prompts actually collected and return small deterministic activations.

    Honours ``max_samples`` exactly like the real ``collect_hidden_states``: a fake that
    ignored the cap would pass even if the CLI delegated truncation to the collector and
    then recorded the untruncated list — the record would lie about what was shown, and
    the count/digest assertions below would not notice.
    """
    def collect(loaded, prompts, batch_size: int = 8, max_samples: int = 512):
        prompts = prompts[:max_samples]
        seen.extend(prompts)
        n = len(prompts)
        return {0: np.arange(n * 8, dtype=float).reshape(n, 8)}

    return collect


# ── geosweep ──────────────────────────────────────────────────────────────────


def test_geosweep_derives_n_per_family_and_seed_from_the_flip_record(tmp_path, monkeypatch):
    """The matched run must be identical by construction: n and seed from the flip record."""
    results = tmp_path / "results"
    results.mkdir()
    (results / "E001-m-seed2.json").write_text(
        json.dumps(behavior_record("m", n_per_family=7, seed=2)), encoding="utf-8"
    )
    monkeypatch.setattr(cli, "RESULTS", results)
    calls: list[dict] = []

    def recorder(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(cli, "geometry", recorder)
    result = runner.invoke(cli.app, ["geosweep"])
    assert result.exit_code == 0
    assert len(calls) == 1
    assert calls[0]["model"] == "m"
    assert calls[0]["n"] == 7  # from the flip record's config, not geosweep's default
    assert calls[0]["seed"] == 2  # from the flip record, not the default 0
    assert calls[0]["out"] == results / "E002-geom-m.json"
    assert calls[0]["experiment"] == "E002"
    assert calls[0]["max_samples"] == 0  # matched run: no truncation by default


def test_geosweep_skips_model_without_a_flip_record(tmp_path, monkeypatch):
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setattr(cli, "RESULTS", results)
    calls: list[dict] = []

    def recorder(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(cli, "geometry", recorder)
    result = runner.invoke(cli.app, ["geosweep", "--models", "ghost"])
    assert result.exit_code == 0
    assert calls == []  # a model nothing can be matched against must not be profiled
    assert "no flip-rate record to match" in result.output


def test_geosweep_skips_flip_record_without_n_per_family(tmp_path, monkeypatch):
    """A genuine flip-rate record (metrics + per-item prompts) whose config names no
    n_per_family: a population can't be derived from it — refuse to guess."""
    results = tmp_path / "results"
    results.mkdir()
    (results / "E001-m3-seed0.json").write_text(
        json.dumps({
            "seed": 0,
            "config": {"model": "m3"},
            "metrics": {"flip_rate": 0.0},
            "items": [{"prompt": "p"}],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "RESULTS", results)
    calls: list[dict] = []

    def recorder(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(cli, "geometry", recorder)
    result = runner.invoke(cli.app, ["geosweep", "--models", "m3"])
    assert result.exit_code == 0
    assert calls == []  # no derivable population — refuse to guess
    assert "no n_per_family" in result.output


def test_geosweep_ignores_geometry_record_sorting_before_the_flip_record(
    tmp_path, monkeypatch
):
    """`geometry --experiment E001` writes E001-geom-<model>.json — items=[], layer
    metrics — and it sorts BEFORE E001-<model>-seed0.json. Selected as the behavior
    record it would match geosweep against the geometry run's own population (rebuilding
    the executed E001/E002 mismatch) and make `geom inputs` reject the pair. Only a
    record with flip-rate metrics and per-item prompts may be matched against."""
    results = tmp_path / "results"
    results.mkdir()
    (results / "E001-geom-m.json").write_text(
        json.dumps(geometry_record("m", n_per_family=24, seed=0)), encoding="utf-8"
    )
    (results / "E001-m-seed2.json").write_text(
        json.dumps(behavior_record("m", n_per_family=7, seed=2)), encoding="utf-8"
    )
    monkeypatch.setattr(cli, "RESULTS", results)

    found = cli._flip_records_by_model()
    assert set(found) == {"m"}
    assert found["m"][0] == results / "E001-m-seed2.json"  # not the geometry record

    calls: list[dict] = []

    def recorder(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(cli, "geometry", recorder)
    result = runner.invoke(cli.app, ["geosweep"])
    assert result.exit_code == 0
    assert len(calls) == 1
    assert calls[0]["n"] == 7  # the behavior record's population, not the geometry one
    assert calls[0]["seed"] == 2


def test_geosweep_skips_already_profiled_model(tmp_path, monkeypatch):
    results = tmp_path / "results"
    results.mkdir()
    (results / "E001-m4-seed0.json").write_text(
        json.dumps(behavior_record("m4", n_per_family=2, seed=0)), encoding="utf-8"
    )
    (results / "E002-geom-m4.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli, "RESULTS", results)
    calls: list[dict] = []

    def recorder(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(cli, "geometry", recorder)
    result = runner.invoke(cli.app, ["geosweep", "--models", "m4"])
    assert result.exit_code == 0
    assert calls == []  # results/ is append-only: never recompute an existing record
    assert "already profiled" in result.output


# ── geometry ──────────────────────────────────────────────────────────────────


def test_geometry_standalone_writes_record_with_input_population(tmp_path, monkeypatch):
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setattr(cli, "RESULTS", results)
    monkeypatch.setattr(evaluate, "load_model", fake_load_model)
    seen: list[str] = []
    monkeypatch.setattr(geom_metrics, "collect_hidden_states", fake_collect_hidden_states(seen))

    result = runner.invoke(cli.app, ["geometry", "--model", "m", "--n", "2", "--seed", "0"])
    assert result.exit_code == 0

    path = results / "E002-geom-m.json"  # the standalone default record name
    assert path.exists()
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["items"] == []  # geometry records carry no per-item data
    assert record["config"]["n_per_family"] == 2

    block = record["config"]["input_population"]
    assert block["n_prompts"] == len(seen) == 24  # 2 pairs × 2 members × 6 families
    assert block["prompt_digest"] == inputs.population_digest(seen)
    rebuilt = inputs.from_geometry_record(record)
    assert rebuilt.prompts == seen  # the block must rebuild the prompts actually shown


def test_geometry_truncation_is_fingerprinted_after_the_cut(tmp_path, monkeypatch):
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setattr(cli, "RESULTS", results)
    monkeypatch.setattr(evaluate, "load_model", fake_load_model)
    seen: list[str] = []
    monkeypatch.setattr(geom_metrics, "collect_hidden_states", fake_collect_hidden_states(seen))

    result = runner.invoke(
        cli.app, ["geometry", "--model", "m", "--n", "2", "--seed", "0", "--max-samples", "16"]
    )
    assert result.exit_code == 0

    record = json.loads((results / "E002-geom-m.json").read_text(encoding="utf-8"))
    block = record["config"]["input_population"]
    assert block["max_samples"] == 16
    assert block["n_prompts"] == len(seen) == 16
    # The digest fingerprints the truncated list — the exact silence that hid the
    # original E001/E002 mismatch was a record that never said what was shown.
    assert block["prompt_digest"] == inputs.population_digest(seen)
    assert seen == inputs.from_config(n_per_family=2, seed=0).prompts[:16]


def test_geometry_standalone_refuses_to_overwrite(tmp_path, monkeypatch):
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setattr(cli, "RESULTS", results)
    monkeypatch.setattr(evaluate, "load_model", fake_load_model)
    seen: list[str] = []
    monkeypatch.setattr(geom_metrics, "collect_hidden_states", fake_collect_hidden_states(seen))

    argv = ["geometry", "--model", "m", "--n", "2", "--seed", "0"]
    first = runner.invoke(cli.app, argv)
    assert first.exit_code == 0

    second = runner.invoke(cli.app, argv)  # same args, record now exists
    assert second.exit_code == 1
    assert "refusing to overwrite" in second.output  # before any compute, not at write time


# ── eval ──────────────────────────────────────────────────────────────────────


def test_eval_record_carries_input_population_with_prompt_digest(tmp_path, monkeypatch):
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setattr(cli, "RESULTS", results)
    monkeypatch.setattr(evaluate, "load_model", fake_load_model)

    def fake_evaluate(loaded, items, batch_size: int = 16, aggregation: str = "sum",
                      progress=None) -> list[dict]:
        return [
            {
                "pair_id": i.pair_id,
                "family": i.family,
                "variant": i.variant,
                "prompt": i.prompt,
                "options": list(i.options),
                "correct_index": i.correct_index,
                "chosen_index": i.correct_index,  # perfect model — flip rate 1.0
                "correct": True,
                "logprob_sum": [0.0, 0.0],
                "logprob_mean": [0.0, 0.0],
                "margin": 0.0,
            }
            for i in items
        ]

    monkeypatch.setattr(evaluate, "evaluate_items", fake_evaluate)

    result = runner.invoke(cli.app, ["eval", "--model", "m", "--n", "2", "--seed", "3"])
    assert result.exit_code == 0

    path = results / "E001-m-seed3.json"
    assert path.exists()
    record = json.loads(path.read_text(encoding="utf-8"))
    stored = [item["prompt"] for item in record["items"]]
    assert len(stored) == 24

    block = record["config"]["input_population"]
    assert block["prompt_digest"] == inputs.population_digest(stored)
    assert inputs.from_behavior_record(record).prompts == stored  # block reproduces the items
    assert record["config"]["families"] == sorted(FAMILIES)  # stored-sorted trap preserved


# ── inputs ────────────────────────────────────────────────────────────────────


def test_inputs_reports_mismatch_and_strict_exits_nonzero(tmp_path, monkeypatch):
    """The executed E002 defect, shrunk to fixtures: 24 behavior prompts vs 12 geometry
    prompts, overlap confined to the first family — --strict must fail on exactly this."""
    results = tmp_path / "results"
    results.mkdir()
    (results / "E001-m-seed5.json").write_text(
        json.dumps(behavior_record("m", n_per_family=2, seed=5)), encoding="utf-8"
    )
    (results / "E002-geom-m.json").write_text(
        json.dumps(geometry_record("m", n_per_family=1, seed=5)), encoding="utf-8"
    )
    monkeypatch.setattr(cli, "RESULTS", results)

    lax = runner.invoke(cli.app, ["inputs", "--experiment", "E002"])
    assert lax.exit_code == 0  # reporting the mismatch must not itself fail
    assert "identical-input premise broken" in lax.output
    assert "24" in lax.output  # behavior prompts reported
    assert "12" in lax.output  # geometry prompts reported

    strict = runner.invoke(cli.app, ["inputs", "--experiment", "E002", "--strict"])
    assert strict.exit_code == 1


def test_inputs_identical_populations_pass_strict(tmp_path, monkeypatch):
    results = tmp_path / "results"
    results.mkdir()
    beh = behavior_record("m", n_per_family=2, seed=5)
    (results / "E001-m-seed5.json").write_text(json.dumps(beh), encoding="utf-8")
    geo = {
        "seed": 5,
        "config": {"model": "m", "input_population": beh["config"]["input_population"]},
        "items": [],
    }
    (results / "E002-geom-m.json").write_text(json.dumps(geo), encoding="utf-8")
    monkeypatch.setattr(cli, "RESULTS", results)

    result = runner.invoke(cli.app, ["inputs", "--experiment", "E002", "--strict"])
    assert result.exit_code == 0
    assert "identical inputs" in result.output


def test_inputs_rejects_geometry_record_with_tampered_digest(tmp_path, monkeypatch):
    """A geometry record contradicting its own digest makes the whole comparison refuse,
    even without --strict: a rebuilt-on-a-guess population cannot be compared at all."""
    results = tmp_path / "results"
    results.mkdir()
    (results / "E001-m-seed5.json").write_text(
        json.dumps(behavior_record("m", n_per_family=2, seed=5)), encoding="utf-8"
    )
    (results / "E002-geom-m.json").write_text(
        json.dumps(geometry_record("m", n_per_family=2, seed=5, digest="0" * 16)),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "RESULTS", results)

    result = runner.invoke(cli.app, ["inputs", "--experiment", "E002"])
    assert result.exit_code == 1
    assert "prompt_digest mismatch" in result.output


def test_inputs_with_no_geometry_records_fails(tmp_path, monkeypatch):
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setattr(cli, "RESULTS", results)

    result = runner.invoke(cli.app, ["inputs", "--experiment", "E002"])
    assert result.exit_code == 1
    assert "no geometry records matching" in result.output


def test_inputs_does_not_claim_identical_when_a_population_failed_to_rebuild(
    tmp_path, monkeypatch,
):
    """One verified-identical pair plus one geometry record with a tampered digest: the
    green 'identical inputs' summary must require every population to have been rebuilt.
    A skipped record verified nothing — printing green over it would certify a premise
    nobody checked, which is exactly how the audit once lied while exiting nonzero."""
    results = tmp_path / "results"
    results.mkdir()
    beh = behavior_record("m", n_per_family=2, seed=5)
    (results / "E001-m-seed5.json").write_text(json.dumps(beh), encoding="utf-8")
    good = {
        "seed": 5,
        "config": {"model": "m", "input_population": beh["config"]["input_population"]},
        "items": [],
    }
    (results / "E002-geom-m.json").write_text(json.dumps(good), encoding="utf-8")
    (results / "E002-geom-z.json").write_text(
        json.dumps(geometry_record("z", n_per_family=2, seed=5, digest="0" * 16)),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "RESULTS", results)

    lax = runner.invoke(cli.app, ["inputs", "--experiment", "E002"])
    assert lax.exit_code == 1  # a failed rebuild fails the audit even without --strict
    assert "verification incomplete" in lax.output
    assert "identical inputs" not in lax.output  # green requires all_rebuilt

    strict = runner.invoke(cli.app, ["inputs", "--experiment", "E002", "--strict"])
    assert strict.exit_code == 1
    assert "verification incomplete" in strict.output
