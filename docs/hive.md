# The hive — how agents are dispatched in this repo

This repo is an AI-first factory for research topics. Think of it as a room full of very
capable people working the same problem from different desks: one is downloading papers, one
is reading a thesis with a pen, two are arguing about whether the metric measures what it
claims, one is trying to break yesterday's result, and someone at the front is keeping track
of what is actually known. Agents do the acquiring, reading, decomposing, building, and
attacking. The coordinator holds the thread and decides what is true.

The pipeline is fixed; only the subject changes.

```
acquire ──► source ──► idea ──► synthesis ──► claim ──► experiment ──► verdict
(find and   (what it   (atomic,  (combine     (falsi-   (preregistered  (honest
 download)   said,      reusable) across       fiable)   seeded,          writeup)
             located)             sources)               baselined)
```

Each stage has an agent that owns it. The roster is shaped this way for one practical
reason: **parallel agents get disjoint files**, so fan-out needs no coordination and no
locking. One writer per path, always.

## Roster

Repo-wide, in `.claude/agents/`. Available from every project.

| Agent | Stage | Writes | Read-only |
|---|---|---|---|
| `lit-scout` | acquire + source | `library/corpus/`, `library/sources/*.md` | |
| `corpus-reader` | source | `library/sources/*.md` (one per document) | |
| `idea-extractor` | idea | `library/ideas/*.md` | |
| `synthesist` | synthesis | `library/syntheses/*.md` | |
| `decomposer` | claim | `projects/*/notes/decomposition-*.md` | |
| `preregistrar` | claim + experiment | `projects/*/notes/claim-*.md`, `projects/*/experiments/E*.md` | |
| `falsifier` | verdict | — | ✔ |
| `run-auditor` | verdict | — | ✔ |
| `lead-hunter` | discovery | `library/leads/*.md` | |
| `writer` | publication | `articles/*.md` | |

Project-scoped agents live in `projects/NNN-slug/.claude/agents/` and are discovered when
the working directory is inside that project. They own that project's source files.

| Project | Agent | Writes |
|---|---|---|
| 002 | `axiom-smith` | `src/ftlaxiom/systems.py`, `oracle.py`, their tests |
| 002 | `gr-toy` | `src/ftlaxiom/qei.py`, its tests |
| 002 | `contamination-auditor` | — (read-only) |

`lit-scout` and `corpus-reader` both write into `library/sources/`, but ownership there is
**per file**: one agent per document, one note per document. Two scouts never touch the same
slug. `library/corpus/INDEX.md` is the one shared file, so it has a single writer at a time —
in a fan-out, readers report their row's new status and the dispatcher applies it to the
existing row as a separate manual edit. `rx ingest` does not do this: it only appends
newly seen documents as `unread` rows and never rewrites an existing row, so status changes
are a single-writer manual step, not an `rx` command.

## The distillation chain

Raw material is heavy and gitignored; the distillate is light and committed.

| Layer | Committed | What it is |
|---|---|---|
| `library/corpus/` | no — index only | PDFs, theses, books. Copyrighted, large, and a contamination hazard if leaked |
| `library/corpus/INDEX.md` | yes | what we have, hashed, with a reading status |
| `library/sources/` | yes | what each document *said*, neutrally, with page locators |
| `library/ideas/` | yes | atomic, reusable, lifted out of the author's vocabulary |
| `library/syntheses/` | yes | positions no single source states |

Each layer is a compression of the one above with a different job. Skipping a layer — going
from a PDF straight to a claim — is how an unchecked paraphrase becomes a load-bearing fact.

## Why ideas are not filed per project

They are **cross-project property**. An idea from a 1980 physics book gets picked up by a
2026 ML experiment; that transfer is the point of the repo and it cannot happen if ideas are
buried under the project that first needed them. `library/` is shared, `projects/` is not.

What makes agents fast is not partitioning the library — it is one-writer-per-path plus a
short, specific brief. A narrow write surface is what lets five agents run at once without
reading each other's output.

## Dispatch patterns that work here

**Open a new subject.** `decomposer` first, to find out what the question actually is and
which parts are reachable on the hardware. Then several `lit-scout` calls in parallel, one
per sub-area, each downloading into the corpus and writing different source notes. Then
`rx ingest` once, then `corpus-reader` per queued document.

**Work the reading queue.** One `corpus-reader` per document, fanned out. Documents are
independent, notes are separate files, so this scales to whatever the machine allows. A book
is one agent's job, not five — page ranges within a document are sequential context, not
parallel work.

**Attack from different angles.** For a hard question, spawn agents with *different lenses*
rather than the same lens N times — mechanism, measurement, prior art, failure, cost,
reachability. Where lenses disagree is where the real uncertainty is; where they agree, one
of them was redundant. Same rule applies to verification: three refuters with distinct
angles beat five identical skeptics, because identical agents on one base model make
identical mistakes.

**Build an experiment.** `preregistrar` writes the doc, *then* project code agents implement
against it. Never the other way round: a metric chosen after seeing the data is not a
measurement, and the ordering is the only thing preventing it.

**Parallel build.** Project code agents own disjoint modules, so they run at the same time
with no interaction.

**Before believing a number.** `run-auditor` for provenance completeness, then `falsifier`
adversarially, then any project-specific auditor. All read-only, all parallelisable, none of
them able to quietly fix what they find — which is the point, because a fix by the finder
leaves no record that there was a problem.

**After a result, especially a null.** `lead-hunter` over the verdict, the run records, and
the "what this cannot conclude" section. A null is where the assumptions become visible;
`uv run tools/rx.py leads` is where the output lands, ranked and gated.

**When a finding is worth sharing.** `writer`, and only after `falsifier` and `run-auditor`
have both been through it. An article is the one artifact here aimed at someone who was not
in the room, so every factual sentence carries a reference key — `ours:` for our code and
measurements at a fixed SHA, `corpus:` for a document we hold **with a page locator**, `lit:`
for published work with its replication status, `src:` for what an interested party asserted.
A number that cannot be walked back to a committed run record does not go in. Neither does a
lead: leads are questions.

## The loop

The coordinator runs passes, not a single fan-out:

```
status/check/leads  ->  dispatch (parallel, disjoint, multi-angle)
        ^                              |
        |                              v
   re-dispatch  <-  audit (read-only)  <-  read what came back
```

Each pass should close a work item, kill a lead, or produce a new one. A pass that does none
of those is a signal to stop and say why — blocked on a decision, or the remaining work is
not worth its cost.

Two things the coordinator never delegates: **whether a number is believed**, and **the
verdict**. Agents report; the coordinator decides and writes it down with what it cannot
conclude.

## Rules that apply to every agent

- Tag every factual statement with an evidence class: `[source]` `[lit]` `[ours]` `[open]`.
- Falsifier before code. Preregister before the number exists.
- A page locator or it did not happen. A model can summarise a pre-cutoff paper fluently
  without opening it; the locator is what separates reading from recall.
- Never commit corpora, weights, or generated item sets.
- Never use git worktrees. Work in this checkout; disjoint files are the isolation
  mechanism.
- A read-only agent stays read-only. Do not grant Write to unblock it — the finding belongs
  to whoever owns the file.
- Report what actually happened, including "I found nothing" and "this did not run".
