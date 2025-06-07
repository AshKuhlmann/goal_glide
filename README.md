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

## Installation

1. Install Python 3.11 or newer.
2. Clone this repository and create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install the required packages:

```bash
pip install -r requirements.txt
```

Alternatively you can install the project in editable mode:

```bash
pip install -e .
```

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
python -m goal_glide pomo start --duration 25 --goal <goal-id>
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

### TUI

If you prefer an interactive interface, run:

```bash
python -m goal_glide.tui
```

## Configuration and Data Files

Data is stored by default in `~/.goal_glide/db.json`. To use a different location set the `GOAL_GLIDE_DB_DIR` environment variable.

Configuration is kept in `~/.goal_glide/config.toml` and controls:

- `quotes_enabled` – show a motivational quote after each session
- `reminders_enabled` – schedule desktop reminders
- `reminder_break_min` – length of the break after a pomodoro
- `reminder_interval_min` – how often to prompt for another session

Run `python -m goal_glide config quotes --enable/--disable` or the reminder commands shown above to modify these settings.
Run `python -m goal_glide config show` to view the current configuration.

## Troubleshooting

- **Missing dependencies** – ensure all packages from `requirements.txt` are installed and that you are using a supported Python version.
- **No desktop notifications** – the notify backend may require additional OS packages (e.g. `notify2` on Linux). Check the console output for warnings.
- **Database not updating** – confirm that `GOAL_GLIDE_DB_DIR` points to a writable directory and that only one instance of Goal Glide is manipulating the files at a time.
- **Quotes do not appear** – network access might be blocked. In that case, a local quote database is used automatically.

## Running Tests

To execute the unit tests run:

```bash
pytest
```

To run the test suite automatically before each push, configure Git to use the
included hooks directory:

```bash
git config core.hooksPath .githooks
```

With this option enabled, `pytest` and `mypy` will run whenever `git push`
is invoked and the push will abort if either the tests or type checks fail.

## Pre-commit Hooks

Run style and type checks automatically on each commit by installing
[pre-commit](https://pre-commit.com/) and enabling the hooks:

```bash
pip install pre-commit
pre-commit install
```

The configured hook runs `black`, `flake8` and `mypy` on staged files so
issues are caught early.

---
Goal Glide is distributed under the terms of the GNU General Public License v3.
