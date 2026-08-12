# Idea — Search over axioms, not over solutions within fixed axioms

**Added:** 2026-08-12
**Status:** `[open]`

## Statement

The productive search in a stuck formal theory is over its **assumptions** — which one can
be dropped while leaving something consistent and non-trivial — not over solutions inside
the assumption set everyone already agrees on.

## Where it comes from

| Source | Locator | Agrees / disagrees / extends |
|---|---|---|
| [[library/sources/ftl-agent-decomposition-chat]] | T4, C4 | Asserts it as the mechanisable core of "the Einstein move" |

## Mechanism

A formal theory is a set of axioms plus derivation rules. Normal work explores the
consequence-set with the axioms held fixed. When the consequence-set contains a
contradiction or a dead end, the fix has to come from the axiom set — but axioms are
invisible in practice, because the ones that have never been questioned are the ones that
read as facts rather than as choices. So the procedure is: enumerate the axioms including
the invisible ones, ask of each what observation forces it, drop the unforced ones one at a
time, and check what survives.

Historically this is what non-Euclidean geometry was (drop the parallel postulate,
1823–1868), what special relativity was (drop absolute simultaneity, 1905), and what
Bell-violating quantum mechanics was (drop local realism, 1964–1982). In each case the
dropped axiom had been treated as self-evident rather than as an empirical commitment.

## What it predicts

- **If true:** given a formal system with an axiom that is genuinely unforced, a search
  procedure that operates on the axiom set finds the productive modification at a rate well
  above one that searches derivations inside the fixed set — and the gap widens as the
  consequence-set grows, because the derivation search is exploring a space that cannot
  contain the answer.
- **If false:** axiom-level search does no better than derivation-level search, because
  which axiom is droppable is only knowable *after* you have the replacement theory. Under
  this reading the historical cases are reconstructed backwards: nobody dropped simultaneity
  and then looked for what survived; Einstein had the light postulate first and simultaneity
  fell out.
- **Discriminating observation:** does the search procedure identify the droppable axiom
  **before** being shown the replacement theory? That ordering is the whole content of the
  idea, and it is what an experiment must control.

## Prior art

`[lit]` — the mathematics is old and settled: independence proofs by relative consistency
(Beltrami 1868, Gödel 1940, Cohen 1963) are exactly "drop the axiom, exhibit a model."
Reverse mathematics (Friedman, Simpson) does this systematically — for a theorem, find the
weakest axiom system that proves it. `[open]` — what has *no* literature is doing the
enumeration step automatically over a theory nobody has already reverse-engineered.
`[lit]` — machine-learning-for-conjecture work (Lean/Coq + LLM: DeepSeek-Prover, AlphaProof
and successors) searches *proofs*, not *axiom sets*. That is a different search space, and
the distinction is the reason this note exists.

## Competing and neighbouring ideas

- Competes with: the reconstruct-backwards reading above — that axiom choice is downstream
  of the new theory rather than upstream of it. This is the null hypothesis, and it is not a
  strawman; most historians of science hold some version of it.
- Depends on: [[library/ideas/measured-vs-assumed]] — the enumeration step is worthless if
  you cannot tell which axioms are forced.
- Composes with: [[library/ideas/parallel-falsification-funnel]] — axiom-space is small
  enough to enumerate and each candidate is cheap to falsify, which is what makes fan-out
  plausible here and not elsewhere.

## Open questions

- Is the historical evidence for this even four independent cases, or one pattern
  retrofitted onto four?
- Can it be tested at all without contamination? Every historical instance is in every
  model's training data — see
  [[library/syntheses/rediscovery-is-recall-under-contamination]].
