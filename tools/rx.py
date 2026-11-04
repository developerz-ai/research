#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""rx — the research repo's command catalog.

Zero dependencies, stdlib only, so it runs from a bare checkout with no venv:

    uv run tools/rx.py help

Everything an agent needs to discover about this repo is reachable from `help`.
Add a command by writing a function named ``cmd_<name>`` with a docstring; it is
registered and documented automatically.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
LIBRARY = ROOT / "library"
PROJECTS = ROOT / "projects"

# ─────────────────────────────────────────────────────────────── output helpers

_NO_COLOR = os.environ.get("NO_COLOR") or not sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return text if _NO_COLOR else f"\033[{code}m{text}\033[0m"


def bold(t: str) -> str:
    return _c("1", t)


def dim(t: str) -> str:
    return _c("2", t)


def green(t: str) -> str:
    return _c("32", t)


def yellow(t: str) -> str:
    return _c("33", t)


def red(t: str) -> str:
    return _c("31", t)


def die(msg: str) -> "NoReturn":  # type: ignore[valid-type]
    print(red(f"error: {msg}"), file=sys.stderr)
    raise SystemExit(1)


def today() -> str:
    return dt.date.today().isoformat()


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not s:
        die(f"cannot slugify {text!r}")
    return s


def git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def render(template: Path, dest: Path, **fields: str) -> None:
    """Copy a template, substituting {{KEY}} placeholders. Never overwrites."""
    if dest.exists():
        die(f"{dest.relative_to(ROOT)} already exists")
    if not template.exists():
        die(f"missing template {template.relative_to(ROOT)}")
    body = template.read_text(encoding="utf-8")
    for key, value in fields.items():
        body = body.replace("{{" + key.upper() + "}}", value)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body, encoding="utf-8", newline="\n")
    print(green("created ") + str(dest.relative_to(ROOT)).replace("\\", "/"))


# ───────────────────────────────────────────────────────────────────── commands


def cmd_help(args: argparse.Namespace) -> int:
    """Show every command in this repo."""
    print()
    print(bold("  rx — developerz.ai research"))
    print(dim("  uv run tools/rx.py <command>"))
    print()
    width = max(len(n) for n in COMMANDS)
    for name, fn in COMMANDS.items():
        summary = (fn.__doc__ or "").strip().splitlines()[0]
        print(f"  {bold(name.ljust(width))}  {summary}")
    print()
    print(bold("  pipeline"))
    print(dim("    acquire ──► source ──► idea ──► synthesis ──► claim ──► experiment ──► verdict"))
    print(dim("                              └──────────► lead ◄──────────┘"))
    print()
    print(bold("  coordinating a project"))
    for line in (
        "uv run tools/rx.py status NNN   where it is at, and whether it is ready",
        "uv run tools/rx.py leads        what is worth more research, ranked",
        "uv run tools/rx.py check        knowledge base lint",
    ):
        print(f"    {line}")
    print()
    print(bold("  inside a project"))
    for line in (
        "uv sync                    install deps into ./.venv",
        "uv run geom doctor         verify backend before any run",
        "uv run geom --help         project CLI",
        "uv run pytest -q           tests",
        "uv run ruff check --fix .  lint",
    ):
        print(f"    {line}")
    print()
    print(dim("  docs: docs/method.md · docs/toolchain.md · docs/starting-a-project.md"))
    print()
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Report hardware, accelerator backend, and toolchain health."""
    print()
    print(bold("  host"))
    print(f"    platform   {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"    python     {platform.python_version()}  {dim(sys.executable)}")
    print(f"    cpu        {platform.processor() or 'unknown'}")
    try:
        print(f"    cores      {os.cpu_count()} logical")
    except Exception:
        pass
    free = shutil.disk_usage(ROOT).free / 1e9
    print(f"    disk free  {free:.0f} GB")

    print()
    print(bold("  toolchain"))
    for tool, probe in (("uv", "--version"), ("git", "--version"), ("gh", "--version")):
        path = shutil.which(tool)
        if path:
            ver = subprocess.run(
                [tool, probe], capture_output=True, text=True
            ).stdout.strip().splitlines()
            print(f"    {tool:<10} {green('ok')}  {dim(ver[0] if ver else path)}")
        else:
            print(f"    {tool:<10} {yellow('missing')}")

    print()
    print(bold("  accelerator"))
    nvsmi = shutil.which("nvidia-smi")
    rocmsmi = shutil.which("rocm-smi")
    found = False
    if nvsmi:
        out = subprocess.run(
            [nvsmi, "--query-gpu=name,memory.total,driver_version",
             "--format=csv,noheader"],
            capture_output=True, text=True,
        ).stdout.strip()
        for line in filter(None, out.splitlines()):
            print(f"    {green('nvidia')}  {line}")
            found = True
    if rocmsmi:
        print(f"    {green('amd')}     rocm-smi present")
        found = True
    if not found:
        print(f"    {yellow('none detected')} — CPU fallback. Every experiment must still run here.")
    print(dim("    torch-level check is per project: cd projects/<p> && uv run geom doctor"))

    print()
    print(bold("  repo"))
    sha = git("rev-parse", "--short", "HEAD")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    dirty = git("status", "--porcelain")
    print(f"    commit     {sha or dim('none yet')} on {branch or dim('-')}")
    print(f"    worktree   {yellow('dirty') if dirty else green('clean')}")
    print(f"    projects   {len(_projects())}")
    print()
    return 0


def _projects() -> list[Path]:
    if not PROJECTS.exists():
        return []
    return sorted(p for p in PROJECTS.iterdir() if p.is_dir() and not p.name.startswith("."))


def cmd_projects(args: argparse.Namespace) -> int:
    """List projects with their question and status."""
    projects = _projects()
    if not projects:
        print(dim("  no projects yet — uv run tools/rx.py new-project \"my idea\""))
        return 0
    print()
    for p in projects:
        readme = p / "README.md"
        question, status = "", "?"
        if readme.exists():
            text = readme.read_text(encoding="utf-8", errors="replace")
            if m := re.search(r"^\*\*Question:\*\*\s*(.+)$", text, re.M):
                question = m.group(1).strip()
            if m := re.search(r"^\*\*Status:\*\*\s*(.+)$", text, re.M):
                status = m.group(1).strip()
        n_exp = len(list((p / "experiments").glob("*.md"))) if (p / "experiments").exists() else 0
        n_res = len(list((p / "results").glob("*.json"))) if (p / "results").exists() else 0
        print(f"  {bold(p.name)}  {dim(status)}")
        if question:
            print(f"    {question}")
        print(dim(f"    {n_exp} experiment doc(s) · {n_res} result file(s)"))
        print()
    return 0


_DEPENDABOT_UV_ENTRY = """\
  - package-ecosystem: "uv"
    directory: "/projects/{directory}"
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


