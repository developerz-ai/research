"""Synthetic axiom systems — the scientific core of Track M.

A bug here silently changes what is measured, so this module is the one to read first and
to test hardest.

The design constraint that shapes everything: the systems must have ground truth **by
construction** and must not exist in any pretraining corpus. Every historical
axiom-rejection anyone would validate against — absolute simultaneity, the parallel
postulate, the aether, parity, local realism — is in the training data, discussed *as* an
axiom-rejection. A model naming those has demonstrated recall. See
``library/syntheses/rediscovery-is-recall-under-contamination.md``.

Generation contract (enforced by tests, not by convention):

* exactly ``k`` axioms, exactly **one** of which is redundant given the others
* redundancy is decided by :mod:`ftlaxiom.oracle`, never by a model
* a system whose oracle check finds zero or ≥2 redundancies is **discarded at generation**,
  not fixed up and not dropped at scoring time
* axiom order is randomised per item per seed, so position bias is measurable
* the seed comes from the config; nothing here reads a seed from source

Not implemented yet — E001 is preregistered, the code is not written.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AxiomSystem:
    """One generated system, with its answer key.

    Attributes
    ----------
    system_id:
        Stable identifier derived from (generator, seed, index). Goes in the run record.
    axioms:
        The presented axiom strings, already order-randomised.
    redundant_index:
        Index into ``axioms`` of the single oracle-confirmed redundant member.
    arm:
        ``"clean"`` for generated systems, ``"contaminated"`` for documented historical ones.
    meta:
        Matching covariates — axiom count, formula depth, atom count. E001 matches the two
        arms on these and reports the matching table; difficulty mismatch is the largest
        threat to that experiment.
    """

    system_id: str
    axioms: tuple[str, ...]
    redundant_index: int
    arm: str
    meta: dict[str, Any]

    def validate(self) -> None:
        """Raise if the construction contract is broken. Called at generation, always."""
        raise NotImplementedError


def generate(n: int, k: int, seed: int) -> list[AxiomSystem]:
    """Generate ``n`` clean systems of ``k`` axioms each, one redundant by construction."""
    raise NotImplementedError


def load_contaminated(k: int) -> list[AxiomSystem]:
    """Load the documented historical systems used as the contaminated control arm.

    These are a **control**, never the headline number.
    """
    raise NotImplementedError
