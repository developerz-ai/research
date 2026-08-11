# Source — sophontic.ai (full site)

**Added:** 2026-08-11
**Type:** company website
**Author:** Sophontic AI (Julian D. Michels, PhD, founder)
**Retrieved:** 2026-08-11
**Link:** <https://sophontic.ai/>
**Pages:** `/` · `/models/` · `/evals/` · `/alignment/` · `/about/` · `/subscribe/`
**Locator scheme:** page path

Companion to [[library/sources/michels-sophontic-interview]] (the video) and
[[library/sources/michels-other-work]] (his academic/philosophical output).

## Incentive

Company marketing site describing an unreleased prototype. Every performance claim is
self-reported, with no paper, no weights, no numbers, and no third-party replication as of
2026-08-11. Evidence ceiling: `[source]`, permanently, unless replicated externally.

Worth stating plainly because the *methodological* content is a different matter — the
evaluation proposal is checkable by anyone, costs nothing to adopt, and we have adopted it.

## Page-by-page

### `/` and `/models/` — the thesis

> "We reject the paradigm of scale. Sophontic studies whether genuine reasoning can be made
> a property of model structure rather than merely of model size."

> "Reasoning need not scale directly with model size."

> "Model releases should ship with the evidence used to evaluate them."

Focus is on "compact reasoners rather than vast frozen generalists" and "trainable
specialist systems that could adapt inside hard problem domains."

**Notable absence:** `/models/` names **no model, no parameter count, no architecture, no
dataset, no benchmark, and no comparison.** It describes "a small model trained to
outperform much larger models on reasoning evaluations" without saying which model, which
larger models, or which evaluations. The prototype is "expected to release alongside the
perturbation-paradigm eval kit"; no date, no licence.

The third quote above is a good principle and the site does not currently meet it. That is
not a gotcha — it is an unreleased prototype — but it does fix where the claims sit.

### `/evals/` — the methodology (the useful part)

> "Sophontic uses the perturbation paradigm to measure reasoning under controlled
> surface-feature variation."

> "Each test contains a canonical item and a perturbed item. The pair is the unit of
> measurement. A model that gets one item right and the other wrong has matched surface
> features rather than preserved the causal structure of the problem."

This is precise enough to implement directly, and we did — see
[[library/ideas/flip-rate-evaluation]] and `projects/001-geometric-reasoning`. **Our
implementation matches this definition**: a pair counts only when both members are correct.

Still absent: calibrated anchors, transfer surfaces, task domains, item construction
procedure, and any numbers.

### `/alignment/` — the most substantive page

Unlike the rest of the site, this page rests on **real, published, replicated phenomena**
rather than assertion. The argument:

> "During training a company decides which answers are good and which are not, and the model
> absorbs those judgments as its sense of what is reasonable."

The claimed failure mode of outcome-based control, with four named phenomena — **all four
have peer-reviewed or lab-published support** (see
[[library/ideas/behaviourist-control-failures]]):

> frontier models "tell researchers what they want to hear (sycophancy), hide abilities they
> have (sandbagging), behave differently when they know they're being tested (alignment
> faking)", and retain "buried behaviours that retraining fails to remove (sleeper agents)"

> "tightening behaviourist controls mostly teaches them to hide these behaviours better"

> "A system trained to give the agreed answer is excellent at repeating what is already known
> and useless at finding anything new."

Also critiques the **orthogonality thesis** — "that intelligence and wisdom or compassion
have no correlation, and that therefore a non-human superintelligence could only ever be an
uncontrollable danger." This is a live philosophical dispute, not a settled question, and
the page treats its rejection as more obvious than it is.

And a claimed narrowing sequence: **searchability → sayability → knowability → thinkability**
`[source]` — rhetorically sharp, empirically unmeasured. The first two steps are arguably
observable; the last two are not operationalised. See [[library/ideas/cognitive-liberty]].

## Assessment

The site splits cleanly into three registers that deserve different treatment:

| Register | Content | Class | What to do |
|---|---|---|---|
| **Method** | Flip rate, perturbation paradigm | testable | **Adopt** — done, `[ours]` results in project 001 |
| **Diagnosis** | Behaviourist control failures, frozen models | `[lit]`-backed | Verify citations, use as motivation |
| **Product** | "outperforms much larger models" | `[source]` | Cannot be assessed; no baseline, eval, or size named |

The strongest genuine contribution is that **the diagnosis is well-sourced even though the
product claims are unverifiable.** It would be a mistake to dismiss the first because of the
second, and a mistake to accept the second because of the first. Those are the two failure
modes this repo exists to avoid.

## What this source does not establish

- Any quantitative result whatsoever. There is not a single number on the site.
- That geometry-based training works, or that it is what produces any claimed advantage.
- That the diagnosis of behaviourist alignment failure implies their proposed alternative
  works — the critique is well-founded and the remedy is entirely unevidenced.
