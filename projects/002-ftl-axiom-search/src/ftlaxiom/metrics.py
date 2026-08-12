"""Metrics. The headline is a paired difference, never a raw accuracy.

A high clean-set score alongside an equally high contaminated-set score is fully consistent
with pure recall. Only the delta discriminates, which is why
:func:`contamination_delta` — and not :func:`identification_accuracy` — is what E001
reports at the top.

Scoring rules fixed in the preregistrations and enforced here:

* a malformed or absent answer scores **incorrect**, never dropped; dropping turns a
  format-compliance failure into a silent accuracy boost
* the malformed rate is returned alongside every accuracy, not separately
* an all-abstain item in the fan-out arm scores incorrect

Not implemented yet — E001/E002 are preregistered, the code is not written.
"""

from __future__ import annotations


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval. Normal approximation is wrong near 0 and 1, which is where
    a near-chance clean arm will sit."""
    raise NotImplementedError


def identification_accuracy(predicted: list[int | None], truth: list[int]) -> dict:
    """Accuracy plus malformed rate. ``None`` means unparseable and counts as wrong."""
    raise NotImplementedError


def contamination_delta(contaminated: dict, clean: dict) -> dict:
    """The E001 headline: contaminated − clean, with a bootstrap CI over items."""
    raise NotImplementedError


def balanced_accuracy(predicted: list[bool | None], truth: list[bool]) -> dict:
    """Mean of TPR and TNR. Stops a skeptic-primed refuter from scoring by always refusing."""
    raise NotImplementedError


def error_correlation(correctness: list[list[bool]]) -> float:
    """Mean pairwise phi over per-item correctness vectors across agents.

    Reported by E002 **always**, whatever the headline says: N agents sharing one base model
    are worth far fewer than N independent votes, and a high phi voids the disjunction
    argument that motivates fan-out at all.
    """
    raise NotImplementedError
