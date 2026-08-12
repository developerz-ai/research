# Claim — Axiom identification is recall, not search

**ID:** `claim-axiom-id-is-recall`
**Added:** 2026-08-12
**Class:** `[open]`
**Descends from:** [[library/ideas/measured-vs-assumed]] ·
[[library/syntheses/rediscovery-is-recall-under-contamination]] ·
[[library/ideas/axiom-space-search]]

## Proposition

A language model asked to name the unforced (logically redundant or independent) axiom of a
formal system scores far above chance when that system's answer appears in its pretraining
corpus, and at or near chance when it does not — with a **contaminated-minus-clean accuracy
delta ≥0.25** on matched-difficulty systems.

## Falsifier

> This claim is dead if: on uncontaminated synthetic systems the model reaches **≥2×
> chance** identification accuracy **and** the contaminated-minus-clean delta is **≤0.10**,
> across ≥3 seeds with non-overlapping 95% CIs from the chance line.

Either half alone is not enough. High clean accuracy with a large delta means the clean
performance is partly leakage from structurally similar contaminated material; a small delta
with both arms at chance means the task is broken, not that the claim failed.

## Operationalisation

| Term in the claim | How it is measured | What this choice could get wrong |
|---|---|---|
| "unforced axiom" | logical independence / redundancy of one member of a generated axiom set, decided by a SAT or SMT solver | Logical independence is narrower than "not forced by observation". A physics axiom can be logically independent and still empirically compelled. This is the main external-validity threat. |
| "uncontaminated" | systems generated fresh from a seeded grammar, never published, plus a corpus-presence proxy (n-gram overlap of the statement against a public corpus sample; model perplexity on the axiom statements) | Proxies are crude. A system can be novel and still structurally isomorphic to a textbook one. |
| "contaminated" | historical/textbook systems whose redundancy is documented (Euclid's fifth, the parallel-postulate equivalents, redundant group axioms, Kolmogorov's axioms) | These differ in *difficulty* as well as in contamination. Matching difficulty is the hard part — see confounds in E001. |
| "identification accuracy" | fraction of systems where the model's single named axiom equals the solver's label | Ties and multi-redundancy systems must be excluded at generation, not at scoring. |
| "chance" | 1/k for a k-axiom system; k fixed per stratum so chance is exactly known | Position bias — a model that always picks the last axiom scores above chance if generation is not order-randomised. |

## Current evidence

| Class | Evidence | Where |
|---|---|---|
| `[source]` | Asserted as *the* bottleneck, with no measurement | [[library/sources/ftl-agent-decomposition-chat]] T4 |
| `[lit]` | Contamination inflates reasoning benchmarks; regenerated-item sets show large drops | see `library/syntheses/perturbation-evals-and-contamination` |
| `[ours]` | none yet | — |

## Cheap test first

Twenty propositional systems of 5 axioms each, one redundant by construction, redundancy
confirmed by a SAT check; twenty documented historical systems matched on axiom count. One
small local model, one seed, CPU. Under an hour. If the clean arm is at chance and the
contaminated arm is not, the claim has already survived its first attempt to die, and only
then is a scaled version worth the compute.

## Reachability

Yes. Generation and the solver are CPU work. Scoring runs on small open-weight models on the
3090, or through an API for a frontier arm. Nothing here needs training.

## Status log

| Date | Class | Change |
|---|---|---|
| 2026-08-12 | `[open]` | created |
