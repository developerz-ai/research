# Idea — Tokenization limits reasoning

**Added:** 2026-08-11
**Status:** `[lit]` — replicated, and a live confound in our own harness

## Statement

A model's tokenizer sets a hard floor on some reasoning tasks: when tokenization destroys
the structure a task depends on — place value, digit alignment, symbol boundaries — no
amount of scale or chain-of-thought recovers it.

## Why it belongs next to the geometry ideas

Because it is the **other** way tokens determine what a model can do, and it is the more
mundane one. Before attributing a reasoning failure to a model's internal geometry, check
whether the tokenizer made the task impossible. That check is cheap, it is frequently
skipped, and it dissolves a good fraction of apparent reasoning results.

This idea is a discipline, not a discovery: it is the first alternative explanation to rule
out, in the same way [[library/ideas/data-quality-over-scale]] is the first alternative for
small-model wins.

## Mechanism

- BPE splits numbers inconsistently — `1234` may become `12|34`, `123|4`, or `1|234`
  depending on corpus frequency. Place value is not preserved, so the model must learn
  arithmetic separately for each segmentation pattern it encounters.
- Carry operations run right-to-left; standard tokenization runs left-to-right. The
  alignment between the algorithm and the token sequence is wrong by construction.
- Digit-count boundaries produce measurable discontinuities in hidden states — models make
  more errors on problems that cross them (e.g. 9+3 vs 7+2).
- Fixes exist and work: digit-level tokenization, right-to-left grouping, fixed-width
  chunking (Llama 3 groups up to three digits), single-token number encodings.

## Evidence

`[lit]`

| Work | Finding |
|---|---|
| "Tokenization Constraints in LLMs: Symbolic and Arithmetic Reasoning Limits" (<https://arxiv.org/abs/2505.14178>) | Token structure causes failure **even with chain-of-thought**; atomically-aligned formats unlock generalisation |
| "Categorical Perception in LLM Hidden States: Structural Warping at Digit-Count Boundaries" (<https://arxiv.org/abs/2603.28258>) | Hidden-state geometry warps at digit-count boundaries — a direct token→geometry link |
| "Efficient numeracy through single-token number embeddings" (<https://arxiv.org/abs/2510.06824>) | Changing the encoding, not the model, improves numeracy |
| "How Numerical Precision Affects Arithmetical Reasoning" (<https://arxiv.org/abs/2410.13857>) | Precision/representation constraints bound arithmetic capability |

The second entry is the interesting one for this repo: it is evidence that **tokenization
changes the internal geometry**, which means a geometry difference between two models can be
a tokenizer difference wearing a disguise.

## What it predicts

- **If tokenization is the binding constraint:** performance on a task jumps when the input
  format changes, with the model held fixed. No retraining required.
- **If it is not:** reformatting does nothing and the failure is elsewhere.
- **Discriminating observation:** re-run the same items with digit-separated numbers
  (`1 8` vs `18`). A large delta means you were measuring the tokenizer.

## Consequence for our own harness

`[ours]` — a confound we listed as low-risk in the E001 preregistration and now judge to be
**understated for one family**.

E001's `arithmetic` family uses two-digit numbers with GPT-2's BPE. GPT-2 tokenizes numbers
inconsistently, so the two answer options in a pair may differ in token count and in
segmentation. Our design controls for option *strings* (identical across a pair) but the
two options within an item are different numbers, so their tokenizations can differ
structurally.

Observed: `arithmetic` had the **lowest flip rate of any family** in the pre-fix run
(gpt2 0.06, gpt2-xl 0.05), and canonical accuracy near 0.4 — below chance. That is
consistent with a tokenization floor rather than a reasoning failure, and the two are not
currently distinguishable in our data.

Preregistered follow-up for E001b: add a digit-separated variant of the `arithmetic` family
and compare. If the gap closes, the family was measuring the tokenizer and its E001 numbers
should be reported separately from the rest.

## Competing and neighbouring ideas

- Confounds: [[library/ideas/flip-rate-evaluation]] — a family can fail for token reasons and
  look like a shortcut result.
- Related: [[library/ideas/token-geometry-and-anisotropy]] — the geometric half of "tokens
  determine what a model can do".
- Constrains: [[library/ideas/reasoning-as-internal-geometry]] — a geometry claim compared
  across model families is partly a tokenizer comparison unless controlled.

## Open questions

1. How much of our `arithmetic` family's floor is tokenization? `[open]` — E001b.
2. Does the digit-count warping show up in our geometric descriptors at 124M? Testable with
   the existing `geom geometry` command.
