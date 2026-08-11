# E002 — Does hidden-state geometry predict reasoning robustness?

**Created:** 2026-08-11
**Status:** **preregistered** → running → analysed → verdict
**Tests:** `claim-geometry-predicts-robustness`
**Depends on:** [E001](E001-flip-rate-across-scale.md) · [E001b](E001b-modern-small-models.md) · [E001c](E001c-current-generation.md)

---

## Preregistration

*Written before the correlation code exists. Thresholds fixed here.*

### The question

Two explanations predict identical benchmark scores and cannot be separated by scores alone:

- **Geometry** — a model reasons well because of how its internal representations are
  organised ([[library/ideas/reasoning-as-internal-geometry]]).
- **Data quality** — a model reasons well because it was trained on better data
  ([[library/ideas/data-quality-over-scale]]).

E001–E001c produced an outcome variable spanning **0.048 → 0.968** flip rate across 15
model measurements. This run asks whether any geometric descriptor tracks that variation
once size is accounted for.

### Hypothesis

At least one descriptor correlates with flip rate after partialling out log parameter count,
with |partial ρ| ≥ 0.5.

**Recorded prior: I expect this to fail, or to produce a correlation that is an artefact of
model family.** Reasons: (a) the descriptors are our guess at an undefined term; (b) the
models differ in data, tokenizer, depth and recipe simultaneously, so size is a weak control;
(c) transformer representations are strongly anisotropic
([[library/ideas/token-geometry-and-anisotropy]]), which compresses the range of every
spectral descriptor. Writing this down so a null cannot be retrofitted as "expected all
along", and a positive cannot be overclaimed.

### Metric

**Descriptors** (all preregistered together — none chosen after seeing results):
`participation_ratio`, `effective_rank`, `intrinsic_dim_twonn`, `anisotropy`.

**Depth handling.** Models differ in layer count (12 → 36), so raw layer indices are not
comparable. Each descriptor is sampled at **relative depths 0.25, 0.50, 0.75, 1.00** by
nearest-layer selection, plus the **max and argmax over all layers** (the Valeriani "hump"
peak, see [[library/ideas/token-geometry-and-anisotropy]]).

**Correlation.** Spearman rank ρ as primary (relationships need not be linear); Pearson r
reported alongside. Control variable: log₁₀(parameters).

**Partial correlation:** `ρ_xy·z = (ρ_xy − ρ_xz·ρ_yz) / sqrt((1−ρ_xz²)(1−ρ_yz²))`

**Multiplicity.** 4 descriptors × 6 depth positions = **24 tests.** This is stated now and
must be stated in the verdict. With n≈15 models, an uncorrected |ρ| ≥ 0.5 will occur by
chance across 24 tests with high probability. Therefore:

- The **primary** test is restricted to descriptors at **relative depth 0.75** (4 tests) —
  chosen now because that is where semantic structure is reported to emerge after the
  intrinsic-dimension peak.
- All 24 are reported as **exploratory**, explicitly labelled, and no exploratory result is
  treated as confirmatory.

### Decision rule

| Outcome (primary, depth 0.75) | Interpretation |
|---|---|
| Some descriptor, \|partial ρ\| ≥ 0.5 | Geometry tracks robustness independently of size — justifies the matched-training experiment |
| All descriptors \|partial ρ\| < 0.3 | **Claim falsified in this regime.** Geometry adds nothing once size is controlled |
| Between 0.3 and 0.5 | Inconclusive. Say so |

### Sample and confounds

n ≈ 15 model measurements from E001/E001b/E001c. Same prompts as the flip-rate runs, so
geometry and behaviour are measured on identical inputs.

- **Small n.** 15 points is few for a partial correlation. CIs will be wide; the verdict must
  not overstate. This is a screening experiment, not a decisive one.
- **Size is a weak control.** Models differ in data, tokenizer, depth, architecture. A
  positive result is confounded by family and must be reported as such.
- **Family effects.** GPT-2 (4), SmolLM2/3 (4), Qwen2.5 (4), Qwen3/3.5 (3). If a correlation
  is driven entirely by GPT-2 sitting at one corner, it is a generation effect wearing a
  geometry costume. **Check: recompute excluding GPT-2.** Preregistered now.
- **Layer 0 is degenerate** — all prompts share a final token, so layer-0 last-token states
  are duplicates and TwoNN returns `nan`. Excluded from all analysis.
- **Correlational only.** No causal claim is available from this design, whatever the result.

### Runs planned

`geom geometry` on every model already measured, seed 0, same item prompts. Then one
correlation pass. No training.

---

## Execution

```bash
uv run geom geosweep --experiment E002        # geometry for every model in the ladder
uv run geom correlate --experiment E002       # join with flip rate, partial correlation
```

## Results

Run 2026-08-11, RTX 3090. 16 models with both a flip-rate measurement and a geometry
profile. Records: `results/E002-geom-*.json`, `results/E002-correlation.json`.

### Primary — relative depth 0.75 (preregistered)

