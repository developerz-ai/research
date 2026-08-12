# Lead — When a model changes its answer across a perturbation, it is almost always right twice

**ID:** `lead-flip-stickiness-near-identity`
**Added:** 2026-08-12
**Status:** `open`
**Score:** kill=3 novelty=2 discrimination=3 load=2 (total 10)
**Origin:** anomaly

## The observation

`[ours]` — In `projects/001-geometric-reasoning`, `flip_rate + stickiness` sums to within
0.005 of **1.000** for most of the 16-model ladder, and the deficit is neither zero nor
random across the rest:

| Model | flip | sticky | deficit |
|---|---|---|---|
| gpt2 | 0.048 | 0.913 | 0.039 |
| gpt2-medium | 0.042 | 0.922 | 0.036 |
| gpt2-large | 0.185 | 0.772 | 0.043 |
| gpt2-xl | 0.171 | 0.793 | 0.036 |
| SmolLM2-135M | 0.185 | 0.792 | 0.023 |
| Qwen2.5-0.5B | 0.327 | 0.648 | 0.025 |
| **SmolLM3-3B** | 0.562 | 0.380 | **0.058** |
| Qwen3.5-2B | 0.772 | 0.210 | 0.018 |
| SmolLM2-1.7B / Qwen2.5-7B / Qwen3.5-9B | — | — | 0.000 |

Source: the findings table in `projects/001-geometric-reasoning/README.md`, computed from
`results/E001*-seed0.json`. **These are sums taken from committed aggregates, not yet
recomputed from per-item data** — see the first work item.

`flip + sticky ≤ 1` is forced by the design (a sticky pair gives the same option on both
members, and the pair's two members have different answers, so a sticky pair cannot be a
flipped one). The *near-equality* is not forced. The deficit is exactly the fraction of pairs
where the model **changed its answer across the perturbation and still got at least one
member wrong** — and for the strongest models that fraction is zero to three decimal places.

## Why it is worth more research

If the deficit really is ~0 at the top of the ladder, then "responded to the perturbation"
and "answered both correctly" are the same event for those models — there is no middle state
where a model notices the change and mishandles it. That is a strong and non-obvious claim
about how these models fail: they either ignore the perturbation entirely or get it right,
with almost nothing in between.

And it makes **SmolLM3-3B the outlier of the whole ladder**, with the largest deficit
(0.058) at a middling flip rate (0.562) — larger than every GPT-2 model despite scoring 3×
better than them. Whatever the deficit measures, it is not "weakness". Nobody has explained
that, and it is sitting in already-committed data.

Downstream: E002's confound analysis treated four descriptors as the interesting variables.
If `stickiness` is very nearly `1 − flip_rate`, it carried almost no independent information
in that analysis, and the deficit — which nobody reported — was the only independent signal
in the metric set.

## What it would take to kill it

Recompute flip, stickiness, and the deficit **from the per-item arrays** in the committed
`results/E001*-seed0.json` files, with a Wilson CI on the deficit at n=600 pairs. Then check
whether the deficit is distinguishable from zero for the top models and whether SmolLM3-3B's
0.058 survives its CI.

Cost: **minutes, CPU, no inference, no new runs.** Everything needed is already in git.

## Score

| Axis | Ours | Why |
|---|---|---|
| kill | **3** | Under an hour on CPU, from committed data |
| novelty | **2** | Searched nothing yet; the pattern is in our own numbers and is not reported anywhere in the project's own writeups |
| discrimination | **3** | Deficit ≈ 0 and deficit > 0 are both informative, and they say opposite things about how these models fail |
| load | **2** | Bears on whether E002's descriptor set had redundant members, and on what the metric suite should be in 002 |

Gates: none triggered.

## What would make this not a discovery

Ranked by likelihood:

1. **A rounding artefact.** The table carries three decimals; deficits of 0.000–0.005 may be
   entirely rounding. This is the most likely explanation and it is why the first work item
   is a recompute, not an interpretation.
2. **Near-algebraic redundancy.** If the item design makes "not sticky" and "both correct"
   almost equivalent for a well-behaved model, the near-identity is a property of the
   *instrument*, not of the models. That would still be worth knowing — it would mean
   `stickiness` should be dropped from the reported metric suite rather than presented as an
   independent signal.
3. **n=600 is not enough** to distinguish 0.000 from 0.005, in which case the interesting
   part reduces to SmolLM3-3B and GPT-2 alone.
4. **A scoring bug** in how half-correct pairs are counted.

## Prior art searched

`[open]` — **not searched.** Paired-perturbation evaluation has a literature, and
"consistency" metrics of this shape are common enough that the near-identity may be a known
property of the design. `novelty` is capped at 2 until someone actually looks.

## Route

Not promoted. First work item is the recompute, in `projects/001-geometric-reasoning`. If
the deficit survives, it becomes a claim there; if it does not, this file records that
`stickiness` is redundant with `flip_rate` and should not be reported as independent.

## Log

| Date | Change |
|---|---|
| 2026-08-12 | created from the E001 findings table |
