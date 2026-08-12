"""Scaffold tests.

These check that the harness is wired and that the *contracts* the experiments depend on
are asserted somewhere. They are deliberately not tests of any measurement — no measurement
code exists yet.

The real tests to write, in order, when the code lands:

* ``systems``: the generation contract holds for thousands of seeds — exactly one redundant
  axiom, oracle-confirmed, order randomised. This is the test that stops a silent change in
  what E001 measures.
* ``oracle``: SMT and brute-force agree on every generated system.
* ``metrics``: a malformed answer scores incorrect rather than being dropped.
* ``qei``: dimensional-analysis assertions fire on a deliberately wrong unit.
"""

from __future__ import annotations

import pytest

from ftlaxiom import metrics, oracle, qei, systems
from ftlaxiom.device import get_device_info


def test_device_resolves():
    info = get_device_info()
    assert info.backend in ("cuda", "rocm", "xpu", "cpu")
    assert info.device is not None


def test_cpu_path_is_reachable():
    """Every experiment must run on CPU — it is the correctness reference."""
    info = get_device_info()
    assert info.backend == "cpu" or info.is_accelerated


@pytest.mark.parametrize(
    "call",
    [
        lambda: systems.generate(n=1, k=5, seed=0),
        lambda: oracle.is_consistent(["a"]),
        lambda: metrics.wilson_ci(1, 2),
        lambda: qei.gap_ratio(1.0, 0.9, 1.0, qei.Assumptions()),
    ],
)
def test_unimplemented_surfaces_are_explicit(call):
    """Stubs raise rather than returning a plausible wrong number.

    A stub that silently returns 0.0 is how a scaffold turns into a fabricated result.
    """
    with pytest.raises(NotImplementedError):
        call()
