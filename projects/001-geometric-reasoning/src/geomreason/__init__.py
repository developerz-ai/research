"""geomreason — a falsification harness for the claim that reasoning is a property of a
model's internal geometry rather than its size.

Entry points:
    geomreason.items       generate paired-perturbation items
    geomreason.evaluate    score a causal LM by option log-likelihood
    geomreason.metrics     flip rate, shortcut gap, stickiness
    geomreason.geometry    hidden-state geometric descriptors
    geomreason.device      accelerator selection (the only vendor-aware module)
    geomreason.provenance  run records
"""

__version__ = "0.1.0"
