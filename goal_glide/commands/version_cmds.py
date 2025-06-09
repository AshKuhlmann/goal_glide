from __future__ import annotations

import click

from .common import console


@click.command("version")
def version_cmds() -> None:
    """Print package version."""
    from .. import __version__

    console.print(__version__)
