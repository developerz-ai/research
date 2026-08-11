# 001-geometric-reasoning

Falsification harness for the claim that reasoning is a property of a model's internal
**geometry** rather than its **size**.

Root conventions apply — `../../CLAUDE.md`. This file holds only what is specific here.

## Question

Is there a geometric quantity of hidden states that predicts reasoning robustness **after
controlling for parameter count and training tokens**?

If yes, "geometry" is a real lever. If no, it is a redescription of data curation in
unfamiliar vocabulary. Source: [[library/sources/michels-sophontic-interview]].

## Claims under test
| Claim | Falsifier | Class |
|---|---|---|
| `claim-flip-rate-tracks-scale` | Flip rate flat or non-monotonic across a 124M→1.5B ladder | `[open]` |
| `claim-geometry-predicts-robustness` | No geometric descriptor correlates with flip rate once size is partialled out | `[open]` |

The vendor's own numbers (60×–1000× smaller beating larger) are **not** under test — they
name no baseline, no eval, and no task distribution, so they are not testable as stated.
We test the mechanism they imply, on our own models.

## Commands
```bash
uv sync --extra dev                       # install
uv run geom doctor                        # backend check — FIRST, in every fresh venv
uv run geom smoke                         # <60s end-to-end, CPU-friendly
uv run geom items --n 2                   # eyeball the items before trusting a number
uv run geom eval --model gpt2 --n 100     # flip rate for one model
uv run geom sweep --models gpt2,gpt2-medium,gpt2-large,gpt2-xl
uv run geom geometry --model gpt2         # per-layer hidden-state descriptors
uv run geom report --pattern "E001-*.json"
uv run pytest -q
uv run ruff check --fix . && uv run ruff format .
```

Backend override without editing files:
```bash
uv sync --index pytorch=https://download.pytorch.org/whl/rocm6.2   # AMD
uv sync --index pytorch=https://download.pytorch.org/whl/cpu       # CPU
RESEARCH_DEVICE=cpu uv run geom eval --model gpt2 --n 5            # force at runtime
```

## Inner loop
1. `uv run geom smoke` after every change — catches wiring breaks in under a minute.
2. `uv run geom eval --model gpt2 --n 10` — one small real run.
3. Full sweep across ≥3 seeds only once step 2 looks sane.

Never start at step 3.

## Layout
| Path | Holds |
|---|---|
| `src/geomreason/items.py` | Paired-perturbation generation. **The scientific core** — a bug here silently changes what is measured |
| `src/geomreason/metrics.py` | Flip rate, shortcut gap, stickiness, Wilson CI |
| `src/geomreason/evaluate.py` | Option log-likelihood scoring |
| `src/geomreason/geometry.py` | Participation ratio, effective rank, TwoNN, anisotropy |
| `src/geomreason/device.py` | **Only** module allowed to name a vendor backend |
| `src/geomreason/provenance.py` | Run records |
| `experiments/` | Preregistrations + verdicts |
| `results/` | Run records (committed) |

## Metric reading guide
| Quantity | Chance | Reads as |
|---|---|---|
| `flip_rate` | **0.25** | Both members of a pair correct. Headline number. |
| `canonical_accuracy` | 0.50 | What a conventional benchmark would report |
| `shortcut_gap` | 0.0 | Expected − observed flip rate. **Large positive = surface matching** |
| `stickiness` | 0.50 | Same option on both members. 1.0 = ignored the perturbation entirely |

A model at 0.5 canonical accuracy and 0.0 flip rate looks mediocre on a benchmark and is
revealed here as answering from surface form alone. That contrast is the point of the design.

## Preventive rules
- **Never publish or commit a generated item set.** Freshness is the contamination defence;
  a published pair set is a benchmark, and benchmarks leak. `data/raw/` is gitignored.
- **Both members of a pair are scored or neither counts.** `score_pairs` raises on a
  half-pair rather than averaging over it — do not "fix" that by dropping incomplete pairs.
- **Options must be identical strings across a pair.** This is the control that removes
  option-string, length, and frequency effects. `Pair.validate()` enforces it; any new
  family must pass it for thousands of seeds (`tests/test_items.py`).
- **A perturbation that leaves the answer under-determined scores a reasoning model as
  wrong.** Affirming the consequent and denying the antecedent are the easy mistakes here —
  both are deliberately excluded from `_conditional`.
- **Score by log-likelihood, never by generation.** 124M models cannot follow an output
  format; parsing their generations measures format compliance and calls it reasoning.
- **`float()` the logits before `log_softmax`.** bf16 loses enough precision to flip close
  option comparisons — the exact quantity being measured.
- **Geometry results are correlational.** A descriptor that tracks flip rate may be a
  passenger. Only intervention shows a cause; do not write a causal sentence from `geometry`.

## Known limits (state these in any verdict)
- 124M–1.5B only. A null here does not falsify the claim at 7B+.
- Our descriptors are a guess at "geometric density", which the source never defines.
- Six synthetic item families ≠ reasoning in general.
