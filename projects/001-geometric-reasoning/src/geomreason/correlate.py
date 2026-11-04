"""Partial correlation between geometric descriptors and reasoning robustness.

Implements the E002 preregistration. Everything here is decided in
``experiments/E002-geometry-vs-robustness.md`` before this file existed: which descriptors,
which depths, which is primary, which threshold, and how multiplicity is handled.

The preregistered grid is 4 descriptors x 6 depth positions = 24 cells: the four numeric
relative depths plus the max/argmax "hump" positions over layers. The 2026-08-11 pass
executed only the 16 numeric cells; ``run`` now covers the full grid and NAMES any cell it
cannot execute rather than silently dropping it. Exploratory cells never influence the
verdict below — the preregistered decision reads the primary tests only.

**This design supports no causal claim**, whatever the numbers say. Models differ in data,
tokenizer, depth and recipe simultaneously; parameter count is a weak control. A positive
result justifies the matched-training experiment. A null is the stronger outcome.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

# Preregistered: sampled at relative depth, since models differ in layer count.
RELATIVE_DEPTHS = (0.25, 0.50, 0.75, 1.00)
DESCRIPTORS = ("participation_ratio", "effective_rank", "intrinsic_dim_twonn", "anisotropy")
PRIMARY_DEPTH = 0.75  # preregistered as THE primary test; everything else is exploratory
SUPPORT_THRESHOLD = 0.5
FALSIFY_THRESHOLD = 0.3

# The full preregistered grid (E002 lines 55-63): 4 descriptors x 6 depth positions.
# "max" is the peak descriptor VALUE per model; "argmax" the RELATIVE DEPTH where the peak
# sits (the Valeriani "hump" position). Labels are the agreed record vocabulary.
GRID_POSITIONS = ("0.25", "0.5", "0.75", "1.0", "max", "argmax")
PRIMARY_POSITION = "0.75"  # the primary test, as a grid label
_POSITION_FRACTIONS = dict(zip(GRID_POSITIONS[:4], RELATIVE_DEPTHS))
assert _POSITION_FRACTIONS[PRIMARY_POSITION] == PRIMARY_DEPTH


def rank(values: list[float]) -> list[float]:
    """Fractional ranks, ties averaged — the basis of Spearman."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        shared = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = shared
        i = j + 1
    return ranks


def pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 3:
        return float("nan")
    mx, my = sum(x) / n, sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    return num / (dx * dy) if dx > 0 and dy > 0 else float("nan")


def spearman(x: list[float], y: list[float]) -> float:
    return pearson(rank(x), rank(y))


def partial(rho_xy: float, rho_xz: float, rho_yz: float) -> float:
    """Correlation of x and y with z partialled out."""
    denom = math.sqrt((1 - rho_xz**2) * (1 - rho_yz**2))
    return (rho_xy - rho_xz * rho_yz) / denom if denom > 1e-12 else float("nan")


@dataclass
class ModelPoint:
    """One model: its reasoning score, its size, and its geometry."""

    model: str
    n_params: int
    flip_rate: float
    layers: list[dict]

    @property
    def log_params(self) -> float:
        return math.log10(self.n_params)

    def at_relative_depth(self, descriptor: str, fraction: float) -> float | None:
        """Descriptor value at a fraction of total depth, nearest layer.

        Layer 0 is excluded: every prompt ends with the same token, so layer-0 last-token
        states are duplicates and the manifold estimators are undefined there.
        """
        usable = [lay for lay in self.layers if lay["layer"] > 0]
        if not usable:
            return None
        target = fraction * max(lay["layer"] for lay in usable)
        nearest = min(usable, key=lambda lay: abs(lay["layer"] - target))
        value = nearest.get(descriptor)
        return None if value is None or (isinstance(value, float) and math.isnan(value)) else value

    def peak_layer(self, descriptor: str) -> dict | None:
        """The layer holding the descriptor's peak: index, value, and relative depth.

        Same layer-0 exclusion as ``at_relative_depth``. The relative depth of the peak is
        the Valeriani "hump" position — WHERE in the stack the descriptor peaks — and is
        normalized by the model's FULL nonzero layer extent, not by the layers where this
        descriptor happens to be usable: a descriptor that is NaN at the final layer must
        not make a layer-6 peak sit at 6/11 instead of 6/12.
        """
        nonzero = [lay for lay in self.layers if lay["layer"] > 0]
        usable = [
            lay for lay in nonzero
            if lay.get(descriptor) is not None
            and not math.isnan(lay[descriptor])
        ]
        if not usable:  # usable ⊆ nonzero, so nonzero is non-empty here too
            return None
        extent = max(lay["layer"] for lay in nonzero)
        best = max(usable, key=lambda lay: lay[descriptor])
        return {
            "layer": best["layer"],
            "value": best[descriptor],
            "relative_depth": best["layer"] / extent,
        }

    def max_over_layers(self, descriptor: str) -> tuple[float, float] | None:
        """Peak value and the relative depth it occurs at — the Valeriani 'hump'."""
        peak = self.peak_layer(descriptor)
        return None if peak is None else (peak["value"], peak["relative_depth"])


