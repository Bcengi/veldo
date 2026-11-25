#!/usr/bin/env python3
"""VELDO-0366: exact distributed coverage; transport never supplies verdict authority."""
import collections
import hashlib
import hmac
import importlib.util
import json
import math
import os
from pathlib import Path
import secrets
import signal
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
SCHEMA = 'veldo.mutation-shard/v1'


class Refused(Exception):
    pass


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def seal(key, body):
    return dict(body=body, mac=hmac.new(key, canonical(body), hashlib.sha256).hexdigest())


def open_receipt(key, envelope):
    if set(envelope) != {'body', 'mac'} or not hmac.compare_digest(
            hmac.new(key, canonical(envelope['body']), hashlib.sha256).hexdigest(), envelope['mac']):
        raise Refused('forged receipt')
    return envelope['body']


def exact(expected, actual, what):
    if len(actual) != len(set(actual)) or collections.Counter(actual) != collections.Counter(list(expected)):
        raise Refused('missing, duplicate or foreign ' + what)


def binding(gate, root, common):
    files = gate.read_inputs(root, common)
    head = gate.git(root, common, 'rev-parse', 'HEAD')
    if gate.git(root, common, 'status', '--porcelain', '--untracked-files=all'):
        raise Refused('distributed inputs must be committed and clean')
    return dict(head=head, input_digest=gate.digest(dict(files=gate.file_identity(files), head=head)))


def qualification(request, host, capacity, checks):
    return dict(schema=SCHEMA, kind='qualification', request=request, host=host,
                capacity=capacity, checks=checks, runtime_digest=digest(checks))


def admit(request, host, document):
    required = load('qualify_mutation_host').REQUIRED
    if (document.get('schema') != SCHEMA or document.get('kind') != 'qualification'
            or document.get('request') != request or document.get('host') != host):
        raise Refused('qualification binding mismatch')
    checks = document.get('checks', {})
    if set(checks) != set(required) or not all(checks[n].get('passed') is True for n in required):
        raise Refused('unqualified host ' + host)
    if checks['namespaces'].get('no_network') is not True:
        raise Refused('unqualified remote network boundary')
    if document.get('runtime_digest') != digest(checks):
        raise Refused('qualification runtime mismatch')
    capacity = document['capacity']
    if set(capacity) != {'cpu', 'memory', 'manager'} or any(
            type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in capacity.values()):
        raise Refused('invalid host capacity')
    return document


def runtime_matches(qualified, evidence):
    return digest(qualified['checks']['toolchain']['evidence']) == digest(evidence)


def plan(gate, cases, hosts, history, leg, remote_suites):
    """LPT over whole control groups; history changes placement, never a verdict or timeout."""
    exact([c['identity'] for c in cases], [c['identity'] for c in cases], 'inventory')
    groups = collections.defaultdict(list)
    for case in cases:
        groups[gate.control_group(case)].append(case)
    costs = {}
    for group, members in groups.items():
        samples = [history.get(c['identity'], {}).get('seconds') for c in members]
        measured = [v for v in samples if type(v) in (int, float) and math.isfinite(v) and v > 0]
        # Two shared controls plus every member. Missing history uses conservative admission cost.
        estimate = max(measured, default=gate.WORKER_CEILING)
        costs[group] = sum(v if type(v) in (int, float) and math.isfinite(v) and v > 0
                           else estimate for v in samples) + 2 * estimate
    assignments = {h: [] for h in hosts}
    work = dict.fromkeys(hosts, 0.0)
    for group in sorted(groups, key=lambda g: (-costs[g], g)):
        members = groups[group]
        eligible = ['local']
        if all(not gate.in_leg(leg, c) and c['suite'] in remote_suites for c in members):
            eligible = list(hosts)
        host = min(eligible, key=lambda h: ((work[h] + costs[group]) / hosts[h]['cpu'], h))
        assignments[host].extend(members)
        work[host] += costs[group]
    return assignments, costs


def assignment(request, host, cases, qualification_receipt):
    return dict(schema=SCHEMA, request=request, host=host, cases=cases,
                qualification_digest=digest(qualification_receipt))


