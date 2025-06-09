Text User Interface
===================

Goal Glide includes a simple TUI built with Textual. Launch it with::

   python -m goal_glide tui

Navigation and key bindings
---------------------------

``a``
    Add a new goal.

``delete``
    Archive the selected goal.

``s``
    Start or stop a pomodoro timer for the highlighted goal.

``t``
    Jot a quick thought linked to the goal.

``e``
    Edit the selected goal.

``q``
    Quit the interface.

Workflow example
----------------

::

   + Goals
   |-- Write blog post
   |-- Exercise daily

Use the arrow keys to move through the tree of goals. Press ``s`` to
start tracking a pomodoro for the highlighted goal. While the timer is
running a progress bar is shown in the details panel.
