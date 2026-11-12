# Environment lock vs run records — the torch 2.14.1 drift

As of 2026-11-04; re-verified against this checkout on 2026-11-12. What drifted, why, why
the checker could not see it, and where it stands now. Every factual line is tagged with its
evidence class and carries `path:line` locators; counts and uniformity greps were run in
this session. No wiki-links: repo paths are cited as written (tools/rx.py:1011-1017 fails
any note link whose final stem is not a library/ file).

## Finding

46 of the 47 committed run records in this project were produced under **torch
2.13.0+cu126**, while the manifest and the lock now resolve **torch 2.14.1+cu126** — a
plain `uv sync` on this checkout builds an environment 46 recorded runs never used. The
2026-11-04 remedy (pin `torch==2.13.0`, regenerate the lock) closed that once; the pin was
later moved to `torch==2.14.1` (`pyproject.toml:7`) and the lock regenerated with it, so
**the drift is open again as of 2026-11-12** — the residual gap this note predicted has
materialised. The tree now holds records from two environments: 46 from the reference box
on torch 2.13.0+cu126, and one CPU run under the new pin.

## The recorded production environment

- 47 run records exist: 42 under `results/`, 5 under `results/superseded/`
  [ours: glob count over `results/**/*.json`, this session].
- 46 of them carry `"torch_version": "2.13.0+cu126"` at line 17 [ours: grep across all 47
  files, 46/47 hits at line 17, this session; e.g. `results/E001-gpt2-seed0.json:17`]. The
  47th, `results/E002-grid-completion.json:17`, carries `"2.14.1+cu126"`.
- Those same 46 uniformly record platform `"Windows 11"` (line 8), python `"3.12.13"`
  (line 10), accelerator `"NVIDIA GeForce RTX 3090"` (line 14), and a `timestamp_utc` dated
  2026-08-11 (line 4) [ours: four greps, 46/46 hits each at the stated line, this session;
  example locators `results/E001-gpt2-seed0.json:4`, `:8`, `:10`, `:14`].
- The exception is `results/E002-grid-completion.json`: Linux 6.8.0-147-generic, python
  3.14.10, accelerator backend `cpu` (no CUDA), `timestamp_utc` 2026-11-04T14:46:50,
  git_sha `94538e8-dirty` [ours: field read of that record, this session]. It is the first
  record in this project not produced on the reference box.
- Provenance chain of that field: `hardware.accelerator.torch_version` is
  `torch.__version__` captured at run time — set in `device.py:134` (DeviceInfo
  construction), serialised by `provenance.py:46` (`"accelerator": info.as_dict()`
  inside `hardware()`, `provenance.py:38-47`) [source]. It records the environment the
  run actually used, not the lockfile — which is exactly what makes drift like this
  measurable after the fact.

## The drift as found (2026-11-04)

