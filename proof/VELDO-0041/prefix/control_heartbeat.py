"""Stand-in for control_heartbeat.py at e231721, where no such module exists (red.py only).

At e231721 the trusted wrapper starts no heartbeat and the receiver watches none, renews no claim and
stops nobody for a missed one. Suite 67 reads nothing from this module but its heartbeat group's name,
and falls back to the same name when the module has none, so this file is empty on purpose. The
pre-change control_launch.py never loads it.
"""
