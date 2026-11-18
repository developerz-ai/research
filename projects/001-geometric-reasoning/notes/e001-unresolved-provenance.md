# E001 — the producing commit is unresolved

As of 2026-11-12. What the 12 E001 run records say about the code that produced them, what
was inspected to establish it, and what cannot be established from this checkout. Every
factual line carries an evidence class and a `path:line` locator; counts and greps were run
in this session. No wiki-links: `tools/rx.py:1058-1061` fails any note link whose final stem
is not a `library/` file, so paths are cited as written.

## Finding

The E001 measurements are intact and their provenance is not. All 12 records carry
`"git_sha": "unknown"` at line 5, and no record anywhere in this tree names the commit that
produced them [ours: `grep -n '"git_sha"' results/E001-gpt2*.json` — 12/12 files hit at line
5, this session; e.g. `results/E001-gpt2-seed0.json:5`].

That string is not a recorded revision that later went missing. It is the fallback value
`provenance.git_sha()` returns when `git rev-parse --short HEAD` or `git status --porcelain`
fails — `except (subprocess.CalledProcessError, FileNotFoundError): return "unknown"`
(`src/geomreason/provenance.py:21-35`, fallback at `:34-35`) — and `RunRecord.write` writes it
verbatim into every record (`src/geomreason/provenance.py:74`) [source]. A run made from an
exported tree, a container without `.git`, or a machine without git on `PATH` therefore
records `"unknown"` and everything else about the run normally.

## What survives as provenance

- **Timestamps.** The 12 records span `2026-08-11T16:00:02+00:00` to
  `2026-08-11T16:01:12+00:00` — a ~70-second sweep, consistent with the one box doing 12
  model × seed runs back to back [ours: `grep -n '"timestamp_utc"'
  results/E001-gpt2*.json`, 12 hits at line 4, this session; e.g.
  `results/E001-gpt2-seed0.json:4`].
- **Hardware and software.** All 12 record `"platform": "Windows 11"` (line 8), platform
  python `"3.12.13"` (line 10), accelerator name `"NVIDIA GeForce RTX 3090"` (line 14) and
  `"torch_version": "2.13.0+cu126"` (line 17) [ours: field reads of
  `results/E001-gpt2-seed0.json:8`, `:10`, `:14`, `:17`, this session; the uniform `2.13.0+cu126`
  across the record set is counted in `notes/env-lock-vs-run-records.md`].
- **Full re-run material.** `seed`, `config` (model, `n_params`, `n_per_family`,
  `n_pairs`, scoring options) and per-item outputs are present in every record, so the
  numbers can be re-analysed without the producing commit [ours: field presence across the 12
  files, this session].

Together that is enough to say *what environment* produced the numbers and *how to
re-run* them; it is not enough to say *which code*.

## What was inspected, and why it does not close the gap

- **The records themselves.** `git_sha` is `"unknown"` in all 12; `notes` said nothing about
  it in the versions this audit started from [ours: `grep -n '"notes"' results/E001-gpt2*.json`,
  12 hits at line 143 with `"notes": ""`, this session]. They now carry the resolution
  statement in `notes` at that line; the metrics, items, config and hardware blocks were
  not touched.
- **The experiment doc.** `experiments/E001-flip-rate-across-scale.md` previously said the
  SHA was "recorded automatically in each run record" — an implication that a revision
  existed somewhere. It did not name one, and the claim is now replaced with this finding
  (Amendment log, 2026-11-12).
- **The other records in this project.** No other record's `git_sha` names E001's commit.
  The only hex revisions anywhere in the project are `94538e8-dirty`
  (`results/E002-grid-completion.json`), `71f65c7-dirty`
  (`results/superseded/E001c-HuggingFaceTB_nanowhale-100m-base-seed0.json`), and
  `b88d033-dirty` (`results/E002-*.json`), and none is offered by any document as E001's
  producing tree [ours: `grep -rn 'git_sha'
  results/` and doc search of `experiments/`, this session].
- **Git history.** Not reachable from this run — the run has no git, and `results/` is
  append-only, so nothing here can be resolved by looking backward at the tree [open].

## Scope note: the superseded records

Four `results/superseded/E001-*` records carry the same `"git_sha": "unknown"` at line 5
[ours: grep over `results/superseded/*.json` — 4 of its 5 files, all at line 5, this session;
`results/superseded/E001-gpt2-seed0.json:5`]. They are the discarded first seed-0 sweep
(see the 2026-08-11 amendment rows for the `role_swap` defect) and they are **outside** the
`rx check` run-record glob `results/*.json`, which is one level deep
(`tools/rx.py:1111`) [source]. They are left byte-identical here, as results are
append-only (`src/geomreason/provenance.py:61-68`), so the checker's new `git_sha` value
check does not and should not report them.

## Consequence

`rx check` identifies `git_sha: "unknown"` as invalid provenance
(`tools/rx.py:1024-1039`), then reports these 12 records as non-failing warnings because each
record's `notes` accepts the gap in writing. The warning is the correct state: it keeps the
genuine gap visible without claiming the check fails. Re-running E001 from a tracked checkout
would close it for future records; it cannot repair these 12, whose code is gone from the
record.

## What this note cannot conclude

- **Which commit produced E001.** Nothing in this tree names it and git history is not
  reachable here [open]. No SHA is written for E001 in this note, and none should be
  inferred.
- **Whether the tree E001 ran from was dirty.** The `"unknown"` fallback fires before the
  dirty check can run, so the usual `-dirty` signal is absent rather than negative [source:
  `src/geomreason/provenance.py:24-33`].
- **Whether the recorded environment can be rebuilt exactly.** That is the separate concern
  of `notes/env-lock-vs-run-records.md`: the lock now resolves torch 2.14.1+cu126, while
  these 12 records were produced under 2.13.0+cu126.
- **Anything about the measurements themselves.** This note is about provenance only. The
  E001 verdict, including its negative result, is unchanged and stands on its own analysis.
