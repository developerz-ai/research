# The hive — how agents are dispatched in this repo

This repo is a factory for research topics. The pipeline is fixed; only the subject changes.

```
source ──► idea ──► synthesis ──► claim ──► experiment ──► verdict
```

Each stage has an agent that owns it. The reason the roster is shaped this way is not
specialisation for its own sake — it is that **parallel agents in this repo get disjoint
files**, so fan-out needs no coordination and no locking. One writer per path, always.

## Roster

Repo-wide, in `.claude/agents/`. Available from every project.

| Agent | Stage | Writes | Model |
|---|---|---|---|
| `lit-scout` | source | `library/sources/*.md` | sonnet |
| `idea-extractor` | idea | `library/ideas/*.md` | inherit |
| `synthesist` | synthesis | `library/syntheses/*.md` | inherit |
| `preregistrar` | claim + experiment | `projects/*/notes/claim-*.md`, `projects/*/experiments/E*.md` | inherit |
| `falsifier` | verdict | **nothing** — read-only | inherit |
| `run-auditor` | verdict | **nothing** — read-only | haiku |

Project-scoped agents live in `projects/NNN-slug/.claude/agents/` and are discovered when
the working directory is inside that project. They own that project's source files.

| Project | Agent | Writes |
|---|---|---|
| 002 | `axiom-smith` | `src/ftlaxiom/systems.py`, `oracle.py`, their tests |
| 002 | `gr-toy` | `src/ftlaxiom/qei.py`, its tests |
| 002 | `contamination-auditor` | nothing — read-only |

## Why ideas are not filed per project

They are **cross-project property**. An idea from a 1980 physics book gets picked up by a
2026 ML experiment; that transfer is the point of the repo and it cannot happen if ideas are
buried under the project that first needed them. `library/` is shared, `projects/` is not.

What makes agents *fast* is not partitioning the library — it is the one-writer-per-path
rule plus a short, specific brief. A narrow write surface is what lets five agents run at
once without reading each other's output.

## Dispatch patterns that work here

**Ingest a new subject.** `lit-scout` on the source, then `idea-extractor` on the resulting
note, then `synthesist` once two or more ideas exist. Sequential — each needs the previous
one's file.

**Prior-art sweep.** Several `lit-scout` calls in parallel, one per subfield, each writing a
different source note. Disjoint by construction.

**Build an experiment.** `preregistrar` writes the doc, *then* the project's code agents
implement against it. Never the other way round: a metric chosen after seeing the data is
not a measurement, and the ordering is the only thing that prevents it.

**Parallel build.** Project code agents own disjoint modules, so `axiom-smith` and `gr-toy`
run at the same time with no interaction.

**Before believing a number.** `run-auditor` for provenance completeness, then `falsifier`
adversarially, then a project-specific auditor if one exists. All read-only, all
parallelisable, none of them can quietly fix what they find — which is the point, because a
fix by the agent that found the problem leaves no record that there was one.

## Rules that apply to every agent

- Tag every factual statement with an evidence class: `[source]` `[lit]` `[ours]` `[open]`.
- Falsifier before code. Preregister before the number exists.
- Never use git worktrees. Work in this checkout; disjoint files are the isolation
  mechanism.
- A read-only agent stays read-only. Do not grant Write to unblock it — the finding belongs
  to whoever owns the file.
- Report what actually happened, including "I found nothing" and "this did not run".
