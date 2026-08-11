# {{NUMBER}} — {{NAME}}

**Question:** (one sentence — the thing this project exists to find out)
**Status:** 🟡 active
**Started:** {{DATE}}

## Why this is worth testing

Where the idea came from, why it is non-obvious, and what changes if it turns out to be
true. Link the library notes: [[library/sources/...]], [[library/ideas/...]].

## Claims under test

| Claim | Falsifier | Class | Experiment |
|---|---|---|---|
| `claim-...` | | `[open]` | `E001` |

## Experiments

| ID | Question | Status | Verdict |
|---|---|---|---|
| E001 | | preregistered | — |

## Findings so far

Running summary. Keep it honest and keep it current — this is the section people read.

## Setup

```bash
uv sync
uv run {{SLUG}} doctor      # verify backend first
uv run {{SLUG}} --help
```

## Verdict

Filled in when the project closes. What survived, what died, what is still open, and what
the work cannot conclude.
