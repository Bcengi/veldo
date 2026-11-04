"""One store server per ChromaDB part of the owner's memory: the only process that opens the store (VELDO-0183 AC4).

Run by the part's own interpreter in the part's code directory, as the user unit setup installs:

    <interpreter> -B control_memory_store.py <part> --code <dir> --data <dir> --socket <path> --state-root <root>
                  --python <factory python>

It takes an exclusive lock on a lock file in the part's data directory and holds it for its whole life; before it
opens the store it refuses by name a store another process holds open (conflict:memory_store_open:<part>:<pid>).
Then it imports the part's own tools (mem0_memory's mcp_server `mcp`, whose tools call memory_store; for memory_kb
the factory's control_memory_kb over its kb package) and serves them over a Unix socket under the state root that
only the owner's account can open (0600 in a 0700 directory, and the peer's uid checked), one call at a time.

ava-memory's `memory_add_smart`, which in the owner's code extracts with a paid model API, is answered here: the
text is extracted by Claude Code on one of the owner's subscription accounts through the account pool (`veldo memory
extract`, a run recorded on its account), and each extracted fact is added through the part's own `memory_add`. The
server's environment keeps only the names a process needs to run, so no paid-API key reaches the part's code.

VELDO-0182's check around a switch reads the store through this server while it runs (`check` and `copy`): its
adapter's reader over the store this process already holds open, and its safety copy taken by this process, so no
second process or client opens the store.

Logs one JSON line per event on standard error (the unit's journal): the start and lock with the part and socket,
and each call's server, tool, catalog revision, memory record revision and run; never memory content or a
credential. Standard library only, besides the part's own code.
"""
import argparse
import asyncio
import contextlib
import fcntl
import importlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import socket
import struct
import subprocess
import sys
import threading
import time

PARTS = ('ava_memory', 'memory_kb')
LOCK = 'veldo-store.lock'
# What the part's code and the extraction command need to run; nothing else of the starting environment reaches
# either, so no paid-API switch or login can (VELDO-0183 AC2).
KEEP = ('PATH', 'HOME', 'LANG', 'LC_ALL', 'TZ', 'USER', 'LOGNAME', 'XDG_RUNTIME_DIR')
# The credentials a call may carry from its bridge, each set for that call only (VELDO-0158 delivers it to the
# bridge, which never puts it in a tool's input).
CREDENTIALS = ('JARVIS_PASSPHRASE',)
SMART, ADD = 'memory_add_smart', 'memory_add'


class Refused(Exception):
    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail
        super().__init__(code + (': ' + detail if detail else ''))


def log(event, **fields):
    sys.stderr.write(json.dumps(dict(fields, event=event, at=round(time.time(), 3)), sort_keys=True) + '\n')
    sys.stderr.flush()


def holders(path, exclude=()):
    """The pids holding a file open at `path` or under it, read from /proc."""
    path = os.path.realpath(str(path))
    found = set()
    for entry in os.listdir('/proc'):
        if not entry.isdigit() or int(entry) in exclude:
            continue
        with contextlib.suppress(OSError):
            for fd in os.listdir('/proc/%s/fd' % entry):
                with contextlib.suppress(OSError):
                    target = os.readlink('/proc/%s/fd/%s' % (entry, fd))
                    if target == path or target.startswith(path + os.sep):
                        found.add(int(entry))
                        break
    return found


def take(part, data):
    """The store's lock, held for the server's life, then the refusal of a store any other process holds open."""
    lock = os.path.join(data, LOCK)
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        others = holders(lock, {os.getpid()})
        raise Refused('conflict:memory_store_open:%s:%s' % (part, min(others) if others else 'unknown')) from None
    others = holders(data, {os.getpid()})
    if others:
        os.close(fd)
        raise Refused('conflict:memory_store_open:%s:%d' % (part, min(others)))
    return fd, lock


def dump(value):
    if hasattr(value, 'model_dump'):
        try:
            return value.model_dump(mode='json', exclude_none=True)
        except TypeError:
            return value.model_dump()
    return value


def content(result):
    """A FastMCP call_tool answer as MCP content: a content sequence, a (content, structured) pair or a dict."""
    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, dict):
        return [dict(type='text', text=json.dumps(result, default=str))]
    return [dump(item) for item in result]


