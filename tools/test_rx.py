"""Tests for the dependency-update validation in ``tools/rx.py``.

The check that a uv-managed project stays discoverable — and stays *correctly*
described — by the updater is the only machine guard on the Dependabot
configuration, and until now no test pinned it: deleting ``_check_dependency_updates``
and ``_lock_divergences`` outright would leave the suite green. These tests drive the
validation against a synthetic tree so each failure mode is asserted separately.

The harness tests pin ``rx test`` and the suites inside ``rx check``. The runner is
faked, so no test spawns a real pytest and none of them reach the network.

The scaffold tests drive ``cmd_new_project`` against the real ``templates/``
directory, so template drift fails here instead of at the next project's
creation.

The gate tests pin ``bin/check``'s contents: every ``projects/NNN-*`` directory
keeps its ruff and pytest step, and the root tools env keeps an exact pytest pin
— CI only sees the gate's exit code, so these are what stop it silently
shrinking. The gate itself runs with a stubbed ``uv``, so its 75/1 exit-code
contract, its echoed success output, and the canonical command it starts get
failing tests of their own.

Run from the repo root:

    uv run --with 'pytest==9.2.0' pytest tools/test_rx.py -q
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

# tools/ is not a package; load rx.py straight from its file.
_RX_PATH = Path(__file__).resolve().parent / "rx.py"
_spec = importlib.util.spec_from_file_location("rx_under_test", _RX_PATH)
assert _spec and _spec.loader
rx = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = rx
_spec.loader.exec_module(rx)


# ── fixtures ───────────────────────────────────────────────────────────────────

DEPENDABOT = """\
version: 2
updates:
  - package-ecosystem: "{ecosystem}"
    directory: "{directory}"
    schedule:
      interval: "weekly"
      day: "thursday"
      time: "01:00"
    cooldown:
      default-days: 14
    groups:
      uv-minor-and-patch:
        patterns: ["*"]
        update-types: ["minor", "patch"]
"""

PYPROJECT = """\
[project]
name = "{name}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["numpy>=1.26", "torch>=2.5"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.uv]
dev-dependencies = []

[[tool.uv.index]]
name = "pytorch"
url = "https://example.test/whl/cu126"
explicit = true

[tool.uv.sources]
torch = [{{ index = "pytorch" }}]
"""

UV_LOCK = """\
version = 1
revision = 1
requires-python = ">=3.11"

[[package]]
name = "{name}"
version = "0.1.0"
source = {{ editable = "." }}
dependencies = [
    {{ name = "numpy" }},
    {{ name = "torch" }},
]

[package.optional-dependencies]
dev = [
    {{ name = "pytest" }},
]

[package.metadata]
requires-dist = [
    {{ name = "numpy", specifier = ">=1.26" }},
    {{ name = "torch", specifier = ">=2.5", index = "https://example.test/whl/cu126" }},
    {{ name = "pytest", marker = "extra == 'dev'", specifier = ">=8.0" }},
]
"""


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _make_tree(
    tmp_path: Path,
    *,
    ecosystem: str = "uv",
    with_lock: bool = True,
    lock_name: str | None = None,
    project: str = "001-test-project",
    package: str = "testpkg",
) -> Path:
    """Build a fake repo root: .github/dependabot.yml + projects/<name>/."""
    _write(
        tmp_path / ".github" / "dependabot.yml",
        DEPENDABOT.format(ecosystem=ecosystem, directory=f"/projects/{project}"),
    )
    project_dir = tmp_path / "projects" / project
    _write(project_dir / "pyproject.toml", PYPROJECT.format(name=package))
    if with_lock:
        _write(project_dir / (lock_name or "uv.lock"), UV_LOCK.format(name=package))
    return tmp_path


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point rx.ROOT and rx.PROJECTS at a synthetic tree for one test.

    The tree starts in the passing shape: a uv-managed project, a 'uv' Dependabot
    entry for its directory, and a committed uv.lock whose recorded requirements
    match the manifest. Each test then breaks exactly one thing.
    """
    monkeypatch.setattr(rx, "ROOT", tmp_path)
    monkeypatch.setattr(rx, "PROJECTS", tmp_path / "projects")
    _make_tree(tmp_path)
    return tmp_path


def _problems() -> list[str]:
    problems: list[str] = []
    rx._check_dependency_updates(problems)
    return problems


# ── the happy path ────────────────────────────────────────────────────────────


def test_uv_managed_project_with_uv_entry_and_lock_is_clean(tree: Path) -> None:
    """The passing shape: ecosystem 'uv', an entry for the directory, a committed lock."""
    assert _problems() == []


def test_project_without_tool_uv_is_not_uv_managed(tree: Path) -> None:
    """A project with no [tool.uv] table is out of scope for the uv ecosystem."""
    _write(
        tree / "projects" / "002-plain" / "pyproject.toml",
        '[project]\nname = "plain"\nversion = "0.1.0"\n',
    )
    assert _problems() == []


def test_missing_dependabot_manifest_is_reported_when_uv_projects_exist(tree: Path) -> None:
    """Deleting the config must not silently disable the whole check.

    With a uv-managed project in the tree, a missing .github/dependabot.yml means
    the updater discovers nothing — that is a problem, not a pass.
    """
    (tree / ".github" / "dependabot.yml").unlink()
    problems = _problems()
    assert len(problems) == 1
    assert "missing" in problems[0]
    assert "001-test-project" in problems[0]


def test_missing_dependabot_manifest_with_no_uv_projects_is_still_clean(tree: Path) -> None:
    """The config is only required once there is something for an updater to discover."""
    (tree / ".github" / "dependabot.yml").unlink()
    _write(
        tree / "projects" / "001-test-project" / "pyproject.toml",
        '[project]\nname = "testpkg"\nversion = "0.1.0"\n',
    )
    assert _problems() == []


def test_dependabot_manifest_without_updates_entries_is_reported(tree: Path) -> None:
    """A present-but-empty manifest is the same silent pass as a deleted one."""
    _write(tree / ".github" / "dependabot.yml", "version: 2\nupdates: []\n")
    problems = _problems()
    assert len(problems) == 1
    assert "no updates entries" in problems[0]
    assert "001-test-project" in problems[0]


# ── each failure mode, separately ─────────────────────────────────────────────


def test_non_uv_ecosystem_is_reported(tree: Path) -> None:
    """A uv-managed project named under another ecosystem is not discoverable."""
    _write(
        tree / ".github" / "dependabot.yml",
        DEPENDABOT.format(ecosystem="pip", directory="/projects/001-test-project"),
    )
    problems = _problems()
    assert len(problems) == 1
    assert "package-ecosystem 'pip'" in problems[0]
    assert "001-test-project" in problems[0]


def test_missing_uv_lock_is_reported(tree: Path) -> None:
    """The uv ecosystem has nothing to discover without a committed lockfile."""
    (tree / "projects" / "001-test-project" / "uv.lock").unlink()
    problems = _problems()
    assert len(problems) == 1
    assert "uv.lock" in problems[0]
    assert "missing" in problems[0]


def test_missing_updates_entry_is_reported(tree: Path) -> None:
    """A uv-managed project with no Dependabot entry is never discovered."""
    _write(
        tree / ".github" / "dependabot.yml",
        'version: 2\nupdates:\n  - package-ecosystem: "uv"\n'
        '    directory: "/projects/999-other"\n',
    )
    problems = _problems()
    assert len(problems) == 1
    assert "no updates entry" in problems[0]
    assert "001-test-project" in problems[0]


def test_lock_that_does_not_resolve_its_manifest_is_reported(tree: Path) -> None:
    """A lock without the project's own root package describes some other project."""
    _write(
        tree / "projects" / "001-test-project" / "uv.lock",
        'version = 1\n\n[[package]]\nname = "somebody-else"\nversion = "0.1.0"\n',
    )
    problems = _problems()
    assert len(problems) == 1
    assert "does not describe this project" in problems[0]


def test_invalid_pyproject_toml_is_reported(tree: Path) -> None:
    """Unparseable TOML is reported rather than crashing the check."""
    _write(tree / "projects" / "001-test-project" / "pyproject.toml", "[project\nname =")
    problems = _problems()
    assert len(problems) == 1
    assert "invalid TOML" in problems[0]


# ── a stale lock: the manifest moved, the lock did not ────────────────────────


def test_stale_lock_kept_after_constraint_bump_is_reported(tree: Path) -> None:
    """The named bug: numpy>=1.26 becomes numpy>=2 and the lock is not regenerated.

    The root package name still matches, so a name-only check passes; the
    constraint recorded in requires-dist is what catches it.
    """
    _write(
        tree / "projects" / "001-test-project" / "pyproject.toml",
        PYPROJECT.format(name="testpkg").replace(
            'dependencies = ["numpy>=1.26", "torch>=2.5"]',
            'dependencies = ["numpy>=2", "torch>=2.5"]',
        ),
    )
    problems = _problems()
    assert len(problems) == 1
    assert "'numpy'" in problems[0]
    assert "'>=2'" in problems[0]
    assert "'>=1.26'" in problems[0]


def test_stale_lock_missing_requirement_is_reported(tree: Path) -> None:
    """A requirement added to the manifest after the lock was written has no record."""
    _write(
        tree / "projects" / "001-test-project" / "uv.lock",
        UV_LOCK.format(name="testpkg").replace(
            '    { name = "numpy", specifier = ">=1.26" },\n', "",
        ),
    )
    problems = _problems()
    assert len(problems) == 1
    assert "'numpy'" in problems[0]
    assert "requires-dist" in problems[0]


def test_stale_lock_requires_python_drift_is_reported(tree: Path) -> None:
    """A lock resolved for a different Python floor is stale too."""
    _write(
        tree / "projects" / "001-test-project" / "pyproject.toml",
        PYPROJECT.format(name="testpkg").replace(
            'requires-python = ">=3.11"', 'requires-python = ">=3.12"'
        ),
    )
    problems = _problems()
    assert len(problems) == 1
    assert "requires-python" in problems[0]


