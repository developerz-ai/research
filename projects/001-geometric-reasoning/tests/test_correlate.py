"""Correlation maths, checked against cases with known answers.

A partial-correlation bug would silently produce or destroy the headline result of E002, so
every piece is pinned to a case where the right answer is known independently.
"""

from __future__ import annotations

import math

import pytest

from geomreason.correlate import (
    ModelPoint,
    partial,
    pearson,
    rank,
    spearman,
)


def test_pearson_perfect_positive() -> None:
    assert pearson([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)


def test_pearson_perfect_negative() -> None:
    assert pearson([1, 2, 3, 4], [8, 6, 4, 2]) == pytest.approx(-1.0)


def test_pearson_uncorrelated() -> None:
    assert abs(pearson([1, 2, 3, 4], [1, 4, 1, 4])) < 0.5


def test_rank_handles_ties_by_averaging() -> None:
    assert rank([10, 20, 20, 30]) == [1.0, 2.5, 2.5, 4.0]


def test_spearman_catches_monotone_nonlinear() -> None:
    """Spearman is primary precisely because the relationship need not be linear."""
    x = [1, 2, 3, 4, 5]
    y = [1, 4, 9, 16, 25]  # monotone but quadratic
    assert spearman(x, y) == pytest.approx(1.0)
    assert pearson(x, y) < 1.0


def test_partial_removes_a_pure_confound() -> None:
    """The case the whole experiment turns on.

    x and y are correlated *only* because both track z. Partialling z out must collapse the
    correlation. If this were broken, E002 would report a confound as a finding — which is
    precisely the error the experiment exists to avoid.

    Tested analytically rather than from constructed data. "x and y are related *only*
    through z" is exactly the condition ρ_xy = ρ_xz · ρ_yz, so the partial must be 0. Hand-
    built data is a poor way to test this — two sequences that merely *look* like noisy
    copies of z can land far from that identity and produce a large partial correctly.

    Note x = y = z exactly is also not the right test: it makes the denominator 0/0 and
    correctly yields NaN.
    """
    # ρ_xy is fully accounted for by both variables' correlation with z.
    assert partial(0.9 * 0.8, 0.9, 0.8) == pytest.approx(0.0, abs=1e-12)
    assert partial(0.5 * 0.5, 0.5, 0.5) == pytest.approx(0.0, abs=1e-12)

    # Slightly more than z explains ⇒ small positive residual, not a large one.
    residual = partial(0.9 * 0.8 + 0.05, 0.9, 0.8)
    assert 0 < residual < 0.25, residual


def test_partial_preserves_a_genuine_relationship() -> None:
    """The mirror case: when z is unrelated, partialling it out changes little."""
    x = [1, 2, 3, 4, 5, 6, 7, 8]
    y = [2, 4, 6, 8, 10, 12, 14, 16]
    z = [5, 1, 8, 2, 7, 3, 6, 4]  # unrelated to both
    rho_xy, rho_xz, rho_yz = spearman(x, y), spearman(x, z), spearman(y, z)
    assert abs(partial(rho_xy, rho_xz, rho_yz)) > 0.9


def test_partial_degenerate_returns_nan() -> None:
    assert math.isnan(partial(0.5, 1.0, 1.0))


def _point(model: str, params: int, flip: float, n_layers: int = 12) -> ModelPoint:
    layers = [
        {
            "layer": i,
            "participation_ratio": float(i),
            "effective_rank": float(i * 2),
            "intrinsic_dim_twonn": float("nan") if i == 0 else float(i) / 2,
            "anisotropy": 0.9,
        }
        for i in range(n_layers + 1)
    ]
    return ModelPoint(model=model, n_params=params, flip_rate=flip, layers=layers)


def test_relative_depth_is_comparable_across_model_depths() -> None:
    """Models have 12-36 layers; raw indices are not comparable, fractions are."""
    shallow = _point("a", 100_000_000, 0.2, n_layers=12)
    deep = _point("b", 100_000_000, 0.2, n_layers=36)
    assert shallow.at_relative_depth("participation_ratio", 1.0) == 12.0
    assert deep.at_relative_depth("participation_ratio", 1.0) == 36.0
    assert shallow.at_relative_depth("participation_ratio", 0.5) == 6.0
    assert deep.at_relative_depth("participation_ratio", 0.5) == 18.0


def test_layer_zero_excluded() -> None:
    """Layer 0 is degenerate — all prompts share a final token — and must never be used."""
    p = _point("a", 100_000_000, 0.2)
    assert p.at_relative_depth("participation_ratio", 0.0) != 0.0


def test_nan_descriptor_returns_none() -> None:
    """A NaN must propagate as 'no data', not as a number."""
    p = _point("a", 100_000_000, 0.2)
    p.layers[3]["participation_ratio"] = float("nan")
    assert p.at_relative_depth("participation_ratio", 3 / 12) is None


def test_max_over_layers_reports_peak_and_depth() -> None:
    p = _point("a", 100_000_000, 0.2)
    value, depth = p.max_over_layers("participation_ratio")
    assert value == 12.0
    assert depth == pytest.approx(1.0)


def test_log_params() -> None:
    assert _point("a", 1_000_000_000, 0.5).log_params == pytest.approx(9.0)
