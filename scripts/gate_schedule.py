#!/usr/bin/env python3
"""Authority DAG execution and one resource ledger (VELDO-0216).

The graph and capacities never come from the candidate. No graph means the shell
keeps its serial loop. Recorded authority estimates seed the first run; fresh
anonymous-memory observations replace those cache-inclusive starting estimates. The inherited socket
is for trusted coordinators, never for their candidate children. Future shard and
case dispatchers claim measured needs on that socket in addition to local admission.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import selectors
import socket
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
GRAPH = HERE / 'gate_graph.json'
CHANNEL = 'VELDO_GATE_LEDGER_FD'
NAME = re.compile(r'^[a-z][a-z0-9_]*(?:\.(?:confined|unconfined))?$')


class Refused(ValueError):
    pass


def load_module(name):
    spec = importlib.util.spec_from_file_location('schedule_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def number(value, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0 and (not positive or value > 0)


def required_nodes(catalog, legs):
    result = {}
    for stage, command in catalog.items():
        if not isinstance(stage, str) or not NAME.fullmatch(stage) or '.' in stage \
                or not isinstance(command, str) or not command.strip():
            raise Refused('invalid catalog item')
        split = legs and legs['stages'].get(stage) == command and stage != 'mutation'
        for leg in ('confined', 'unconfined') if split else (None,):
            result[stage + ('.' + leg if leg else '')] = (stage, leg)
    return result


def read_graph(catalog, declaration=None, path=GRAPH):
    try:
        raw = Path(path).read_bytes()
        graph = json.loads(raw)
        if not isinstance(graph, dict) or set(graph) != {'schema', 'nodes', 'reserve', 'mutation_floor'} \
                or graph['schema'] != 'veldo.gate-graph/v1':
            raise Refused('invalid graph schema')
        nodes = graph['nodes']
        required = required_nodes(catalog, declaration)
        if not isinstance(nodes, dict):
            raise Refused('graph nodes must be an object')
        if set(nodes) != set(required):
            raise Refused('graph node set differs from required catalog: missing=%s unknown=%s' %
                          (sorted(set(required) - set(nodes)), sorted(set(nodes) - set(required))))
        for name, node in nodes.items():
            fields = {'depends_on', 'writes_candidate', 'manager', 'ports'}
            if not isinstance(node, dict) or not fields <= set(node) \
                    or set(node) - fields - {'host_lock', 'estimate'}:
                raise Refused('invalid node ' + name)
            deps = node['depends_on']
            if not isinstance(deps, list) or any(not isinstance(d, str) or d not in nodes for d in deps) \
                    or len(set(deps)) != len(deps) or node['writes_candidate'] is not False:
                raise Refused('invalid dependencies or candidate writer: ' + name)
            validate_claim(dict(cpu=0, memory=0, manager=node['manager'], ports=node['ports'],
                                host_lock=node.get('host_lock', 'none')))
            if 'estimate' in node:
                startup_estimate(node['estimate'])
        done = set()
        while len(done) < len(nodes):
            ready = {n for n, v in nodes.items() if n not in done and set(v['depends_on']) <= done}
            if not ready:
                raise Refused('graph cycle')
            done.update(ready)
        for key in ('reserve', 'mutation_floor'):
            if not isinstance(graph[key], dict) or set(graph[key]) != {'cpu', 'memory'} \
                    or not all(number(v) for v in graph[key].values()):
                raise Refused('invalid ' + key)
        return graph, 'sha256:' + hashlib.sha256(raw).hexdigest(), required
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise Refused('invalid graph: ' + str(error)) from error


def validate_claim(claim):
    fields = {'cpu', 'memory', 'manager', 'ports'}
    if not isinstance(claim, dict) or not fields <= set(claim) or set(claim) - fields - {'host_lock'} \
            or not number(claim['cpu']) or not number(claim['memory']) \
            or claim['manager'] not in ('none', 'shared', 'exclusive') \
            or claim.get('host_lock', 'none') not in ('none', 'shared', 'exclusive') \
            or not isinstance(claim['ports'], list) \
            or any(type(p) is not int or not 1 <= p <= 65535 for p in claim['ports']) \
            or len(set(claim['ports'])) != len(claim['ports']):
        raise Refused('invalid_resource_requirement: malformed claim')


class Ledger:
    def __init__(self, capacity, floor=None):
        if set(capacity) != {'cpu', 'memory', 'manager'} or not all(number(v, True) for v in capacity.values()) \
                or type(capacity['manager']) is not int:
            raise Refused('invalid_resource_requirement: capacity')
        self.capacity = capacity
        self.floor = floor or {'cpu': 0, 'memory': 0}
        if any(self.floor[r] > capacity[r] for r in self.floor):
            raise Refused('invalid_resource_requirement: mutation floor exceeds capacity')
        self.held, self.events = {}, []
        self.refusals = set()
        self.peak = dict.fromkeys(capacity, 0)
        self.mutation_pending = bool(any(self.floor.values()))
        self.mutation_claimants = set()
        self.mutation_root = None

    def totals(self):
        return {r: sum(c[r] for c in self.held.values()) for r in self.capacity}

    def demand(self, claim):
        validate_claim(claim)
        c = dict(claim)
        c['manager'] = self.capacity['manager'] if claim['manager'] == 'exclusive' else int(claim['manager'] == 'shared')
        if any(c[r] > self.capacity[r] for r in self.capacity):
            raise Refused('invalid_resource_requirement: claim exceeds capacity')
        return c

    def event(self, action, name, resource, claim=None):
        if action == 'refuse':
            key = (name, resource)
            if key in self.refusals:
                return
            self.refusals.add(key)
        else:
            self.refusals.clear()
        totals = self.totals()
        self.events.append(dict(at=time.monotonic(), action=action, claimant=name, resource=resource,
                                claim=claim, granted=totals))
        print('ledger %s %s resource=%s cpu=%g memory=%g manager=%g' %
              (action, name, resource, totals['cpu'], totals['memory'], totals['manager']), flush=True)
        for r in self.peak:
            self.peak[r] = max(self.peak[r], totals[r])

    def acquire(self, name, claim, mutation=False):
        if name in self.held:
            raise Refused('invalid_resource_requirement: duplicate claimant ' + name)
        c, totals = self.demand(claim), self.totals()
        for r in self.capacity:
            limit = self.capacity[r]
            # Cold nodes use all capacity, but cannot steal a pending mutation floor.
            if r in self.floor and self.mutation_pending and not mutation:
                held_for_mutation = sum(self.held[n][r] for n in self.mutation_claimants)
                limit -= max(0, self.floor[r] - held_for_mutation)
            if totals[r] + c[r] > limit:
                self.event('refuse', name, r, claim)
                return False
        lock = c.get('host_lock', 'none')
        if lock != 'none' and any(h.get('host_lock', 'none') != 'none' and
                'exclusive' in (lock, h.get('host_lock')) for h in self.held.values()):
            self.event('refuse', name, 'host_lock', claim)
            return False
        occupied = set(p for held in self.held.values() for p in held['ports'])
        if occupied.intersection(c['ports']):
            self.event('refuse', name, 'ports', claim)
            return False
        self.held[name] = c
        if mutation:
            self.mutation_claimants.add(name)
            if self.mutation_root is None:
                self.mutation_root = name
        self.event('grant', name, 'cpu,memory,manager,host_lock,ports', claim)
        return True

    def release(self, name):
        if name not in self.held:
            raise Refused('unknown claimant ' + name)
        del self.held[name]
        self.mutation_claimants.discard(name)
        if name == self.mutation_root:
            self.mutation_pending = False
        self.event('release', name, 'cpu,memory,manager,host_lock,ports')


class Client:
    """Nonblocking admission reply over an inherited authority-only socket.

    A refusal means poll completions and retry; it never authorizes a launch. The
    coordinator retains its own claim. A shard dispatcher must use coordinator-only
    measurements for that claim, then claim every running shard separately.
    """
    def __init__(self, fd=None):
        self.socket = socket.socket(fileno=os.dup(int(os.environ[CHANNEL]) if fd is None else fd))
        self.file = self.socket.makefile('rwb', buffering=0)

    def request(self, operation, name, claim=None):
        self.file.write((json.dumps(dict(operation=operation, name=name, claim=claim)) + '\n').encode())
        raw = self.file.readline(65537)
        if not raw or len(raw) > 65536:
            raise Refused('ledger channel closed or oversized reply')
        answer = json.loads(raw)
        if 'error' in answer:
            raise Refused(answer['error'])
        return answer['granted']

    def acquire(self, name, cpu, memory, manager='none', ports=(), host_lock='none'):
        return self.request('acquire', name, dict(cpu=cpu, memory=memory, manager=manager,
                                                 ports=list(ports), host_lock=host_lock))

    def release(self, name):
        return self.request('release', name)

    def close(self):
        self.file.close()
        self.socket.close()


def startup_estimate(estimate):
    """Historical total cgroup memory is an estimate above the observed anon use.

    It is never labelled an anonymous-memory measurement. Round CPU upward to a
    tenth of a core and memory upward to a GiB; fresh observations take precedence.
    """
    if not isinstance(estimate, dict) or set(estimate) != {
            'source', 'wall_seconds', 'cpu_seconds', 'peak_cgroup_memory_bytes'} \
            or not isinstance(estimate['source'], str) or not estimate['source'].strip() \
            or not all(number(estimate[k], True) for k in
                       ('wall_seconds', 'cpu_seconds', 'peak_cgroup_memory_bytes')):
        raise Refused('invalid authority startup estimate')
    return dict(cpu=max(1, math.ceil(estimate['cpu_seconds'] / estimate['wall_seconds'] * 10) / 10),
                memory=math.ceil(estimate['peak_cgroup_memory_bytes'] / 2**30) * 2**30)


def node_claim(node, measured, capacity):
    if measured:
        demand = dict(cpu=measured['cpu_rate'], memory=measured['peak_anon_bytes'])
        source = 'authority anonymous-memory measurement'
    elif 'estimate' in node:
        demand = startup_estimate(node['estimate'])
        source = 'recorded startup estimate: ' + node['estimate']['source']
    else:
        demand = dict(cpu=capacity['cpu'], memory=capacity['memory'])
        source = 'no authority estimate; reserving full gate capacity'
    return dict(demand, manager=node['manager'], ports=node['ports'],
                host_lock=node.get('host_lock', 'none')), source


def capacities(graph, scope, manifest, cgroup_root=Path('/sys/fs/cgroup')):
    """Kernel capacity, bounded by every ancestor, minus the declared reserve."""
    scope = Path(scope)
    base = cgroup_root / str(scope).lstrip('/')
    own = Path('/proc/self/cgroup').read_text().split('::', 1)[1].strip()
    if not scope.is_absolute() or '..' in scope.parts:
        raise Refused('invalid gate scope')
    if not (own == str(scope) or own.startswith(str(scope).rstrip('/') + '/')):
        raise Refused('gate scope is not an ancestor of this scheduler')
    cpu, memory = float(len(os.sched_getaffinity(0))), float('inf')
    for path in [base, *base.parents]:
        if path != cgroup_root and cgroup_root not in path.parents:
            break
        quota, period = (path / 'cpu.max').read_text().split() if (path / 'cpu.max').exists() else ('max', '100000')
        if quota != 'max':
            cpu = min(cpu, int(quota) / int(period))
        limit = (path / 'memory.max').read_text().strip() if (path / 'memory.max').exists() else 'max'
        if limit != 'max':
            memory = min(memory, int(limit))
    manager = json.loads(Path(manifest).read_text())['resource_capacities']['systemd_user_manager']
    return dict(cpu=cpu - graph['reserve']['cpu'], memory=memory - graph['reserve']['memory'], manager=manager)


class Meter:
    """A delegated cgroup per node; anonymous peak sampled every scheduler poll.

    CPU is the kernel cumulative counter. Samples include descendants across sessions.
    A live descendant at completion refuses the node; claims remain held until cleanup.
    """
    def __init__(self, scope, name):
        self.path = Path('/sys/fs/cgroup') / scope.lstrip('/') / ('node-' + str(os.getpid()) + '-' + name)
        self.path.mkdir()
        self.peak = 0
        self.finished = None

    def command(self, argv):
        return [sys.executable, '-I', '-S', str(HERE / 'gate_schedule.py'), '--enter-node', str(self.path), '--', *argv]

    def sample(self):
        memory = dict(line.split() for line in (self.path / 'memory.stat').read_text().splitlines())
        self.peak = max(self.peak, int(memory['anon']))
        cpu = dict(line.split() for line in (self.path / 'cpu.stat').read_text().splitlines())
        return dict(cpu_seconds=int(cpu['usage_usec']) / 1e6, peak_anon_bytes=self.peak,
                    metrics_source='cgroup-v2-anon-sampled-50ms')

    def finish(self):
        if self.finished is not None:
            return self.finished
        result = self.sample()
        populated = 'populated 1' in (self.path / 'cgroup.events').read_text()
        if populated:
            (self.path / 'cgroup.kill').write_text('1')
            while 'populated 1' in (self.path / 'cgroup.events').read_text():
                time.sleep(.05)
        for path in sorted(self.path.rglob('*'), reverse=True):
            if path.is_dir():
                path.rmdir()
        self.path.rmdir()
        result['live_descendants'] = populated
        self.finished = result
        return result


def input_guard(root):
    # Exactly the mutation stage's closure and comparison, extended across all nodes.
    mutation = load_module('check_gate_mutations')
    common = os.environ.get('VELDO_EXPECTED_GIT_COMMON')
    if not common:
        raise Refused('candidate Git boundary needs VELDO_EXPECTED_GIT_COMMON')
    files = mutation.read_inputs(root, common)
    head = mutation.git(root, common, 'rev-parse', 'HEAD')
    return lambda: mutation.inputs_unchanged(root, common, files, head)


def command_for(root, stage, leg, command, record, receipt, listing, prior_times=None):
    if stage == 'mutation':
        return [sys.executable, '-I', '-S', str(HERE / 'check_gate_mutations.py'), '--root', str(root),
                '--receipt', str(receipt), '--legs-record', str(record)]
    if listing:
        argv = [sys.executable, '-I', '-S', str(HERE / 'gate_legs.py'), '--root', str(root),
                '--stage', stage, '--record', str(record)]
        if leg:
            argv += ['--leg', leg]
        if stage == 'integration' and prior_times:
            argv += ['--prior-times', str(prior_times)]
        return argv + ['--', command]
    return [sys.executable, '-I', '-S', str(HERE / 'gate_candidate.py'), '--root', str(root), '--', 'bash', '-c', command]


def run(catalog, root, directory, record, receipt, *, graph_path=GRAPH, declaration_path=None,
        capacity=None, measurement_store=None, meter_factory=None, guard_factory=input_guard, serial=False):
    """Run the real graph. Explicit injected boundaries are for fixture authorities only.

    CLI exposes no graph, capacity, measurement-store, runner or guard override.
    """
    directory, root = Path(directory), Path(root)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    legs = load_module('gate_legs')
    listing = Path(declaration_path) if declaration_path else HERE / 'gate_unconfined.json'
    declaration = legs.load(listing)[0] if listing.exists() else None
    graph, digest, required = read_graph(catalog, declaration, graph_path)
    scope = os.environ.get('VELDO_GATE_SCOPE', '')
    capacity = capacity if capacity is not None else capacities(graph, scope, HERE / 'suites/manifest.json')
    ledger = Ledger(capacity, graph['mutation_floor'])
    if serial:
        print('scheduler fixture serial control', flush=True)
    store = legs.LEG_TIMES if measurement_store is None else measurement_store
    key = hashlib.sha256((digest + json.dumps(catalog, sort_keys=True) +
                         (listing.read_text() if declaration else '') +
                         Path(__file__).read_text() + (HERE / 'gate_legs.py').read_text()).encode()).hexdigest()
    prior_times = directory / 'prior-unit-times.json'
    prior = {}
    if declaration:
        declaration_digest = legs.load(listing)[1]
        for leg in ('confined', 'unconfined'):
            value = legs.measurement(store, declaration_digest, leg, str(record))
            if value:
                prior[leg] = dict(value, fresh='an earlier gate run')
    prior_times.write_text(json.dumps(prior))
    claims = {}
    for name, node in graph['nodes'].items():
        measured = legs.read_resources(store, key, name)
        claim, source = node_claim(node, measured, capacity)
        ledger.demand(claim)  # Refuse impossible requests before any launch.
        print('node %s: %s' % (name, source), flush=True)
        claims[name] = claim
    if 'mutation' not in required:
        ledger.mutation_pending = False
    unchanged = guard_factory(root)
    pending = list(required)
    # Start mutation first so its floor cannot deadlock an unmeasured first run.
    pending.sort(key=lambda n: n != 'mutation')
    active, results = {}, {}
    waited_for = {name: set() for name in required}
    selector = selectors.DefaultSelector()
    started = time.monotonic()
    next_print = 0
    ordered = list(required)
    failed_tree = False
    try:
        while pending or active:
            for name in list(pending):
                node = graph['nodes'][name]
                if not set(node['depends_on']) <= results.keys():
                    continue
                if serial and active:
                    waited_for[name].update(active)
                    continue
                if not ledger.acquire(name, claims[name], mutation=name == 'mutation'):
                    waited_for[name].update(active)
                    continue
                stage, leg = required[name]
                log = open(directory / (name + '.log'), 'w')
                parent, child = socket.socketpair()
                parent.setblocking(False)
                meter = None
                try:
                    meter = meter_factory(name) if meter_factory else Meter(scope, name)
                    argv = command_for(root, stage, leg, catalog[stage], record, receipt, declaration, prior_times)
                    env = {k: v for k, v in os.environ.items() if k not in
                           (legs.LEG, legs.ENTRIES, legs.DIGEST, legs.UNIT_SECONDS, CHANNEL)}
                    env[CHANNEL] = str(child.fileno())
                    env['PYTHONDONTWRITEBYTECODE'] = '1'
                    env['VELDO_GATE_GRAPH_DIGEST'] = digest
                    node_started = time.monotonic()
                    proc = subprocess.Popen(meter.command(argv), cwd=root, env=env,
                                            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                            pass_fds=(child.fileno(), *legs._launcher_fds()))
                except BaseException:
                    parent.close()
                    log.close()
                    if meter:
                        meter.finish()
                    ledger.release(name)
                    raise
                finally:
                    child.close()
                active[name] = dict(proc=proc, log=log, meter=meter, socket=parent,
                                    buffer=b'', started=node_started, children=set(), error=None)
                selector.register(parent, selectors.EVENT_READ, name)
                pending.remove(name)
                print('node %s start %.6f' % (name, active[name]['started'] - started), flush=True)
            if pending and not active:
                raise Refused('invalid_resource_requirement: no runnable claim fits')
            for event, _mask in selector.select(.05 if active else 0):
                name = event.data
                item = active[name]
                try:
                    data = item['socket'].recv(65536)
                    if not data:
                        selector.unregister(item['socket'])
                        continue
                    item['buffer'] += data
                    if len(item['buffer']) > 65536:
                        raise Refused('oversized ledger request')
                    while b'\n' in item['buffer']:
                        line, item['buffer'] = item['buffer'].split(b'\n', 1)
                        request = json.loads(line)
                        child_name = request['name']
                        if not isinstance(child_name, str) or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,200}', child_name):
                            raise Refused('invalid ledger claimant')
                        claimant = name + '/' + child_name
                        if request['operation'] == 'acquire':
                            granted = ledger.acquire(claimant, request['claim'], mutation=name == 'mutation')
                            if granted:
                                item['children'].add(claimant)
                        elif request['operation'] == 'release' and claimant in item['children']:
                            ledger.release(claimant)
                            item['children'].remove(claimant)
                            granted = True
                        else:
                            raise Refused('invalid ledger operation or foreign release')
                        item['socket'].sendall((json.dumps({'granted': granted}) + '\n').encode())
                except (ValueError, KeyError, TypeError, OSError) as error:
                    item['error'] = 'ledger_protocol: ' + str(error)
                    try:
                        item['socket'].sendall((json.dumps({'error': str(error)}) + '\n').encode())
                    except OSError:
                        pass
            for name, item in list(active.items()):
                item['meter'].sample()
                code = item['proc'].poll()
                if code is None:
                    continue
                end = time.monotonic()
                metrics = item['meter'].finish()
                tree_ok = unchanged()
                if not tree_ok:
                    failed_tree = True
                    # Every overlapping node is suspect; never silently blame an innocent
                    # last finisher and let the writing node pass.
                    for other in active.values():
                        other['error'] = 'candidate_tree_changed'
                error = item['error'] or ('live_descendants' if metrics.get('live_descendants') else None)
                if item['children']:
                    error = error or 'unreleased_ledger_claim'
                    for claimant in item['children']:
                        ledger.release(claimant)
                elapsed = end - item['started']
                result = dict(start=item['started'] - started, end=end - started, wall_seconds=elapsed,
                              verdict='pass' if code == 0 and error is None else 'FAIL',
                              returncode=code, error=error, **metrics)
                results[name] = result
                if result['verdict'] == 'pass' and measurement_store is None:
                    try:
                        legs.record_resources(store, key, name, elapsed, metrics)
                    except OSError as error:
                        print('node %s: resource measurement not stored: %s' % (name, error), flush=True)
                item['log'].close()
                if item['socket'] in selector.get_map():
                    selector.unregister(item['socket'])
                item['socket'].close()
                ledger.release(name)
                del active[name]
                print('node %s end %.6f %s %.3fs%s' % (name, result['end'], result['verdict'], elapsed,
                      ' ' + error if error else ''), flush=True)
            while next_print < len(ordered) and ordered[next_print] in results:
                name = ordered[next_print]
                print('== ' + name, flush=True)
                print((directory / (name + '.log')).read_text(errors='replace'), end='', flush=True)
                next_print += 1
        if not unchanged():
            failed_tree = True
        if failed_tree:
            for result in results.values():
                result.update(verdict='FAIL', error=result['error'] or 'candidate_tree_changed_during_graph')
        stages = {stage: 'pass' if all(results[n]['verdict'] == 'pass' for n, pair in required.items()
                                     if pair[0] == stage) else 'FAIL' for stage in catalog}
        for name, result in results.items():
            result['admission_dependencies'] = sorted(other for other in waited_for[name]
                if results[other]['end'] <= result['start'])
        chains = {}
        def chain(n):
            if n not in chains:
                chains[n] = results[n]['wall_seconds'] + max((chain(d) for d in set(graph['nodes'][n]['depends_on']) | set(results[n]['admission_dependencies'])), default=0)
            return chains[n]
        critical = max(required, key=chain) if required else None
        return dict(schema='veldo.gate-schedule/v1', graph=digest, stages=stages, nodes=results,
                    checks_run=len(stages), inputs_unchanged=not failed_tree,
                    wall_seconds=time.monotonic() - started, critical_path_seconds=chain(critical) if critical else 0,
                    critical_path_end=critical, capacities=capacity, peak_granted=ledger.peak,
                    ledger=ledger.events, claims=claims)
    finally:
        # On exceptional exit, own only these nodes. Never signal another gate or touch its lock.
        cleanup_errors = []
        for name, item in active.items():
            try:
                item['proc'].kill()
                item['meter'].finish()
            except Exception as error:
                cleanup_errors.append('%s: %s' % (name, error))
            finally:
                item['proc'].wait()
                item['log'].close()
                item['socket'].close()
        selector.close()
        if cleanup_errors:
            raise Refused('node cleanup failed: ' + '; '.join(cleanup_errors))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ['--enter-node']:
        path = Path(argv[1])
        (path / 'cgroup.procs').write_text(str(os.getpid()))
        os.execvp(argv[3], argv[3:])
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--stage', nargs=2, action='append', default=[])
    args = parser.parse_args(argv)
    try:
        if len(dict(args.stage)) != len(args.stage):
            raise Refused('duplicate catalog stage')
        result = run(dict(args.stage), args.root, args.directory, args.record, args.receipt)
        (args.directory / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
        (args.directory / 'graph-field').write_text(',"graph":' + json.dumps(result['graph']))
        for stage, verdict in result['stages'].items():
            (args.directory / (stage + '.status')).write_text(verdict)
        if args.output is not None:
            fd, pending = tempfile.mkstemp(prefix='.gate-schedule-', dir=args.output.parent)
            try:
                with os.fdopen(fd, 'w') as handle:
                    json.dump(result, handle, indent=2)
                    handle.write('\n')
                os.replace(pending, args.output)
            finally:
                if os.path.exists(pending):
                    os.unlink(pending)
        return int(any(v != 'pass' for v in result['stages'].values()))
    except (OSError, ValueError, KeyError) as error:
        print('GATE: RED (scheduler: %s); no successful graph receipt' % error, flush=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