class Mem0:
    """mem0_memory's own tools: its mcp_server's FastMCP `mcp`, imported, never run."""

    def __init__(self, code, extract):
        self.mcp = importlib.import_module('mcp_server').mcp
        self.extract = extract

    def list(self):
        return [dump(tool) for tool in asyncio.run(self.mcp.list_tools())]

    def call(self, name, arguments):
        if name == SMART:
            return self.smart(arguments)
        return content(asyncio.run(self.mcp.call_tool(name, arguments)))

    def schema(self, name):
        tool = next((t for t in self.list() if t['name'] == name), None)
        if tool is None:
            raise KeyError(name)
        return tool.get('inputSchema') or {}

    def smart(self, arguments):
        """Extract on the owner's subscription, then add each fact with the part's own memory_add."""
        schema = self.schema(SMART)
        names = list(schema.get('required') or []) + list(schema.get('properties') or {})
        field = next((n for n in names if isinstance(arguments.get(n), str)), None)
        if field is None:
            raise ValueError('no text to extract from')
        extracted = self.extract(arguments[field])
        target = self.schema(ADD)
        properties = target.get('properties') or {}
        into = next(n for n in list(target.get('required') or []) + list(properties)
                    if (properties.get(n) or {}).get('type', 'string') == 'string')
        extra = {k: v for k, v in arguments.items() if k in properties and k not in (field, into)}
        added = [content(asyncio.run(self.mcp.call_tool(ADD, dict(extra, **{into: fact}))))
                 for fact in extracted['facts']]
        return [dict(type='text', text=json.dumps(dict(added=added, facts=len(extracted['facts']),
                                                       extraction=extracted['run'])))]


class KB:
    """memory_kb's tools, the factory's control_memory_kb over its kb package."""

    def __init__(self, factory):
        spec = importlib.util.spec_from_file_location('control_memory_kb', str(Path(factory) / 'control_memory_kb.py'))
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def list(self):
        return self.module.tools()

    def call(self, name, arguments):
        return [dict(type='text', text=json.dumps(self.module.call(name, arguments), default=str))]


class Inspector:
    """VELDO-0182's check, read inside this server: its adapter's reader (control_memory_adapter.inspect) over the
    store this process holds open, and its safety copy (control_memory_check.copy_data) taken by this process. The
    sampled rows go back over the socket only, as they come back over the adapter's pipe; never to the journal."""

    def __init__(self, part, data, factory, root):
        self.part, self.data, self.factory = part, data, factory
        self.copies = os.path.realpath(os.path.join(root, 'memory', 'copies'))
        self.loaded = {}

    def module(self, name):
        if name not in self.loaded:
            spec = importlib.util.spec_from_file_location('memory_store_' + name, str(Path(self.factory) / (name + '.py')))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.loaded[name] = module
        return self.loaded[name]

    def check(self, operation, sample):
        if operation not in ('before', 'after') or not isinstance(sample, list):
            return dict(error='invalid_input:memory_store:check')
        adapter = self.module('control_memory_adapter')
        # The adapter's memory_kb reader points kb.store's _get_collection at existing collections only; the
        # server's own tools get theirs back afterwards.
        kb = importlib.import_module('kb.store') if self.part == 'memory_kb' else None
        kept = kb._get_collection if kb else None
        try:
            # The part's code may print diagnostics, which may carry content: never to the journal.
            with open(os.devnull, 'w') as quiet, contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
                return adapter.inspect(dict(part=self.part, entry=dict(data=self.data), operation=operation,
                                            sample=sample))
        except Exception as error:  # noqa: BLE001 - the check's refusal names it, as the adapter's pipe does
            cause = str(error) if isinstance(error, adapter.Unavailable) else type(error).__name__
            return dict(error='unavailable_service:memory_store:%s:check' % self.part, cause=cause)
        finally:
            if kb:
                kb._get_collection = kept

    def copy(self, target):
        target = str(target or '')
        if (not os.path.isabs(target) or os.path.lexists(target)
                or os.path.dirname(os.path.dirname(os.path.realpath(target))) != self.copies):
            return dict(error='invalid_input:memory_store:copy')
        CHECK = self.module('control_memory_check')
        try:
            CHECK.copy_data(self.data, Path(target), self.part)
        except CHECK.M.Refused as error:
            return dict(error=error.code)
        return dict(copied=True)


def extractor(python, factory, root):
    """`veldo memory extract`: the text on its standard input, the facts and the run on its output."""
    def extract(text):
        argv = [python, '-B', str(Path(factory) / 'control_factory_setup_memory.py'), 'extract', '--state-root', root]
        done = subprocess.run(argv, input=json.dumps(dict(text=text)), capture_output=True, text=True, timeout=900,
                              env=dict(os.environ))
        answer = json.loads(done.stdout.strip().splitlines()[-1]) if done.stdout.strip() else {}
        if done.returncode or 'facts' not in answer:
            raise RuntimeError('extraction refused: %s' % answer.get('reason', 'no answer'))
        return answer
    return extract


