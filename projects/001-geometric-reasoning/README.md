# 001 — Geometric reasoning

**Question:** Is there a geometric quantity of hidden states that predicts reasoning robustness after controlling for parameter count and training tokens?
**Status:** 🟢 primary question answered — 16 models measured (2019→2026, 124M→9B), E002 came back confounded/null
**Started:** 2026-08-11

## Why this is worth testing

Julian D. Michels (Sophontic AI) argues that reasoning is a property of a model's internal
geometry rather than its size, and that engineering that geometry yields reasoning
outperforming models 60×–1000× larger `[source]`
([[library/sources/michels-sophontic-interview]]).

Those performance numbers are not testable as stated — no named baseline, no eval, no task
distribution, no paper, no weights. Under this repo's rules they stay `[source]` and we do
not attempt to reproduce them.

What *is* testable is the mechanism the argument depends on, and it is testable cheaply.
Two things make this project worth running:

1. **The rival explanation is strong and boring.** Curated data and curriculum ordering
   already produce small models that beat much larger ones, at exactly this scale, with no
   geometric story ([[library/ideas/data-quality-over-scale]]). Nobody has published the
   ablation separating the two. The interesting question is whether geometry adds anything
   once data quality is controlled for — see
   [[library/syntheses/geometry-vs-scale-is-empirical]].
2. **Their evaluation method is genuinely good and freely borrowable.** Flip rate on paired
   perturbations is a rebranding of contrast sets `[lit]`, it is contamination-resistant,
   and it can be pointed at any model today ([[library/ideas/flip-rate-evaluation]]).
   We adopt the instrument regardless of what happens to the claims.

## Claims under test

| Claim | Falsifier | Class | Experiment |
|---|---|---|---|
| Flip rate rises monotonically with scale over 124M→1.5B | Flat or non-monotonic across the ladder | `[open]` | E001 |
| Some geometric descriptor predicts flip rate after partialling out size | No descriptor correlates once size is controlled | `[open]` | E002 |

## Experiments

| ID | Question | Status | Verdict |
|---|---|---|---|
| [E001](experiments/E001-flip-rate-across-scale.md) | Flip rate across GPT-2, 124M→1.5B | **analysed** | Nothing reaches chance — but this turned out to be about GPT-2, not about small models |
| [E001b](experiments/E001b-modern-small-models.md) | Same, on 2024 models (SmolLM2, Qwen2.5) | **analysed** | 3–8× higher at matched size; reverses E001's reading |
| [E001c](experiments/E001c-current-generation.md) | Same, on 2026 models (Qwen3/3.5, SmolLM3) | **analysed** | 1.88B reaches 0.772 with zero shortcut gap; 9B reaches 0.968 |
| [E002](experiments/E002-geometry-vs-robustness.md) | Does any hidden-state geometric descriptor track flip rate independently of size? | **analysed** | **Confounded → no.** Best surviving \|partial ρ\| = 0.006 (n=12, GPT-2 family removed) |

None required training; all four ran in an afternoon.

## The headline

**Geometry does not predict reasoning robustness once you control for size.**

Across **n=16** — every measured model, no exclusions — every geometric descriptor
correlates strongly with flip rate at first glance (ρ up to +0.850). Essentially all of it is
size. Control for parameter count and drop the GPT-2 family (**n=12**, the same 16 minus the
four GPT-2 models), and the best surviving partial correlation is **0.006** — against a
falsification threshold of 0.3 fixed before the code was written.

The apparent signal was four 2019 models sitting in a corner: old models have both worse
geometry and worse reasoning, and nothing connects the two except vintage.

This does **not** refute the geometry claim — we tested no intervention, and our descriptors
are a guess at a term the source never defines. It does mean the cheap screen came back
empty, so the expensive matched-training experiment is not justified on this evidence.

## Findings so far

**16 models, 2019 → 2026, 124M → 9B, 600 fresh pairs each** `[ours]`

