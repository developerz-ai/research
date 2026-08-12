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
| [`projects/`](projects/) | Self-contained PoCs, one directory each |
| [`tools/`](tools/) | Shared scripts |
| [`.claude/agents/`](.claude/agents/) | One agent per pipeline stage — see [`docs/hive.md`](docs/hive.md) |

The pipeline is deliberately linear:

```
source  ──►  idea  ──►  synthesis  ──►  claim  ──►  experiment  ──►  verdict
(what was    (atomic,   (combine      (falsifiable  (preregistered,  (honest
 said)        reusable)  across        + a metric)   seeded, with a    writeup)
                         sources)                    baseline)
```

See [`docs/method.md`](docs/method.md) for what each step demands.

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

cd projects/001-geometric-reasoning
uv sync                       # creates .venv, installs deps
uv run geom doctor            # verifies the backend, prints hardware
```

Full details in [`docs/toolchain.md`](docs/toolchain.md).

## Working with agents

The pipeline stages map one-to-one onto subagents, and each owns a **disjoint set of
files** — one writer per path — so several can run at once without coordinating.
`lit-scout` writes source notes, `idea-extractor` writes ideas, `synthesist` writes
syntheses, `preregistrar` writes claims and experiment docs, and `falsifier` and
`run-auditor` write nothing at all: they report, and whoever owns the file decides what to
change. Projects add their own agents for their own modules.

Roster and dispatch patterns: [`docs/hive.md`](docs/hive.md).

## Ground rules

- Claims are tagged by evidence class (`[source]`, `[lit]`, `[ours]`, `[open]`) — a company's
  claim about its own product never silently becomes a fact.
- Falsification conditions are written before the code that could satisfy them.
- Every number is backed by a seeded run in `results/` with a git SHA.
- Baselines are matched on compute budget, not on convenience.

More in [`CLAUDE.md`](CLAUDE.md).
