"""The preregistered 24-cell depth grid must be complete, labelled, and omission-detecting.

E002's preregistration names 4 descriptors x 6 depth positions = 24 tests; the 2026-08-11
pass executed only the 16 numeric cells and the max/argmax "hump" cells never ran. These
tests pin the completed grid: exactly the preregistered cells, peak-row semantics (max =
peak VALUE, argmax = the peak's RELATIVE DEPTH), per-item provenance on the peak rows, and
a machine check that a missing cell is NAMED rather than silently skipped — so removing
any one cell from run()'s exploratory output fails here.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from geomreason.cli import RECONCILE_FIELDS, reconcile_grid
from geomreason.correlate import (
    DESCRIPTORS,
    GRID_POSITIONS,
    ModelPoint,
    cell_rows,
    run,
)

NUMERIC_POSITIONS = ("0.25", "0.5", "0.75", "1.0")


def _layers(
    i: int,
    n_layers: int = 12,
    peak_layer: int = 6,
    nan50_descriptor: str | None = None,
    nan_last_descriptor: str | None = None,
) -> list[dict]:
    """Layers 0..n_layers for model i: every descriptor rises to ``peak_layer``, then falls.

    Value at usable layer L is L*(i+1) below the peak and (2*peak_layer - L)*(i+1) above
    it, so the maximum is unique at ``peak_layer`` and its relative depth is
    ``peak_layer / n_layers``. Layer 0 is NaN (degenerate, excluded from analysis). Setting
    ``nan50_descriptor`` poisons one descriptor at the layer nearest relative depth 0.5 in
    every model, which is how a grid cell goes missing in real data.
    ``nan_last_descriptor`` poisons one descriptor at the final layer: the peak's
    denominator must stay the model's full nonzero extent, not the usable layers.
    """
    layers = [{"layer": 0, **{d: float("nan") for d in DESCRIPTORS}}]
    scales = {
        "participation_ratio": 1.0,
        "effective_rank": 2.0,
        "intrinsic_dim_twonn": 0.5,
        "anisotropy": 0.01,
    }
    for layer in range(1, n_layers + 1):
        base = layer if layer <= peak_layer else 2 * peak_layer - layer
        row = {d: base * (i + 1) * s for d, s in scales.items()}
        if nan50_descriptor is not None and layer == n_layers // 2:
            row[nan50_descriptor] = float("nan")
        if nan_last_descriptor is not None and layer == n_layers:
            row[nan_last_descriptor] = float("nan")
        layers.append({"layer": layer, **row})
    return layers


# Params deliberately non-monotone in i: a ladder whose geometry is perfectly
# rank-monotone with size drives rho(geom, size) to 1.0, the partial's denominator to 0,
# and every partial correlation to NaN — the drift pins need finite numbers to perturb.
_LADDER_PARAMS = (
    100_000_000, 400_000_000, 200_000_000, 800_000_000, 300_000_000, 700_000_000,
    500_000_000, 900_000_000, 150_000_000, 600_000_000, 250_000_000, 1_000_000_000,
)


def _ladder(**kwargs) -> list[ModelPoint]:
    return [
        ModelPoint(
            model=f"m-{i}",
            n_params=_LADDER_PARAMS[i],
            flip_rate=0.1 + 0.05 * i,
            layers=_layers(i, **kwargs),
        )
        for i in range(12)
    ]


def _by_cell(report: dict) -> dict:
    return {(r["descriptor"], r["position"]): r for r in report["exploratory"]}


def test_grid_emits_exactly_the_24_preregistered_cells() -> None:
    """Removing any one cell from run()'s exploratory output fails here."""
    report = run(_ladder())
    cells = {(r["descriptor"], r["position"]) for r in report["exploratory"]}
    assert cells == {(d, p) for d in DESCRIPTORS for p in GRID_POSITIONS}
    assert len(report["exploratory"]) == 24
    assert report["n_exploratory_tests"] == 24
    grid = report["grid"]
    assert grid["positions"] == ["0.25", "0.5", "0.75", "1.0", "max", "argmax"]
    assert grid["n_cells_preregistered"] == 24
    assert grid["n_cells_executed"] == 24
    assert grid["missing_cells"] == []
    assert grid["complete"] is True


