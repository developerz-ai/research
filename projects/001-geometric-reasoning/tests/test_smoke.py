"""The ``geom smoke`` verdict matrix, pinned end to end.

The old smoke printed ``smoke passed`` unconditionally: a model check that was skipped
for network reasons reported the same exit code as one that actually ran, and a broken
checkpoint read as "wiring fine". Every branch here was previously uncovered — nothing
failed if the classifier was deleted or the verdict lines were lost.

Tests run the real typer app through CliRunner with the model-facing seams
monkeypatched at module level (``geomreason.evaluate.load_model`` and
``evaluate.evaluate_items`` — smoke imports them inside the function, so module-level
patching wins). No network, no GPU, no checkpoint download, nothing written to
``results/``.

Transport exceptions are simulated by tagging a synthetic class with the vendor's
``__module__`` prefix rather than importing hub names: requests is not installed in
this venv and the hub's transport churns between releases, while the prefix contract
does not. When the real ``huggingface_hub.errors`` package is importable, one of its
own exception classes is exercised too — version-proof by construction, proven on the
real thing when it is present.

Output assertions collapse whitespace because rich soft-wraps at the console width: a
verdict line may break mid-sentence, but never mid-word.
"""

from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from geomreason import cli, evaluate
from geomreason.evaluate import LoadedModel

runner = CliRunner()


# ── seams ─────────────────────────────────────────────────────────────────────


def fake_load_model(name: str) -> LoadedModel:
    """Stand-in for the HF loader: just what the CLI prints and records."""
    return LoadedModel(
        model=None,
        tokenizer=None,
        name=name,
        n_params=124_000_000,
        device_info=SimpleNamespace(backend="cpu"),
    )


def perfect_scorer(loaded, items, batch_size: int = 16, aggregation: str = "sum",
                   progress=None) -> list[dict]:
    """A model that always picks the correct option — smoke's happy path."""
    return [
        {
            "pair_id": item.pair_id,
            "family": item.family,
            "variant": item.variant,
            "prompt": item.prompt,
            "options": list(item.options),
            "correct_index": item.correct_index,
            "chosen_index": item.correct_index,
            "correct": True,
        }
        for item in items
    ]


def error_from_module(module: str, message: str) -> Exception:
    """An exception class tagged with *module* — the transport churns, the prefix doesn't."""
    cls = type("SimulatedTransportError", (Exception,), {"__module__": module})
    return cls(message)


def real_hub_error() -> Exception | None:
    """A constructible ``huggingface_hub.errors`` exception, if the hub is installed.

    Skips classes under builtin ConnectionError/TimeoutError, so the test proves the
    MRO-prefix branch rather than the isinstance shortcut.
    """
    try:
        errors = importlib.import_module("huggingface_hub.errors")
    except ImportError:
        return None
    for name in dir(errors):
        cls = getattr(errors, name)
        if not (isinstance(cls, type) and issubclass(cls, BaseException)):
            continue
        if cls.__module__.split(".", 1)[0] != "huggingface_hub":
            continue
        if issubclass(cls, (ConnectionError, TimeoutError)):
            continue
        for args in ((), ("hub unreachable",)):
            try:
                return cls(*args)
            except TypeError:
                continue
    return None


def flat_output(result) -> str:
    """Output with rich's soft-wraps normalised away (breaks land on word boundaries)."""
    return " ".join(result.output.split())


def patch_seams(monkeypatch, loader, scorer=perfect_scorer) -> None:
    monkeypatch.setattr(evaluate, "load_model", loader)
    monkeypatch.setattr(evaluate, "evaluate_items", scorer)


# ── happy path ────────────────────────────────────────────────────────────────


def test_smoke_passes_when_model_check_runs(monkeypatch):
    patch_seams(monkeypatch, fake_load_model)

    result = runner.invoke(cli.app, ["smoke"])

    assert result.exit_code == 0
    assert "smoke passed" in flat_output(result)
    assert "skipped" not in result.output
    assert "PARTIAL" not in result.output
    assert "FAILED" not in result.output


# ── availability errors → smoke PARTIAL, exit 1, never 'smoke passed' ────────


