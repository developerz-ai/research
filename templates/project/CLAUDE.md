# {{NUMBER}}-{{SLUG}}

<one line: what this project is trying to find out>

Root conventions apply — see `../../CLAUDE.md`. This file holds only what is specific here.

## Question

The single sentence this project exists to answer.

## Claims under test
| Claim | Falsifier | Class |
|---|---|---|
| `claim-...` | | `[open]` |

## Agents

Project agents live in `.claude/agents/` here and own **disjoint files** — one writer per
path, so they can run in parallel with no coordination.

| Agent | Owns | Use for |
|---|---|---|
| | | |

Repo-wide agents apply too: `lit-scout`, `idea-extractor`, `synthesist`, `preregistrar`,
`falsifier`, `run-auditor`. Roster and dispatch patterns: `../../docs/hive.md`.

## Commands
```bash
uv sync                                   # install
uv run {{SLUG}} doctor                    # backend check — run first in a fresh venv
uv run {{SLUG}} smoke                     # <60s end-to-end on CPU; run after every change
uv run {{SLUG}} --help                    # full CLI

uv run pytest -q                          # tests
uv run ruff check --fix . && uv run ruff format .
```

## Inner loop
1. `uv run {{SLUG}} smoke` — cheap, CPU, catches wiring breaks.
2. Real run at small `--limit` and one seed.
3. Full run across ≥3 seeds only once the small run looks sane.

Never start with step 3. A full sweep that dies at 80% teaches nothing and costs hours.

## Layout
| Path | Holds |
|---|---|
| `src/{{PKG}}/` | Library code + CLI |
| `experiments/` | Preregistrations and verdicts, `E001-*.md` |
| `explore/` | Scratch scripts and probes. **Nothing here is a result** |
| `notes/` | Claims, literature review, working notes |
| `results/` | Run records (JSON, committed) |
| `data/` | Inputs. `data/raw/` and `data/cache/` are gitignored |
| `tests/` | Fast tests; no GPU required |

## Project rules
- Backend selection goes through `{{PKG}}.device` — no `.cuda()`, no `"cuda"` literals elsewhere.
- Every run writes a record via `{{PKG}}.provenance` (seed · git SHA · hardware · config · per-item outputs).
- Preregister in `experiments/` before writing the code that produces the number.

## Preventive rules
- (add the ones specific to this project — the ones an agent would violate *while writing new code*, with no error to warn it)
