# Idea — Behaviourist vs cognitive training

**Added:** 2026-08-11
**Status:** `[lit]` for the distinction; `[open]` for the claimed advantage

## Statement

Training that rewards correct outputs shapes behaviour; training that supervises a model's
internal operations shapes cognition — and only the second reliably produces reasoning
rather than an imitation of it.

## Where it comes from

| Source | Locator | Agrees / disagrees / extends |
|---|---|---|
| [[library/sources/michels-sophontic-interview]] | 13:48, 36:09 (C8) | frames the industry as behaviourist and Sophontic as cognitive |
| Process supervision literature | see below | supports the weaker, well-tested version |

The psychology analogy (behaviourism vs cognitivism) is the speaker's background showing.
It is a genuinely useful framing — the distinction it points at is real and has an ML
literature — but the analogy is not itself evidence, and the strong version does not follow
from the weak one.

## Mechanism

- **Outcome supervision** — reward the final answer. The model is free to reach it any way
  that works, including shortcuts that generalise poorly. Reward hacking is the extreme case.
- **Process supervision** — reward the intermediate steps. Constrains *how* the answer is
  reached, not just what it is.
- **Representation supervision** — the strong version the source proposes: constrain the
  internal states directly, not merely the emitted reasoning trace. Auxiliary losses on
  hidden geometry would be an instance. This is the part with no public method attached.

Note the ladder: each rung constrains more of the computation and requires more supervision
signal. The source's proposal sits on the top rung, which is also the rung with the least
published evidence.

## What it predicts

- **If true:** models trained with internal-state supervision show better *robustness*
  (flip rate, out-of-distribution transfer) at equal accuracy — the gap appears in
  generalisation, not in-distribution performance.
- **If false:** internal supervision is an expensive regulariser whose benefit disappears
  once the outcome-supervised baseline gets the same compute.
- **Discriminating observation:** equal accuracy in-distribution, divergent flip rate on
  perturbed pairs. That combination is hard to explain any other way.

## Prior art

`[lit]`

- **Process supervision** — Lightman et al. 2023, "Let's Verify Step by Step",
  <https://arxiv.org/abs/2305.20050>. Process reward models beat outcome reward models on
  maths reasoning. This is real evidence for the *middle* rung.
- **Representation engineering** — Zou et al. 2023, <https://arxiv.org/abs/2310.01405>.
  Reading and steering internal representations; demonstrates internal states are
  manipulable and causally relevant.
- **Reward hacking / Goodhart** — the empirical case that outcome supervision alone is
  exploitable.
- **Latent/soft-thought reasoning (e.g. COCONUT)** — reasoning in continuous hidden space
  rather than tokens.

Process supervision working is good evidence for the framing and weak evidence for the
strong claim. Supervising *emitted steps* is not supervising *internal geometry*; the
source's method is the untested rung.

## Competing and neighbouring ideas

- Underpins: [[library/ideas/reasoning-as-internal-geometry]] — this is the training-side
  half of that claim.
- Measured by: [[library/ideas/flip-rate-evaluation]].
- Competes with: the bitter-lesson position — that hand-designed internal structure loses to
  general methods plus compute, every time, and that this is the most-replicated finding in
  the field. Any experiment here should be read as a test against that prior, not against
  a strawman.

## Open questions

1. Does an auxiliary loss on hidden-state geometry improve flip rate at matched compute? `[open]`
2. Is there a cheap internal supervision signal, or does it require labels nobody has?
3. Does the benefit survive scaling, or is it a small-model crutch that vanishes with data?
