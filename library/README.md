# Library

The cross-project knowledge layer. Projects come and go; this accumulates.

| Directory | One file per | Answers |
|---|---|---|
| `sources/` | book, paper, talk, interview, video | *What was said?* |
| `ideas/` | atomic idea | *What is the reusable mechanism?* |
| `syntheses/` | combination across sources | *What follows that nobody stated?* |

## Rules

- **Sources are neutral.** They record what was said, with locators, plus who benefits if
  you believe it. Your assessment goes in the idea or claim note, not here.
- **Ideas are atomic and portable.** One sentence, statable without the author's
  vocabulary. If it cannot be lifted out of its source, extraction is not finished.
- **Syntheses carry the risk.** Mark clearly which parts are inherited and which part is
  new. The new part is the reason the file exists.
- **Every note carries evidence tags** (`[source]`, `[lit]`, `[ours]`, `[open]`).
  `uv run tools/rx.py check` fails on notes that have none.
- **Link liberally** with double-bracket wiki links to note slugs. A dangling link marks work to do rather
  than an error, but `rx check` will list it so it does not get forgotten.

## Why ideas are separated from sources

So that an idea from a 1980 physics book can be picked up by a 2026 ML experiment without
dragging its original framing along. Most of the value in this repo is expected to come
from pairs of ideas whose sources have never been read together — which only works if the
ideas are stored in a form that travels.

## Current index

### Sources
- [Michels — geometric reasoning interview](sources/michels-sophontic-interview.md) `[source]` — the 53-min video, 12 claims with locators
- [sophontic.ai — full site](sources/sophontic-website.md) `[source]` — all pages; the `/alignment/` page is the substantive one
- [Michels — wider body of work](sources/michels-other-work.md) `[source]` — *Principia Cybernetica*, teleodynamics, where the vocabulary originates

### Ideas

*From the Sophontic material*
- [Reasoning as internal geometry](ideas/reasoning-as-internal-geometry.md) — reasoning is a property of representational structure, not parameter count
- [Flip-rate evaluation](ideas/flip-rate-evaluation.md) `[ours]` — paired perturbations as a test that surface heuristics cannot pass. **Built and run.**
- [Frozen giants](ideas/frozen-giants.md) — scaling yields large, static, centrally-controlled models, and that is a design choice
- [Behaviourist vs cognitive training](ideas/behaviourist-vs-cognitive-training.md) — optimising outputs vs shaping internal operations
- [Cognitive liberty](ideas/cognitive-liberty.md) — model locality as a precondition for freedom of thought
- [Latent space as implicate order](ideas/latent-space-as-implicate-order.md) — Bohm's enfolded order as a lens on representation. A boundary marker, not a direction.

*Established literature — the controls and rivals*
- [Data quality over scale](ideas/data-quality-over-scale.md) `[lit]` — **the rival explanation for every small-model win**
- [Linear representation hypothesis](ideas/linear-representation-hypothesis.md) `[lit]` — concepts as directions
- [Token geometry and anisotropy](ideas/token-geometry-and-anisotropy.md) `[lit]` `[ours]` — representations live in a narrow cone; the first bar any geometric claim must clear
- [Tokenization limits reasoning](ideas/tokenization-limits-reasoning.md) `[lit]` — the tokenizer can make a task impossible; check before blaming geometry
- [Latent reasoning](ideas/latent-reasoning.md) `[lit]` — COCONUT and continuous thought: the mainstream counterpart to the geometry claim
- [Behaviourist control failures](ideas/behaviourist-control-failures.md) `[lit]` — sycophancy, sandbagging, alignment faking, sleeper agents
- [Attractor states](ideas/attractor-states.md) `[lit]` — the bliss attractor; the empirical seed of the whole programme

### Syntheses
- [Geometry vs scale is an empirical question](syntheses/geometry-vs-scale-is-empirical.md)
- [Perturbation evals as the only honest small-model comparison](syntheses/perturbation-evals-and-contamination.md)