| Model | Params | Year | Flip rate | Shortcut gap | Stickiness |
|---|---|---|---|---|---|
| gpt2 | 124M | 2019 | 0.048 | +0.156 | 0.913 |
| gpt2-medium | 355M | 2019 | 0.042 | +0.161 | 0.922 |
| gpt2-large | 774M | 2019 | 0.185 | +0.127 | 0.772 |
| gpt2-xl | 1.5B | 2019 | 0.171 | +0.116 | 0.793 |
| SmolLM2-135M | 135M | 2024 | 0.185 | +0.147 | 0.792 |
| SmolLM2-360M | 362M | 2024 | 0.337 | +0.109 | 0.662 |
| Qwen2.5-0.5B | 494M | 2024 | 0.327 | +0.097 | 0.648 |
| Qwen2.5-1.5B | 1.54B | 2024 | 0.532 | +0.052 | 0.465 |
| SmolLM2-1.7B | 1.71B | 2024 | 0.530 | +0.055 | 0.470 |
| Qwen2.5-3B | 3.09B | 2024 | 0.803 | +0.006 | 0.193 |
| Qwen2.5-7B | 7.62B | 2024 | 0.800 | +0.009 | 0.200 |
| Qwen3-0.6B | 596M | 2025 | 0.483 | +0.061 | 0.512 |
| Qwen3-1.7B | 1.72B | 2025 | 0.498 | +0.052 | 0.498 |
| **Qwen3.5-2B** | 1.88B | 2026 | **0.772** | −0.004 | 0.210 |
| SmolLM3-3B | 3.08B | 2025 | 0.562 | +0.003 | 0.380 |
| **Qwen3.5-9B** | 8.95B | 2026 | **0.968** | +0.000 | 0.032 |
| *chance* | — | — | *0.250* | *0.000* | *0.500* |

1. **Vintage beats size.** At matched parameters, 2024 models score 3–8× GPT-2, and Qwen3.5-2B
   (1.88B) beats SmolLM3-3B (3.08B) by 0.21 while being 40% smaller. Across the whole table,
   knowing a model's training recipe predicts flip rate better than knowing its size — which
   is [[library/ideas/data-quality-over-scale]] restated in our own measurements.
2. **The shortcut signature decays to exactly zero.** From +0.156 (gpt2) to 0.000
   (Qwen3.5-9B). At the top, errors on the two members of a pair are statistically
   independent — no surface-matching signal left to detect.
3. **Canonical accuracy is not diagnostic.** GPT-2 scores 0.69–0.76 on canonical items alone
   while managing 0.04–0.19 paired. A conventional benchmark would call those models
   competent. **That contrast is the most transferable result here.**
4. **Two of our own errors, both caught by the harness:**
   - An item family solvable by "answer the last-named entity" at flip rate 1.0. Now guarded
     by `uv run geom baselines` on every run.
   - A model that loaded with **randomly-initialised weights** and returned 0.013 — which
     would have read as "a 100M model cannot reason". `load_model` now refuses any checkpoint
     with missing keys.
   Both discarded runs are kept in `results/superseded/` with explanations.
5. **And one wrong conclusion, corrected:** E001b called 0.80 an instrument ceiling based on
   Qwen2.5-3B and -7B agreeing. Qwen3.5-9B then scored 0.968 on the same items. Two models
   agreeing is not a ceiling.

**Consequence:** E002 is unblocked — flip rate now spans 0.048 → 0.968, ample variance to
correlate geometric descriptors against. Restrict to **≤2B**, where the shortcut gap is
still non-zero and the metric discriminates. **Not applied:** E002 ran the full **16-model**
ladder, including Qwen2.5-7B and Qwen3.5-9B — see
[E002](experiments/E002-geometry-vs-robustness.md). Remaining gaps:

- **~100M current generation is still unmeasured.** `nanowhale-100m-base` failed to load
  correctly: it was **excluded before it was ever a valid measurement** (partly
  randomly-initialised weights, 0.013, quarantined in `results/superseded/`), so it is not
  one of the 16 models in the table above — and it is the single most relevant data point for
  the source's ~124M claim. Needs a transformers version matching `DeepseekV4ForCausalLM`.
