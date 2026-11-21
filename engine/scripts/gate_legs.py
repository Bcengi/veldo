#!/usr/bin/env python3
"""The gate's unconfined leg: the declared suites that run outside the confinement, by name.

Owner decision, Telegram 32403-32407, 2026-10-07 (VELDO-0208, "Unconfined leg"). The suites that
need the systemd user manager or nested strace cannot pass inside the gate's Landlock domain
without granting the escape it denies, and a KVM guest was rejected as too heavy. They run the
way they ran before that domain existed: outside it, in a separate, named leg of the unit and
integration stages, and their mutation cases in the mutation stage's unconfined leg (the stage is
declared with the command MUTATION_COMMAND; scripts/check_gate_mutations.py runs that leg with
mutation_leg and record below; since a mutation case runs its whole suite in one worker, a case of
a suite listed only for some rows is refused, never run there). Every other stage and suite stays
confined.

THE LIST IS THE AUTHORITY'S, NEVER THE CANDIDATE'S. It is read from beside this file
(scripts/gate_unconfined.json in the authority checkout), a protected path, so adding a suite to
it is a reviewed change with the owner's approval. The installer ships no list: the one this
repository carries is its own owner's decision, so an adopter's gate confines every stage. A candidate's own copy of
the list or an environment variable it sets decides nothing: the leg variables a candidate command
sees are set here, and the caller's are dropped. The candidate's dispatcher applies the list
(scripts/selftest.py, scripts/run_scope.py, scripts/suites/shared.py, and scripts/check_first_use.py,
which hands the leg to its nested selftest.py), and those files are protected too; without that, a
candidate could make its dispatcher ignore the leg. selftest.py and check_first_use.py keep scripts/
and scripts/suites/ behind the standard library on sys.path, so no unprotected file there shadows a
standard-library module they import, and selftest.py loads run_scope.py and suites/shared.py from
their fixed paths, so no unprotected file stands in for either; this runner runs from the authority
as python3 -I -S.

WHAT THE UNCONFINED LEG TRUSTS, stated because it is the cost of the decision. That leg executes
the candidate's dispatcher and the listed suites with the owner's own authority, exactly as before
VELDO-0208; the list and the protected dispatcher bound which suites and rows run there, not
what the code of a listed suite does once it runs. Review of the candidate is the safeguard for
that code. That is why the leg is printed with its suite list on the stage line and recorded in the
stamp and the gate event: it is visible on every run, never silent.

  gate_legs.py --root <candidate> --stage <name> --record <file> -- <command>
      One gate stage. A stage the list declares, with exactly its declared command, runs twice:
      the confined leg (every suite except the ones listed whole, and every row of a suite listed
      for some rows except those rows) through scripts/gate_candidate.py, then the unconfined leg
      (only the listed suites and rows) directly. Any other stage runs confined only.
  gate_legs.py --declared --stage <name> -- <command>
      Exit 0 when the list declares this stage with exactly this command, 1 when it does not, 2
      when the list is invalid. verify.sh asks before the stage runs, so it knows a leg is expected
      whatever candidate code later does to the record.
  gate_legs.py --load-proof --root <candidate> --record <file> [--opened <record>]
      The load-proof leg (VELDO-0358, AC13; the section THE LOAD-PROOF LEG below): every suite of the
      proven set in its own process under the load of scripts/gate_load.py. Exit 1 on any failed or
      hung row and on load_not_applied. --load-stamp <file> [--wall <seconds>] prints the stamp's
      "load" value from the leg's record.
  gate_legs.py --stamp <file> [--expect <stage,stage>]
      The stamp's "unconfined" value: the declaration's digest and the entries each stage ran
      unconfined. With --expect, a record that is missing, empty, unreadable or does not hold
      exactly those stages is an error, never {}: candidate code in the unconfined leg can delete or
      truncate the record, and that must not read as "no unconfined leg ran".

THE MEASURED BUDGET (VELDO-0214). The integration stage's command, scripts/check_first_use.py, runs
the identical selftest set under the identical confinement that the unit stage's same leg ran just
before it, so the unit leg's wall time is the measurement its budget is derived from. This runner
times every leg it runs. A unit leg that passed is recorded in the authority's leg-time store
(LEG_TIMES, under the owner's ~/.cache, which the confined leg cannot write), keyed by this
authority checkout, the declaration's digest and the leg; a leg that failed may have stopped early,
so it records nothing and the last passing measurement stands. Each integration leg is then handed
the matching unit leg's last fresh measurement in UNIT_SECONDS, beside the leg variables: this gate
run's when the unit leg ran here, an earlier run's when it did not (a reused or skipped unit stage
records nothing), and nothing at all when the store has none.

WHO CAN TOUCH THE VALUE. Like the declaration digest, the variable is set only here and the
caller's is always dropped, so a candidate cannot set it. The confined leg cannot reach the store
at all: the gate profile denies ~/.cache/veldo to it. The unconfined leg runs with the owner's own
authority (VELDO-0208), so its code can rewrite the store like anything else the owner can write,
including the confined leg's entry between the unit and the integration stage. That buys nothing
toward a verdict: the budget only bounds how long the gate waits, scripts/check_first_use.py holds
it between a floor of 1800s and a ceiling of 6 hours whatever the store says, and a run over it is
CANNOT ANSWER, which is red.

THE STORE HOLDS ONLY GATE MEASUREMENTS. After each recording, only files of authority checkouts
that no longer exist are removed. Files for existing checkouts and unfinished .pending- files
stay. The owner's store records only the authority's own list: a suite that
drives this runner over a fixture list is testing the runner, not timing the gate, and its leg is
said and not recorded. Where the authority lives is no test: the lander runs the gate from an
installation it lays down under the system temporary directory
(tempfile.mkdtemp(prefix="veldo-observation-") / "installed"), and that gate's measurement must
reach its own integration stage. A suite that drives a temporary authority copy over that copy's
own list keeps out of the owner's store from its own side, by giving that driver a scratch HOME.
There is no environment override for the store's path, because that would be one more input to
forge.

THE LEG'S SHARDS (VELDO-0221). The candidate's dispatcher runs a leg's suites as parallel shards,
and each shard claims its measured CPU and anonymous memory from the gate-wide ledger (VELDO-0216).
THE LEDGER CHANNEL ITSELF NEVER REACHES A CANDIDATE COMMAND (VELDO_GATE_LEDGER_FD stays this
runner's, as VELDO-0216 requires of every node). This runner asks the ledger on the dispatcher's
behalf: a declared leg's command is handed a channel of its own (VELDO_GATE_SHARD_LEDGER_FD, a socket
pair this runner serves while the leg runs; ShardClaims below), over which the dispatcher can only
ask to start one named suite's shard and say that it ended. THE CLAIM IS READ FROM THE AUTHORITY'S
STORE, never from the request: what that suite's shard measured in this leg's last passing unit
stage, one core and 1 GiB for a suite never measured; the size a candidate names in its request is
not read. The measurement itself is reported by the leg's dispatcher, a process of the candidate's
tree, over the metrics pipe, and a process of the same account outside every domain (an unconfined
shard) can reach that pipe; so a stored claim is evidence of what ran, not a value the authority
computed alone, and the gate ledger holds every shard's claim to what it can always grant
(scripts/gate_schedule.py Ledger.shard_claim) so an oversized one costs parallelism, never the leg. The same measurements are handed to the dispatcher (VELDO_GATE_SHARD_CLAIMS), which only
orders its shards by them. In the unit stage the command also gets a pipe the dispatcher writes
each passing shard's wall seconds, CPU seconds and peak anonymous memory to
(VELDO_GATE_SHARD_METRICS_FD), which this runner records after a passing leg under the same rule as
the leg's own time: only the authority's own list reaches the owner's store. The confined leg gets
both descriptors through the launcher's --inherit, the unconfined leg as inherited descriptors; the
dispatcher keeps them from every shard, and scripts/selftest.py and scripts/run_scope.py are
protected. All three variables are set only here, the caller's always dropped. The manager is not
claimed per shard: the unconfined leg's node already holds it for the leg (scripts/gate_graph.json),
and the dispatcher admits the manifest's exclusive and shared manager suites inside that hold.
"""
import argparse
import hashlib
import fcntl
import math
import importlib.util
import json
import os
from pathlib import Path
import re
import select
import signal
import subprocess
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
DECLARATION = HERE / 'gate_unconfined.json'
SCHEMA = 'veldo.gate-unconfined/v1'
# verify.sh's mutation stage is no shell command: CHECK_mutation declares it by this text.
MUTATION_COMMAND = 'authority mutation stage'
LEG, ENTRIES, DIGEST = 'VELDO_GATE_LEG', 'VELDO_GATE_UNCONFINED', 'VELDO_GATE_DECLARATION'
# VELDO-0214: the unit leg's measured seconds, handed to the matching integration leg.
UNIT_SECONDS = 'VELDO_GATE_UNIT_SECONDS'
# VELDO-0221: what a leg's shard dispatcher is handed (see the docstring).
LEDGER_CHANNEL = 'VELDO_GATE_LEDGER_FD'
SHARD_LEDGER = 'VELDO_GATE_SHARD_LEDGER_FD'
SHARD_CLAIMS, SHARD_METRICS = 'VELDO_GATE_SHARD_CLAIMS', 'VELDO_GATE_SHARD_METRICS_FD'
SHARD_CHANNELS = (SHARD_LEDGER, SHARD_METRICS)
SHARD_UNMEASURED = {'cpu': 1.0, 'memory': 1 << 30}
MEASURED_STAGE, BUDGETED_STAGE = 'unit', 'integration'
LEG_TIMES = Path.home() / '.cache' / 'veldo' / 'gate-leg-seconds'
RESOURCE_READ_MAX_AGE_DAYS = 30
TIMES_NAME = re.compile(r'^[0-9a-f]{32}\.json$')
SUITE = re.compile(r'^[0-9A-Za-z][0-9A-Za-z_]*$')
ROWS = re.compile(r'^[a-z][a-z0-9-]*$')


