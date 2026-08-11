"""geom — project CLI.

    uv run geom doctor      verify the backend before anything else
    uv run geom smoke       <60s end-to-end check, CPU-friendly
    uv run geom eval        flip rate for one model
    uv run geom sweep       flip rate across a list of models
    uv run geom geometry    hidden-state geometry for one model
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import baselines as baseline_lib
from . import geometry as geom_metrics
from . import items as item_gen
from . import metrics as metric_lib
from .device import enable_fast_matmul, get_device_info, seed_everything
from .provenance import RunRecord

app = typer.Typer(add_completion=False, help=__doc__, no_args_is_help=True)
console = Console()

RESULTS = Path(__file__).resolve().parents[2] / "results"


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
    n: int = typer.Option(64, help="pairs per family to draw prompts from"),
    seed: int = typer.Option(0),
    batch_size: int = typer.Option(8),
    max_samples: int = typer.Option(384),
    out: Path | None = typer.Option(None),
    experiment: str = typer.Option("E002"),
) -> None:
    """Hidden-state geometry per layer, on the same prompts used for flip rate."""
    from .evaluate import load_model

    seed_everything(seed)
    enable_fast_matmul()

    pairs = item_gen.generate(n_per_family=n, seed=seed)
    prompts = [item.prompt for item in item_gen.flatten(pairs)]

    with console.status(f"loading {model}…"):
        loaded = load_model(model)
    with console.status("collecting hidden states…"):
        per_layer = geom_metrics.collect_hidden_states(
            loaded, prompts, batch_size=batch_size, max_samples=max_samples
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

    out = out or RESULTS / f"{experiment}-geometry-{model.replace('/', '_')}-seed{seed}.json"
    path = RunRecord(
        experiment=experiment,
        seed=seed,
        config={"model": model, "n_params": loaded.n_params, "n_per_family": n,
                "max_samples": max_samples, "n_prompts": min(len(prompts), max_samples)},
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
