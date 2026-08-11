# Idea — Reasoning as internal geometry

**Added:** 2026-08-11
**Status:** `[open]` — the general form; parts are `[lit]`

## Statement

A model's reasoning ability is determined by the geometric organisation of its
representation space, not by its parameter count — so it can be engineered directly instead
of being bought with scale.

## Where it comes from

| Source | Locator | Agrees / disagrees / extends |
|---|---|---|
| [[library/sources/michels-sophontic-interview]] | 0:14, 7:22, 12:31 (C1) | asserts it as the core thesis |
| Representation-geometry literature | see below | supports the *weaker* form: structure exists and is causally relevant |

**The two forms are not the same claim, and conflating them is the main risk here.**

- **Weak form** `[lit]`: representations have measurable geometric structure, and that
  structure is causally involved in model behaviour. This is well supported.
- **Strong form** `[open]`: that geometry is the *binding constraint* on reasoning, is
  largely independent of scale, and can be optimised directly to buy capability that scale
  would otherwise buy.

Every interesting consequence needs the strong form. Nearly all the evidence supports only
the weak one.

## Mechanism

Proposed: concepts occupy directions and manifolds in the residual stream; reasoning is a
trajectory through that space; a model reasons well when the space is organised so that the
required transformations are simple and reliably reachable. Training the geometry directly
— rather than only the output distribution — would then shape the operations rather than
the answers.

**Gap:** the source gives no definition of "geometric density", so the mechanism cannot be
reproduced as stated, only guessed at. Candidate measurable proxies, all our own
speculation until shown otherwise: intrinsic dimensionality of hidden states, participation
ratio of the activation covariance spectrum, anisotropy, linear-probe separability of
task-relevant features, effective rank across layers. See [[library/ideas/linear-representation-hypothesis]].

## What it predicts

- **If true:** two models with identical parameter count and training budget, differing only
  in a geometry-shaping objective, differ substantially in reasoning robustness — and the
  gap is visible in the geometric metric *before* it shows in task accuracy.
- **If false:** geometric metrics track scale and data volume, and add nothing once those
  are controlled for. Any apparent gain disappears when the baseline is budget-matched.
- **Discriminating observation:** hold params and tokens fixed, vary only the geometric
  intervention, measure both a geometry metric and a robustness metric. A correlation that
  survives budget-matching is the evidence; anything else is confounded by data quality or
  specialisation — see [[library/ideas/data-quality-over-scale]].

The discriminating version matters because the competing explanation is boring and strong:
small specialists beating large generalists on narrow domains is a well-replicated result
that requires no geometric story at all.

## Prior art

`[lit]` — this idea has a substantial literature under other names:

- **Linear representation hypothesis** — concepts as directions; Park et al., ICML 2024,
  <https://proceedings.mlr.press/v235/park24c.html>
- **The Geometry of Reasoning: Flowing Logics in Representation Space** —
  <https://arxiv.org/abs/2510.09782>
- **Latent-space reasoning** — computation over hidden states rather than emitted tokens;
  e.g. chain-of-superposition <https://arxiv.org/abs/2510.15522>
- **Representation engineering / activation steering** — the applied branch: if directions
  are causal, editing them changes behaviour. Broadly replicated.
- **Intrinsic dimension of representations** — long-standing tooling for measuring the
  geometry, independent of any claim about reasoning.

The literature establishes the weak form comfortably. What is missing there, as here, is a
budget-matched demonstration that optimising geometry *directly* beats spending the same
compute on data or parameters.

## Competing and neighbouring ideas

- Competes with: [[library/ideas/data-quality-over-scale]] — the leading rival explanation
  for every small-model win, and the one an experiment must rule out.
- Depends on: [[library/ideas/linear-representation-hypothesis]] — if structure is not
  linear/measurable, "engineering the geometry" has no handle.
- Measured by: [[library/ideas/flip-rate-evaluation]] — robustness, not accuracy, is the
  outcome variable that would show this.
- Motivated by: [[library/ideas/latent-space-as-implicate-order]] — philosophically, not
  mechanically. Keep separate.

## What we measured

`[ours]` — `projects/001-geometric-reasoning`, E002, 2026-08-11. 16 models, 124M→9B,
2019→2026.

**No geometric descriptor predicts reasoning robustness once size is controlled.**
Participation ratio, effective rank, TwoNN intrinsic dimension and anisotropy all correlate
with flip rate at ρ = 0.57–0.85 raw — and essentially all of it is mediated by parameter
count. Best surviving partial ρ after removing the GPT-2 family: **0.006**.

The apparent +0.692 for intrinsic dimension was four 2019 models in one corner. Old models
have both worse geometry and worse reasoning; nothing links the two but vintage.

Scope, stated plainly: this tests *our* descriptors, at one depth, across models that differ
in everything at once. It is a screening result, not a refutation. No intervention was
tested, and the strong form remains untested rather than disproved.

## Open questions

1. What is "geometric density"? Still undefined. Until it is, every test is a test of our
   guess, and a proponent can always say we measured the wrong quantity. `[open]`
2. ~~Does any geometric metric predict reasoning robustness after controlling for
   parameters?~~ **Not among the four we tried, across 16 models.** `[ours]`
3. Would a *better-controlled* ladder — one family, one corpus, varying only size — show a
   surviving correlation? Our confound was uncontrolled model diversity; this is the fix, and
   it requires training. `[open]`
4. Can a geometry-shaping auxiliary loss beat spending the same compute on better data?
   The decisive experiment. **Not justified by current evidence** — the cheap screen came
   back empty. `[open]`
5. Does it transfer, or work only inside a narrow domain where specialisation already
   explains the result?