class Invalid(ValueError):
    pass


def load(path=DECLARATION):
    """(declaration, digest) of the authority's list, or Invalid naming what is wrong."""
    try:
        raw = Path(path).read_bytes()
        document = json.loads(raw)
    except (OSError, ValueError) as error:
        raise Invalid('unreadable: %s' % error)
    if not isinstance(document, dict) or set(document) != {'schema', 'authority', 'stages', 'suites'}:
        raise Invalid('keys must be exactly schema, authority, stages, suites')
    if document['schema'] != SCHEMA:
        raise Invalid('schema must be %s' % SCHEMA)
    if not isinstance(document['authority'], str) or not document['authority'].strip():
        raise Invalid('authority must name the decision')
    stages = document['stages']
    if not isinstance(stages, dict) or not stages or not all(
            isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in stages.items()):
        raise Invalid('stages must map each stage to its exact command')
    suites, seen = document['suites'], set()
    if not isinstance(suites, list) or not suites:
        raise Invalid('suites must be a non-empty list')
    for entry in suites:
        if not isinstance(entry, dict) or not set(entry) <= {'suite', 'rows', 'reason'} \
                or not {'suite', 'reason'} <= set(entry):
            raise Invalid('each entry is {suite, reason} with optional rows: %r' % (entry,))
        if not isinstance(entry['suite'], str) or not SUITE.match(entry['suite']):
            raise Invalid('suite name %r is not a single safe name' % (entry['suite'],))
        if 'rows' in entry and not (isinstance(entry['rows'], str) and ROWS.match(entry['rows'])):
            raise Invalid('rows of %s must be a lower-case tag' % entry['suite'])
        if not isinstance(entry['reason'], str) or len(entry['reason'].strip()) < 10:
            raise Invalid('%s has no reason' % entry['suite'])
        if entry['suite'] in seen:
            raise Invalid('%s is listed twice' % entry['suite'])
        seen.add(entry['suite'])
    return document, 'sha256:' + hashlib.sha256(raw).hexdigest()


def entries(document):
    """The leg's entries in the form the candidate's dispatcher reads: name or name:rows."""
    return [e['suite'] + (':' + e['rows'] if 'rows' in e else '') for e in document['suites']]


def _env(leg=None, listed=(), digest=None, measured=None, claims=None):
    env = {k: v for k, v in os.environ.items() if k not in (LEG, ENTRIES, DIGEST, UNIT_SECONDS)}
    for authority_variable in ('VELDO_GATE_LEDGER_FD', 'VELDO_GATE_GRAPH_DIGEST', SHARD_CLAIMS, *SHARD_CHANNELS):
        env.pop(authority_variable, None)
    if leg:
        env[LEG], env[ENTRIES], env[DIGEST] = leg, ','.join(listed), digest
        if measured is not None:
            env[UNIT_SECONDS] = json.dumps(dict(measured, leg=leg, declaration=digest),
                                           sort_keys=True, separators=(',', ':'))
        if claims:
            env[SHARD_CLAIMS] = json.dumps(claims, sort_keys=True, separators=(',', ':'))
    return env


def _shards_file(times, digest, leg):
    """This authority's per-suite shard measurements for one declaration and leg."""
    identity = '%s\n%s\nshards\n%s' % (HERE.parent, digest, leg)
    return Path(times) / (hashlib.sha256(identity.encode()).hexdigest()[:32] + '.json')


def read_shard_claims(times, digest, leg):
    """{suite: {cpu, memory, seconds}} last recorded for this authority, declaration and leg, or {}.
    A record that is not this authority's, or older than RESOURCE_READ_MAX_AGE_DAYS, is not read."""
    try:
        path = _shards_file(times, digest, leg)
        document = json.loads(path.read_text())
        if document.get('authority') != str(HERE.parent) or document.get('declaration') != digest \
                or document.get('leg') != leg or not isinstance(document.get('suites'), dict) \
                or time.time() - path.stat().st_mtime > RESOURCE_READ_MAX_AGE_DAYS * 86400:
            return {}
    except (OSError, ValueError, AttributeError):
        return {}
    claims = {}
    for suite, item in document['suites'].items():
        try:
            values = {key: item[key] for key in ('cpu', 'memory', 'seconds')}
        except (TypeError, KeyError):
            continue
        if SUITE.match(suite) and all(type(v) in (int, float) and math.isfinite(v) and v > 0
                                      for v in values.values()):
            claims[suite] = values
    return claims


