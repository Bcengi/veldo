"""The file memory directory handed to every run whose role lists it (VELDO-0184).

THE ITEM (AC1). A role's capability configuration (VELDO-0127) may carry a `file_memory` item, {"load": mode};
a run lists the file memory when its bound role revision carries it `always`. The one directory is the memory
record's (VELDO-0182) `file_memory` part, whichever account runs the turn, and its index is MEMORY.md there.

THE HANDOFF (`handed`). Checked before acceptance: a run that lists the item and whose memory record names no
present directory with an index is refused by name (`invalid_input:memory:file:absent`). The engine module turns
it into its own qualified form: Claude Code's `autoMemoryEnabled` and `autoMemoryDirectory` in the run's
generated flag settings, with CLAUDE_CODE_DISABLE_AUTO_MEMORY left unset (control_engine_claude); Codex's
workspace-write writable root and the index, after LAYOUT, in its developer instructions, its own memory feature
off (control_engine_codex). A version whose qualification record lacks the form launches no run that lists the
item (`missing_evidence:engine_baseline:<version>`).

THE RECORD (AC3). `launch_line` is the execution record's launch line, written right after the wrapper's
identity line: the handed directory, the form used and the digest of the index as the run loaded it (read at the
spawn), bound to the memory record's revision and the engine's qualification (engine, version, digest). Never
memory content: every read, write or edit of a file in the directory is the engine's own tool call line,
redacted as every line is (VELDO-0141).
"""
import hashlib
import os
from pathlib import Path
import stat

ITEM = 'file_memory'
INDEX = 'MEMORY.md'
MODES = ('always', 'when assigned')
ABSENT = 'invalid_input:memory:file:absent'
MISMATCH = 'binding_mismatch:engine_memory'
LAUNCH_LINE = 'file_memory'
# The one paragraph naming the layout, before the index, in a Codex run's developer instructions (AC2).
LAYOUT = ('Your file memory is the directory %s, shared with every other run of yours on any engine and account. '
          'Keep one fact per file there, each a short Markdown file with a descriptive name, and keep its index, '
          'MEMORY.md, current: one line per memory file, added, changed or removed in the same turn as the file. '
          'Read a memory file before relying on it. The index as it stands at the start of this turn follows.')


class Refused(Exception):
    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail
        super().__init__(code + (': ' + detail if detail else ''))


def valid_item(value):
    """Whether a capability configuration's `file_memory` item is well formed: {"load": one of MODES}."""
    return isinstance(value, dict) and set(value) == {'load'} and value['load'] in MODES


def listed(revision):
    """Whether a bound role revision lists the file memory `always`."""
    item = revision.get(ITEM) if isinstance(revision, dict) else None
    return valid_item(item) and item['load'] == 'always'


def _index(directory):
    """The index's bytes, read once through no link, else None."""
    try:
        fd = os.open(os.path.join(directory, INDEX), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        data = b''
        for block in iter(lambda: os.read(fd, 65536), b''):
            data += block
        return data
    except OSError:
        return None
    finally:
        os.close(fd)


def handed(memory, revision):
    """{directory, revision}: the file memory a run that lists the item is handed, else None for a run that does
    not. `memory` is the receiver's memory handoff (control_memory.handoff, None without a record). A directory
    that is absent, not a directory or without its index refuses the run by name."""
    if not listed(revision):
        return None
    try:
        directory = memory['definition']['parts'][ITEM]['data']
    except (TypeError, KeyError):
        raise Refused(ABSENT) from None
    if (not isinstance(directory, str) or not os.path.isabs(directory) or not os.path.isdir(directory)
            or os.path.islink(directory) or _index(directory) is None):
        raise Refused(ABSENT, str(directory))
    return {'directory': os.path.realpath(directory), 'revision': memory['revision']}


def loaded(handoff):
    """(index text, its digest) as the run loads it, read at the spawn; refused by name when it is gone."""
    data = _index(handoff['directory'])
    if data is None:
        raise Refused(ABSENT, handoff['directory'])
    return data.decode('utf-8', 'replace'), 'sha256:' + hashlib.sha256(data).hexdigest()


def same_directory(path, directory):
    """Whether an engine's reported memory path is `directory` (the binary writes it with a trailing separator)."""
    return isinstance(path, str) and bool(path) and os.path.normpath(path) == os.path.normpath(directory)


def launch_line(handoff, form, digest, binding):
    """The execution record's launch line (AC3): names, the digest and the bindings; never memory content."""
    return {LAUNCH_LINE: {'directory': handoff['directory'], 'form': form, 'index': INDEX, 'index_digest': digest,
                          'memory_revision': handoff['revision'],
                          'qualification': {k: (binding or {}).get(k) for k in ('engine', 'version', 'sha256')}}}


def index_path(handoff):
    return str(Path(handoff['directory']) / INDEX)
