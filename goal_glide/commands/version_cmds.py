from __future__ import annotations

import click


@click.command("version")
def version_cmds() -> None:
    """Print package version."""
    from .. import __version__

    click.echo(__version__)