def load_points(results_dir: Path, geometry_experiment: str = "E002") -> list[ModelPoint]:
    """Join geometry records with flip-rate records, by model name."""
    flip: dict[str, dict] = {}
    for path in sorted(results_dir.glob("E001*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        model = record.get("config", {}).get("model")
        rate = record.get("metrics", {}).get("flip_rate")
        if model is None or rate is None:
            continue
        # Average across seeds where several exist.
        entry = flip.setdefault(model, {"rates": [], "n_params": record["config"].get("n_params")})
        entry["rates"].append(rate)

    points: list[ModelPoint] = []
    for path in sorted(results_dir.glob(f"{geometry_experiment}-geom-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        model = record.get("config", {}).get("model")
        if model not in flip:
            continue
        rates = flip[model]["rates"]
        points.append(
            ModelPoint(
                model=model,
                n_params=record["config"]["n_params"],
                flip_rate=sum(rates) / len(rates),
                layers=record.get("metrics", {}).get("layers", []),
            )
        )
    return points


def cell_rows(
    points: list[ModelPoint], descriptor: str, position: str
) -> tuple[list[tuple], list[dict]]:
    """Per-model measurements for one grid cell: (descriptor value, flip, log params).

    Numeric positions sample the descriptor at a relative depth (nearest layer). "max"
    takes each model's peak descriptor VALUE, carrying the peak layer index as per-item
    provenance; "argmax" takes the RELATIVE DEPTH of that peak. Layer 0 is excluded in
    every case: every prompt ends with the same token, so layer-0 last-token states are
    duplicates and the manifold estimators are undefined there.
    """
    fraction = _POSITION_FRACTIONS.get(position)
    if fraction is None and position not in ("max", "argmax"):
        raise ValueError(f"unknown grid position: {position!r}")
    rows: list[tuple] = []
    per_model: list[dict] = []
    for p in points:
        if fraction is not None:
            value = p.at_relative_depth(descriptor, fraction)
        else:
            peak = p.peak_layer(descriptor)
            value = None
            if peak is not None:
                if position == "max":
                    value = peak["value"]
                    per_model.append({"model": p.model, "peak_layer": peak["layer"]})
                else:  # argmax
                    value = peak["relative_depth"]
                    per_model.append({
                        "model": p.model,
                        "relative_peak_depth": peak["relative_depth"],
                    })
        if value is not None:
            rows.append((value, p.flip_rate, p.log_params))
    return rows, per_model


def _stats_row(
    descriptor: str,
    position: str,
    fraction: float | None,
    rows: list[tuple],
    per_model: list[dict],
) -> dict | None:
    """Partial-correlation row for one cell, or None when fewer than 4 models have data."""
    if len(rows) < 4:
        return None
    geom = [r[0] for r in rows]
    flip = [r[1] for r in rows]
    size = [r[2] for r in rows]

    rho_gf = spearman(geom, flip)
    rho_gs = spearman(geom, size)
    rho_fs = spearman(flip, size)

    row: dict = {"descriptor": descriptor, "position": position}
    if fraction is not None:
        row["relative_depth"] = fraction
    row.update({
        "n": len(rows),
        "spearman_geom_flip": round(rho_gf, 4),
        "spearman_geom_size": round(rho_gs, 4),
        "spearman_flip_size": round(rho_fs, 4),
        "partial_spearman": round(partial(rho_gf, rho_gs, rho_fs), 4),
        "pearson_geom_flip": round(pearson(geom, flip), 4),
    })
    if per_model:
        # No aggregate without per-item data behind it: peak rows carry each model's peak.
        row["per_model"] = per_model
    return row


def cell_correlate(points: list[ModelPoint], descriptor: str, position: str) -> dict | None:
    """Partial correlation for one preregistered grid cell; None when the cell has no data."""
    rows, per_model = cell_rows(points, descriptor, position)
    return _stats_row(descriptor, position, _POSITION_FRACTIONS.get(position), rows, per_model)


def run(points: list[ModelPoint]) -> dict:
    """Full preregistered analysis: primary tests, exploratory grid, family check."""
    primary = [
        result
        for d in DESCRIPTORS
        if (result := cell_correlate(points, d, PRIMARY_POSITION)) is not None
    ]
    exploratory: list[dict] = []
    missing_cells: list[list[str]] = []
    for d in DESCRIPTORS:
        for position in GRID_POSITIONS:
            result = cell_correlate(points, d, position)
            if result is None:
                missing_cells.append([d, position])
            else:
                exploratory.append(result)

    # The preregistered multiplicity statement is 4 x 6 = 24 (E002 lines 55-63). The
    # 2026-08-11 pass executed only the 16 numeric cells; the grid block makes any gap
    # machine-checkable instead of discoverable by counting rows.
    grid = {
        "positions": list(GRID_POSITIONS),
        "n_cells_preregistered": len(DESCRIPTORS) * len(GRID_POSITIONS),
        "n_cells_executed": len(exploratory),
        "missing_cells": missing_cells,
        "complete": not missing_cells,
    }

    # Preregistered confound check: is any correlation driven entirely by GPT-2 sitting in
    # one corner? If so it is a generation effect, not a geometry effect.
    without_gpt2 = [p for p in points if not p.model.startswith("gpt2")]
    primary_no_gpt2 = [
        result
        for d in DESCRIPTORS
        if (result := cell_correlate(without_gpt2, d, PRIMARY_POSITION)) is not None
    ]

    strongest = max(
        (r for r in primary if not math.isnan(r["partial_spearman"])),
        key=lambda r: abs(r["partial_spearman"]),
        default=None,
    )

    # The confound check is part of the decision, not a footnote. A correlation that
    # disappears when one model family is removed is a property of that family, not of
    # geometry. Reading only the primary test called E002 SUPPORTED on the strength of a
    # partial rho that fell from +0.692 to +0.006 once GPT-2 was excluded.
    by_descriptor = {r["descriptor"]: r["partial_spearman"] for r in primary_no_gpt2}
    survives = False
    confound_note = "no confound check available"
    if strongest is not None:
        without = by_descriptor.get(strongest["descriptor"])
        if without is not None and not math.isnan(without):
            survives = abs(without) >= FALSIFY_THRESHOLD and (
                without * strongest["partial_spearman"] > 0  # sign must hold too
            )
            confound_note = (
                f"{strongest['descriptor']}: {strongest['partial_spearman']:+.3f} with "
                f"GPT-2, {without:+.3f} without"
            )

    if strongest is None:
        verdict = "no usable primary test"
    elif abs(strongest["partial_spearman"]) < FALSIFY_THRESHOLD:
        verdict = "FALSIFIED in this regime"
    elif not survives:
        verdict = "CONFOUNDED — correlation does not survive removing the GPT-2 family"
    elif abs(strongest["partial_spearman"]) >= SUPPORT_THRESHOLD:
        verdict = "SUPPORTED"
    else:
        verdict = "INCONCLUSIVE"

    return {
        "confound_check": confound_note,
        "survives_confound_check": survives,
        "n_models": len(points),
        "primary_depth": PRIMARY_DEPTH,
        "primary": primary,
        "primary_excluding_gpt2": primary_no_gpt2,
        "exploratory": exploratory,
        "grid": grid,
        "n_exploratory_tests": len(exploratory),
        "strongest_primary": strongest,
        "verdict": verdict,
        "thresholds": {"support": SUPPORT_THRESHOLD, "falsify": FALSIFY_THRESHOLD},
        "caveat": (
            "Correlational only. Parameter count is a weak control: models differ in data, "
            "tokenizer, depth and recipe simultaneously. No causal claim is available from "
            "this design."
        ),
    }
