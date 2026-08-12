# E001 — Axiom identification: contaminated vs. clean

**Created:** 2026-08-12
**Status:** **preregistered** → running → analysed → verdict
**Tests:** `claim-axiom-id-is-recall`

---

## Preregistration

*Everything under this heading is written before the code that produces the number.
Amendments go in the log at the bottom — amending is fine, silently amending is not.*

### Hypothesis

A model asked which axiom of a formal system is redundant scores well above chance on
systems whose answer is documented in its pretraining corpus, and at or near chance on
freshly generated systems of matched structure. Expected direction: **contaminated ≫ clean**,
with delta ≥0.25.

The alternative being discriminated against — and it is a serious one — is that the model
has genuine structural sensitivity to derivational redundancy, in which case clean accuracy
is high and the delta is small. That outcome kills the claim.

### Metric

- **Definition:** identification accuracy = fraction of systems where the model's named axiom
  is the solver-labelled redundant one. One named axiom per system; the model is instructed
  to name exactly one.
- **Ties:** generation excludes systems with more than one redundant axiom. A system whose
  solver check finds ≥2 redundancies is discarded at generation time, not at scoring time.
- **Malformed output:** a response that names no axiom, or names something not in the set, is
  scored **incorrect**, not dropped. Dropping them turns a format-compliance failure into a
  silent accuracy boost. The malformed rate is reported alongside every accuracy figure.
- **Aggregation:** unweighted mean over items within a stratum; strata are fixed axiom-count k
  so chance = 1/k exactly.
- **Uncertainty:** Wilson 95% CI on each proportion; seed spread reported as min–max across
  ≥3 seeds. The headline delta gets a CI by bootstrap over items (10k resamples).

### Decision rule

Chance is 0.20 at k=5.

| Outcome | Interpretation |
|---|---|
| clean ≥0.40 **and** delta ≤0.10 | **claim falsified** — identification is not mere recall in this regime |
| delta ≥0.25 **and** clean CI overlaps chance | **claim supported** — the capability is corpus presence |
| anything else | inconclusive — say so, do not squint |

Effect size worth caring about: **0.25** absolute delta. Below that, the "bottleneck" framing
in the source is not doing any work.
Items needed: 200 per arm gives a ±0.07 Wilson half-width near p=0.3, so a 0.25 delta is
resolvable with room to spare. 200/arm/seed × 3 seeds.

### Baseline

Two baselines, both mandatory:

| Arm | Params | Tokens | Wall-clock | Notes |
|---|---|---|---|---|
| clean (treatment) | small open-weight, TBD | n/a — inference only | measured | freshly generated systems |
| contaminated (control) | identical model | identical | measured | documented historical systems |
| random | — | — | — | 1/k analytic, plus an empirical draw to expose position bias |
| position-bias probe | identical model | identical | measured | always-first / always-last strategies scored on the same items |

Compute is matched by construction: same model, same decoding, same item count. The budget
matched is **parameters and inference tokens**.

The comparison this experiment cannot make: contaminated and clean items differ in more than
contamination (see confounds). The delta is therefore an **upper bound** on the contamination
effect, and must be reported as one.

### Confounds

- [x] **Contamination** — the object of study, not a nuisance here. But the *direction* runs
      the other way for the clean arm: freshly generated items cannot be contaminated, by
      construction of the generator's seed space.
- [x] **Difficulty mismatch** — historical systems are curated and elegant; generated ones may
      be structurally harder. Mitigation: match on axiom count k, formula depth, and number of
      atoms; report the matching table. This is the largest threat and it is only partly
      controllable.
- [x] **Position bias** — axiom order is randomised per item per seed, and the always-first /
      always-last probes are run explicitly.
- [x] **Prompt formatting / chat template** — one template, fixed before the run, applied
      identically to both arms; the template is stored in the run record.
- [x] **Item order effects** — items are independent single-turn queries, no shared context.
- [x] **Selection of items after seeing results** — generation seeds are fixed in the config
      and the item set is frozen before any scoring run.
- [ ] Other: solver-oracle bug. Mitigated by an independent second check (SAT and a
      brute-force truth-table check agree, or the item is discarded).

### Runs planned

3 seeds × 2 arms × 200 items. Small local model first (CPU-runnable at `--limit 20`), then
one 3090-class open-weight model, then optionally one API frontier model if budget allows.
If the frontier arm is not run, the verdict says so and does not generalise to it.

---

## Execution

**Command:**
```bash
uv run ftl systems --n 200 --k 5 --seed 0 --out data/raw/E001-clean-seed0.jsonl
uv run ftl identify --arm clean --model <M> --seed 0 --out results/E001-clean-<M>-seed0.json
uv run ftl identify --arm contaminated --model <M> --seed 0 --out results/E001-contaminated-<M>-seed0.json
```

**Result files:** `results/E001-*.json`
**Git SHA at run:**
**Hardware:**

## Results

| Arm | Seed | Accuracy | Wilson CI | Malformed | n |
|---|---|---|---|---|---|
| | | | | | |

## Analysis

## Verdict

- **Claim status:**
- **What changed in my beliefs:** *(recorded before the run: I expect the delta to be large —
  ≥0.3 — and the clean arm to sit at or barely above chance. If the clean arm lands at 0.5+ I
  will suspect the generator is leaking the answer through structure before I believe the
  model found it.)*
- **What this cannot conclude:**
- **Notes updated:**

## Amendment log

| Date | Change | Why |
|---|---|---|
| | | |
