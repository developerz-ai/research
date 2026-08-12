"""Project CLI.

``doctor`` and ``smoke`` work today. Everything else is a stub whose preregistration exists
and whose code does not — calling one tells you which experiment doc to read.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .device import get_device_info

app = typer.Typer(add_completion=False, help="002 — FTL axiom search. See CLAUDE.md.")
console = Console()

_UNBUILT = {
    "systems": "experiments/E001-axiom-id-contamination-delta.md",
    "identify": "experiments/E001-axiom-id-contamination-delta.md",
    "falsify": "experiments/E002-fanout-vs-single-matched-budget.md",
    "qei": "experiments/E003-qei-gap-1plus1d.md",
}


def _not_built(name: str) -> None:
    doc = _UNBUILT[name]
    console.print(f"[yellow]`{name}` is preregistered but not implemented.[/yellow]")
    console.print(f"Read [bold]{doc}[/bold] before writing it — the metric, threshold, and")
    console.print("baseline are fixed there, and choosing them after seeing data is not a")
    console.print("measurement. Amend the doc if they need to change; do not amend silently.")
    raise typer.Exit(code=2)


@app.command()
def doctor() -> None:
    """Report the accelerator backend. Run this FIRST in every fresh venv."""
    info = get_device_info()
    table = Table(title=f"ftlaxiom {__version__} — backend")
    table.add_column("field")
    table.add_column("value")
    for key, value in info.as_dict().items():
        table.add_row(key, str(value))
    console.print(table)
    for note in info.notes:
        console.print(f"[yellow]note:[/yellow] {note}")
    if not info.is_accelerated:
        console.print(
            "[yellow]CPU only.[/yellow] That is a supported path — every experiment must run "
            "here at a reduced --limit. If you expected a GPU, the torch wheel is wrong: a "
            "CPU-only wheel is a silent failure, not an error."
        )


@app.command()
def smoke() -> None:
    """Cheap end-to-end wiring check. Under 60s on CPU. Run after every change."""
    info = get_device_info()
    console.print(f"backend: [bold]{info.backend}[/bold] ({info.name})")
    built = ["device", "provenance"]
    pending = sorted(_UNBUILT)
    console.print(f"built:   {', '.join(built)}")
    console.print(f"pending: {', '.join(pending)}")
    console.print(
        "[yellow]Scaffold only — no experiment code exists yet, so this check cannot "
        "verify a measurement path.[/yellow] Extend it as each module lands."
    )


@app.command()
def systems(
    n: int = typer.Option(200, help="how many systems"),
    k: int = typer.Option(5, help="axioms per system; chance accuracy is 1/k"),
    seed: int = typer.Option(..., help="from the config, never from source"),
) -> None:
    """Generate clean axiom systems with one oracle-confirmed redundant member."""
    _not_built("systems")


@app.command()
def identify(
    arm: str = typer.Option(..., help="clean | contaminated"),
    model: str = typer.Option(...),
    seed: int = typer.Option(...),
) -> None:
    """E001: which axiom does the model name as redundant?"""
    _not_built("identify")


@app.command()
def falsify(
    arm: str = typer.Option(..., help="fanout | single"),
    n: int = typer.Option(5, help="agents in the fanout arm"),
    model: str = typer.Option(...),
    seed: int = typer.Option(...),
) -> None:
    """E002: fan-out vs. one agent at matched output-token budget."""
    _not_built("falsify")


@app.command()
def qei(tau: float = typer.Option(...)) -> None:
    """E003: warp-metric energy requirement vs. QEI allowance, 1+1D."""
    _not_built("qei")


if __name__ == "__main__":
    app()
