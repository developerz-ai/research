# E001b — Flip rate across modern open-weight small models

**Created:** 2026-08-11
**Status:** **preregistered** → running → analysed → verdict
**Tests:** `claim-flip-rate-tracks-scale`, on a ladder that is actually relevant
**Follows:** [E001](E001-flip-rate-across-scale.md)

---

## Preregistration

*Written before this run. Metric and decision rule are inherited **verbatim** from E001 —
they were fixed before any number existed and are not being re-chosen now that E001's
outcome is known.*

### Why this run exists

E001 tested GPT-2 (2019) and found flip rates of 0.04–0.19 against a chance rate of 0.25.
That is a real result about GPT-2 and weak evidence about small models in general: GPT-2
predates instruction tuning, curated pretraining data, and every data-quality technique in
[[library/ideas/data-quality-over-scale]]. Concluding "small models cannot do paired
reasoning" from it would be exactly the overreach this repo is built to avoid.

This is also the honest test of the source's claim. Sophontic asserts reasoning at the 124M
scale `[source]`. Modern models *at and below* that scale are the relevant comparison, not a
seven-year-old base model.

### Hypothesis

Modern small models substantially exceed GPT-2 at matched parameter count, and at least one
model ≤1.5B exceeds chance flip rate (0.25).

Alternative being discriminated against: flip rate is a property of the paired task that
scale and modern data do not fix in this size range, and everything ≤7B sits near or below
chance.

Prior expectation, recorded now: **modern models will beat GPT-2 clearly**, because these
items are easy for anything with decent instruction-adjacent pretraining. Less confident
whether the smallest (135M) clears chance. If nothing at 7B clears it, suspect our items or
our scoring before believing the models.

### Model ladder

Two families, each varying only size within itself — the same matched-recipe logic that made
GPT-2 the right choice in E001, now applied to current models.

| Family | Models | Params |
|---|---|---|
| SmolLM2 | `HuggingFaceTB/SmolLM2-135M`, `-360M`, `-1.7B` | 135M → 1.7B |
| Qwen2.5 | `Qwen/Qwen2.5-0.5B`, `-1.5B`, `-3B`, `-7B` | 0.5B → 7B |
| *(carried from E001)* | GPT-2 family | 124M → 1.5B |

Base models only, no instruct variants — our prompt format has no chat template, and mixing
tuned and base models would confound the size comparison with a format effect.

`SmolLM2-135M` is deliberately included: it is **smaller than GPT-2** and trained on curated
data, so it directly tests data quality against size at the scale the source's claim names.

### Metric and decision rule — inherited from E001, unchanged

Flip rate (both members of a pair correct), chance 0.25, Wilson 95% CI, option
log-likelihood scoring with `sum` aggregation, 600 pairs (100 × 6 families).

| Outcome | Interpretation |
|---|---|
| Some model ≤1.5B ≥ 0.45 | Small modern models do the paired task; scale is not the binding constraint |
| Monotone rise reaching ≥0.45 only at ≥3B | Task is real but needs scale in this range |
| All models within [0.20, 0.30] | The task is not being done at any size tested |
| Everything < 0.20 including 7B | **Suspect the harness before the models** — see below |

### Pre-committed self-check

If even Qwen2.5-7B scores below 0.20, the most likely explanation is **our instrument**, not
a universal failure of language models at relational reasoning. In that case the required
next step is to inspect per-item outputs and margins before writing any verdict about
models. Committing to this now so it cannot be rationalised later.

### Confounds beyond E001's list

- **Training data is unknown and differs across families.** Qwen and SmolLM2 pretraining
  corpora are not public in detail. Size is the only controlled variable *within* a family;
  across families almost nothing is controlled. Report within-family trends primarily.
- **Contamination remains excluded by construction** — items are generated fresh from a seed
  and never published.
- **Tokenizers differ across families**, which matters most for `arithmetic`
  ([[library/ideas/tokenization-limits-reasoning]]). Report that family separately.

### Runs planned

Seed 0 across all models first; seeds 1–2 for any model that clears 0.20, to get a spread.
7B in bf16 is ~15GB and fits the 3090.

---

## Execution

```bash
uv run geom sweep --models HuggingFaceTB/SmolLM2-135M,HuggingFaceTB/SmolLM2-360M,Qwen/Qwen2.5-0.5B,HuggingFaceTB/SmolLM2-1.7B,Qwen/Qwen2.5-1.5B,Qwen/Qwen2.5-3B,Qwen/Qwen2.5-7B --n 100 --seed 0 --experiment E001b
```

**Result files:** `results/E001b-*.json`

## Results

Run 2026-08-11, RTX 3090, seed 0, 600 pairs each. Records in `results/E001b-*.json`.

| Model | Params | Flip rate | 95% CI | Canonical acc | Perturbed acc | Shortcut gap | Stickiness |
|---|---|---|---|---|---|---|---|
| SmolLM2-135M | 135M | 0.185 | [0.16, 0.22] | 0.653 | 0.508 | +0.147 | 0.792 |
| SmolLM2-360M | 362M | 0.337 | [0.30, 0.38] | 0.663 | 0.672 | +0.109 | 0.662 |
| Qwen2.5-0.5B | 494M | 0.327 | [0.29, 0.37] | 0.650 | 0.652 | +0.097 | 0.648 |
| SmolLM2-1.7B | 1.71B | 0.530 | [0.49, 0.57] | 0.745 | 0.785 | +0.055 | 0.470 |
| Qwen2.5-1.5B | 1.54B | 0.532 | [0.49, 0.57] | 0.782 | 0.747 | +0.052 | 0.465 |
| Qwen2.5-3B | 3.09B | **0.803** | [0.77, 0.83] | 0.933 | 0.867 | +0.006 | 0.193 |
| Qwen2.5-7B | 7.62B | 0.800 | [0.77, 0.83] | 0.940 | 0.860 | +0.009 | 0.200 |
| *chance* | — | *0.250* | — | *0.500* | *0.500* | *0.000* | *0.500* |

