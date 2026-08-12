# Lead — {{TITLE}}

**ID:** `lead-{{SLUG}}`
**Added:** {{DATE}}
**Status:** `open` | `claimed` | `promoted` | `dead`
**Score:** kill=? novelty=? discrimination=? load=? (total ?)
**Origin:** anomaly | contradiction | gap | untested-assumption | our-null

## The observation

What was actually seen, with its evidence class and a locator. One paragraph. A lead that
cannot point at something concrete — a number, a quote with a page, a pair of sources that
disagree — is a hunch, and hunches go in the idea notes, not here.

## Why it is worth more research

The specific thing that is not known, and why not knowing it matters. Not "this is
interesting" — what breaks, or what would be believed differently, depending on the answer.

## What it would take to kill it

The cheapest measurement whose outcome you would believe, and its cost. This is the field
that decides whether the lead is real work or a wish.

## Score

| Axis | 0 | 1 | 2 | 3 | Ours |
|---|---|---|---|---|---|
| **kill** — cost to falsify | not reachable on this hardware | GPU-week | GPU-day | under an hour, CPU | |
| **novelty** — verified absence of prior art | known result | probably known | searched, nothing close | searched, and the absence is itself notable | |
| **discrimination** — do both outcomes inform? | only a positive is informative | weakly | yes | separates two live hypotheses cleanly | |
| **load** — what depends on it | nothing | a note | an experiment | a project's premise | |

**Gates, applied before the total means anything:**

- `kill = 0` → **dead**. Unreachable is unreachable; say so and move on.
- `discrimination = 0` → **dead**. A lead only a positive result could settle is a way to
  confirm something, not to find out.
- `novelty = 0` → **dead**, unless the point is replication, in which case say that plainly.

The total is a sort key for the queue. It is not a claim about truth, and a high total on a
lead nobody has searched prior art for is just enthusiasm with arithmetic on it.

## What would make this not a discovery

The boring explanation, written down now while it is cheap. Noise, a bug, an artefact of one
model family, a metric that is a rescaling of another, a known result under a different name.
Rank these by how likely they are — if the most likely one is "measurement bug", the first
work item is checking the measurement, not chasing the phenomenon.

## Prior art searched

`[lit]` — what was searched, where, and what came back. "Not searched yet" is an honest
entry and caps `novelty` at 1 until someone does it.

## Route

If promoted: which project, which claim, which experiment. If dead: why, and the date. A
dead lead stays in the file — the record of what was ruled out is worth as much as the queue.

## Log

| Date | Change |
|---|---|
| {{DATE}} | created |
