"""Project CLI.

``doctor`` and ``smoke`` are the scaffold's whole command set. Experiment commands
get added here as their preregistrations land in ``experiments/`` — never before.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .device import get_device_info

app = typer.Typer(add_completion=False, help="{{NUMBER}} — {{SLUG}}. See CLAUDE.md.")
console = Console()


@app.command()
def doctor() -> None:
    """Report the accelerator backend. Run this FIRST in every fresh venv."""
    info = get_device_info()
    table = Table(title=f"{{PKG}} {__version__} — backend")
    table.add_column("field")
    table.add_column("value")
    for key, value in info.as_dict().items():
        table.add_row(key, str(value))
    console.print(table)
    for note in info.notes:
        console.print(f"[yellow]note:[/yellow] {note}")
    if not info.is_accelerated:
        console.print(
            "[yellow]CPU only.[/yellow] That is a supported path — every experiment must "
            "run here at a reduced --limit. If you expected a GPU, the torch wheel is "
            "wrong: a CPU-only wheel is a silent failure, not an error."
        )


@app.command()
def smoke() -> None:
    """Cheap end-to-end wiring check. Under 60s on CPU. Run after every change."""
    info = get_device_info()
    console.print(f"backend: [bold]{info.backend}[/bold] ({info.name})")
    console.print("built:   device, cli, provenance")
    console.print(
        "[yellow]Scaffold only — no experiment code exists yet, so this check cannot "
        "verify a measurement path.[/yellow] Extend it as each module lands."
    )


if __name__ == "__main__":
    app()
