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
import datetime as dt
import json
import os
import platform
import re
import shutil
import subprocess
import sys
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
    print(dim("    source ──► idea ──► synthesis ──► claim ──► experiment ──► verdict"))
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


def cmd_new_project(args: argparse.Namespace) -> int:
    """Scaffold projects/NNN-slug from the project template."""
    slug = slugify(args.name)
    existing = _projects()
    nums = [int(m.group(1)) for p in existing if (m := re.match(r"(\d+)-", p.name))]
    number = f"{max(nums, default=0) + 1:03d}"
    dest = PROJECTS / f"{number}-{slug}"
    if dest.exists():
        die(f"{dest.name} already exists")

    for sub in ("experiments", "notes", "results", "data", f"src/{slug.replace('-', '_')}", "tests"):
        (dest / sub).mkdir(parents=True, exist_ok=True)

    fields = dict(slug=slug, number=number, name=args.name, date=today(),
                  pkg=slug.replace("-", "_"))
    render(TEMPLATES / "project" / "CLAUDE.md", dest / "CLAUDE.md", **fields)
    render(TEMPLATES / "project" / "README.md", dest / "README.md", **fields)
    (dest / "data" / ".gitkeep").touch()
    (dest / "results" / ".gitkeep").touch()
    print()
    print(f"  next: {bold(f'cd projects/{number}-{slug}')}")
    print(dim("  then write notes/ and a preregistered experiments/E001-*.md before any code"))
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    """Create a source, idea, claim, or experiment note from a template."""
    kind, slug = args.kind, slugify(args.slug)
    fields = dict(slug=slug, date=today(), title=args.slug)
    if kind in ("source", "idea", "synthesis"):
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


def cmd_check(args: argparse.Namespace) -> int:
    """Lint the knowledge base: dangling [[links]], untagged claims, orphan results."""
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
    "check": cmd_check,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rx", add_help=False)
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("help")
    sub.add_parser("doctor")
    sub.add_parser("projects")
    sub.add_parser("check")

    p_np = sub.add_parser("new-project")
    p_np.add_argument("name", help="human name; slugified for the directory")

    p_new = sub.add_parser("new")
    p_new.add_argument("kind", choices=["source", "idea", "synthesis", "claim", "experiment"])
    p_new.add_argument("slug")
    p_new.add_argument("--project", help="required for claim/experiment")

    args = parser.parse_args(argv)
    fn = COMMANDS.get(args.command or "help")
    if fn is None:
        return cmd_help(args)
    return fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
