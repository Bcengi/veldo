"""A stand-in for .veldo/control_service.py at b738c79, where no authority service exists. It supplies
only the names suite 66 calls and each does nothing, so every row reports the pre-change code by
assertion rather than by a missing name."""
CLOSURE = ()
EXIT_LOCK_HELD = None


class Refused(Exception):
    code = detail = guidance = None


def install(*args, **kwargs):
    return {}


def start(*args, **kwargs):
    return {}


def stop(*args, **kwargs):
    return {}


def uninstall(*args, **kwargs):
    return {}


def worker_writable(environment=None):
    return []


def taxonomy(code):
    return None
