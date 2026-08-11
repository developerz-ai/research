# E001c — Flip rate on the current generation (2026-08)

**Created:** 2026-08-11
**Status:** **preregistered** → running → analysed → verdict
**Follows:** [E001b](E001b-modern-small-models.md)

---

## Preregistration

*Metric and decision rule inherited verbatim from E001. Not re-chosen.*

### Why this run exists

E001b used SmolLM2 and Qwen2.5 — good models, but as of 2026-08 they are **a generation
behind**. Model IDs were confirmed against the HuggingFace API rather than from memory:
Qwen is on **Qwen3.6/Qwen3.5**, HuggingFaceTB has shipped **SmolLM3** and **nanowhale-100m**,
Google is on **Gemma 4**.

E001b already showed the effect it was designed to find (0.048 → 0.803 across generations
and scale). This run asks the sharper question that E001b's result makes interesting:

**Has the small end caught up?** Sophontic's claim is specifically about ~124M-scale models
`[source]`. `nanowhale-100m-base` is a **2026 model at 100M parameters** — smaller than
GPT-2, current training. If small-scale reasoning is achievable without any geometric
intervention, this is where it shows.

### Hypothesis

1. Current-generation models beat their previous-generation counterparts at matched size.
2. `nanowhale-100m` (100M, 2026) substantially beats `gpt2` (124M, 2019), and beats or
   matches `SmolLM2-135M` (2024).
3. At least one model **≤2B** exceeds **0.80** flip rate — the level Qwen2.5-3B reached.

Recorded prior: confident on (1) and (2); genuinely unsure on (3). If a ≤2B model hits 0.80,
that is a meaningful data point for "reasoning does not require scale" — reached entirely
through data and training quality, with no geometric engineering involved.

### Model ladder

Base models where available, confirmed present on the Hub.

| Model | Params | Generation |
|---|---|---|
| `HuggingFaceTB/nanowhale-100m-base` | 100M | 2026 |
| `Qwen/Qwen3-0.6B-Base` | 0.6B | Qwen3 |
| `Qwen/Qwen3-1.7B-Base` | 1.7B | Qwen3 |
| `Qwen/Qwen3.5-2B-Base` | 2B | **Qwen3.5** |
| `HuggingFaceTB/SmolLM3-3B-Base` | 3B | SmolLM3 |
| `Qwen/Qwen3.5-9B-Base` | 9B | **Qwen3.5** |

9B in bf16 is ~18GB — fits the 3090's 24GB, but it is the ceiling. If it OOMs, that is a
hardware limit to report, not a result.

Gemma 4 is excluded: gated behind a licence acceptance, so it cannot be part of a
reproducible run without credentials.

### Decision rule — inherited, unchanged

Flip rate, chance 0.25, Wilson 95% CI, 600 pairs (100 × 6 families), `sum` aggregation.

| Outcome | Interpretation |
|---|---|
| A ≤2B model ≥ 0.80 | Small-scale reasoning achieved by data/training alone — no geometry needed |
| Monotone rise, ≥0.80 only at ≥3B | Capability tracks scale in this range |
| `nanowhale-100m` ≈ `gpt2` | Generation is not the explanation; something else drove E001b |

### Confounds

Everything from E001b, plus:

- **Qwen3/Qwen3.5 are hybrid-reasoning models.** Base variants should not emit thinking
  traces, and our scoring never generates — but base-variant availability and behaviour must
  be verified per model rather than assumed.
- **Cross-family comparison remains uncontrolled.** Training data and tokenizers differ.
  Within-family trends (Qwen3 0.6B → 1.7B) are the interpretable ones.
- **`arithmetic` still carries a tokenizer confound** — report separately
  ([[library/ideas/tokenization-limits-reasoning]]).

---

## Execution

```bash
uv run geom sweep --models HuggingFaceTB/nanowhale-100m-base,Qwen/Qwen3-0.6B-Base,Qwen/Qwen3-1.7B-Base,Qwen/Qwen3.5-2B-Base,HuggingFaceTB/SmolLM3-3B-Base,Qwen/Qwen3.5-9B-Base --n 100 --seed 0 --experiment E001c
```

## Results

Run 2026-08-11, RTX 3090, seed 0, 600 pairs each. Records in `results/E001c-*.json`.

| Model | Params | Flip rate | 95% CI | Canonical acc | Perturbed acc | Shortcut gap | Stickiness |
|---|---|---|---|---|---|---|---|
| `nanowhale-100m-base` | 110M | **excluded** | — | — | — | — | — |
| Qwen3-0.6B-Base | 596M | 0.483 | [0.44, 0.52] | 0.783 | 0.695 | +0.061 | 0.512 |
| Qwen3-1.7B-Base | 1.72B | 0.498 | [0.46, 0.54] | 0.837 | 0.658 | +0.052 | 0.498 |
| Qwen3.5-2B-Base | 1.88B | 0.772 | [0.74, 0.80] | 0.907 | 0.847 | −0.004 | 0.210 |
| SmolLM3-3B-Base | 3.08B | 0.562 | [0.52, 0.60] | 0.768 | 0.735 | +0.003 | 0.380 |
| **Qwen3.5-9B-Base** | 8.95B | **0.968** | [0.95, 0.98] | 0.985 | 0.983 | +0.000 | 0.032 |

**`nanowhale-100m-base` is excluded, not zero.** It is a `DeepseekV4ForCausalLM` whose
`shared_experts` and `hc_head` tensors were missing from our transformers version and were
**randomly initialised**. It loaded, ran, and returned 0.013 — a number that reads like
"a 100M model cannot reason" and actually measures a partly-random network. Quarantined in
`results/superseded/` with the details; `load_model` now refuses to score any model with
missing keys.

