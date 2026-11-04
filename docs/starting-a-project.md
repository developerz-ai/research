# Starting a project

```bash
uv run tools/rx.py new-project "geometric reasoning"
```

That creates `projects/NNN-geometric-reasoning/` — numbers are assigned in creation
order and never reused — rendered from `templates/project/` with the CLI name and the
underscore package name filled in:

- `CLAUDE.md` and `README.md`
- `pyproject.toml`: torch pinned to the PyTorch cu126 index (the default PyPI wheel is
  CPU-only and fails silently), a typer CLI, and a `dev` extra with pytest and ruff.
  `new-project` runs `uv lock` right there, so the lock exists before your first sync.
- `src/<pkg>/` with `device.py` (the only module allowed to name a vendor backend),
  `cli.py` (`doctor` + `smoke`), and `provenance.py` (run records)
- `tests/test_scaffold.py`, so `uv run pytest -q` has something real to run from day one
- the standard subdirectories: `experiments/`, `notes/`, `results/`, `data/`, `explore/`,
  `tests/`
- one appended `uv` entry in `.github/dependabot.yml`, so the weekly updater discovers
  the project

If `uv lock` could not run — offline, or no uv on PATH — the scaffolder says so, and
`uv run tools/rx.py check` keeps flagging the missing `uv.lock` until you generate and
commit it. That visibility is deliberate: a uv-managed project with no committed lock
is invisible to the updater.

First commands in the new project:

```bash
cd projects/NNN-geometric-reasoning
uv sync                # add --extra dev for pytest and ruff
uv run <slug> doctor   # verify the backend BEFORE anything else
```

## Before you write code

The ordering here is not bureaucratic — it is the part that makes a result mean something.

1. **Read the source properly and write the source note.** `rx new source <slug>`.
   Neutral record of what was said, with locators. Include the incentive paragraph.
2. **Extract ideas.** `rx new idea <slug>`. One per file, one sentence each, stated so they
   survive being lifted out of the source's vocabulary.
3. **Look for prior art.** Most "new" ideas have a literature under a different name.
   Finding it is usually cheaper than a GPU-week, and occasionally it has already been
   settled.
4. **Write the claim, with its falsifier.** `rx new claim <slug> --project NNN-slug`.
   If you cannot write the falsifier, you do not have a claim yet.
5. **Preregister the first experiment.** `rx new experiment <slug> --project NNN-slug`.
   Hypothesis, metric, threshold, baseline, confounds — all before the code exists.

Only then: build the thing.

## Sizing the first experiment

Aim for **under an hour**, on CPU if possible. The first experiment's job is to kill the
claim cheaply, not to settle it definitively. Most claims that are going to die die cheaply.

Ask: what is the smallest measurement whose outcome I would actually believe? Build that.

## Choosing a baseline

The most common way a result becomes unreadable is an unmatched baseline. Match on compute
budget and name which budget you matched — parameters, training tokens, wall-clock, or all
three.

"We compared against a model someone else trained" is almost never matched, and a
comparison against a model whose training data you do not know is not a controlled
comparison at all. If that is the best available, say so in the confounds section and
weaken the conclusion accordingly.

## Definition of done

A project is done when its `README.md` verdict section answers:

- Which claims survived, which died, which are still open?
- What is the strongest version of the result, stated with its uncertainty?
- What does this **not** conclude? Which regime was tested?
- What would the next experiment be?

A project can also close with "this could not be tested on available hardware" — that is a
legitimate outcome, provided the note says so plainly instead of substituting an easier
question and implying it answered the original one.
