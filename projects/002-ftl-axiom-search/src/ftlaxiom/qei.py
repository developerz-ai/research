"""Track P — warp-metric energy requirement vs. quantum-energy-inequality allowance, 1+1D.

Geometrised units throughout (G = c = ħ = 1). Every quantity carries its units in the
config and a dimensional-analysis assertion runs before the integral, because a unit error
is by far the most likely way this produces a wrong scaling exponent.

What this computes and what it does not:

* **Computes** a ratio R = required / permitted, under a *stated* assumption set — field
  content, sampling interval, regulator, dimensionality.
* **Does not** compute whether FTL is possible. A bound derived under assumptions constrains
  those assumptions; it does not forbid the phenomenon. Quote the assumption list with the
  number, every time. See ``notes/out-of-scope-ftl.md``.

1+1D is a toy. Every sentence that reports a number from here names the dimension.
If R ≤ 1 anywhere in the sensible parameter range, treat it as a bug until three
independent checks say otherwise.

Not implemented yet — E003 is preregistered, the code is not written.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Assumptions:
    """The assumption set a number is only meaningful alongside.

    Serialised into every run record and into the E003 results table. This dataclass is
    also Track M's input: the assumption the ratio is most sensitive to is the one an
    axiom search would be pointed at first.
    """

    dimensions: str = "1+1"
    field_content: str = "massless minimally coupled scalar"
    sampling_interval_tau: float | None = None
    regulator: str = "unset"
    semiclassical: bool = True


def required_negative_energy(delta: float, v: float, grid_n: int) -> float:
    """Integrate T_μν u^μ u^ν over the bubble wall of a 1+1D Alcubierre-type line element."""
    raise NotImplementedError


def permitted_negative_energy(tau: float, assumptions: Assumptions) -> float:
    """Ford-Roman-type quantum energy inequality bound over the same sampling interval."""
    raise NotImplementedError


def gap_ratio(delta: float, v: float, tau: float, assumptions: Assumptions) -> dict:
    """R = required / permitted, with a Richardson grid-refinement error estimate.

    Returns the ratio, both energies, the convergence estimate, and the assumptions —
    never the ratio alone.
    """
    raise NotImplementedError
