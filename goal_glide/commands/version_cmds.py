from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.command("version")
def version_cmds() -> None:
    """Print package version."""
    from .. import __version__

    console.print(__version__)

