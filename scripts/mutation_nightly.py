#!/usr/bin/env python3
"""VELDO-0267: the nightly full mutation sweep on the trunk.

Every registered case runs once a night on the trunk tip, fresh, with its baseline traced; a gate
then runs only the cases its candidate's changes select (scripts/mutation_selection.py).

INSTALL (the owner's host configuration, one crontab line; the runner names no host itself):

  15 1 * * * XDG_RUNTIME_DIR=/run/user/$(id -u) /usr/bin/python3 -I -S <authority checkout>/scripts/mutation_nightly.py >> $HOME/.local/state/veldo/mutation-nightly/cron.log 2>&1

The notifier is named in <state directory>/nightly.json as {"notifier": ["<command>", "<arg>", ...]};
the message is appended as the last argument. Without one the runner prints that nobody was told.

WHAT ONE RUN DOES
  1. resolves the trunk tip (the rule's nightly.trunk branch of the authority's repository);
  2. takes the host lock every heavy run serializes on (scripts/gate_host.json, VELDO-0220) with a
     blocking exclusive flock, waiting for a running gate rather than overlapping it, and moves itself
     into its own user scope with the gate's memory limit;
  3. checks the trunk tip out cleanly into <state>/checkout (a detached linked worktree, the same
     path every night so measured case times carry over) and runs that checkout's own
     check_gate_mutations.py --full: every case fresh, every baseline traced;
  4. records veldo.mutation-sweep/v1 in <state>/sweeps/<run id>.json: run id, trunk commit, start,
     end, verdict, every surviving mutant and driver error, the wall, CPU and peak memory line, and
     the coverage map with its digest. Only a green sweep publishes <state>/coverage.json;
  5. tells the owner once when the sweep is red, naming the commit and each failing case, and once
     when it has not finished by the configured local deadline (07:00).

Standard library only.
"""
import datetime
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import resource
import secrets
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent


