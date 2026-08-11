"""The verdict rule must not be able to report a confounded correlation as a finding.

This is the guard for a real failure: E002's first verdict function read only the primary
test and returned SUPPORTED on a partial rho of +0.692 that fell to +0.006 once the GPT-2
family was excluded. The confound check existed, was preregistered, ran, printed the
disproof — and the verdict ignored it.
"""

from __future__ import annotations

from geomreason.correlate import ModelPoint, run


def _point(model: str, params: int, flip: float, geom_scale: float) -> ModelPoint:
    """A model whose descriptors are a controllable function of geom_scale."""
    layers = [
        {
            "layer": i,
            "participation_ratio": geom_scale * i,
            "effective_rank": geom_scale * i * 2,
            "intrinsic_dim_twonn": geom_scale * i / 2,
            "anisotropy": 0.99 - geom_scale / 100,
        }
        for i in range(13)
    ]
    return ModelPoint(model=model, n_params=params, flip_rate=flip, layers=layers)


def _ladder(gpt2_geom: float, gpt2_flip: float, other_geom_by_index) -> list[ModelPoint]:
    """Four GPT-2 models at one corner, plus eight others."""
    points = [
        _point(f"gpt2-{i}", 100_000_000 * (i + 1), gpt2_flip, gpt2_geom) for i in range(4)
    ]
    points += [
        _point(f"other-{i}", 100_000_000 * (i + 1), 0.3 + 0.07 * i, other_geom_by_index(i))
        for i in range(8)
    ]
    return points


def test_confounded_correlation_is_not_reported_as_supported() -> None:
    """GPT-2 at an extreme corner; no relationship among the rest ⇒ must not be SUPPORTED."""
    report = run(_ladder(gpt2_geom=0.1, gpt2_flip=0.05, other_geom_by_index=lambda i: 5.0))
    assert report["verdict"] != "SUPPORTED", report["verdict"]
    assert not report["survives_confound_check"]


def test_report_always_carries_the_confound_check() -> None:
    report = run(_ladder(gpt2_geom=0.1, gpt2_flip=0.05, other_geom_by_index=lambda i: 5.0))
    assert "confound_check" in report
    assert "survives_confound_check" in report
    assert "primary_excluding_gpt2" in report


def test_flat_geometry_is_falsified() -> None:
    """No geometric variation at all ⇒ cannot be supported."""
    points = [
        _point(f"m-{i}", 100_000_000 * (i + 1), 0.1 * i, 1.0) for i in range(12)
    ]
    report = run(points)
    assert report["verdict"] != "SUPPORTED"


def test_verdict_vocabulary_is_closed() -> None:
    """Guard against a typo silently producing an unrecognised verdict string."""
    report = run(_ladder(gpt2_geom=0.1, gpt2_flip=0.05, other_geom_by_index=lambda i: 5.0))
    assert report["verdict"] in {
        "SUPPORTED",
        "INCONCLUSIVE",
        "FALSIFIED in this regime",
        "CONFOUNDED — correlation does not survive removing the GPT-2 family",
        "no usable primary test",
    }
