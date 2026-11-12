# Reviewer instructions — developerz-ai/research

> Read by the developerz.ai reviewer at EVERY review of this repository, at the reviewed
> commit, as this repo's own layer of the reviewer's prompt — established by dz-runner setup mode.
> It refines the platform rules (a finding is cited or withheld; the bot always discloses)
> and never overrides them. Edit freely; keep it under 12,000 characters — past that it is cut.

## Stack

Python 3.12 + uv + PyTorch. The gate is `bin/check` (`export PATH="$HOME/.local/bin:$PATH" && uv run tools/rx.py check && uv run --with pytest pytest tools/test_rx.py -q && (cd projects/001-geometric-reasoning && uv run --extra dev ruff check . && uv run --extra dev pytest -q) && (cd projects/002-ftl-axiom-search && uv run --extra dev ruff check . && uv run --extra dev pytest -q)`): a change that does not pass it is not proven, whatever its description says.

## Review conventions

- TODO(setup): the conventions a reviewer must hold this repo to (from CLAUDE.md / CONTRIBUTING), each as a rule.

## Gates that matter

- TODO(setup): which checks decide a change here, and what "proven" means for a pull request.

## Never flag

- TODO(setup): what never to flag — generated or vendored files, style a formatter owns, conventions this repo chose on purpose.
