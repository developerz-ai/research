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
| install | `bin/setup` | bash. Debian/Ubuntu: apt-installs missing curl, ca-certificates, git (needs passwordless sudo). Windows Git Bash, RHEL or a box without sudo: that step is skipped — those tools must already be present. Everywhere: loads `.env`, activates `.githooks` via `git config core.hooksPath`, installs uv, syncs both project venvs |
| run | `bin/dev` | loads `.env`, then `uv run tools/rx.py doctor`, `projects`, `leads`, and each project's `<slug> doctor` — on developerz.ai runs, start it with code_bash_background when you need a running stack |
| prove | `bin/check` | `uv run tools/rx.py check` → the tools tests (pytest pinned to the projects' lock, not latest) → each project's ruff + pytest, one step per tool, every failure classified: environment (index unreachable) exits 75, a red change exits 1 |
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
| 75 | a resource the gate NEEDS is unreachable — it refused to grade. Implemented in `bin/check`: uv or git missing on PATH, or a step's output showing the package index/network was unreachable | refuse the commit, and blame the environment, never the change |
| 79 | every check the gate ran PASSED, but it cannot grade the whole change here (a scoped gate meeting a change whose dependents are the whole suite) — reserved: `bin/check` grades everything it defines and never emits 79 today | commit it and open the pull request; CI grades the rest |
| any other non-zero | the gate ran and the change is red | refuse the commit, and blame the change |

- Guard preconditions FIRST and `exit 75` when one is unmet. `exit 1` there tells the
  platform your change is broken when it is your environment that is. `bin/check`
  implements this: uv/git missing on PATH is 75, a step whose output shows the
  package index unreachable is 75, everything else that fails is 1.
- `exit 79` only when every check you ran passed. Anything failed is `exit 1`;
  a deferral never hides a red.
- Changed a dependency? Re-run `bin/setup` before `bin/check`, or you are proving a stale tree.
- Add the test that fails first, then the fix — a green run that never went red proves nothing.
