# explore — scratch scripts, not results

Where agents try things. One-off scripts, quick probes, sanity checks, plots made to look at
rather than to publish, half-finished ideas that may not survive the afternoon.

Committed on purpose, so the coordinator can see what was already tried and nobody repeats
it. But:

> **Nothing in this directory is a result.** No number produced here may be quoted, put in a
> README, or used in a verdict.

A number becomes a result by coming out of a preregistered experiment, with a run record in
`results/` carrying seed, git SHA, hardware, full config, and per-item outputs. That is the
only path. Exploration that produces something interesting gets **rerun** through that path —
it does not get promoted by being written up confidently.

## Rules

- Name scripts for what they ask: `probe-deficit-from-per-item.py`, not `test2.py`.
- Put the finding in a sibling `.md` with the same stem, and say what would have to happen
  for it to become a claim. That file is what the coordinator reads.
- No output files here that look like run records. `rx check` will flag a `*.json` in this
  directory carrying `seed` and `metrics` keys — that shape belongs in `results/`.
- If a probe turns into something, hand it to `preregistrar` and let the experiment doc be
  written before the real run. A metric chosen after seeing an exploratory number is exactly
  the failure the preregistration exists to prevent, and "I already saw it in explore/" makes
  it worse, not better.
