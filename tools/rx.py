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
    """Create a source, idea, synthesis, lead, claim, or experiment note from a template."""
    kind, slug = args.kind, slugify(args.slug)
    fields = dict(slug=slug, date=today(), title=args.slug)
    if kind == "lead":
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

    for doc, line in _index_rows().items():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        status, note = cells[0], cells[5].strip("`")
        if status == "noted" and (note in ("-", "") or not (ROOT / note).exists()):
            problems.append(
                f"library/corpus/INDEX.md: '{doc}' marked noted but its source note is missing")
        if status not in ("unread", "reading", "noted", "skipped"):
            problems.append(
                f"library/corpus/INDEX.md: '{doc}' has unknown status {status!r}")

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
    p_new.add_argument("kind",
                       choices=["source", "idea", "synthesis", "lead", "claim", "experiment"])
    p_new.add_argument("slug")
    p_new.add_argument("--project", help="required for claim/experiment")

    args = parser.parse_args(argv)
    fn = COMMANDS.get(args.command or "help")
    if fn is None:
        return cmd_help(args)
    return fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