def validate_assignment(gate, root, common, task, qualified):
    if (task.get('schema') != SCHEMA or task.get('request') != qualified['request']
            or task.get('host') != qualified['host']
            or task.get('qualification_digest') != digest(qualified)):
        raise Refused('assignment binding mismatch')
    current = binding(gate, root, common)
    if any(task['request'][k] != v for k, v in current.items()):
        raise Refused('assignment input mismatch')
    registry = gate.inventory(root, common)
    if digest(registry) != task['request']['inventory_digest']:
        raise Refused('assignment registry mismatch')
    known = {c['identity']: c for c in registry}
    ids = [c['identity'] for c in task['cases']]
    exact(ids, ids, 'assignment')
    if any(known.get(c['identity']) != c for c in task['cases']):
        raise Refused('assignment definition mismatch')
    selected_groups = {gate.control_group(c) for c in task['cases']}
    if any(c['identity'] not in ids for c in registry if gate.control_group(c) in selected_groups):
        raise Refused('split control group')


def result_body(task, qualified, stage, cleaned):
    return dict(schema=SCHEMA, kind='result', assignment_digest=digest(task),
                request=task['request'], host=task['host'], qualification_digest=digest(qualified),
                runtime_digest=qualified['runtime_digest'], cleaned=cleaned, stage=stage)


def accept(gate, task, qualified, body):
    if task['host'] != 'local':
        admit(task['request'], task['host'], qualified)
    if (body.get('schema') != SCHEMA or body.get('kind') != 'result'
            or body.get('request') != task['request'] or body.get('host') != task['host']
            or body.get('assignment_digest') != digest(task)
            or body.get('qualification_digest') != digest(qualified)
            or body.get('runtime_digest') != qualified['runtime_digest']):
        raise Refused('receipt input/session/assignment mismatch')
    stage = body['stage']
    if (body.get('cleaned') is not True or stage.get('status') != 'passed'
            or stage.get('surviving_workers') != 0 or stage.get('invalid_results')
            or stage.get('reused') != 0 or stage.get('force_fresh') is not True
            or stage.get('input_digest') != task['request']['input_digest']):
        raise Refused('failed or unclean shard')
    if task['host'] != 'local' and stage.get('no_network') is not True:
        raise Refused('remote worker network boundary absent')
    expected = {c['identity']: c for c in task['cases']}
    exact(expected, [r['case']['identity'] for r in stage['results']], 'results')
    exact(expected, [r['identity'] for r in stage['case_receipts']], 'case receipts')
    if any(r.get('validated') is not True or r.get('source') != 'fresh' for r in stage['case_receipts']):
        raise Refused('pending case receipt')
    if any(stage.get(k) != len(expected) for k in ('registered', 'executed', 'rejected')):
        raise Refused('shard count mismatch')
    if any(o.get('error') or o.get('scratch_removed') is not True for o in stage['worker_outcomes']):
        raise Refused('worker cleanup failure')
    for record in stage['results']:
        gate.validate_result(record, expected[record['case']['identity']])
    return stage


def aggregate(gate, cases, tasks, qualifications, envelopes, keys, request):
    exact(tasks, list(envelopes), 'shards')
    expected = [c['identity'] for c in cases]
    exact(expected, [c['identity'] for task in tasks.values() for c in task['cases']], 'assignments')
    registered = {c['identity']: c for c in cases}
    if any(registered.get(c['identity']) != c for task in tasks.values() for c in task['cases']):
        raise Refused('foreign case definition')
    stages = []
    for host, task in tasks.items():
        if task['request'] != request:
            raise Refused('foreign assignment')
        stages.append(accept(gate, task, qualifications[host], open_receipt(keys[host], envelopes[host])))
    results = [r for stage in stages for r in stage['results']]
    exact(expected, [r['case']['identity'] for r in results], 'aggregate results')
    return dict(schema='veldo.mutation-stage/v1', scope='full', status='passed',
                input_digest=request['input_digest'], distributed=True, request=request,
                results=results, case_receipts=[r for s in stages for r in s['case_receipts']],
                registered=len(cases), executed=len(cases), rejected=len(cases), reused=0,
                force_fresh=request.get('force_fresh', False), invalid_results=[], surviving_workers=0,
                worker_outcomes=[o for s in stages for o in s['worker_outcomes']],
                worker_invocations=sum(s['worker_invocations'] for s in stages),
                elapsed=max((s['elapsed'] for s in stages), default=0),
                elapsed_basis='maximum shard execution; gate scheduler measures total stage wall',
                drivers={d: dict(registered=sum(c['driver'] == d for c in cases),
                                  executed=sum(c['driver'] == d for c in cases), reused=0)
                         for d in gate.DRIVERS},
                shards=envelopes, assignments=tasks, qualifications=qualifications)


