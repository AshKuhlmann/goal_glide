from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Callable, ParamSpec, TypeVar, TypedDict, cast

import click
from rich.console import Console

from ..config import ConfigDict
from ..exceptions import GoalGlideError
from ..models.storage import Storage

P = ParamSpec("P")
R = TypeVar("R")

console = Console()


class AppContext(TypedDict):
    storage: Storage
    config: ConfigDict


def handle_exceptions(func: Callable[P, R]) -> Callable[P, R]:
    """Catch and handle exceptions uniformly."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation aborted by user.[/yellow]")
            raise SystemExit(130)
        except GoalGlideError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            raise SystemExit(1)
        except click.ClickException as exc:
            exc.show()
            raise SystemExit(1)
        except Exception as exc:
            console.print(f"[bold red]An unexpected error occurred:[/bold red] {exc}")
            raise SystemExit(1)

    return wrapper


def get_storage() -> Storage:
    db_dir = os.environ.get("GOAL_GLIDE_DB_DIR")
    return Storage(Path(db_dir) if db_dir else None)