def test_stale_lock_index_source_drift_is_reported(tree: Path) -> None:
    """uv sources are part of the contract: the lock must record the same index."""
    _write(
        tree / "projects" / "001-test-project" / "pyproject.toml",
        PYPROJECT.format(name="testpkg").replace(
            'url = "https://example.test/whl/cu126"',
            'url = "https://example.test/whl/rocm"',
        ),
    )
    problems = _problems()
    assert len(problems) == 1
    assert "'torch'" in problems[0]
    assert "index" in problems[0]


def test_source_naming_undefined_index_is_reported(tree: Path) -> None:
    """A source pointing at an index the manifest never defines cannot be resolved."""
    _write(
        tree / "projects" / "001-test-project" / "pyproject.toml",
        PYPROJECT.format(name="testpkg").replace(
            'torch = [{ index = "pytorch" }]',
            'torch = [{ index = "nowhere" }]',
        ),
    )
    problems = _problems()
    assert len(problems) == 1
    assert "'nowhere'" in problems[0]


def test_removed_index_source_is_reported(tree: Path) -> None:
    """Deleting the manifest's source declaration must not leave the old pin passing.

    The forward index comparison only visits packages the manifest still names,
    so removing ``torch = [{ index = "pytorch" }]`` used to leave the lock's
    cu126 pin unexamined; the locked side is compared too.
    """
    _write(
        tree / "projects" / "001-test-project" / "pyproject.toml",
        PYPROJECT.format(name="testpkg").replace('torch = [{ index = "pytorch" }]', ""),
    )
    problems = _problems()
    assert len(problems) == 1
    assert "'torch'" in problems[0]
    assert "cu126" in problems[0]
    assert "no index source" in problems[0]


def test_stale_lock_extra_mismatch_is_reported(tree: Path) -> None:
    """An extra added to the manifest after the lock was written is caught by name."""
    _write(
        tree / "projects" / "001-test-project" / "pyproject.toml",
        PYPROJECT.format(name="testpkg").replace(
            'dev = ["pytest>=8.0"]',
            'dev = ["pytest>=8.0", "ruff>=0.6"]',
        ),
    )
    problems = _problems()
    assert len(problems) == 1
    assert "'dev'" in problems[0]


def test_stale_lock_extra_constraint_bump_is_reported(tree: Path) -> None:
    """A constraint bump inside an extra is caught via the extra-scoped requires-dist.

    The lock's ``[package.optional-dependencies]`` carries names only, so bumping
    the manifest from pytest>=8.0 to pytest>=9.0 passes a name-set comparison;
    the specifier lives on the marker-scoped record in requires-dist.
    """
    _write(
        tree / "projects" / "001-test-project" / "pyproject.toml",
        PYPROJECT.format(name="testpkg").replace(
            'dev = ["pytest>=8.0"]',
            'dev = ["pytest>=9.0"]',
        ),
    )
    problems = _problems()
    assert len(problems) == 1
    assert "'pytest'" in problems[0]
    assert "'dev'" in problems[0]
    assert "'>=9.0'" in problems[0]
    assert "'>=8.0'" in problems[0]


# ── duplicate directory entries ───────────────────────────────────────────────


def test_duplicate_directory_entries_are_reported_as_their_own_problem(tree: Path) -> None:
    """Two entries naming one directory are a config bug, not an override pair.

    Collapsing them into a dict keyed by directory would leave one entry
    unvalidated and check the other against the wrong ecosystem.
    """
    _write(
        tree / ".github" / "dependabot.yml",
        DEPENDABOT.format(ecosystem="uv", directory="/projects/001-test-project")
        + DEPENDABOT.format(ecosystem="pip", directory="/projects/001-test-project"),
    )
    problems = _problems()
    assert len(problems) == 2
    duplicate = next(p for p in problems if "same directory" in p)
    assert "001-test-project" in duplicate
    # Both entries are named, so neither can be silently dropped.
    assert "'uv'" in duplicate
    assert "'pip'" in duplicate
    # And the wrong ecosystem is still reported against its own entry.
    assert any("package-ecosystem 'pip'" in p for p in problems)


def test_duplicate_identical_entries_are_still_reported(tree: Path) -> None:
    """An exact copy-paste duplicate is the same bug and gets the same problem."""
    entry = DEPENDABOT.format(ecosystem="uv", directory="/projects/001-test-project")
    _write(tree / ".github" / "dependabot.yml", entry + entry)
    problems = _problems()
    assert len(problems) == 1
    assert "same directory" in problems[0]


def test_distinct_directories_are_not_duplicates(tree: Path) -> None:
    """Two projects, two entries, two directories — nothing to report."""
    _make_tree(
        tree,
        ecosystem="uv",
        project="002-other-project",
        package="otherpkg",
    )
    _write(
        tree / ".github" / "dependabot.yml",
        DEPENDABOT.format(ecosystem="uv", directory="/projects/001-test-project")
        + DEPENDABOT.format(ecosystem="uv", directory="/projects/002-other-project"),
    )
    assert _problems() == []


# ── _lock_divergences, directly ───────────────────────────────────────────────


def test_lock_divergences_empty_for_matching_lock(tmp_path: Path) -> None:
    pyproject = _write(tmp_path / "pyproject.toml", PYPROJECT.format(name="testpkg"))
    lock = _write(tmp_path / "uv.lock", UV_LOCK.format(name="testpkg"))
    assert rx._lock_divergences(pyproject, lock) == []


def test_lock_divergences_names_the_root_package(tmp_path: Path) -> None:
    pyproject = _write(tmp_path / "pyproject.toml", PYPROJECT.format(name="testpkg"))
    lock = _write(
        tmp_path / "uv.lock",
        'version = 1\n\n[[package]]\nname = "other"\nversion = "0.1.0"\n',
    )
    divergences = rx._lock_divergences(pyproject, lock)
    assert len(divergences) == 1
    assert "testpkg" in divergences[0]


def test_lock_divergences_for_unparseable_lock(tmp_path: Path) -> None:
    pyproject = _write(tmp_path / "pyproject.toml", PYPROJECT.format(name="testpkg"))
    lock = _write(tmp_path / "uv.lock", "not = [toml")
    assert rx._lock_divergences(pyproject, lock) != []


def test_lock_divergences_when_manifest_has_no_name(tmp_path: Path) -> None:
    pyproject = _write(tmp_path / "pyproject.toml", '[project]\nversion = "0.1.0"\n')
    lock = _write(tmp_path / "uv.lock", UV_LOCK.format(name="testpkg"))
    assert rx._lock_divergences(pyproject, lock) != []


def test_lock_divergences_compare_specifiers_not_just_names(tmp_path: Path) -> None:
    """The regression this exists for: same root package, old constraint."""
    pyproject = _write(
        tmp_path / "pyproject.toml",
        PYPROJECT.format(name="testpkg").replace(
            'dependencies = ["numpy>=1.26", "torch>=2.5"]',
            'dependencies = ["numpy>=2", "torch>=2.5"]',
        ),
    )
    lock = _write(tmp_path / "uv.lock", UV_LOCK.format(name="testpkg"))
    divergences = rx._lock_divergences(pyproject, lock)
    assert any("'numpy'" in d and "'>=2'" in d and "'>=1.26'" in d for d in divergences)


# ── bin/check: the gate's contents are pinned, not just its exit code ───────

GATE_SCRIPT = _RX_PATH.parent.parent / "bin" / "check"

# Every projects/NNN-* directory must be gated by bin/check: CI only sees the
# gate's exit code, so a project — or one half of its check — dropped from the
# script would otherwise shrink the suite with CI staying green.
GATED_PROJECTS = sorted(
    p.name
    for p in (_RX_PATH.parent.parent / "projects").iterdir()
    if p.is_dir() and re.match(r"\d{3}-", p.name)
)


def _gate_steps_for(project: str, fragment: str) -> list[str]:
    """Lines of bin/check that pair a project directory with a check fragment."""
    gate = GATE_SCRIPT.read_text(encoding="utf-8")
    return [ln for ln in gate.splitlines() if f"projects/{project}" in ln and fragment in ln]


@pytest.mark.parametrize("project", GATED_PROJECTS)
def test_bin_check_runs_ruff_for_every_project(project: str) -> None:
    """Each project keeps its ruff step, reached only after its cd succeeds."""
    lines = _gate_steps_for(project, "uv run --extra dev ruff check .")
    assert lines, f"no ruff step for {project} in bin/check"
    assert any("&&" in ln for ln in lines), (
        f"the ruff step for {project} no longer requires its cd to succeed"
    )


@pytest.mark.parametrize("project", GATED_PROJECTS)
def test_bin_check_runs_pytest_for_every_project(project: str) -> None:
    """Each project keeps its pytest step."""
    assert _gate_steps_for(project, "uv run --extra dev pytest -q"), (
        f"no pytest step for {project} in bin/check"
    )


def test_bin_check_pins_the_tools_pytest() -> None:
    """`uv run --with pytest` resolves latest-at-run-time — that must not float.

    The gate's own runner is installed fresh on every CI run, so an exact pin is
    what keeps a new pytest release from turning every unrelated change red —
    and the pin must be a version the projects' locks actually record (the pin
    follows the projects' lock), not any exact number someone typed in.
    """
    gate = GATE_SCRIPT.read_text(encoding="utf-8")
    match = re.search(
        r"--with(?:[ \t]+|[ \t]*=[ \t]*)['\"]?pytest==(\d+\.\d+\.\d+)", gate
    )
    assert match, "bin/check runs an unpinned --with pytest"
    locked = {
        pkg["version"]
        for lock in (_RX_PATH.parent.parent / "projects").glob("*/uv.lock")
        for pkg in tomllib.loads(lock.read_text(encoding="utf-8")).get("package", [])
        if pkg.get("name") == "pytest"
    }
    assert locked, "no projects/*/uv.lock records a pytest version for the gate to follow"
    assert match.group(1) in locked, (
        f"gate pin pytest=={match.group(1)} is recorded by no projects' uv.lock "
        f"(locked pytest versions: {sorted(locked)})"
    )


