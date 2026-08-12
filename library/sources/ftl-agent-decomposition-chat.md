# Source — FTL / teleportation decomposed into an agent pipeline (chat transcript)

**Added:** 2026-08-12
**Type:** chat transcript (LLM assistant, unidentified model/date)
**Author / speaker:** an LLM assistant, in conversation with @sebyx07
**Published:** unpublished; pasted into this repo 2026-08-12
**Link:** `library/sources/raw/` — not archived; the transcript is quoted inline below
**Locator scheme:** turn numbers (T1…T5), counted from the first assistant reply

## Incentive

This is an LLM describing what LLM swarms are good for. That is a **structurally
self-serving claim** — the tool is asserting its own applicability — and it arrives with no
measurement, no baseline, and no cost accounting. Under the repo's rule it stays `[source]`
permanently until replicated by someone with nothing to gain from the answer.

Second incentive worth naming: the transcript is *fluent about physics it does not test*.
The physics content (T1–T2) is a competent textbook summary and is not the object of study
here. The **method** content (T3–T5) is the part that makes a testable engineering claim,
and it is the part with no evidence behind it at all.

## Summary

The user asks what would have to be discovered to permit FTL travel and matter
teleportation. T1–T2 answer conventionally: GR + QM as currently formulated forbid both;
the blockers are a quantum-gravity formalism, macroscopic negative energy density, a
resolution of FTL-induced closed timelike curves, and the no-cloning theorem. T3–T5 pivot
to *method*: the assistant proposes that the historical "Einstein move" was a search over
**axioms** rather than over solutions within fixed axioms, and that this move is partially
mechanisable — a three-layer pipeline where agents enumerate hidden assumptions (L1), a
large parallel fleet rebuilds the formalism with each assumption inverted and falsifies
almost all of them cheaply (L2), and the few survivors escalate to sustained human or
high-capability-model attention (L3). T5 adds a cost argument: the dominant lever is not
making the expensive tier fast, it is making the cheap filter good enough that the
expensive tier is rarely invoked.

## Claims

| # | Claim | Locator | Class | Checkable? |
|---|---|---|---|---|
| C1 | GR + QM as formulated forbid FTL for anything carrying mass or information | T1 | `[source]` | yes — but not on our hardware; standard textbook physics, `[lit]` elsewhere |
| C2 | Alcubierre / Morris-Thorne metrics are valid solutions; the blocker is the stress-energy side, which needs negative energy density | T2 | `[source]` | yes, `[lit]`; out of scope here |
| C3 | No-cloning forbids matter teleportation-as-copying, and is a consequence of QM's linearity axiom, not of technique | T2 | `[source]` | yes, `[lit]`; settled |
| C4 | **The productive move is search over axiom space, not over solutions within fixed axioms** | T4 | `[source]` | needs operationalising — this is idea `axiom-space-search` |
| C5 | **LLMs cannot reliably distinguish "this is measured" from "this is assumed since 1687"; this is the actual bottleneck** | T4, "Why this is genuinely hard" | `[source]` | **yes, cheaply** — this is the project |
| C6 | **Massively parallel falsification of axiom-perturbations is buildable now and is where many agents earn their keep** | T4, L2 | `[source]` | yes — swarm vs single at matched budget |
| C7 | Selecting which internally-consistent-but-weird framework is worth pursuing ("scientific taste") is not currently mechanisable | T4, L3 | `[source]` | no — not operationalised, and probably not on our hardware |
| C8 | **The dominant cost lever is filter precision, not expensive-tier throughput: a Tier-0/1 funnel killing 99.9% means the heavy tier sees a tiny pre-filtered stream** | T5 | `[source]` | yes — the 99.9% figure is asserted with no measurement |
| C9 | Cross-branch memoisation of shared sub-lemmas is a bigger performance lever than raw throughput, because theory-space has large structural overlap | T5 | `[source]` | yes, but downstream of C8 |

## Quotes

> "This is a search over axioms, not over solutions within fixed axioms. That's the key
> distinction from what most 'AI for science' does today." — T4

> "current LLMs pattern-match on existing physics text, they don't reliably distinguish
> 'this is measured' from 'this is assumed because everyone since 1687 assumed it.' That's
> the actual bottleneck." — T4

> "Most attempts collapse into contradiction immediately — that's fine, it's cheap to
> falsify at scale. This is genuinely where 'many subagents' helps: massively parallel
> falsification, not massively parallel insight-generation." — T4

> "the actual engineering priority isn't 'make the GR solver fast' — it's 'make the filter
> so good that the GR solver is rarely invoked.'" — T5

## Terminology

| Their term | Nearest standard term | Notes |
|---|---|---|
| "Layer 1 / assumption-extraction" | axiom identification; presupposition extraction | No standard benchmark exists for it. That absence is why 002 exists. |
| "Layer 2 / counterfactual-consistency" | independence testing; model search for a modified axiom set | Classical proof theory has done this by hand since Beltrami (1868) |
| "Layer 3 / scientific taste" | theory choice; research heuristics | Not operationalised in the transcript. Unfalsifiable as stated. |
| "Tier 0/1/2/3 funnel" | cascaded filtering; staged verification | Standard IR/retrieval architecture, applied to theory search |
| "the Einstein move" | rejecting an unforced auxiliary hypothesis | Historically contested — see the synthesis note |

## Ideas extracted

- [[library/ideas/axiom-space-search]]
- [[library/ideas/measured-vs-assumed]]
- [[library/ideas/parallel-falsification-funnel]]

## What this source does not establish

- **No measurement anywhere.** Every quantitative claim (99.9% filter kill rate, "many
  subagents earn their keep") is asserted. None has a number behind it.
- **No baseline.** The swarm proposal is never compared against one agent given the same
  total token budget — the only comparison that could make "parallel helps" mean anything.
- **No contamination discussion.** Every historical axiom-rejection it names (simultaneity,
  aether, parallel postulate, parity) is in every model's pretraining corpus. A model
  "finding" these has demonstrated recall, not search. The transcript never raises this,
  and it is the single largest threat to the whole L1 proposal.
- **L3 is unfalsifiable as written.** "Taste" has no metric attached, so the proposal cannot
  fail at that layer — which also means it cannot succeed there.
- **The physics is not the object of study.** C1–C3 are conventional and correct as far as
  they go, but nothing about them is decidable from a 3090. See
  `projects/002-axiom-search/notes/out-of-scope-ftl.md`.
