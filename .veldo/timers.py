"""Effective product timers. Wave 1 owners register their modules' entries here.

Call register at module initialization, effective at the arming site, and report in
start records. A profile also covers registrations made after it was selected.
"""
import math

WAIT_HANG_SECONDS = 600
_ENTRIES = {}
_PROFILE = None


def register(name, value, module, kind):
    if (not isinstance(name, str) or not name or not isinstance(module, str) or not module
            or kind not in ('contract', 'deadline') or type(value) not in (int, float)
            or not math.isfinite(value) or value <= 0):
        raise ValueError('invalid timer entry')
    entry = dict(name=name, value=value, module=module, kind=kind)
    if name in _ENTRIES and _ENTRIES[name] != entry:
        raise ValueError('conflicting timer: ' + name)
    _ENTRIES[name] = entry
    return effective(name)


def set_profile(except_name=None, *, hang_seconds=WAIT_HANG_SECONDS):
    """Set every timer but the named subject to the wait hang bound."""
    global _PROFILE
    if except_name is not None and except_name not in _ENTRIES:
        raise ValueError('unknown timer: ' + except_name)
    if type(hang_seconds) not in (int, float) or not math.isfinite(hang_seconds) or hang_seconds <= 0:
        raise ValueError('invalid hang bound')
    _PROFILE = (except_name, hang_seconds)


def reset_profile():
    global _PROFILE
    _PROFILE = None


def effective(name):
    entry = _ENTRIES[name]
    if _PROFILE is not None and name != _PROFILE[0]:
        return _PROFILE[1]
    return entry['value']


def report():
    return [dict(entry, value=effective(name)) for name, entry in sorted(_ENTRIES.items())]
