# Claim — The FTL energy gap is a finite, quotable number

**ID:** `claim-qei-gap-is-finite`
**Added:** 2026-08-12
**Class:** `[open]`
**Descends from:** [[library/sources/ftl-agent-decomposition-chat]] C2

## Proposition

For an Alcubierre-type warp metric in 1+1D with wall thickness Δ and bubble velocity v, the
ratio

> R(Δ, v) = |negative energy the metric requires| / |negative energy a quantum energy
> inequality permits over the same sampling interval|

is finite and computable, and scales as a stated power of Δ and v — so the blocker can be
quoted as a number with an assumption list attached, rather than as the word "impossible".

## Falsifier

> This claim is dead if: R is undefined, divergent, or non-monotonic in Δ under every
> assumption set we can state — i.e. there is no finite ratio to quote, so the "gap" framing
> is wrong and the honest statement stays qualitative.

Also dead, in a more interesting way, if R ≤ 1 anywhere in the physically sensible parameter
range under assumptions we are willing to defend. That would be a result worth a great deal
of scrutiny and almost certainly indicates a bug — treat it as a bug until three independent
checks say otherwise.

## Operationalisation

| Term in the claim | How it is measured | What this choice could get wrong |
|---|---|---|
| "energy required" | integrate the stress-energy tensor computed from the 1+1D warp line element over the bubble wall region, in geometrised units | Reduced dimensionality changes the scaling exponents. A 1+1D number is not a 3+1D number and must never be quoted as one. |
| "energy permitted" | a Ford-Roman-type quantum energy inequality for a massless scalar field, evaluated on the same sampling interval | The QEI is field-, dimension-, and observer-dependent. Different field content gives a different bound; the choice must be stated with the number. |
| "the same sampling interval" | proper time along a chosen geodesic observer, fixed per run | The bound depends strongly on this. An unfavourable choice manufactures whichever answer is wanted — fix it in the preregistration. |
| "finite" | numerically stable to <1% across a grid refinement doubling | Divergence at the wall is expected analytically; the regulator used must be stated and its effect on R reported. |

## Current evidence

| Class | Evidence | Where |
|---|---|---|
| `[lit]` | Alcubierre (1994) metric; Ford-Roman quantum inequalities; Pfenning-Ford bounds on warp bubbles — all established, all report the requirement exceeding the allowance by many orders of magnitude | to be cited properly in E003's prior-art section |
| `[ours]` | none yet | — |

**Note the honest position of this claim:** the literature has already done the 3+1D version
and the answer is known to be enormous. This is a *reproduction*, and its value is that the
assumption list comes out explicit and machine-readable, as Track M's input. Reproducing a
known result and saying so is the correct framing; presenting it as new would not be.

## Cheap test first

1+1D, single wall thickness, single velocity, coarse grid, CPU, analytic cross-check against
the published closed form where one exists. Under an hour. If it does not reproduce the
published order of magnitude, the implementation is wrong — no interpretation until it does.

## Reachability

Yes for 1+1D and 2+1D toys on CPU/3090. **No** for 3+1D numerical relativity with adaptive
mesh refinement — out of scope, stated in `out-of-scope-ftl.md`.

## Status log

| Date | Class | Change |
|---|---|---|
| 2026-08-12 | `[open]` | created |