def coordinate(gate, root, common, leg, transport=None):
    """Only the existing full gate may opt in. Fake transports exercise this same aggregation."""
    transport = transport or load('mutation_transport')
    partial = dict(schema='veldo.mutation-stage/v1', scope='full', status='failed', distributed=True,
                   registered=0, executed=0, reused=0, rejected=0, worker_invocations=0, elapsed=0,
                   results=[], invalid_results=[], shards={}, assignments={})
    nodes, envelopes, tasks, quals, keys = {}, {}, {}, {}, {}
    previous = {}
    result = partial
    try:
        host_module = load('gate_host')
        scheduler = load('gate_schedule')
        if host_module.inside(host_module.load()) is None or scheduler.CHANNEL not in os.environ:
            raise Refused('distributed mutation requires the owning gate lock and ledger')
        config = json.loads((ROOT / 'scripts/mutation_hosts.json').read_text())
        if config['schema'] != 'veldo.mutation-hosts/v1':
            raise Refused('unknown hosts configuration')
        source = binding(gate, root, common)
        if binding(gate, ROOT, gate.common_directory(ROOT)) != source:
            raise Refused('remote source differs from the gate authority')
        cases = gate.inventory(root, common)
        partial['registered'] = len(cases)
        request = dict(source, session=secrets.token_hex(32), inventory_digest=digest(cases),
                       force_fresh=load('mutation_reuse').truthy(os.environ.get('VELDO_GATE_FORCE_FRESH', '0')),
                       collect_all=os.environ.get('VELDO_GATE_COLLECT_ALL') == '1')
        graph = json.loads((ROOT / 'scripts/gate_graph.json').read_text())
        capacity = scheduler.capacities(graph, os.environ[host_module.SCOPE_ENV],
                                         ROOT / 'scripts/suites/manifest.json')
        capacities = dict(local=capacity)
        def cancelled(signum, frame):
            raise Refused('coordinator cancelled')
        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            previous[signum] = signal.signal(signum, cancelled)
        for entry in config['hosts']:
            name = entry['name']
            if name == 'local' or name in nodes:
                raise Refused('duplicate host')
            key = keys[name] = secrets.token_bytes(32)
            node = nodes[name] = transport.SSHNode(root, entry, request, key)
            quals[name] = admit(request, name, open_receipt(key, node.qualify()))
            capacities[name] = quals[name]['capacity']
        if not nodes:
            raise Refused('no remote hosts configured')
        assigned, costs = plan(gate, cases, capacities, gate.order_history(), leg, config['remote_suites'])
        # The local authority already belongs to the gate's qualified execution boundary.
        # Its receipt is not used to qualify a remote host.
        quals['local'] = dict(schema=SCHEMA, kind='local-gate', request=request, host='local',
                             capacity=capacity, runtime_digest=digest(dict(local=source)))
        keys['local'] = secrets.token_bytes(32)
        nodes['local'] = transport.LocalNode(root, request, keys['local'])
        for name in list(nodes):
            if not assigned[name]:
                nodes[name].close()
                del nodes[name]
                continue
            tasks[name] = assignment(request, name, assigned[name], quals[name])
            nodes[name].dispatch(tasks[name], quals[name])
        partial['assignments'] = tasks
        first_error = None
        for name, envelope in transport.completed(nodes):
            if name not in tasks or name in envelopes:
                raise Refused('duplicate or foreign shard receipt')
            envelopes[name] = envelope
            partial['shards'] = dict(envelopes)
            try:
                accept(gate, tasks[name], quals[name], open_receipt(keys[name], envelope))
            except Exception as error:
                first_error = first_error or error
                if os.environ.get('VELDO_GATE_COLLECT_ALL') != '1':
                    raise first_error
        if first_error is not None:
            raise first_error
        if binding(gate, root, common) != source:
            raise Refused('inputs changed during distributed stage')
        result = aggregate(gate, cases, tasks, quals, envelopes, keys, request)
        result['group_costs'] = costs
        local_stage = envelopes.get('local', {}).get('body', {}).get('stage', {})
        if 'unconfined' in local_stage:
            result['unconfined'] = local_stage['unconfined']
        return result
    except Exception as error:
        partial.update(error='distributed_refused', detail=str(error))
        return partial
    finally:
        cleanup_errors = []
        for node in nodes.values():
            try:
                node.close()
                if getattr(node, 'partial', None):
                    try:
                        result.setdefault('cancelled_shards', []).append(json.loads(node.partial))
                    except (ValueError, TypeError):
                        result.setdefault('cancelled_shard_errors', []).append('incomplete cancellation receipt')
            except Exception as error:
                cleanup_errors.append(str(error))
        if cleanup_errors:
            result.update(status='failed', cleanup_errors=cleanup_errors)
            result.setdefault('error', 'distributed_cleanup_failed')
        for signum, handler in previous.items():
            signal.signal(signum, handler)
