# E001 — Flip rate across a model-size ladder

**Created:** 2026-08-11
**Status:** **preregistered** → running → analysed → verdict
**Tests:** `claim-flip-rate-tracks-scale`, and provides the outcome variable for `claim-geometry-predicts-robustness`

---

## Preregistration

*Written before the harness produced any number. Amendments go in the log at the bottom.*

### Hypothesis

Flip rate rises monotonically with parameter count across GPT-2 124M → 1.5B, and the
**shortcut gap** (expected − observed flip rate) shrinks as size increases.

The alternative being discriminated against: flip rate is flat near chance across the whole
ladder, i.e. none of these models does the paired task at all, and canonical accuracy
reflects surface statistics throughout.

Both outcomes are informative, and the second is the one we consider more likely a priori —
these are small base models and the items require tracking a single load-bearing fact.
Recording that expectation now is what makes the result readable later.

### Metric

**Primary:** flip rate = fraction of pairs where the model is correct on *both* members.

- **Definition:** per pair, correct iff `chosen_index == correct_index` on canonical *and*
  perturbed. Chance = 0.25.
- **Scoring:** option log-likelihood, `sum` aggregation. Both options are identical strings
  across the pair by construction, so length normalisation cannot change which model wins;
  `mean` is recorded as a secondary check that this holds.
- **Ties:** exact log-probability ties are recorded via `margin`; `argmax` resolves to index
  0. Expected count ≈ 0 with float scoring — if any appear, they are reported, not silently
  broken.
- **Generation failures:** none possible. Nothing is generated and nothing is parsed, which
  is why this scoring method was chosen for models that cannot follow a format.
- **Aggregation:** overall and per family. A result driven by one family is reported as such.
- **Uncertainty:** Wilson 95% CI on the flip-rate proportion; spread across 3 item seeds.

**Secondary:** `shortcut_gap` and `stickiness` — these detect surface matching, which plain
accuracy cannot see.

### Decision rule

Thresholds fixed now.

| Outcome | Interpretation |
|---|---|
| Flip rate rises monotonically, largest model ≥ 0.45 | Scale buys paired-item robustness in this range |
| All models within [0.20, 0.30] with overlapping CIs | Falsified — no model in this range does the task; the ladder is uninformative about geometry |
| Non-monotonic, or gains inside CI overlap | Inconclusive. Say so; do not squint at it |

- **Effect size worth caring about:** 0.10 absolute flip-rate difference between adjacent rungs.
- **Items needed:** 600 pairs (100 × 6 families). Wilson half-width at p≈0.25, n=600 is
  ≈0.035 — comfortably below a 0.10 effect. Three seeds give a spread on top of that.

### Baseline

Two, both required:

| Arm | Params | Tokens | Notes |
|---|---|---|---|
| gpt2 | 124M | ~10B (WebText) | the scale the source's claim names |
| gpt2-medium | 355M | ~10B | same data, same recipe |
| gpt2-large | 774M | ~10B | same data, same recipe |
| gpt2-xl | 1.5B | ~10B | same data, same recipe |
| **constant-answer** | — | — | analytic: flip rate exactly 0.0, stickiness 1.0 |
| **chance** | — | — | analytic: flip rate 0.25 |

The GPT-2 family is chosen deliberately: same architecture, same training corpus, same
recipe, varying only size. That is the closest thing to a budget-matched size ladder
available without training anything, and it is why this ladder rather than a mix of modern
models — those differ in data, tokenizer, and recipe simultaneously, which would make the
size comparison uninterpretable.

The constant-answer baseline is not decoration: it is the number a surface-matching model
gets, and the design's entire claim is that such a model scores 0.0 here while scoring ~0.5
on a conventional benchmark.

### Confounds

- [x] **Contamination** — excluded by construction. Items generated fresh from a seed, never
      published. A memorising model is actively penalised on the perturbed member.
