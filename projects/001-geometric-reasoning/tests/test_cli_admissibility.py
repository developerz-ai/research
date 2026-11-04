"""The item-admissibility contract as ENFORCED by ``geom eval`` and ``geom sweep``.

Until now only the standalone ``geom baselines`` command measured admissibility; an eval or
a sweep would happily score a population a trivial heuristic aces — the exact way the
original broken ``role_swap`` family reached a writeup. These tests pin the enforced
contract: on an inadmissible population the commands exit nonzero, name the offending
family and heuristic, load no model, and write no run record; on the anchored admissible
population (``n_per_family=100, seed=0``, proven admissible by ``tests/test_baselines.py``)
they run to completion and write their records.

``typer.Exit`` subclasses ``Exception``: a sweep's broad ``except Exception`` would swallow
the guard as a per-model "failed" and still exit 0. So the sweep checks the population up
front — the population is model-independent (``item_gen.generate(n, seed)``), outside the
try — and re-raises ``typer.Exit`` in the except tuple.

No network, no GPU: the model-facing seams are monkeypatched
(``geomreason.evaluate.load_model`` / ``evaluate_items``), typer CliRunner style, the
pattern of ``tests/test_cli_matching.py``.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from typer.testing import CliRunner

from geomreason import baselines, cli, evaluate
from geomreason import items as item_gen
from geomreason.baselines import ADMISSIBLE_CEILING  # the preregistered line, single source
from geomreason.evaluate import LoadedModel
from geomreason.items import Item, Pair

runner = CliRunner()


def broken_pair() -> Pair:
    """Hand-built defect, per ``tests/test_baselines.py``: the swapped-name dative pair.

    Swapping the names puts the correct answer last-mentioned in *both* members, so
    ``last_mentioned_entity`` scores a perfect flip rate on this family.
    """
    return Pair(
        canonical=Item(
            prompt="Alice gave the book to Bob. Question: who has the book now? Answer:",
            options=(" Alice", " Bob"), correct_index=1,
            family="role_swap_broken", variant="canonical", pair_id="x-0",
        ),
        perturbed=Item(
            prompt="Bob gave the book to Alice. Question: who has the book now? Answer:",
            options=(" Alice", " Bob"), correct_index=0,
            family="role_swap_broken", variant="perturbed", pair_id="x-0",
        ),
    )


def recording_load_model(calls: list[str]):
    """A loader that records every call; real LoadedModel shape, no network, no GPU."""

    def load(name: str) -> LoadedModel:
        calls.append(name)
        return LoadedModel(
            model=None,
            tokenizer=None,
            name=name,
            n_params=124_000_000,
            device_info=SimpleNamespace(backend="cpu"),
        )

    return load


def fake_evaluate(loaded, items, batch_size: int = 16, aggregation: str = "sum",
                  progress=None) -> list[dict]:
    """A perfect model — same fixture shape as ``tests/test_cli_matching.py``."""
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


# ── unit: the predicate ───────────────────────────────────────────────────────


def test_admissibility_violations_flags_the_broken_family() -> None:
    broken = item_gen.flatten([broken_pair()])
    assert baselines.admissibility_violations(broken) == {
        "role_swap_broken": ("last_mentioned_entity", 1.0),
    }


def test_admissibility_violations_empty_on_the_anchored_population() -> None:
    flat = item_gen.flatten(item_gen.generate(n_per_family=100, seed=0))
    assert baselines.admissibility_violations(flat) == {}


def test_ceiling_is_the_preregistered_value() -> None:
    # Pin the line here: a silent redefinition in baselines.py must fail a test, not
    # quietly widen or tighten the gate every run passes through.
    assert ADMISSIBLE_CEILING == 0.40


# ── geom eval ─────────────────────────────────────────────────────────────────


def test_eval_refuses_inadmissible_population(tmp_path, monkeypatch) -> None:
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setattr(cli, "RESULTS", results)
    loaded: list[str] = []
    monkeypatch.setattr(evaluate, "load_model", recording_load_model(loaded))
    monkeypatch.setattr(item_gen, "generate", lambda **kwargs: [broken_pair()])

    result = runner.invoke(cli.app, ["eval", "--model", "m", "--n", "1", "--seed", "0"])

    assert result.exit_code == 1
    assert "role_swap_broken" in result.output  # names the family...
    assert "last_mentioned_entity" in result.output  # ...and the heuristic that aces it
    assert "ceiling 0.40" in result.output
    assert loaded == []  # refuses before any model work
    assert list(results.glob("*.json")) == []  # no run record


def test_eval_completes_on_the_anchored_admissible_population(tmp_path, monkeypatch) -> None:
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setattr(cli, "RESULTS", results)
    loaded: list[str] = []
    monkeypatch.setattr(evaluate, "load_model", recording_load_model(loaded))
    monkeypatch.setattr(evaluate, "evaluate_items", fake_evaluate)

    result = runner.invoke(cli.app, ["eval", "--model", "m", "--n", "100", "--seed", "0"])

    assert result.exit_code == 0
    assert loaded == ["m"]
    path = results / "E001-m-seed0.json"
    assert path.exists()  # the run record is written
    record = json.loads(path.read_text(encoding="utf-8"))
    assert len(record["items"]) == 1200  # 100 pairs × 2 members × 6 families


# ── geom sweep ────────────────────────────────────────────────────────────────


def test_sweep_refuses_inadmissible_population_before_any_model(
    tmp_path, monkeypatch,
) -> None:
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setattr(cli, "RESULTS", results)
    loaded: list[str] = []
    monkeypatch.setattr(evaluate, "load_model", recording_load_model(loaded))
    monkeypatch.setattr(evaluate, "evaluate_items", fake_evaluate)
    monkeypatch.setattr(item_gen, "generate", lambda **kwargs: [broken_pair()])

    result = runner.invoke(cli.app, ["sweep", "--models", "m1,m2,m3"])

    assert result.exit_code == 1
    assert "role_swap_broken" in result.output
    assert "failed" not in result.output  # never dressed up as a per-model failure
    assert loaded == []  # refuses before ANY model loads
    assert list(results.glob("*.json")) == []  # no run record


def test_sweep_completes_on_the_anchored_admissible_population(
    tmp_path, monkeypatch,
) -> None:
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setattr(cli, "RESULTS", results)
    loaded: list[str] = []
    monkeypatch.setattr(evaluate, "load_model", recording_load_model(loaded))
    monkeypatch.setattr(evaluate, "evaluate_items", fake_evaluate)

    result = runner.invoke(cli.app, ["sweep", "--models", "m", "--n", "100", "--seed", "0"])

    assert result.exit_code == 0
    assert loaded == ["m"]
    assert (results / "E001-m-seed0.json").exists()  # the run record is written
