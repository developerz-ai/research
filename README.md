# developerz.ai — research

A workbench for taking interesting ideas seriously enough to try to break them.

We read a lot: books, papers, talks, interviews. Most interesting claims in AI are stated
in one place and tested in none. This repo is where we pull those ideas apart, combine
them across sources, and build a small proof of concept to find out which parts survive
contact with a GPU.

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

## Hardware

Everything here is designed to run on one workstation: **RTX 3090 (24 GB)**, Ryzen 7 5700X3D
(8c/16t), 64 GB RAM. This is a constraint we like — an idea that only works at datacenter
scale is an idea we cannot check, and a good chunk of this repo exists to ask whether that
scale was ever necessary.

## Setup

```powershell
# one-time: uv manages Python and every project venv
irm https://astral.sh/uv/install.ps1 | iex

cd projects/001-geometric-reasoning
uv sync                       # creates .venv, installs deps
uv run python -m geomreason.doctor   # verifies CUDA, prints hardware
```

Full details in [`docs/toolchain.md`](docs/toolchain.md).

## Ground rules

- Claims are tagged by evidence class (`[source]`, `[lit]`, `[ours]`, `[open]`) — a company's
  claim about its own product never silently becomes a fact.
- Falsification conditions are written before the code that could satisfy them.
- Every number is backed by a seeded run in `results/` with a git SHA.
- Baselines are matched on compute budget, not on convenience.

More in [`CLAUDE.md`](CLAUDE.md).
