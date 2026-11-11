---
description: How the knowledge base is linted and each finding fixed. Use for rx check, dangling link, evidence tag, run record, lead scoring, dependabot drift.
---

> House skill — established by dz-runner setup mode from this repo's own evidence, then owned by its maintainers. Correct it in place; setup never overwrites a skill that exists.

1. From the repo root run `uv run tools/rx.py check`. `knowledge base clean` means the KB is fine; any other line names one problem and the exit code is 1.
2. `dangling link [[...]]` → the target file does not exist: create it with `uv run tools/rx.py new idea <slug>` (or `source`, `synthesis`) or fix the link.
3. `no evidence tags` in `library/sources`, `library/ideas` or `library/syntheses` → add `[source]`, `[lit]`, `[ours]` or `[open]` to that note.
4. `library/corpus/INDEX.md` row marked `noted` whose source note is missing → write the note at the referenced path or set the row back to `reading`/`unread`; a status outside `unread|reading|noted|skipped` is invalid.
5. Article finding: a cited `projects/...`, `library/...` or `tools/...` path that does not exist → fix the path; `no reference keys` → add an `ours:`, `corpus:`, `lit:` or `src:` key.
6. `run-record shape in explore/` → the JSON carries both `seed` and `metrics`: nothing in `explore/` is a result, so move it to `results/` or drop those keys.
7. Lead finding: `unscored axes` → score kill, novelty, discrimination and load; `marked promoted with no route recorded` → add a `## Route` section; `gated on ... but still open` → mark the lead dead.
8. `run record missing 'seed' | 'git_sha' | 'config'` → the run is not a result: re-run it through the project's provenance writer.
9. Dependency-update drift: a uv-managed project with no committed `uv.lock`, a Dependabot entry on another ecosystem, or a lock that no longer matches its manifest → `cd projects/NNN-slug && uv lock`, commit `uv.lock` beside the manifest, and keep the `.github/dependabot.yml` entry on ecosystem `uv` for that directory.
10. Re-run `uv run tools/rx.py check` until it is clean, then `uv run --with 'pytest==9.1.1' pytest tools/test_rx.py -q` — the pin follows the projects' lock; never let the gate's pytest float to latest.
