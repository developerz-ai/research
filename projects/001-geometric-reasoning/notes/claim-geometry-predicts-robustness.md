# Claim — A geometric descriptor predicts reasoning robustness independently of size

**ID:** `claim-geometry-predicts-robustness`
**Added:** 2026-08-11
**Class:** `[open]`
**Descends from:** [[library/ideas/reasoning-as-internal-geometry]] · [[library/syntheses/geometry-vs-scale-is-empirical]]

## Proposition

Across open causal LMs from 124M to 1.5B parameters, at least one hidden-state geometric
descriptor (participation ratio, effective rank, TwoNN intrinsic dimension, anisotropy)
correlates with flip rate on freshly generated paired-perturbation items **after partialling
out log parameter count**, with |partial r| ≥ 0.5.

## Falsifier

> This claim is dead if: no descriptor, at any layer depth, reaches |partial r| ≥ 0.3 with
> flip rate once log-parameters is partialled out — across ≥6 models and ≥3 item seeds.

Written before any code that produces the number. The 0.3 floor is deliberately more
generous than the 0.5 the claim asserts, so that "supported", "dead", and "inconclusive"
are three distinct outcomes rather than two.

## Operationalisation

The gap between the source's vocabulary and something measurable is where the intellectual
work is, and every choice below is a place the test could fail to be a test of the claim.

| Term in the claim | How it is measured | What this choice could get wrong |
|---|---|---|
| "internal geometry" | Four descriptors of last-token hidden states per layer | The source never defines "geometric density". A proponent can always say we measured the wrong quantity — which is why all four are preregistered together rather than chosen after the fact. |
| "reasoning" | Flip rate on 6 synthetic families | Synthetic templates are not reasoning in general. They are contamination-proof, which no natural benchmark is. |
| "independently of size" | Partial correlation controlling log-params | Open models differ in training tokens and data too. Params is a weak control — the honest ceiling on this design. |
| "robustness" | Both members of a pair correct | Sensitive to item quality; guarded by `Pair.validate()` and the item tests. |
| layer choice | Every layer; report the max and the profile | Multiple comparisons across layers inflate the best correlation. Report the whole profile, not just the peak. |

## Current evidence

| Class | Evidence | Where |
|---|---|---|
| `[source]` | Michels asserts geometry determines reasoning | [[library/sources/michels-sophontic-interview]] C1 |
| `[lit]` | Representation geometry is real, measurable, causally relevant | [[library/ideas/linear-representation-hypothesis]] |
| `[lit]` | Rival explanation: data quality/curriculum produces the same outcome with no geometry | [[library/ideas/data-quality-over-scale]] |
| `[ours]` | **No descriptor survives.** Best \|partial ρ\| = 0.006 across 16 models once size is controlled and GPT-2 is removed. Raw ρ up to +0.850 is entirely mediated by size. | `experiments/E002-geometry-vs-robustness.md` |

## Cheap test first

E001/E002 on existing open models. **No training.** Under an hour on the reference box, and
it can kill the programme before a GPU-week is spent: if nothing correlates across a ladder
of models that already differ enormously in geometry, an auxiliary geometry loss is unlikely
to be the missing lever.

## Reachability

Reachable at 124M–1.5B on a 24GB card, and on CPU at reduced item counts. **Not** reachable
at 7B+ for the training follow-up. If E002 comes back positive, the natural next experiment
(train matched models with and without a geometry-shaping loss) is reachable only at ≤1B —
that limit goes in the verdict rather than being discovered later.

## Known weakness of this design

Partialling out parameter count does **not** control for training tokens or data quality,
which differ across open models and are the rival explanation. A positive result here is
therefore suggestive, not decisive — it would justify the matched-training experiment, not
substitute for it. A negative result is stronger: if nothing correlates even *without*
proper controls, adding controls will not create a correlation.

Asymmetric evidential value is a reason to run it, not a flaw to hide.

## Status log

| Date | Class | Change |
|---|---|---|
| 2026-08-11 | `[open]` | created, falsifier fixed before implementation |
| 2026-08-11 | `[ours]` | **Confounded, trending falsified.** E002: best surviving partial ρ = 0.006 vs a 0.3 falsification threshold. The apparent +0.692 was the GPT-2 family sitting in one corner — old models have both worse geometry and worse reasoning, with nothing linking the two. Scoped: our descriptors, one depth, 16 uncontrolled models, no intervention tested. |
