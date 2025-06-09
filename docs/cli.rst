Command Line Interface
======================

The ``goal_glide`` command provides a collection of subcommands for
managing goals, thoughts and pomodoro sessions.  Below are some common
command sequences.

Add a new goal with high priority and a deadline::

   python -m goal_glide add "Write blog post" --priority high --deadline 2024-12-01

List all active goals::

   python -m goal_glide list

Archive an old goal and later restore it::

   python -m goal_glide archive <goal-id>
   python -m goal_glide restore <goal-id>

Start a pomodoro linked to a specific goal::

   python -m goal_glide pomo start --goal <goal-id>
   python -m goal_glide pomo stop

Key options
-----------

``--priority``
    One of ``low``, ``medium`` or ``high`` (defaults to ``medium``).

``--deadline``
    Optional due date in ``YYYY-MM-DD`` format shown in the TUI when
    approaching or past due.

``--tag``
    Add one or more tags to a goal for later filtering, e.g.
    ``goal_glide tag add <goal-id> work personal``.

``--goal``
    When starting a pomodoro this records the session against the goal so
    statistics can be generated later.

Run ``python -m goal_glide --help`` for a full list of commands and
options.
