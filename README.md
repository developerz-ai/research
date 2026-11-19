# developerz.ai — research

A workbench for taking interesting ideas seriously enough to try to break them.

We read a lot: books, papers, talks, interviews. Most interesting claims are stated in one
place and tested in none. This repo is where we pull those ideas apart, combine them across
sources, and build a small proof of concept to find out which parts survive contact with a
GPU.

Subjects are not restricted to AI — empirical sciences and advanced mathematics are in
scope, on one condition: **the project has to reach a falsifiable measurement on the
reference hardware.** Where the headline question cannot (most of physics), the project
writes that down before the first run and tests the reachable sub-question without implying
it settled the original. Project 002 is the worked example.

Each project ends in a written verdict. **"It did not replicate" is a publishable result
here.**

## How it is organised

| Path | What lives there |
|---|---|
| [`docs/`](docs/) | The method, the toolchain, how to start a project |
| [`templates/`](templates/) | Copy-paste starting points for notes and projects |
| [`library/`](library/) | Cross-project knowledge: sources, atomic ideas, syntheses |
| [`library/corpus/`](library/corpus/) | The raw pile of papers, theses, and books. Gitignored — [`INDEX.md`](library/corpus/INDEX.md) is what's committed |
| [`library/leads/`](library/leads/) | **Discoveries** — things worth more research, scored and gated |
| [`articles/`](articles/) | Findings worth sharing. Concise, and every sentence carries a reference |
| [`projects/`](projects/) | Self-contained PoCs, one directory each |
| [`tools/`](tools/) | Shared scripts |
| [`.claude/agents/`](.claude/agents/) | One agent per pipeline stage — see [`docs/hive.md`](docs/hive.md) |

The pipeline is deliberately linear, with one loop back:

```
acquire ─► source ─► idea ─► synthesis ─► claim ─► experiment ─► verdict
(find and   (what it  (atomic,  (combine     (falsi-  (preregistered  (honest
 download)   said,     reusable) across       fiable   seeded,          writeup)
             located)            sources)     + metric) baselined)
                           │                                  │
                           └───────────► lead ◄───────────────┘
                              (worth more research, scored)
```

Leads flow **out** of the pipeline as much as into it — a verdict, especially a null one, is
the richest source of things worth looking at next. `uv run tools/rx.py leads` shows the
queue, ranked, with gates applied: a lead that can't be killed cheaply, or where only a
positive result would be informative, is dead on arrival.

See [`docs/method.md`](docs/method.md) for what each step demands, and
[`library/leads/README.md`](library/leads/README.md) for the scoring gates.

## Projects

| # | Project | Question | Status |
|---|---|---|---|
| 001 | [geometric-reasoning](projects/001-geometric-reasoning/) | Is reasoning a property of a model's internal geometry rather than its size? Can a small model be *engineered* into robust reasoning? | 🟡 active |
| 002 | [ftl-axiom-search](projects/002-ftl-axiom-search/) | What would have to be discovered for FTL travel or teleportation — and does an LLM axiom search find unforced assumptions, or only recall the ones history already rejected? | 🟡 scaffold |

## Hardware

Everything here is designed to run on one workstation: **RTX 3090 (24 GB)**, Ryzen 7 5700X3D
(8c/16t), 64 GB RAM. This is a constraint we like — an idea that only works at datacenter
scale is an idea we cannot check, and a good chunk of this repo exists to ask whether that
scale was ever necessary.

## Setup

```powershell
# one-time: uv manages Python and every project venv
irm https://astral.sh/uv/install.ps1 | iex

uv run tools/rx.py help       # catalog of every command in the repo
uv run tools/rx.py doctor     # hardware + backend report
uv run tools/rx.py test       # the test suites: root suite + every project with a synced .venv
uv run tools/rx.py check      # the knowledge-base lint, then the test suites
python bin/check              # shim over the same check (POSIX: ./bin/check)

cd projects/001-geometric-reasoning
uv sync                       # creates .venv, installs deps
uv run geom doctor            # verifies the backend, prints hardware
```

`rx check` runs the test suites as well as the knowledge-base lint — a red suite is a red check. `bin/check` is a thin shim over that same command (`./bin/check` on POSIX, `python bin/check` on Windows), so one command proves the tree end to end.

Full details in [`docs/toolchain.md`](docs/toolchain.md).

## Working with agents

This is an AI-first factory: agents do the acquiring, reading, decomposing, building, and
attacking. The pipeline stages map one-to-one onto subagents, and each owns a **disjoint set
of files** — one writer per path — so several run at once without coordinating.

`lit-scout` searches for material and downloads what it can legally get into
`library/corpus/`; `corpus-reader` works through the queue one document at a time and writes
source notes with page locators; `idea-extractor` and `synthesist` distil those into ideas
and syntheses; `decomposer` cuts a big question into attackable sub-problems; `preregistrar`
fixes the metric and threshold before any code exists; and `falsifier` and `run-auditor`
write nothing at all — they report, and whoever owns the file decides what to change.
Projects add their own agents for their own modules.

For a hard question, spawn agents with **different lenses** rather than the same lens N
times. Where the lenses disagree is where the real uncertainty is — and identical agents on
one base model make identical mistakes.

Roster and dispatch patterns: [`docs/hive.md`](docs/hive.md).

## Ground rules

- Claims are tagged by evidence class (`[source]`, `[lit]`, `[ours]`, `[open]`) — a company's
  claim about its own product never silently becomes a fact.
- Falsification conditions are written before the code that could satisfy them.
- Every number is backed by a seeded run in `results/` with a git SHA.
- Baselines are matched on compute budget, not on convenience.

More in [`CLAUDE.md`](CLAUDE.md).

License: MIT, see [LICENSE](LICENSE) and [NOTICE](NOTICE).