- Pre-fix, `pyproject.toml:7` allowed `torch>=2.5`, and the committed `uv.lock` resolved
  torch 2.14.1+cu126 (torch package block's version line at `uv.lock:1057`), with wheels
  uploaded 2026-09-30 — after the 2026-08-11 runs [open: coordinator survey of this
  checkout on 2026-11-04, before the fix landed; those exact lines no longer exist in the
  tree because the files changed in this same cycle — the verified current state is under
  Remedy].
- `uv.lock` is committed because reproducibility is the whole point
  (`docs/toolchain.md:46`); a checkout whose lock cannot rebuild the recorded
  environment breaks that promise for all 46 records at once [ours].
- Scope of the break: under the inherited lock, `uv sync` could not reproduce any of
  the 46 recorded runs — not an approximation; a different torch version entirely.

## Why it drifted

- The project's dependencies are discovered by the weekly updater through the
  committed lock: ecosystem `uv`, directory `/projects/001-geometric-reasoning`,
  weekly Thursday 01:00 [source: `.github/dependabot.yml:18-29`; discovery-anchor
  table `docs/toolchain.md:50-58`, project row `:57`].
- The open range `torch>=2.5` made any newer torch a valid update target, so a
  routine minor bump legitimately walked past the version every record carries
  [open — which updater PR moved the lock lives on GitHub, not in this tree;
  delivery is unverified from a checkout per `docs/toolchain.md:64-71`].
- The 2026-11-04 fix replaced the range with an exact pin, which is what closed the
  drift — for one cycle. The manifest says as much itself: the pin constrains `uv sync`,
  but the updater can move it in a later PR [source: `pyproject.toml:30-33`]. It did: the
  pin is `torch==2.14.1` today, and `results/E002-grid-completion.json` was produced under
  it on 2026-11-04 [ours].

## Why the checker missed it

- `_lock_divergences` (`tools/rx.py:753-927`) reads exactly two files: the manifest
  and the lock, both parsed at `tools/rx.py:767-768` [source]. It compares
  requires-python (788-793), requires-dist specifiers (809-824), index sources in
  both directions (826-882), and extras (884-925). It never reads `results/`
  [source: function body, 753-927].
- `rx check` does scan run records — but only for JSON validity and the presence of
  `seed`, `git_sha`, `config` (`tools/rx.py:1067-1076`, field list at 1073, inside
  `_knowledge_base_problems`, `tools/rx.py:1000-1079`) [source]. No recorded
  environment field is ever compared against the lock. The check now also runs the test
  suites (`tools/rx.py:1100`) — that adds a red-suite gate, not an environment gate.
- So a lock that no longer matches any recorded run passes as long as it still
  describes the manifest: the checkout was green while unreproducible [ours:
  reading of the source, this session]. This drift class needs a check that reads
  `torch_version` out of the records; none existed, and none exists now.

## Remedy — what landed, and where it stands on 2026-11-12

- Landed 2026-11-04, since superseded: the manifest pinned `torch==2.13.0` and the lock
  was regenerated to resolve 2.13.0+cu126 from the pinned cu126 index, so the checkout
  could rebuild the recorded environment. A later bump to `torch==2.14.1` restored the
  drift this note opened on.
- Current state, verified 2026-11-12: `pyproject.toml:7` declares `torch==2.14.1`, with
  the rationale and the updater caveat in the adjacent comment [source:
  `pyproject.toml:30-33`].
- The lock resolves torch `2.14.1+cu126` from registry
  `https://download.pytorch.org/whl/cu126` [source: `uv.lock:1056-1058`], wheels
  uploaded 2026-09-30 [source: `uv.lock:1077-1096`] — after the 2026-08-11 runs, so the
  cp312 `win_amd64` wheel of the recorded platform [source: `uv.lock:1082`] is not the
  wheel those runs were produced from.
- The root package's requires-dist entry carries specifier `==2.14.1` and the cu126
  index URL [source: `uv.lock:165`]; no `2.13.0` reference remains anywhere in the
  lock [ours: grep over `uv.lock`, 0 hits, this session].
- Unchanged, deliberately: the explicit uv index entry `[tool.uv.index]` — name
  `pytorch`, url `https://download.pytorch.org/whl/cu126`, `explicit = true`
  [source: `pyproject.toml:40-43`] — and the `[tool.uv.sources]` torch mapping
  [source: `pyproject.toml:45-46`]. Backend overrides without a file edit
  (`pyproject.toml:35-37`) and the lock-vs-manifest index comparison
  (`tools/rx.py:826-882`) stay valid.
- The lock is regenerated by `uv lock` from the project directory — the checker's
  divergence messages carry a `(run 'uv lock')` remedy (`tools/rx.py:793`, `:824`, `:866`);
  hand-editing is not a route [source].

## Residual gap [open]

The checker still enforces the pin against the lock, but nothing ties the lock to the
*recorded* environment: a deliberate pin bump again yields a checkout unable to reproduce
historical records while passing every current check. That is not hypothetical here — the
bump reopened this exact drift, and `results/E002-grid-completion.json` is a run under the
new pin that every current check accepts. A guard comparing the lock's resolved torch
version against the dominant `torch_version` in `results/*.json` would close the class,
not just this instance — it would have flagged both the bump and the mixed-environment
record set. Lead material; deliberately not built here.

## What this note cannot conclude

- That the 2.14.1 lock ever reached a synced machine, or which updater PR moved it —
  that history is on GitHub, outside this tree [source: `docs/toolchain.md:64-71`].
- Anything about torch 2.14.1's behaviour on the reference hardware: no CUDA run in this
  tree used it. The one 2.14.1 record is a CPU run on Linux.
- The pre-fix locators (`pyproject.toml:7` = `torch>=2.5`; `uv.lock:1057` =
  `2.14.1+cu126`) come from the coordinator survey cited above and are not
  re-verifiable from this tree after the 2026-11-04 fix — those line numbers now carry
  different content. All "landed" locators are as of 2026-11-12 and re-verifiable by the
  greps named in this note.
