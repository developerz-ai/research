# Idea — Frozen giants

**Added:** 2026-08-11
**Status:** `[source]` for the framing; the underlying facts are `[lit]`

## Statement

Frontier models are static after training — they cannot learn from use — and that
"frozen" property, not their size, is the structural weakness of the scaling paradigm.

## Where it comes from

| Source | Locator | Agrees / disagrees / extends |
|---|---|---|
| [[library/sources/michels-sophontic-interview]] | 5:06, 21:09, 26:32 (C5) | frames scaling as "alchemical" and its products as "frozen giants" |

## Two claims wearing one phrase

Worth separating, because they have very different evidential status:

1. **Frontier models do not learn after deployment.** `[lit]` — straightforwardly true.
   Weights are fixed; adaptation happens in-context or through periodic retraining by the
   vendor. Continual learning remains unsolved (catastrophic forgetting).
2. **Scaling is "alchemical" — empirical trial-and-error rather than principled science.**
   `[source]` — rhetoric, but with a defensible core. Scaling laws are empirical fits, and
   capability emergence is predicted poorly if at all. The pejorative framing is doing work
   the evidence does not require, though: an empirical regularity that reliably predicts
   loss is not alchemy, it is engineering without a theory. Those are different complaints.

Claim 1 is the one that carries consequences. Claim 2 is mostly a mood.

## Mechanism

Cost asymmetry is the actual argument. Training is a large one-time expense, so it is
amortised by serving one model to everyone. That forces the model to be a generalist, forces
it to be static, and concentrates control over its behaviour in whoever paid for the run.
A model cheap enough to retrain per-user or per-domain removes all three constraints at
once — which is why the size claim and the political claim are linked rather than merely
adjacent. See [[library/ideas/cognitive-liberty]].

## What it predicts

- **If true:** the practical advantage of a small local model shows up most in *adaptation*
  — a model that continues learning on a user's domain overtakes a larger static one on
  that domain, given enough interaction.
- **If false:** in-context learning and retrieval substitute adequately for weight updates,
  and the frozen property costs nothing that matters.
- **Discriminating observation:** a task where the needed knowledge exceeds the context
  window and cannot be retrieved piecemeal. If long-context and RAG close the gap there,
  "frozen" is not the weakness claimed.

That last one is testable on a 3090 and has not obviously been done cleanly.

## Prior art

`[lit]`

- Catastrophic forgetting / continual learning — decades of literature, no solved general case.
- Scaling laws — Kaplan et al. 2020, Hoffmann et al. 2022 (Chinchilla). Empirical fits that
  predict loss well and capabilities poorly.
- Energy/cost analyses of frontier training — real, though frequently quoted with
  inconsistent methodology; treat specific numbers with suspicion regardless of who cites them.

## Competing and neighbouring ideas

- Supports: [[library/ideas/cognitive-liberty]] — the political argument depends on this
  technical one.
- Competes with: the view that scale plus in-context learning is sufficient, and that
  weight-level adaptation is an inefficiency rather than a capability.

## Open questions

1. Is there a task class where continual weight updates beat long-context + retrieval at
   matched cost? `[open]`
2. How much adaptation does a 124M–1B model need before it beats a frozen 70B on a narrow
   domain — and is that a geometry result or just fine-tuning working as expected?