Generational comparison at matched size:

| Params | Qwen2.5 (E001b) | Qwen3 / Qwen3.5 (E001c) | Change |
|---|---|---|---|
| ~0.5–0.6B | 0.327 | 0.483 | **+48%** |
| ~1.5–1.7B | 0.532 | 0.498 (Qwen3) · **0.772** (Qwen3.5-2B) | −6% · **+45%** |
| ~3B | 0.803 | 0.562 (SmolLM3) | — different family |
| ~8–9B | 0.800 (Qwen2.5-7B) | **0.968** | **+21%** |

## Analysis

**Preregistered.**

1. **Hypothesis 1 (generational gain) — supported, with one exception.** Qwen3-0.6B beats
   Qwen2.5-0.5B by 48%. Qwen3.5-2B beats Qwen2.5-1.5B by 45%. Qwen3.5-9B beats Qwen2.5-7B
   by 21%. The exception is **Qwen3-1.7B (0.498) ≈ Qwen3-0.6B (0.483)** — nearly flat across
   a 2.9× parameter increase within the same generation.

2. **Hypothesis 2 (nanowhale vs gpt2) — untestable.** The model could not be loaded
   correctly. Reporting this as a failure to test, not as a result.

3. **Hypothesis 3 (a ≤2B model reaching 0.80) — narrowly missed, and close enough to matter.**
   **Qwen3.5-2B-Base scores 0.772** [0.74, 0.80] with a shortcut gap of **−0.004**. The CI
   touches 0.80. This is a 1.88B model performing at the level Qwen2.5 needed 3–7B to reach,
   with errors independent across the pair.

**The correction to E001b.**

E001b concluded that the item set "saturates at ~0.80" and called this "a ceiling of the
instrument, not a property of models", because Qwen2.5-3B (0.803) and Qwen2.5-7B (0.800)
were identical.

**That was wrong, and E001c falsifies it.** Qwen3.5-9B reaches **0.968** on the same items,
with stickiness 0.032 and a shortcut gap of exactly 0.000. The instrument has at least
0.97 of headroom. The 3B/7B plateau was a property of **the Qwen2.5 family**, not of our
items.

The error is instructive and worth keeping visible: two models agreeing at 0.80 looked like
a ceiling, and one model from a different family was enough to disprove it. *Two points do
not establish a ceiling* — a conclusion drawn from an apparent plateau needs a model from
outside the plateau before it means anything. E001b's writeup has been corrected in place
with a pointer here.

**Post-hoc** (not preregistered):

4. **Generation dominates size in this range.** Qwen3.5-2B (1.88B, 0.772) beats
   SmolLM3-3B (3.08B, 0.562) by a wide margin despite being 40% smaller. Across all runs,
   knowing a model's *training recipe and vintage* predicts flip rate better than knowing
   its parameter count — which is [[library/ideas/data-quality-over-scale]] stated in our
   own numbers, spanning 2019→2026 and 124M→9B.

5. **The shortcut gap reaches zero and stays there.** Qwen3.5-2B (−0.004), SmolLM3-3B
   (+0.003), Qwen3.5-9B (+0.000). Above ~2B in the current generation, errors on the two
   members of a pair are statistically independent — no surface-matching signal remains to
   detect. The metric has done its job and is no longer discriminative up there.

## Verdict

**Current-generation small models do the paired-perturbation task, and the small end has
moved a long way.** A 1.88B base model reaches 0.772 with zero shortcut gap; a 9B base model
reaches 0.968.

**Bearing on the source's claim.** Sophontic asserts engineered geometry lets ~124M models
outperform models 60×–1000× larger `[source]`. Our results neither support nor refute that —
we tested no geometric intervention. What they do establish is **the bar such a claim must
clear**: reasoning robustness at small scale is being delivered *right now* by ordinary data
and training improvements, with no geometric engineering involved, and the rate of
improvement per generation is steep. A geometric method must beat this moving curve at
matched compute, not merely land on it.

**What this cannot conclude.**

- Nothing about geometry. No intervention was tested.
- Nothing at ~100M in the current generation — the one model in that class failed to load.
  **This is the gap that matters most** for the source's specific claim, and it is
  unresolved.
- Cross-family comparisons are uncontrolled (different corpora, tokenizers, recipes).
  Only within-family trends are interpretable.
- Single seed. E001 showed seed-to-seed spread ≤0.06, so the large gaps here are safe, but
  the Qwen3-0.6B vs Qwen3-1.7B near-tie (0.483 vs 0.498) is **not** resolvable at one seed.

**Consequence for E002.** Flip rate now spans 0.048 → 0.968 across 12 models. That is ample
variance for correlating geometric descriptors against, and the ladder should be restricted
to **≤2B**, where the metric still discriminates.

## Amendment log

| Date | Change | Why |
|---|---|---|
| 2026-08-11 | created | E001b's ladder was a generation behind; model IDs confirmed via the HF API |
| 2026-08-11 | `load_model` casts device+dtype together | `dtype=` at load time left a mixed-precision checkpoint partly fp32; nanowhale failed at the first matmul |
| 2026-08-11 | `load_model` refuses checkpoints with missing keys | nanowhale loaded with randomly-initialised experts and scored 0.013. A silently-random model must never produce a number. |
| 2026-08-11 | E001b's "instrument saturates at 0.80" corrected | Falsified by Qwen3.5-9B at 0.968 on the same items |

## Amendment log

| Date | Change | Why |
|---|---|---|
| 2026-08-11 | created | E001b's ladder was a generation behind; model IDs confirmed via the HF API |
