# 002-ftl-axiom-search

Two tracks: compute the one FTL number the reference hardware can decide, and test whether
an LLM axiom-search procedure works before pointing it at physics.

Root conventions apply — `../../CLAUDE.md`. This file holds only what is specific here.

## Start here (cold session)

Nothing is implemented. Scaffold, preregistrations, and library notes only, as of
2026-08-12. The work queue, in order — each item names the agent that owns it:

1. **`gr-toy`** — implement `qei.py` against `experiments/E003-qei-gap-1plus1d.md`. Cheapest
   real result in the project, CPU, minutes. Validate against the published analytic form
   before interpreting anything.
2. **`axiom-smith`** — implement `systems.py` + `oracle.py` against
   `experiments/E001-axiom-id-contamination-delta.md`. The contract tests come first; the
   generator is the scientific core and a bug there is silent.
3. **`lit-scout`** — prior art for E003's numerator and denominator (Alcubierre 1994;
   Ford-Roman quantum inequalities; Pfenning-Ford warp-bubble bounds) into
   `library/sources/`. E003's claim note has a placeholder citation block waiting.
4. Then `metrics.py`, then the E001 run, then `contamination-auditor` before believing any
   clean-arm number, then `falsifier` before any verdict.

Read `notes/out-of-scope-ftl.md` before writing a sentence about FTL. It was written before
any run, on purpose.

## Agents

| Agent | Owns | Use for |
|---|---|---|
| `axiom-smith` | `systems.py`, `oracle.py`, their tests | Track M's generator and solver oracle |
| `gr-toy` | `qei.py`, its tests | Track P's 1+1D energy computation |
| `contamination-auditor` | nothing (read-only) | is a Track M number search or memory? |

Repo-wide agents apply here too — `preregistrar`, `falsifier`, `run-auditor`, `lit-scout`,
`idea-extractor`, `synthesist`. Roster and dispatch patterns: `../../docs/hive.md`.

## Question

Track P: how large is the gap between the negative energy an FTL metric **requires** and the
negative energy quantum field theory **permits**, in reduced dimensionality, and which
assumption on each side carries the gap?

Track M: does a model identify the unforced axiom of a formal system when the answer is not
in its training corpus — and does fan-out beat one agent at matched budget on the falsify
step?

## Claims under test
| Claim | Falsifier | Class |
|---|---|---|
| `claim-axiom-id-is-recall` | ≥2× chance on clean systems **and** contaminated−clean delta ≤0.10 | `[open]` |
| `claim-fanout-beats-single` | Fan-out ≤ single agent at matched token budget | `[open]` |
| `claim-qei-gap-is-finite` | No finite requirement/allowance ratio under any stated assumption set | `[open]` |

## Commands
```bash
uv sync                                   # install
uv run ftl doctor                         # backend check — run first in a fresh venv
uv run ftl smoke                          # <60s end-to-end on CPU; run after every change
uv run ftl --help                         # full CLI

uv run pytest -q
uv run ruff check --fix . && uv run ruff format .
```

## Inner loop
1. `uv run ftl smoke` — cheap, CPU, catches wiring breaks.
2. Real run at small `--limit` and one seed.
3. Full run across ≥3 seeds only once the small run looks sane.

Never start with step 3.

## Layout
| Path | Holds |
|---|---|
| `src/ftlaxiom/systems.py` | Synthetic axiom-system generation. **The scientific core of Track M** — a bug here silently changes what is measured |
| `src/ftlaxiom/oracle.py` | Ground truth: independence/redundancy by SAT/SMT, never by a model |
| `src/ftlaxiom/metrics.py` | Identification accuracy, contamination delta, agreement/error-correlation |
| `src/ftlaxiom/qei.py` | Track P: warp-metric energy requirement and quantum-energy-inequality bound |
| `src/ftlaxiom/device.py` | **Only** module allowed to name a vendor backend |
| `src/ftlaxiom/provenance.py` | Run records |
| `experiments/` | Preregistrations + verdicts |
| `explore/` | Scratch scripts and probes. **Nothing here is a result** — see its README |
| `results/` | Run records (committed) |

## Project rules
- Backend selection goes through `ftlaxiom.device` — no `.cuda()`, no `"cuda"` literals elsewhere.
- Every run writes a record via `ftlaxiom.provenance` (seed · git SHA · hardware · config · per-item outputs).
- Preregister in `experiments/` before writing the code that produces the number.

## Preventive rules
- **Never let a model produce ground truth.** Redundancy and independence labels come from a
  solver (SAT/SMT/model search). A model grading a model is not a measurement, and it is the
  easiest way to manufacture a positive result here.
- **Never validate the axiom search on a historical example.** Simultaneity, the aether, the
  parallel postulate, parity, local realism — all are in every pretraining corpus, discussed
  *as* axiom-rejections. They belong in the contaminated arm as a control, never in the
  headline number. See [[library/syntheses/rediscovery-is-recall-under-contamination]].
- **Never publish or commit a generated system set.** Freshness is the contamination
  defence; a published set is a benchmark and benchmarks leak. `data/raw/` is gitignored.
- **Report the delta, not the accuracy.** A high clean-set score with an equally high
  contaminated-set score is consistent with pure recall. Only the paired difference
  discriminates.
- **Match the budget before comparing arms.** Fan-out vs. single agent is meaningless unless
  total output tokens are equal, and the budget unit is fixed in the preregistration.
- **Measure inter-agent error correlation, always.** N agreeing agents sharing one base model
  are worth far fewer than N independent votes; without this number the fan-out result is
  uninterpretable.
- **Track P computes a gap, never a possibility verdict.** An energy-condition violation
  bound says what a stated assumption set forbids. Writing "therefore warp drive is
  impossible" overstates it by exactly the assumptions listed — quote the assumptions with
  the number, every time.
- **Reduced dimensionality is a toy.** A 1+1D result does not carry to 3+1D. Say which was
  run in every sentence that reports a number.

## Known limits (state these in any verdict)
- Cannot conclude anything about whether FTL or matter teleportation is possible. See
  `notes/out-of-scope-ftl.md`.
- Track M's synthetic systems are propositional/algebraic; logical independence is a narrow
  analogue of "unforced by observation" in physics.
- Small open-weight models plus whatever API budget is available — not frontier-scale.
