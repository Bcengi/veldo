"""One ordered stream of a Mac run's output, VELDO-0147 AC3. Standard library only.

The Mac wrapper reads the engine's standard output and standard error and appends every chunk it
reads to one file (FILE), each as one frame line tagged with its stream, so the order between the
two streams is kept as the wrapper saw it. The Mac receiver (control_worker) sends those lines down
its own channel while the engine runs and ends with one end frame. The main node
(control_launch.RemoteLaunch) reads them into the run's execution record.

Three places count the same thing with Tally, and none waits for another: the wrapper counts what
the engine printed, and those totals go into the result the Mac signs; the receiver counts what it
sent, for the end frame; the main node counts what it received. A record is kept as complete only
when the main node's totals equal the signed ones (control_execution_record.remote_problem).

A stream's totals are its line count (a last line with no newline counts), its byte count and the
SHA-256 of its bytes.
"""
import base64
import hashlib
import json

SCHEMA = 'veldo.macos_stream/v1'
STREAMS = ('stdout', 'stderr')
FIELDS = ('lines', 'bytes', 'sha256')
FILE = 'engine.stream'
CHUNK = 32768
END = 'end'


def chunk(stream, data):
    """One frame line carrying `data` as the engine printed it on `stream`."""
    return json.dumps({'stream': stream, 'data': base64.b64encode(data).decode('ascii')}).encode('ascii') + b'\n'


def end(totals):
    """The end frame: the sender's totals of what it sent."""
    return json.dumps({'stream': END, 'schema': SCHEMA, 'streams': totals}, sort_keys=True).encode('ascii') + b'\n'


def parse(line):
    """(stream, bytes) for a chunk frame, (END, totals) for an end frame, None for any other line."""
    try:
        frame = json.loads(line)
    except ValueError:
        return None
    if not isinstance(frame, dict):
        return None
    if frame.get('stream') == END and frame.get('schema') == SCHEMA:
        return END, frame.get('streams')
    if frame.get('stream') in STREAMS and isinstance(frame.get('data'), str):
        try:
            return frame['stream'], base64.b64decode(frame['data'], validate=True)
        except ValueError:
            return None
    return None


def problems(totals):
    """Whether `totals` is not exactly {stdout, stderr}, each {lines, bytes, sha256}."""
    if not isinstance(totals, dict) or set(totals) != set(STREAMS):
        return True
    for value in totals.values():
        if not isinstance(value, dict) or set(value) != set(FIELDS):
            return True
        digest = value['sha256']
        if (type(value['lines']) is not int or value['lines'] < 0 or type(value['bytes']) is not int
                or value['bytes'] < 0 or not isinstance(digest, str) or len(digest) != 64
                or any(c not in '0123456789abcdef' for c in digest)):
            return True
    return False


class Tally:
    def __init__(self):
        self.state = {name: [hashlib.sha256(), 0, 0, b''] for name in STREAMS}

    def feed(self, stream, data):
        if data:
            entry = self.state[stream]
            entry[0].update(data)
            entry[1] += len(data)
            entry[2] += data.count(b'\n')
            entry[3] = data[-1:]

    def totals(self):
        return {name: {'lines': newlines + (1 if size and last != b'\n' else 0), 'bytes': size,
                       'sha256': hasher.hexdigest()}
                for name, (hasher, size, newlines, last) in self.state.items()}
