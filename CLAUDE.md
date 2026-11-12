# research

Research monorepo for developerz.ai. A factory for research topics: many independent
projects, one fixed pipeline. Each takes an idea — from a book, paper, or talk — and finds
out whether it's **true**, via a runnable PoC plus documentation.

## Non-negotiables
Each rule lives here and nowhere else in this file. Break one and the work is rejected.

| Rule | Detail / guard |
|---|---|
| **Verdicts, not products** | Output = documented verdicts. A cleanly-measured negative is a success — never soften one. Shippable things graduate to their own repo. |
| **uv only** | Python 3.12 via uv. Never `pip install` into system Python. |
| **Device-agnostic code** | Call `pick_device()` / `autocast_dtype()` from the project's `device` module. No vendor branching, no `.cuda()`, no `"cuda"` literals, no `torch.cuda.*` capability checks (`torch.cuda.is_available()` is `True` on ROCm). `ruff` enforces it outside `device.py`. |
| **`pathlib.Path` only** | Repo runs on Windows *and* Linux; a hardcoded `/` breaks one and nobody tests the other. |
| **Tag every factual statement** | Evidence class (table below). Untagged prose = opinion. |
| **Falsifier before code** | Write what would kill the claim before what might confirm it. |
| **Preregister** | Hypothesis + metric + threshold + item count land in the experiment doc before the number exists. Amending is allowed — say that you amended and why. |
| **Matched baseline** | Matched on compute budget — say which (params · tokens · wall-clock). Vendor benchmark numbers are not baselines: reproduce the *eval*, compare on your own matched pair. |
| **≥3 seeds, seeds in config** | One seed is an anecdote; report spread. A seed baked into source cannot be swept. |
| **No number without a run record** | `results/*.json` carries seed, git SHA, hardware, full config, per-item outputs. Never report an aggregate without the per-item data. |
| **Contamination check** | Before any benchmark claim: if the eval predates the model's cutoff, assume it is in the training data until shown otherwise. |
| **Scope the finding** | State what the experiment cannot conclude. |
| **A SKIPPED check is not green** | `rx check` exits non-zero if any suite fails or cannot start (pytest missing). A project with no usable `.venv` is SKIPPED (remedy: `uv sync --extra dev`) — those tests never ran; say so. |
| **No cross-project imports** | Promote shared code to `tools/` or copy it. |
| **No weights or raw corpora in git** | `results/` JSON + plots **are** committed; `library/corpus/**` is not, except its committed `INDEX.md`. |
| **No git worktrees** | Work in this checkout. Parallel agents get disjoint files. |

## Scope
Subjects are not restricted to AI. Empirical sciences and advanced mathematics are in
scope, on one condition: the project must reach a **falsifiable measurement on the reference
hardware**. Where the headline question cannot (most of physics), the project says so
explicitly in writing *before* the first run, and tests the reachable sub-question without
implying it settled the original (never quietly swap in an easier question) — worked example:
`projects/002-ftl-axiom-search/notes/out-of-scope-ftl.md`. Philosophy is welcome as
*motivation*, never as a substitute for a metric. No benchmark-leaderboard chasing: we test
mechanisms, not scores.

## Response Rules
- Execute. No preamble. No restating the task.
- Lead with the finding. Reasoning after, only if non-obvious.
- Parallel tool calls when independent.
- Read before speculating. Measure before claiming.
- Disagree when the user is wrong. State the correction.
- Terse. Fragments OK. Paths/commands/numbers stay exact.

## Evidence classes
| Tag | Means | Rule |
|---|---|---|
| `[source]` | The source asserts it | Cite file + locator (timestamp/page). Vendor claims about their own product **stay here permanently** until independently replicated. |
| `[lit]` | External published work supports it | Cite URL/arXiv. Note peer review + replication status. |
| `[ours]` | We measured it here | Cite experiment ID + results file. |
| `[open]` | Unverified | Fine to hold. Not fine to build on silently. |

The failure mode this prevents: a `[source]` claim quietly promoting itself to background fact over a few weeks.

## Layout
| Path | Holds |
|---|---|
| `bin/` | `check` — the canonical "is this tree green?" shim. |
| `docs/` | Method, toolchain, project kickoff. Load on demand. |
| `templates/` | Copy when starting a source/idea/claim/experiment/project. |
| `library/corpus/` | The raw pile — papers, theses, books. **Gitignored**; `INDEX.md` is the committed record. |
| `library/sources/` | One file per book/paper/talk consumed. What was said, neutrally, with locators. |
| `library/ideas/` | One file per atomic idea. Reusable across projects. |
| `library/syntheses/` | Combinations across sources. The point of the repo. |
| `library/leads/` | **Discoveries** — things worth more research, scored and gated. What the repo produces of its own. |
| `articles/` | Findings worth sharing, written for outsiders. Concise, every sentence referenced. |
| `projects/NNN-slug/` | Self-contained PoC. Own venv, own `CLAUDE.md`, own agents. |
| `tools/` | Shared scripts (`rx.py`). |
| `.claude/agents/` | Repo-wide pipeline agents. Roster + dispatch → `docs/hive.md`. |

Ideas are **cross-project property** and live only in `library/ideas/`. Never file one under
a project — the transfer of an idea between projects is the point of the repo.

Project numbers are assigned in creation order, never changed, never reused — links stay stable.

