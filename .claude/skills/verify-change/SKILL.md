---
description: Prove a change in developerz-ai/research before committing or opening a pull request — the repo's own install, run and check commands. Use before every commit.
---

# Verify a change in developerz-ai/research

> House skill — established by dz-runner setup mode from this repo’s own
> detected commands. Correct it in place; setup never overwrites a skill that exists.

## The one gate

`bin/check` is the gate. CI runs it and the pre-commit hook runs it, so a change that
passes it locally passes everywhere.

| Step | Command | What it is |
|------|---------|------------|
| install | `bin/setup` | (dpkg -s curl ca-certificates git >/dev/null 2>&1 \|\| (sudo -n apt-get update && sudo -n apt-get install -y --no-install-recommends curl ca-certificates git)) && curl -LsSf https://astral.sh/uv/install.sh \| sh && export PATH="$HOME/.local/bin:$PATH" && uv sync --extra dev --project projects/001-geometric-reasoning && uv sync --extra dev --project projects/002-ftl-axiom-search |
| run | `bin/dev` | export PATH="$HOME/.local/bin:$PATH" && uv run tools/rx.py doctor && uv run tools/rx.py projects && uv run tools/rx.py leads && (cd projects/001-geometric-reasoning && uv run geom doctor) && (cd projects/002-ftl-axiom-search && uv run ftl doctor) — on developerz.ai runs, start it with code_bash_background when you need a running stack |
| prove | `bin/check` | export PATH="$HOME/.local/bin:$PATH" && uv run tools/rx.py check && uv run --with pytest pytest tools/test_rx.py -q && (cd projects/001-geometric-reasoning && uv run --extra dev ruff check . && uv run --extra dev pytest -q) && (cd projects/002-ftl-axiom-search && uv run --extra dev ruff check . && uv run --extra dev pytest -q) |
| stop | `bin/stop` | true — on developerz.ai runs, the platform runs this when your session ends — do not stop the stack yourself |

## Rules

- Run every command from the repo root — the scripts `cd` there themselves.
- `bin/check` red is not a pull request. Fix the cause, never silence the gate.

## Exit codes `bin/check` must use

A coding box runs this gate before it commits, and it has to tell a FAILING change
from a gate it could not run — otherwise correct work is thrown away as if it were
red. Exit 1 cannot carry that difference, so two codes are reserved:

| Exit | Means | What the platform does |
|------|-------|------------------------|
| 0 | the change passes | commit it |
| 75 | a resource the gate NEEDS is unreachable (a database, a service, a credential) — it refused to grade | refuse the commit, and blame the environment, never the change |
| 79 | every check the gate ran PASSED, but it cannot grade the whole change here (a scoped gate meeting a change whose dependents are the whole suite) | commit it and open the pull request; CI grades the rest |
| any other non-zero | the gate ran and the change is red | refuse the commit, and blame the change |

- Guard preconditions FIRST and `exit 75` when one is unmet. `exit 1` there tells the
  platform your change is broken when it is your environment that is.
- `exit 79` only when every check you ran passed. Anything failed is `exit 1`;
  a deferral never hides a red.
- Changed a dependency? Re-run `bin/setup` before `bin/check`, or you are proving a stale tree.
- Add the test that fails first, then the fix — a green run that never went red proves nothing.
