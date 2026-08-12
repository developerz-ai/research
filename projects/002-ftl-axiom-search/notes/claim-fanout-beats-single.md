# Claim — Fan-out beats one agent on falsification, at matched budget

**ID:** `claim-fanout-beats-single`
**Added:** 2026-08-12
**Class:** `[open]`
**Descends from:** [[library/ideas/parallel-falsification-funnel]]

## Proposition

On deciding whether a modified axiom set is inconsistent, N independent agents each given
budget B/N reach **≥0.10 higher balanced accuracy** than one agent given the full budget B,
at equal total output tokens — and the advantage does *not* appear on the generative half of
the task (proposing a modification worth testing), where the single agent ties or wins.

## Falsifier

> This claim is dead if: at matched total output tokens, the fan-out arm's balanced accuracy
> on the falsify task is **≤** the single-agent arm's, across ≥3 seeds, or the difference's
> 95% CI includes zero.

Secondary kill: if measured inter-agent error correlation is **≥0.8**, the disjunction
argument that motivates fan-out is void and any observed gain is claimed for the wrong
reason — report this even when the headline difference is positive.

## Operationalisation

| Term in the claim | How it is measured | What this choice could get wrong |
|---|---|---|
| "matched budget" | total **output tokens** summed across all agents in the arm, equal within 5% | Output tokens ignore prompt cost, which fan-out pays N times. Wall-clock and dollars rank the arms differently — this choice favours fan-out, and saying so is part of the result. |
| "balanced accuracy" | mean of true-positive and true-negative rate on consistent/inconsistent sets, 50/50 by construction | A refuter prompted to be skeptical scores well by always refusing; the balanced form and the 50/50 split are what stop that. |
| "independent agents" | same base model, same prompt, different sampling seed | This is the weakest form of independence and the most likely reason the claim fails. A perspective-diverse variant (different lenses per agent) is the obvious follow-up, not the headline. |
| "inter-agent error correlation" | mean pairwise phi coefficient over per-item correctness vectors | Needs enough items for a stable estimate; underpowered here is worse than not reporting it. |
| "the generative half" | proposing which axiom to drop, scored against the solver label | Conflating the two halves is the mistake the whole claim exists to avoid. |

## Current evidence

| Class | Evidence | Where |
|---|---|---|
| `[source]` | "massively parallel falsification, not massively parallel insight-generation" | [[library/sources/ftl-agent-decomposition-chat]] T4 |
| `[lit]` | Self-consistency, debate, best-of-N with verifier all report gains — mostly **without** a matched-compute single-agent baseline | see `library/ideas/parallel-falsification-funnel` prior art |
| `[ours]` | none yet | — |

## Cheap test first

N=5 versus N=1 on 40 items (20 consistent, 20 inconsistent) from E001's generator, one small
local model, one seed. The only thing this cheap run has to establish is that the budget
accounting is right and the two arms actually spend the same. Get that wrong and every later
number is decoration.

## Reachability

Yes, with a small local model. A frontier-model arm is API-budget-bound, not
hardware-bound; if it is not run, say so rather than implying the result covers it.

## Status log

| Date | Class | Change |
|---|---|---|
| 2026-08-12 | `[open]` | created |
