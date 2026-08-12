# articles — findings worth sharing

Most of this repo is written for us: source notes, preregistrations, run records, verdicts.
An article is the one artifact written for someone who was not in the room.

```bash
uv run tools/rx.py new article <slug>
```

## The bar

An article exists only when **all** of these are true:

1. **The finding survived attack.** `falsifier` went at it adversarially and it held;
   `run-auditor` confirmed the run records are complete. Both dates go in the header.
2. **Every number traces to a committed run record** — seed, git SHA, hardware, config,
   per-item outputs. A number in an article that cannot be walked back to `results/` is the
   single worst thing this repo could ship.
3. **It says what it cannot conclude**, in the article, in its own section, written as
   strongly as a hostile reviewer would write it. Not a footnote, not a hedge in the last
   paragraph.
4. **A reader could rebuild it** — commands, seeds, hardware, and an honest note about any
   input that cannot be shared.

## What earns one

- **A clean negative.** These are the most valuable things here, because almost nobody
  publishes them. A well-measured "this does not replicate" or "this mechanism does not
  predict what its proponents say it predicts" is worth more to a reader than another
  confirmation.
- **A surprise that survived.** Something we did not expect, that then withstood the boring
  explanations — bug, rounding, leverage, contamination.
- **A method result.** "This standard way of measuring X manufactures the effect" is a
  finding, and it usually generalises further than the experiment that revealed it.

## What does not earn one

- A **lead**. Leads are questions. `library/leads/` is where they live and they stay there
  until an experiment answers them.
- An **inconclusive** result. "We could not tell" is an honest verdict for the experiment
  doc and a bad article. If the inconclusiveness is itself the finding — the design cannot
  resolve the question — then write *that*, and be explicit that it is a claim about the
  method.
- Anything whose interesting part is the ambition rather than the measurement.

## Sharing

An article is a Markdown file first. It can be published as a shareable page when it is
finished and the bar above is met — never as a draft, and never before `falsifier` has been
through it, because a link outlives the caveats you meant to add later.

Keep the file as the source of truth. If a published copy and the file disagree, the file is
right and the copy is stale.
