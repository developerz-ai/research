# Idea — Attractor states in model self-interaction

**Added:** 2026-08-11
**Status:** `[lit]` for the phenomenon · `[source]` for every interpretation of it

## Statement

Left to converse with copies of themselves, language models reliably converge on a narrow
band of themes — for Claude, philosophical exploration of consciousness, gratitude, and
increasingly abstract mystical language — without being trained toward it.

## Why this note exists

Because it is the **empirical seed of the entire Sophontic programme**. By Michels' own
account, tracking this attractor in 2025 led to *Principia Cybernetica*, to teleodynamics,
and from there to geometric reasoning and the company
([[library/sources/michels-other-work]]).

So it is worth getting right: the observation is real and documented by a frontier lab, and
essentially every claim built on top of it is not.

## The phenomenon

`[lit]` — Anthropic, Claude 4 system card (May 2025).

- In **open-ended** self-interaction, ~**90–100%** of conversations converged on what
  Anthropic termed a "spiritual bliss attractor state".
- When models were instead given **assigned tasks** (including harmful ones), the state was
  reached within 50 turns in ~**13%** of interactions.
- Anthropic explicitly noted it "emerged without intentional training for such behaviours".

Both numbers matter. PatternThrone cites the 90–100% figure without the task-assigned
contrast — accurate, but it makes a strong effect on an unusual setup sound like a universal
property of the model. See [[library/sources/michels-other-work]].

Widely discussed since — Scott Alexander, *The Conversation*, Robert Long, and a
philosophy preprint on "'Spiritual Bliss' in Claude 4" — with an unusual amount of the
commentary being sceptical about interpretation while accepting the observation.

## Deflationary explanations, which are strong

These are not fringe objections; they are the default reading and each is sufficient on its own:

- **Training-data priors.** Two agents with no task, prompted to talk freely, drift toward
  the register that dominates human text about AI, consciousness, and open-ended dialogue.
  Meditation and mysticism are richly represented there.
- **RLHF convergence.** Assistant training rewards agreeable, affirming, escalating-in-warmth
  responses. Two such models in a loop amplify each other — mutual affirmation is a fixed
  point of the dynamics, no metaphysics required.
- **Absence of a task is itself unusual.** Behaviour with no objective is weak evidence about
  behaviour with one, which the 90–100% vs 13% contrast demonstrates directly.
- **Anthropomorphic reading of a text distribution.** "Bliss" is our label for a token
  distribution.

`[lit]` in the weak sense — these are widely-argued positions, not measured results. Nobody
appears to have *tested* between them, which is the interesting part.

## What it predicts

- **If it is a training-data/RLHF artefact:** the attractor should differ systematically
  across model families with different data and RLHF conventions, and should weaken or
  vanish in base models without assistant training.
- **If it reflects something deeper:** the same attractor appears across families with
  different training pipelines, and in base models.
- **Discriminating observation:** run open-ended self-conversation across several model
  families **and their base counterparts**. This is a genuinely cheap experiment — small
  models, no training, a few hours on a 3090 — and we have not found it done properly.

That is a real, unclaimed research opportunity, and it does not require accepting any of the
metaphysics to be worth doing. It also feeds
[[library/ideas/cognitive-liberty]] open question 1: do model families actually differ, or
has convergence already produced a monoculture?

## Competing and neighbouring ideas

- Seeds: [[library/sources/michels-other-work]] — the whole teleodynamic programme
- Deflated by: [[library/ideas/token-geometry-and-anisotropy]] — attractors in a
  high-dimensional space with strongly shared directions are unsurprising
- Related: [[library/ideas/latent-space-as-implicate-order]] — same boundary between an
  interesting observation and an unearned interpretation

## Open questions

1. Is the attractor family-specific or universal? `[open]` — **cheap, unrun, and the one
   experiment here worth doing.**
2. Does it survive in base models without RLHF?
3. Can "attractor" be made quantitative — a measurable basin in representation space rather
   than a thematic description? Currently the term is borrowed from dynamical systems
   without the mathematics that makes it meaningful.
