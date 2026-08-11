# Idea — Data quality over scale

**Added:** 2026-08-11
**Status:** `[lit]` — repeatedly replicated

## Statement

Curated data and curriculum ordering buy capability that would otherwise require far more
parameters, so small models can beat much larger ones without any change to architecture or
training objective.

## Why this note matters most

**This is the rival explanation for every small-model win**, and any claim about geometry,
architecture, or novel objectives has to beat it before it means anything.

It is the boring hypothesis, it is extremely well supported, and it explains most reported
"small model beats big model" results on its own. An experiment that does not control for
it cannot distinguish a new mechanism from ordinary good data engineering — which is
exactly the ablation missing from [[library/sources/michels-sophontic-interview]].

## Evidence

`[lit]`

| Work | Result |
|---|---|
| **TinyStories** (Eldan & Li 2023, <https://arxiv.org/abs/2305.07759>) | <10M params produce fluent, coherent English with basic reasoning, given a vocabulary-restricted synthetic corpus |
| **phi-1** (Gunasekar et al. 2023, <https://arxiv.org/abs/2306.11644>) | 1.3B on 7B curated tokens beats Codex-12B and much larger models on coding |
| **phi-2 / phi-4** | continued: textbook-quality data beats 5–25× larger models on reasoning benchmarks |
| **Curriculum on GPT-2 124M** (<https://arxiv.org/abs/2505.11643>) | a four-stage easy-to-hard curriculum reaches target accuracy in half the steps of single-phase training, at identical size |

The last one is the closest published analogue to the intervention project 001 is testing,
at exactly the same scale, and it required no geometric story at all.

## Mechanism

Several routes, not mutually exclusive:

- Removing noisy/irrelevant data raises the effective signal per token.
- Ordering easy→hard shapes the optimisation path — the model learns composable primitives
  before compositions, rather than memorising surface statistics of hard examples.
- Restricting vocabulary and syntax reduces the entropy the model must model at all, freeing
  capacity for structure.

Note that the second route is *itself* a claim about internal organisation. Curriculum
learning and "training the geometry" may not be rivals so much as the same phenomenon
described in two vocabularies — which is a synthesis worth writing, and a reason to measure
geometry on curriculum-trained models before assuming a new mechanism is needed.

## What it predicts

- **If true:** a small model trained on curated/curriculum data matches a much larger model
  on the curated domain, with **no architectural or objective change**.
- **Therefore:** any geometry experiment must include a curriculum-only arm at matched
  compute. Without it, a positive result is uninterpretable.
- **Discriminating observation:** does the geometric intervention add anything *on top of*
  a strong curriculum baseline? That delta is the only number that speaks to the geometry
  claim.

## Also known

`[lit]` — the deflationary companion result: small models beat large ones **on the narrow
domain they were specialised for** and lose badly outside it. A specialist beating a
generalist on the specialist's home turf is expected, not evidence of a new mechanism. Any
"60× smaller model wins" claim must state the task distribution before it can be assessed at
all.

## Competing and neighbouring ideas

- **Competes directly with** [[library/ideas/reasoning-as-internal-geometry]] as an
  explanation for the same observations.
- Related: the bitter lesson — general methods plus compute beat hand-designed structure.
  Note the tension: data curation is *also* a form of hand-designed structure that works,
  so the bitter lesson is not the whole story either.

## Open questions

1. Does curriculum training measurably change hidden-state geometry? If yes, "geometric
   engineering" may be a redescription rather than a new mechanism. `[open]`
2. At matched compute, curriculum vs geometric auxiliary loss vs both — which wins on flip
   rate? This is the experiment that would settle it.