- [x] **Option-string effects** — excluded by construction. Options are identical strings
      across a pair; only which is correct changes.
- [x] **Answer priors** — excluded by construction. Correct answers are exactly balanced
      per family (`test_correct_answers_balanced_per_family`).
- [ ] **Tokenizer artefacts** — same tokenizer across the whole GPT-2 ladder, so it cannot
      drive a *size* trend. Would matter if the ladder mixed families.
- [ ] **Length bias** — options are short and matched; `mean` aggregation recorded as a check.
- [ ] **Item quality** — a broken or ambiguous item scores a reasoning model as wrong.
      Mitigated by `Pair.validate()` and by reading `geom items` output before trusting a
      number. Residual risk: template-level ambiguity that validation cannot detect.
- [ ] **Family imbalance** — 6 families weighted equally; the overall number could be driven
      by one. Per-family breakdown is reported alongside.
- [ ] **Prompt format** — one fixed format, no chat template. Base models only. Extending to
      instruction-tuned models would require a format decision that is itself a confound.

### Runs planned

3 seeds (0, 1, 2) × 4 models × 600 pairs = 14,400 items ≈ 28,800 scored continuations.
Estimated wall-clock on the RTX 3090: minutes for gpt2, well under an hour for the full
sweep. CPU path verified at reduced `--limit` first.

---

## Execution

```bash
uv run geom doctor
uv run geom items --n 2                      # read them first
for seed in 0 1 2; do
  uv run geom sweep --models gpt2,gpt2-medium,gpt2-large,gpt2-xl --n 100 --seed $seed
done
uv run geom report --pattern "E001-*.json"
```

**Result files:** `results/E001-*.json`
**Git SHA at run:** _(recorded automatically in each run record)_
**Hardware:** _(recorded automatically)_

## Results

Run 2026-08-11 on RTX 3090, 3 seeds × 4 models × 600 pairs. Full records in
`results/E001-*.json`.

| Model | Params | Flip rate (3 seeds) | Mean | Canonical acc | Perturbed acc | Shortcut gap | Stickiness |
|---|---|---|---|---|---|---|---|
| gpt2 | 124M | 0.058 · 0.050 · 0.035 | **0.048** | 0.729 | 0.280 | +0.156 | 0.913 |
| gpt2-medium | 355M | 0.040 · 0.047 · 0.038 | **0.042** | 0.726 | 0.280 | +0.161 | 0.922 |
| gpt2-large | 774M | 0.175 · 0.180 · 0.200 | **0.185** | 0.692 | 0.451 | +0.127 | 0.772 |
| gpt2-xl | 1.5B | 0.143 · 0.175 · 0.195 | **0.171** | 0.755 | 0.380 | +0.116 | 0.793 |
| *chance* | — | — | *0.250* | *0.500* | *0.500* | *0.000* | *0.500* |
| *constant answer* | — | — | *0.000* | *~0.50* | *~0.50* | *+0.250* | *1.000* |

Seed-to-seed spread is ≤0.06 everywhere; Wilson half-widths ≈0.03. The differences
discussed below are outside both.

## Analysis

**Preregistered.**

1. **Every model is below chance.** The best mean flip rate is 0.185 against a chance rate
   of 0.250, and no single run reached 0.20 except one gpt2-large seed that landed exactly
   there. Below chance is not "slightly worse than guessing" — it means errors are
   *anti-correlated* across the pair, which is what happens when both answers come from the
   surface form the two members share.

2. **Canonical accuracy is not remotely diagnostic.** Every model scores 0.69–0.76 on the
   canonical items alone. A conventional benchmark would report that number and describe
   these models as substantially better than chance at relational reasoning. The paired
   design shows the same models at 0.04–0.19. **That gap is the entire point of the
   instrument**, and it reproduces cleanly at every size tested.

3. **Stickiness 0.77–0.92** — the models give the *same* answer to both members of a pair
   on the large majority of items. They are not reasoning badly; they are largely not
   responding to the perturbation at all.

