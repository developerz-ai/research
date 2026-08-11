# Idea — Token geometry and anisotropy

**Added:** 2026-08-11
**Status:** `[lit]` — well replicated, and independently reproduced here `[ours]`

## Statement

Transformer token representations do not spread through their embedding space — they
concentrate in a narrow high-dimensional cone with near-uniform pairwise cosine similarity,
so the raw geometry of a hidden state is dominated by an artefact of training rather than by
meaning.

## Why this is the first thing to know about "the geometry of a model"

Any claim about a model's internal geometry — including
[[library/ideas/reasoning-as-internal-geometry]] — has to survive this fact. If nearly all
directions are shared, then cosine similarity, nearest-neighbour structure, and most naive
geometric summaries are measuring the cone, not the concept.

It is the reason a geometric result needs a control, and the reason "we looked at the latent
space and saw structure" is not evidence on its own. **You will always see structure.**

## Mechanism

- **Representation degeneration.** Likelihood maximisation with weight tying pushes
  embeddings away from the origin in a shared direction. Rare and unused tokens contribute
  gradients that drag the whole distribution the same way.
- **Rogue dimensions.** A handful of dimensions dominate the variance. Timkey & van Schijndel
  showed that removing just a few restores much of the meaningful similarity structure —
  the anisotropy is concentrated, not diffuse.
- **Inherent to self-attention.** Later work argues anisotropy arises from the attention
  mechanism itself, not only from the training objective, which is why it appears across
  architectures and modalities.
- **Frequency effects.** Token frequency organises the space; common and rare tokens occupy
  systematically different regions.

## Evidence

`[lit]`

| Work | Finding |
|---|---|
| Gao et al. 2019, "Representation Degeneration Problem in Training NLG" | The original diagnosis; weight tying + likelihood training produce a narrow cone |
| Ethayarajh 2019, "How Contextual are Contextualized Word Representations?" | Contextual embeddings are highly anisotropic; cosine similarity is inflated across the board |
| Timkey & van Schijndel 2021, "All Bark and No Bite: Rogue Dimensions" ([pdf](https://vansky.github.io/assets/pdf/timkey_vanschijndel-2021-emnlp.pdf)) | A few dimensions dominate; removing them restores similarity structure |
| Godey et al. 2024, "Anisotropy Is Inherent to Self-Attention" (<https://arxiv.org/abs/2401.12143>) | Not merely a training artefact — arises from attention itself |
| Valeriani et al. 2023, "Geometry of hidden representations of large transformer models" (<https://arxiv.org/abs/2302.00294>) | Intrinsic dimension follows a characteristic **hump** across layers; semantic structure emerges at the contraction after the peak |
| "The Shape of Learning: Anisotropy and Intrinsic Dimensions" (<https://arxiv.org/abs/2311.05928>) | Joint treatment of both quantities across training |

## What we measured

`[ours]` — `projects/001-geometric-reasoning`, `geom geometry` on gpt2, 2026-08-11.

Mean pairwise cosine similarity of last-token hidden states, per layer: **0.861 – 0.996**,
across all 13 layers. Participation ratio 1.2–4.7 out of an ambient 768 dimensions;
effective rank 1.4–10.9.

So: **fewer than 5 effective directions out of 768**, and vectors ~90-99% aligned with each
other. This reproduces the published picture exactly, on the first try, with no tuning.

Two consequences we hit immediately:

1. **Layer 0 intrinsic dimension was undefined** (`nan`). All our prompts end with the same
   token, so the layer-0 last-token embeddings are literally duplicates. The estimator
   correctly refused rather than fabricating a number — but it is a reminder that "take the
   last token's hidden state" interacts with prompt templating in ways that can silently
   degenerate.
2. **Descriptors must be computed on centred activations.** Uncentred, they largely measure
   the cone's offset. Our `describe_layer` centres before the spectrum, but `anisotropy` is
   deliberately computed uncentred, as the confound indicator.

## What it predicts

- **If a geometric metric is meaningful:** it survives centring and removal of the top few
  rogue dimensions. A correlation that vanishes under those controls was measuring frequency
  and offset.
- **If not:** the metric tracks token frequency statistics and prompt template, which is what
  a naive "latent space" analysis usually recovers.
- **Discriminating observation:** compute the metric before and after dropping the top-k
  dominant dimensions. Report both. A robust effect barely moves.

## Competing and neighbouring ideas

- Constrains: [[library/ideas/reasoning-as-internal-geometry]] — any geometric claim must
  clear this bar first.
- Nuances: [[library/ideas/linear-representation-hypothesis]] — concepts can be linear
  directions *and* sit in a narrow cone; the cone makes them harder to see, not absent.
- Related: [[library/ideas/tokenization-limits-reasoning]] — the other way tokens constrain
  what a model can do.
- Deflates: [[library/ideas/latent-space-as-implicate-order]] — "everything enfolded in
  everything" has a mundane and measurable version, and this is a large part of it.

## Open questions

1. Does anisotropy differ systematically between models that pass and fail flip-rate items?
   `[open]` — cheap to check with the existing harness.
2. Does the intrinsic-dimension hump (Valeriani et al.) shift with reasoning ability at
   matched size? This is the most promising geometric quantity we have found so far, and it
   is a better E002 candidate than the flat summaries we started with.
3. Do the rogue dimensions carry reasoning-relevant information, or only frequency?
