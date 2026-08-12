# research

Research monorepo for developerz.ai. A factory for research topics: many independent
projects, one fixed pipeline. Each takes an idea — from a book, paper, or talk — and finds
out whether it's **true**, via a runnable PoC plus documentation.

Subjects are not restricted to AI. Empirical sciences and advanced mathematics are in
scope, on one condition: the project must reach a **falsifiable measurement on the reference
hardware**. Where the headline question cannot (most of physics), the project says so
explicitly in writing *before* the first run, and tests the reachable sub-question without
implying it settled the original — see `projects/002-ftl-axiom-search/notes/out-of-scope-ftl.md`
for the worked example.

Output = **documented verdicts**, not products. A cleanly-measured negative result is a success. Never soften one.

## Response Rules
- Execute. No preamble. No restating the task.
- Lead with the finding. Reasoning after, only if non-obvious.
- Parallel tool calls when independent.
- Read before speculating. Measure before claiming.
- Disagree when the user is wrong. State the correction.
- Terse. Fragments OK. Paths/commands/numbers stay exact.

## Research Rules
- **Tag every factual statement** with an evidence class (below). Untagged prose = opinion.
- **Falsifier before code.** Write what would kill the claim before writing what might confirm it.
- **Preregister.** Hypothesis + metric + threshold land in the experiment doc before the number exists.
- **Baseline or it didn't happen.** Matched on compute budget — say which (params · tokens · wall-clock).
- **Multiple seeds.** One seed is an anecdote. ≥3 seeds + spread is a result.
- **No number without a run record.** `results/*.json` carries seed, git SHA, hardware, full config, per-item outputs.
- **Scope the finding.** State what the experiment cannot conclude.

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
| `docs/` | Method, toolchain, project kickoff. Load on demand. |
| `templates/` | Copy when starting a source/idea/claim/experiment/project. |
| `library/corpus/` | The raw pile — papers, theses, books. **Gitignored**; `INDEX.md` is the committed record. |
| `library/sources/` | One file per book/paper/talk consumed. What was said, neutrally, with locators. |
| `library/ideas/` | One file per atomic idea. Reusable across projects. |
| `library/syntheses/` | Combinations across sources. The point of the repo. |
| `library/leads/` | **Discoveries** — things worth more research, scored and gated. What the repo produces of its own. |
| `projects/NNN-slug/` | Self-contained PoC. Own venv, own `CLAUDE.md`, own agents. |
| `tools/` | Shared scripts. |
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
| Python | 3.12, managed by **uv** only |
| DL | PyTorch. Wheel index pinned per backend (`cu126` / `rocm` / `cpu`) — never default PyPI |
| Platforms | **Windows + Linux. macOS is not a target.** |
| Accelerators | NVIDIA (CUDA) · AMD (ROCm, Linux) · CPU fallback always works |
| Reference box | RTX 3090 24GB · Ryzen 7 5700X3D 8c/16t · 64GB RAM |

### Portability policy
Never branch on vendor in experiment code. Call `pick_device()` / `autocast_dtype()` from the project's `device` module and let it resolve the backend.

| Rule | Why |
|---|---|
| No `.cuda()`, no `device="cuda"` literals | Breaks CPU + ROCm. Use `pick_device()`. |
| No `torch.cuda.*` for capability checks | True on ROCm too, and misleading. Use the helpers. |
| `bf16` only when the device reports support | Ampere+ and MI200+ yes; older cards and most CPUs no — silently catastrophic elsewhere. |
| Every experiment must **run** on CPU | Smaller `--limit`, same code path. This is the correctness reference and how CI stays free. |
| Anything vendor-specific (flash-attn, Triton, `torch.compile`) is **opt-in with a fallback** | It won't build on ROCm/Windows. Guard it, don't require it. |
| `pathlib.Path` only | Windows *and* Linux. |

`RESEARCH_DEVICE=cpu|cuda|auto` overrides detection for any run.

## Working a project — the coordinator protocol

When told *"let's work on `projects/NNN-slug`"*, you are the coordinator. You hold the
thread and decide what is true; the hive does the work.

**1. Find out where it's at — before proposing anything.**
```bash
uv run tools/rx.py status NNN     # readiness, experiment states, orphan results, claims
uv run tools/rx.py check          # dangling links, untagged notes, incomplete run records
uv run tools/rx.py leads          # the discovery queue, ranked
```
Then read that project's `CLAUDE.md` — its **Start here** section is the work queue, and its
preventive rules are the things an agent will otherwise violate with no error to warn it.
If `status` says the venv is not synced, that is step one and `<cli> doctor` is step two: a
CPU-only torch wheel is a silent failure, not an error.