4. **Scale helps, but not monotonically, and not enough.** 124M → 1.5B is 12.5× the
   parameters for a flip-rate rise of 0.048 → 0.171. Real (CIs do not overlap), but the
   trend breaks twice: gpt2-medium is *below* gpt2 despite 2.9× the parameters, and gpt2-xl
   is at or below gpt2-large across two of three seeds. The jump happens entirely between
   355M and 774M.

**Post-hoc** (noticed after seeing results, not preregistered, weaker evidence):

5. The per-family breakdown of the first (invalid) run showed gpt2 at 0.98/0.03 on
   `comparison` and 0.04/0.96 on `transitive` — mirror images. Both are explained by a
   single rule: *answer the last-named entity*. That pattern is what exposed the broken
   `role_swap` family, and it suggests small-model behaviour on these items is better
   described by one positional heuristic than by degraded reasoning.

6. The most interesting quantity may be **stickiness rather than flip rate**. It is well
   defined even when accuracy is at chance, and it fell monotonically with scale in a way
   flip rate did not (0.913 → 0.922 → 0.772 → 0.793). Worth preregistering as a primary
   metric in E002 rather than treating as a diagnostic.

## Verdict

**Against the preregistered decision rule:**

- Support condition (monotonic rise, largest model ≥ 0.45): **not met**, decisively.
- Falsification condition (all within [0.20, 0.30], overlapping CIs): **not met either** —
  the models are mostly *below* that band.
- Rule outcome: **non-monotonic ⇒ inconclusive on the monotonicity hypothesis.**

`claim-flip-rate-tracks-scale` → **falsified as stated** (the rise is not monotonic), with
the stronger and cleaner finding being that no GPT-2-family model at any size tested does
these paired tasks at all.

**What changed in my beliefs.** The preregistration recorded an expectation that flat-near-
chance was more likely than a clean scaling trend. That was roughly right, but two things
were not anticipated: that scores would sit consistently *below* chance rather than at it,
and that the failure would be this cleanly attributable to a single positional heuristic.

**What this cannot conclude.**

- Nothing about instruction-tuned or modern models. GPT-2 is a 2019 base-model family; its
  failure here is unsurprising and is not evidence about Llama/Qwen-class small models.
  **Extending the ladder to modern ≤1.5B models is the obvious next run** and costs an hour.
- Nothing about the geometry claim. E001 only establishes the outcome variable. Its actual
  finding for E002 is a problem: **flip rate has almost no usable variance across this
  ladder** (0.04–0.19, all sub-chance), so correlating it against geometric descriptors
  would be correlating against noise. E002 needs either a wider model ladder or stickiness
  as the outcome variable.
- Nothing about reasoning in general — six synthetic families, one prompt format.

**Consequence for the project.** E002 as originally drafted should not be run on this
ladder. Revised plan in `README.md`.

**Notes updated:** `notes/claim-geometry-predicts-robustness.md` (reachability),
[[library/ideas/flip-rate-evaluation]] (open question 1 now has an `[ours]` answer).

## Amendment log

| Date | Change | Why |
|---|---|---|
| 2026-08-11 | created | — |
| 2026-08-11 | `role_swap` family redesigned; first seed-0 sweep discarded | The family perturbed by swapping names, which also swapped positions, so a recency heuristic scored flip rate 1.0 on it. Discarded runs preserved with the full explanation in `results/superseded/`. Guarded permanently by `tests/test_baselines.py` and `geom baselines`. |
| 2026-08-11 | Added trivial-heuristic baselines to the harness | The confound above was invisible to the preregistered confound list, which assumed item validity rather than measuring it. Admissibility is now checked, not assumed. |
| 2026-08-11 | Fixed ungrammatical `conditional` question form | "did the alarm rings?" — malformed English is a confound; models were partly scored on it. |
