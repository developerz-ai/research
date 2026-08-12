# Idea — Fan out to falsify, not to generate

**Added:** 2026-08-12
**Status:** `[open]`

## Statement

Parallel agents pay for themselves when each one's job is to *kill* a candidate cheaply and
independently, and the total cost is then dominated by the precision of the cheap filter
rather than by the throughput of the expensive verifier.

## Where it comes from

| Source | Locator | Agrees / disagrees / extends |
|---|---|---|
| [[library/sources/ftl-agent-decomposition-chat]] | T4 (L2), T5 (C8, C9) | Asserts both halves; measures neither |

## Mechanism

Two separate assertions live inside this, and they should not be tested together:

1. **Fan-out helps for falsification specifically.** Falsification is disjunctive — any one
   agent finding a contradiction settles the candidate, so N independent attempts compose by
   OR and errors do not accumulate. Generation is conjunctive — a good proposal needs many
   things right at once, so N shallow attempts do not compose into one deep one. The
   prediction is that fan-out beats a single long-context agent on the falsify task and
   loses to it on the propose task, **at matched total token budget**.
2. **Cost is filter-dominated.** In a cascade where tier *k* costs `c_k` per item and passes
   fraction `p_k`, total cost is `c_0 + p_0·c_1 + p_0·p_1·c_2 + …`. When `c_3 ≫ c_0`, the
   term that matters is `p_0·p_1`, so a marginal improvement in early-tier precision beats a
   large speedup in the last tier. That is arithmetic, not a hypothesis. What *is* a
   hypothesis is the claimed `p ≈ 0.001` — a filter that aggressive is useless if it also
   discards the true positives, and the transcript never mentions recall.

## What it predicts

- **If true:** at equal token spend, N parallel refuters confirm/kill a candidate set more
  accurately than one agent given N× the budget; and a cheap filter exists with recall high
  enough (say ≥0.9 on known-good candidates) at a pass rate low enough to matter.
- **If false:** the parallel arm loses or ties, because independent agents make *correlated*
  errors — same base model, same prompt, same blind spot — so N votes are worth far fewer
  than N independent votes, and the diversity the disjunction argument assumes is not there.
- **Discriminating observation:** measured inter-agent error correlation. If refuters agree
  on their mistakes, the disjunction argument is void regardless of the headline accuracy.

## Prior art

`[lit]` — self-consistency / majority-vote sampling, debate and multi-agent verification,
best-of-N with a verifier: all show gains, most **without matching the budget against a
single agent given the same compute**, which is the comparison that decides this.
`[lit]` — cascaded inference and early-exit routing in retrieval and serving is a mature
area; the cost arithmetic above is standard there.
`[open]` — the specific claim that correlated errors do *not* void the fan-out gain for
formal-consistency checking.

## Competing and neighbouring ideas

- Competes with: "just use a bigger context and one strong reasoner" — the single-agent arm
  is the baseline, and it is a serious one.
- Composes with: [[library/ideas/axiom-space-search]] — a small candidate space with cheap
  independent falsification is the one shape where this idea should look best. If it fails
  here it fails everywhere.
- Neighbours: [[library/ideas/flip-rate-evaluation]] — both insist the informative number is
  a *paired difference*, not a raw score.

## Open questions

- What is the right unit for "matched budget" — output tokens, wall-clock, or dollars? They
  rank the arms differently and the answer must be fixed before the run.
- Does memoisation across candidates (C9) survive contact with real overlap rates, or is
  sub-lemma reuse rarer than the transcript assumes?
