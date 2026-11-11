---
description: How a new project is scaffolded and made runnable. Use for rx new-project, templates/project, dependabot entry, uv.lock, doctor, smoke.
---

> House skill — established by dz-runner setup mode from this repo's own evidence, then owned by its maintainers. Correct it in place; setup never overwrites a skill that exists.

1. From the repo root: `uv run tools/rx.py new-project "some subject"` → `projects/NNN-some-subject/` (number = creation order, never reused), rendered from `templates/project/`: `CLAUDE.md`, `README.md`, `pyproject.toml`, `src/<pkg>/{__init__,device,cli,provenance}.py`, `tests/test_scaffold.py`, plus `experiments/ notes/ results/ data/ explore/`.
   - The scaffolder self-validates; on failure it deletes the half-built directory and exits non-zero → fix `templates/project/` and re-run.
2. The scaffolder appends a `uv` entry to `.github/dependabot.yml` for the new directory and runs `uv lock` in it. If `uv.lock` is missing: `cd projects/NNN-slug && uv lock`, then commit `uv.lock` — `uv run tools/rx.py check` flags the missing lock until it exists.
3. For ROCm or a CPU-only box, edit the `pytorch` index URL in the project's `pyproject.toml` to `https://download.pytorch.org/whl/rocm6.2` or `https://download.pytorch.org/whl/cpu`, then `uv sync` and commit `pyproject.toml` together with `uv.lock`. A one-shot `uv sync --index` override is not persistent — later `uv run` re-syncs against the manifest.
4. `cd projects/NNN-slug && uv sync --extra dev` → creates `.venv` with pytest and ruff.
5. `uv run <slug> doctor` → prints backend, device and bf16 support; a CPU-only wheel on a GPU box is the silent failure this catches.
6. `uv run <slug> smoke` → under 60s, CPU end-to-end wiring check; run it after every change.
7. `uv run pytest -q` → the scaffold test; `uv run ruff check --fix .` for lint. Do not run `ruff format .` as a gate — the tree is not format-clean.
8. Write the project's `CLAUDE.md` start-here and claim sections, then preregister the first experiment before any measurement code: the first experiment's job is to kill the claim cheaply, under an hour, on CPU if possible.