| Descriptor | n | ρ(geom, flip) | ρ(geom, size) | **partial ρ** |
|---|---|---|---|---|
| participation_ratio | 16 | +0.588 | +0.665 | **+0.031** |
| effective_rank | 16 | +0.571 | +0.641 | **+0.037** |
| intrinsic_dim_twonn | 16 | +0.850 | +0.694 | **+0.692** |
| anisotropy | 16 | −0.318 | −0.565 | **+0.420** |

### Confound check — same, excluding the GPT-2 family (preregistered)

| Descriptor | n | ρ(geom, flip) | ρ(geom, size) | **partial ρ** |
|---|---|---|---|---|
| participation_ratio | 12 | +0.748 | +0.853 | **−0.392** |
| effective_rank | 12 | +0.706 | +0.783 | **−0.201** |
| intrinsic_dim_twonn | 12 | +0.706 | +0.741 | **+0.006** |
| anisotropy | 12 | −0.524 | −0.594 | **+0.164** |

## Analysis

**Preregistered.**

1. **The primary test appears to pass, and it is an artefact.** `intrinsic_dim_twonn`
   reaches partial ρ = +0.692, above the 0.5 support threshold. Removing the four GPT-2
   models sends it to **+0.006**. The entire correlation is those four models sitting in one
   corner: they are old, and they have both worse geometry and worse reasoning. Nothing
   connects the two except vintage.

2. **Two descriptors change sign** when GPT-2 is removed (participation_ratio +0.031 →
   −0.392; effective_rank +0.037 → −0.201). With n=12 and four descriptors, a sign flip of
   that size is what noise looks like. None of these is a stable measurement.

3. **The raw correlations are strong and entirely explained by size.** Every descriptor
   correlates with flip rate at ρ = 0.57–0.85 *before* controlling. Nearly all of it is
   mediated by parameter count: bigger models have higher intrinsic dimension and reason
   better, and geometry adds nothing on top. This is the exact shape of confound the design
   was built to detect.

4. **Anisotropy at +0.420** is the only descriptor in the inconclusive band on the primary
   test, and it drops to +0.164 without GPT-2. Not a finding.

**Post-hoc** (labelled, weaker):

5. The strongest *raw* signal is intrinsic dimension (ρ = +0.850 with flip rate), consistent
   with [[library/ideas/token-geometry-and-anisotropy]] — but it tracks size, not capability
   given size. If a geometric quantity ever does predict reasoning independently, intrinsic
   dimension is still the one to watch; this design simply cannot separate it from scale.

## Verdict

**`claim-geometry-predicts-robustness` → CONFOUNDED, trending toward falsified.**

No geometric descriptor predicts reasoning robustness once parameter count is controlled and
the GPT-2 family is removed. Best surviving |partial ρ| is **0.006**, against a preregistered
falsification threshold of 0.3.

Under the preregistered rule the primary test alone would read SUPPORTED. **The confound
check — written into the preregistration before any number existed — is what kills it.**
That is the check doing its job.

**What changed in my beliefs.** The preregistration recorded an expectation that this would
fail or produce a family artefact. It produced exactly a family artefact. That prediction
being right is mild evidence the framework is working; it is not evidence about geometry.

**A harness failure worth recording.** The verdict function initially read only the primary
test and printed **SUPPORTED**. The confound check was preregistered, implemented, executed,
and printed directly beneath — showing +0.692 → +0.006 — and the verdict ignored it. A
correct analysis with a wrong summary line is more dangerous than a broken analysis, because
the summary is what gets quoted. Fixed: the confound check is now part of the decision, sign
included, guarded by `tests/test_verdict.py`.

**What this cannot conclude.**

- **It does not refute the geometry claim.** No geometric intervention was tested. This says
  our four descriptors, at one depth, across 16 uncontrolled models, do not predict
  robustness given size. A trained intervention could still work.
- **The descriptors are our guess** at an undefined term. A proponent can reasonably say we
  measured the wrong quantity — that objection is unanswerable while "geometric density"
  remains undefined ([[library/sources/sophontic-website]]).
- **n=16, and the models differ in everything at once** — data, tokenizer, depth, recipe,
  vintage. Parameter count is a weak control, which is precisely why the result is
  "confounded" rather than "falsified".
- **Correlational by construction.** Only a matched-training experiment can separate cause.

**Consequence.** The cheap screen has been run and it found nothing. Under this project's
own logic — *if nothing correlates across a ladder spanning 0.048 → 0.968, the expensive
experiment is not worth running* — the matched-training experiment is **not justified on
this evidence**. It would become justified if someone published an operational definition of
the geometric objective, or if a better-controlled ladder (same family, same data, varying
only size) showed a surviving correlation.

**Notes updated:** `notes/claim-geometry-predicts-robustness.md`,
[[library/ideas/reasoning-as-internal-geometry]].

## Amendment log

| Date | Change | Why |
|---|---|---|
| 2026-08-11 | created | E001c gave flip rate enough variance to correlate against |
| 2026-08-11 | verdict function now incorporates the confound check | It reported SUPPORTED on a correlation the check had already disproved on the line above |

## Amendment log

| Date | Change | Why |
|---|---|---|
| 2026-08-11 | created | E001c gave flip rate enough variance to correlate against |
