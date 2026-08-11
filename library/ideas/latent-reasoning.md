# Idea — Latent reasoning

**Added:** 2026-08-11
**Status:** `[lit]` — an active, published research programme

## Statement

A model can reason in its continuous hidden space instead of in emitted tokens, feeding
hidden states back as inputs — which decouples "thinking time" from sequence length and lets
a single state hold several candidate steps at once.

## Why it matters here

This is **the closest thing in the peer-reviewed literature to what Sophontic describes**,
and it is nobody's metaphysics. If "reasoning happens in latent space and can be engineered
there" has a mainstream form, this is it — with methods, baselines, and numbers.

Anyone evaluating the geometric-reasoning claim should read this literature first. It shows
the general idea is taken seriously, and it shows what taking it seriously looks like when
the claims come with evidence.

## Mechanism

Standard chain-of-thought forces every intermediate step through the token bottleneck: the
model must commit to one discrete token, discarding the rest of the distribution. Latent
reasoning removes that commitment.

- **COCONUT** (Hao et al. 2024, <https://arxiv.org/abs/2412.06769>) — "chain of continuous
  thought": the last hidden state is fed back as the next input embedding instead of being
  decoded. The continuous state can encode **multiple alternative next steps at once**,
  giving something like breadth-first search where CoT does depth-first with early commitment.
- **Reasoning by superposition** (<https://arxiv.org/abs/2505.12514>) — theoretical account
  of why that works: a continuous thought holds a superposition of reasoning paths.
- Follow-on work covers latent-thinking reward signals, hidden-state recurrence with on-policy
  RL, sparse-transcoder views of latent reasoning, and detecting misaligned reasoning in
  continuous-thought models.

That last one is worth noting: latent reasoning **removes the readable trace**, which is a
real safety cost. The field is already working on it. It is also a direct tension with
[[library/ideas/behaviourist-control-failures]] — reasoning you cannot read is reasoning you
cannot supervise.

## What it predicts

- **If true:** latent reasoning beats token CoT at matched compute on tasks needing search
  or backtracking, and the advantage grows with branching factor.
- **If false:** the token bottleneck is a useful regulariser and continuous states drift.
- **Discriminating observation:** tasks with high branching where CoT must commit early.
  COCONUT reports exactly this pattern.

## How this relates to the geometric-reasoning claim

Both say the interesting computation happens in continuous internal space rather than in
emitted tokens. The differences are what matter:

| | Latent reasoning `[lit]` | Geometric reasoning `[source]` |
|---|---|---|
| Mechanism | Feed hidden states back as inputs | "Train the internal geometry" — unspecified |
| Definition | Precise, implementable | "Geometric density" undefined |
| Evidence | Published, with baselines | None public |
| Claim size | Better use of compute at a given scale | 60×–1000× smaller beats larger |

The honest summary: **the general direction has real support; the specific claim has none.**
That is a much more useful position than either "it's nonsense" or "it's the future".

## Competing and neighbouring ideas

- Neighbour and mainstream counterpart to: [[library/ideas/reasoning-as-internal-geometry]]
- Constrained by: [[library/ideas/token-geometry-and-anisotropy]] — continuous states inherit
  the cone
- In tension with: [[library/ideas/behaviourist-control-failures]] — unreadable reasoning
  cannot be process-supervised

## Open questions

1. Does latent reasoning change the geometric descriptors we measure? Would be a direct
   bridge between the `[lit]` mechanism and the `[source]` claim. `[open]`
2. Are there latent-reasoning results at ≤1.5B that we could reproduce on one GPU?
3. Does latent reasoning improve **flip rate**, or only accuracy? Nobody has reported it, and
   we now have the harness to ask.
