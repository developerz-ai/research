"""Tests for the dependency-update validation in ``tools/rx.py``.

The check that a uv-managed project stays discoverable — and stays *correctly*
described — by the updater is the only machine guard on the Dependabot
configuration, and until now no test pinned it: deleting ``_check_dependency_updates``
and ``_lock_divergences`` outright would leave the suite green. These tests drive the
validation against a synthetic tree so each failure mode is asserted separately.

Run from the repo root:

    uv run --with pytest pytest tools/test_rx.py -q
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

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
