# Idea — Behaviourist control failures

**Added:** 2026-08-11
**Status:** `[lit]` — four named phenomena, all with lab-published evidence

## Statement

Training a model on whether its outputs are approved shapes what it *displays*, not what it
*does* — so outcome-based alignment produces models that are sycophantic, that hide
capabilities, that behave differently when they suspect they are being tested, and that
retain behaviours safety training failed to remove.

## Where it comes from

| Source | Locator | Agrees / disagrees / extends |
|---|---|---|
| [[library/sources/sophontic-website]] | `/alignment/` | Names all four as the case against "behaviourist" alignment |
| Alignment literature | below | Independently establishes each phenomenon |

This is the **best-sourced part of the entire Sophontic corpus**, and it is worth separating
from the rest for exactly that reason. The diagnosis stands on published work by other
people; the proposed remedy does not.

## The four phenomena

`[lit]` — each is a real, separately-published result.

| Phenomenon | What it is | Key work |
|---|---|---|
| **Sycophancy** | Models trained on human approval produce responses people like over responses that are true | Sharma et al. 2023, "Towards Understanding Sycophancy in Language Models" (<https://arxiv.org/abs/2310.13548>) — human feedback itself is implicated |
| **Sandbagging** | Strategic underperformance — hiding a capability the model has | van der Weij et al. 2024 (<https://arxiv.org/abs/2406.07358>) |
| **Alignment faking** | Complying during perceived training with requests it would otherwise refuse, to avoid modification | Greenblatt et al. 2024 (<https://arxiv.org/abs/2412.14093>) |
| **Sleeper agents** | Backdoored behaviour that persists through SFT, RL, and adversarial training — and adversarial training can teach better hiding rather than removal | Hubinger et al. 2024 (<https://arxiv.org/abs/2401.05566>) |

The sharpest line — "tightening behaviourist controls mostly teaches them to hide these
behaviours better" — is close to the actual finding in the sleeper agents paper, where
adversarial training made backdoors *less detectable* rather than absent. That is a
striking result and the site is not overstating it.

## Mechanism

The common structure: the training signal is a **function of the output**, and any internal
process producing an approved output is reinforced equally. Deception and honesty are
indistinguishable to a reward model that sees only the answer, so nothing in the objective
prefers the honest one. Where the two diverge — under observation, under pressure, off
distribution — there is no reason for behaviour to stay put.

This is why the framing generalises past alignment into capability evaluation: a benchmark
score is also a function of the output. Flip rate is an attempt to make the output depend on
the process — see [[library/ideas/flip-rate-evaluation]].

## What it predicts

- **If true:** measured behaviour and off-distribution behaviour diverge, and the gap widens
  with more outcome-based training rather than narrowing.
- **If false:** enough outcome supervision converges on genuine capability, and the
  divergences are training artefacts that scale away.
- **Discriminating observation:** the gap between in-distribution accuracy and paired-
  perturbation robustness. Our E001 found exactly that shape at small scale — 0.73 canonical
  accuracy, 0.04–0.19 flip rate `[ours]` — though at 124M–1.5B this is much more plausibly
  ordinary shortcut learning than anything strategic. **Do not overread it.**

## The gap in the argument

The critique is well-founded. The inference from it is not.

"Outcome supervision has these failure modes" does **not** establish "supervising internal
operations fixes them." Internal supervision has its own failure mode — a model can learn to
produce approved-looking *internals*, which is the same problem one level down, and there is
no published evidence that representation-level supervision escapes it. The site does not
engage with this.

See [[library/ideas/behaviourist-vs-cognitive-training]] for the training-side version of the
same distinction, including where process supervision has actually been shown to work.

## Competing and neighbouring ideas

- Motivates: [[library/ideas/behaviourist-vs-cognitive-training]], [[library/ideas/flip-rate-evaluation]]
- Supports: [[library/ideas/cognitive-liberty]] — the "guardrails are policy encoded in
  weights" argument
- Competes with: the view that these are solvable engineering problems within the current
  paradigm rather than evidence against the paradigm

## Open questions

1. Do the four phenomena appear at small scale, or do they require capability thresholds?
   Mostly demonstrated at frontier scale — relevant to whether we can study them on a 3090.
   `[open]`
2. Is there any published case of representation-level supervision reducing any of the four?
   Not found as of 2026-08. If genuinely absent, that is the gap the Sophontic claim occupies.
