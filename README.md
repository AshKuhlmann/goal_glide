# Goal Glide

Goal Glide is a simple command line and text user interface (TUI) application for managing personal goals and tracking focused work using the Pomodoro technique. Goals, sessions and short "thought" notes are stored in a small JSON database under your home directory.

Features include:

- Add, remove and list goals with priorities
- Tag goals and archive or restore them
- Start/stop Pomodoro sessions with optional motivational quotes
- Desktop break reminders after each session
- Capture quick thoughts and attach them to goals
- Display focus statistics and streaks
- Optional Textual based TUI for an interactive view
- Set deadlines on goals with visual warnings when approaching

## Installation

1. Install Python 3.11 or newer. The Rust compiler is also required to build some dependencies. Install it via [rustup](https://rustup.rs/). On Apple M-series Macs, run `rustup target add x86_64-apple-darwin` so native extensions compile correctly.
2. Clone this repository and create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install the required packages with [Poetry](https://python-poetry.org/):

```bash
poetry install
```
The `filelock` package is included to handle database locking.

## Usage

Launch the command line interface with:

```bash
python -m goal_glide --help
```

### Managing Goals

Add a goal:

```bash
python -m goal_glide add "Write a novel"
```

List goals (active by default):

```bash
python -m goal_glide list
python -m goal_glide list --due-soon  # due within 3 days
python -m goal_glide list --overdue   # past deadline
```

Archive and restore:

```bash
python -m goal_glide archive <goal-id>
python -m goal_glide restore <goal-id>
```

Tags allow filtering goals:

```bash
python -m goal_glide tag add <goal-id> writing health
python -m goal_glide list --tag writing
```

### Pomodoro Sessions

Start and stop a session (optionally linking it to a goal):

```bash
python -m goal_glide pomo start --goal <goal-id>
python -m goal_glide pomo stop
```
The `--goal` flag records the session against the specified goal for
later statistics and reporting.

Motivational quotes are shown on completion when enabled (default). Use `goal config quotes --disable` to turn them off.

Desktop break reminders can be enabled with:

```bash
python -m goal_glide reminder enable
```

Configure interval and break length:

```bash
python -m goal_glide reminder config --break 5 --interval 30
```

### Thoughts

Capture a quick note optionally linked to a goal:

```bash
python -m goal_glide thought jot "Remember to research" -g <goal-id>
```

List recent thoughts:

```bash
python -m goal_glide thought list
```

### Statistics

Show the current week's focus history:

```bash
python -m goal_glide stats
```

Use `--month` for the last month and `--goals` to show totals for top goals.
Custom ranges can be specified with `--from` and `--to` using `YYYY-MM-DD` dates.

### TUI

If you prefer an interactive interface, run:

```bash
python -m goal_glide.tui
```

```
┏━━━━━━━━━━━━━ Goal Glide ━━━━━━━━━━━━━┓
┃ ID │ Title          Pri.  Tags      ┃
┃─────────────────────────────────────┃
┃ 1  │ Example goal   high  project   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

[Press S to start Pomodoro]

q Quit  s Start/Stop  a Add Goal  delete Archive
```

Basic keys:

- `q` – quit
- `s` – start or stop a session
- `a` – add a goal
- `delete` – archive goal

See the [TUI documentation](docs/tui.rst) for a full list of keys,
workflow tips and troubleshooting guidance. A screenshot of the interface
is included there under `docs/_static/`.

### Command Reference

Quick examples of common commands:

- **add** – create a goal.
  ```bash
  python -m goal_glide add "Read more books" --deadline 2030-01-01
  ```
- **remove** – delete a goal permanently.
  ```bash
  python -m goal_glide remove <goal-id>
  ```
- **update** – change a goal's title, priority or deadline.
  ```bash
  python -m goal_glide update <goal-id> --title "New title" --priority high --deadline 2030-01-01
  ```
- **archive** / **restore** – hide or unhide a goal.
  ```bash
  python -m goal_glide archive <goal-id>
  python -m goal_glide restore <goal-id>
  ```
- **tag add/rm** – manage goal tags.
  ```bash
  python -m goal_glide tag add <goal-id> writing
  python -m goal_glide tag rm <goal-id> writing
  ```
- **pomo start/stop** – run a pomodoro timer.
  ```bash
  python -m goal_glide pomo start
  python -m goal_glide pomo stop
  ```
- **reminder enable/disable** – toggle desktop reminders.
  ```bash
  python -m goal_glide reminder enable
  python -m goal_glide reminder disable
  ```
- **reminder config** – set break and interval lengths.
  ```bash
  python -m goal_glide reminder config --break 5 --interval 30
  ```
- **reminder status** – show current reminder settings.
  ```bash
  python -m goal_glide reminder status
  ```
- **stats** – view focus history. Use `--month` for the last month or specify
  a custom range with `--from` and `--to`.
  ```bash
  python -m goal_glide stats --month
  ```
- **report make** – build a progress report.
  ```bash
  python -m goal_glide report make --week
  ```
  Use `--from` and `--to` to generate a report for a custom date range.
- **version** – display package version.
  ```bash
  python -m goal_glide version
  ```

## Reports

Generate a summary of your sessions and goals with:

```bash
python -m goal_glide report make --week|--month|--all --format [html|md|csv] --out ~/reports/progress.html
# or specify a custom range
python -m goal_glide report make --from 2023-01-01 --to 2023-01-31 --format html --out ~/reports/january.html
```

The HTML and Markdown templates used for report generation live in `goal_glide/templates/`.

## Configuration and Data Files

Data is stored by default in `~/.goal_glide/db.json`. To use a different location set the `GOAL_GLIDE_DB_DIR` environment variable.
The database file is protected by `db.json.lock` to prevent corruption when multiple instances write concurrently.

Active pomodoro session data is written to `~/.goal_glide/session.json`. The
file is locked using `session.json.lock` while being updated.
Running multiple instances simultaneously is not recommended. Set
`GOAL_GLIDE_SESSION_FILE` to override this file path.

Configuration is kept in `~/.goal_glide/config.toml`. Set `GOAL_GLIDE_CONFIG_DIR` to override this path. The file controls:

- `quotes_enabled` – show a motivational quote after each session
- `reminders_enabled` – schedule desktop reminders
- `reminder_break_min` – length of the break after a pomodoro
- `reminder_interval_min` – how often to prompt for another session
- `pomo_duration_min` – default pomodoro duration

Run `python -m goal_glide config quotes --enable/--disable` or the reminder commands shown above to modify these settings.
Run `python -m goal_glide config show` to view the current configuration.

### Restoring From Backups

Backup the database and session files periodically to avoid data loss:

```bash
cp ~/.goal_glide/db.json ~/backups/db.json.bak
cp ~/.goal_glide/session.json ~/backups/session.json.bak
```

Restore them if something goes wrong:

```bash
cp ~/backups/db.json.bak ~/.goal_glide/db.json
cp ~/backups/session.json.bak ~/.goal_glide/session.json
```

### Exporting Sessions

Export all recorded sessions to a CSV file using the report command:

```bash
python -m goal_glide report make --all --format csv --out ~/sessions.csv
```

## Troubleshooting

- **Missing dependencies** – ensure all packages are installed via `poetry install` and that you are using a supported Python version.
- **No desktop notifications** – if Goal Glide prints a message about installing
  a helper, follow the instructions for your OS. On macOS install
  [`terminal-notifier`](https://github.com/julienXX/terminal-notifier) with
  Homebrew: `brew install terminal-notifier`. On Linux install the
  [`notify2`](https://pypi.org/project/notify2/) Python package
  (`pip install notify2`) or `notify-send` from `libnotify-bin`
  (`sudo apt install libnotify-bin`). On Windows install
  [`win10toast`](https://pypi.org/project/win10toast/)
  (`pip install win10toast`).
- **Database or path errors** – confirm that `GOAL_GLIDE_DB_DIR` and the new `GOAL_GLIDE_SESSION_FILE` point to writable locations. The database is protected by `db.json.lock` to avoid concurrent writes; remove the lock file if the program was interrupted.
- **Quotes do not appear** – network access might be blocked. In that case, a local quote database is used automatically.

## Running Tests

To execute the unit tests with coverage run:

```bash
pytest --cov=goal_glide --cov-report=term-missing
```

To run the test suite automatically before each push, configure Git to use the
included hooks directory:

```bash
git config core.hooksPath .githooks
```

With this option enabled, the test suite will run with coverage and `mypy`
whenever `git push` is invoked. The push will abort if tests, coverage
(`--cov-fail-under=80`) or type checks fail.

## Pre-commit Hooks

Run style and type checks automatically on each commit by installing
[pre-commit](https://pre-commit.com/) and enabling the hooks:

```bash
pip install pre-commit
pre-commit install
```

The configured hook runs `black`, `flake8`, `ruff` and `mypy` on staged files so
issues are caught early.

## Documentation

Sphinx configuration files live in the `docs` directory. Run `make html` inside that folder to build the HTML docs. The full manual with command examples, TUI key bindings and API documentation is available there. See [`docs/cli.rst`](docs/cli.rst), [`docs/tui.rst`](docs/tui.rst) and [`docs/api.rst`](docs/api.rst) for the individual sections.

---
Goal Glide is distributed under the terms of the GNU General Public License v3.

## Contributing

To run the test suite with coverage use:

```bash
pytest --cov=goal_glide
```

Enable the provided Git hooks so tests and type checks run automatically before each push:

```bash
git config core.hooksPath .githooks
```

This activates `.githooks/pre-push` which runs the same `pytest --cov=goal_glide` command along with `mypy`.

Install [pre-commit](https://pre-commit.com/) to check formatting and types on every commit:

```bash
pip install pre-commit
pre-commit install
```

The hooks defined in `.pre-commit-config.yaml` enforce coding standards using Black, Flake8, Ruff and Mypy.
