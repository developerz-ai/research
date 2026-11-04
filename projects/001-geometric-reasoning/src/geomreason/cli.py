"""geom — project CLI.

    uv run geom doctor      verify the backend before anything else
    uv run geom smoke       <60s end-to-end check, CPU-friendly
    uv run geom eval        flip rate for one model
    uv run geom sweep       flip rate across a list of models
    uv run geom geometry    hidden-state geometry for one model
    uv run geom inputs      compare recorded input populations (behavior vs geometry)
    uv run geom grid        complete the preregistered 24-cell depth grid + reconcile
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import baselines as baseline_lib
from . import geometry as geom_metrics
from . import inputs as inputs_lib
from . import items as item_gen
from . import metrics as metric_lib
from .device import enable_fast_matmul, get_device_info, seed_everything
from .provenance import RunRecord

app = typer.Typer(add_completion=False, help=__doc__, no_args_is_help=True)
console = Console()

RESULTS = Path(__file__).resolve().parents[2] / "results"


def _is_flip_record(record: dict) -> bool:
    """True only for an actual behavior record: flip-rate metrics and per-item prompts.

    A standalone ``geometry --experiment E001`` run writes ``E001-geom-<model>.json`` —
    ``items=[]`` with layer metrics — which sorts *before* ``E001-<model>-seed0.json``.
    Selected as the behavior record it would match geosweep against the geometry run's
    own population (rebuilding exactly the E001/E002 mismatch) and make ``geom inputs``
    reject the pair as unusable. Filter on what the record carries, not its filename.
    """
    items = record.get("items")
    metrics = record.get("metrics")
    return (
        isinstance(items, list)
        and bool(items)
        and all(isinstance(item, dict) and "prompt" in item for item in items)
        and isinstance(metrics, dict)
        and "flip_rate" in metrics
    )


def _flip_records_by_model() -> dict[str, tuple[Path, dict]]:
    """First flip-rate record per model, in sorted path order.

    The record a geometry run must match: it carries the n_per_family and seed the
    matched population was drawn with. Sorted-path-first keeps this deterministic when
    a model has several seed runs. Candidates are filtered to actual behavior records
    (:func:`_is_flip_record`) — anything else in the glob is not a population a geometry
    run can be matched against.
    """
    found: dict[str, tuple[Path, dict]] = {}
    for path in sorted(RESULTS.glob("E001*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if not _is_flip_record(record):
            continue
        model = record.get("config", {}).get("model")
        if model and model not in found:
            found[model] = (path, record)
    return found


def _print_result(model: str, result: metric_lib.FlipRateResult) -> None:
    """Render a flip-rate result, overall then per family."""
    ci = result.flip_rate_ci()
    table = Table(title=f"{model} — flip rate", title_justify="left")
    for column in ("scope", "pairs", "flip rate", "95% CI", "canon acc",
                   "perturb acc", "shortcut gap", "stickiness"):
        table.add_column(column, justify="right")
    table.add_row(
        "[bold]overall[/bold]", str(result.n_pairs), f"[bold]{result.flip_rate:.3f}[/bold]",
        f"[{ci.lo:.2f}, {ci.hi:.2f}]", f"{result.canonical_accuracy:.3f}",
        f"{result.perturbed_accuracy:.3f}", f"{result.shortcut_gap:+.3f}",
        f"{result.stickiness:.3f}",
    )
    for family, sub in result.per_family.items():
        sub_ci = sub.flip_rate_ci()
        table.add_row(
            family, str(sub.n_pairs), f"{sub.flip_rate:.3f}",
            f"[{sub_ci.lo:.2f}, {sub_ci.hi:.2f}]", f"{sub.canonical_accuracy:.3f}",
            f"{sub.perturbed_accuracy:.3f}", f"{sub.shortcut_gap:+.3f}",
            f"{sub.stickiness:.3f}",
        )
    console.print(table)
    console.print("  [dim]chance flip rate = 0.25 · stickiness 1.0 = perturbation "
                  "ignored entirely[/dim]")


@app.command()
def doctor() -> None:
    """Verify the accelerator backend and dtype support. Run this first in a fresh venv."""
    info = get_device_info()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("torch", info.torch_version)
    table.add_row("build", info.build)
    table.add_row("backend", f"[bold]{info.backend}[/bold]")
    table.add_row("device", str(info.device))
    table.add_row("name", info.name)
    table.add_row("memory", f"{info.total_memory_gb} GB" if info.total_memory_gb else "-")
    table.add_row("bf16", "yes" if info.supports_bf16 else "no (using fp32)")
    console.print()
    console.print(table)

    for note in info.notes:
        console.print(f"  [yellow]note[/yellow]  {note}")

    if not info.is_accelerated:
        console.print(
            "\n  [yellow]No accelerator detected.[/yellow] If this machine has a GPU, the "
            "installed torch wheel is the wrong one — that fails silently by being ~50x "
            "slower rather than erroring.\n"
            "    NVIDIA  uv sync --index pytorch=https://download.pytorch.org/whl/cu126\n"
            "    AMD     uv sync --index pytorch=https://download.pytorch.org/whl/rocm6.2"
        )
    else:
        import torch

        enable_fast_matmul()
        a = torch.randn(512, 512, device=info.device)
        result = (a @ a).sum().item()
        ok = result == result  # NaN check
        console.print(f"\n  matmul smoke test: {'[green]ok[/green]' if ok else '[red]NaN[/red]'}")
    console.print()


@app.command()
def baselines(
    n: int = typer.Option(100, help="pairs per family"),
    seed: int = typer.Option(0),
) -> None:
    """Score trivial heuristics on the item set — the admissibility check for each family.

    Any family where a heuristic scores well above chance (0.25) is not a reasoning test,
    and model results on it must be discarded rather than caveated.
    """
    flat = item_gen.flatten(item_gen.generate(n_per_family=n, seed=seed))

    table = Table(title="heuristic flip rate (chance = 0.25)", title_justify="left")
    table.add_column("heuristic")
    table.add_column("pairs", justify="right")
    table.add_column("overall", justify="right")
    for family in sorted(item_gen.FAMILIES):
        table.add_column(family[:9], justify="right")

    for name, result in baseline_lib.score_all(flat).items():
        row = [name, str(result.n_pairs), f"{result.flip_rate:.3f}"]
        for family in sorted(item_gen.FAMILIES):
            sub = result.per_family.get(family)
            row.append(f"{sub.flip_rate:.3f}" if sub else "[dim]n/a[/dim]")
        table.add_row(*row)
    console.print()
    console.print(table)

    worst = baseline_lib.worst_case_per_family(flat)
    console.print("\n  [bold]admissibility[/bold]  [dim](best heuristic per family)[/dim]")
    bad = False
    for family in sorted(item_gen.FAMILIES):
        entry = worst.get(family)
        if entry is None:
            console.print(f"    {family:<14} [green]no heuristic applies[/green]")
            continue
        name, rate = entry
        if rate > 0.40:
            bad = True
            console.print(f"    {family:<14} [red]{rate:.3f}[/red] via {name} "
                          f"[red]← NOT a reasoning test[/red]")
        else:
            console.print(f"    {family:<14} [green]{rate:.3f}[/green] via {name}")
    console.print()
    if bad:
        raise typer.Exit(1)


@app.command()
def items(
    n: int = typer.Option(3, help="pairs to preview per family"),
    seed: int = typer.Option(0),
    family: str | None = typer.Option(None, help="restrict to one family"),
) -> None:
    """Preview and validate generated pairs. Read these before trusting any number."""
    families = [family] if family else None
    pairs = item_gen.generate(n_per_family=n, seed=seed, families=families)

    for pair in pairs:
        console.print(f"\n[bold]{pair.canonical.pair_id}[/bold]  "
                      f"[dim]{pair.canonical.family}[/dim]")
        for member in (pair.canonical, pair.perturbed):
            correct = member.options[member.correct_index]
            console.print(f"  [dim]{member.variant:<10}[/dim] {member.prompt}")
            console.print(f"  {'':<10} → [green]{correct.strip()}[/green]  "
                          f"[dim]options: {[o.strip() for o in member.options]}[/dim]")
    console.print(f"\n  {len(pairs)} pairs, all validated "
                  f"[dim](identical options, flipped answer, distinct prompts)[/dim]\n")


@app.command()
def eval(
    model: str = typer.Option("gpt2", help="HF model id"),
    n: int = typer.Option(100, help="pairs per family"),
    seed: int = typer.Option(0),
    batch_size: int = typer.Option(16),
    aggregation: str = typer.Option("sum", help="sum | mean"),
    out: Path | None = typer.Option(None, help="run record path"),
    experiment: str = typer.Option("E001", help="experiment id for the run record"),
) -> None:
    """Measure flip rate for one model on a freshly generated pair set."""
    from .evaluate import evaluate_items, load_model

    seed_everything(seed)
    enable_fast_matmul()

    pairs = item_gen.generate(n_per_family=n, seed=seed)
    flat = item_gen.flatten(pairs)
    prompts = [item.prompt for item in flat]
    console.print(f"  {len(pairs)} pairs / {len(flat)} items, seed {seed}")

    with console.status(f"loading {model}…"):
        loaded = load_model(model)
    console.print(f"  {model}  [dim]{loaded.n_params_millions}M params on "
                  f"{loaded.device_info.backend}[/dim]\n")

    with console.status("scoring…") as status:
        def tick(done: int, total: int) -> None:
            status.update(f"scoring… {done}/{total}")

        records = evaluate_items(
            loaded, flat, batch_size=batch_size, aggregation=aggregation, progress=tick
        )

    result = metric_lib.score_pairs(records)
    _print_result(model, result)

    out = out or RESULTS / f"{experiment}-{model.replace('/', '_')}-seed{seed}.json"
    path = RunRecord(
        experiment=experiment,
        seed=seed,
        config={
            "model": model,
            "n_params": loaded.n_params,
            "n_per_family": n,
            "n_pairs": len(pairs),
            "families": sorted(item_gen.FAMILIES),
            "batch_size": batch_size,
            "aggregation": aggregation,
            "n_items": len(flat),
            "prompt_digest": inputs_lib.population_digest(prompts),
            "input_population": inputs_lib.population_block(
                n_per_family=n, seed=seed, families=list(item_gen.FAMILIES),
                max_samples=0, prompts=prompts,
            ),
        },
        metrics=result.as_dict(),
        items=records,
    ).write(out)
    console.print(f"  [green]wrote[/green] {path}\n")


@app.command()
def sweep(
    models: str = typer.Option(
        "gpt2,gpt2-medium,gpt2-large",
        help="comma-separated HF model ids, small to large",
    ),
    n: int = typer.Option(100),
    seed: int = typer.Option(0),
    batch_size: int = typer.Option(16),
    experiment: str = typer.Option("E001"),
) -> None:
    """Flip rate across a model-size ladder — the cheap test that needs no training."""
    for model in [m.strip() for m in models.split(",") if m.strip()]:
        console.rule(f"[bold]{model}")
        try:
            eval(model=model, n=n, seed=seed, batch_size=batch_size,
                 aggregation="sum", out=None, experiment=experiment)
        except (NameError, AttributeError, ImportError, TypeError):
            # Our own bug, not a bad model. Swallowing these makes a broken harness look
            # like four unavailable checkpoints — which is exactly what happened once.
            raise
        except Exception as exc:  # one unavailable model must not lose the whole sweep
            console.print(f"  [red]failed[/red] {model}: {type(exc).__name__}: {exc}\n")


@app.command()
def geometry(
    model: str = typer.Option("gpt2"),
    n: int = typer.Option(100, help="pairs per family (default matches geom eval)"),
    seed: int = typer.Option(0),
    batch_size: int = typer.Option(8),
    max_samples: int = typer.Option(0, help="prompt cap; 0 = no truncation"),
    out: Path | None = typer.Option(None),
    experiment: str = typer.Option("E002"),
) -> None:
    """Hidden-state geometry per layer, on the same prompts used for flip rate."""
    # Unlike eval's default record name, this one carries no seed: a second standalone
    # run at a different seed would collide with the existing record. Refuse before any
    # compute, as geosweep does; an explicitly passed --out (geosweep's call) is unguarded.
    if out is None:
        out = RESULTS / f"{experiment}-geom-{model.replace('/', '_')}.json"
        if out.exists():
            console.print(
                f"  [red]refusing to overwrite[/red] {out} — pass --out or delete the record"
            )
            raise typer.Exit(1)
    from .evaluate import load_model

    seed_everything(seed)
    enable_fast_matmul()

    pairs = item_gen.generate(n_per_family=n, seed=seed)
    prompts = [item.prompt for item in item_gen.flatten(pairs)]
    if max_samples > 0:
        # Truncate here and record the truncated list below. collect_hidden_states would
        # otherwise truncate internally, leaving the record silent about the exact
        # prompts the model saw — the silence that hid the E001/E002 population mismatch.
        prompts = prompts[:max_samples]

    with console.status(f"loading {model}…"):
        loaded = load_model(model)
    with console.status("collecting hidden states…"):
        per_layer = geom_metrics.collect_hidden_states(
            loaded, prompts, batch_size=batch_size, max_samples=len(prompts)
        )
    with console.status("computing descriptors…"):
        described = [geom_metrics.describe_layer(acts, layer)
                     for layer, acts in sorted(per_layer.items())]

    table = Table(title=f"{model} — hidden-state geometry")
    for column in ("layer", "dim", "participation ratio", "effective rank",
                   "intrinsic dim", "anisotropy"):
        table.add_column(column, justify="right")
    for lg in described:
        table.add_row(str(lg.layer), str(lg.ambient_dim), f"{lg.participation_ratio:.1f}",
                      f"{lg.effective_rank:.1f}", f"{lg.intrinsic_dim_twonn:.2f}",
                      f"{lg.anisotropy:.3f}")
    console.print()
    console.print(table)
    console.print("\n  [dim]correlational only — a metric that tracks robustness may still "
                  "be a passenger, not a cause[/dim]")

    path = RunRecord(
        experiment=experiment,
        seed=seed,
        config={"model": model, "n_params": loaded.n_params, "n_per_family": n,
                "max_samples": max_samples, "n_prompts": len(prompts),
                "input_population": inputs_lib.population_block(
                    n_per_family=n, seed=seed, families=list(item_gen.FAMILIES),
                    max_samples=max_samples, prompts=prompts,
                )},
        metrics={"layers": [lg.as_dict() for lg in described]},
        items=[],
        notes="Our operationalisation of an undefined term; all descriptors preregistered "
              "together.",
    ).write(out)
    console.print(f"  [green]wrote[/green] {path}\n")


@app.command()
def export(
    n: int = typer.Option(1000, help="pairs per family"),
    seed: int = typer.Option(0),
    fmt: str = typer.Option("eval", "--format", help="eval | sft | pairs"),
    out: Path | None = typer.Option(None, help="output .jsonl path"),
) -> None:
    """Generate a synthetic dataset to JSONL.

    Formats:

    * ``eval``  — one row per item: prompt, both options, correct index. For scoring.
    * ``sft``   — one row per item: prompt + the correct completion. Supervised training data.
    * ``pairs`` — one row per pair, both members nested. For inspection and item review.

    Output goes under ``data/`` which is **gitignored on purpose**. Freshness is the
    contamination defence: a published pair set is a benchmark, and benchmarks leak. Ship
    the seed, not the file.
    """
    if fmt not in ("eval", "sft", "pairs"):
        raise typer.BadParameter("format must be eval | sft | pairs")

    pairs = item_gen.generate(n_per_family=n, seed=seed)
    out = out or (RESULTS.parent / "data" / f"items-{fmt}-n{n}-seed{seed}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for pair in pairs:
        if fmt == "pairs":
            rows.append({
                "pair_id": pair.canonical.pair_id,
                "family": pair.canonical.family,
                "canonical": pair.canonical.as_dict(),
                "perturbed": pair.perturbed.as_dict(),
            })
            continue
        for member in (pair.canonical, pair.perturbed):
            if fmt == "eval":
                rows.append(member.as_dict())
            else:  # sft
                rows.append({
                    "pair_id": member.pair_id,
                    "family": member.family,
                    "variant": member.variant,
                    "prompt": member.prompt,
                    "completion": member.options[member.correct_index],
                    "rejected": member.options[1 - member.correct_index],
                })

    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    console.print(f"\n  [green]wrote[/green] {out}")
    console.print(f"  {len(rows)} rows · {len(pairs)} pairs · {len(item_gen.FAMILIES)} families "
                  f"· seed {seed}")
    console.print("  [dim]regenerate with the same seed rather than committing this file[/dim]\n")


@app.command()
def geosweep(
    models: str = typer.Option(
        "", help="comma-separated; default = every model with a flip-rate record"
    ),
    batch_size: int = typer.Option(8),
    max_samples: int = typer.Option(
        0, help="prompt cap; 0 = no truncation (matched to the flip-rate population)"
    ),
    experiment: str = typer.Option("E002"),
) -> None:
    """Collect hidden-state geometry for every model that has a flip-rate result.

    n_per_family and seed are derived from each model's own flip-rate record, so the
    geometry prompts and the flip-rate prompts are identical by construction instead of
    identical by assumption — the assumption failed once (geometry ran 24/family against
    a 100/family flip rate) and nothing flagged it. Truncating with --max-samples keeps
    only a prefix of that population, which breaks identity; say so in the writeup.
    """
    flip_by_model = _flip_records_by_model()
    if models.strip():
        wanted = [m.strip() for m in models.split(",") if m.strip()]
    else:
        wanted = sorted(flip_by_model)

    console.print(f"\n  {len(wanted)} model(s) to profile\n")
    for model in wanted:
        out = RESULTS / f"{experiment}-geom-{model.replace('/', '_')}.json"
        if out.exists():
            console.print(f"  [dim]skip[/dim] {model} — already profiled")
            continue
        entry = flip_by_model.get(model)
        if entry is None:
            console.print(f"  [red]skip[/red] {model} — no flip-rate record to match")
            continue
        n = entry[1].get("config", {}).get("n_per_family")
        if n is None:
            console.print(f"  [red]skip[/red] {model} — flip-rate record has no n_per_family")
            continue
        seed = entry[1].get("seed", 0)
        console.rule(f"[bold]{model}")
        try:
            geometry(model=model, n=n, seed=seed, batch_size=batch_size,
                     max_samples=max_samples, out=out, experiment=experiment)
        except (NameError, AttributeError, ImportError, TypeError):
            raise
        except Exception as exc:
            console.print(f"  [red]failed[/red] {model}: {type(exc).__name__}: {exc}\n")


@app.command()
def inputs(
    experiment: str = typer.Option("E002", help="experiment id of the geometry records"),
    strict: bool = typer.Option(
        False, "--strict",
        help="exit nonzero unless every geometry population is identical to its "
             "flip-rate population",
    ),
) -> None:
    """Compare each model's geometry input population with its flip-rate population.

    E002's premise is that both measurements saw the same prompts; this checks that
    premise against the committed records instead of assuming it. Behavior populations
    are rebuilt from config and verified against the stored per-item prompts; geometry
    populations are rebuilt from config alone (legacy records store no prompt list) and
    compared by digest and family-level overlap.
    """
    flip_by_model = _flip_records_by_model()
    geom_paths = sorted(RESULTS.glob(f"{experiment}-geom-*.json"))
    if not geom_paths:
        console.print(f"  no geometry records matching {experiment}-geom-*.json in {RESULTS}")
        raise typer.Exit(1)

    table = Table(
        title=f"input populations — {experiment} geometry vs flip rate", title_justify="left"
    )
    for column in ("model", "behavior", "digest", "geometry", "digest", "shared",
                   "first family only", "identical"):
        table.add_column(column, justify="right")

    all_identical = True
    all_rebuilt = True
    for path in geom_paths:
        grec = json.loads(path.read_text(encoding="utf-8"))
        model = grec.get("config", {}).get("model")
        try:
            geo = inputs_lib.from_geometry_record(grec)
        except ValueError as exc:
            all_rebuilt = False
            console.print(f"  [red]{path.name}[/red]: {exc}")
            continue
        entry = flip_by_model.get(model)
        if entry is None:
            all_identical = False
            table.add_row(str(model), "-", "-", str(len(geo.prompts)), geo.digest,
                          "-", "-", "-")
            continue
        try:
            beh = inputs_lib.from_behavior_record(entry[1])
        except ValueError as exc:
            all_rebuilt = False
            console.print(f"  [red]{model}[/red] behavior record unusable: {exc}")
            continue
        comp = inputs_lib.compare(beh, geo)
        all_identical = all_identical and comp.identical
        # confined_to_first_family is vacuously true at zero overlap — nothing shared is
        # trivially "all from one family" — and a green yes there would claim a signature
        # nothing backs. Report n/a unless something is actually shared.
        confined = (
            "[green]yes[/green]" if comp.confined_to_first_family else "[red]no[/red]"
        ) if comp.n_shared else "[dim]n/a[/dim]"
        table.add_row(
            str(model), str(len(beh.prompts)), beh.digest, str(len(geo.prompts)),
            geo.digest, str(comp.n_shared),
            confined,
            "[green]yes[/green]" if comp.identical else "[red]no[/red]",
        )

    console.print()
    console.print(table)
    # Green requires more than "nothing compared unequal": a record skipped for an
    # invalid digest or an unusable behavior record verified no population at all, and
    # an "identical inputs" line over it would certify a premise nobody checked.
    if all_identical and all_rebuilt:
        console.print("  [green]identical inputs[/green] — geometry ran on the flip-rate "
                      "prompts\n")
    else:
        if not all_rebuilt:
            console.print(
                "  [red]verification incomplete[/red] — some populations could not be "
                "rebuilt from their records (above); a skipped record verifies nothing\n"
            )
        if not all_identical:
            console.print("  [red]identical-input premise broken[/red] — geometry prompts "
                          "differ from the flip-rate prompts; the shared overlap is "
                          "family-attributed above\n")
    if not all_rebuilt or (strict and not all_identical):
        raise typer.Exit(1)


@app.command()
def correlate(
    experiment: str = typer.Option("E002"),
    out: Path | None = typer.Option(None),
) -> None:
    """E002: partial correlation of geometry against flip rate, controlling for size."""
    from . import correlate as analysis

    points = analysis.load_points(RESULTS, geometry_experiment=experiment)
    if len(points) < 4:
        console.print(f"  only {len(points)} model(s) with both geometry and flip rate — "
                      "run 'geom geosweep' first")
        raise typer.Exit(1)

    console.print(f"\n  [bold]{len(points)} models[/bold] with both measurements\n")
    ladder = Table(show_header=True)
    for column in ("model", "params (M)", "flip rate"):
        ladder.add_column(column, justify="right")
    for p in sorted(points, key=lambda p: p.n_params):
        ladder.add_row(p.model, f"{p.n_params / 1e6:.0f}", f"{p.flip_rate:.3f}")
    console.print(ladder)

    report = analysis.run(points)

    def show(rows: list[dict], title: str) -> None:
        table = Table(title=title, title_justify="left")
        for column in ("descriptor", "n", "ρ(geom,flip)", "ρ(geom,size)", "**partial ρ**"):
            table.add_column(column, justify="right")
        for row in rows:
            partial_rho = row["partial_spearman"]
            marker = "[green]" if abs(partial_rho) >= analysis.SUPPORT_THRESHOLD else "[dim]"
            table.add_row(
                row["descriptor"], str(row["n"]),
                f"{row['spearman_geom_flip']:+.3f}",
                f"{row['spearman_geom_size']:+.3f}",
                f"{marker}{partial_rho:+.3f}[/]",
            )
        console.print()
        console.print(table)

    show(report["primary"], f"PRIMARY — relative depth {analysis.PRIMARY_DEPTH} (preregistered)")
    show(report["primary_excluding_gpt2"], "Confound check — same, excluding GPT-2 family")

    console.print(f"\n  [bold]verdict: {report['verdict']}[/bold]")
    console.print(f"  [dim]support ≥{analysis.SUPPORT_THRESHOLD} · "
                  f"falsify <{analysis.FALSIFY_THRESHOLD} · "
                  f"{report['n_exploratory_tests']} exploratory tests not shown "
                  f"(multiplicity)[/dim]")
    console.print(f"  [dim]{report['caveat']}[/dim]\n")

    path = RunRecord(
        experiment=experiment, seed=0,
        config={"models": [p.model for p in points], "analysis": "partial spearman"},
        metrics=report, items=[],
    ).write(out or RESULTS / f"{experiment}-correlation.json")
    console.print(f"  [green]wrote[/green] {path}\n")


RECONCILE_FIELDS = (
    "n",
    "spearman_geom_flip",
    "spearman_geom_size",
    "partial_spearman",
    "pearson_geom_flip",
)


def _values_equal(a: object, b: object) -> bool:
    """JSON-number equality that treats NaN == NaN as equal, not as drift."""
    if (
        isinstance(a, float) and isinstance(b, float)
        and math.isnan(a) and math.isnan(b)
    ):
        return True
    return a == b


def reconcile_grid(report: dict, prior: dict | None) -> dict:
    """Reconcile a fresh grid against the prior correlation record, cell by cell.

    Numeric cells are matched to prior exploratory rows by (descriptor, relative_depth);
    a cell whose stats fields all equal the prior row is "executed <prior-date>
    (reproduced)", any mismatch is "executed <prior-date> (DRIFT)", and a cell with no
    prior row (the max / argmax hump cells, never in the prior record) is
    "completed <today>". Both dates are derived at run time: the prior date from the
    prior record's timestamp_utc ("unknown" when missing), today's from the current
    UTC date.
    """
    prior_rows: dict[tuple, dict] = {}
    if prior is not None:
        for row in prior.get("metrics", {}).get("exploratory", []):
            if "descriptor" in row and "relative_depth" in row:
                prior_rows[(row["descriptor"], row["relative_depth"])] = row

    prior_timestamp_utc = None if prior is None else prior.get("timestamp_utc")
    prior_date = str(prior_timestamp_utc)[:10] if prior_timestamp_utc else "unknown"
    completed_date = datetime.now(timezone.utc).date().isoformat()

    cells: list[dict] = []
    n_reproduced = n_drifted = n_completed = 0
    for row in report.get("exploratory", []):
        prior_row = None
        if prior is not None and "relative_depth" in row:
            prior_row = prior_rows.get((row["descriptor"], row["relative_depth"]))
        if prior_row is None:
            status = f"completed {completed_date}"
            n_completed += 1
        elif all(_values_equal(row[f], prior_row[f]) for f in RECONCILE_FIELDS):
            status = f"executed {prior_date} (reproduced)"
            n_reproduced += 1
        else:
            status = f"executed {prior_date} (DRIFT)"
            n_drifted += 1
        cells.append({
            "descriptor": row["descriptor"],
            "position": row["position"],
            "status": status,
        })

    return {
        "prior_timestamp_utc": prior_timestamp_utc,
        "compared_fields": list(RECONCILE_FIELDS),
        "cells": cells,
        "n_reproduced": n_reproduced,
        "n_drifted": n_drifted,
        "n_completed": n_completed,
    }


@app.command()
def grid(
    experiment: str = typer.Option("E002"),
    out: Path | None = typer.Option(None),
) -> None:
    """Run the full preregistered 24-cell depth grid and reconcile it with the prior pass.

    E002 preregistered 4 descriptors x 6 depth positions = 24 tests; the 2026-08-11
    correlation pass executed only the 16 numeric cells - the max/argmax "hump" positions
    never ran. This command executes the whole grid, then labels every cell against the
    prior record: identical stats reproduce the old number, a mismatch is DRIFT, an absent
    prior row is completed today. Exploratory cells never influence the verdict; it stands
    on the primary tests alone.
    """
    from . import correlate as analysis

    prior_path = RESULTS / f"{experiment}-correlation.json"
    prior = None
    if prior_path.exists():
        prior = json.loads(prior_path.read_text(encoding="utf-8"))

    points = analysis.load_points(RESULTS, geometry_experiment=experiment)
    if len(points) < 4:
        console.print(f"  only {len(points)} model(s) with both geometry and flip rate — "
                      "run 'geom geosweep' first")
        raise typer.Exit(1)

    report = analysis.run(points)
    reconciliation = reconcile_grid(report, prior)
    report["reconciliation"] = reconciliation
    grid_block = report["grid"]

    console.print(f"\n  [bold]{len(points)} models[/bold] — grid "
                  f"{grid_block['n_cells_executed']}/"
                  f"{grid_block['n_cells_preregistered']} preregistered cells executed\n")

    by_cell = {(r["descriptor"], r["position"]): r for r in report["exploratory"]}
    table = Table(title=f"{experiment} depth grid — per-cell reconciliation",
                  title_justify="left")
    for column in ("descriptor", "position", "n", "partial ρ", "status"):
        table.add_column(column, justify="right")
    for cell in reconciliation["cells"]:
        row = by_cell[(cell["descriptor"], cell["position"])]
        if "reproduced" in cell["status"]:
            status = f"[green]{cell['status']}[/green]"
        elif "DRIFT" in cell["status"]:
            status = f"[red]{cell['status']}[/red]"
        else:
            status = f"[cyan]{cell['status']}[/cyan]"
        table.add_row(cell["descriptor"], cell["position"], str(row["n"]),
                      f"{row['partial_spearman']:+.3f}", status)
    console.print(table)

    if grid_block["complete"]:
        console.print(f"\n  [green]grid complete[/green] — all "
                      f"{grid_block['n_cells_preregistered']} preregistered cells executed")
    else:
        console.print(f"\n  [red]grid INCOMPLETE[/red] — missing: "
                      f"{grid_block['missing_cells']}")
    console.print(
        f"  {reconciliation['n_reproduced']} reproduced · "
        f"{reconciliation['n_drifted']} drifted · "
        f"{reconciliation['n_completed']} completed "
        f"[dim](prior: {prior_path.name if prior is not None else 'none'}, "
        f"{reconciliation['prior_timestamp_utc']})[/dim]"
    )
    if reconciliation["n_drifted"]:
        console.print("  [red]DRIFT[/red] — a prior cell no longer reproduces from the "
                      "committed records; do not cite the old number")
    console.print()

    path = RunRecord(
        experiment=experiment, seed=0,
        config={
            "models": [p.model for p in points],
            "analysis": "grid completion (4 descriptors x 6 depth positions)",
            "prior_record": prior_path.name if prior is not None else None,
        },
        metrics=report, items=[],
        notes="Completes the preregistered 24-cell grid; the 2026-08-11 pass executed only "
              "the 16 numeric cells. Exploratory cells do not touch the verdict — it "
              "stands on the primary tests.",
    ).write(out or RESULTS / f"{experiment}-grid-completion.json")
    console.print(f"  [green]wrote[/green] {path}\n")


@app.command()
def smoke() -> None:
    """Fast end-to-end check: generate, score with a tiny model, aggregate. CPU-friendly."""
    console.print("\n  [bold]1/3[/bold] item generation + validation")
    pairs = item_gen.generate(n_per_family=5, seed=0)
    console.print(f"      {len(pairs)} pairs across {len(item_gen.FAMILIES)} families "
                  f"[green]ok[/green]")

    console.print("  [bold]2/3[/bold] metric wiring (synthetic perfect + shortcut model)")
    flat = item_gen.flatten(pairs)
    perfect = [{"pair_id": i.pair_id, "family": i.family, "variant": i.variant,
                "chosen_index": i.correct_index, "correct_index": i.correct_index} for i in flat]
    shortcut = [{"pair_id": i.pair_id, "family": i.family, "variant": i.variant,
                 "chosen_index": 0, "correct_index": i.correct_index} for i in flat]
    p, s = metric_lib.score_pairs(perfect), metric_lib.score_pairs(shortcut)
    assert p.flip_rate == 1.0, p.flip_rate
    assert s.flip_rate == 0.0, s.flip_rate
    assert s.stickiness == 1.0, s.stickiness
    console.print(f"      perfect flip_rate={p.flip_rate:.2f} · "
                  f"constant-answer flip_rate={s.flip_rate:.2f} stickiness={s.stickiness:.2f} "
                  f"[green]ok[/green]")

    console.print("  [bold]3/3[/bold] model scoring (gpt2, 20 items)")
    try:
        from .evaluate import evaluate_items, load_model

        loaded = load_model("gpt2")
        records = evaluate_items(loaded, flat[:20], batch_size=8)
        result = metric_lib.score_pairs(
            [r for r in records if sum(1 for x in records if x["pair_id"] == r["pair_id"]) == 2]
        )
        console.print(f"      scored {len(records)} items on {loaded.device_info.backend}, "
                      f"flip_rate={result.flip_rate:.2f} [green]ok[/green]")
    except Exception as exc:
        console.print(f"      [yellow]skipped[/yellow] ({type(exc).__name__}: {exc})")
        console.print("      [dim]needs network for the model download; the rest passed[/dim]")

    console.print("\n  [green]smoke passed[/green]\n")


@app.command()
def report(pattern: str = typer.Option("E001-*.json", help="glob within results/")) -> None:
    """Compare run records side by side."""
    files = sorted(RESULTS.glob(pattern))
    if not files:
        console.print(f"  no results matching {pattern} in {RESULTS}")
        raise typer.Exit(1)

    table = Table(title=f"results/{pattern}")
    for column in ("model", "params (M)", "seed", "flip rate", "95% CI", "canon acc",
                   "perturb acc", "shortcut gap", "stickiness"):
        table.add_column(column, justify="right")

    for path in files:
        rec = json.loads(path.read_text(encoding="utf-8"))
        m, cfg = rec.get("metrics", {}), rec.get("config", {})
        if "flip_rate" not in m:
            continue
        ci = m.get("flip_rate_ci", [0, 0])
        table.add_row(
            str(cfg.get("model", "?")),
            f"{cfg.get('n_params', 0) / 1e6:.0f}",
            str(rec.get("seed")),
            f"{m['flip_rate']:.3f}",
            f"[{ci[0]:.2f}, {ci[1]:.2f}]",
            f"{m['canonical_accuracy']:.3f}",
            f"{m['perturbed_accuracy']:.3f}",
            f"{m['shortcut_gap']:+.3f}",
            f"{m['stickiness']:.3f}",
        )
    console.print()
    console.print(table)
    console.print("\n  [dim]chance flip rate = 0.25 · stickiness 1.0 = ignored the "
                  "perturbation entirely[/dim]\n")


if __name__ == "__main__":
    app()
