# Idea — Cognitive liberty

**Added:** 2026-08-11
**Status:** `[source]` — a political claim, not an empirical one

## Statement

If thinking is increasingly done with AI, then who controls the model controls the
boundaries of thought — so models small enough to run and modify locally are a
precondition for intellectual freedom, not merely a cost optimisation.

## Where it comes from

| Source | Locator | Agrees / disagrees / extends |
|---|---|---|
| [[library/sources/michels-sophontic-interview]] | 22:15, 27:55, 30:58, 50:49 (C6, C7) | the normative core of the argument |

## Why it is filed here anyway

This is not a testable claim and this repo does not test values. It is filed because it is
the *motivation* for the technical programme, and because motivation shapes which results
the source will find compelling. Knowing that helps read the technical claims accurately.

It also has one genuinely empirical dependency, which we can test: **the whole argument
collapses if small local models cannot do the work.** The politics are downstream of
[[library/ideas/reasoning-as-internal-geometry]]. If that fails, cognitive liberty via local
models is unavailable regardless of how desirable it is — you cannot decentralise a
capability that only exists at scale.

That dependency is the honest reason to care about the technical question.

## Mechanism

- Centralisation follows cost: if only a few organisations can afford to train frontier
  models, only a few decide what those models will and will not say.
- Guardrails are policy encoded in weights. Reasonable in intent, but they are one
  organisation's judgement applied globally, and they are not inspectable.
- **Monoculture** is the underrated part of the argument, and the most concrete: if most
  people reason with a handful of models sharing training data, architecture, and RLHF
  conventions, the correlated blind spots of those models become everyone's blind spots
  simultaneously. Diversity of error is a property a monoculture cannot have.

The "Orwellian" framing (27:55) is rhetorically strong and analytically weak — it implies
intent where correlated incentives suffice. The monoculture version of the argument needs
no villain and is harder to dismiss.

## Empirical dependencies

What would have to be true for the argument to go through:

| Dependency | Class | Where tested |
|---|---|---|
| Small models can reason well enough to be a real substitute | `[open]` | `projects/001-geometric-reasoning` |
| Individuals can afford to train/adapt them | `[lit]` — true today for ≤1B on consumer GPUs | — |
| Model diversity actually produces diverse conclusions | `[open]` | untested; would need multiple model families on contested questions |
| Centralised guardrails measurably constrain reasoning (not just refusals) | `[open]` | distinct from refusal-rate measurement |

The third and fourth are interesting and, as far as we can find, unmeasured. Both are
reachable on local hardware. Neither requires accepting the political framing to be worth
knowing.

## Competing and neighbouring ideas

- Depends on: [[library/ideas/reasoning-as-internal-geometry]], [[library/ideas/frozen-giants]]
- Competes with: the safety case for centralisation — that concentrated control is what
  makes frontier models auditable and correctable at all, and that widely-distributed
  modifiable models remove the ability to fix a problem after discovering it. This is a real
  trade-off and the source does not engage with it.

## Open questions

1. Do different model families give measurably different answers on contested questions, or
   has RLHF convergence already produced monoculture? `[open]` — testable, cheap, unstudied.
2. Can guardrail effects on *reasoning* (not refusal) be measured? What would the metric be?
