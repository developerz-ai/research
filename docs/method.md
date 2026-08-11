# Method

How an idea travels through this repo, and what each stage owes the next one.

```
source ──► idea ──► synthesis ──► claim ──► experiment ──► verdict
```

The stages exist to stop one specific failure: reading something compelling, believing it,
and then building on it for months without ever checking. Each arrow is a place where a
claim has to earn its passage.

---

## 1. Source

**One file per book, paper, talk, interview, or video** in `library/sources/`.

A source note records *what was said*, faithfully, with locators (timestamp, page,
section). It is not the place for your opinion about whether it is true. Keep the two
apart — a source note you cannot trust to be neutral is useless as a reference later.

Include:
- Bibliographic detail and a stable link.
- Who is speaking and what their incentive is. A founder describing their own product is
  a different evidentiary object than an independent replication. Write that down.
- The claims, each with a locator.
- Direct quotes for anything load-bearing. Paraphrase drifts.

Template: [`templates/source.md`](../templates/source.md)

## 2. Idea

**One file per atomic idea** in `library/ideas/`.

An idea is the smallest reusable unit — a mechanism, a principle, a technique. It should
be statable in one sentence and should survive being lifted out of the source it came
from. If you cannot separate the idea from its author's framing, you have not finished
extracting it yet.

Ideas are cross-project property. The whole point is that an idea from a 1980 physics
book can be picked up by a 2026 ML experiment. Link liberally: `[[library/ideas/slug]]`.

Each idea note carries:
- The one-sentence statement.
- Which sources assert it, and whether they agree.
- What it would predict if true — this is what makes it reachable by experiment later.
- Nearby ideas it competes with or depends on.

Template: [`templates/idea.md`](../templates/idea.md)

## 3. Synthesis

**Combinations** in `library/syntheses/`.

This is the stage the repo exists for. A synthesis takes two or more ideas — usually from
sources that have never been read together — and states a position that neither source
states alone. Cross-domain is the norm, not the exception.

A synthesis is worth writing when it is *non-obvious* and *consequential*: it should change
what you would do or expect. "These two authors agree" is not a synthesis. "A's mechanism
explains why B's method fails in the regime B never tested" is.

Say plainly which parts are inherited from the sources and which part is yours. The new
part is the part that carries the risk.

## 4. Claim

A claim is a synthesis or idea sharpened until it can be **wrong**.

The test: can you write down, in advance, a measurement whose outcome would make you
abandon it? If not, it is not a claim yet. Park it under "open questions" and move on —
there is no shame in an idea that is not yet testable, only in pretending that it is.

A claim states:
- The proposition, in one sentence, with quantities where possible.
- The **falsifier**: the concrete result that kills it.
- The evidence class it currently sits at (`[source]`, `[lit]`, `[ours]`, `[open]`).
- What a *cheap* version of the test would look like. Prefer the cheap test first.

Beware claims that are technically falsifiable but practically unreachable ("this holds at
100B parameters"). Reformulate to something a 3090 can decide, or mark it explicitly as
out of reach and say so in the verdict.

Template: [`templates/claim.md`](../templates/claim.md)

## 5. Experiment

**Preregistered, seeded, baselined.** In `projects/NNN-slug/experiments/`.

Write the experiment document *before* the code that produces the number. It fixes:

- **Hypothesis** — which claim this tests, and the direction of the expected effect.
- **Metric** — exactly how it is computed, including how ties and failures are handled.
- **Decision rule** — the threshold, chosen in advance, with the effect size you care
  about and the number of items needed to see it. Choosing the threshold after seeing the
  data is how people fool themselves.
- **Baseline** — what this is being compared against, **matched on compute budget**
  (parameters, tokens seen, wall-clock, or all three; say which). An unmatched baseline
  makes a result unreadable.
- **Confounds** — what else could produce this number. Contamination, tokenizer effects,
  prompt formatting, and item-order effects are the usual suspects.

Then run it. Every run writes a record into `results/` containing seed, git SHA, hardware,
full config, and raw per-item outputs. Aggregate numbers without per-item data cannot be
re-analysed and are worth much less.

Report **uncertainty**. A single seed is an anecdote. Three seeds and a spread is a result.
Where the metric is a proportion over items, give a confidence interval.

Template: [`templates/experiment.md`](../templates/experiment.md)

## 6. Verdict

The writeup. It says which claims survived, which died, and which are still open, and it
updates the evidence class on the original claim and idea notes.

Rules:
- **Negative results are written up in full.** They are the most valuable thing in this
  repo, because nobody else publishes them.
- State what the experiment **cannot** conclude. Scope the finding to the regime tested.
- If a result surprised you, say what you believed before. That is the record of whether
  the method is working.
- Link back: verdict → experiment → claim → synthesis → idea → source. Someone should be
  able to walk from a number to the sentence in a book that started it.

---

## Evidence classes

Used inline in every note. They are the immune system of this repo.

| Tag | Means | Rule |
|---|---|---|
| `[source]` | The source asserts it | Cite file + locator. **Self-reported vendor numbers stay here permanently** unless independently replicated. |
| `[lit]` | Published external work supports it | Cite URL/arXiv. Note if it is peer reviewed and whether anyone replicated it. |
| `[ours]` | We measured it here | Cite experiment ID + results file. |
| `[open]` | Unverified | Fine to have. Not fine to build on silently. |

The most common failure mode in AI reading is a `[source]` claim quietly promoting itself
to background fact over a few weeks. Tagging is cheap; re-deriving what you believed and
why, six months later, is not.

## A note on hostile reading

Read generously enough to understand the strongest version of an argument, then test it
adversarially. Both halves matter. Dismissing an idea because its author uses unfamiliar
vocabulary is as much a failure as accepting it because the vocabulary is impressive —
and in AI, where philosophy and engineering claims routinely arrive in the same paragraph,
both failures are easy. Separate the two kinds of claim and test the engineering one.
