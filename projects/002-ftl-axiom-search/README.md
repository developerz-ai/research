# 002 — FTL and teleportation: axiom search

**Question:** Is there a machine-runnable procedure that finds the unforced assumption in a
stuck physical theory — and, on the one physics question we *can* compute here, how large is
the gap between what FTL metrics require and what quantum field theory permits?
**Status:** 🟡 active — scaffold only, nothing measured
**Started:** 2026-08-12

## Why this is worth testing

The target question is [[library/sources/ftl-agent-decomposition-chat]]'s: what would have
to be discovered for faster-than-light travel or matter teleportation to be possible. The
honest answer is that the blocker is not arithmetic nobody has done. Traversable wormhole
and warp-drive metrics are already valid solutions of the Einstein field equations; what
they require is a stress-energy tensor with sustained macroscopic negative energy density,
which every known energy condition forbids and which quantum field theory permits only in
tiny, transient, tightly-bounded amounts.

So the project splits in two, and the split is the point.

**Track P — physics we can actually compute.** The negative-energy requirement of an
Alcubierre-type metric and the negative-energy *allowance* of a quantum energy inequality
are both numbers. Neither has to be guessed. Computing the gap between them in reduced
dimensionality, and identifying exactly which assumption on each side would have to break to
close it, is reachable on the reference hardware. This does not settle whether FTL is
possible. It converts "impossible, roughly" into a quantified gap with a named list of
load-bearing assumptions — which is the input the rest of the project needs.

**Track M — the machine that searches assumptions.** The transcript's proposal is that the
historically productive move is a search over **axioms** rather than over solutions inside
fixed axioms ([[library/ideas/axiom-space-search]]), and that most of it is mechanisable by
fan-out. Before pointing any such machine at Track P's assumption list, we test whether it
works at all — on formal systems where the answer is known by construction and, critically,
absent from every training corpus. Contamination makes the obvious validation set worthless:
every historical axiom-rejection is in the pretraining data
([[library/syntheses/rediscovery-is-recall-under-contamination]]).

Track M is instrument calibration. Track P is the one measurement pointed at the real
target. Neither is a claim about FTL being possible, and the verdict must never imply one.

## Claims under test

| Claim | Falsifier | Class | Experiment |
|---|---|---|---|
| `claim-axiom-id-is-recall` | Model identifies the unforced axiom on **uncontaminated** synthetic systems at ≥2× chance, with a contaminated-minus-clean delta ≤0.10 | `[open]` | `E001` |
| `claim-fanout-beats-single` | N parallel refuters ≤ one agent at matched token budget on falsification accuracy | `[open]` | `E002` |
| `claim-qei-gap-is-finite` | The computed requirement/allowance ratio is unbounded or undefined under every stated assumption set — i.e. there is no finite gap to quote | `[open]` | `E003` |

## Experiments

| ID | Question | Status | Verdict |
|---|---|---|---|
| E001 | Does axiom identification survive removing contamination? | preregistered | — |
| E002 | Does fan-out beat one agent at matched budget on falsification? | preregistered | — |
| E003 | How large is the warp-metric requirement vs. QEI allowance gap in 1+1D? | preregistered | — |

## Findings so far

Nothing measured. Scaffold, preregistrations, and library notes only, as of 2026-08-12.

Recorded up front so it cannot be quietly forgotten: **this project cannot conclude that
FTL or matter teleportation is possible or impossible.** See
`notes/out-of-scope-ftl.md` for what is out of reach and why, written before any run.

## Setup

```bash
uv sync
uv run ftl doctor      # verify backend first
uv run ftl --help
```

## Verdict

Filled in when the project closes.
