# Lead — One model family carries an entire geometric correlation

**ID:** `lead-gpt2-geometry-regime-break`
**Added:** 2026-08-12
**Status:** `open`
**Score:** kill=3 novelty=1 discrimination=3 load=3 (total 10)
**Origin:** our-null

## The observation

`[ours]` — E002 in `projects/001-geometric-reasoning`
(`results/E002-correlation.json`, metrics.confound_check):

> `intrinsic_dim_twonn: +0.692 with GPT-2, +0.006 without`

Across 16 models spanning 124M→9B and 2019→2026, intrinsic dimensionality correlates with
reasoning robustness at **ρ = +0.692**. Remove the four GPT-2 models and the correlation is
**+0.006** — not weakened, *annihilated*. The other twelve models, spanning four families
and three model generations, contribute essentially nothing.

E002 correctly read this as a confound and refused to call the claim supported. That verdict
is right and stands. What it did not do — because it was not what E002 asked — is explain
**why one family behaves as if it is in a different regime.**

## Why it is worth more research

Two readings, and they have opposite consequences:

1. **Family artefact.** GPT-2 differs in tokenizer, data, depth, training recipe, and
   vintage all at once. The correlation is spurious, driven by four points at one end of
   both axes. Under this reading, geometry is dead as a lever and the story ends.
2. **Regime break.** Something real changed between the 2019 recipe and the modern one, and
   intrinsic dimension tracks reasoning robustness *inside* the old regime but not the new
   one. Under this reading geometry is not dead — it is a variable that modern training
   already saturates, which is a far more interesting statement and predicts that the
   correlation should reappear in any *deliberately undertrained* modern model.

Nothing in the repo currently distinguishes these, and the difference decides whether
`claim-geometry-predicts-robustness` is falsified or merely mis-scoped. That is a project
premise, which is why `load` is 3.

The discriminating prediction is concrete: under (2), a modern-family model trained on
deliberately degraded data or stopped early should fall back onto the GPT-2 trend line.
Under (1) it should not.

## What it would take to kill it

Cheapest first: the four GPT-2 points are already measured. Plot intrinsic dimension against
flip rate for the 16 models and check whether GPT-2 sits on a *different line* or merely at
the *extreme end of the same one*. If it is the same line and GPT-2 is just at one end, the
"regime" reading dies immediately — this is leverage in a regression, not a second regime,
and the finding is that n=16 with clustered predictors cannot support the analysis at all.

Cost: **minutes, CPU, from committed results.** No new inference.

Only if GPT-2 is genuinely off-line does the more expensive check follow: measure two or
three additional 2019-era or deliberately weak models to see whether the old-regime trend has
more than four points behind it.

## Score

| Axis | Ours | Why |
|---|---|---|
| kill | **3** | The cheap version runs on committed data in minutes |
| novelty | **1** | "Correlations driven by one cluster" is a textbook regression pathology; what may be novel is the specific 2019-vs-modern regime reading, not the statistical observation |
| discrimination | **3** | Same-line vs. off-line cleanly separates the two readings, and both outcomes change what the project concludes |
| load | **3** | Decides whether 001's central claim is falsified or mis-scoped |

Gates: none triggered. Note `novelty = 1` honestly — this is mostly a known statistical
pathology, and the lead earns its place on `load`, not on originality.

## What would make this not a discovery

Ranked by likelihood:

1. **Leverage, not regime.** Four points at the extreme of both axes will produce a large
   correlation and its removal will destroy it, with no mechanism involved whatsoever. This
   is the most likely explanation by a wide margin.
2. **n=16 is too small** for any partial correlation with a clustered predictor. The right
   conclusion would then be "the analysis was underpowered", which is a finding about method,
   not about geometry.
3. **The descriptor is the wrong quantity.** E002 already records that "geometric density" is
   undefined in the source and that the four descriptors are a guess.

## Prior art searched

`[open]` — **not searched.** Worth checking whether intrinsic-dimension-vs-capability
correlations have been reported across model vintages; there is a literature on intrinsic
dimensionality of transformer representations
([[library/ideas/token-geometry-and-anisotropy]]) that may already cover it.

## Route

Not promoted. First work item — the same-line-vs-off-line check — belongs in
`projects/001-geometric-reasoning` as a re-analysis of existing results, not a new
experiment. If GPT-2 is on the same line, this file closes as `dead` and records that the
E002 confound check found leverage rather than a regime.

## Log

| Date | Change |
|---|---|
| 2026-08-12 | created from the E002 confound check |
