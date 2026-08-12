"""Ground truth. A solver decides redundancy and consistency — never a model.

A model grading a model is not a measurement, and it is the cheapest available way to
manufacture a positive result in this project. Everything in here is deterministic.

Two checks, and they must agree or the item is discarded:

1. SMT (z3): axiom *i* is redundant iff ``{axioms} \\ {i} ⊨ i``, i.e. the negation is unsat.
2. Brute-force truth-table evaluation, for systems small enough to permit it.

Disagreement between the two means a bug, not an interesting edge case.

Not implemented yet — E001 is preregistered, the code is not written.
"""

from __future__ import annotations


def is_redundant(axioms: list[str], index: int) -> bool:
    """Is ``axioms[index]`` entailed by the rest?"""
    raise NotImplementedError


def redundant_indices(axioms: list[str]) -> list[int]:
    """Every redundant member. Generation requires exactly one."""
    raise NotImplementedError


def is_consistent(axioms: list[str]) -> bool:
    """Does a model of the axiom set exist? The label E002's falsify task is scored against."""
    raise NotImplementedError
