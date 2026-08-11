"""Geometric descriptors, checked against clouds whose true structure is known.

These metrics are our stand-in for an undefined term. If they do not behave correctly on
synthetic data with a known answer, nothing they say about a real model can be trusted.
"""

from __future__ import annotations

import numpy as np
import pytest

from geomreason.geometry import (
    anisotropy,
    describe_layer,
    effective_rank,
    intrinsic_dim_twonn,
    participation_ratio,
)


def test_participation_ratio_isotropic_equals_dimension() -> None:
    """Equal variance in every direction ⇒ PR = ambient dimension."""
    assert participation_ratio(np.ones(64)) == pytest.approx(64.0)


def test_participation_ratio_rank_one_equals_one() -> None:
    """All variance in one direction ⇒ PR = 1, regardless of ambient dimension."""
    eigenvalues = np.zeros(64)
    eigenvalues[0] = 10.0
    assert participation_ratio(eigenvalues) == pytest.approx(1.0)


def test_participation_ratio_between_extremes() -> None:
    eigenvalues = np.array([10.0, 5.0, 1.0, 0.1])
    assert 1.0 < participation_ratio(eigenvalues) < 4.0


def test_effective_rank_isotropic_equals_dimension() -> None:
    assert effective_rank(np.ones(32)) == pytest.approx(32.0, rel=1e-6)


def test_effective_rank_rank_one() -> None:
    eigenvalues = np.zeros(32)
    eigenvalues[0] = 1.0
    assert effective_rank(eigenvalues) == pytest.approx(1.0)


def test_effective_rank_sees_tail_that_pr_misses() -> None:
    """A long tail of small components moves effective rank more than PR.

    This is why both are recorded: superposition lives in that tail.
    """
    spiked = np.array([100.0] + [0.01] * 200)
    assert effective_rank(spiked) > participation_ratio(spiked)


def test_twonn_recovers_low_dimensional_manifold() -> None:
    """A 2D plane embedded in 50D should read as ~2 dimensions, not 50."""
    rng = np.random.default_rng(0)
    latent = rng.normal(size=(600, 2))
    basis = rng.normal(size=(2, 50))
    estimate = intrinsic_dim_twonn(latent @ basis)
    assert 1.5 < estimate < 3.0, estimate


def test_twonn_recovers_higher_dimension() -> None:
    rng = np.random.default_rng(1)
    latent = rng.normal(size=(800, 6))
    basis = rng.normal(size=(6, 50))
    estimate = intrinsic_dim_twonn(latent @ basis)
    assert 4.0 < estimate < 9.0, estimate


def test_twonn_rejects_tiny_sample() -> None:
    with pytest.raises(ValueError, match="at least"):
        intrinsic_dim_twonn(np.random.default_rng(0).normal(size=(5, 10)))


def test_twonn_returns_nan_on_degenerate_cloud() -> None:
    """Duplicated points make the estimator undefined — report, do not fabricate."""
    x = np.ones((50, 10))
    assert np.isnan(intrinsic_dim_twonn(x))


def test_anisotropy_high_for_narrow_cone() -> None:
    """Vectors clustered around one direction ⇒ mean cosine near 1."""
    rng = np.random.default_rng(2)
    x = np.tile(np.array([1.0] + [0.0] * 19), (200, 1)) + rng.normal(scale=0.01, size=(200, 20))
    assert anisotropy(x) > 0.95


def test_anisotropy_low_for_isotropic_cloud() -> None:
    rng = np.random.default_rng(3)
    assert abs(anisotropy(rng.normal(size=(400, 40)))) < 0.15


def test_describe_layer_reports_every_descriptor() -> None:
    rng = np.random.default_rng(4)
    latent = rng.normal(size=(300, 3))
    activations = latent @ rng.normal(size=(3, 64))

    result = describe_layer(activations, layer=5)
    assert result.layer == 5
    assert result.n_samples == 300
    assert result.ambient_dim == 64
    # A rank-3 cloud in 64 dimensions: every dimensionality measure should say ~3.
    assert result.participation_ratio < 6
    assert result.effective_rank < 6
    assert 1.5 < result.intrinsic_dim_twonn < 5.0
    assert set(result.as_dict()) == {
        "layer", "n_samples", "ambient_dim", "participation_ratio",
        "effective_rank", "intrinsic_dim_twonn", "anisotropy", "mean_norm",
    }


def test_describe_layer_rejects_wrong_shape() -> None:
    with pytest.raises(ValueError, match="expected"):
        describe_layer(np.zeros((10, 10, 10)), layer=0)
