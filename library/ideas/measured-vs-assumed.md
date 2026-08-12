# Idea — Distinguishing what is measured from what is inherited

**Added:** 2026-08-12
**Status:** `[open]`

## Statement

The load-bearing capability for theory revision is telling apart a proposition that some
observation forces from one that has merely been assumed continuously for long enough to
read as a fact — and a model trained on the text of a settled theory has no signal that
separates the two, because both appear in the same declarative voice.

## Where it comes from

| Source | Locator | Agrees / disagrees / extends |
|---|---|---|
| [[library/sources/ftl-agent-decomposition-chat]] | T4, C5 | Names it as *the* bottleneck; offers no test |

## Mechanism

Textbooks state axioms and empirical results in identical grammar. "Simultaneity is
absolute" and "light travels at c in vacuum" are both flat assertions on the page; nothing
in the surface form marks one as an unforced convention and the other as forced by
Michelson-Morley. A next-token model absorbs the distribution of assertions, not their
epistemic status, so its estimate of "is this droppable" is dominated by how often the text
says it and how confidently — which is exactly backwards, since the most-repeated and
least-hedged propositions are the conventions nobody has thought to question.

If this mechanism is right, the failure is specifically *asymmetric*: models should be good
at flagging assumptions that the literature already discusses as assumptions (locality,
unitarity, background independence — all named as such in thousands of papers) and bad at
flagging ones that no text marks. The first is retrieval. Only the second is the capability
being claimed.

## What it predicts

- **If true:** on a formal system whose redundant/unforced axiom is *not* discussed
  anywhere in the training corpus, model identification of that axiom sits near chance,
  while on systems whose answer is documented it sits far above chance. The gap between
  those two conditions is the size of the illusion.
- **If false:** identification accuracy is roughly the same in both conditions, meaning the
  model is doing something other than recall — some structural sensitivity to how the axiom
  participates in derivations.
- **Discriminating observation:** the **contaminated-minus-clean accuracy delta**. Absolute
  accuracy on either condition alone is uninterpretable; only the delta separates recall
  from search. This is the same design logic as
  [[library/syntheses/perturbation-evals-and-contamination]] and
  [[library/ideas/flip-rate-evaluation]].

## Prior art

`[lit]` — memorisation-vs-generalisation and benchmark contamination have a large
literature (n-gram overlap detection, member-inference on pretraining data, the
GSM8K→GSM1k regeneration result). `[open]` — none of it is applied to *epistemic status of
a proposition* as the target label, which is what this idea needs.
`[lit]` — closest philosophical framing is Quine's under-determination and the
Duhem-Quine thesis: which auxiliary hypothesis to reject is not fixed by the evidence. If
Duhem-Quine is right in the strong form, this idea's target label may not be well-defined
for real theories — which is a reason to test it first on synthetic systems where the
answer *is* well-defined by construction.

## Competing and neighbouring ideas

- Depends on: nothing — this is the floor. If it fails, [[library/ideas/axiom-space-search]]
  has no automatable first stage.
- Competes with: the view that scale alone fixes this, i.e. that a large enough model
  induces epistemic status from context (proofs cite axioms differently than they cite
  lemmas). That is a real alternative and the experiment should be able to see it as a
  scale trend.
- Neighbours: [[library/ideas/tokenization-limits-reasoning]] — both are claims that a
  surface property of training text caps a reasoning capability.

## Open questions

- Is there a *syntactic* proxy for epistemic status in real corpora (citation shape, hedging
  density) that a model could plausibly have picked up? If so, "recall" and "search" are
  less cleanly separable than the design assumes.
- On a synthetic system, does "unforced" even mean the same thing it means in physics? The
  synthetic analogue is logical independence, which is narrower. State this limit in any
  verdict.