def _append_dependabot_entry(project_dir: str) -> str:
    """Append one 'uv' updates entry for /projects/<project_dir> to .github/dependabot.yml.

    Byte-append only: existing entries are never rewritten, and a manifest that already
    names this directory is left untouched. The entry is the exact shape
    .github/dependabot.yml and _check_dependency_updates expect — a uv-managed project
    without one is invisible to the weekly updater.
    """
    manifest = ROOT / ".github" / "dependabot.yml"
    directory = f"/projects/{project_dir}"
    if manifest.exists():
        entries = _dependabot_entries(
            manifest.read_text(encoding="utf-8", errors="replace"))
        if any(str(e.get("directory")) == directory for e in entries):
            return f"dependabot: entry for {directory} already present — nothing appended"
    body = manifest.read_bytes() if manifest.exists() else b"version: 2\nupdates:\n"
    if not body.endswith(b"\n"):
        body += b"\n"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_bytes(
        body + _DEPENDABOT_UV_ENTRY.format(directory=project_dir).encode("utf-8"))
    return f"dependabot: appended 'uv' entry for {directory}"


def _try_uv_lock(dest: Path) -> str:
    """Attempt 'uv lock' in the freshly scaffolded project. Best-effort, never fatal.

    Offline or uv-less environments skip it — deliberately not silently: the missing
    uv.lock stays visible to 'rx check' until someone generates and commits it. That
    visibility is the point; a silent pass here is the failure mode.
    """
    if shutil.which("uv") is None:
        return "lock:    uv not on PATH — uv.lock NOT generated"
    try:
        proc = subprocess.run(
            ["uv", "lock"], cwd=dest, capture_output=True, text=True, timeout=300
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"lock:    uv lock failed ({exc}) — uv.lock NOT generated"
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        reason = detail[-1] if detail else f"exit {proc.returncode}"
        return f"lock:    uv lock failed ({reason}) — uv.lock NOT generated"
    return "lock:    uv.lock generated"


def _validate_scaffold(dest: Path, *, slug: str, pkg: str) -> list[str]:
    """Self-check the rendered project against what its own CLAUDE.md advertises.

    Every startup command the generated docs promise — uv sync, uv run <slug>
    doctor/smoke/--help, pytest, ruff — must resolve to something that exists in the
    rendered tree, and no rendered file may retain an unreplaced {{...}} placeholder.
    This is the guard that keeps templates/project/ and cmd_new_project from drifting
    apart silently: a template edit that breaks the scaffold dies here, at creation.
    """
    problems: list[str] = []

    for f in sorted(dest.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(dest).as_posix()
        for leftover in re.findall(r"\{\{[A-Za-z_][A-Za-z0-9_]*\}\}",
                                   f.read_text(encoding="utf-8", errors="replace")):
            problems.append(f"{rel}: unreplaced placeholder {leftover}")

    for sub in ("experiments", "notes", "results", "data", "explore", "tests"):
        if not (dest / sub).is_dir():
            problems.append(f"{sub}/ missing — the generated CLAUDE.md layout names it")

    try:
        manifest = tomllib.loads((dest / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return problems + [f"pyproject.toml does not parse ({exc})"]

    project = manifest.get("project", {})
    if project.get("name") != pkg:
        problems.append(
            f"pyproject.toml: project.name is {project.get('name')!r}, expected {pkg!r}")
    if project.get("scripts", {}).get(slug) != f"{pkg}.cli:app":
        problems.append(
            f"pyproject.toml: [project.scripts] must wire {slug!r} = '{pkg}.cli:app' — "
            "`rx status` discovers the CLI through exactly that line")
    tool = manifest.get("tool", {})
    indexes = [i for i in tool.get("uv", {}).get("index", []) if isinstance(i, dict)]
    if not any(i.get("name") == "pytorch" for i in indexes):
        problems.append(
            "pyproject.toml: no [[tool.uv.index]] 'pytorch' pin — the default PyPI torch "
            "wheel is CPU-only and fails silently")
    dev = {_requirement_parts(str(r))[0] for r in
           project.get("optional-dependencies", {}).get("dev", [])}
    for needed, command in (("pytest", "uv run pytest -q"), ("ruff", "uv run ruff check")):
        if needed not in dev:
            problems.append(
                f"pyproject.toml: dev extra missing {needed!r} — CLAUDE.md advertises "
                f"`{command}`")
    if "ruff" not in tool:
        problems.append("pyproject.toml: no [tool.ruff] — CLAUDE.md advertises `uv run ruff`")

    modules = {
        "__init__.py": ("__version__",),
        "device.py": ("DeviceInfo", "get_device_info", "pick_device", "autocast_dtype",
                      "seed_everything"),
        "cli.py": ("app", "doctor", "smoke"),
        "provenance.py": ("RunRecord", "git_sha", "hardware"),
    }
    for module, symbols in modules.items():
        path = dest / "src" / pkg / module
        if not path.exists():
            problems.append(f"src/{pkg}/{module} missing — CLAUDE.md names it")
            continue
        body = path.read_text(encoding="utf-8", errors="replace")
        for sym in symbols:
            if not re.search(rf"^(?:def |class )?{re.escape(sym)}\b", body, re.M):
                problems.append(
                    f"src/{pkg}/{module}: {sym} is not defined — a documented command or "
                    "contract resolves to it")
        if module == "cli.py":
            try:
                tree = ast.parse(body)
            except SyntaxError as exc:
                problems.append(f"src/{pkg}/{module}: invalid Python ({exc})")
                continue
            registered = set()
            for node in tree.body:
                if not isinstance(node, ast.FunctionDef):
                    continue
                for decorator in node.decorator_list:
                    if not (
                        isinstance(decorator, ast.Call)
                        and isinstance(decorator.func, ast.Attribute)
                        and isinstance(decorator.func.value, ast.Name)
                        and decorator.func.value.id == "app"
                        and decorator.func.attr == "command"
                    ):
                        continue
                    name = next((k.value for k in decorator.keywords if k.arg == "name"),
                                decorator.args[0] if decorator.args else None)
                    if name is None or (isinstance(name, ast.Constant) and name.value is None):
                        registered.add(node.name.replace("_", "-"))
                    elif isinstance(name, ast.Constant) and isinstance(name.value, str):
                        registered.add(name.value)
            for command in ("doctor", "smoke"):
                if command not in registered:
                    problems.append(
                        f"src/{pkg}/{module}: {command} is not registered on app — "
                        f"CLAUDE.md advertises `uv run {slug} {command}`")
    if not (dest / "tests" / "test_scaffold.py").exists():
        problems.append("tests/test_scaffold.py missing — `uv run pytest -q` has no tests")
    return problems


def cmd_new_project(args: argparse.Namespace) -> int:
    """Scaffold projects/NNN-slug from the project template."""
    slug = slugify(args.name)
    existing = _projects()
    nums = [int(m.group(1)) for p in existing if (m := re.match(r"(\d+)-", p.name))]
    number = f"{max(nums, default=0) + 1:03d}"
    dest = PROJECTS / f"{number}-{slug}"
    if dest.exists():
        die(f"{dest.name} already exists")

    pkg = slug.replace("-", "_")
    for sub in ("experiments", "notes", "results", "data", "explore", f"src/{pkg}", "tests"):
        (dest / sub).mkdir(parents=True, exist_ok=True)

    fields = dict(slug=slug, number=number, name=args.name, date=today(), pkg=pkg)
    render(TEMPLATES / "project" / "CLAUDE.md", dest / "CLAUDE.md", **fields)
    render(TEMPLATES / "project" / "README.md", dest / "README.md", **fields)
    render(TEMPLATES / "project" / "pyproject.toml", dest / "pyproject.toml", **fields)
    for module in ("__init__.py", "device.py", "cli.py", "provenance.py"):
        render(TEMPLATES / "project" / module, dest / "src" / pkg / module, **fields)
    render(TEMPLATES / "project" / "test_scaffold.py",
           dest / "tests" / "test_scaffold.py", **fields)
    for keep in ("data", "results", "explore"):
        (dest / keep / ".gitkeep").touch()

    problems = _validate_scaffold(dest, slug=slug, pkg=pkg)
    if problems:
        print()
        for p in problems:
            print(red(f"  invalid scaffold: {p}"))
        # A half-built project on disk is worse than none: a retry dies on
        # "already exists" (numbers are never reused), and rx check would flag
        # the zombie's missing uv.lock and dependabot entry forever.
        shutil.rmtree(dest, ignore_errors=True)
        print(yellow(f"  removed projects/{dest.name} — nothing was created"))
        die("scaffold self-validation failed — fix templates/project/ or cmd_new_project")

    print()
    print(f"  {_append_dependabot_entry(dest.name)}")
    print(f"  {_try_uv_lock(dest)}")
    if not (dest / "uv.lock").exists():
        print(yellow(f"  remedy: cd projects/{number}-{slug} && uv lock, then commit uv.lock —"))
        print(yellow("  'uv run tools/rx.py check' keeps flagging the missing lock until then"))
    print()
    print(f"  next: {bold(f'cd projects/{number}-{slug} && uv sync && uv run {slug} doctor')}")
    print(dim("  then write notes/ and a preregistered experiments/E001-*.md before any code"))
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    """Create a source, idea, synthesis, lead, claim, or experiment note from a template."""
    kind, slug = args.kind, slugify(args.slug)
    fields = dict(slug=slug, date=today(), title=args.slug)
    if kind == "article":
        render(TEMPLATES / "article.md", ARTICLES / f"{slug}.md", **fields)
    elif kind == "lead":
        # Leads carry the lead- prefix in the filename so the queue is greppable.
        render(TEMPLATES / "lead.md", LEADS / f"lead-{slug}.md", **fields)
    elif kind in ("source", "idea", "synthesis"):
        dest = LIBRARY / f"{kind}s" / f"{slug}.md"
        render(TEMPLATES / f"{kind}.md", dest, **fields)
    elif kind == "claim":
        if not args.project:
            die("claim needs --project (e.g. --project 001-geometric-reasoning)")
        dest = PROJECTS / args.project / "notes" / f"claim-{slug}.md"
        render(TEMPLATES / "claim.md", dest, **fields)
    elif kind == "experiment":
        if not args.project:
            die("experiment needs --project (e.g. --project 001-geometric-reasoning)")
        exp_dir = PROJECTS / args.project / "experiments"
        if not exp_dir.exists():
            die(f"no such project: {args.project}")
        nums = [int(m.group(1)) for f in exp_dir.glob("E*.md")
                if (m := re.match(r"E(\d+)", f.name))]
        eid = f"E{max(nums, default=0) + 1:03d}"
        dest = exp_dir / f"{eid}-{slug}.md"
        render(TEMPLATES / "experiment.md", dest, eid=eid, **fields)
    else:
        die(f"unknown kind {kind!r}")
    return 0


CORPUS = LIBRARY / "corpus"
CORPUS_INDEX = CORPUS / "INDEX.md"
DOC_SUFFIXES = {".pdf", ".epub", ".djvu", ".txt", ".md", ".html", ".htm", ".ps"}
_INDEX_HEADER = (
    "| status | document | sha256 | size | added | source note |\n"
    "|---|---|---|---|---|---|\n"
)


def _sha256(path: Path, limit: int = 64 * 1024 * 1024) -> str:
    """Hash the first ``limit`` bytes. Enough to identify a document, cheap on a 400MB scan."""
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1 << 20):
            h.update(chunk)
            limit -= len(chunk)
            if limit <= 0:
                break
    return h.hexdigest()[:12]


def _index_rows() -> dict[str, str]:
    """Existing INDEX.md rows, keyed by document path. Rows are never rewritten by rx —
    status is maintained by whoever read the document."""
    if not CORPUS_INDEX.exists():
        return {}
    rows: dict[str, str] = {}
    for line in CORPUS_INDEX.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 6 and cells[0] not in ("status", "---"):
            rows[cells[1].strip("`")] = line
    return rows


def cmd_ingest(args: argparse.Namespace) -> int:
    """Register new documents in library/corpus/ into its INDEX.md reading queue."""
    CORPUS.mkdir(parents=True, exist_ok=True)
    known = _index_rows()
    found = [
        p for p in sorted(CORPUS.rglob("*"))
        if p.is_file() and p.suffix.lower() in DOC_SUFFIXES
        # The corpus dir's own committed files are not corpus documents.
        and not (p.parent == CORPUS and p.name in ("INDEX.md", "README.md"))
    ]
    if not found:
        print(yellow(f"  no documents in {CORPUS.relative_to(ROOT).as_posix()}/"))
        print(dim("  drop PDFs/EPUBs there (gitignored), then re-run ingest"))
        return 0

    new_rows: list[str] = []
    for doc in found:
        rel = doc.relative_to(CORPUS).as_posix()
        if rel in known:
            continue
        size_mb = doc.stat().st_size / 1e6
        new_rows.append(
            f"| unread | `{rel}` | `{_sha256(doc)}` | {size_mb:.1f} MB | {today()} | - |"
        )
        print(green("queued ") + rel)

    if new_rows:
        body = CORPUS_INDEX.read_text(encoding="utf-8") if CORPUS_INDEX.exists() else ""
        if "| status |" not in body:
            body = (body.rstrip() + "\n\n" if body.strip() else "") + _INDEX_HEADER
        body = body.rstrip("\n") + "\n" + "\n".join(new_rows) + "\n"
        CORPUS_INDEX.write_text(body, encoding="utf-8", newline="\n")

    unread = sum(1 for line in known.values() if line.split("|")[1].strip() == "unread")
    print()
    print(f"  {len(found)} document(s) present, {len(new_rows)} newly queued, "
          f"{unread + len(new_rows)} unread")
    print(dim("  never commit the documents themselves - INDEX.md is the committed artifact"))
    return 0


LEADS = LIBRARY / "leads"
ARTICLES = ROOT / "articles"
_AXES = ("kill", "novelty", "discrimination", "load")


def _leads() -> list[dict]:
    """Parse lead notes into sortable records. Gates are applied here, not by the reader."""
    out = []
    for path in sorted(LEADS.glob("lead-*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        scores = {ax: int(m.group(1)) for ax in _AXES
                  if (m := re.search(rf"\b{ax}=(\d)", text))}
        status = (m.group(1).strip("`") if (m := re.search(r"\*\*Status:\*\*\s*(\S+)", text))
                  else "?")
        origin = (m.group(1).strip("`") if (m := re.search(r"\*\*Origin:\*\*\s*([\w-]+)", text))
                  else "?")
        title = next((ln[len("# Lead — "):].strip() for ln in text.splitlines()
                      if ln.startswith("# Lead")), path.stem)
        gated = [ax for ax in ("kill", "discrimination", "novelty") if scores.get(ax) == 0]
        out.append({
            "path": path, "slug": path.stem, "title": title, "status": status,
            "origin": origin, "scores": scores, "gated": gated,
            "total": sum(scores.values()) if len(scores) == len(_AXES) else -1,
        })
    return out


def cmd_leads(args: argparse.Namespace) -> int:
    """List the discovery queue: things worth more research, ranked, gates applied."""
    leads = _leads()
    if not leads:
        print(yellow("  no leads yet"))
        print(dim("  uv run tools/rx.py new lead <slug>   (see library/leads/README.md)"))
        return 0

    live = [x for x in leads if not x["gated"] and x["status"] in ("open", "claimed")]
    live.sort(key=lambda x: -x["total"])
    rest = [x for x in leads if x not in live]

    print()
    print(bold("  discovery queue") + dim("   kill/novelty/discrimination/load"))
    print()
    for lead in live:
        s = "/".join(str(lead["scores"].get(ax, "?")) for ax in _AXES)
        print(f"  {green(str(lead['total']).rjust(2))}  {s}  {dim(lead['origin'].ljust(20))}"
              f"  {lead['title']}")
        print(f"      {dim(lead['path'].relative_to(ROOT).as_posix())}")
    if rest:
        print()
        print(bold("  not in the queue"))
        for lead in rest:
            why = ("gated on " + ", ".join(lead["gated"])) if lead["gated"] else lead["status"]
            print(f"  {yellow('--')}  {lead['title']}  {dim('(' + why + ')')}")
    print()
    print(dim("  score is a sort key, not a truth. cheapest-to-kill first."))
    print()
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Readiness and state of one project: is it set up, and where is it at?"""
    matches = [p for p in _projects() if args.project in p.name]
    if not matches:
        die(f"no project matching {args.project!r}; try: uv run tools/rx.py projects")
    proj = matches[0]

    print()
    print(bold(f"  {proj.name}"))

    print()
    print(bold("  readiness"))
    venv = proj / ".venv"
    pyproject = proj / "pyproject.toml"
    print(f"    pyproject   {green('ok') if pyproject.exists() else yellow('missing')}")
    print(f"    venv        {green('ok') if venv.exists() else yellow('not synced') + dim('  -> uv sync')}")
    cli = ""
    if pyproject.exists():
        body = pyproject.read_text(encoding="utf-8", errors="replace")
        if m := re.search(r"^\s*(\w[\w-]*)\s*=\s*\"[\w.]+:app\"", body, re.M):
            cli = m.group(1)
    if cli:
        print(f"    cli         {cli}" + dim(f"   -> uv run {cli} doctor"))

    print()
    print(bold("  experiments"))
    exps = sorted((proj / "experiments").glob("E*.md"))
    results = list((proj / "results").glob("*.json"))
    if not exps:
        print(dim("    none preregistered"))
    for exp in exps:
        text = exp.read_text(encoding="utf-8", errors="replace")
        eid = exp.name.split("-")[0]
        runs = [r for r in results if r.name.startswith(eid)]
        # A verdict exists when the Verdict section names an outcome. The template's own
        # "supported / falsified / inconclusive" prompt is stripped first, or every
        # freshly-scaffolded experiment would report itself as decided.
        vsec = text.split("## Verdict", 1)[1][:800] if "## Verdict" in text else ""
        vsec = vsec.replace("supported / falsified / inconclusive", "")
        decided = re.search(r"(?i)\b(falsified|supported|inconclusive|confounded)\b", vsec)
        verdict = "verdict" if decided else ("has runs" if runs else "preregistered")
        colour = green if verdict == "verdict" else (yellow if runs else dim)
        print(f"    {eid:<6} {colour(verdict.ljust(14))} {len(runs)} run record(s)  "
              f"{dim(exp.name)}")

    orphans = [r for r in results
               if not any(r.name.startswith(e.name.split("-")[0]) for e in exps)]
    if orphans:
        print()
        print(f"    {yellow('orphan results')} (a number with no preregistration):")
        for o in orphans:
            print(f"      {o.name}")

    print()
    print(bold("  claims"))
    for note in sorted((proj / "notes").glob("claim-*.md")):
        text = note.read_text(encoding="utf-8", errors="replace")
        cls = m.group(1) if (m := re.search(r"\*\*Class:\*\*\s*`?\[?(\w+)", text)) else "?"
        print(f"    [{cls}] {note.stem}")

    print()
    print(bold("  next"))
    doc = proj / "CLAUDE.md"
    if doc.exists() and "Start here" in doc.read_text(encoding="utf-8", errors="replace"):
        print(dim(f"    read {proj.name}/CLAUDE.md -> 'Start here' work queue"))
    else:
        print(dim(f"    read {proj.name}/CLAUDE.md"))
    print()
    return 0


def _dependabot_entries(text: str) -> list[dict[str, object]]:
    """Parse the small, fixed subset of Dependabot's YAML this repo uses.

    stdlib only: PyYAML is not available in the bare-checkout toolchain. The parser
    accepts exactly the shape in .github/dependabot.yml and ignores everything else.
    """
    entries: list[dict[str, object]] = []
    entry: dict[str, object] | None = None
    in_groups = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "updates:":
            continue
        if line.startswith("- "):
            entry = {}
            entries.append(entry)
            in_groups = False
            line = line[2:].strip()
        if entry is None:
            continue
        if line.startswith("package-ecosystem:"):
            entry["package-ecosystem"] = line.split(":", 1)[1].strip().strip('"\'')
        elif line.startswith("directory:"):
            entry["directory"] = line.split(":", 1)[1].strip().strip('"\'')
        elif line == "groups:":
            in_groups = True
        elif in_groups and line.endswith(":"):
            entry["group"] = line[:-1]
            in_groups = False
    return entries


def _canonical_name(name: str) -> str:
    """PEP 503 normalisation: uv lowercases names and dashes run together in uv.lock."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_parts(requirement: str) -> tuple[str, str]:
    """Split a manifest requirement into (canonical name, constraint).

    "torch[cpu] >=2.5,<3 ; python_version >= '3.12'" -> ("torch", ">=2.5,<3").
    The marker after ';' is dropped: uv.lock records markers on its own terms and
    they carry no staleness signal.
    """
    head = requirement.split(";", 1)[0].strip()
    match = re.match(r"[A-Za-z0-9._-]+", head)
    if match is None:
        return "", head.replace(" ", "")
    name = _canonical_name(match.group(0))
    rest = head[match.end():].strip()
    if rest.startswith("[") and "]" in rest:
        rest = rest.split("]", 1)[1].strip()
    return name, rest.replace(" ", "")


def _lock_divergences(pyproject: Path, lock: Path) -> list[str]:
    """Every way uv.lock fails to describe pyproject.toml's project; empty == resolves.

    Carrying the project's root package is not enough: a lock written before the
    manifest changed keeps that name while pinning the old requirements — numpy
    stays at >=1.26 after the manifest moves to numpy>=2. So the recorded root
    requirements ([package.metadata].requires-dist), the uv index sources resolved
    through [[tool.uv.index]] — compared in both directions, so a source deleted
    from the manifest is caught from the locked side too — requires-python, and
    the extras (names, and via their extra-scoped requires-dist records the
    constraints) are each compared against the manifest itself. Every divergence
    is one string naming what moved.
    """
    try:
        manifest = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        locked = tomllib.loads(lock.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [f"unparseable, so it cannot be checked against its manifest ({exc})"]

    project = manifest.get("project", {})
    name = project.get("name")
    if not name:
        return ["pyproject.toml declares no project.name — nothing to anchor the lock to"]

    canonical = _canonical_name(str(name))
    root = next(
        (pkg for pkg in locked.get("package", [])
         if _canonical_name(str(pkg.get("name", ""))) == canonical),
        None,
    )
    if root is None:
        return [f"root package '{name}' is absent — the lock does not describe this project"]

    divergences: list[str] = []

    manifest_python = str(project.get("requires-python", "")).strip()
    lock_python = str(locked.get("requires-python", "")).strip()
    if manifest_python != lock_python:
        divergences.append(
            f"requires-python is {lock_python!r} but the manifest says "
            f"{manifest_python!r} (run 'uv lock')")

    locked_reqs: dict[str, list[dict[str, object]]] = {}
    for entry in root.get("metadata", {}).get("requires-dist", []):
        if isinstance(entry, dict):
            key = _canonical_name(str(entry.get("name", "")))
            locked_reqs.setdefault(key, []).append(entry)

    def _main_entry(req_name: str) -> dict[str, object] | None:
        """The requires-dist record for a plain dependency; extra-scoped ones don't count."""
        return next(
            (e for e in locked_reqs.get(req_name, [])
             if "extra ==" not in str(e.get("marker", ""))),
            None,
        )

    for requirement in [str(r) for r in project.get("dependencies", [])]:
        req_name, constraint = _requirement_parts(requirement)
        if not req_name:
            divergences.append(f"requirement {requirement!r} has no parseable name")
            continue
        entry = _main_entry(req_name)
        if entry is None:
            divergences.append(
                f"'{req_name}' is required by the manifest but absent from requires-dist "
                "(run 'uv lock')")
            continue
        locked_spec = str(entry.get("specifier", "") or "").replace(" ", "")
        if constraint != locked_spec:
            divergences.append(
                f"'{req_name}' constraint is {constraint!r} in the manifest but "
                f"{locked_spec!r} in the lock (run 'uv lock')")

    # uv index sources: the manifest pins some requirements to a named index; the lock
    # records the resolved index URL on the requirement it was resolved from. Non-index
    # source kinds (path/git/url) live on the package table instead and are not compared.
    tool_uv = manifest.get("tool", {}).get("uv", {})
    indexes = {
        str(idx.get("name")): str(idx.get("url", ""))
        for idx in tool_uv.get("index", [])
        if isinstance(idx, dict) and idx.get("name")
    }
    sources = tool_uv.get("sources", {})
    if not isinstance(sources, dict):
        sources = {}
    for source_pkg, source_def in sources.items():
        pkg = _canonical_name(str(source_pkg))
        defs = source_def if isinstance(source_def, list) else [source_def]
        index_name = next(
            (str(d.get("index")) for d in defs
             if isinstance(d, dict) and d.get("index") is not None),
            None,
        )
        entry = _main_entry(pkg)
        if index_name is None:
            if entry is not None and entry.get("index"):
                divergences.append(
                    f"'{pkg}' is pinned to index '{entry['index']}' in the lock but the "
                    "manifest declares no index source for it (run 'uv lock')")
            continue
        resolved = indexes.get(index_name, "")
        if not resolved:
            divergences.append(
                f"source for '{pkg}' names index {index_name!r} with no matching "
                "[[tool.uv.index]] entry")
        elif entry is None:
            divergences.append(
                f"'{pkg}' has an index source but is absent from requires-dist (run 'uv lock')")
        else:
            locked_index = str(entry.get("index", "") or "")
            if locked_index != resolved:
                divergences.append(
                    f"'{pkg}' index source resolves to {resolved!r} in the manifest but "
                    f"{locked_index!r} in the lock (run 'uv lock')")

    # The forward pass above only visits packages the manifest still names, so a
    # source deleted from the manifest leaves the lock's pin unexamined. Compare the
    # locked side too: any requires-dist entry carrying an index must still have a
    # surviving manifest source. (Every other shape — a source naming a missing
    # index, an unresolvable or mismatched one — is reported by the forward pass,
    # so this fires only where no source survives at all.)
    declared_sources = {_canonical_name(str(k)) for k in sources}
    for req_key, entries in locked_reqs.items():
        pinned = [e for e in entries if e.get("index")]
        if not pinned or req_key in declared_sources:
            continue
        locked_index = str(pinned[0].get("index", "") or "")
        divergences.append(
            f"'{req_key}' is pinned to index {locked_index!r} in the lock but the "
            "manifest declares no index source for it (run 'uv lock')")

    # Optional dependencies: the lock's [package.optional-dependencies] records names
    # only, so the constraint is compared where uv records it — the extra-scoped
    # requires-dist entry (marker `extra == '<extra>'`), same as the main dependencies.
    locked_extras = root.get("optional-dependencies", {})

    def _extra_entry(extra_name: str, req_name: str) -> dict[str, object] | None:
        """The requires-dist record for req_name scoped to this extra, if any."""
        scoped = re.compile(rf"extra\s*==\s*['\"]{re.escape(extra_name)}['\"]")
        return next(
            (e for e in locked_reqs.get(req_name, [])
             if scoped.search(str(e.get("marker", "")))),
            None,
        )

    for extra, requirements in project.get("optional-dependencies", {}).items():
        want = sorted(_requirement_parts(str(r))[0] for r in requirements)
        have = sorted(
            _canonical_name(str(e.get("name", "")))
            for e in locked_extras.get(extra, [])
            if isinstance(e, dict)
        )
        if want != have:
            divergences.append(
                f"extra {extra!r} is {want} in the manifest but {have} in the lock "
                "(run 'uv lock')")
            continue
        for requirement in [str(r) for r in requirements]:
            req_name, constraint = _requirement_parts(requirement)
            if not req_name:
                divergences.append(f"requirement {requirement!r} has no parseable name")
                continue
            entry = _extra_entry(extra, req_name)
            if entry is None:
                divergences.append(
                    f"'{req_name}' is required by extra {extra!r} but has no "
                    "extra-scoped requires-dist record (run 'uv lock')")
                continue
            locked_spec = str(entry.get("specifier", "") or "").replace(" ", "")
            if constraint != locked_spec:
                divergences.append(
                    f"'{req_name}' constraint is {constraint!r} in the manifest for "
                    f"extra {extra!r} but {locked_spec!r} in the lock (run 'uv lock')")

    return divergences


def _check_dependency_updates(problems: list[str]) -> None:
    """A uv-managed project is discoverable only via ecosystem "uv" + a committed uv.lock.

    The Dependabot manifest is required, not optional: with uv-managed projects in the
    tree and no .github/dependabot.yml, nothing would be checked at all — the silent
    pass this function exists to prevent.
    """
    manifest_path = ROOT / ".github" / "dependabot.yml"
    entries: list[dict[str, object]] = []
    if manifest_path.exists():
        entries = _dependabot_entries(manifest_path.read_text(encoding="utf-8", errors="replace"))
    # Every entry per directory is kept. Two entries naming one directory are a config
    # bug, not an override pair: collapsing them would silently validate one entry
    # against the other's ecosystem and leave the other one unchecked.
    by_dir: dict[str, list[dict[str, object]]] = {}
    for entry in entries:
        by_dir.setdefault(str(entry.get("directory", "")), []).append(entry)

    for directory, dupes in by_dir.items():
        if len(dupes) > 1:
            listed = ", ".join(
                f"#{i + 1} (package-ecosystem {e.get('package-ecosystem')!r})"
                for i, e in enumerate(dupes)
            )
            problems.append(
                f".github/dependabot.yml: {len(dupes)} updates entries name the same "
                f"directory {directory!r}: {listed}; only one can apply")

    uv_projects: list[Path] = []
    for pyproject in sorted(PROJECTS.glob("*/pyproject.toml")):
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            problems.append(f"{pyproject.relative_to(ROOT).as_posix()}: invalid TOML ({exc})")
            continue
        if "uv" in data.get("tool", {}):
            uv_projects.append(pyproject)

    if not entries:
        if uv_projects:
            state = "missing" if not manifest_path.exists() else "has no updates entries"
            names = ", ".join(
                p.parent.relative_to(ROOT).as_posix() for p in uv_projects)
            problems.append(
                f".github/dependabot.yml: {state} - {len(uv_projects)} uv-managed "
                f"project(s) ({names}) have no updater configuration")
        return

    for pyproject in uv_projects:
        project_dir = pyproject.parent
        rel = project_dir.relative_to(ROOT).as_posix()
        dir_entries = by_dir.get(f"/{rel}")
        if not dir_entries:
            problems.append(
                f".github/dependabot.yml: no updates entry for uv-managed project '{rel}'")
            continue
        for entry in dir_entries:
            if entry.get("package-ecosystem") != "uv":
                problems.append(
                    f".github/dependabot.yml: uv-managed project '{rel}' names package-ecosystem "
                    f"{entry.get('package-ecosystem')!r}; an updater can only discover it as 'uv'")
        lock = project_dir / "uv.lock"
        if not lock.exists():
            problems.append(
                f"{rel}/uv.lock: missing - the uv ecosystem has nothing to discover")
            continue
        for divergence in _lock_divergences(pyproject, lock):
            problems.append(f"{rel}/uv.lock: {divergence}")


def cmd_check(args: argparse.Namespace) -> int:
    """Lint the knowledge base and the dependency-update configuration."""
    problems: list[str] = []
    notes = list(LIBRARY.rglob("*.md")) + list(PROJECTS.rglob("notes/*.md")) + \
        list(PROJECTS.rglob("experiments/*.md"))
    known = {p.stem for p in LIBRARY.rglob("*.md")}

    for note in notes:
        text = note.read_text(encoding="utf-8", errors="replace")
        rel = note.relative_to(ROOT).as_posix()
        for link in re.findall(r"\[\[([^\]]+)\]\]", text):
            target = link.split("/")[-1]
            if target not in known:
                problems.append(f"{rel}: dangling link [[{link}]]")
        if note.parent.name in ("sources", "ideas", "syntheses") and \
                not re.search(r"\[(source|lit|ours|open)\]", text):
            problems.append(f"{rel}: no evidence tags — every note needs them")

    for doc, line in _index_rows().items():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        status, note = cells[0], cells[5].strip("`")
        if status == "noted" and (note in ("-", "") or not (ROOT / note).exists()):
            problems.append(
                f"library/corpus/INDEX.md: '{doc}' marked noted but its source note is missing")
        if status not in ("unread", "reading", "noted", "skipped"):
            problems.append(
                f"library/corpus/INDEX.md: '{doc}' has unknown status {status!r}")

    # An article is the one thing here a stranger reads. Every repo path it cites must
    # resolve, and an unreferenced article is opinion with a byline.
    for art in ARTICLES.glob("*.md"):
        if art.name == "README.md":
            continue
        text = art.read_text(encoding="utf-8", errors="replace")
        rel = art.relative_to(ROOT).as_posix()
        for path in set(re.findall(r"`((?:projects|library|tools)/[\w./-]+)`", text)):
            if not (ROOT / path).exists() and "NNN" not in path and "E00N" not in path:
                problems.append(f"{rel}: cites a path that does not exist - {path}")
        if not re.search(r"\[(ours|lit|corpus|src):", text):
            problems.append(f"{rel}: no reference keys - every factual sentence needs one")

    for probe in PROJECTS.rglob("explore/*.json"):
        try:
            rec = json.loads(probe.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(rec, dict) and {"seed", "metrics"} <= set(rec):
            problems.append(
                f"{probe.relative_to(ROOT).as_posix()}: run-record shape in explore/ - "
                "nothing there is a result; move it to results/ or drop the seed/metrics keys")

    for lead in _leads():
        rel = lead["path"].relative_to(ROOT).as_posix()
        if len(lead["scores"]) != len(_AXES):
            missing = [ax for ax in _AXES if ax not in lead["scores"]]
            problems.append(f"{rel}: unscored axes {', '.join(missing)} - it cannot be ranked")
        if lead["status"] == "promoted" and "## Route" not in lead["path"].read_text(
                encoding="utf-8", errors="replace"):
            problems.append(f"{rel}: marked promoted with no route recorded")
        if lead["gated"] and lead["status"] == "open":
            problems.append(
                f"{rel}: gated on {', '.join(lead['gated'])} but still open - mark it dead")

    for results in PROJECTS.rglob("results/*.json"):
        try:
            rec = json.loads(results.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{results.relative_to(ROOT).as_posix()}: invalid JSON ({exc})")
            continue
        for field in ("seed", "git_sha", "config"):
            if field not in rec:
                problems.append(
                    f"{results.relative_to(ROOT).as_posix()}: run record missing '{field}'")

    _check_dependency_updates(problems)

    if problems:
        print()
        for p in problems:
            print(f"  {yellow('warn')}  {p}")
        print()
        print(f"  {len(problems)} problem(s)")
        return 1
    print(green("  knowledge base clean"))
    return 0


COMMANDS = {
    "help": cmd_help,
    "doctor": cmd_doctor,
    "projects": cmd_projects,
    "new-project": cmd_new_project,
    "new": cmd_new,
    "ingest": cmd_ingest,
    "leads": cmd_leads,
    "status": cmd_status,
    "check": cmd_check,
}


def main(argv: list[str] | None = None) -> int:
    # Windows consoles default to cp1252, which cannot encode the pipeline arrows below and
    # kills the command with a UnicodeEncodeError. Not worth losing a command over.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(prog="rx", add_help=False)
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("help")
    sub.add_parser("doctor")
    sub.add_parser("projects")
    sub.add_parser("check")
    sub.add_parser("ingest")
    sub.add_parser("leads")

    p_st = sub.add_parser("status")
    p_st.add_argument("project", help="project name or fragment, e.g. 002")

    p_np = sub.add_parser("new-project")
    p_np.add_argument("name", help="human name; slugified for the directory")

    p_new = sub.add_parser("new")
    p_new.add_argument("kind", choices=["source", "idea", "synthesis", "lead", "article",
                                        "claim", "experiment"])
    p_new.add_argument("slug")
    p_new.add_argument("--project", help="required for claim/experiment")

    args = parser.parse_args(argv)
    fn = COMMANDS.get(args.command or "help")
    if fn is None:
        return cmd_help(args)
    return fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