def load(path):
    spec = importlib.util.spec_from_file_location('nightly_' + Path(path).stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


selection = load(HERE / 'mutation_selection.py')


def say(text):
    print('nightly: ' + text, flush=True)


def take_lock(path):
    """Block until the exclusive lock is ours; (descriptor, seconds waited)."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o664)
    started = time.monotonic()
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd, time.monotonic() - started


def deadline_after(started, text, local=time.localtime):
    """The first local `HH:MM` strictly after `started` (epoch seconds)."""
    hour, minute = (int(part) for part in text.split(':'))
    moment = datetime.datetime.fromtimestamp(started)
    target = moment.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= moment:
        target += datetime.timedelta(days=1)
    return target.timestamp()


def failures_of(receipt):
    """Every surviving mutant and driver error the stage recorded, as {case, error, detail}."""
    found, seen = [], set()
    for item in receipt.get('invalid_results', []) if isinstance(receipt, dict) else []:
        if not isinstance(item, dict):
            continue
        case = item.get('case')
        identity = case.get('identity') if isinstance(case, dict) else item.get('name')
        entry = {'case': str(identity or 'stage'), 'error': str(item.get('error', 'driver_error')),
                 'detail': str(item.get('detail', ''))[:500]}
        key = (entry['case'], entry['error'])
        if key not in seen:
            seen.add(key)
            found.append(entry)
    if not found and (not isinstance(receipt, dict) or receipt.get('status') != 'passed'):
        error = receipt.get('error', 'driver_error') if isinstance(receipt, dict) else 'no_receipt'
        detail = receipt.get('detail', '') if isinstance(receipt, dict) else 'the stage left no receipt'
        found.append({'case': 'stage:' + str(error), 'error': str(error), 'detail': str(detail)[:500]})
    return found


def coverage_map(receipt, run_id, commit, finished_at, case_inputs):
    """The sealed veldo.mutation-coverage/v1 map of a green sweep."""
    traces = receipt.get('coverage_traces') or {}
    cases = {}
    for result in receipt['results']:
        case = result['case']
        files = traces.get(case['identity'])
        cases[case['identity']] = {'definition': selection.definition_digest(case),
                                   'files': sorted(files) if isinstance(files, list) else None}
    return selection.seal({'schema': selection.COVERAGE_SCHEMA, 'run_id': run_id, 'trunk_commit': commit,
                           'finished_at': finished_at, 'toolchains': selection.toolchain_digests(case_inputs),
                           'cases': cases})


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name('.' + path.name + '.%d' % os.getpid())
    pending.write_text(json.dumps(value, sort_keys=True, indent=1) + '\n')
    os.replace(pending, path)


class Scope:
    """The runner's own user scope (gate_host.make_scope) and its CPU and memory counters."""
    def __init__(self, host, config):
        self.host, self.config, self.state = host, config, {}

    def enter(self):
        self.host.make_scope(self.config, state=self.state)

    def usage(self):
        base = self.host.CGROUP_ROOT / self.state['cgroup'].lstrip('/')
        cpu = memory = None
        try:
            for line in (base / 'cpu.stat').read_text().splitlines():
                if line.startswith('usage_usec '):
                    cpu = int(line.split()[1]) / 1e6
            memory = int((base / 'memory.peak').read_text().split()[0])
        except (OSError, ValueError, IndexError):
            pass
        return cpu, memory


def children_usage():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime, usage.ru_maxrss * 1024


class Runner:
    def __init__(self, *, root, state, trunk, lock, notifier, deadline='07:00', sweep=None, scope=None,
                 clock=time.time):
        self.root, self.state, self.trunk, self.lock = Path(root), Path(state), trunk, lock
        self.notifier, self.deadline, self.clock = list(notifier or []), deadline, clock
        self.sweep = sweep or self.run_stage
        self.scope = scope
        self.notified = []

    def git(self, *arguments, cwd=None):
        _git_process = selection.git_boundary()
        result = _git_process.run(['git', '-C', str(cwd or self.root), *arguments], capture_output=True,
                                  text=True, timeout=600)
        if result.returncode:
            raise RuntimeError('git %s: %s' % (' '.join(arguments), result.stderr.strip()[:300]))
        return result.stdout.strip()

    def notify(self, message):
        self.notified.append(message)
        if not self.notifier:
            say('no notifier is configured; nobody was told: ' + message)
            return
        try:
            subprocess.run([*self.notifier, message], timeout=120, check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError) as error:
            say('the notifier failed (%s): %s' % (error, message))

    def checkout(self, commit):
        directory = self.state / 'checkout'
        self.git('worktree', 'prune')
        if directory.exists():
            self.git('worktree', 'remove', '--force', str(directory))
        self.git('worktree', 'add', '--detach', '--force', str(directory), commit)
        return directory

    def release_checkout(self, directory):
        try:
            self.git('worktree', 'remove', '--force', str(directory))
        except RuntimeError as error:
            say('the checkout %s was not removed (%s)' % (directory, error))

    def run_stage(self, checkout, receipt_path):
        """The checkout's own gate stage in full mode. The receipt is the stage's own record."""
        command = [sys.executable, '-I', '-S', str(checkout / 'scripts/check_gate_mutations.py'),
                   '--root', str(checkout), '--receipt', str(receipt_path), '--full']
        environment = {k: v for k, v in os.environ.items() if not k.startswith('VELDO_')}
        subprocess.run(command, cwd=checkout, env=environment, stdout=sys.stdout, stderr=sys.stderr, check=False)
        return json.loads(Path(receipt_path).read_text())

    def run(self):
        started = self.clock()
        run_id = 'nightly-%s-%s' % (time.strftime('%Y%m%dT%H%M%SZ', time.gmtime(started)), secrets.token_hex(3))
        say('start %s at %s' % (run_id, selection.utc(started)))
        commit = self.git('rev-parse', '--verify', 'refs/heads/%s^{commit}' % self.trunk)
        late = threading.Timer(max(0.0, deadline_after(started, self.deadline) - self.clock()),
                               lambda: self.notify('Veldo nightly mutation sweep %s on %s has not finished by %s'
                                                   % (run_id, commit[:12], self.deadline)))
        late.daemon = True
        late.start()
        say('waiting for the host lock %s' % self.lock)
        try:
            fd, waited = take_lock(self.lock)
        except BaseException:
            late.cancel()
            raise
        say('took the host lock %s after %.1fs' % (self.lock, waited))
        try:
            if self.scope is not None:
                self.scope.enter()
            locked_at = self.clock()
            directory = self.checkout(commit)
            try:
                receipt_path = self.state / ('receipt-%s.json' % run_id)
                try:
                    receipt = self.sweep(directory, receipt_path)
                except (OSError, ValueError) as error:
                    receipt = {'status': 'failed', 'error': 'driver_error', 'detail': str(error)}
                try:
                    case_inputs = json.loads((directory / 'scripts/mutation_case_inputs.json').read_text())
                except (OSError, ValueError):
                    case_inputs = None
            finally:
                self.release_checkout(directory)
            finished = self.clock()
            green = isinstance(receipt, dict) and receipt.get('status') == 'passed'
            if self.scope is not None:
                cpu, memory = self.scope.usage()
            else:
                cpu, memory = children_usage()
            record = {'schema': selection.SWEEP_SCHEMA, 'run_id': run_id, 'trunk_commit': commit,
                      'started_at': selection.utc(started), 'locked_at': selection.utc(locked_at),
                      'lock_wait_seconds': round(waited, 3), 'finished_at': selection.utc(finished),
                      'finished_epoch': finished,
                      'verdict': 'green' if green else 'red',
                      'failures': [] if green else failures_of(receipt),
                      'host': {'wall_seconds': round(finished - started, 3), 'cpu_seconds': cpu,
                               'peak_memory_bytes': memory},
                      'stage': {k: receipt.get(k) for k in ('registered', 'executed', 'reused', 'rejected',
                                                             'worker_invocations', 'elapsed', 'error')}
                      if isinstance(receipt, dict) else None,
                      'coverage': None}
            if green:
                try:
                    published = coverage_map(receipt, run_id, commit, record['finished_at'], case_inputs)
                except (KeyError, TypeError, selection.Invalid) as error:
                    published = None
                    record.update(verdict='red', failures=[{'case': 'stage:coverage_unavailable',
                                                            'error': 'coverage_unavailable', 'detail': str(error)}])
                if published is not None:
                    write_json(self.state / 'coverage' / (run_id + '.json'), published)
                    write_json(self.state / 'coverage.json', published)
                    record['coverage'] = {'digest': published['digest'],
                                          'path': str(self.state / 'coverage' / (run_id + '.json'))}
            late.cancel()
            write_json(self.state / 'sweeps' / (run_id + '.json'), record)
            try:
                Path(receipt_path).unlink()
            except OSError:
                pass
            if record['verdict'] == 'red':
                self.notify('Veldo nightly mutation sweep %s is RED on %s: %s' % (
                    run_id, commit[:12], ', '.join(f['case'] for f in record['failures'])))
            if isinstance(receipt, dict) and 'registered' in receipt and 'elapsed' in receipt:
                say_line = ('mutations: {status} registered={registered} executed={executed} reused={reused} '
                            'rejected={rejected} workers={worker_invocations} elapsed={elapsed:.3f}s')
                try:
                    print(say_line.format(**receipt), flush=True)
                except (KeyError, ValueError, TypeError):
                    pass
            say('end %s at %s: %s, trunk %s, wall %.0fs, cpu %s s, peak memory %s bytes' % (
                run_id, record['finished_at'], record['verdict'], commit[:12], finished - started, cpu, memory))
            return record
        finally:
            late.cancel()
            os.close(fd)


def configured(rule_path=None):
    rule = selection.load_rule(rule_path or selection.RULE)
    nightly = rule['nightly']
    state = selection.state_directory(rule)
    notifier = nightly['notifier']
    try:
        local = json.loads((state / 'nightly.json').read_text())
        if isinstance(local.get('notifier'), list) and all(isinstance(a, str) for a in local['notifier']):
            notifier = local['notifier']
    except (OSError, ValueError, AttributeError):
        pass
    return rule, state, notifier


def main(argv):
    if argv:
        print('usage: mutation_nightly.py   (no arguments; see the header for the crontab line)', file=sys.stderr)
        return 2
    try:
        rule, state, notifier = configured()
    except selection.Invalid as error:
        say('refused: %s' % error)
        return 1
    host = load(HERE / 'gate_host.py')
    try:
        config = host.load()
    except host.Refused as error:
        say('refused: the gate host configuration is invalid (%s)' % error)
        return 1
    root = HERE.parent
    scope = Scope(host, config['scope']) if config['scope'] is not None else None
    runner = Runner(root=root, state=state, trunk=rule['nightly']['trunk'], lock=config['lock'],
                    notifier=notifier, deadline=rule['nightly'].get('deadline_local', '07:00'), scope=scope)
    try:
        record = runner.run()
    except (OSError, RuntimeError, host.Refused) as error:
        say('not run: %s' % error)
        runner.notify('Veldo nightly mutation sweep did not run: %s' % error)
        return 1
    return 0 if record['verdict'] == 'green' else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