# ── package resolution: nothing this repo owns may resolve a package at latest ─

# A package spec without a version is resolved by its index at run time: the
# newest publish, every time, with the developer's environment in scope. The
# gate's pytest is pinned above; the copies of that command — the skills, the
# commands, the docs a reviewer copies from — have to be pinned too.
#
# The platform's setup template owns four files: the merge proof accepts only
# the platform's own bytes for them, so this repo cannot pin what they run —
# their drift belongs in the platform's template, in a separate pull request.
PLATFORM_OWNED_FILES = frozenset(
    {
        ".dz/maintainer/maintainer.yml",
        ".dz/maintainer/reviewer.md",
        ".github/workflows/ci.yml",
        ".mcp.json",
    }
)

# They are not unchecked, though — they are scanned too, against this list. A
# package spec that still floats in one of them is an open defect with a named
# route; a spec that is NOT on this list fails the gate. Excluding those files
# outright is what let .mcp.json launch an unpinned package with the
# developer's SENTRY_ACCESS_TOKEN and DEVELOPERZ_API_KEY in scope, unnoticed.
#
# (file, spec) -> the record of the open defect: who owns the fix, and how it
# is fixed. The record is read by the test below, so it cannot rot into an
# inert note — an entry without a route is a defect nobody can act on, and an
# entry whose spec the platform has since pinned is stale and must be dropped.
PLATFORM_OWNED_FLOATING_SPECS = {
    (
        ".dz/maintainer/reviewer.md",
        "--with pytest",
    ): {
        "owner": "the platform's setup template",
        "route": (
            "pin the gate's pytest — tools/test_rx.py runs pytest==9.2.0"
        ),
    },
    (
        ".mcp.json",
        "bunx @sentry/mcp-server",
    ): {
        "owner": "the platform's setup template",
        "route": (
            "pin @sentry/mcp-server in .mcp.json's args to a FULL three-component "
            "version — `bunx @sentry/mcp-server@0.49.0`: bun and npm both read a "
            "partial version as a range (`@1` is 1.x and serves the newest match), "
            "so `@1` is not a pin; 0.49.0 was the registry's latest on 2026-11-12, "
            "re-check registry.npmjs.org/@sentry/mcp-server/latest — it starts "
            "at every agent start with the developer's SENTRY_ACCESS_TOKEN and "
            "DEVELOPERZ_API_KEY in scope"
        ),
    },
}

# Directories that hold no repo content: caches, venvs, the raw corpus, scratch.
SCAN_SKIP_DIRS = frozenset(
    {
        ".codegraph",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "node_modules",
        "venv",
    }
)
SCAN_SKIP_PATHS = frozenset({"library/corpus", "tmp"})
SCAN_SUFFIXES = frozenset(
    {".cfg", ".ini", ".json", ".md", ".sh", ".toml", ".txt", ".yaml", ".yml"}
)
# Extensionless files: the repo's own scripts.
SCAN_SCRIPT_DIRS = frozenset({".githooks", "bin"})
# Named files whose text the suffix does not say: the env template. A floating
# spec must not be able to hide in a name the suffix list forgot.
SCAN_NAMES = frozenset({".env.example"})
# The developer's own local files — credentials, not the repo's. Never read.
SCAN_SKIP_NAMES = frozenset(
    {".env", ".git-credentials", ".netrc", ".npmrc", ".pypirc"}
)

REPO_ROOT = _RX_PATH.parent.parent
_THIS_FILE = Path(__file__).resolve().relative_to(REPO_ROOT).as_posix()


def _is_repo_text(path: Path, rel_dir: str) -> bool:
    """True when the file is one of the repo's own text files.

    The suffix list covers the formats the repo writes. A file with no suffix
    at all — the repo's own scripts, .gitignore, .gitattributes — is text too,
    and so is a named dot-config: a floating spec that hides in a name the
    suffix list forgot is still a floating spec. The developer's local
    credentials are not the repo's and are never read.
    """
    if path.name in SCAN_SKIP_NAMES:
        return False
    if path.suffix in SCAN_SUFFIXES or path.name in SCAN_NAMES:
        return True
    return path.suffix == "" or rel_dir in SCAN_SCRIPT_DIRS


