# Superseded results

Kept, not deleted. These runs are the evidence that caught a design flaw, and discarding
them would erase the record of how the harness was corrected.

## E001-*-seed0.json (2026-08-11) — invalid item set

Produced before `role_swap` was fixed. The original family perturbed a dative sentence by
**swapping the two names**, which also swapped their positions. The correct answer therefore
sat in the last-mentioned position in *both* members of every pair, so the heuristic
"answer the last-named entity" scored a **flip rate of 1.0** on that family.

Consequences for these files:

- `role_swap` flip rates (gpt2 0.98 → gpt2-xl 0.68) measure recency, not reasoning. The
  apparent *decline* with scale is larger models moving away from a pure positional
  heuristic — real, but not what the family claimed to measure.
- The overall flip rate is inflated by roughly `role_swap_flip / 6` in every run.
- Every other family's numbers are unaffected, and the cross-family pattern in them is what
  identified the bug: gpt2 scored 0.98/0.03 on `comparison` and 0.04/0.96 on `transitive` —
  the signature of a single positional rule applied everywhere.

Fixed by perturbing the **verb** (`gave … to` → `received … from`) so both names hold their
positions. Guarded permanently by `tests/test_baselines.py`, and by
`uv run geom baselines`, which now runs the same admissibility check on demand.

Do not cite these numbers. Cite the re-run.
