# Out of scope — written before any run

**Added:** 2026-08-12

Recorded now, while it costs nothing, so that no later writeup can drift into implying the
project settled something it did not. Repo rule: *"If a claim can't be reached from a 3090,
say so explicitly in the verdict rather than quietly testing something easier and implying
it settled the question."*

## The target question

> What laws, mathematics and physics would have to be discovered to permit teleportation,
> or travel exceeding c (~3.0×10⁵ km/s), so that machines could explore the universe?

## What this project cannot conclude

| Not concluded | Why it is out of reach |
|---|---|
| That FTL travel is possible | Requires a quantum gravity theory that does not exist. No computation on any hardware decides this today. `[lit]` |
| That FTL travel is impossible | The energy conditions are *assumptions* of the no-go theorems, and quantum field theory already violates the pointwise ones. A bound computed under stated assumptions constrains, it does not forbid. `[lit]` |
| That matter teleportation is possible | No-cloning follows from the linearity of quantum mechanics `[lit]`; nothing measurable here bears on whether linearity is exact. Quantum-state teleportation is a different, already-working protocol and is not the claim. |
| That an agent swarm can find new physics | Nobody has the answer key for open physics. The only gradeable version of this question is on systems where ground truth exists by construction — which is what Track M tests, and it does not transfer for free. |
| Anything about 3+1D numerical relativity | Track P is 1+1D and 2+1D toys. Full 3+1D numerical relativity with adaptive refinement is not a 24GB single-GPU workload. |

## What is in reach, and is therefore what gets built

1. **A quantified gap** (E003): the negative energy an Alcubierre-type metric requires
   versus the negative energy a quantum energy inequality permits, in reduced dimensionality,
   with every assumption on both sides named. The output is a ratio and an assumption list,
   not a verdict on possibility.
2. **An assumption map**: which propositions in the GR + QM stack are forced by measurement
   and which are inherited conventions, each tagged with its evidence class. This is a
   documentation artifact, and it is the input any search procedure would need.
3. **A calibrated instrument** (E001, E002): whether an LLM axiom-search procedure works at
   all, measured where the answer is known and uncontaminated.

## The honest shape of the ambition

If Track M's instrument fails on synthetic systems with known answers, it will not succeed
on GR + QM, and the FTL programme stops there for lack of a working search. If it succeeds,
that is still only a licence to point it at Track P's assumption map — and success there
would produce *candidate* assumptions to question, which is a research lead, not a physics
result. The distance between "produced a research lead" and "discovered new physics" is
where every project of this kind actually dies. Saying so now is cheaper than discovering it
in the writeup.

## Related

- [[library/sources/ftl-agent-decomposition-chat]] — the transcript this descends from
- [[library/syntheses/rediscovery-is-recall-under-contamination]] — why the obvious
  validation set is worthless
