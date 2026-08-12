# {{TITLE}}

**Written:** {{DATE}} · **Status:** draft | reviewed | published
**Survived:** `falsifier` (date) · `run-auditor` (date)

> One sentence: the finding, with its number and uncertainty.

---

## Finding

Three sentences at most. The number, its uncertainty, and the regime it holds in. A reader
who stops here should have the result and no wrong impression of it. If it is negative, say
so here. [ours:E00N]

## Why it matters

What was believed before — with a reference, not a straw man — and what changes. Two
paragraphs. [lit:key] [src:key]

## Method

Design, baseline and what it was matched on, item count, seeds. Link the preregistration:
the threshold being written first only counts if the reader can see that it was.
[ours:E00N-doc]

## Numbers

| Arm | Metric | CI | n | Run record |
|---|---|---|---|---|
| | | | | `projects/NNN-slug/results/....json` |

## What this does not show

Scope to the regime tested. Name what stayed uncontrolled and the objection you cannot
answer. Write it as a hostile reviewer would. If this section is hard to fill, the result is
not understood well enough to publish.

## Next

The experiment that would settle what this one could not, and roughly what it costs.

## Reproducing

```bash
```

Commands, seeds, hardware, git SHA. Any input that cannot be shared — a licensed corpus, a
paywalled document — is named, with what a reader can do instead.

---

## References

**Every factual sentence above carries a key.** A sentence with no key is opinion and does
not belong in an article. Keys are cheap; an unreferenced number is not.

### Ours — code and measurements

Repo paths at a fixed SHA, so a reader lands on the same bytes we did.

| Key | What | Where |
|---|---|---|
| `ours:E00N` | the measurement | `projects/NNN-slug/results/E00N-*.json` @ `<sha>` |
| `ours:E00N-doc` | the preregistration | `projects/NNN-slug/experiments/E00N-*.md` @ `<sha>` |
| `ours:impl` | the code that produced it | `projects/NNN-slug/src/pkg/module.py:LN` @ `<sha>` |

### Corpus — books, theses, papers we read

Page locators are mandatory. A claim sourced from a document we hold, without a page, is
unverifiable — and a model can produce a fluent summary of a pre-cutoff document without
opening it, which is precisely what the locator rules out.

| Key | Citation | Locator | Corpus |
|---|---|---|---|
| `corpus:author-year` | Author, *Title*, publisher/venue, year. DOI/ISBN | p. NN | `library/corpus/INDEX.md` sha `xxxxxxxxxxxx` |

### Literature — published external work

| Key | Citation | Peer reviewed | Replicated | Link |
|---|---|---|---|---|
| `lit:author-year` | | yes/no | yes/no/unknown | arXiv/DOI/URL |

### Sources — what someone asserted

Claims by a party with an interest in being believed. These stay `[source]` no matter how
often they are repeated.

| Key | Who, and what they gain | Locator | Note |
|---|---|---|---|
| `src:slug` | | 00:00 / p. NN | `library/sources/<slug>.md` |

---

**House style.** Concise. Lead with the finding. Cut every sentence that does not carry a
number, a reference, or a caveat — target under 1200 words before the reference tables.
Evidence classes are `[ours]` `[lit]` `[source]` `[open]`; see
[`docs/method.md`](../docs/method.md).