def shard_measurements(text):
    """{suite: {cpu, memory, seconds}} from the lines a leg's dispatcher wrote to its metrics pipe.
    A line that is not one suite's finite positive wall, CPU and memory is dropped."""
    measured = {}
    for line in text.splitlines():
        try:
            item = json.loads(line)
            suite, wall = item['suite'], item['wall_seconds']
            cpu, memory = item['cpu_seconds'], item['peak_anon_bytes']
        except (ValueError, TypeError, KeyError):
            continue
        if not isinstance(suite, str) or not SUITE.match(suite) or not all(
                type(v) in (int, float) and math.isfinite(v) and v > 0 for v in (wall, cpu, memory)):
            continue
        # A shard never claims under a tenth of a core: a suite that mostly waits still starts an
        # interpreter and its preamble.
        measured[suite] = {'cpu': max(0.1, cpu / wall), 'memory': memory, 'seconds': wall}
    return measured


def record_shard_claims(times, digest, leg, measured):
    """Keep each suite's largest measured claim and its latest wall time; said, not fatal."""
    if not measured:
        return False
    try:
        Path(times).mkdir(mode=0o700, parents=True, exist_ok=True)
        suites = read_shard_claims(times, digest, leg)
        for suite, item in measured.items():
            previous = suites.get(suite, {})
            suites[suite] = {'cpu': max(item['cpu'], previous.get('cpu', 0)),
                             'memory': max(item['memory'], previous.get('memory', 0)),
                             'seconds': item['seconds']}
        target = _shards_file(times, digest, leg)
        fd, pending = tempfile.mkstemp(prefix='.pending-', dir=str(target.parent))
        with os.fdopen(fd, 'w') as handle:
            json.dump({'authority': str(HERE.parent), 'declaration': digest, 'leg': leg, 'suites': suites},
                      handle, sort_keys=True)
        os.replace(pending, target)
    except OSError as error:
        print('   unit: could not record the %s leg\'s shard measurements in %s (%s)' % (leg, times, error),
              flush=True)
        return False
    prune_times(times, keep=target)
    return True


def _times_file(times, digest):
    """This authority's leg-time file for one declaration: a different list is different legs."""
    key = hashlib.sha256(('%s\n%s' % (HERE.parent, digest)).encode()).hexdigest()[:32]
    return Path(times) / (key + '.json')


