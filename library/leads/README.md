# leads — things worth more research

The rest of the pipeline **verifies claims other people made**. This directory is where the
repo produces something of its own: observations that nobody has followed up, ranked by
whether following them up is worth it.

```
acquire ─► source ─► idea ─► synthesis ─► claim ─► experiment ─► verdict
                                   │                        │
                                   └────────► lead ◄────────┘
```

Leads come **out** of the pipeline as much as they go into it. A verdict — especially a null
one — is one of the richest sources of them.

## Where leads actually come from

In rough order of how often they turn out to be real:

| Origin | What it looks like |
|---|---|
| `our-null` | Something we measured did not do what it should have. Nulls are where the assumptions are visible. |
| `anomaly` | A number in our own results that nobody predicted and nobody has explained. |
| `contradiction` | Two sources that cannot both be right, and nobody has noticed they disagree. |
| `gap` | A claim everyone builds on that nobody has ever tested — usually because testing it is unglamorous. |
| `untested-assumption` | A step in a method that is never justified, only inherited. |

Notably absent: "an idea I had". Those are idea notes. A lead points at something that
already exists in the world or in our results.

## The scoring gate

Every lead is scored on four axes — `kill`, `novelty`, `discrimination`, `load` — and three
gates apply *before* the total means anything:

- **`kill = 0` is dead.** Not reachable on the reference hardware. Record it, say so, move on.
- **`discrimination = 0` is dead.** If only a positive result would be informative, it is a
  way to confirm a belief, not to find something out.
- **`novelty = 0` is dead**, unless the lead is explicitly a replication.

This is deliberately harsh, because the failure mode is not missing a good lead — it is a
queue of forty exciting entries that nobody can act on. A lead the gates kill has still done
its job by being written down.

## What a lead is not

- Not a hypothesis. It is an observation plus a reason to look closer.
- Not a claim. It has no falsifier yet; writing one is what promotion means.
- Not a project. Most leads die at the cheap check, which is the point.

## Workflow

```bash
uv run tools/rx.py new lead <slug>   # from templates/lead.md
uv run tools/rx.py leads             # the queue, ranked, gates applied
```

`lead-hunter` (see `docs/hive.md`) mines the corpus, the source notes, and `results/` for
new ones. `rx check` flags a lead marked `promoted` with no route recorded.

Dead leads stay in the directory. The record of what was ruled out, and why, is worth as
much as the queue — it is the only thing that stops the same lead being rediscovered every
six months.
