---
description: How a claim and its preregistered experiment are written here. Use for rx new claim, rx new experiment, decision rule, threshold, seeds, baseline.
---

> House skill — established by dz-runner setup mode from this repo's own evidence, then owned by its maintainers. Correct it in place; setup never overwrites a skill that exists.

1. From the repo root create the claim: `uv run tools/rx.py new claim <slug> --project NNN-slug` → `projects/NNN-slug/notes/claim-<slug>.md`.
   - No concrete falsifier writable now → the claim is not a claim yet: leave it as an open question and stop.
2. Create the experiment doc: `uv run tools/rx.py new experiment <slug> --project NNN-slug` → `projects/NNN-slug/experiments/E00N-<slug>.md` (number = creation order, never reused).
3. Fill the Preregistration section before any code: hypothesis with direction and the alternative it discriminates against; metric with ties, refusals and malformed outputs, aggregation and uncertainty method; decision rule with numeric thresholds, effect size, item count and the reason for that count; baseline matched on a named budget (params, tokens, wall-clock); confounds (contamination, tokenizer, prompt format, item order, position and length bias, post-hoc item selection); runs planned with seeds, wall-clock and the CPU path at reduced `--limit`.
4. Implement inside the project: `cd projects/NNN-slug && uv sync --extra dev`, then `uv run <slug> doctor`, then `uv run <slug> smoke` (under 60s, CPU).
   - `doctor` reports a CPU-only wheel on a GPU box → `uv sync --index pytorch=https://download.pytorch.org/whl/cu126` (or `rocm6.2`), then make it persistent by editing the project's `pyproject.toml` index.
5. Run one seed per invocation and let the project write the record: `uv run <slug> <cmd> --seed 0 --out results/E00N-seed0.json`. The record carries seed, git SHA, hardware, config and per-item outputs.
   - `git_sha` is `unknown` → git is missing or this is not a repo: install git and re-run.
6. Run ≥3 seeds before believing a spread, then aggregate with the project's own commands (`uv run geom grid` reconciles the 24-cell depth grid; `uv run ftl falsify` compares fan-out against a single agent). There is no generic report command.
7. Write the Verdict section in the same experiment doc: claim status in the regime tested, what changed in beliefs, what it cannot conclude, which notes changed evidence class. Amend the preregistration only in the amendment log, with the reason.
8. Gate the change: `uv run tools/rx.py check` must print `knowledge base clean`, then `uv run --with 'pytest==9.2.0' pytest tools/test_rx.py -q` — pinned, like the projects' lock.
   - `check` reports a missing `uv.lock` → `cd projects/NNN-slug && uv lock` and commit it beside the manifest.
