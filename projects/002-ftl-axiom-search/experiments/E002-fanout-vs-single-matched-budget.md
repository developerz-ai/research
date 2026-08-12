# E002 — Fan-out vs. one agent, at matched token budget

**Created:** 2026-08-12
**Status:** **preregistered** → running → analysed → verdict
**Tests:** `claim-fanout-beats-single`

---

## Preregistration

### Hypothesis

On deciding whether a modified axiom set is consistent, N=5 independent agents at budget B/5
each reach higher balanced accuracy than one agent at budget B. Expected direction:
**fan-out > single**, by ≥0.10 balanced accuracy.

The alternative being discriminated against: agents sharing a base model make correlated
errors, so five votes are worth barely more than one, and the single agent's longer chain of
reasoning wins outright. Prior belief leans toward this alternative on the falsify task being
close, and toward the single agent clearly winning on the generative task.

### Metric

- **Definition:** balanced accuracy = (TPR + TNR)/2 over a 50/50 consistent/inconsistent set.
  Fan-out arm's answer is majority vote over N; ties (impossible at odd N) not applicable.
- **Ties:** N is odd. If an agent returns no parseable verdict, it abstains and the majority
  is taken over the remainder; an all-abstain item counts as **incorrect**.
- **Malformed / refusal:** counted incorrect, rate reported separately per arm.
- **Aggregation:** unweighted over items.
- **Uncertainty:** Wilson CI per arm; paired bootstrap (10k) over items for the arm
  difference; min–max across ≥3 seeds.
- **Secondary metric — inter-agent error correlation:** mean pairwise phi over per-item
  correctness vectors within the fan-out arm. Reported always, whatever the headline says.

### Decision rule

| Outcome | Interpretation |
|---|---|
| fan-out − single ≥ +0.10, CI excludes 0 | claim supported in this regime |
| fan-out − single ≤ 0, CI excludes 0 | claim falsified |
| between, or CI includes 0 | inconclusive |

Independent of the above, **phi ≥0.8 voids the mechanism** the claim proposes even if the
headline is positive. That is reported as a separate line, not folded into the verdict.

Effect size worth caring about: 0.10 balanced accuracy.
Items needed: 300 (150/150) gives ≈±0.055 half-width per arm; the paired bootstrap on the
difference is tighter since items are shared.

### Baseline

**The single agent at full budget B is the baseline, and it is the whole experiment.** A
fan-out result without it is unreadable.

| Arm | Agents | Budget each | Total output tokens | Notes |
|---|---|---|---|---|
| fan-out | 5 | B/5 | B ±5% | same model, same prompt, different sampling seed |
| single | 1 | B | B ±5% | identical model and decoding temperature |
| chance | — | — | — | 0.50 by construction |

Budget unit: **total output tokens**, equal within 5%, verified from the run record and not
from the config. Named explicitly because this unit favours fan-out — it ignores the prompt
tokens fan-out pays five times. A wall-clock-matched and a dollar-matched restatement of the
same runs are reported as secondary columns.

### Confounds

- [x] **Budget accounting error** — the single most likely way this experiment produces a
      wrong answer. Verified post-hoc from token counts in the run record; a >5% mismatch
      invalidates the run rather than being corrected by rescaling.
- [x] **Prompt asymmetry** — the fan-out prompt and the single-agent prompt must ask for the
      same thing. Both fixed before the run and stored in the record.
- [x] **Refusal skew** — a skeptic-primed refuter can score by always refusing; the 50/50
      split and balanced accuracy are the control.
- [x] **Contamination** — items come from E001's generator, so the same freshness argument
      applies.
- [x] **Item order effects** — independent single-turn queries.
- [x] **Selection after seeing results** — item set frozen before scoring; N fixed at 5 in
      advance (sweeping N post-hoc and reporting the best is the obvious way to fool
      ourselves here, and is forbidden without an amendment entry).
- [ ] Other: temperature. Fan-out needs sampling diversity; the single agent is run at the
      same temperature so the comparison is not a temperature comparison in disguise.

### Runs planned

3 seeds × 2 arms × 300 items, small local model. Generative-half sub-experiment (propose
which axiom to drop) on the same items, same budget rule, reported separately — the claim
predicts fan-out does **not** win there, and a fan-out win there would be as informative as a
loss on the falsify half.

---

## Execution

**Command:**
```bash
uv run ftl falsify --arm fanout --n 5 --budget <B> --model <M> --seed 0 --out results/E002-fanout-seed0.json
uv run ftl falsify --arm single --n 1 --budget <B> --model <M> --seed 0 --out results/E002-single-seed0.json
```

**Result files:** `results/E002-*.json`
**Git SHA at run:**
**Hardware:**

## Results

| Arm | Seed | Balanced acc | CI | Output tokens | Abstain rate | n |
|---|---|---|---|---|---|---|
| | | | | | | |

Inter-agent error correlation (phi):

## Analysis

## Verdict

- **Claim status:**
- **What changed in my beliefs:** *(recorded before the run: I expect fan-out to win the
  falsify half by less than the claimed 0.10, and inter-agent phi to come out high enough —
  0.6+ — that the disjunction argument is weaker than the source implies.)*
- **What this cannot conclude:**
- **Notes updated:**

## Amendment log

| Date | Change | Why |
|---|---|---|
| | | |