def notify(message):
    address = os.environ.pop('NOTIFY_SOCKET', None)
    if not address:
        return
    if address.startswith('@'):
        address = '\0' + address[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as out:
        out.sendto(message, address)


def listen(path):
    directory = Path(path).parent
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = directory.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077 or directory.is_symlink():
        raise Refused('invalid_input:memory_store:socket_directory', str(directory))
    with contextlib.suppress(FileNotFoundError):
        os.unlink(path)  # left by a server that died; the lock this server holds says none runs now
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    old = os.umask(0o177)
    try:
        server.bind(str(path))
    finally:
        os.umask(old)
    os.chmod(path, 0o600)
    server.listen(32)
    return server


class Server:
    """Connections are read on threads of their own; every tool runs on the one thread that imported the part's
    code (the part's own objects, a SQLite connection among them, may be bound to it), one call at a time."""

    def __init__(self, part, tools, inspector=None):
        self.part, self.tools, self.calls, self.inspector = part, tools, queue.Queue(), inspector
        self.counts = {}

    def answer(self, request):
        """Called on a connection's thread: the call is queued for the tools' thread and waited for."""
        done, box = threading.Event(), []
        self.calls.put((request, box, done))
        done.wait()
        return box[0]

    def run(self, request):
        op = request.get('op')
        if op == 'list':
            return dict(tools=self.tools.list())
        if op in ('check', 'copy') and self.inspector:
            answer = (self.inspector.check(request.get('operation'), request.get('sample'))
                      if op == 'check' else self.inspector.copy(request.get('target')))
            log('memory_check', part=self.part, op=op, operation=request.get('operation'),
                outcome=answer.get('error') or 'ok')
            return answer
        if op != 'call' or not isinstance(request.get('name'), str):
            return dict(error='invalid_input:memory_store:request')
        about = request.get('about') if isinstance(request.get('about'), dict) else {}
        given = {k: v for k, v in (request.get('credentials') or {}).items() if k in CREDENTIALS and isinstance(v, str)}
        name, outcome = request['name'], 'ok'
        os.environ.update(given)
        try:
            result = dict(content=self.tools.call(name, request.get('arguments') or {}), isError=False)
        except Exception as error:  # noqa: BLE001 - a tool's own failure is its answer, as MCP gives it
            result = dict(content=[dict(type='text', text='%s: %s' % (type(error).__name__, error))], isError=True)
            outcome = 'error'
        finally:
            for key in given:
                os.environ.pop(key, None)
        key = '%s/%s' % (about.get('server') or self.part, name)
        self.counts[key] = self.counts.get(key, 0) + 1
        log('memory_call', part=self.part, server=about.get('server'), tool=name, outcome=outcome,
            catalog_revision=about.get('catalog_revision'), memory_revision=about.get('memory_revision'),
            run=about.get('run'), calls=self.counts[key])
        return result

    def handle(self, conn):
        with conn:
            uid = struct.unpack('3i', conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i')))[1]
            if uid != os.getuid():
                log('memory_peer_refused', part=self.part, uid=uid)
                return
            stream = conn.makefile('rwb')
            for line in stream:
                try:
                    request = json.loads(line)
                    answer = self.answer(request if isinstance(request, dict) else {})
                except ValueError:
                    answer = dict(error='invalid_input:memory_store:request')
                stream.write((json.dumps(answer) + '\n').encode())
                stream.flush()

    def accept(self, server):
        while True:
            conn, _ = server.accept()
            threading.Thread(target=self.handle, args=(conn,), daemon=True).start()

    def serve(self, server):
        threading.Thread(target=self.accept, args=(server,), daemon=True).start()
        while True:
            request, box, done = self.calls.get()
            try:
                box.append(self.run(request))
            except Exception as error:  # noqa: BLE001 - listing failed: the request is answered, never dropped
                box.append(dict(error='unavailable_service:memory_store:%s:%s' % (self.part, type(error).__name__)))
            done.set()


def main(argv=None):
    parser = argparse.ArgumentParser(prog='control_memory_store')
    parser.add_argument('part', choices=PARTS)
    for name in ('--code', '--data', '--socket', '--state-root', '--python'):
        parser.add_argument(name, required=True)
    args = parser.parse_args(argv)
    for name in list(os.environ):
        if name not in KEEP and name != 'NOTIFY_SOCKET':
            del os.environ[name]
    factory = str(Path(__file__).resolve().parent)
    try:
        os.chdir(args.code)
        sys.path.insert(0, args.code)
        fd, lock = take(args.part, args.data)
        log('memory_store_lock', part=args.part, lock=lock, pid=os.getpid())
        tools = (Mem0(args.code, extractor(args.python, factory, args.state_root)) if args.part == 'ava_memory'
                 else KB(factory))
        server = listen(args.socket)
    except Refused as error:
        log('memory_store_refused', part=args.part, reason=error.code)
        sys.stdout.write(json.dumps(dict(outcome='refused', reason=error.code)) + '\n')
        return 1
    log('memory_store_start', part=args.part, socket=args.socket, lock=lock, pid=os.getpid())
    notify(b'READY=1')
    try:
        Server(args.part, tools, Inspector(args.part, args.data, factory, args.state_root)).serve(server)
    finally:
        os.close(fd)
    return 0


if __name__ == '__main__':
    sys.exit(main())