- **Seeds.** E001b/E001c are single-seed. The large gaps are safe (E001 spread was ≤0.06) but
  the Qwen3-0.6B vs Qwen3-1.7B near-tie (0.483 vs 0.498) is not resolvable at one seed.
- **Input populations (disclosed 2026-11-04).** E002's geometry pass profiled 288 prompts
  (24 pairs/family) against flip-rate runs of 1200 items (100 pairs/family) — the certified
  overlap is only the seed-0 common prefix (the first family's 48 prompts,
  position-aligned; total prompt-string overlap is higher through chance template
  collisions, which are not matched inputs). The verdict is unaffected but the
  identical-inputs premise in the E002 preregistration did not hold as executed; see the
  input-population audit in [E002](experiments/E002-geometry-vs-robustness.md). Future
  geosweep runs are matched to each model's flip-rate record and `geom inputs` verifies.
- **E001d** — add a digit-separated variant of the `arithmetic` family. Later reading
  ([[library/ideas/tokenization-limits-reasoning]]) says a BPE tokenizer can make arithmetic
  impossible regardless of reasoning ability, and `arithmetic` had our lowest flip rate with
  sub-chance canonical accuracy — the signature of a tokenizer floor. Our preregistration
  listed this confound as low-risk; that judgement was wrong and the family's numbers should
  be reported separately until it is settled.
- **E002** — reconsider **stickiness** as the outcome variable. It is well defined even at
  chance accuracy and fell overall with scale (0.913 → 0.793, non-monotonically) across
  124M → 1.5B, as flip rate rose overall (0.048 → 0.171, also non-monotonically).

Two things a functional check of `geom geometry` on gpt2 already surfaced, worth fixing
before E002 is preregistered (not results — the run was a wiring check, so it was not kept):

- **Layer 0 intrinsic dimension is undefined**, and correctly reports `nan`. Every prompt
  ends with the same token (`Answer:`), so the layer-0 last-token embeddings are duplicates.
  E002 must either skip layer 0 or pool differently.
- **Anisotropy is 0.86–0.996 at every layer**, with participation ratio 1.2–4.7 out of 768
  ambient dimensions. This reproduces the published representation-degeneration picture
  exactly ([[library/ideas/token-geometry-and-anisotropy]]): fewer than five effective
  directions, vectors ~90–99% mutually aligned. Raw cosine geometry is nearly uninformative
  here. Descriptors must be computed on centred activations, and E002 should preregister a
  before/after top-k-dimension-removal comparison — a geometric effect that vanishes when
  the rogue dimensions go was measuring token frequency.
- **The better geometric candidate is the intrinsic-dimension *profile*, not a flat
  summary.** Valeriani et al. find a characteristic hump across layers, with semantic
  structure emerging at the contraction after the peak. Our gpt2 profile shows that shape
  (rising to ~5.3 at layer 8, falling to ~1.4 by layer 11). That is a more promising E002
  outcome variable than participation ratio.

## Setup

```bash
uv sync --extra dev
uv run geom doctor      # verify backend first
uv run geom smoke       # <60s end-to-end. Exit 0 only on a full pass including the model check;
                        #   'smoke PARTIAL' (exit 1) = model path skipped (network/unavailable model);
                        #   'smoke FAILED' (exit 1) = load/scoring failure, cause printed
uv run geom items --n 2 # read the items before trusting any number
```

## What this project cannot conclude

Stated in advance so the verdict cannot quietly expand:

- Nothing about 7B+ models. A null at 1.5B does not falsify the claim at frontier scale.
- Nothing about Sophontic's actual system, which is not public.
- Nothing causal from E002 alone — geometric descriptors are correlational until an
  intervention experiment says otherwise.
- Nothing about "reasoning" in general. Six synthetic families are a probe, not a definition.
