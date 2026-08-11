# {{EID}} — {{TITLE}}

**Created:** {{DATE}}
**Status:** preregistered → running → analysed → **verdict**
**Tests:** `claim-...`

---

## Preregistration

*Everything under this heading is written **before** the code that produces the number.
Amendments go in the log at the bottom — amending is fine, silently amending is not.*

### Hypothesis

What is expected, and in which direction. State the alternative you are discriminating
against, not just the outcome you hope for.

### Metric

Exactly how it is computed. Include the unglamorous parts, because they are where results
get manufactured by accident:

- Definition:
- How ties are handled:
- How generation failures / refusals / malformed outputs are handled:
- Aggregation across items:
- Uncertainty: (CI method for proportions; spread across seeds)

### Decision rule

The threshold, chosen now.

| Outcome | Interpretation |
|---|---|
| metric ≥ X | claim supported in this regime |
| metric ≤ Y | claim falsified in this regime |
| between | inconclusive — say so, do not squint |

Effect size worth caring about: ___
Items needed to detect it: ___ (state the power calculation or the reasoning)

### Baseline

What this is compared against, **matched on compute budget**. Name which budget is matched:
parameters, training tokens, wall-clock, or all three. An unmatched baseline makes the
result unreadable, and "we compared to a model someone else trained" is almost never matched.

| Arm | Params | Tokens | Wall-clock | Notes |
|---|---|---|---|---|
| treatment | | | | |
| baseline | | | | |

### Confounds

What else could produce this number?

- [ ] Contamination — does the eval predate the model's data cutoff?
- [ ] Tokenizer artefacts
- [ ] Prompt formatting / chat template
- [ ] Item order effects
- [ ] Position or length bias
- [ ] Selection of items after seeing results
- [ ] Other:

### Runs planned

Seeds, configurations, expected wall-clock. Confirm it fits the hardware budget before
starting, and confirm the CPU path runs at reduced `--limit`.

---

## Execution

**Command:**
```bash
uv run geom ... --seed 0 --out results/{{EID}}-seed0.json
```

**Result files:** `results/{{EID}}-*.json`
**Git SHA at run:**
**Hardware:**

## Results

Numbers with uncertainty. Per-item data lives in the result files; put the aggregate here
and say where the raw data is.

| Arm | Seed | Metric | CI | n |
|---|---|---|---|---|
| | | | | |

## Analysis

What the numbers say. Distinguish what was preregistered from what you noticed afterwards —
post-hoc observations are valuable and are not evidence at the same strength. Label them.

## Verdict

- **Claim status:** supported / falsified / inconclusive, in this regime
- **What changed in my beliefs:** (say what you expected beforehand — this is the record of
  whether the method is working)
- **What this cannot conclude:**
- **Notes updated:** links to the claim/idea files whose evidence class changed

## Amendment log

| Date | Change | Why |
|---|---|---|
| | | |
