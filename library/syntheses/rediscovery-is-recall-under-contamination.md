# Synthesis — Every test of "can AI find new physics" is a memory test unless the physics is new

**Added:** 2026-08-12
**Status:** `[open]` until tested

## Ingredients

| Idea | From | Contributes |
|---|---|---|
| [[library/ideas/measured-vs-assumed]] | [[library/sources/ftl-agent-decomposition-chat]] | The capability under test: separating forced propositions from inherited ones |
| [[library/syntheses/perturbation-evals-and-contamination]] | prior repo work (001) | The design pattern: a paired item whose surface is familiar and whose answer is not |
| [[library/ideas/axiom-space-search]] | [[library/sources/ftl-agent-decomposition-chat]] | The search procedure whose first stage this gates |

## The combination

**Inherited:** benchmarks that predate a model's cutoff are contaminated (standard).
**Inherited:** the interesting number in a contamination-sensitive eval is a *paired
difference*, not a raw score (001's design).

**New — and this is the risky part:** the proposal to have agents "identify the hidden
assumption in GR + QM" is, as stated, **untestable in principle**, not merely
uninstrumented. Every historical axiom-rejection anyone would validate it against —
absolute simultaneity, the parallel postulate, the aether, parity conservation, local
realism — is in the pretraining corpus, discussed *as an axiom-rejection*, thousands of
times. A model naming absolute simultaneity as the droppable axiom of Newtonian kinematics
has demonstrated retrieval and nothing else. And a model naming a droppable axiom in
present-day GR + QM cannot be scored at all, because nobody has the answer key.

The capability is therefore squeezed from both sides: where we can grade, the answer is
memorised; where the answer is not memorised, we cannot grade. Any honest test has to
manufacture a third region — **formal systems with ground truth by construction and no
presence in any corpus**. That is the only place the claim is decidable, and it costs the
claim its generality: success on synthetic systems does not transfer to physics for free,
and must never be reported as if it did.

## Why nobody has said this

The contamination literature and the AI-for-science literature barely cite each other. The
first is about benchmark hygiene on tasks with known answers; the second is about
open-ended discovery where the whole point is that no answer exists. The failure mode lives
exactly on the seam: a discovery system validated on historical rediscoveries, presented as
evidence it can do novel discovery. Papers that "rediscover" Kepler's laws or known
physical equations from data are the standard instance, and the objection applies to all of
them.

## What it would predict

- **Novel prediction:** model accuracy at identifying the unforced axiom drops toward chance
  as corpus presence of that specific system drops — and the drop is *steeper* than the
  drop on ordinary reasoning tasks over the same systems, because the epistemic-status label
  has no surface signal while derivational structure does.
- Not implied by contamination alone, because plain contamination predicts a uniform drop
  across all task types over the same material. The claim here is a task-specific
  differential.
- Not implied by `measured-vs-assumed` alone, because that idea says the capability is
  absent; it does not say the standard way of demonstrating the capability is structurally
  incapable of detecting its absence.

## How it could be wrong

1. **Synthetic systems are too easy or too alien.** Logical independence in a small
   propositional system may be decidable by a shallow heuristic no physicist would call
   insight, or so unlike physics that a null result says nothing about the real task. This
   is the most likely failure and the verdict must scope to it explicitly.
2. **Corpus presence is not measurable well enough** to make "steeper drop" a real
   comparison. Proxy measures (n-gram overlap, model perplexity on the statement) are crude.
3. **The differential exists but for a boring reason** — e.g. epistemic-status questions are
   simply harder, uniformly, contaminated or not. The control for this is a matched
   ordinary-reasoning task over the identical systems.
4. Duhem-Quine in its strong form: for real theories "which axiom is unforced" may have no
   determinate answer, so the synthetic ground truth is not a scale model of the target.

## Route to a claim

`projects/002-ftl-axiom-search` — `claim-axiom-id-is-recall`. Cheapest test: generate
propositional/algebraic axiom systems with a known-redundant member, score identification
against a matched contaminated set of historical systems, report the **delta**. CPU-runnable
at small item counts; the ground truth comes from a SAT/SMT independence check, not from a
model.
