# corpus — the raw pile

Drop PDFs, EPUBs, theses, papers, and books here. **Nothing in this directory is
committed except `README.md` and `INDEX.md`.**

```bash
uv run tools/rx.py ingest    # register new documents into INDEX.md
```

## Why the documents stay out of git

Three separate reasons, any one of which is sufficient:

- Repo rule: never commit raw corpora. A monorepo that carries a few hundred PDFs stops
  being clonable.
- Most of this material is copyrighted. Redistribution is not ours to do.
- A document committed here is a document that can leak into a future training set. This
  repo runs contamination-sensitive experiments; polluting the very corpora we test against
  would be an own goal.

`INDEX.md` is the committed artifact: it records *what we read*, with a hash, so a claim
sourced from page 214 of a thesis stays traceable without the thesis being in git.

## The reading queue

`INDEX.md` is a table with one row per document and a `status`:

| status | means |
|---|---|
| `unread` | registered, nobody has opened it |
| `reading` | an agent or a human is working through it now |
| `noted` | a source note exists in `library/sources/` — the note names the file and hash |
| `skipped` | opened, judged not worth a note. The reason belongs in the row |

`uv run tools/rx.py check` flags a row marked `noted` whose source note is missing, and any
unknown status.

## How documents get read

`corpus-reader` (see `docs/hive.md`) opens a document in page ranges, writes a source note
with **page locators on every load-bearing quote**, and flips the row to `noted`.

The locator discipline is not bureaucracy. A model asked about a paper published before its
cutoff can produce a fluent, confident, entirely-from-memory summary of it without opening
the file — and that summary will be right often enough to be dangerous. A page number is
checkable against the PDF; a recalled paraphrase is not. If a claim in a source note has no
locator, treat it as unverified regardless of how plausible it reads.
