# Idea — Linear representation hypothesis

**Added:** 2026-08-11
**Status:** `[lit]` — well supported, with known limits

## Statement

High-level concepts are encoded as linear directions in a model's representation space, so
they can be found with linear probes and changed by adding vectors.

## Where it comes from

Not from the Sophontic source — this is the established literature that
[[library/ideas/reasoning-as-internal-geometry]] needs in order to have any handle at all.
If concepts were not recoverable by tractable geometric operations, "engineering the
geometry" would have nothing to grip.

| Source | Class | Note |
|---|---|---|
| Mikolov et al. 2013 — `king − man + woman ≈ queen` | `[lit]` | first evidence, word embeddings |
| Park et al., ICML 2024 — <https://proceedings.mlr.press/v235/park24c.html> | `[lit]` | formalises it for LLMs; categorical + hierarchical structure |
| Zou et al. 2023 — representation engineering, <https://arxiv.org/abs/2310.01405> | `[lit]` | causal: steering along directions changes behaviour |
| Elhage et al. 2022 — toy models of superposition | `[lit]` | why more features than dimensions can coexist |

## Mechanism

The residual stream is a shared vector space that layers read from and write to. Features
are directions in it. Because there are more useful features than dimensions, features are
stored in **superposition** — non-orthogonal, tolerable as long as few are active at once.

The practical consequences are what matter here: a linear probe can recover a feature, and
adding its direction can induce it. Both are cheap, and both work on a 3090.

## What it predicts

- **If true:** task-relevant features are linearly decodable from hidden states, and probe
  accuracy tracks the model's ability to use the feature.
- **If false (for a given feature):** only non-linear probes recover it, and steering along
  any single direction fails to change behaviour.
- **Discriminating observation:** compare linear vs non-linear probe accuracy on the same
  feature. A large gap marks a feature that is *not* linearly represented — which is
  informative rather than a failure.

## Known limits

Strict linearity does not hold universally, and the exceptions are systematic rather than
noise:

- Some features are **multi-dimensional or manifold-like** — colours, dates, years,
  circular quantities. A single direction is the wrong object for these.
- Superposition means directions are **not orthogonal**, so steering one feature perturbs
  others. Clean single-feature intervention is an approximation.
- Probe accuracy measures **decodability, not use**. A feature can be linearly present and
  causally irrelevant — the most common overclaim in this literature, and the one to guard
  against when using probes as evidence for a geometric story.

That last limit is directly relevant to project 001: a geometric metric that correlates with
reasoning may be a passenger rather than a cause. Causal intervention, not correlation, is
what distinguishes them.

## Competing and neighbouring ideas

- Underpins: [[library/ideas/reasoning-as-internal-geometry]]
- Nuances: [[library/ideas/latent-space-as-implicate-order]] — superposition is the real,
  measurable version of "everything enfolded in everything".

## Open questions

1. Which reasoning-relevant features are linear and which are not?
2. Does linear decodability of a feature predict flip-rate robustness on items requiring it?
   `[open]` — this is the bridge experiment between probes and behaviour.
