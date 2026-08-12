"""Run records.

A number without one of these is not a result. Every run writes seed, git SHA, hardware,
full config, and per-item outputs — the per-item data is what lets a result be re-analysed
later without re-running it.
"""

from __future__ import annotations

import datetime as dt
import json
import platform
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


def git_sha(repo: Path | None = None) -> str:
    """Short SHA, with a ``-dirty`` suffix when the worktree has uncommitted changes."""
    cwd = repo or Path(__file__).resolve().parent
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=cwd, capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return f"{sha}-dirty" if dirty else sha
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def hardware() -> dict[str, Any]:
    from .device import get_device_info

    info = get_device_info()
    return {
        "platform": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
        "python": platform.python_version(),
        "accelerator": info.as_dict(),
    }


@dataclass
class RunRecord:
    """One experiment run, serialised whole."""

    experiment: str
    seed: int
    config: dict[str, Any]
    metrics: dict[str, Any] = field(default_factory=dict)
    items: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""

    def write(self, path: Path) -> Path:
        """Write the record. Refuses to overwrite — results are append-only."""
        path = Path(path)
        if path.exists():
            raise FileExistsError(
                f"{path} exists. Results are append-only; pick a new filename rather than "
                "silently replacing a measurement."
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "experiment": self.experiment,
            "timestamp_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            "git_sha": git_sha(),
            "seed": self.seed,
            "hardware": hardware(),
            "config": self.config,
            "metrics": self.metrics,
            "notes": self.notes,
            "items": self.items,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8", newline="\n")
        return path


def load(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
