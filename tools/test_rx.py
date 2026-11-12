"""Tests for the dependency-update validation in ``tools/rx.py``.

The check that a uv-managed project stays discoverable — and stays *correctly*
described — by the updater is the only machine guard on the Dependabot
configuration, and until now no test pinned it: deleting ``_check_dependency_updates``
and ``_lock_divergences`` outright would leave the suite green. These tests drive the
validation against a synthetic tree so each failure mode is asserted separately.

The harness tests pin ``rx test`` and the suites inside ``rx check``. The runner is
faked, so no test spawns a real pytest and none of them reach the network. The
``bin/check`` shim is loaded by path, and the process it starts is faked too.

The scaffold tests drive ``cmd_new_project`` against the real
``templates/`` directory, so template drift fails here instead of at the next
project's creation.

Run from the repo root:

    uv run --with pytest pytest tools/test_rx.py -q
"""

from __future__ import annotations

import ast
import importlib.machinery
import importlib.util
import re
import shutil
import subprocess
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import ModuleType

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


# ── bin/check: the shim over the canonical command ─────────────────────────────

_CHECK_PATH = _RX_PATH.parent.parent / "bin" / "check"


def _load_check() -> ModuleType:
    """Load bin/check as a module — the file has no .py suffix, so the loader is explicit."""
    loader = importlib.machinery.SourceFileLoader("bin_check_under_test", str(_CHECK_PATH))
    spec = importlib.util.spec_from_file_location(
        "bin_check_under_test", _CHECK_PATH, loader=loader)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bin_check_forwards_to_the_canonical_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """bin/check is a shim: it forwards to `uv run tools/rx.py check` and adds nothing."""
    check = _load_check()
    calls: list[list[str]] = []

    def fake_call(command, **kwargs):
        calls.append(list(command))
        return 0

    monkeypatch.setattr(check.shutil, "which", lambda name: "/usr/local/bin/uv")
    monkeypatch.setattr(check.subprocess, "call", fake_call)
    assert check.main(["--no-tests"]) == 0
    assert calls == [["uv", "run", str(_CHECK_PATH.parent.parent / "tools" / "rx.py"),
                      "check", "--no-tests"]]


def test_bin_check_returns_the_child_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shim hands back the child's exit code: a red check is a red bin/check."""
    check = _load_check()
    monkeypatch.setattr(check.shutil, "which", lambda name: "/usr/local/bin/uv")
    monkeypatch.setattr(check.subprocess, "call", lambda command, **kwargs: 3)
    assert check.main([]) == 3


def test_bin_check_falls_back_to_this_interpreter_without_uv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without uv on PATH the shim still runs the same check, on this interpreter."""
    check = _load_check()
    calls: list[list[str]] = []

    def fake_call(command, **kwargs):
        calls.append(list(command))
        return 0

    monkeypatch.setattr(check.shutil, "which", lambda name: None)
    monkeypatch.setattr(check.subprocess, "call", fake_call)
    assert check.main([]) == 0
    assert calls == [[sys.executable, str(_CHECK_PATH.parent.parent / "tools" / "rx.py"),
                      "check"]]


def test_bin_check_returns_one_when_the_check_cannot_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A check that cannot start is a failure, never a silent zero."""
    check = _load_check()

    def boom(command, **kwargs):
        raise OSError("no such file or directory")

    monkeypatch.setattr(check.shutil, "which", lambda name: "/usr/local/bin/uv")
    monkeypatch.setattr(check.subprocess, "call", boom)
    assert check.main([]) == 1
