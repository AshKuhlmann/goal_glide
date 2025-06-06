import uuid
from datetime import datetime
import click
from rich.console import Console
from rich.table import Table
from .models import Goal
from .storage import Storage

console = Console()

@click.group()
@click.pass_context
def cli(ctx):
    ctx.obj = Storage()

@cli.command()
@click.argument('title')
@click.option('-p', '--priority', type=click.Choice(['low', 'med', 'high']), default='med')
@click.pass_obj
def add(storage: Storage, title: str, priority: str):
    title = title.strip()
    if not title:
        console.print('[red]Title cannot be empty.[/red]')
        return
    if storage.find_by_title(title):
        console.print('[yellow]Warning: goal with this title already exists.[/yellow]')
    goal = Goal(id=str(uuid.uuid4()), title=title, created=datetime.utcnow(), priority=priority)
    storage.add_goal(goal)
    console.print(f"[green]Added:[/green] {title} ({goal.id})")

@cli.command()
@click.option('--all', 'show_all', is_flag=True, help='Show all goals including archived')
@click.option('--archived', 'archived_only', is_flag=True, help='Show only archived')
@click.option('--priority', type=click.Choice(['low', 'med', 'high']))
@click.pass_obj
def list(storage: Storage, show_all: bool, archived_only: bool, priority: str):
    goals = storage.list_goals(include_archived=show_all, archived_only=archived_only, priority=priority)
    table = Table(title='Goals')
    table.add_column('ID')
    table.add_column('Title')
    table.add_column('Priority')
    table.add_column('Created')
    table.add_column('Archived')
    for g in goals:
        table.add_row(g.id.split('-')[0], g.title, g.priority, g.created.isoformat(), str(g.archived))
    console.print(table)

@cli.command()
@click.argument('goal_id')
@click.pass_obj
def remove(storage: Storage, goal_id: str):
    if click.confirm(f'Remove goal {goal_id}?'):
        removed = storage.remove_goal(goal_id)
        if removed:
            console.print(f"[green]Removed[/green] {goal_id}")
        else:
            console.print('[red]Goal not found.[/red]')

if __name__ == '__main__':
    cli()
