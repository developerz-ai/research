# Environment lock vs run records — the torch 2.14.1 drift

As of 2026-11-04. What drifted, why, why the checker could not see it, and what landed.
Every factual line is tagged with its evidence class and carries `path:line` locators;
counts and uniformity greps were run in this session. No wiki-links: repo paths are
cited as written (tools/rx.py:815-818 fails any note link whose final stem is not a
library/ file).

## Finding

All 46 committed run records in this project were produced under **torch 2.13.0+cu126**,
while the `uv.lock` this cycle inherited resolved **torch 2.14.1+cu126** — a plain
`uv sync` on that checkout built an environment no recorded run ever used. The drift is
closed as of this note: the manifest pins `torch==2.13.0` and the regenerated lock
resolves 2.13.0+cu126 from the pinned cu126 index.

## The recorded production environment

- 46 run records exist: 41 under `results/`, 5 under `results/superseded/`
  [ours: glob count over `results/**/*.json`, this session].
- Every one of the 46 carries `"torch_version": "2.13.0+cu126"` at line 17
  [ours: grep across all 46 files, 46/46 hits at line 17, this session; e.g.
  `results/E001-gpt2-seed0.json:17`].
- The same 46 files uniformly record platform `"Windows 11"` (line 8), python
  `"3.12.13"` (line 10), accelerator `"NVIDIA GeForce RTX 3090"` (line 14), and a
  `timestamp_utc` dated 2026-08-11 (line 4) [ours: four greps, 46/46 hits each at the
  stated line, this session; example locators `results/E001-gpt2-seed0.json:4`, `:8`,
  `:10`, `:14`].
- Provenance chain of that field: `hardware.accelerator.torch_version` is
  `torch.__version__` captured at run time — set in `device.py:134` (DeviceInfo
  construction), serialised by `provenance.py:46` (`"accelerator": info.as_dict()`
  inside `hardware()`, `provenance.py:38-47`) [source]. It records the environment the
  run actually used, not the lockfile — which is exactly what makes drift like this
  measurable after the fact.

## The drift as found

- Pre-fix, `pyproject.toml:7` allowed `torch>=2.5`, and the committed `uv.lock`
  resolved torch 2.14.1+cu126 (torch package block's version line at `uv.lock:1057`),
  with wheels uploaded 2026-09-30 — after the 2026-08-11 runs [open: coordinator
  survey of this checkout on 2026-11-04, before the fix landed; those exact lines no
  longer exist in the tree because the files changed in this same cycle — the verified
  current state is under Remedy].
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
  [open — which Dependabot PR moved the lock lives on GitHub, not in this tree;
  delivery is unverified from a checkout per `docs/toolchain.md:64-69`].

## Why the checker missed it

- `_lock_divergences` (`tools/rx.py:558-732`) reads exactly two files: the manifest
  and the lock, both parsed at `tools/rx.py:571-573` [source]. It compares
  requires-python (593-598), requires-dist specifiers (600-629), index sources in
  both directions (631-687), and extras (689-730). It never reads `results/`
  [source: function body, 558-732].
- `rx check` does scan run records — but only for JSON validity and the presence of
  `seed`, `git_sha`, `config` (`tools/rx.py:868-877`, field list at 874) [source].
  No recorded environment field is ever compared against the lock.
- So a lock that no longer matches any recorded run passes as long as it still
  describes the manifest: the checkout was green while unreproducible [ours:
  reading of the source, this session]. This drift class needs a check that reads
  `torch_version` out of the records; none existed.

## Remedy (landed this cycle, verified 2026-11-04)

- `pyproject.toml:7` now declares `torch==2.13.0` — the version every record
  carries — with the rationale in the adjacent comment, including the Dependabot
  pointer [source: `pyproject.toml:27-30`].
- The lock resolves torch `2.13.0+cu126` from registry
  `https://download.pytorch.org/whl/cu126` [source: `uv.lock:1059-1061`], including
  the cp312 `win_amd64` wheel of the recorded platform [source: `uv.lock:1084`,
  upload-time 2026-07-08 — predating every run record's 2026-08-11 timestamp,
  consistent with the records having been produced from exactly this wheel].
- The root package's requires-dist entry carries specifier `==2.13.0` and the cu126
  index URL [source: `uv.lock:168`]; no `2.14.1` reference remains anywhere in the
  lock [ours: grep over `uv.lock`, 0 hits, this session].
- Unchanged, deliberately: the explicit uv index entry `[tool.uv.index]` — name
  `pytorch`, url `https://download.pytorch.org/whl/cu126`, `explicit = true`
  [source: `pyproject.toml:37-40`] — and the `[tool.uv.sources]` torch mapping
  [source: `pyproject.toml:42-43`]. Backend overrides without a file edit
  (`pyproject.toml:32-34`) and the lock-vs-manifest index comparison
  (`tools/rx.py:643-687`) stay valid.
- The lock is regenerated by `uv lock` from the project directory — the checker's
  divergence messages all end `(run 'uv lock')` (`tools/rx.py:598`, `:629`, `:671`);
  hand-editing is not a route [source].

## Residual gap [open]

The checker now enforces the pin against the lock, but nothing ties the lock to the
*recorded* environment: a future deliberate pin bump would again yield a checkout
unable to reproduce historical records while passing every current check. A guard
comparing the lock's resolved torch version against the dominant `torch_version` in
`results/*.json` would close the class, not just this instance. Lead material;
deliberately not built here.

## What this note cannot conclude

- That the 2.14.1 lock ever reached a synced machine, or which Dependabot PR moved
  it — that history is on GitHub, outside this tree
  [source: `docs/toolchain.md:64-69`].
- Anything about torch 2.14.1's behaviour; no run here used it.
- The pre-fix locators (`pyproject.toml:7` = `torch>=2.5`; `uv.lock:1057` =
  `2.14.1+cu126`) come from the coordinator survey cited above and are not
  re-verifiable from this tree after this cycle's fix. All "landed" locators are as
  of 2026-11-04 and re-verifiable by the greps named in this note.