def test_numeric_rows_carry_relative_depth_and_peak_rows_do_not() -> None:
    report = run(_ladder())
    for row in report["exploratory"]:
        if row["position"] in ("max", "argmax"):
            assert "relative_depth" not in row
        else:
            assert row["relative_depth"] == float(row["position"])
            assert "per_model" not in row


def test_unknown_position_is_refused_not_silently_treated() -> None:
    """A position outside the preregistered grid raises, naming the bad position.

    cell_rows would otherwise fall through to the peak branch and fabricate a cell
    for any typo'd position; this pins the guard, so deleting the ValueError fails.
    """
    with pytest.raises(ValueError, match=r"unknown grid position: '0\.9'"):
        cell_rows(_ladder(), "participation_ratio", "0.9")


def test_max_row_value_is_the_peak_descriptor_value() -> None:
    """Peak at layer 6 of 12 — mid-stack, not the top layer.

    The per-model peak layer indices pin WHERE the cell read; the rank correlation pins
    WHAT it read: peak values 6*(i+1) rise with flip 0.1+0.05*i, so rho is exactly 1 —
    a row built from a constant (the argmax value) would be NaN here instead.
    """
    report = run(_ladder())
    max_row = _by_cell(report)[("participation_ratio", "max")]
    assert max_row["n"] == 12
    assert [e["peak_layer"] for e in max_row["per_model"]] == [6] * 12
    assert [e["model"] for e in max_row["per_model"]] == [f"m-{i}" for i in range(12)]
    assert max_row["spearman_geom_flip"] == pytest.approx(1.0)
    # rho = 1 alone cannot catch a wrong-layer read: the depth-0.75 values (3*(i+1) here)
    # are as rank-monotone in the flip rate as the true peaks, while the peak_layer
    # metadata stays correct — so assert the cell's ACTUAL inputs, the peak values.
    rows, _ = cell_rows(_ladder(), "participation_ratio", "max")
    assert [r[0] for r in rows] == [6.0 * (i + 1) for i in range(12)]


def test_argmax_row_value_is_the_peak_relative_depth() -> None:
    """The argmax cell correlates the POSITION of the peak, not its height.

    Every peak sits at 6/12 = 0.5 relative depth, so this cell's values are constant and
    the correlation is honestly NaN — whereas the peak VALUES vary (rho = 1, previous
    test). If argmax ever regressed to reusing the peak value, this row stops being NaN.
    """
    report = run(_ladder())
    argmax_row = _by_cell(report)[("participation_ratio", "argmax")]
    assert argmax_row["n"] == 12
    assert [e["relative_peak_depth"] for e in argmax_row["per_model"]] == [0.5] * 12
    assert [e["model"] for e in argmax_row["per_model"]] == [f"m-{i}" for i in range(12)]
    assert math.isnan(argmax_row["spearman_geom_flip"])


def test_missing_final_layer_does_not_shrink_the_argmax_denominator() -> None:
    """A descriptor NaN at the FINAL layer must not change where the peak sits.

    With participation_ratio missing at layer 12, every profile still peaks at layer 6 of
    a 12-layer stack: relative depth 6/12 = 0.5. Normalizing by the max layer where the
    descriptor is *usable* instead records 6/11 ≈ 0.545 for every model — the denominator
    excluded layers with missing descriptor values (review finding, PR #10).
    """
    ladder = _ladder(nan_last_descriptor="participation_ratio")
    rows, per_model = cell_rows(ladder, "participation_ratio", "argmax")
    assert [r[0] for r in rows] == [0.5] * 12
    assert [e["relative_peak_depth"] for e in per_model] == [0.5] * 12
    # The missing final layer changes the denominator only: the peak's identity and value
    # are untouched, so the max cell still reads layer 6 with values 6*(i+1).
    max_rows, max_per_model = cell_rows(ladder, "participation_ratio", "max")
    assert [e["peak_layer"] for e in max_per_model] == [6] * 12
    assert [r[0] for r in max_rows] == [6.0 * (i + 1) for i in range(12)]
    report = run(ladder)
    argmax_row = _by_cell(report)[("participation_ratio", "argmax")]
    assert argmax_row["n"] == 12
    assert math.isnan(argmax_row["spearman_geom_flip"])


