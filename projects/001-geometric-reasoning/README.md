# 001 — Geometric reasoning

**Question:** Is there a geometric quantity of hidden states that predicts reasoning robustness after controlling for parameter count and training tokens?
**Status:** 🟡 active — E001 run and analysed; E002 blocked, redesign pending
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
| [E001](experiments/E001-flip-rate-across-scale.md) | What are the flip rates of open models 124M→1.5B, and does the shortcut gap shrink with scale? | **analysed** | Claim falsified as stated; no model reaches chance |
| E002 | Does any hidden-state geometric descriptor track flip rate independently of size? | **blocked by E001** — see below | — |

E001 required no training and ran in under an hour, which is why it went first.

## Findings so far

**E001 (2026-08-11, 3 seeds × 4 models × 600 pairs, RTX 3090)** `[ours]`

| Model | Params | Flip rate | Canonical acc | Stickiness |
|---|---|---|---|---|
| gpt2 | 124M | 0.048 | 0.729 | 0.913 |
| gpt2-medium | 355M | 0.042 | 0.726 | 0.922 |
| gpt2-large | 774M | 0.185 | 0.692 | 0.772 |
| gpt2-xl | 1.5B | 0.171 | 0.755 | 0.793 |
| *chance* | — | *0.250* | *0.500* | *0.500* |

1. **No GPT-2-family model reaches chance flip rate**, at any size tested. Below chance
   means errors are anti-correlated across the pair — both answers coming from the surface
   form the two members share.
2. **Canonical accuracy is 0.69–0.76 throughout.** A conventional benchmark would report
   that number and call these models decent at relational reasoning. The paired design puts
   the same models at 0.04–0.19. That contrast is the instrument working, and it is the most
   transferable result here.
3. **Scale helps non-monotonically and insufficiently.** 12.5× parameters buys 0.048 → 0.171,
   entirely between 355M and 774M; gpt2-medium is *below* gpt2 and gpt2-xl is at or below
   gpt2-large.
4. **A methodological finding worth more than the numbers:** the first run scored 0.98 flip
   rate on one family, which turned out to be solvable by "answer the last-named entity".
   Item families are now checked against trivial heuristics on every run
   (`uv run geom baselines`); the discarded runs are preserved in `results/superseded/`
   with the full explanation.

**Consequence:** E002 cannot run on this ladder. Flip rate has almost no usable variance
across it (0.04–0.19, all sub-chance), so correlating it against geometric descriptors would
be correlating against noise. Revised next steps:

- **E001b** — extend the ladder to modern ≤1.5B models (Qwen, Llama, SmolLM). One hour.
  GPT-2 is a 2019 base family and its failure is weak evidence about small models today.
- **E001c** — add a digit-separated variant of the `arithmetic` family. Later reading
  ([[library/ideas/tokenization-limits-reasoning]]) says a BPE tokenizer can make arithmetic
  impossible regardless of reasoning ability, and `arithmetic` had our lowest flip rate with
  sub-chance canonical accuracy — the signature of a tokenizer floor. Our preregistration
  listed this confound as low-risk; that judgement was wrong and the family's numbers should
  be reported separately until it is settled.
- **E002** — reconsider **stickiness** as the outcome variable. It is well defined even at
  chance accuracy and fell with scale where flip rate did not.

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
uv run geom smoke       # <60s end-to-end
uv run geom items --n 2 # read the items before trusting any number
```

## What this project cannot conclude

Stated in advance so the verdict cannot quietly expand:

- Nothing about 7B+ models. A null at 1.5B does not falsify the claim at frontier scale.
- Nothing about Sophontic's actual system, which is not public.
- Nothing causal from E002 alone — geometric descriptors are correlational until an
  intervention experiment says otherwise.
- Nothing about "reasoning" in general. Six synthetic families are a probe, not a definition.
