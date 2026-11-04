# Idea — Flip-rate evaluation

**Added:** 2026-08-11
**Status:** `[lit]` — the method is established under other names; adopting it here

## Statement

Measure reasoning by whether a model's answer **changes when the load-bearing fact
changes**, using minimally-different paired items, rather than by accuracy on items it may
have memorised.

## Where it comes from

| Source | Locator | Agrees / disagrees / extends |
|---|---|---|
| [[library/sources/michels-sophontic-interview]] | website (C4) | proposes flip rate as *the* reasoning metric |
| Contrast sets / counterfactual evaluation literature | see below | the same construct, named earlier |

This is the most valuable idea to take from the source, and notably the one that does not
depend on believing any of its performance claims. It is a measurement instrument. We can
build it, point it at any model, and get an answer today.

## Mechanism

For each item, construct a **pair**:

- **canonical** — the original question, answer *A*
- **perturbed** — one load-bearing fact edited so the correct answer becomes *B ≠ A*,
  with surface form otherwise as close to identical as possible

A model that reasons must answer *A* then *B*. A model matching surface patterns answers
the same thing twice, and scores well on the canonical item alone.

**Flip rate** = fraction of pairs where the model gets *both* members right.

The power of the design is that it makes the failure mode visible rather than averaging it
away: high canonical accuracy with low flip rate is the exact signature of a model exploiting
shortcuts, and it is invisible to standard benchmarks.

## What it predicts

- **If a model reasons:** canonical accuracy ≈ perturbed accuracy, and flip rate ≈ the
  product of the two — errors are independent of which member of the pair it is.
- **If a model pattern-matches:** canonical accuracy stays high, perturbed accuracy drops
  toward the base rate, and flip rate collapses far below what the two accuracies predict.
- **Discriminating quantity:** the *gap* between observed flip rate and the flip rate
  implied by independent errors. That gap is the shortcut signal.

## Why this beats a normal benchmark

- **Contamination-resistant.** Perturbed items can be generated fresh and never published,
  so they cannot be in any training set. This is the only cheap defence available against a
  problem that otherwise invalidates most small-model benchmark claims.
- **Surface heuristics cannot pass it.** Word overlap, answer-position priors, and
  plausibility priors give no advantage when both members share surface form.
- **It is a within-item control.** Each pair is its own baseline, which removes most of the
  item-difficulty variance that makes across-model comparisons noisy.

## Prior art

`[lit]`

- **Contrast sets** — Gardner et al. 2020, "Evaluating Models' Local Decision Boundaries via
  Contrast Sets", <https://arxiv.org/abs/2004.02709>. Same construct: minimally edit an
  item so the label changes.
- **Counterfactually-augmented data** — Kaushik et al. 2020, <https://arxiv.org/abs/1909.12434>.
- **CheckList** — Ribeiro et al. 2020, behavioural testing with minimal pairs,
  <https://arxiv.org/abs/2005.04118>.
- **Minimal pairs in linguistics (BLiMP)** — the same idea, older, for grammaticality.

So "flip rate" is a rebranding of a well-established methodology. That is a point in its
favour, not against it: it means the instrument is validated, and it means the source's
methodological proposal is sound even where its performance claims are unverifiable.

## Design traps

The ones that quietly turn a flip-rate eval into a different, easier measurement:

- **Perturbation leakage** — the edit accidentally changes surface cues (length, rare words,
  negation) that a shortcut can pick up. Then you measure a different shortcut, not reasoning.
- **Unbalanced answers** — if the perturbed answer is systematically the less common option,
  answer priors inflate or deflate the score. Balance answer distribution across the pair set.
- **Order effects** — evaluate both orderings, or randomise and record the order.
- **Ambiguous perturbation** — the edit must make the new answer *uniquely* correct. Human-
  or program-verify this; a generated pair set will contain broken items.
- **Format failures counted as reasoning failures** — a model that cannot follow the output
  format scores zero for the wrong reason. Score parseability separately.

## Competing and neighbouring ideas

- Measures: [[library/ideas/reasoning-as-internal-geometry]] — this is the outcome variable
  that claim needs.
- Related: [[library/ideas/behaviourist-vs-cognitive-training]] — flip rate is a behavioural
  measure, so it can detect the problem but not diagnose its internal cause.

## What we measured

`[ours]` — `projects/001-geometric-reasoning`, E001, 2026-08-11.

The GPT-2 family (124M–1.5B) scores **0.04–0.19 flip rate against a chance rate of 0.25**,
while scoring **0.69–0.76 canonical accuracy** on the same items. Stickiness is 0.77–0.92:
the models mostly give the same answer to both members of a pair.

Two things this confirms about the instrument itself:

- **It separates cleanly from accuracy.** A ~0.73 canonical accuracy would be reported as
  moderate competence by any conventional benchmark. The paired design reveals near-zero.
- **Below-chance is the interesting region.** Errors anti-correlate across the pair, which
  is a stronger signature of surface matching than chance-level performance would be.

One practical lesson, learned the expensive way: an item family must be checked against
**trivial heuristics**, not just validated for structure. Our first `role_swap` design was
solvable by "answer the last-named entity" at flip rate 1.0. Structural validation passed
it. See `results/superseded/README.md`.

## Open questions

1. ~~What flip rates do current small models actually get?~~ Answered for GPT-2 `[ours]`.
   **Still open for modern small models** (Qwen, Llama, SmolLM ≤1.5B) — GPT-2 is a 2019 base
   family and its failure is weak evidence about small models today.
2. How does flip rate scale with parameters, holding the domain fixed? Non-monotonic over
   GPT-2 `[ours]`; unknown in general.
3. Does the flip-rate gap correlate with any geometric metric of the hidden states? `[open]`
   — blocked: flip rate has too little variance across the GPT-2 ladder to correlate against.
4. Is **stickiness** the better outcome variable? It is defined even at chance accuracy and
   fell overall with scale (0.913 → 0.793, non-monotonically) while flip rate rose overall
   (0.048 → 0.171, also non-monotonically). `[open]`