def test_primary_cell_is_the_075_grid_cell() -> None:
    """The preregistered primary test IS the 0.75 cell; the two views must agree."""
    report = run(_ladder())
    cells = _by_cell(report)
    primary = {r["descriptor"]: r for r in report["primary"]}
    for d in DESCRIPTORS:
        assert cells[(d, "0.75")]["partial_spearman"] == primary[d]["partial_spearman"]


def test_missing_cell_is_named_not_skipped() -> None:
    """effective_rank is NaN at the layer nearest depth 0.5 in every model: exactly that
    cell disappears — and the grid must name it rather than silently shrink."""
    report = run(_ladder(nan50_descriptor="effective_rank"))
    grid = report["grid"]
    assert grid["complete"] is False
    assert grid["missing_cells"] == [["effective_rank", "0.5"]]
    assert grid["n_cells_executed"] == 23
    assert len(report["exploratory"]) == 23
    assert report["n_exploratory_tests"] == 23


def test_too_few_models_leaves_every_cell_missing() -> None:
    report = run(_ladder()[:3])
    grid = report["grid"]
    assert grid["complete"] is False
    assert grid["n_cells_executed"] == 0
    assert grid["missing_cells"] == [[d, p] for d in DESCRIPTORS for p in GRID_POSITIONS]
    assert report["verdict"] == "no usable primary test"


def _prior_from(report: dict, timestamp: str = "2026-08-11T17:07:08+00:00") -> dict:
    """A prior record in the shape of results/E002-correlation.json: numeric cells only."""
    keep = {"descriptor", "relative_depth", *RECONCILE_FIELDS}
    return {
        "timestamp_utc": timestamp,
        "metrics": {
            "exploratory": [
                {k: v for k, v in row.items() if k in keep}
                for row in report["exploratory"]
                if "relative_depth" in row
            ]
        },
    }


def _statuses(reconciliation: dict) -> dict:
    return {
        (c["descriptor"], c["position"]): c["status"] for c in reconciliation["cells"]
    }


def test_reconciliation_labels_reproduced_and_completed() -> None:
    report = run(_ladder())
    reconciliation = reconcile_grid(report, _prior_from(report))
    status = _statuses(reconciliation)
    completed_label = f"completed {datetime.now(UTC).date().isoformat()}"
    for d in DESCRIPTORS:
        for p in NUMERIC_POSITIONS:
            assert status[(d, p)] == "executed 2026-08-11 (reproduced)"
        for p in ("max", "argmax"):
            assert status[(d, p)] == completed_label
    assert reconciliation["n_reproduced"] == 16
    assert reconciliation["n_drifted"] == 0
    assert reconciliation["n_completed"] == 8
    assert reconciliation["prior_timestamp_utc"] == "2026-08-11T17:07:08+00:00"


def test_reconciliation_flags_drift_on_any_mismatch() -> None:
    report = run(_ladder())
    prior = _prior_from(report)
    prior["metrics"]["exploratory"][0]["partial_spearman"] += 0.001
    reconciliation = reconcile_grid(report, prior)
    first = report["exploratory"][0]
    status = _statuses(reconciliation)
    assert status[(first["descriptor"], first["position"])] == "executed 2026-08-11 (DRIFT)"
    assert reconciliation["n_drifted"] == 1
    assert reconciliation["n_reproduced"] == 15


def test_reconciliation_treats_nan_as_equal_not_drift() -> None:
    report = run(_ladder())
    prior = _prior_from(report)
    report["exploratory"][0]["pearson_geom_flip"] = float("nan")
    prior["metrics"]["exploratory"][0]["pearson_geom_flip"] = float("nan")
    assert reconcile_grid(report, prior)["n_drifted"] == 0


def test_reconciliation_without_prior_completes_every_cell() -> None:
    reconciliation = reconcile_grid(run(_ladder()), None)
    assert reconciliation["n_completed"] == 24
    assert reconciliation["n_reproduced"] == 0
    assert reconciliation["n_drifted"] == 0
    assert reconciliation["prior_timestamp_utc"] is None


def test_reconciliation_compares_every_stats_field() -> None:
    assert set(RECONCILE_FIELDS) == {
        "n",
        "spearman_geom_flip",
        "spearman_geom_size",
        "partial_spearman",
        "pearson_geom_flip",
    }
