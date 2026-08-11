# Synthesis — Geometry vs scale is an empirical question with a cheap decisive experiment

**Added:** 2026-08-11
**Status:** `[open]` until tested → `projects/001-geometric-reasoning`

## Ingredients

| Idea | From | Contributes |
|---|---|---|
| [[library/ideas/reasoning-as-internal-geometry]] | Michels/Sophontic | the claim: structure, not size, determines reasoning |
| [[library/ideas/data-quality-over-scale]] | TinyStories, phi, curriculum literature | the rival explanation for every small-model win |
| [[library/ideas/flip-rate-evaluation]] | Sophontic method + contrast-set literature | a contamination-resistant outcome measure |
| [[library/ideas/linear-representation-hypothesis]] | Park, Zou, Elhage | measurable geometric quantities, and the warning that decodability ≠ use |

## The combination

**New:** The geometry claim and the data-quality claim make *identical* predictions about
task accuracy and are therefore indistinguishable on any benchmark — but they make
*different* predictions about the relationship between hidden-state geometry and robustness.
That difference is measurable at 124M parameters, in hours, on one consumer GPU.

The argument:

- **Inherited (Sophontic):** engineering internal geometry produces reasoning that
  outperforms much larger models.
- **Inherited (literature):** curated data and curriculum ordering already produce exactly
  that outcome at exactly that scale, with no geometric intervention whatsoever.
- **New:** these two are not competing explanations of *different* results — they are
  competing explanations of the *same* result. Every published demonstration of the first
  is also a demonstration of the second, because geometry-shaping training changes the data
  distribution the model sees and curriculum-shaped training changes the geometry the model
  forms. Neither side has published the ablation that separates them.
- **Therefore:** the interesting question is not "can a small model reason?" (settled: yes,
  in narrow domains) but **"is there a geometric quantity that predicts reasoning robustness
  after controlling for parameters and training tokens?"** If yes, geometry is a real lever.
  If no, "geometric reasoning" is a redescription of data curation in unfamiliar vocabulary.

## Why nobody has said this

Because the two literatures do not read each other. The data-quality results come from
industrial labs reporting benchmark scores; the representation-geometry results come from
interpretability researchers who mostly study large models and rarely train anything. The
Sophontic framing comes from a third place again — consciousness studies — and uses
vocabulary neither of the other two recognises.

The comparison requires holding all three simultaneously, plus the willingness to treat a
vendor claim as a hypothesis rather than as either fact or nonsense.

## What it would predict

Novel prediction: **geometric metrics measured on curriculum-trained models will move in
the same direction as on geometry-trained models.** If curriculum training alone reorganises
hidden-state geometry, then geometry is a *consequence* of good training rather than an
independent lever — and the Sophontic mechanism, if it works, works for a reason its
proponents have not identified.

- **Not implied by data-quality alone:** that literature reports accuracy and says nothing
  about internal structure. It has no prediction about geometry at all.
- **Not implied by the geometry claim alone:** it predicts its own intervention works,
  and is silent about whether an unrelated intervention produces the same internal change.
- **Discriminating:** measure a geometric quantity across arms that differ only in training
  regime at matched compute. Three outcomes, all informative:

| Outcome | Reading |
|---|---|
| Geometry predicts robustness, independent of regime | Geometry is a real measurable correlate — worth pursuing as a lever |
| Geometry changes only with curriculum, not with the geometric objective | The vocabulary is new, the mechanism is not |
| Geometry uncorrelated with robustness once budget-matched | The whole framing is decorative; report it plainly |

## How it could be wrong

Most likely failure modes, in order:

1. **"Geometric density" is undefined**, so we test our own proxies and a proponent can
   always say we tested the wrong quantity. Unavoidable — mitigate by measuring several
   proxies and preregistering all of them, so the choice cannot be made after seeing results.
2. **Decodability ≠ use.** A geometric metric may correlate with robustness while being
   causally irrelevant. Correlation gets us to an interesting result; only intervention gets
   us to a mechanism.
3. **124M may be below the regime** where the effect exists. A null at this scale does not
   falsify the claim at 7B. Must be stated in the verdict rather than glossed.
4. **Our perturbation set may be flawed** in ways that make flip rate measure something else
   — see the design traps in [[library/ideas/flip-rate-evaluation]].

## Route to a claim

`projects/001-geometric-reasoning`. Cheapest first step needs **no training at all**:
measure flip rate and geometric metrics across a range of existing open models (124M → 7B).
If no geometric quantity tracks flip rate across that range once size is controlled for, the
expensive training experiment is not worth running.

That is an afternoon's work and it can kill the programme before we spend a GPU-week on it.