Generation comparison at matched size (E001 vs E001b):

| Params | GPT-2 (2019) | Modern (2024) | Ratio |
|---|---|---|---|
| ~124–135M | 0.048 | 0.185 | 3.9× |
| ~355–362M | 0.042 | 0.337 | 8.0× |
| ~1.5B | 0.171 | 0.532 | 3.1× |

## Analysis

**Preregistered.**

1. **E001's null was an artefact of testing a 2019 model.** At every matched size, modern
   models score 3–8× higher. The claim "small models cannot do paired-perturbation reasoning"
   was never supported by E001 — E001 supported "GPT-2 cannot", which is a much narrower
   statement and exactly why this run was required before drawing conclusions.

2. **The hypothesis is met, well below the threshold size.** SmolLM2-360M (0.337) exceeds
   chance, at ~1/4 the parameters of gpt2-xl (0.171). Qwen2.5-1.5B reaches 0.532.

3. **The shortcut signature decays monotonically with capability**, and this is the cleanest
   result in the run:

   | Model | Flip rate | Shortcut gap | Stickiness |
   |---|---|---|---|
   | gpt2 124M | 0.048 | +0.156 | 0.913 |
   | SmolLM2-135M | 0.185 | +0.147 | 0.792 |
   | SmolLM2-360M | 0.337 | +0.109 | 0.662 |
   | Qwen2.5-1.5B | 0.532 | +0.052 | 0.465 |
   | Qwen2.5-3B | 0.803 | **+0.006** | 0.193 |

   At 3B the shortcut gap is **statistically indistinguishable from zero** — errors are
   independent across the pair, which is what "not using a surface heuristic" looks like
   numerically. The metric behaves as designed across the full range from pure heuristic to
   near-independent errors.

4. ~~**The item set saturates at ~0.80.**~~ **← WRONG. Corrected 2026-08-11 by
   [E001c](E001c-current-generation.md).**

   The original claim: Qwen2.5-3B (0.803) and Qwen2.5-7B (0.800) are identical within noise
   despite 2.5× the parameters, therefore this is a ceiling of the instrument and any
   comparison at ≥3B measures our items rather than the model.

   **Qwen3.5-9B-Base scores 0.968 on the same items**, with stickiness 0.032 and a shortcut
   gap of exactly 0.000. There is no instrument ceiling at 0.80; there is at least 0.97 of
   headroom. The plateau was a property of **the Qwen2.5 family**, not of the item set.

   Kept visible rather than rewritten, because the mistake generalises: *two models agreeing
   is not a ceiling.* An apparent plateau needs a model from outside it before it can be
   attributed to the instrument. One model from a different family was enough to overturn
   this.

**Post-hoc** (not preregistered):

5. **Data quality tracks size almost exactly.** SmolLM2-1.7B (0.530) and Qwen2.5-1.5B (0.532)
   are indistinguishable despite different labs, corpora, and tokenizers. So is
   SmolLM2-360M (0.337) vs Qwen2.5-0.5B (0.327). Two independent families landing on the same
   curve suggests this task is governed by something both share — scale plus modern data —
   rather than by lab-specific technique.

6. `transitive` remained at ~0 for the smallest models with stickiness 1.000 — the recency
   heuristic identified in E001 persists across generations at small scale.

## Verdict

`claim-flip-rate-tracks-scale` → **supported on modern models**, over 135M–3B, saturating
thereafter. This **reverses the reading** of E001, which is why E001's verdict was scoped to
GPT-2 rather than to small models generally.

**What changed in my beliefs.** The preregistration predicted modern models would beat GPT-2
clearly and expressed uncertainty about whether the smallest would clear chance. Both were
right. What was *not* anticipated: how cleanly the shortcut gap would decay to zero, and
that 3B and 7B would be identical — the ceiling arrived earlier than expected.

**What this cannot conclude.**

- **Nothing about geometry.** This is an outcome-variable calibration run. It says the
  instrument works and where it saturates; it says nothing about *why* models differ.
- **Nothing about the source's claim.** A 3B model reaching 0.80 is not evidence for or
  against "engineered geometry lets 124M beat models 60× larger". It does establish that
  paired-perturbation reasoning at this difficulty is **reached by ordinary means** —
  data and scale — which raises the bar for what a geometric intervention must demonstrate:
  it must beat this curve at matched compute, not merely land on it.
- **Cross-family comparisons are uncontrolled** — different corpora, tokenizers, recipes.
  Only within-family trends are interpretable.

**Consequence for E002.** The blocker is cleared. Flip rate now has real variance
(0.185 → 0.803) across a ladder, so correlating geometric descriptors against it is
meaningful. ~~Restrict the correlation to ≤3B, above which the metric saturates.~~
**Amended:** restrict to **≤2B**, where the shortcut gap is still non-zero and the metric
discriminates — not because of a ceiling (there isn't one; see the correction above) but
because above ~2B in the current generation the gap reaches zero and stops distinguishing
models.

**Notes updated:** [[library/ideas/data-quality-over-scale]], [[library/ideas/flip-rate-evaluation]].

## Amendment log

| Date | Change | Why |
|---|---|---|
| 2026-08-11 | created | E001's GPT-2 ladder was too old to answer the question it was asked |