def read_times(times, digest):
    """{leg: {seconds, at, run}} last recorded for this authority and declaration, or {}."""
    try:
        document = json.loads(_times_file(times, digest).read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(document, dict) or document.get('declaration') != digest \
            or not isinstance(document.get('legs'), dict):
        return {}
    return {leg: item for leg, item in document['legs'].items() if isinstance(item, dict)}


def _record_time_locked(times, digest, leg, seconds, run):
    """Record one passing unit leg's wall time; a store that cannot be written is said, not fatal."""
    try:
        Path(times).mkdir(mode=0o700, parents=True, exist_ok=True)
        legs = read_times(times, digest)
        legs[leg] = {'seconds': round(seconds, 1), 'run': run,
                     'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        target = _times_file(times, digest)
        fd, pending = tempfile.mkstemp(prefix='.pending-', dir=str(target.parent))
        with os.fdopen(fd, 'w') as handle:
            json.dump({'authority': str(HERE.parent), 'declaration': digest, 'legs': legs}, handle,
                      sort_keys=True)
        os.replace(pending, target)
    except OSError as error:
        print('   unit: could not record the %s leg time in %s (%s); the integration stage uses '
              'the last measurement recorded there' % (leg, times, error), flush=True)
        return False
    prune_times(times, keep=target)
    return True


def record_time(times, digest, leg, seconds, run):
    # Confined and unconfined unit nodes may finish together. Serialize the existing
    # read/replace transaction so neither fresh measurement overwrites its sibling.
    try:
        Path(times).mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(times, os.O_RDONLY | os.O_DIRECTORY)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            return _record_time_locked(times, digest, leg, seconds, run)
        finally:
            os.close(descriptor)
    except OSError as error:
        print('   unit: could not lock the leg-time store %s (%s); using the last measurement' %
              (times, error), flush=True)
        return False


def _resources_file(times, digest, node):
    identity = '%s\n%s\n%s' % (HERE.parent, digest, node)
    return Path(times) / (hashlib.sha256(identity.encode()).hexdigest()[:32] + '.json')


def read_resources(times, digest, node):
    try:
        path = _resources_file(times, digest, node)
        item = json.loads(path.read_text())
        if item.get('authority') != str(HERE.parent) or item.get('digest') != digest \
                or item.get('node') != node or time.time() - path.stat().st_mtime > RESOURCE_READ_MAX_AGE_DAYS * 86400:
            return None
        for key in ('cpu_rate', 'peak_anon_bytes'):
            value = item[key]
            if type(value) not in (float, int) or not math.isfinite(value) or value <= 0:
                return None
        return item
    except (OSError, ValueError, TypeError, KeyError):
        return None


def record_resources(times, digest, node, seconds, metrics):
    # Called only by the authority scheduler after a passing, input-stable node.
    # One file per node avoids read/modify/write races between independent legs.
    if seconds <= 0 or metrics.get('metrics_source') != 'cgroup-v2-anon-sampled-50ms':
        return
    Path(times).mkdir(mode=0o700, parents=True, exist_ok=True)
    target = _resources_file(times, digest, node)
    previous = read_resources(times, digest, node) or {}
    # VELDO-0221: a leg node that ran its suites as shards records its dispatcher's claim, not its
    # cgroup's total (scripts/gate_schedule.py LEG_DISPATCHER). The two are different quantities, so
    # the larger-of-two rule holds only between records of one kind: the other kind is replaced.
    dispatcher = metrics.get('dispatcher') is True
    if (previous.get('dispatcher') is True) != dispatcher:
        previous = {}
    item = dict(authority=str(HERE.parent), digest=digest, node=node, wall_seconds=seconds,
                cpu_seconds=metrics['cpu_seconds'], dispatcher=dispatcher,
                cpu_rate=max(previous.get('cpu_rate', 0), metrics['cpu_seconds'] / seconds),
                peak_anon_bytes=max(previous.get('peak_anon_bytes', 0), metrics['peak_anon_bytes']),
                at=time.time())
    fd, pending = tempfile.mkstemp(prefix='.pending-', dir=str(target.parent))
    with os.fdopen(fd, 'w') as handle:
        json.dump(item, handle, sort_keys=True)
    os.replace(pending, target)
    prune_times(times, keep=target)


def prune_times(times, keep):
    """Remove only timing files whose authority checkout is gone, never `keep` or .pending-
    files. An unreadable file or checkout is left. Said, not fatal. Returns the names removed."""
    removed = []
    try:
        listing = list(os.scandir(str(times)))
    except OSError:
        return removed
    for entry in listing:
        if entry.name == Path(keep).name or not TIMES_NAME.match(entry.name):
            continue
        try:
            if not entry.is_file(follow_symlinks=False):
                continue
            try:
                authority = json.loads(Path(entry.path).read_text()).get('authority')
            except (ValueError, AttributeError):
                continue
            if not isinstance(authority, str) or not authority:
                continue
            try:
                Path(authority).stat()
            except FileNotFoundError:
                os.unlink(entry.path)
                removed.append(entry.name)
        except OSError:
            continue
    if removed:
        print('   unit: removed %d leg-time file%s from %s (authority checkout gone)'
              % (len(removed), '' if len(removed) == 1 else 's', times),
              flush=True)
    return removed


def owner_store_refusal(times, path, authority=None):
    """Why this leg's time must not go into the owner's store, or None. Only the owner's store is
    guarded: a caller that names its own store is testing the runner and records there."""
    if Path(times) != LEG_TIMES:
        return None
    authority = Path(HERE.parent if authority is None else authority).resolve()
    if Path(path).resolve() != (authority / 'scripts' / DECLARATION.name):
        return 'the list %s is not this authority\'s own' % path
    return None


def measurement(times, digest, leg, run):
    """The integration leg's handed value: the matching unit leg's last fresh time, or None."""
    item = read_times(times, digest).get(leg)
    try:
        seconds = float(item['seconds'])
    except (TypeError, KeyError, ValueError):
        return None
    if not seconds > 0 or seconds == float('inf'):
        return None
    return {'seconds': seconds, 'at': str(item.get('at')),
            'fresh': 'this gate run' if item.get('run') == run else 'an earlier gate run'}


class ShardClaims:
    """The leg's side of the gate ledger, served to the candidate's shard dispatcher (VELDO-0221).

    The dispatcher writes one request per line, {operation: acquire | release, name: <suite>}, and
    reads one reply, {granted: bool} or {error: text}. An acquire is forwarded to the gate ledger
    with THIS runner's claim for that suite (`claims`, else SHARD_UNMEASURED); a refusal there is a
    refusal here and the dispatcher asks again later. Nothing a candidate sends reaches the ledger
    but a suite's name, checked first: a malformed line, a name that is no suite name, a second
    acquire of a held name or a release of one not held is answered with an error and never
    forwarded, because the scheduler fails a node whose channel carries an invalid request. What
    the dispatcher still holds when the leg ends is released here, so a dispatcher that died does
    not leave its node holding claims."""

    def __init__(self, ledger, claims):
        import socket
        import threading
        self.ledger = socket.socket(fileno=os.dup(int(ledger)))
        self.stream = self.ledger.makefile('rwb', buffering=0)
        self.claims, self.held, self.asked = dict(claims), set(), []
        self.ours, self.theirs = socket.socketpair()
        os.set_inheritable(self.theirs.fileno(), True)
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def fileno(self):
        return self.theirs.fileno()

    def forward(self, operation, name, claim=None):
        self.stream.write((json.dumps({'operation': operation, 'name': name, 'claim': claim}) + '\n').encode())
        raw = self.stream.readline(65537)
        if not raw or len(raw) > 65536:
            raise OSError('the gate ledger closed its channel')
        return json.loads(raw)

    def answer(self, line):
        try:
            request = json.loads(line)
            operation, name = request['operation'], request['name']
        except (ValueError, TypeError, KeyError):
            return {'error': 'malformed request'}
        if not isinstance(name, str) or not SUITE.match(name) or len(name) > 100:
            return {'error': 'not a suite name'}
        if operation == 'acquire' and name not in self.held:
            claim = dict(self.claims.get(name, SHARD_UNMEASURED))
            reply = self.forward('acquire', name, {'cpu': claim['cpu'], 'memory': claim['memory'],
                                                   'manager': 'none', 'ports': [], 'host_lock': 'none'})
            self.asked.append((name, claim['cpu'], claim['memory'], reply.get('granted')))
            if reply.get('granted') is True:
                self.held.add(name)
            return {'error': reply['error']} if 'error' in reply else {'granted': reply.get('granted') is True}
        if operation == 'release' and name in self.held:
            self.held.discard(name)
            reply = self.forward('release', name)
            return {'error': reply['error']} if 'error' in reply else {'granted': True}
        return {'error': 'invalid operation, a second acquire or a foreign release'}

    def serve(self):
        try:
            stream = self.ours.makefile('rwb', buffering=0)
            for line in stream:
                if len(line) > 4096:
                    break
                stream.write((json.dumps(self.answer(line)) + '\n').encode())
        except (OSError, ValueError):
            pass

    def close(self):
        """After the leg's command ended: stop serving and release what it still held."""
        import socket
        self.theirs.close()
        try:
            self.ours.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.thread.join(120)
        self.ours.close()
        for name in sorted(self.held):
            try:
                self.forward('release', name)
            except (OSError, ValueError):
                break
        self.held.clear()
        self.stream.close()
        self.ledger.close()


def _channels(env):
    """The leg's descriptors named in an environment leg_run built: {variable: descriptor}."""
    return {name: int(env[name]) for name in SHARD_CHANNELS if env.get(name, '').isdigit()}


def confined(root, command, env):
    """The stage command in the gate's domain, exactly as verify.sh's veldo_candidate runs it. A
    leg's channels (VELDO-0221) cross the launcher by its --inherit, which gate_candidate.py does
    not take: the launcher is then started here with the same arguments gate_candidate.py gives it."""
    channels = _channels(env)
    if not channels:
        return subprocess.run([sys.executable, '-I', '-S', str(HERE / 'gate_candidate.py'), '--root',
                               str(root), '--', 'bash', '-c', command], env=env,
                              stdin=subprocess.DEVNULL, pass_fds=_launcher_fds()).returncode
    # The launcher and its configuration are the ones beside gate_candidate.py, as that file finds them.
    scripts = (HERE / 'gate_candidate.py').resolve().parent
    config = env.get('VELDO_AGENT_CONFIG', str(scripts / 'agent_sandbox.json'))
    inherit = [word for fd in channels.values() for word in ('--inherit', str(fd))]
    code = subprocess.run([sys.executable, '-I', '-S', str(scripts / 'agent_sandbox.py'), '--profile', 'gate',
                           '--config', config, '--worktree', str(root), *inherit, '--', 'bash', '-c', command],
                          env=env, stdin=subprocess.DEVNULL, close_fds=True,
                          pass_fds=(*_launcher_fds(), *channels.values())).returncode
    if code:
        print('candidate execution failed in store-denied domain (publication forbidden)', file=sys.stderr)
    return code


def _launcher_fds():
    """Inside a tree the agent launcher made, the launcher this starts is nested and is handed the
    tree's marker (VELDO-0210 AC6), as the launcher gate_candidate.py runs finds it; nothing
    elsewhere."""
    launcher = (HERE / 'gate_candidate.py').resolve().parent / 'agent_sandbox.py'
    spec = importlib.util.spec_from_file_location('veldo_agent_sandbox', launcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.launcher_fds()


# What verify.sh exports for its own launchers, never for candidate code. The confined launcher
# reads VELDO_EXPECTED_GIT_COMMON and then drops it (agent_sandbox.py); handed on here, it made every
# gate a listed suite runs for a fixture repository check that repository against the authority's
# common directory and refuse it, so 0050 and 0148 failed only inside the real gate.
AUTHORITY_ONLY = ('VELDO_EXPECTED_GIT_COMMON', 'VELDO_GATE_LEDGER_FD', 'VELDO_GATE_GRAPH_DIGEST')


def unconfined(root, command, env):
    """The stage command outside every domain, in the candidate, as before VELDO-0208. A leg's
    channels (VELDO-0221) reach it as inherited descriptors; the gate ledger's own never does."""
    env = {k: v for k, v in env.items() if k not in AUTHORITY_ONLY}
    return subprocess.run(['bash', '-c', command], cwd=str(root), env=env, stdin=subprocess.DEVNULL,
                          pass_fds=tuple(_channels(env).values())).returncode


def run_stage(root, stage, command, record, path=DECLARATION, times=LEG_TIMES, leg=None, prior=None):
    try:
        document, digest = load(path)
    except Invalid as error:
        print('   %s: the unconfined list %s is invalid (%s); nothing ran, in either leg'
              % (stage, path, error), flush=True)
        return 1
    declared = document['stages'].get(stage)
    if declared is None or declared != command:
        # Not a declared leg: the whole stage is confined, and no caller variable reaches it.
        return confined(root, command, _env())
    listed = entries(document)
    whole = [e for e in document['suites'] if 'rows' not in e]
    if leg != 'unconfined':
        print('   %s: confined leg - every suite except the %d listed whole, and of the %d listed for some '
              'rows, every row but those' % (stage, len(whole), len(listed) - len(whole)), flush=True)
    # The record file is this gate run's own (verify.sh makes it with mktemp), so its path names
    # the run a measurement came from.
    run = str(record)

    def leg_run(leg, runner):
        handed = (prior.get(leg) if prior is not None else measurement(times, digest, leg, run)) if stage == BUDGETED_STAGE else None
        if stage == BUDGETED_STAGE:
            print('   %s: %s leg budget input: %s' % (stage, leg, 'unit %s leg %.1fs, %s (%s)'
                  % (leg, handed['seconds'], handed['fresh'], handed['at']) if handed
                  else 'no unit %s leg measurement recorded' % leg), flush=True)
        # VELDO-0221: the leg's shard dispatcher asks this runner for each shard's claim on the gate
        # ledger, with the claims the last passing unit leg measured, and in the unit stage reports
        # what it measures. See the docstring: the ledger's own channel stays here.
        claims = read_shard_claims(times, digest, leg)
        environment = _env(leg, listed, digest, handed, claims)
        asking, metrics, write = None, None, None
        if os.environ.get(LEDGER_CHANNEL, '').isdigit():
            asking = ShardClaims(os.environ[LEDGER_CHANNEL], claims)
            environment[SHARD_LEDGER] = str(asking.fileno())
        if stage == MEASURED_STAGE:
            metrics, write = os.pipe()
            os.set_inheritable(write, True)
            environment[SHARD_METRICS] = str(write)
        started = time.monotonic()
        try:
            code = runner(root, command, environment)
        finally:
            if write is not None:
                os.close(write)
            if asking is not None:
                asking.close()
        seconds = time.monotonic() - started
        print('   %s: %s leg: %s (%.1fs)' % (stage, leg, 'pass' if code == 0 else 'FAIL', seconds),
              flush=True)
        measured = {}
        if metrics is not None:
            with os.fdopen(metrics, 'rb') as handle:
                measured = shard_measurements(handle.read().decode('utf-8', 'replace'))
        if stage == MEASURED_STAGE and code == 0:
            refusal = owner_store_refusal(times, path)
            if refusal is None:
                record_time(times, digest, leg, seconds, run)
                if record_shard_claims(times, digest, leg, measured):
                    print('   %s: %s leg: %d shard measurement(s) recorded for the next gate\'s claims'
                          % (stage, leg, len(measured)), flush=True)
            else:
                print('   %s: %s leg time not recorded in the owner\'s store: %s' % (stage, leg, refusal),
                      flush=True)
        return code

    if leg == 'confined':
        return leg_run('confined', confined)
    inside = leg_run('confined', confined) if leg is None else 0
    print('   %s: UNCONFINED LEG - runs outside the confinement by owner decision (VELDO-0208, %s), '
          '%d entr%s: %s' % (stage, os.path.basename(str(path)), len(listed),
                              'y' if len(listed) == 1 else 'ies', ', '.join(listed)), flush=True)
    outside = leg_run('unconfined', unconfined)
    write_record(record, stage, digest, listed)
    return 0 if inside == 0 and outside == 0 else 1


def write_record(record, stage, digest, listed):
    data = (json.dumps({'stage': stage, 'declaration': digest, 'entries': listed},
                       sort_keys=True) + '\n').encode()
    fd = os.open(record, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        if os.write(fd, data) != len(data):
            raise OSError('short leg record append')
    finally:
        os.close(fd)


def mutation_leg(path=DECLARATION):
    """The mutation stage's unconfined leg from the authority's list: None when there is no list or
    it does not declare the mutation stage with exactly MUTATION_COMMAND (every case confined, as
    before), else {declaration, entries, suites}. An invalid list raises Invalid: nothing runs."""
    if not Path(path).exists():
        return None
    document, digest = load(path)
    if document['stages'].get('mutation') != MUTATION_COMMAND:
        return None
    return {'declaration': digest, 'entries': entries(document),
            'suites': sorted(e['suite'] for e in document['suites'])}


def declared(stage, command, path=DECLARATION):
    """0 when the list declares this stage with exactly this command, 1 when not, 2 when invalid."""
    try:
        document, _ = load(path)
    except Invalid:
        return 2
    return 0 if document['stages'].get(stage) == command else 1


def stamp(record, expected=None):
    """The stamp value, compact JSON. A record this cannot read is an error, never {}. With the
    stages a leg was expected in, a record that does not hold exactly those is an error too."""
    legs, digests = {}, set()
    if expected is not None and not Path(record).is_file():
        raise Invalid('the leg record is missing')
    try:
        text = Path(record).read_text() if Path(record).exists() else ''
        for line in text.splitlines():
            item = json.loads(line)
            legs[item['stage']] = list(item['entries'])
            digests.add(item['declaration'])
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise Invalid('unreadable leg record: %s' % error)
    if expected is not None and set(legs) != set(expected):
        raise Invalid('the leg record holds stages %s where %s were expected'
                      % (sorted(legs) or 'none', sorted(expected)))
    if not legs:
        return {}
    if len(digests) != 1:
        raise Invalid('the stages ran under different declarations')
    return {'declaration': digests.pop(), 'legs': legs}


# ---- THE LOAD-PROOF LEG (VELDO-0358, AC13) ----------------------------------------------------
#
# After the unit and integration stages and before the mutation stage, the gate runs every suite of
# the PROVEN SET once, each in its own process through the dispatcher's own selector, eight at a
# time, under the load of scripts/gate_load.py, and every CHANGED suite of that set repeatedly. Any
# failed or hung row is the gate's red and the mutation stage is not started. Nothing is run again
# because it failed, nothing is voided, and no reading of the host's speed is a verdict.
#
# THE PROVEN SET IS COMPUTED, never listed: a suite with no entry in the authority's wall-clock
# baseline (scripts/suites/wallclock_baseline.json, a protected file) for its own file or for any
# file of its opened-files record. The selector runs a suite with its measured prerequisite
# closure in one process, so a proven suite runs here when its whole closure is proven; until then
# it is named as waiting, and a suite that has not been converted cannot make this leg red.
#
# A SUITE IS CHANGED when its own file differs between the candidate and the authority, or a
# changed file is in the opened-files record of at most three suites (a fixture of its own). A
# changed file more suites open adds no repetition: the whole proven set already runs once. In a
# checkout that is its own authority nothing differs, as for the census.
#
# THE REPETITION COUNT is twenty, lowered to fit thirty minutes of loaded time at the leg's slots,
# from each suite's loaded time in the previous leg's record, never below five. The allowance
# decides how many runs are made and never a verdict; nothing here bounds how long the leg takes.
# A suite process is ended only after the process hang bound with no line on its output.
LOAD_SLOTS = 8
LOAD_REPETITIONS, LOAD_REPETITIONS_FLOOR = 20, 5
LOAD_ALLOWANCE_SECONDS = 1800
LOAD_OWN_FIXTURE_SUITES = 3
LOAD_BASELINE = 'scripts/suites/wallclock_baseline.json'
LOAD_OPENED = '.veldo/opened_files.json'
LOAD_SCHEMA = 'veldo.load-proof/v1'
SUITE_COMMAND = 'python3 scripts/selftest.py --suite %s'
RED_LINES = ('SELFTEST FAIL', 'SELFTEST HUNG', 'SELFTEST NOT RUN')
PARTIAL_LINE = re.compile(r'^selftest \(PARTIAL, \d+ of \d+ suites\): (\d+) passed, (\d+) failed in ([0-9.]+)s$')
PARTIAL_PASSED_EXIT = 2  # scripts/run_scope.py: a selector's run that failed no row


def load_generator():
    spec = importlib.util.spec_from_file_location('veldo_gate_load', HERE / 'gate_load.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _same(left, right):
    try:
        return left.stat().st_size == right.stat().st_size and left.read_bytes() == right.read_bytes()
    except OSError:
        return False


def load_inputs(root, baseline, opened):
    """(baselined files, opened-files record, suites in manifest order, closures) or Invalid."""
    try:
        document = json.loads(Path(baseline).read_text())
        files = {os.path.normpath(entry['file']) for entry in document['entries'] if entry.get('count', 1)}
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise Invalid('unreadable wall-clock baseline %s: %s' % (baseline, error))
    try:
        record = json.loads(Path(opened).read_text())
        if not isinstance(record, dict) or not all(
                isinstance(k, str) and isinstance(v, list) and all(isinstance(p, str) for p in v)
                for k, v in record.items()):
            raise ValueError('not suite name to a list of paths')
        record = {name: sorted({os.path.normpath(p) for p in paths}) for name, paths in record.items()}
        manifest = json.loads((Path(root) / 'scripts/suites/manifest.json').read_text())
        # The shared namespace is every suite's preamble and no suite the selector can name.
        suites = [(s['name'], 'scripts/suites/' + s['file']) for s in manifest['suites']
                  if s['file'] != manifest.get('shared')]
        closures = json.loads((Path(root) / 'scripts/suites/requires.json').read_text())['requires']
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise Invalid('unreadable load-proof input: %s' % error)
    for name, _ in suites:
        if not SUITE.match(name):
            raise Invalid('suite name %r is not a single safe name' % (name,))
    return files, record, suites, closures


def proven_set(baselined, record, suites, closures):
    """{suite: None when it runs in the leg, else why it does not}, in manifest order."""
    own = {}
    for name, file in suites:
        if name not in record:
            own[name] = 'no opened-files record'
            continue
        held = sorted(f for f in {file, *record[name]} if f in baselined)
        own[name] = 'baseline entry in %s' % held[0] if held else None
    result = {}
    for name, _ in suites:
        waiting = [other for other in closures.get(name) or [name] if own.get(other, 'not in the manifest')]
        result[name] = own[name] or ('proven, waiting for its prerequisite %s' % waiting[0] if waiting else None)
    return result


def changed_suites(root, authority, record, suites):
    """{suite: the changed file that makes it a changed suite}; nothing in its own authority."""
    root, authority = Path(root), Path(authority)
    if root.resolve() == authority.resolve():
        return {}
    files = dict(suites)
    users = {}
    for name, paths in record.items():
        for path in paths:
            users.setdefault(path, set()).add(name)
    changed = {}
    for name, file in suites:
        if not _same(root / file, authority / file):
            changed[name] = file
    for path, names in sorted(users.items()):
        if len(names) <= LOAD_OWN_FIXTURE_SUITES and path not in files.values() \
                and not _same(root / path, authority / path):
            for name in names:
                changed.setdefault(name, path)
    return {name: why for name, why in changed.items() if name in files}


def repetitions(seconds, slots):
    """How often each changed suite runs: twenty, lowered until the runs fit the allowance at the
    leg's slots (the longest run first, each on the slot that is free first), never below five.
    `seconds` is each changed suite's loaded time in the previous leg's record; a suite with none
    counts as nothing, since there is nothing to lower it by."""
    for count in range(LOAD_REPETITIONS, LOAD_REPETITIONS_FLOOR, -1):
        free = [0.0] * slots
        for run in sorted((s or 0.0 for s in seconds for _ in range(count)), reverse=True):
            free[free.index(min(free))] += run
        if max(free) <= LOAD_ALLOWANCE_SECONDS:
            return count
    return LOAD_REPETITIONS_FLOOR


def _load_file(times, slots):
    key = hashlib.sha256(('load-proof\n%s\n%d' % (HERE.parent, slots)).encode()).hexdigest()[:32]
    return Path(times) / (key + '.json')


def read_load(times, slots):
    """The previous leg's record for this authority and these slots: {set, peak, suites} or {}."""
    try:
        item = json.loads(_load_file(times, slots).read_text())
        if item.get('authority') != str(HERE.parent) or not isinstance(item.get('suites'), dict):
            return {}
        return item
    except (OSError, ValueError, AttributeError):
        return {}


def record_load(times, slots, digest, peak, seconds):
    """Keep what the next leg needs: this set's memory peak and each suite's loaded time."""
    try:
        Path(times).mkdir(mode=0o700, parents=True, exist_ok=True)
        previous = read_load(times, slots)
        suites = dict(previous.get('suites') or {})
        suites.update(seconds)
        item = dict(authority=str(HERE.parent), kind='load-proof', slots=slots, suites=suites,
                    set=digest if peak else previous.get('set'), peak=peak or previous.get('peak'))
        target = _load_file(times, slots)
        fd, pending = tempfile.mkstemp(prefix='.pending-', dir=str(target.parent))
        with os.fdopen(fd, 'w') as handle:
            json.dump(item, handle, sort_keys=True)
        os.replace(pending, target)
    except OSError as error:
        print('   load-proof: this leg\'s times were not recorded in %s (%s)' % (times, error), flush=True)


def judge(lines, code, hung):
    """(verdict, the red lines, the suite process's own loaded seconds) of one suite process. A
    process is green only on its own evidence: the selector's passing exit, its summary line with
    rows passed and none failed, and no failed, hung or not-run row line."""
    red = [line.strip() for line in lines if line.strip().startswith(RED_LINES)]
    summary = None
    for line in lines:
        summary = PARTIAL_LINE.match(line.strip()) or summary
    seconds = float(summary.group(3)) if summary else None
    if hung:
        return 'hung', red + ['no line on its output for the process hang bound'], seconds
    if summary is None:
        return 'FAIL', red + ['no summary line: the suite process ended with status %s' % code], seconds
    if red or int(summary.group(2)) or not int(summary.group(1)) or code != PARTIAL_PASSED_EXIT:
        return 'FAIL', red or ['%s passed, %s failed, exit status %s'
                               % (summary.group(1), summary.group(2), code)], seconds
    return 'pass', [], seconds


def suite_run(generator, hang, root, name, leg, env, fds=()):
    """One suite in its own process, inside the load, through the confinement its leg has. It is
    ended only when its output has been silent for the process hang bound (`hang` holds the two
    hang bounds of the design's section 6, as scripts/gate_load.py names them)."""
    command = SUITE_COMMAND % name
    if leg == 'unconfined':
        argv = ['bash', '-c', command]
        env = {k: v for k, v in env.items() if k not in AUTHORITY_ONLY}
    else:
        argv = [sys.executable, '-I', '-S', str(HERE / 'gate_candidate.py'), '--root', str(root), '--',
                'bash', '-c', command]
    process = subprocess.Popen(generator.wrap(argv), cwd=str(root), env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True,
                               pass_fds=fds)
    # The heavy child being awaited. Its progress is its output: the bound runs from its last line,
    # never from its start, so a suite that is slow under the load is never ended for it.
    child = dict(what='suite run: scripts/selftest.py --suite ' + name, output=process.stdout.fileno())
    text, hung = b'', False
    while True:
        if not select.select([child['output']], [], [], hang.PROCESS_HANG_SECONDS)[0]:
            hung = True
            print('   load-proof: %s: no line for %ds; ending it' % (child['what'], hang.PROCESS_HANG_SECONDS), flush=True)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            break
        data = os.read(child['output'], 65536)
        if not data:
            break
        text += data
    process.stdout.close()
    code = process.wait()
    lines = text.decode(errors='replace').splitlines()
    verdict, red, seconds = judge(lines, code, hung)
    return dict(suite=name, leg=leg, verdict=verdict, red=red, seconds=seconds, tail=lines[-30:])


def run_load_proof(root, record, opened=None, baseline=None, path=DECLARATION, times=LEG_TIMES,
                   slots=LOAD_SLOTS):
    """The leg. 0 when nothing in it is red (or nothing is proven yet), 1 otherwise."""
    root, authority = Path(root).resolve(), HERE.parent
    baseline = Path(baseline) if baseline else authority / LOAD_BASELINE
    opened = Path(opened) if opened else authority / LOAD_OPENED
    out = dict(schema=LOAD_SCHEMA, state='ran', verdict='pass', error=None, slots=slots)

    def finish(code):
        Path(record).write_text(json.dumps(out, sort_keys=True) + '\n')
        return code

    def nothing(state, why):
        print('   load-proof: %s; no suite is proven yet and nothing ran' % why, flush=True)
        out.update(state=state)
        return finish(0)

    if not baseline.exists():
        return nothing('no_baseline', 'the authority has no wall-clock baseline (%s)' % LOAD_BASELINE)
    if not opened.exists():
        return nothing('no_record', 'there is no opened-files record (%s)' % opened.name)
    try:
        baselined, opened_files, suites, closures = load_inputs(root, baseline, opened)
        declaration = load(path) if Path(path).exists() else None
    except Invalid as error:
        print('   load-proof: %s; the leg is RED' % error, flush=True)
        out.update(verdict='FAIL', error='invalid_input')
        return finish(1)
    state = proven_set(baselined, opened_files, suites, closures)
    runs_in = [name for name, _ in suites if state[name] is None]
    waiting = [name for name, _ in suites if state[name] and state[name].startswith('proven, waiting')]
    changed = {n: why for n, why in changed_suites(root, authority, opened_files, suites).items() if n in runs_in}
    out.update(proven=len(runs_in) + len(waiting), waiting=len(waiting), suites_run=len(runs_in))
    print('   load-proof: %d of %d suites are proven (no baseline entry in the suite or in a file it opens)'
          '%s; %d run' % (len(runs_in) + len(waiting), len(suites),
                          ', %d of them waiting for a prerequisite suite' % len(waiting) if waiting else '',
                          len(runs_in)), flush=True)
    if not runs_in:
        out.update(state='empty')
        return finish(0)
    load = load_generator()
    previous = read_load(times, slots)
    count = repetitions([(previous.get('suites') or {}).get(name) for name in changed], slots) if changed else 1
    for name in sorted(changed):
        print('   load-proof: %s is changed (%s): %d runs' % (name, changed[name], count), flush=True)
    listed = {e['suite']: e.get('rows') for e in declaration[0]['suites']} if declaration else {}
    tasks = []
    for name in runs_in:
        legs = [None] if not declaration else ['unconfined'] if name in listed and listed[name] is None \
            else ['confined', 'unconfined'] if name in listed else ['confined']
        tasks += [(name, leg) for leg in legs for _ in range(count if name in changed else 1)]
    digest = hashlib.sha256('\n'.join(runs_in).encode()).hexdigest()
    high = int(previous['peak'] * load.MEMORY_HIGH_PERCENT / 100) \
        if previous.get('set') == digest and isinstance(previous.get('peak'), int) else None
    write_dirs, beside = [tempfile.gettempdir()], None
    try:
        # A directory on the checkout's file system and outside the checkout: nothing a writer does
        # can show in the candidate's tree.
        beside = tempfile.mkdtemp(prefix='.veldo-load-', dir=str(root.parent))
        write_dirs.append(beside)
    except OSError as error:
        print('   load-proof: no writer on the checkout\'s file system (%s)' % error, flush=True)
    scope = os.environ.get('VELDO_GATE_SCOPE') or None
    results, lock, red_suites = [], threading.Lock(), set()
    # The marker a nested launcher is handed, as for the functional legs; an authority with no
    # launcher of its own (a fixture's) hands nothing.
    fds = _launcher_fds() if (HERE / 'agent_sandbox.py').is_file() else ()
    try:
        try:
            generator = load.Generator(slots, write_dirs, scope=scope, memory_high=high)
        except load.Refused as error:
            print('   load-proof: no cgroup for the leg (%s): no memory level' % error, flush=True)
            generator = load.Generator(slots, write_dirs)
        with generator:
            canary = subprocess.run(generator.wrap([sys.executable, '-I', '-S', str(HERE / 'gate_load.py'),
                                                    '--canary']), stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL).returncode
            out['canary'] = {0: 'green', 1: 'red'}.get(canary, 'error %s' % canary)
            print('   load-proof: the canary under this load: %s (a test synchronized by a sleep is red here; '
                  'data, no verdict)' % out['canary'], flush=True)

            def worker():
                while True:
                    with lock:
                        if not tasks:
                            return
                        name, leg = tasks.pop(0)
                        if name in red_suites:
                            continue  # a red suite's remaining repetitions add nothing to its verdict
                    env = _env(leg, entries(declaration[0]), declaration[1]) if leg else _env()
                    try:
                        outcome = suite_run(generator, load.HANG, root, name, leg, env, fds)  # one run is the verdict
                    except (OSError, ValueError) as error:  # a suite that could not be started is red, by name
                        outcome = dict(suite=name, leg=leg, verdict='FAIL', seconds=None, tail=[],
                                       red=['the suite process could not be started: %s' % error])
                    with lock:
                        results.append(outcome)
                        if outcome['verdict'] != 'pass':
                            red_suites.add(name)

            threads = [threading.Thread(target=worker) for _ in range(slots)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        out['load'] = generator.record
    finally:
        if beside:
            try:
                os.rmdir(beside)
            except OSError:
                pass
    per_suite, seconds = {}, {}
    for outcome in results:
        item = per_suite.setdefault(outcome['suite'], dict(runs=0, verdict='pass', seconds=None))
        item['runs'] += 1
        if outcome['seconds'] is not None:
            item['seconds'] = max(item['seconds'] or 0.0, outcome['seconds'])
        if outcome['verdict'] != 'pass':
            item['verdict'] = outcome['verdict']
            print('   load-proof: %s: %s%s' % (outcome['suite'], 'HUNG' if outcome['verdict'] == 'hung' else 'FAIL',
                                               ' (%s leg)' % outcome['leg'] if outcome['leg'] else ''), flush=True)
            for line in outcome['red'] or outcome['tail']:
                print('      ' + line, flush=True)
    for name in runs_in:
        item = per_suite.get(name)
        if item and item['verdict'] == 'pass':
            print('   load-proof: %s: pass, %d run%s%s' % (
                name, item['runs'], '' if item['runs'] == 1 else 's',
                ', %.1fs loaded' % item['seconds'] if item['seconds'] is not None else ''), flush=True)
            if item['seconds'] is not None:
                seconds[name] = item['seconds']
    for line in load.summary(out['load']):
        print('   load-proof: ' + line, flush=True)
    red = sorted(name for name, item in per_suite.items() if item['verdict'] != 'pass')
    out.update(suites=per_suite, red=red, repetitions=count if changed else None, changed=sorted(changed))
    if red or len(per_suite) != len(runs_in):
        out.update(verdict='FAIL', error='red_rows')
    if not out['load']['applied']:
        out.update(verdict='FAIL', error=load.NOT_APPLIED)
    if Path(times) != LEG_TIMES or baseline == authority / LOAD_BASELINE:
        peak = out['load']['memory'].get('peak') if out['verdict'] == 'pass' else None
        record_load(times, slots, digest, peak, seconds)
    print('   load-proof: %s' % ('pass' if out['verdict'] == 'pass' else 'RED (%s)' % out['error']), flush=True)
    return finish(0 if out['verdict'] == 'pass' else 1)


def load_stamp(record, wall=None):
    """The stamp's "load" value: the load record of this gate's leg, in counts. A record this
    cannot read is an error, never absent: the leg was expected."""
    try:
        document = json.loads(Path(record).read_text())
        if document.get('schema') != LOAD_SCHEMA:
            raise ValueError('not a load-proof record')
        value = {key: document[key] for key in ('state', 'verdict', 'error', 'slots', 'proven', 'waiting',
                                                'suites_run', 'canary', 'red', 'changed', 'repetitions')
                 if key in document}
        if 'suites' in document:
            value['runs'] = sum(item['runs'] for item in document['suites'].values())
            value['suite_seconds'] = {name: item['seconds'] for name, item in sorted(document['suites'].items())}
        if 'load' in document:
            load_record = document['load']
            value['load'] = {
                'applied': load_record['applied'], 'cpus': len(load_record['cpus']),
                'spinners': len(load_record['spinners']),
                'spinners_alive': sum(1 for s in load_record['spinners'] if s['alive']),
                'spinner_cpu_seconds': round(sum(s['cpu_seconds'] for s in load_record['spinners']), 1),
                'writers': len(load_record['writers']),
                'writers_alive': sum(1 for w in load_record['writers'] if w['alive']),
                'writer_bytes': sum(w['bytes'] for w in load_record['writers']),
                'memory': {k: v for k, v in load_record['memory'].items() if k != 'unreadable'},
                'probe': load_record['probe']}
        if wall is not None:
            value['wall_seconds'] = wall
        return value
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise Invalid('unreadable load-proof record: %s' % error)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--root')
    parser.add_argument('--stage')
    parser.add_argument('--record')
    parser.add_argument('--leg', choices=('confined', 'unconfined'))
    parser.add_argument('--prior-times', type=Path)
    parser.add_argument('--stamp')
    parser.add_argument('--expect')
    parser.add_argument('--declared', action='store_true')
    parser.add_argument('--load-proof', action='store_true')
    parser.add_argument('--opened')
    parser.add_argument('--load-stamp')
    parser.add_argument('--wall', type=int)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.stamp is not None:
        try:
            expected = None if args.expect is None else [s for s in args.expect.split(',') if s]
            print(json.dumps(stamp(args.stamp, expected), sort_keys=True, separators=(',', ':')))
        except Invalid as error:
            print('null')
            print('gate legs: %s; the gate is RED' % error, file=sys.stderr)
            return 1
        return 0
    if args.load_stamp is not None:
        try:
            print(json.dumps(load_stamp(args.load_stamp, args.wall), sort_keys=True, separators=(',', ':')))
        except Invalid as error:
            print('null')
            print('gate legs: %s; the gate is RED' % error, file=sys.stderr)
            return 1
        return 0
    if args.load_proof:
        if not (args.root and args.record):
            parser.error('--load-proof needs --root and --record')
        return run_load_proof(args.root, args.record, opened=args.opened)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if args.declared:
        if not args.stage or len(command) != 1:
            parser.error('--declared needs --stage and exactly one command string')
        return declared(args.stage, command[0])
    if not (args.root and args.stage and args.record) or len(command) != 1:
        parser.error('--root, --stage, --record and exactly one command string are required')
    prior = json.loads(args.prior_times.read_text()) if args.prior_times else None
    return run_stage(args.root, args.stage, command[0], args.record, leg=args.leg, prior=prior)


if __name__ == '__main__':
    sys.exit(main())