## Pipeline
```
acquire ──► source ──► idea ──► synthesis ──► claim ──► experiment ──► verdict
                            │                                    │
                            └──────────────► lead ◄──────────────┘
```
Each arrow is where a claim earns passage. Details → `docs/method.md`.

Leads flow **out** of the pipeline as much as into it: a verdict — especially a null one —
is the richest source of things worth more research. `library/leads/README.md` holds the
scoring gates.

## Stack
| | |
|---|---|
| Python | 3.12 |
| DL | PyTorch. Wheel index pinned per backend (`cu126` / `rocm` / `cpu`) — never default PyPI |
| Platforms | **Windows + Linux. macOS is not a target.** |
| Accelerators | NVIDIA (CUDA) · AMD (ROCm, Linux) · CPU fallback always works |
| Reference box | RTX 3090 24GB · Ryzen 7 5700X3D 8c/16t · 64GB RAM |

Portability:
- **A CPU-only torch wheel is a silent failure, not an error.** Everything "works", 50× slower. Guard: `uv run geom doctor` in every fresh venv — it fails loudly when wheel and hardware disagree.
- `bf16` only when the device reports support (Ampere+, MI200+); elsewhere it is silently catastrophic.
- Every experiment must **run** on CPU (smaller `--limit`, same code path) — the correctness reference, and how CI stays free.
- Vendor-specific code (flash-attn, Triton, `torch.compile`) is opt-in with a fallback; it won't build on ROCm/Windows.
- `RESEARCH_DEVICE=cpu|cuda|auto` overrides detection for any run.

## Commands
```bash
# from repo root — the DX entrypoint, no venv needed
bin/check                        # canonical green check: thin shim over `uv run tools/rx.py check`
bin/check --no-tests             # same, lint only (fast)
uv run tools/rx.py help          # catalog of every command in the repo
uv run tools/rx.py status NNN    # readiness + state of one project
uv run tools/rx.py check         # KB lint (dangling links, untagged notes, run records, dependency-update config), then the test suites
uv run tools/rx.py test          # the test suites: root suite + every project with a synced .venv
uv run tools/rx.py leads         # discovery queue: what is worth more research
uv run tools/rx.py ingest        # acquire + queue documents from the corpus
uv run tools/rx.py doctor        # hardware + backend report
uv run tools/rx.py projects      # status of every project
uv run tools/rx.py new-project "slug"
uv run tools/rx.py new source|idea|synthesis|lead|article <slug>
uv run tools/rx.py new claim|experiment <slug> --project NNN

# inside a project
cd projects/001-geometric-reasoning
uv sync                          # create .venv + install
uv run geom doctor               # verify backend BEFORE anything else
uv run geom --help               # project CLI
uv run pytest -q                 # tests
uv run ruff check --fix . && uv run ruff format .
```
Discover depth via `rx.py help` — do not duplicate the catalog here. Per-project commands live in that project's `CLAUDE.md`.

## Working a project — the coordinator protocol
When told *"let's work on `projects/NNN-slug`"*, you are the coordinator. You hold the
thread and decide what is true; the hive does the work.

**1. Find out where it's at — before proposing anything.** Run `rx.py status NNN`,
`bin/check`, `rx.py leads`. Then read that project's `CLAUDE.md` — its **Start here**
section is the work queue, and its preventive rules are what an agent will otherwise violate
with no error to warn it. If `status` says the venv is not synced, that is step one and
`<cli> doctor` is step two.

**2. Dispatch the hive.** Roster and ownership: `docs/hive.md`.
- Everything independent goes out **in parallel**.
- A hard question gets **several agents at different angles**, not the same angle N times.
  Where the lenses disagree is the real uncertainty; identical agents on one base model make identical mistakes.
- Read-only agents (`falsifier`, `run-auditor`, `contamination-auditor`) run *after* work
  lands, never as a substitute for it.

**3. Loop.** Dispatch → read what came back → audit → re-dispatch. Each pass should close a
work item, kill a lead, or produce a new one. Stop when the queue is empty, the next step
is blocked on something only the user can decide, or the remainder is not worth its cost — and say which.

**4. Never delegate the judgement.** Subagents report; you decide.
- No number is believed until `run-auditor` (provenance) and `falsifier` (adversarial) have been through it.
- The verdict is written by you, in the experiment doc.
- After any experiment finishes — especially a null — run `lead-hunter`.

**5. Report honestly.** What ran, what did not, what was skipped and why.

## Writing style for notes
- Markdown. Cross-link as `[[library/ideas/slug]]`. Link liberally; a dangling link marks work to do.
- Separate what a source *said* from whether it's *true*. Different files.
- Date load-bearing claims (`As of 2026-08`).
- Write for a reader in six months who doesn't remember the conversation.
- When you disagree with a source, say so and say why.

## Docs index (load on demand)
| Read this | Before |
|---|---|
| `docs/method.md` | Writing any note, or designing an experiment |
| `docs/hive.md` | Dispatching agents — who owns which files, and why they are disjoint |
| `docs/toolchain.md` | Touching env, CUDA, native/C code, or VRAM budgets |
| `docs/starting-a-project.md` | Creating `projects/NNN-*` |
| `projects/*/CLAUDE.md` | Touching that project |

Org-wide conventions: [developerz-ai/gold-standards-in-ai](https://github.com/developerz-ai/gold-standards-in-ai).
