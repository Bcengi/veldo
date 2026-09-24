"""Stand-in for control_retirement.py at e231721, where no such module exists (red.py only).

At e231721 the runner returns a worker slot from its own `_retire`, which forgets the dispatch's group
after the first attempt, holds no outcome or clone obligation and keeps no pending list. Suite 67 reads
nothing from this module (it reaches retirement only through the runner), so this file is empty on
purpose. The pre-change control_launch.py never loads it.
"""