**2. Dispatch the hive.** Roster and ownership: `docs/hive.md`.
- Everything independent goes out **in parallel, on disjoint files**. One writer per path is
  what makes that safe — no locking, no coordination.
- A hard question gets **several agents at different angles**, not the same angle N times.
  Where the lenses disagree is where the real uncertainty is; identical agents on one base
  model make identical mistakes.
- Read-only agents (`falsifier`, `run-auditor`, `contamination-auditor`) run *after* work
  lands, never as a substitute for it.

**3. Loop.** Dispatch → read what came back → audit → re-dispatch. Each pass should either
close a work item, kill a lead, or produce a new one. Stop when the queue is empty, the next
step is blocked on something only the user can decide, or the remaining work is not worth
its cost — and say which.

**4. Never delegate the judgement.** Subagents report; you decide. Specifically:
- No number is believed until `run-auditor` (provenance) and `falsifier` (adversarial) have
  been through it.
- The verdict is written by you, in the experiment doc, with what it *cannot* conclude.
- After any experiment finishes — especially a null — run `lead-hunter`. A null is where the
  assumptions become visible, and it is the repo's richest source of new work.

**5. Report honestly.** What ran, what did not, what was skipped and why. A cleanly-measured
negative is a success. Never soften one.

## Commands
```bash
# from repo root — the DX entrypoint, no venv needed
uv run tools/rx.py help          # catalog of every command in the repo
uv run tools/rx.py status NNN    # readiness + state of one project
uv run tools/rx.py leads         # discovery queue: what is worth more research
uv run tools/rx.py doctor        # hardware + backend report
uv run tools/rx.py new-project "slug"
uv run tools/rx.py new source|idea|claim|experiment <slug>
uv run tools/rx.py projects      # status of every project

# inside a project
cd projects/001-geometric-reasoning
uv sync                          # create .venv + install
uv run geom doctor               # verify backend BEFORE anything else
uv run geom --help               # project CLI
uv run pytest -q                 # tests
uv run ruff check --fix . && uv run ruff format .
```
Discover depth via `rx.py help` — do not memorise or duplicate the catalog here. Per-project commands live in that project's `CLAUDE.md`.

## Hard boundaries
- Never `pip install` into system Python. uv only.
- Never commit weights, checkpoints, or raw corpora. `results/` JSON + plots **are** committed.
- Never let a project import another project. Promote shared code to `tools/` or copy it.
- Never report an aggregate without per-item data behind it — it can't be re-analysed.
- Never use git worktrees. Work in this checkout. Parallel agents get disjoint files.

## Preventive rules (these bite before any symptom appears)
- **A CPU-only torch wheel is a silent failure, not an error.** The default PyPI wheel has no GPU; everything still "works", just 50× slower, and you won't notice until the run is done. Guard: `uv run geom doctor` in every fresh venv — it fails loudly when the wheel and the hardware disagree.
- **`torch.cuda.is_available()` is `True` on AMD/ROCm.** It is not a vendor test. Branching on it puts CUDA-only code on an AMD card. Guard: `device.py` helpers only; `ruff` forbids `.cuda()` and `"cuda"` literals outside that module.
- **Vendor benchmark numbers are not baselines.** "60× smaller model beats X" compares against an unnamed X on an unnamed eval. Reproduce the *eval*, then compare on your own matched pair, or the number means nothing.
- **A metric chosen after seeing the data is not a measurement.** Threshold + item count go in the experiment doc first. Amending is allowed — say that you amended and why.
- **Paths: `pathlib.Path` only.** This repo runs on Windows *and* Linux; a hardcoded `/` breaks one of them and nobody tests the other.
- **Seeds live in the config, not the code.** A seed baked into a source file cannot be swept, and a sweep is the only way to know if a result is real.
- **Contamination check before any benchmark claim.** If the eval set predates the model's cutoff, assume it's in the training data until shown otherwise.

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

## What NOT to do here
- **No products.** Something worth shipping graduates to its own repo; this one keeps the verdict.
- **No benchmark leaderboard chasing.** We test mechanisms, not scores.
- **No unfalsifiable projects.** Philosophy is welcome as *motivation*; it never substitutes for a metric. If a claim can't be reached from a 3090, say so explicitly in the verdict rather than quietly testing something easier and implying it settled the question.
