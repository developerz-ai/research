"""Scaffold tests — the harness is wired and its contracts hold.

These deliberately test no measurement: no measurement code exists yet. When the
first experiment module lands, its contract tests land beside it in this directory.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from {{PKG}} import provenance
from {{PKG}}.device import get_device_info


def test_device_resolves():
    info = get_device_info()
    assert info.backend in ("cuda", "rocm", "xpu", "cpu")
    assert info.device is not None


def test_cpu_path_is_reachable(monkeypatch: pytest.MonkeyPatch):
    """Every experiment must run on CPU — it is the correctness reference."""
    monkeypatch.setenv("RESEARCH_DEVICE", "cpu")
    info = get_device_info()
    assert info.backend == "cpu"
    assert info.device.type == "cpu"
    assert not info.is_accelerated


def test_run_record_round_trip(tmp_path: Path):
    """A record survives write -> load, and results stay append-only."""
    record = provenance.RunRecord(
        experiment="E000-smoke",
        seed=7,
        config={"limit": 3, "seed": 7},
        metrics={"wired": 1.0},
        items=[{"i": i, "ok": True} for i in range(3)],
    )
    path = record.write(tmp_path / "E000-seed7.json")
    loaded = provenance.load(path)
    assert loaded["seed"] == 7
    assert loaded["config"] == {"limit": 3, "seed": 7}
    assert loaded["items"] == [{"i": i, "ok": True} for i in range(3)]
    assert loaded["git_sha"]
    with pytest.raises(FileExistsError):
        record.write(path)


def test_run_record_concurrent_writers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Both writers reach serialization; only one may create the measurement."""
    barrier = Barrier(2)
    monkeypatch.setattr(provenance, "git_sha", lambda: "test-sha")

    def hardware():
        barrier.wait(timeout=10)
        return {"accelerator": "test"}

    monkeypatch.setattr(provenance, "hardware", hardware)
    path = tmp_path / "E000-race.json"

    def write(seed):
        record = provenance.RunRecord("E000", seed, {"seed": seed}, items=[{"seed": seed}])
        try:
            record.write(path)
        except FileExistsError:
            return None
        return seed

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, [1, 2]))
    winners = [seed for seed in results if seed is not None]
    assert len(winners) == 1
    loaded = provenance.load(path)
    assert loaded["seed"] == winners[0]
    assert loaded["items"] == [{"seed": winners[0]}]