def _text_files(*, platform_owned: bool) -> list[tuple[str, str]]:
    """Every (repo-relative path, text) this repo owns and can edit.

    `platform_owned=False` — the repo's own files, the platform's excluded.
    `platform_owned=True` — only the platform-owned files.
    """
    found: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        rel_dir = Path(dirpath).relative_to(REPO_ROOT).as_posix()
        keep = []
        for name in dirnames:
            child = name if rel_dir == "." else f"{rel_dir}/{name}"
            if name in SCAN_SKIP_DIRS or child in SCAN_SKIP_PATHS:
                continue
            keep.append(name)
        dirnames[:] = sorted(keep)
        for name in sorted(filenames):
            path = Path(dirpath) / name
            rel = path.relative_to(REPO_ROOT).as_posix()
            if (rel in PLATFORM_OWNED_FILES) != platform_owned:
                continue
            if rel == _THIS_FILE:
                continue
            if not _is_repo_text(path, rel_dir):
                continue
            try:
                found.append((rel, path.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError):
                continue
    return found


def _repo_owned_text_files() -> list[tuple[str, str]]:
    """Every (repo-relative path, text) this repo owns and can edit."""
    return _text_files(platform_owned=False)


# `--with pytest` (no version) pulls whatever the index serves newest, and
# `--with=pytest` is that same command in another spelling — uv accepts both,
# so both are read.
_UNPINNED_WITH = re.compile(
    r"--with(?:[ \t]+|[ \t]*=[ \t]*)['\"]?([A-Za-z0-9_.\-=]+)"
)

# A runner executes the package it is handed and the index decides which
# publish that is. The move hides behind several names: `bun x` is `bunx`,
# `pnpm dlx` and `npm exec` are npx under another word, `uvx --from pkg tool`
# names the package in a flag, and `uv tool run pkg` is uvx spelled out. A
# flag may also sit between the runner and the package (`bunx --bun pkg`), and
# the package may carry a comparator (`uvx pkg==1.2.3`). Reading only
# "npx | bunx | uvx" leaves the class an open door: the next file to use
# another spelling runs an unpinned publish again and this gate says nothing.
_RUNNER_PATTERNS = (
    re.compile(r"\b(?:bunx|bun[ \t]+x|npx|pnpx|uvx)\b"),
    re.compile(r"\b(?:pnpm|npm|yarn)[ \t]+(?:dlx|exec)\b"),
    re.compile(r"\buv[ \t]+tool[ \t]+(?:run|install)\b"),
)
# Flags whose value IS the package: `uvx --from ruff==0.1.0 ruff`,
# `npm exec --package=@scope/pkg@1.2.3 -- cmd`. The value may be attached with
# `=` or given as the next word, and npm may repeat the flag.
_PACKAGE_FLAGS = frozenset({"--from", "--package", "--pkg"})
# `-p` is the short spelling of `--package` for npm and bunx — both measured
# in their own --help output — but for uvx it is `--python`, so it names the
# package only for the runners that spell it that way. Reading it for uvx
# would name a Python version a package.
_NPM_SHORT_PACKAGE_FLAG = "-p"
# The uv runners, whose `-p` is --python.
_UV_RUNNERS = frozenset({"uv", "uvx"})
# Punctuation prose leaves around a command: quotes, backticks, brackets.
_PROSE_PUNCTUATION = "\"'`(),.;"
# What a package spec looks like on a command line: an npm name — scoped or
# not — with an optional version or version range and an optional comparator.
_PACKAGE_TOKEN = re.compile(
    r"^(?:@[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+|[A-Za-z0-9][A-Za-z0-9_.\-]*)"
    r"(?:@[^\s]+)?(?:[<>=!~][^\s]+)?$"
)

# A server config names its runner in "command" and the package in "args", so
# the pair has to be read as a pair: "bunx" alone says nothing, "bunx
# @sentry/mcp-server" says the newest publish runs with the caller's secrets.
PACKAGE_RUNNERS = frozenset({"bunx", "dlx", "npx", "pnpx", "uvx"})
EXEC_COMMANDS = frozenset({"dlx", "exec"})
# `bun x pkg` is `bunx pkg` — the same runner under its long spelling.
BUN_LONG_FORM = "x"
# `npm exec pkg`, `pnpm dlx pkg`, `yarn dlx pkg`: the runner is the manager.
NPM_MANAGERS = frozenset({"npm", "pnpm", "yarn"})


def _package_token(word: str) -> str | None:
    """The package spec in `word`, or None when it names no package."""
    word = word.strip(_PROSE_PUNCTUATION)
    return word if _PACKAGE_TOKEN.match(word) else None


def _packages_after_words(
    words: list[str], start: int, runner: str = ""
) -> list[str]:
    """The package specs the words from `start` on name.

    Flags are skipped — except the ones whose value IS the package
    (`uvx --from pkg tool`, `npm exec --package=pkg -- cmd`): their value may
    be attached with `=` or given as the next word, and npm may repeat the
    flag, so every value is read. A word that is only punctuation the prose
    left around the runner is skipped too. Once a flag named the package, the
    words after it are the command it runs, not another package; with no such
    flag, the first real word that names a package is it — and the first real
    word that names none ends the scan, so a config's own keys are never read
    as one.
    """
    package_flags = _PACKAGE_FLAGS
    if runner.split(" ")[0] not in _UV_RUNNERS:
        package_flags = package_flags | {_NPM_SHORT_PACKAGE_FLAG}
    specs: list[str] = []
    index = start
    while index < len(words):
        word = words[index].strip(_PROSE_PUNCTUATION)
        if not word:
            index += 1
            continue
        if word.startswith("-"):
            flag, separator, value = word.partition("=")
            if separator and flag in package_flags:
                token = _package_token(value)
                if token:
                    specs.append(token)
                index += 1
                continue
            if word in package_flags and index + 1 < len(words):
                token = _package_token(words[index + 1])
                if token:
                    specs.append(token)
                index += 2
                continue
            index += 1
            continue
        if not specs:
            token = _package_token(word)
            if token:
                specs.append(token)
        break
    return specs


def _runner_package_specs(data: object) -> list[tuple[str, str]]:
    """(runner, package spec) of every config entry that runs a package."""
    specs: list[tuple[str, str]] = []
    if isinstance(data, dict):
        command = data.get("command")
        args = data.get("args")
        if isinstance(command, str) and isinstance(args, list):
            words = [a for a in args if isinstance(a, str)]
            name = Path(command).name
            if name in PACKAGE_RUNNERS:
                packages = _packages_after_words(words, 0, name)
                runner = name
            elif name == "bun" and words[:1] == [BUN_LONG_FORM]:
                packages = _packages_after_words(words, 1, f"bun {BUN_LONG_FORM}")
                runner = f"bun {BUN_LONG_FORM}"
            elif (
                name in NPM_MANAGERS
                and words[:1]
                and words[0] in EXEC_COMMANDS
            ):
                packages = _packages_after_words(words, 1, f"{name} {words[0]}")
                runner = f"{name} {words[0]}"
            else:
                packages, runner = [], name
            for package in packages:
                specs.append((runner, package))
        for value in data.values():
            specs.extend(_runner_package_specs(value))
    elif isinstance(data, list):
        for value in data:
            specs.extend(_runner_package_specs(value))
    return specs


def _text_package_specs(text: str) -> list[tuple[str, str]]:
    """(runner, package spec) of every package a runner in `text` executes."""
    specs: list[tuple[str, str]] = []
    for pattern in _RUNNER_PATTERNS:
        for match in pattern.finditer(text):
            line = text[match.end():].split("\n", 1)[0]
            runner = " ".join(match.group(0).split())
            for package in _packages_after_words(line.split(), 0, runner):
                specs.append((runner, package))
    return specs


# An exact version names one publish and no other. Two grammars, two rules:
#
#   PEP 440 (uv) — `pkg==1.2.3`. `pkg==1` counts too: PEP 440 zero-pads it
#   to 1.0.0, so it names one publish (packaging: `==1` matches 1.0.0, not
#   1.0.1).
#
#   npm (bunx, npx) — `pkg@1.2.3`. npm reads a PARTIAL version as a range:
#   `@1` is `1.x` and `@1.2` is `1.2.x`, and the index then serves the newest
#   publish that matches — `npm view semver@1 version` lists 20 of them,
#   where `npm view semver@1.1.4 version` lists exactly one. An npm pin
#   therefore needs all three components: `@1` is a range wearing a pin's
#   clothes, and a gate that read it as exact would call a floating spec
#   pinned — the class this whole gate exists to catch.
#
# Both patterns match the WHOLE spec, so a spec carrying a second constraint
# (`pkg==1.2.3||2.0.0`) names more than one publish and is not a pin either.
_PEP440_PIN = re.compile(r"^[^=!<>\s]*==\d+(?:\.\d+)*(?:[-+][0-9A-Za-z.\-]+)?$")
_NPM_PIN = re.compile(
    r"^@?[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)?@\d+\.\d+\.\d+"
    r"(?:[-+][0-9A-Za-z.\-]+)?$"
)


def _names_an_exact_version(spec: str) -> bool:
    """True when a package spec pins one publish (``==`` for uv, ``@`` for npm)."""
    return bool(_PEP440_PIN.match(spec) or _NPM_PIN.match(spec))


def _floating_specs(rel: str, text: str) -> list[str]:
    """Every package spec in `text` that its index resolves at run time."""
    floating: list[str] = []
    for match in _UNPINNED_WITH.finditer(text):
        if not _names_an_exact_version(match.group(1)):
            floating.append(f"--with {match.group(1)}")
    for runner, package in _text_package_specs(text):
        if not _names_an_exact_version(package):
            floating.append(f"{runner} {package}")
    if rel.endswith(".json"):
        try:
            data = json.loads(text)
        except ValueError:
            data = None
        for runner, package in _runner_package_specs(data):
            if not _names_an_exact_version(package):
                floating.append(f"{runner} {package}")
    return floating


# ── the guard for the class, tested where the class is detected ──────────────
#
# The gates below are only as good as the detection under them. A regex that
# stops reading one spelling of "run the newest publish" opens the door again,
# and nothing else in this suite would notice: the gate would go on reporting
# "clean" while a file ran an unpinned package with the caller's secrets in
# scope. These tests pin the spellings, so a future edit to the detection
# cannot quietly narrow it.


_RUNNER_FORMS = [
    "bunx @sentry/mcp-server",
    "bun x @sentry/mcp-server",
    "npx @sentry/mcp-server",
    "pnpx @sentry/mcp-server",
    "uvx @sentry/mcp-server",
    "pnpm dlx @sentry/mcp-server",
    "npm exec @sentry/mcp-server",
    "yarn dlx @sentry/mcp-server",
    "uv tool run @sentry/mcp-server",
    "bunx --bun @sentry/mcp-server",
    "uvx --from @sentry/mcp-server tool",
    "uvx --from=@sentry/mcp-server tool",
    "npm exec --package=@sentry/mcp-server -- sentry-mcp",
    "bunx --package=@sentry/mcp-server sentry-mcp",
    "npx -p @sentry/mcp-server sentry-mcp",
]


@pytest.mark.parametrize("form", _RUNNER_FORMS)
def test_every_runner_spelling_is_read_as_a_floating_package(form: str) -> None:
    """Each way of running a package at run time is caught, not just npx/bunx."""
    assert _floating_specs("notes.md", form), form


@pytest.mark.parametrize(
    "form",
    [
        "bunx @sentry/mcp-server@0.49.0",
        "bun x @sentry/mcp-server@0.49.0",
        "npx @sentry/mcp-server@0.49.0",
        "uvx @sentry/mcp-server==0.49.0",
        "bunx --bun @sentry/mcp-server@0.49.0",
        "uvx --from @sentry/mcp-server==0.49.0 tool",
        "uvx --from=ruff==0.1.0 ruff",
        "npm exec --package=@sentry/mcp-server@0.49.0 -- sentry-mcp",
        "npm exec --package=is-number@7.0.0 -- is-number",
    ],
)
def test_a_pinned_package_is_not_reported_as_floating(form: str) -> None:
    """A spec with an exact version is a pin — the gate must not cry wolf."""
    assert not _floating_specs("notes.md", form), form


@pytest.mark.parametrize(
    "form",
    [
        "uv run --with=pytest pytest -q",
        "uv run --with='pytest' pytest -q",
    ],
)
def test_the_equals_form_of_with_is_read_as_a_floating_package(form: str) -> None:
    """`--with=pkg` resolves the newest publish, exactly like `--with pkg`.

    The two spellings are the same command, and uv accepts both — a regex that
    reads only the spaced one leaves the class an open door, and nothing else
    in this suite would notice.
    """
    assert _floating_specs("notes.md", form), form


def test_the_equals_form_of_with_with_a_pin_is_not_floating() -> None:
    """`--with=pkg==1.2.3` names one publish — a pin, spelled with `=`."""
    assert not _floating_specs("notes.md", "uv run --with=pytest==9.2.0 pytest -q")


def test_an_inline_package_flag_names_the_package_not_the_command() -> None:
    """`npm exec --package=pkg -- cmd` runs pkg; cmd is not the package.

    Reading the command instead of the package would report the wrong spec —
    and would report a pinned package as floating.
    """
    floating = _floating_specs(
        "notes.md", "npm exec --package=@sentry/mcp-server -- sentry-mcp"
    )
    assert "npm exec @sentry/mcp-server" in floating, floating


@pytest.mark.parametrize(
    "spec",
    [
        "@sentry/mcp-server@1.x",
        "@sentry/mcp-server@^1.2.3",
        "@sentry/mcp-server@latest",
        "@sentry/mcp-server>=1.0",
        "@sentry/mcp-server==1.x",
    ],
)
def test_a_version_range_is_not_an_exact_version(spec: str) -> None:
    """A range still resolves at run time: the index serves the newest match."""
    assert not _names_an_exact_version(spec), spec
    assert _floating_specs("notes.md", f"bunx {spec}"), spec


@pytest.mark.parametrize(
    "spec",
    [
        "@sentry/mcp-server@1",
        "@sentry/mcp-server@1.2",
    ],
)
def test_a_partial_npm_version_is_a_range_not_a_pin(spec: str) -> None:
    """npm reads a partial version as a range: `@1` is `1.x`, `@1.2` is `1.2.x`.

    The index then serves the newest publish that matches — the same defect as
    `@1.x`, wearing a pin's clothes. `npm view semver@1 version` lists 20
    matching publishes; `npm view semver@1.1.4 version` lists exactly one. A
    gate that read `@<digits>` as an exact pin would call that spec pinned,
    which is the class this whole gate exists to catch.
    """
    assert not _names_an_exact_version(spec), spec
    assert _floating_specs("notes.md", f"bunx {spec}"), spec


def test_a_pep440_partial_version_is_still_a_pin() -> None:
    """PEP 440 zero-pads `==1` to 1.0.0, so it names one publish — a pin.

    The two grammars differ here on purpose: npm's partial version is a
    range, PEP 440's is a single version.
    """
    assert _names_an_exact_version("pytest==1")
    assert _names_an_exact_version("pytest==1.2")
    assert not _floating_specs("notes.md", "uvx pytest==1")


@pytest.mark.parametrize(
    "command,args",
    [
        ("bunx", ["@sentry/mcp-server"]),
        ("bun", ["x", "@sentry/mcp-server"]),
        ("bunx", ["--bun", "@sentry/mcp-server"]),
        ("npm", ["exec", "@sentry/mcp-server"]),
        ("pnpm", ["dlx", "@sentry/mcp-server"]),
    ],
)
def test_a_server_config_is_read_as_running_a_package(
    command: str, args: list[str]
) -> None:
    """A config names its runner in "command" and its package in "args"."""
    config = {"mcpServers": {"sentry-mcp": {"command": command, "args": args}}}
    assert _floating_specs("mcp.json", json.dumps(config)), (command, args)


def test_a_pinned_server_config_is_not_reported_as_floating() -> None:
    """The config path reads a pin as a pin too."""
    config = {
        "mcpServers": {
            "sentry-mcp": {"command": "bunx", "args": ["@sentry/mcp-server@0.49.0"]}
        }
    }
    assert not _floating_specs("mcp.json", json.dumps(config))


def test_no_repo_owned_file_resolves_a_package_at_latest() -> None:
    """No file this repo owns may resolve a package at its newest version.

    A floating spec runs whatever the index published when the command ran —
    with the developer's environment in scope. Pin it, or do not run it.
    """
    offenders = [
        f"{rel}: {spec}"
        for rel, text in _repo_owned_text_files()
        for spec in _floating_specs(rel, text)
    ]
    assert not offenders, "packages resolved at latest: " + "; ".join(offenders)


def test_platform_owned_files_resolve_no_unrecorded_package_at_latest() -> None:
    """The platform's own files may not carry an unrecorded floating spec.

    The repo cannot pin what the platform's setup template writes, so the specs
    that still float there are recorded in PLATFORM_OWNED_FLOATING_SPECS, each
    with the route that fixes it. A spec that is not on that list is not a
    recorded defect: it fails here.
    """
    offenders = [
        f"{rel}: {spec}"
        for rel, text in _text_files(platform_owned=True)
        for spec in _floating_specs(rel, text)
        if (rel, spec) not in PLATFORM_OWNED_FLOATING_SPECS
    ]
    assert not offenders, (
        "packages resolved at latest in platform-owned files: " + "; ".join(offenders)
    )


def test_the_scan_reads_every_platform_owned_file() -> None:
    """The platform-owned gate is only as good as the files it read.

    A renamed or missing platform file leaves the offender list empty and the
    gate green, so the scan must prove it read every one of them.
    """
    scanned = {rel for rel, _ in _text_files(platform_owned=True)}
    missing = sorted(PLATFORM_OWNED_FILES - scanned)
    assert not missing, "platform-owned files not scanned: " + ", ".join(missing)


def test_every_recorded_floating_spec_is_live_and_routed() -> None:
    """A recorded defect must still be there, and must say who fixes it.

    The repo cannot pin what the platform's setup template writes, so the record
    is the only handle on it — and a record that lies is worse than no record:
    an entry the platform has already fixed is stale and must be dropped, and
    an entry without an owner and a route is a defect nobody can act on.
    """
    floating = {
        rel: set(_floating_specs(rel, text))
        for rel, text in _text_files(platform_owned=True)
    }
    stale = [
        f"{rel}: {spec}"
        for (rel, spec) in PLATFORM_OWNED_FLOATING_SPECS
        if spec not in floating.get(rel, set())
    ]
    assert not stale, (
        "recorded defects the platform has since fixed — drop the entry: "
        + "; ".join(stale)
    )
    unrouted = [
        f"{rel}: {spec}"
        for (rel, spec), record in PLATFORM_OWNED_FLOATING_SPECS.items()
        if not record.get("owner", "").strip()
        or not record.get("route", "").strip()
    ]
    assert not unrouted, (
        "recorded defects without an owner and a route: " + "; ".join(unrouted)
    )


def test_repo_owned_copies_of_the_gate_pytest_use_the_gates_pin() -> None:
    """A copy of the gate's tools-pytest command must name the gate's pin.

    The gate runs one pytest version; a doc that tells a reviewer to run
    another is not the gate, and a copy that floats is worse — it resolves the
    newest release at run time.
    """
    gate = GATE_SCRIPT.read_text(encoding="utf-8")
    match = re.search(
        r"--with(?:[ \t]+|[ \t]*=[ \t]*)['\"]?pytest==(\d+\.\d+\.\d+)", gate
    )
    assert match, "bin/check runs an unpinned --with pytest"
    gate_pin = match.group(1)
    offenders = [
        f"{rel}: pytest=={quoted}"
        for rel, text in _repo_owned_text_files()
        for quoted in re.findall(
            r"--with(?:[ \t]+|[ \t]*=[ \t]*)['\"]?pytest==([\d.]+)", text
        )
        if quoted != gate_pin
    ]
    assert not offenders, (
        f"copies of the gate's pytest pin disagree with bin/check's {gate_pin}: "
        + "; ".join(offenders)
    )


# ── bin/check's exit-code contract, run with a stubbed uv ──────────────────────

# The 75/1 classification is a behavior of the script, not of its text: reverting
# step() to a bare `&&` chain, or widening the network-phrase grep, leaves every
# content-pinning test above green while misgrading failures. These tests run the
# gate itself against a stub `uv` — every step starts with `uv run`, so one stub
# scripts each scenario with no install and no network. The stub owns `$HOME`:
# the gate prepends `$HOME/.local/bin` to PATH itself, so stubbing the inherited
# PATH alone is shadowed by any real uv installed there.

_STUB_UV = """\
#!/usr/bin/env bash
printf '%s\\n' "$STUB_UV_SAYS"
exit "${STUB_UV_EXIT:-0}"
"""

needs_bash = pytest.mark.skipif(
    shutil.which("bash") is None, reason="bin/check is a bash script"
)


def _run_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    says: str = "",
    exits: int = 0,
    stubs: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    stub_dir = tmp_path / "home" / ".local" / "bin"
    _write(stub_dir / "uv", _STUB_UV).chmod(0o755)
    for name, body in (stubs or {}).items():
        _write(stub_dir / name, body).chmod(0o755)
    monkeypatch.setenv("HOME", str(stub_dir.parent.parent))
    monkeypatch.setenv("PATH", f"{stub_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("STUB_UV_SAYS", says)
    monkeypatch.setenv("STUB_UV_EXIT", str(exits))
    # The gate cds to the repo root itself; the stub shadows only `uv` (plus any
    # named `stubs`), so git, grep and the rest resolve normally and the
    # hook-mode precondition holds unless a test stubs git to break it.
    return subprocess.run(
        [shutil.which("bash") or "bash", str(GATE_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=120,
    )


def _run_gate_with_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tools: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run the gate with a PATH holding only `tools` (name -> script body) and
    `dirname`, which the gate needs to cd before its tool preconditions."""
    # Resolved before PATH is narrowed below.
    bash = shutil.which("bash")
    assert bash
    bin_dir = tmp_path / "only-bin"
    bin_dir.mkdir()
    dirname = shutil.which("dirname")
    assert dirname, "dirname is needed to run bin/check"
    (bin_dir / "dirname").symlink_to(dirname)
    for name, body in tools.items():
        _write(bin_dir / name, body).chmod(0o755)
    # An empty HOME: the gate prepends $HOME/.local/bin, where a real uv lives.
    monkeypatch.setenv("HOME", str(tmp_path / "empty-home"))
    monkeypatch.setenv("PATH", str(bin_dir))
    return subprocess.run(
        [bash, str(GATE_SCRIPT)], capture_output=True, text=True, timeout=120
    )


@needs_bash
def test_bin_check_exit_75_when_a_step_cannot_reach_the_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Index-unreachable output grades as the environment (75), never as red."""
    proc = _run_gate(
        tmp_path,
        monkeypatch,
        says="warning: failed to fetch https://pypi.org/simple/pip/",
        exits=1,
    )
    assert proc.returncode == 75, proc.stderr
    assert "could not reach the package index" in proc.stderr


@needs_bash
def test_bin_check_exit_1_on_a_plain_red_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure with no network phrase is a red change (1), not environment (75)."""
    proc = _run_gate(
        tmp_path, monkeypatch, says="ERROR: 2 failed, 42 passed in 0.31s", exits=1
    )
    assert proc.returncode == 1, proc.stderr
    assert "the change is red" in proc.stderr


@needs_bash
def test_bin_check_echoes_step_output_on_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On success each step's captured output is echoed, so a proof is reproducible."""
    proc = _run_gate(
        tmp_path, monkeypatch, says="knowledge base clean (stubbed)", exits=0
    )
    assert proc.returncode == 0, proc.stderr
    assert "knowledge base clean (stubbed)" in proc.stdout
    # Derived from the projects on disk, not today's step count: two repo-wide
    # steps, then one ruff and one pytest step per gated project.
    expected = ["rx knowledge base", "tools tests"] + [
        f"{project[:3]} {check}" for project in GATED_PROJECTS for check in ("ruff", "pytest")
    ]
    ran = [ln[len("==> ") :] for ln in proc.stderr.splitlines() if ln.startswith("==> ")]
    assert ran == expected, proc.stderr


@needs_bash
def test_bin_check_exit_75_when_uv_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No uv on PATH is the environment (75): the gate refuses to grade."""
    proc = _run_gate_with_only(tmp_path, monkeypatch, {"git": "#!/bin/sh\nexit 0\n"})
    assert proc.returncode == 75, proc.stderr
    assert "uv not found on PATH" in proc.stderr
    assert "==> " not in proc.stderr


@needs_bash
def test_bin_check_exit_75_when_git_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No git on PATH is the environment (75), not a red change."""
    proc = _run_gate_with_only(tmp_path, monkeypatch, {"uv": _STUB_UV})
    assert proc.returncode == 75, proc.stderr
    assert "git not found on PATH" in proc.stderr
    assert "==> " not in proc.stderr


@needs_bash
def test_bin_check_exit_1_when_the_hook_is_not_executable_in_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hook git records as 100644 is silently skipped: the gate grades it red (1)."""
    stub_git = (
        "#!/usr/bin/env bash\n"
        "printf '100644 0000000000000000000000000000000000000000 0\\t.githooks/pre-commit\\n'\n"
    )
    proc = _run_gate(tmp_path, monkeypatch, stubs={"git": stub_git})
    assert proc.returncode == 1, proc.stderr
    assert ".githooks/pre-commit is mode '100644'" in proc.stderr
    assert "==> " not in proc.stderr


# ── scaffolding: cmd_new_project renders a project that boots ─────────────────

REAL_TEMPLATES = _RX_PATH.parent.parent / "templates"
PLACEHOLDER = re.compile(r"\{\{[A-Za-z_][A-Za-z0-9_]*\}\}")

# A uv.lock that resolves exactly the rendered manifest (torch on the pinned pytorch
# index, typer, rich, and the dev extra). Written by hand: the tests must not run uv.
GENERATED_LOCK = """\
version = 1
requires-python = ">=3.11"

[[package]]
name = "{pkg}"
version = "0.1.0"
source = {{ editable = "." }}

[package.optional-dependencies]
dev = [
    {{ name = "pytest" }},
    {{ name = "ruff" }},
]

[package.metadata]
requires-dist = [
    {{ name = "rich", specifier = ">=13.7" }},
    {{ name = "torch", specifier = ">=2.5", index = "https://download.pytorch.org/whl/cu126" }},
    {{ name = "typer", specifier = ">=0.12" }},
    {{ name = "pytest", marker = "extra == 'dev'", specifier = ">=8.0" }},
    {{ name = "ruff", marker = "extra == 'dev'", specifier = ">=0.6" }},
]
"""


@pytest.fixture
def scaffold_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A synthetic repo root pointed at the REAL templates dir, with uv absent.

    Nothing may write into the real projects/ or .github/, and nothing may reach
    the network: 'which' reports no uv, so the scaffolder's best-effort lock step
    is skipped instead of run.
    """
    monkeypatch.setattr(rx, "ROOT", tmp_path)
    monkeypatch.setattr(rx, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(rx, "TEMPLATES", REAL_TEMPLATES)
    monkeypatch.setattr(rx.shutil, "which", lambda name: None)
    _write(
        tmp_path / ".github" / "dependabot.yml",
        DEPENDABOT.format(ecosystem="uv", directory="/projects/000-existing"),
    )
    return tmp_path


def _scaffold(tree: Path, name: str = "widget physics") -> Path:
    assert rx.main(["new-project", name]) == 0
    return tree / "projects" / "001-widget-physics"


def test_new_project_renders_a_parsable_manifest(scaffold_tree: Path) -> None:
    """Generated pyproject: valid TOML wiring the CLI, the index pin, the dev extra."""
    dest = _scaffold(scaffold_tree)
    manifest = tomllib.loads((dest / "pyproject.toml").read_text(encoding="utf-8"))
    assert manifest["project"]["name"] == "widget_physics"
    # rx status discovers the CLI through exactly this line.
    assert manifest["project"]["scripts"]["widget-physics"] == "widget_physics.cli:app"
    uv = manifest["tool"]["uv"]
    assert any(i["name"] == "pytorch" for i in uv["index"])
    assert uv["sources"]["torch"] == [{"index": "pytorch"}]
    dev = {rx._requirement_parts(r)[0]
           for r in manifest["project"]["optional-dependencies"]["dev"]}
    assert dev == {"pytest", "ruff"}
    ignores = manifest["tool"]["ruff"]["lint"]["per-file-ignores"]
    assert ignores["src/widget_physics/device.py"] == ["PTH"]
    assert ignores["src/widget_physics/cli.py"] == ["B008"]


def test_new_project_renders_the_advertised_tree(scaffold_tree: Path) -> None:
    """src modules, tests, and every directory the generated CLAUDE.md names exist."""
    dest = _scaffold(scaffold_tree)
    for sub in ("experiments", "notes", "results", "data", "explore"):
        assert (dest / sub).is_dir(), sub
    pkg = dest / "src" / "widget_physics"
    for module in ("__init__.py", "device.py", "cli.py", "provenance.py"):
        assert (pkg / module).is_file(), module
    assert (dest / "tests" / "test_scaffold.py").is_file()

    # Static checks only: importing the rendered package would need torch, which the
    # root test environment does not have — and must not need.
    device = ast.parse((pkg / "device.py").read_text(encoding="utf-8"))
    defined = {n.name for n in ast.walk(device)
               if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    assert {"DeviceInfo", "get_device_info", "pick_device", "autocast_dtype",
            "seed_everything"} <= defined
    cli = ast.parse((pkg / "cli.py").read_text(encoding="utf-8"))
    assert {"doctor", "smoke"} <= {n.name for n in ast.walk(cli)
                                   if isinstance(n, ast.FunctionDef)}
    prov = ast.parse((pkg / "provenance.py").read_text(encoding="utf-8"))
    assert "RunRecord" in {n.name for n in ast.walk(prov) if isinstance(n, ast.ClassDef)}
    # The rendered tests import the package by its rendered underscore name.
    assert "from widget_physics import provenance" in \
        (dest / "tests" / "test_scaffold.py").read_text(encoding="utf-8")


def test_no_rendered_file_keeps_a_placeholder(scaffold_tree: Path) -> None:
    dest = _scaffold(scaffold_tree)
    for f in dest.rglob("*"):
        if f.is_file():
            body = f.read_text(encoding="utf-8")
            assert not PLACEHOLDER.search(body), f"{f.name}: {PLACEHOLDER.search(body)!r}"


def test_new_project_appends_exactly_one_uv_dependabot_entry(
    scaffold_tree: Path,
) -> None:
    """One new entry for /projects/<new-dir>; every existing byte stays identical."""
    manifest = scaffold_tree / ".github" / "dependabot.yml"
    before = manifest.read_bytes()
    _scaffold(scaffold_tree)
    after = manifest.read_bytes()
    assert after.startswith(before)
    appended = after[len(before):].decode("utf-8")
    assert appended == rx._DEPENDABOT_UV_ENTRY.format(directory="001-widget-physics")
    entries = rx._dependabot_entries(after.decode("utf-8"))
    assert [(e["package-ecosystem"], e["directory"]) for e in entries] == [
        ("uv", "/projects/000-existing"),
        ("uv", "/projects/001-widget-physics"),
    ]


def test_dependabot_append_is_idempotent(scaffold_tree: Path) -> None:
    """Re-appending an existing entry is a no-op, not a duplicate."""
    rx._append_dependabot_entry("001-widget-physics")
    once = (scaffold_tree / ".github" / "dependabot.yml").read_bytes()
    note = rx._append_dependabot_entry("001-widget-physics")
    assert "already present" in note
    assert (scaffold_tree / ".github" / "dependabot.yml").read_bytes() == once


def test_uv_lock_failure_warns_with_the_remedy(
    scaffold_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """uv absent: the scaffolder says so, and the missing lock stays rx-check-visible."""
    dest = _scaffold(scaffold_tree)
    assert not (dest / "uv.lock").exists()
    out = capsys.readouterr().out
    assert "uv.lock NOT generated" in out
    assert "uv lock" in out and "commit uv.lock" in out
    assert _problems() == [
        "projects/001-widget-physics/uv.lock: missing - the uv ecosystem has nothing to "
        "discover"
    ]


def test_generated_project_is_clean_once_a_matching_lock_lands(
    scaffold_tree: Path,
) -> None:
    """With a lock that resolves the rendered manifest, check has nothing to say."""
    dest = _scaffold(scaffold_tree)
    _write(dest / "uv.lock", GENERATED_LOCK.format(pkg="widget_physics"))
    assert _problems() == []


def test_scaffold_self_validation_fails_on_template_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The guard: a template that stops satisfying the scaffold contract dies loudly."""
    broken = tmp_path / "templates"
    shutil.copytree(REAL_TEMPLATES, broken)
    pp = broken / "project" / "pyproject.toml"
    # Break the CLI wiring while keeping the TOML parseable, so the failure is
    # attributed by the scaffold contract, not by the TOML parser.
    pp.write_text(
        pp.read_text(encoding="utf-8").replace(
            '{{SLUG}} = "{{PKG}}.cli:app"', 'other-cli = "{{PKG}}.cli:app"'),
        encoding="utf-8",
    )
    monkeypatch.setattr(rx, "ROOT", tmp_path)
    monkeypatch.setattr(rx, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(rx, "TEMPLATES", broken)
    monkeypatch.setattr(rx.shutil, "which", lambda name: None)
    _write(
        tmp_path / ".github" / "dependabot.yml",
        DEPENDABOT.format(ecosystem="uv", directory="/projects/000-existing"),
    )
    with pytest.raises(SystemExit) as exc:
        rx.main(["new-project", "widget physics"])
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "[project.scripts]" in out
    assert "does not parse" not in out
    # A scaffold that failed validation must not touch the updater manifest.
    body = (tmp_path / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert "000-existing" in body
    assert "/projects/001-widget-physics" not in body


@pytest.fixture
def broken_template_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """scaffold_tree, but on a private *copy* of the real templates.

    A test that corrupts a template must corrupt a copy: the real templates/
    directory is shared and stays pristine.
    """
    broken = tmp_path / "templates"
    shutil.copytree(REAL_TEMPLATES, broken)
    monkeypatch.setattr(rx, "ROOT", tmp_path)
    monkeypatch.setattr(rx, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(rx, "TEMPLATES", broken)
    monkeypatch.setattr(rx.shutil, "which", lambda name: None)
    _write(
        tmp_path / ".github" / "dependabot.yml",
        DEPENDABOT.format(ecosystem="uv", directory="/projects/000-existing"),
    )
    return broken


def test_unreplaced_placeholder_fails_validation(
    broken_template_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The 'no {{...}} survives render' contract has a failing test.

    Renaming a template's {{SLUG}} to a field render() never supplies leaves it
    verbatim in the output; the validator branch must die on it at creation
    instead of shipping the placeholder inside src/<pkg>/__init__.py.
    """
    init = broken_template_tree / "project" / "__init__.py"
    init.write_text(
        init.read_text(encoding="utf-8").replace("{{SLUG}}", "{{SLUGX}}"),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc:
        rx.main(["new-project", "widget physics"])
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "src/widget_physics/__init__.py: unreplaced placeholder {{SLUGX}}" in out


def test_failed_validation_removes_the_scaffold(
    broken_template_tree: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The zombie-dir bug: a scaffold that fails validation leaves nothing behind.

    A leftover projects/NNN-slug/ blocks the retry with 'already exists' or
    silently burns the next number (numbers are never reused), and rx check
    would flag its missing uv.lock and dependabot entry forever.
    """
    pp = broken_template_tree / "project" / "pyproject.toml"
    pp.write_text(
        pp.read_text(encoding="utf-8").replace(
            '{{SLUG}} = "{{PKG}}.cli:app"', 'other-cli = "{{PKG}}.cli:app"'
        ),
        encoding="utf-8",
    )
    dest = rx.PROJECTS / "001-widget-physics"
    with pytest.raises(SystemExit) as exc:
        rx.main(["new-project", "widget physics"])
    assert exc.value.code == 1
    assert not dest.exists()
    assert "removed projects/001-widget-physics" in capsys.readouterr().out
    # Once the template is fixed, the retry reuses the number instead of dying
    # on 'already exists' or quietly becoming 002.
    monkeypatch.setattr(rx, "TEMPLATES", REAL_TEMPLATES)
    assert rx.main(["new-project", "widget physics"]) == 0
    assert (dest / "pyproject.toml").is_file()
    entries = rx._dependabot_entries(
        (rx.ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    assert [e["directory"] for e in entries].count("/projects/001-widget-physics") == 1


def test_uv_lock_nonzero_exit_warns_with_reason(
    scaffold_tree: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The failed-lock branch: a uv that runs but exits non-zero is reported.

    The last stderr line is the reason, the missing lock stays rx-check-visible,
    and no uv.lock is left half-written on disk.
    """

    class _Failed:
        returncode = 2
        stdout = ""
        stderr = "error: resolution failed\nhint: pytorch index unreachable"

    monkeypatch.setattr(rx.shutil, "which", lambda name: "/usr/local/bin/uv")
    monkeypatch.setattr(rx.subprocess, "run", lambda *a, **k: _Failed())
    dest = _scaffold(scaffold_tree)
    assert not (dest / "uv.lock").exists()
    out = capsys.readouterr().out
    assert "uv lock failed (hint: pytorch index unreachable)" in out
    assert "uv.lock NOT generated" in out
    assert "commit uv.lock" in out


@pytest.mark.parametrize("command", ["doctor", "smoke"])
@pytest.mark.parametrize("decorator", ["", '@app.command("renamed")\n', '@other.command()\n'])
def test_missing_command_registration_fails_validation(
    broken_template_tree: Path, capsys: pytest.CaptureFixture[str],
    command: str, decorator: str,
) -> None:
    cli = broken_template_tree / "project" / "cli.py"
    _write(cli, cli.read_text(encoding="utf-8").replace(
        f"@app.command()\ndef {command}", f"{decorator}def {command}"))
    with pytest.raises(SystemExit) as exc:
        rx.main(["new-project", "widget physics"])
    assert exc.value.code == 1
    assert f"{command} is not registered on app" in capsys.readouterr().out
    assert not (rx.PROJECTS / "001-widget-physics").exists()


def test_scaffold_run_record_concurrent_writers(
    scaffold_tree: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    dest = _scaffold(scaffold_tree)
    spec = importlib.util.spec_from_file_location(
        "scaffold_provenance", dest / "src" / "widget_physics" / "provenance.py")
    assert spec and spec.loader
    provenance = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, provenance)
    spec.loader.exec_module(provenance)
    barrier = Barrier(2)
    monkeypatch.setattr(provenance, "git_sha", lambda: "test-sha")

    def hardware():
        barrier.wait(timeout=10)
        return {"accelerator": "test"}

    monkeypatch.setattr(provenance, "hardware", hardware)
    path = dest / "results" / "E000-race.json"

    def write(seed):
        try:
            provenance.RunRecord("E000", seed, {"seed": seed}, items=[{"seed": seed}]).write(path)
        except FileExistsError:
            return None
        return seed

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, [1, 2]))
    winners = [seed for seed in results if seed is not None]
    assert len(winners) == 1
    record = provenance.load(path)
    assert record["seed"] == winners[0]
    assert record["items"] == [{"seed": winners[0]}]


# ── the test harness: `rx test`, and the suites inside `rx check` ───────────────

DEMO_TEST = "def test_demo():\n    assert True\n"


class _Proc:
    """The shape of a finished child process."""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeRunner:
    """Stands in for ``subprocess.run``: records the commands, answers with verdicts.

    No test here may spawn a real pytest or reach the network, so every child
    process the harness starts is answered by this fake.
    """

    def __init__(
        self,
        *,
        returncode: int = 0,
        stdout: str = "1 passed in 0.01s",
        stderr: str = "",
        raises: bool = False,
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.raises = raises
        self.commands: list[list[str]] = []
        self.cwds: list[str | None] = []
        self.envs: list[dict[str, str]] = []

    def __call__(self, command, **kwargs):
        self.commands.append(list(command))
        self.cwds.append(kwargs.get("cwd"))
        self.envs.append(kwargs.get("env") or {})
        if "--help" in command:
            # the uv capability probe, not a test run
            return _Proc(0, stdout="      --isolated\n")
        if self.raises:
            raise OSError("no such file or directory")
        return _Proc(self.returncode, self.stdout, self.stderr)

    def pytest_commands(self) -> list[list[str]]:
        """The commands meant to run pytest, not the uv capability probe."""
        return [c for c in self.commands if "pytest" in c]


class _MissingPytestRunner(FakeRunner):
    """The project's venv has no pytest: the probe says so, everything else is green."""

    def __call__(self, command, **kwargs):
        if command[1:2] == ["-c"]:
            self.commands.append(list(command))
            self.cwds.append(kwargs.get("cwd"))
            self.envs.append(kwargs.get("env") or {})
            return _Proc(1, stderr="No module named pytest")
        return super().__call__(command, **kwargs)


class _TimeoutRunner(FakeRunner):
    """Every child process but the uv capability probe times out."""

    def __call__(self, command, **kwargs):
        if "--help" in command:
            return super().__call__(command, **kwargs)
        self.commands.append(list(command))
        self.cwds.append(kwargs.get("cwd"))
        self.envs.append(kwargs.get("env") or {})
        raise subprocess.TimeoutExpired(cmd=list(command), timeout=1800)


class _NoPytest:
    """Stands in for ``importlib.util`` in rx's namespace: pytest is not here."""

    class util:  # noqa: N801 - the stdlib name rx.py reaches for
        @staticmethod
        def find_spec(name: str):
            return None


@pytest.fixture
def harness_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A synthetic repo root: a root suite, one synced project, one unsynced.

    The root suite runs, the synced project's suite runs, and the project with
    no .venv is reported SKIPPED. Nothing here touches the real projects/.
    """
    monkeypatch.setattr(rx, "ROOT", tmp_path)
    monkeypatch.setattr(rx, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(rx, "LIBRARY", tmp_path / "library")
    monkeypatch.setattr(rx, "ARTICLES", tmp_path / "articles")
    monkeypatch.setattr(rx, "_UV_ISOLATED", None)
    _write(tmp_path / "tools" / "test_demo.py", DEMO_TEST)
    _write(tmp_path / "projects" / "002-synced" / "tests" / "test_demo.py", DEMO_TEST)
    _write(tmp_path / "projects" / "002-synced" / ".venv" / "bin" / "python", "")
    _write(tmp_path / "projects" / "001-unsynced" / "tests" / "test_demo.py", DEMO_TEST)
    return tmp_path


def _fake_uv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend uv is on PATH: the harness then drives pytest through it."""
    monkeypatch.setattr(rx.shutil, "which", lambda name: "/usr/local/bin/uv")


def test_rx_test_runs_the_root_suite_and_exits_zero(
    harness_tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """The happy path: the root suite runs, its verdict is printed, the exit code is 0."""
    runner = FakeRunner()
    _fake_uv(monkeypatch)
    monkeypatch.setattr(rx.subprocess, "run", runner)
    assert rx.main(["test"]) == 0
    out = capsys.readouterr().out
    assert "PASS" in out
    assert "root" in out
    assert "tools/test_demo.py" in out
    assert "1 passed in 0.01s" in out
    assert runner.pytest_commands(), runner.commands


def test_rx_test_fails_and_names_the_suite_when_a_suite_fails(
    harness_tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A red suite is a red run, and the summary says which suite was red."""
    runner = FakeRunner(returncode=1, stdout="1 failed in 0.01s")
    _fake_uv(monkeypatch)
    monkeypatch.setattr(rx.subprocess, "run", runner)
    assert rx.main(["test"]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "root" in out
    assert "pytest exit 1" in out
    assert "1 failed in 0.01s" in out


def test_a_project_without_a_synced_venv_is_reported_skipped(
    harness_tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """No .venv means the project's tests never ran: SKIPPED with a remedy, not a pass."""
    runner = FakeRunner()
    _fake_uv(monkeypatch)
    monkeypatch.setattr(rx.subprocess, "run", runner)
    assert rx.main(["test"]) == 0
    out = capsys.readouterr().out
    assert "SKIP" in out
    assert "001-unsynced" in out
    assert "uv sync --extra dev" in out
    # the unsynced project was never started
    assert not any(cwd and cwd.endswith("001-unsynced") for cwd in runner.cwds)


def test_a_project_venv_without_an_interpreter_is_reported_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A .venv with no interpreter never ran anything: SKIPPED with the remedy."""
    monkeypatch.setattr(rx, "ROOT", tmp_path)
    monkeypatch.setattr(rx, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(rx.shutil, "which", lambda name: None)
    _write(tmp_path / "tools" / "test_demo.py", DEMO_TEST)
    _write(tmp_path / "projects" / "003-nointerp" / "tests" / "test_demo.py", DEMO_TEST)
    (tmp_path / "projects" / "003-nointerp" / ".venv").mkdir(parents=True)
    runner = FakeRunner()
    monkeypatch.setattr(rx.subprocess, "run", runner)
    assert rx.main(["test"]) == 0
    out = capsys.readouterr().out
    assert "SKIP" in out
    assert "003-nointerp" in out
    assert "uv sync --extra dev" in out


def test_a_synced_project_runs_its_own_suite_with_its_own_interpreter(
    harness_tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A project with a synced .venv runs its suite on that venv's interpreter."""
    runner = FakeRunner()
    _fake_uv(monkeypatch)
    monkeypatch.setattr(rx.subprocess, "run", runner)
    assert rx.main(["test"]) == 0
    out = capsys.readouterr().out
    assert "002-synced" in out
    project_calls = [
        command for command, cwd in zip(runner.commands, runner.cwds)
        if cwd and cwd.endswith("002-synced")
    ]
    assert project_calls, runner.commands
    assert project_calls[0][0].endswith("python")
    assert project_calls[0][1:3] == ["-m", "pytest"]


def test_a_project_venv_without_pytest_fails_with_the_remedy(
    harness_tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A venv synced without the dev extra is an environment gap, named as one.

    The suite run on such a venv exits 1 on "No module named pytest", which the
    report would call a failed test — no cause, no remedy. It is a missing
    dependency in the project's environment: FAIL, with the remedy.
    """
    runner = _MissingPytestRunner()
    _fake_uv(monkeypatch)
    monkeypatch.setattr(rx.subprocess, "run", runner)
    assert rx.main(["test"]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "002-synced" in out
    assert "pytest is not installed" in out
    assert "uv sync --extra dev" in out
    # the raw interpreter error is not what the report leads with
    assert "No module named pytest" not in out
    # and the project's suite was never started
    assert not any(cwd and cwd.endswith("002-synced") for cwd in runner.cwds)


def test_pytest_exit_5_is_a_failure_not_a_pass(
    harness_tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """pytest exits 5 when it collected nothing: that is a failure, never a pass."""
    runner = FakeRunner(returncode=5, stdout="no tests ran in 0.01s")
    _fake_uv(monkeypatch)
    monkeypatch.setattr(rx.subprocess, "run", runner)
    assert rx.main(["test"]) == 1
    out = capsys.readouterr().out
    assert "no tests collected" in out
    assert "PASS" not in out


def test_a_suite_that_cannot_start_is_a_failure(
    harness_tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A suite that could not be started is a loud failure, never a silent pass."""
    runner = FakeRunner(raises=True)
    _fake_uv(monkeypatch)
    monkeypatch.setattr(rx.subprocess, "run", runner)
    assert rx.main(["test"]) == 1
    out = capsys.readouterr().out
    assert "could not start" in out


def test_a_suite_that_times_out_is_a_failure(
    harness_tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A suite that never finishes is a failure, not a pass."""
    runner = _TimeoutRunner()
    _fake_uv(monkeypatch)
    monkeypatch.setattr(rx.subprocess, "run", runner)
    assert rx.main(["test"]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "timed out" in out


def test_rx_test_fails_when_the_root_suite_has_no_test_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """No test file means nothing was tested: the run fails rather than passes."""
    monkeypatch.setattr(rx, "ROOT", tmp_path)
    monkeypatch.setattr(rx, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(rx.shutil, "which", lambda name: None)
    assert rx.main(["test"]) == 1
    out = capsys.readouterr().out
    assert "no test files found" in out


def test_the_root_suite_runs_through_uv_without_touching_the_outer_venv(
    harness_tree: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The inner run may not sync or modify the environment rx.py itself runs in."""
    runner = FakeRunner()
    _fake_uv(monkeypatch)
    monkeypatch.setattr(rx.subprocess, "run", runner)
    monkeypatch.setenv("VIRTUAL_ENV", "/tmp/outer-ephemeral-env")
    assert rx.main(["test"]) == 0
    commands = runner.pytest_commands()
    assert commands, runner.commands
    command = commands[0]
    assert command[:2] == ["uv", "run"]
    assert "--with" in command and "pytest" in command
    assert "tools/test_demo.py" in command
    # the child inherits no virtualenv, so it cannot touch the outer one
    assert all("VIRTUAL_ENV" not in env for env in runner.envs)


def test_the_root_suite_falls_back_to_this_interpreter_without_uv(
    harness_tree: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without uv on PATH the suite runs on this interpreter — pytest is not imported."""
    runner = FakeRunner()
    monkeypatch.setattr(rx.shutil, "which", lambda name: None)
    monkeypatch.setattr(rx.subprocess, "run", runner)
    assert rx.main(["test"]) == 0
    commands = runner.pytest_commands()
    assert commands, runner.commands
    assert commands[0][:3] == [sys.executable, "-m", "pytest"]


def test_the_root_suite_without_pytest_in_this_interpreter_fails_with_the_remedy(
    harness_tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """No uv and no pytest here: the run fails and says how to fix it."""
    monkeypatch.setattr(rx.shutil, "which", lambda name: None)
    monkeypatch.setattr(rx, "importlib", _NoPytest)
    runner = FakeRunner()
    monkeypatch.setattr(rx.subprocess, "run", runner)
    assert rx.main(["test"]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "pytest is not installed in this interpreter" in out
    assert "uv run --with pytest pytest" in out
    # the gap was found before the run, so the root suite was never started
    assert str(harness_tree) not in runner.cwds


def test_rx_check_runs_the_suites_and_fails_on_a_red_suite(
    harness_tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """`rx check` runs the suites after the lint: a red suite is a red check."""
    monkeypatch.setattr(rx, "_knowledge_base_problems", lambda: [])
    runner = FakeRunner(returncode=1, stdout="1 failed in 0.01s")
    _fake_uv(monkeypatch)
    monkeypatch.setattr(rx.subprocess, "run", runner)
    assert rx.main(["check"]) == 1
    out = capsys.readouterr().out
    assert "knowledge base clean" in out
    assert "FAIL" in out
    assert "root" in out
    assert runner.pytest_commands(), runner.commands


def test_rx_check_is_green_when_the_lint_and_the_suites_pass(
    harness_tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """The whole check — lint and suites — is one exit code."""
    monkeypatch.setattr(rx, "_knowledge_base_problems", lambda: [])
    runner = FakeRunner()
    _fake_uv(monkeypatch)
    monkeypatch.setattr(rx.subprocess, "run", runner)
    assert rx.main(["check"]) == 0
    out = capsys.readouterr().out
    assert "knowledge base clean" in out
    assert "PASS" in out


def test_rx_check_still_fails_on_a_knowledge_base_problem(
    harness_tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """The lint still has teeth: a knowledge-base problem fails the check."""
    monkeypatch.setattr(
        rx, "_knowledge_base_problems", lambda: ["library/x.md: dangling link [[y]]"])
    runner = FakeRunner()
    _fake_uv(monkeypatch)
    monkeypatch.setattr(rx.subprocess, "run", runner)
    assert rx.main(["check"]) == 1
    out = capsys.readouterr().out
    assert "dangling link" in out


def test_rx_check_no_tests_skips_the_suites(
    harness_tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """`rx check --no-tests` is the fast lint: no suite is started."""
    monkeypatch.setattr(rx, "_knowledge_base_problems", lambda: [])
    runner = FakeRunner()
    _fake_uv(monkeypatch)
    monkeypatch.setattr(rx.subprocess, "run", runner)
    assert rx.main(["check", "--no-tests"]) == 0
    out = capsys.readouterr().out
    assert "--no-tests" in out
    assert runner.commands == []


def test_rx_never_imports_pytest() -> None:
    """rx.py stays stdlib-only: pytest is spawned in a child, never imported."""
    source = _RX_PATH.read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import pytest|from pytest)", source, re.M)


def test_help_lists_the_test_command(capsys: pytest.CaptureFixture[str]) -> None:
    """`rx help` is the catalog: the new command has to be in it."""
    assert "test" in rx.COMMANDS
    assert rx.main(["help"]) == 0
    out = capsys.readouterr().out
    assert any(line.strip().startswith("test ") for line in out.splitlines())


# ── bin/check: the canonical check is its first step ──────────────────────────

# Where main's bin/check was a shim that only ever forwarded to the canonical
# `uv run tools/rx.py check`, the merged bin/check is the gate whose FIRST step
# is that same canonical command, followed by the pinned tools suite and every
# project's ruff + pytest — one canonical command, one implementation of "is
# this tree green?". The shim's forwarding survives as the gate's first step;
# what does not survive is its no-uv fallback: without uv the gate refuses to
# grade (exit 75, the documented contract in
# .claude/skills/verify-change/SKILL.md) instead of silently grading on
# whatever interpreter it happens to run under. The child's exit code still
# decides the verdict — a red step is exit 1 — and a gate that cannot even
# start is never a silent zero: missing uv or git is exit 75. All three are
# pinned by the exit-code tests above; this section pins the surviving step.

_RECORDING_UV = """\
#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$STUB_UV_LOG"
exit "${STUB_UV_EXIT:-0}"
"""


@needs_bash
def test_bin_check_starts_from_the_canonical_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The gate's first uv command is the canonical check, spelled in full.

    Whatever else the gate grows, it must start at ``uv run tools/rx.py
    check`` — a gate that stops running the canonical command first has forked
    "is this tree green?" into two implementations again, the exact defect
    main's shim existed to prevent. The stub records the argv of every ``uv``
    the gate starts, so the first recorded line is the gate's opening move.
    """
    stub_dir = tmp_path / "home" / ".local" / "bin"
    _write(stub_dir / "uv", _RECORDING_UV).chmod(0o755)
    log = stub_dir.parent.parent / "uv-argv.log"
    monkeypatch.setenv("HOME", str(stub_dir.parent.parent))
    monkeypatch.setenv("PATH", f"{stub_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("STUB_UV_LOG", str(log))
    proc = subprocess.run(
        [shutil.which("bash") or "bash", str(GATE_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert log.read_text(encoding="utf-8").splitlines()[0] == "run tools/rx.py check"