@pytest.mark.parametrize(
    ("exc", "label"),
    [
        (ConnectionError("peer reset"), "builtin-ConnectionError"),
        (TimeoutError("timed out"), "builtin-TimeoutError"),
        (error_from_module("huggingface_hub.errors", "hub unreachable"), "hub-mro"),
        (error_from_module("httpx.exceptions", "transport gone"), "httpx-mro"),
        (error_from_module("httpx2.exceptions", "transport gone"), "httpx2-mro"),
        (error_from_module("requests.exceptions", "connection refused"), "requests-mro"),
        (error_from_module("urllib3.exceptions", "read error"), "urllib3-mro"),
    ],
    ids=[
        "builtin-ConnectionError", "builtin-TimeoutError", "hub-mro", "httpx-mro",
        "httpx2-mro", "requests-mro", "urllib3-mro",
    ],
)
def test_smoke_reports_partial_on_availability_error(monkeypatch, exc, label):
    def raise_it(name):
        raise exc

    patch_seams(monkeypatch, raise_it)

    result = runner.invoke(cli.app, ["smoke"])

    flat = flat_output(result)
    assert result.exit_code == 1
    assert "smoke PARTIAL — wiring 2/3 ok · model check skipped" in flat
    assert type(exc).__name__ in flat  # the cause is named, not just the verdict
    assert str(exc) in flat
    assert "skipped" in result.output  # the step line is kept …
    assert "cache" in result.output  # … with the actionable remedy
    assert "smoke passed" not in result.output


def test_smoke_reports_partial_on_real_hub_exception(monkeypatch):
    exc = real_hub_error()
    if exc is None:
        pytest.skip("huggingface_hub not importable in this venv")

    def raise_it(name):
        raise exc

    patch_seams(monkeypatch, raise_it)

    result = runner.invoke(cli.app, ["smoke"])

    assert result.exit_code == 1
    assert "smoke PARTIAL" in flat_output(result)
    assert "smoke passed" not in result.output


# ── other model failures → smoke FAILED, exit 1 ───────────────────────────────


def test_smoke_reports_failed_on_checkpoint_mismatch(monkeypatch):
    message = (
        "gpt2: 3 weight(s) missing from the checkpoint and randomly initialised "
        "(shared_experts, hc_head)"
    )

    def raise_it(name):
        raise RuntimeError(message)  # what evaluate.py:71 raises on a mismatched ckpt

    patch_seams(monkeypatch, raise_it)

    result = runner.invoke(cli.app, ["smoke"])

    flat = flat_output(result)
    assert result.exit_code == 1
    assert "smoke FAILED" in flat
    assert "RuntimeError" in flat
    assert "randomly initialised" in flat
    assert "smoke PARTIAL" not in result.output
    assert "smoke passed" not in result.output


def test_smoke_reports_failed_on_scoring_error(monkeypatch):
    def broken_scorer(loaded, items, batch_size=16, aggregation="sum", progress=None):
        raise ValueError("pair 3 is incomplete — both variants must be scored")

    patch_seams(monkeypatch, fake_load_model, broken_scorer)

    result = runner.invoke(cli.app, ["smoke"])

    flat = flat_output(result)
    assert result.exit_code == 1
    assert "smoke FAILED" in flat
    assert "ValueError" in flat
    assert "both variants must be scored" in flat
    assert "smoke passed" not in result.output


# ── our-bug classes propagate, never read as 'skipped' ────────────────────────


@pytest.mark.parametrize(
    "exc",
    [
        NameError("name 'score_pairs' is not defined"),
        AttributeError("module has no attribute 'score_pairs'"),
        ImportError("cannot import name 'score_pairs'"),
        TypeError("score_pairs() got an unexpected keyword argument"),
    ],
    ids=["NameError", "AttributeError", "ImportError", "TypeError"],
)
def test_smoke_reraises_our_bug_classes(monkeypatch, exc):
    def raise_it(name):
        raise exc  # the same tuple sweep() re-raises at cli.py:290

    patch_seams(monkeypatch, raise_it)

    result = runner.invoke(cli.app, ["smoke"])

    assert result.exit_code == 1
    assert isinstance(result.exception, type(exc))  # propagated, not converted to exit
    assert not isinstance(result.exception, SystemExit)
    assert "PARTIAL" not in result.output
    assert "FAILED" not in result.output
    assert "smoke passed" not in result.output
    assert "skipped" not in result.output


# ── the classifier itself ─────────────────────────────────────────────────────


def test_classifier_matches_module_prefixes_without_imports():
    assert cli._is_availability_error(ConnectionError("x"))
    assert cli._is_availability_error(TimeoutError("x"))
    for module in (
        "huggingface_hub", "huggingface_hub.errors", "httpx", "httpx2",
        "requests", "requests.exceptions", "urllib3",
    ):
        assert cli._is_availability_error(error_from_module(module, "x")), module


def test_classifier_rejects_our_bugs_and_plain_failures():
    for exc in (
        RuntimeError("x"), ValueError("x"), AssertionError("x"),
        OSError("disk full"), KeyError("x"),
    ):
        assert not cli._is_availability_error(exc), type(exc).__name__


def test_classifier_accepts_real_hub_exception_mro():
    exc = real_hub_error()
    if exc is None:
        pytest.skip("huggingface_hub not importable in this venv")
    assert not isinstance(exc, (ConnectionError, TimeoutError))
    assert cli._is_availability_error(exc)
