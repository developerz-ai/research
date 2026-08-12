# E003 — Warp-metric energy requirement vs. quantum energy inequality, 1+1D

**Created:** 2026-08-12
**Status:** **preregistered** → running → analysed → verdict
**Tests:** `claim-qei-gap-is-finite`

---

## Preregistration

### Hypothesis

The ratio R = |required negative energy| / |QEI-permitted negative energy| for a 1+1D
Alcubierre-type warp bubble is finite, computable, and enormous — expected **log₁₀R in the
range 20–60** for wall thickness Δ near the Planck-to-nuclear range and v ≈ c, scaling as a
negative power of Δ.

This is a **reproduction** of a known literature result in reduced dimensionality, run for
two reasons: to verify the implementation against published closed forms, and to produce an
explicit machine-readable assumption list as Track M's input. It is not a new physics claim
and must not be written up as one.

### Metric

- **Definition:** R(Δ, v) as above, in geometrised units (G = c = ħ = 1), with the energy
  integrals taken over the bubble wall region and a fixed proper-time sampling interval τ
  along a chosen geodesic observer.
- **Numerator:** integral of T_μν u^μ u^ν from the 1+1D warp line element, evaluated on the
  grid.
- **Denominator:** a Ford-Roman-type quantum energy inequality bound for a massless minimally
  coupled scalar field over the same τ.
- **Failures:** a grid on which the integral has not converged to <1% under a resolution
  doubling is **discarded, not reported**. Non-convergence is logged with the parameters.
- **Aggregation:** R is reported per (Δ, v) grid point; the headline is the scaling exponent
  fit across Δ, with its residual.
- **Uncertainty:** grid-refinement error estimate (Richardson) per point; the exponent fit
  gets a standard error. No seed spread — this is deterministic; the "seeds" are grid
  resolutions and the fixed sampling interval, all swept.

### Decision rule

| Outcome | Interpretation |
|---|---|
| R finite, converged, log₁₀R within an order of magnitude of the published 3+1D scaling behaviour after dimensional adjustment | claim supported; implementation validated |
| R divergent or non-convergent under every regulator we can state | claim falsified — the gap framing is wrong |
| R ≤ 1 anywhere in the sensible range | **treat as a bug.** Three independent checks required before any interpretation |

Effect size: the claim is about finiteness and scaling, not about a specific magnitude.
Grid points: Δ swept over 5 decades × v ∈ {0.5, 0.9, 0.99, 1.1, 10} c.

### Baseline

The baseline is **the published analytic result**, not another run of our own code.

| Arm | What | Matched on | Notes |
|---|---|---|---|
| ours (1+1D numeric) | grid integration | — | the thing being validated |
| analytic 1+1D | closed form where one exists | same Δ, v, τ | primary correctness check |
| published 3+1D | literature values | dimensionally adjusted | sanity check only; **not** a match, and the mismatch is expected |

Compute budget matched: not applicable — this is a deterministic numerical computation, not
a model comparison. Wall-clock is reported for reproduction cost only.

### Confounds

- [x] **Unit errors.** The most likely source of a wrong exponent by far. Mitigation: every
      quantity carries its units in the config; a dimensional-analysis assertion runs before
      the integral.
- [x] **Regulator dependence.** The wall integral diverges analytically; the regulator choice
      changes R. All regulators tried are reported, not only the favourable one.
- [x] **Sampling interval choice.** The QEI bound depends strongly on τ. τ is fixed in this
      preregistration and swept only as a declared secondary analysis.
- [x] **Field content.** The bound is derived for a massless minimally coupled scalar. Other
      field content gives other bounds; this is stated with every number and not buried.
- [x] **Dimensionality.** 1+1D. Every reported sentence names the dimension.
- [ ] Contamination / tokenizer / prompt: **not applicable** — no model is involved in this
      experiment. Recorded explicitly so the absence is not mistaken for an oversight.

### Runs planned

CPU. Full sweep is minutes, not hours. `--limit` reduces the Δ grid for the smoke path.

---

## Execution

**Command:**
```bash
uv run ftl qei --delta-decades 5 --v 0.5,0.9,0.99,1.1,10 --tau <T> --out results/E003-qei-1p1d.json
```

**Result files:** `results/E003-*.json`
**Git SHA at run:**
**Hardware:**

## Results

| Δ | v | numerator | denominator | log₁₀R | grid err |
|---|---|---|---|---|---|
| | | | | | |

Fitted scaling exponent in Δ:

## Analysis

## Verdict

- **Claim status:**
- **What changed in my beliefs:** *(recorded before the run: I expect this to reproduce the
  known enormous gap. The informative output is not the number but the assumption list —
  specifically which of {energy conditions, field content, sampling interval, dimensionality,
  semiclassical approximation} the gap is most sensitive to. That list is what Track M gets
  pointed at.)*
- **What this cannot conclude:** nothing about whether FTL is possible. A bound computed
  under stated assumptions constrains those assumptions; it does not forbid the phenomenon.
  See `../notes/out-of-scope-ftl.md`.
- **Notes updated:**

## Amendment log

| Date | Change | Why |
|---|---|---|
| | | |
