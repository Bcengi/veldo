#!/usr/bin/env python3
"""VELDO-0262 AC1: the recorded exchange corpus, its generator, its replay and the resume crossing.

  python3 proof/VELDO-0262/corpus.py record --python <langgraph interpreter>   record on the LangGraph runner
  python3 proof/VELDO-0262/corpus.py replay [--root REPOSITORY]                replay on the step runner
  python3 proof/VELDO-0262/corpus.py twice [--root REPOSITORY]                 replay twice, compare bytes
  python3 proof/VELDO-0262/corpus.py cross --python <langgraph interpreter>    resumes cross both ways

Every exchange is one veldo.graph/v1 request, answered by a runner built exactly as production builds it:
a workflow revision runner (the runner with the step kinds and one revision spliced before its entry
point), the project pipeline runner (control_graph_pm.py spliced), the runtime qualification runner
(control_runtime.QUALIFICATION spliced) and a probe runner (PROBES below: the node failures, the step
bound, the notes merge, fan-out refusals). A worker child, started once per interpreter, compiles each
runner source once and runs every exchange in a fresh module namespace through the runner's own
serve() over the canonical request bytes, so the answer bytes are what the runner writes.

The generated set is seeded (SEED): GENERATED revisions over every step kind the runner registers,
check rules over every field type, fan-outs of width 2 to 8, bounded loops back through a check, and
failing nodes (an owner wait with no answer, a check with a field unsupplied or of the wrong type, a port
leading to a kind the runner does not run), each driven to its end by a seeded script of supplied
results, with suspend, cancel and malformed resumes along the way.

The corpus is gzip JSON lines under corpus/, each file under 1 MB: every record is {runner, request,
answer} with the answer's runtime label replaced by the placeholder RUNNER unless it says nothing ran.
Replay compares canonical JSON and stops at the first difference, naming the exchange and the field.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CORPUS = HERE / 'corpus'
SEED = 262
GENERATED = 520
GUARD = "\nif __name__ == '__main__':\n"
NO_RUNTIME = {'name': 'none', 'version': ''}
PLACEHOLDER = {'name': 'RUNNER', 'version': 'RUNNER'}
CHUNK = 900
WORKER = r'''
import io, json, sys
codes = {}
for line in sys.stdin:
    message = json.loads(line)
    if 'source' in message:
        codes[message['key']] = compile(message['source'], message['key'], 'exec')
        continue
    namespace = {'__name__': 'veldo_corpus_runner', '__builtins__': __builtins__}
    exec(codes[message['key']], namespace)
    workflows = namespace['workflows']() if 'workflows' in namespace else namespace['WORKFLOWS']
    out = io.StringIO()
    namespace['serve'](workflows, io.StringIO(message['request']), out)
    sys.stdout.write(json.dumps({'answer': out.getvalue()}) + '\n')
    sys.stdout.flush()
'''
PROBES = r'''
# VELDO-0262 corpus probe workflows: every node failure, the step bound and the notes merge.
def _p_loop(view):
    return {'next': 'n'}


def _p_chain_a(view):
    return {'next': 'b', 'notes': {'k': 'a', 'a': view['step']}}


def _p_chain_b(view):
    return {'next': 'c', 'notes': {'k': 'b'}, 'proposals': [{'type': 'priority', 'proposal_id': 'p-b',
                                                             'subject': 'unit-1', 'priority': view['step']}]}


def _p_chain_c(view):
    if view['supplied_results']:
        return {'next': None, 'notes': {'k': 'c'}, 'proposals': [{'type': 'priority', 'proposal_id': 'p-c',
                                                                  'subject': 'unit-1', 'priority': 2}]}
    return {'next': 'a', 'suspend': True, 'notes': {'k': 'c-wait', 'seen': view['notes'].get('k')}}


def _p_raise(view):
    raise KeyError('probe')


def _p_list(view):
    return [1]


def _p_untyped(view):
    return {'next': None, 'admitted': True}


def _p_unnamed(view):
    return {'failure': {'code': 'made_up', 'detail': 'x'}}


def _p_named(view):
    return {'failure': {'code': 'missing_evidence', 'detail': 'probe needs ' + 'x' * 600}}


def _p_suspend_proposal(view):
    return {'next': 'end', 'suspend': True, 'proposals': [{'type': 'priority', 'proposal_id': 'p',
                                                           'subject': 'u', 'priority': 1}]}


def _p_suspend_nowhere(view):
    return {'next': None, 'suspend': True}


def _p_nowhere(view):
    return {'next': 'missing'}


def _p_empty(view):
    return {'next': None}


def _p_tuple(view):
    return {'next': None, 'proposals': [{'type': 'priority', 'proposal_id': 'p', 'subject': 'u', 'priority': (1,)}]}


def _p_fan_wide(view):
    return {'next': {'b%d' % i: 'end' for i in range(9)}, 'suspend': True, 'notes': {'join': 'end'}}


def _p_fan_unsuspended(view):
    return {'next': {'x': 'end', 'y': 'end'}, 'notes': {'join': 'end'}}


def _p_fan(view):
    return {'next': {'x': 'bx', 'y': 'by', 'z': 'bz'}, 'suspend': True, 'notes': {'join': 'end'}}


def _p_bx(view):
    return {'next': 'end', 'suspend': True, 'notes': {'last': ['bx', 'done', 'end']}}


def _p_by(view):
    if view['supplied_results']:
        return {'next': 'end', 'suspend': True, 'notes': {'last': ['by', 'done', 'end']}}
    return {'next': 'by', 'suspend': True, 'notes': {'last': None}}


def _p_bz(view):
    return {'failure': {'code': 'invalid_input', 'detail': 'bz failed'}} if view['snapshot']['id'] == 'fail' else (
        {'next': 'end', 'suspend': True, 'notes': {'last': ['bz', 'done', 'end'], 'decision': {'b': view['branch']}}})


def _p_end(view):
    return {'next': None, 'proposals': [{'type': 'completion', 'proposal_id': 'p-end', 'subject': 'u',
                                         'evidence': ['sha256:' + '1' * 64]}]}


for _p_name, _p_node in (('loop', _p_loop), ('raise', _p_raise), ('list', _p_list), ('untyped', _p_untyped),
                         ('unnamed', _p_unnamed), ('named', _p_named), ('suspend-proposal', _p_suspend_proposal),
                         ('suspend-nowhere', _p_suspend_nowhere), ('nowhere', _p_nowhere), ('empty', _p_empty),
                         ('tuple', _p_tuple), ('fan-wide', _p_fan_wide), ('fan-unsuspended', _p_fan_unsuspended)):
    WORKFLOWS['probe-' + _p_name] = {'version': 1, 'entry': 'n', 'nodes': {'n': _p_node, 'end': _p_end}}
WORKFLOWS['probe-chain'] = {'version': 1, 'entry': 'a', 'nodes': {'a': _p_chain_a, 'b': _p_chain_b, 'c': _p_chain_c}}
WORKFLOWS['probe-fan'] = {'version': 1, 'entry': 'f', 'nodes': {'f': _p_fan, 'bx': _p_bx, 'by': _p_by, 'bz': _p_bz,
                                                                  'end': _p_end}}
'''


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def sha(text):
    return 'sha256:' + hashlib.sha256(text.encode()).hexdigest()


def _load(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Runners:
    """Runner sources as production builds them, for one of the two runners."""

    def __init__(self, root, kind):
        self.veldo, self.kind = Path(root) / '.veldo', kind

    def base(self):
        return (self.veldo / ('control_graph_langgraph.py' if self.kind == 'langgraph' else 'control_graph_steps.py')).read_text()

    def splice(self, block):
        source = self.base()
        assert source.count(GUARD) == 1
        return source.replace(GUARD, '\n' + block + '\n' + GUARD, 1)

    def source(self, key):
        what, _, rest = key.partition(':')
        if what == 'revision':
            text, version = json.loads(rest)
            if self.kind == 'langgraph':
                steps = (self.veldo / 'control_workflow_langgraph.py').read_text()
                return self.splice(steps + '\nveldo_register_workflow(%r, %d)\n' % (text, version))
            steps = (self.veldo / 'control_workflow_steps.py').read_text()
            return self.splice(steps + '\nVELDO_DEFINITION = (%r, %d)\n' % (text, version))
        if what == 'pm':
            return self.splice((self.veldo / 'control_graph_pm.py').read_text())
        if what == 'qualification':
            text = (self.veldo / 'control_runtime.py').read_text()
            return self.splice(text.split("QUALIFICATION = r'''", 1)[1].split("'''", 1)[0])
        if what == 'probe':
            return self.splice(PROBES)
        raise ValueError(key)


class Worker:
    def __init__(self, python, runners, flags):
        self.runners, self.known = runners, set()
        self.proc = subprocess.Popen([python] + flags + ['-c', WORKER], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     text=True, cwd='/', env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})

    def ask(self, key, request):
        if key not in self.known:
            self.proc.stdin.write(json.dumps({'key': key, 'source': self.runners.source(key)}) + '\n')
            self.known.add(key)
        self.proc.stdin.write(json.dumps({'key': key, 'request': canonical(request)}) + '\n')
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError('the corpus worker ended')
        return json.loads(json.loads(line)['answer'])

    def close(self):
        self.proc.stdin.close()
        self.proc.wait()


def labelled(answer):
    """The answer with its runtime label replaced by the placeholder, unless it says nothing ran."""
    body = dict(answer)
    if body.get('runtime') != NO_RUNTIME:
        body['runtime'] = PLACEHOLDER
    return body


# -- the generated set ---------------------------------------------------------------------------------

FIELD_VALUES = {'number': [0, 3, 7, 12, 40], 'yes_no': [True, False], 'choice': ['red', 'green', 'blue'],
                'text': ['alpha', 'beta release', 'gamma']}
COMPARE = {'text': ('is', 'is not', 'contains', 'is one of'),
           'number': ('is', 'is not', 'less than', 'at most', 'more than', 'at least', 'is one of'),
           'yes_no': ('is', 'is not'), 'choice': ('is', 'is not', 'is one of')}
WAITING = ('grooming', 'owner_wait', 'assignment', 'check')


def _condition(rng, fields):
    name = rng.choice(sorted(fields))
    kind = fields[name]['type']
    comparison = rng.choice(COMPARE[kind])
    if comparison == 'is one of':
        value = rng.sample(FIELD_VALUES[kind], min(2, len(FIELD_VALUES[kind])))
    elif comparison == 'contains':
        value = rng.choice(['a', 'beta', 'z'])
    else:
        value = rng.choice(FIELD_VALUES[kind])
    return {'field': name, 'comparison': comparison, 'value': value}


def generate(rng, index):
    """One seeded revision: a main path of waiting nodes, perhaps a fan-out block with a join, perhaps a
    bounded loop back through a check, and a terminal result handling node (or a dead end)."""
    fields = {}
    for number in range(rng.randint(1, 3)):
        kind = rng.choice(sorted(FIELD_TYPES))
        fields['f%d' % number] = dict({'type': kind, 'source': {'subject': 'f%d' % number}},
                                      **({'choices': FIELD_VALUES['choice']} if kind == 'choice' else {}))
    nodes, transitions = {}, []

    def node(name, kind, config=None):
        nodes[name] = {'kind': kind, 'config': config or {}}
        return name

    def route(source, port, target):
        transitions.append({'id': 't%d' % len(transitions), 'from': source, 'port': port, 'to': target})
        return transitions[-1]['id']

    def check_config():
        return {'branches': [{'name': 'r%d' % b, 'conditions': [_condition(rng, fields) for _ in range(rng.randint(1, 2))]}
                             for b in range(rng.randint(1, 3))], 'otherwise': True}

    def ports(name):
        kind = nodes[name]['kind']
        if kind == 'check':
            return [b['name'] for b in nodes[name]['config']['branches']] + ['otherwise']
        return {'grooming': ['groomed'], 'owner_wait': ['admit', 'decline'], 'assignment': ['done'],
                'join': ['done']}.get(kind, [])

    main = []
    for number in range(rng.randint(1, 5)):
        kind = rng.choice(WAITING)
        main.append(node('m%d' % number, kind, check_config() if kind == 'check' else None))
    end = node('done', 'result_handling') if rng.random() < 0.85 else node('done', rng.choice(['build', 'land']))
    fan_at = rng.randrange(len(main)) if rng.random() < 0.6 else None
    for position, name in enumerate(main):
        following = main[position + 1] if position + 1 < len(main) else end
        if position == fan_at:
            width = rng.randint(2, 8)
            starts, lasts = [], []
            for b in range(width):
                kind = rng.choice(WAITING)
                first = node('b%d-%d' % (b, 0), kind, check_config() if kind == 'check' else None)
                chain = [first]
                if rng.random() < 0.4:
                    kind = rng.choice(WAITING)
                    chain.append(node('b%d-%d' % (b, 1), kind, check_config() if kind == 'check' else None))
                starts.append(first)
                lasts.append(chain)
            join = node('j', 'join', {'inputs': []})
            port = ports(name)[0]
            ids = [route(name, port, first) for first in starts]
            nodes[join]['config']['inputs'] = ids
            for chain in lasts:
                for here, there in zip(chain, chain[1:] + [join]):
                    for p in ports(here):
                        route(here, p, there)
            for p in ports(name)[1:]:
                route(name, p, following)
            route(join, 'done', following)
            continue
        for number, p in enumerate(ports(name)):
            if nodes[name]['kind'] == 'check' and number == 0 and position > 0 and rng.random() < 0.3:
                route(name, p, main[rng.randrange(position)])  # a bounded loop back
            elif nodes[name]['kind'] == 'owner_wait' and p == 'decline' and rng.random() < 0.5:
                continue  # a port with no transition ends the cycle without a proposal
            else:
                route(name, p, following)
    return {'id': 'gen-%04d' % index, 'entry': main[0], 'nodes': nodes, 'transitions': transitions, 'fields': fields}


FIELD_TYPES = ('number', 'yes_no', 'choice', 'text')


def _result(identifier, value):
    return {'id': identifier, 'version': 1, 'digest': sha(identifier + canonical(value)), 'value': value}


def supplied(rng, definition, notes):
    """A seeded script step: what the cycle supplies for this exchange."""
    values = {}
    for name, field in sorted(definition['fields'].items()):
        roll = rng.random()
        if roll < 0.08:
            continue
        values[name] = rng.choice(FIELD_VALUES[field['type']] if roll < 0.92 else FIELD_VALUES['text'] + [5])
    items = [_result('subject', {'unit': 'unit-%s' % definition['id'], 'state': 'ready'})]
    if rng.random() < 0.85:
        items.append(_result('owner_answer', {'state': rng.choice(['accepted', 'accepted', 'declined', 'pending'])}))
    if rng.random() < 0.8:
        items.append(_result('worker_result', {'kind': 'proof_bundle'}))
    if rng.random() < 0.7:
        items.append(_result('accepted_result', {'kind': 'proof_bundle'}))
    if rng.random() < 0.9:
        items.append(_result('fields', values))
    for branch, entry in sorted((notes.get('branches') or {}).items()):
        position = entry.get('position') if type(entry) is dict else None
        if position is None:
            continue
        for key, value in (('owner_answer', {'state': 'accepted'}), ('worker_result', {'kind': 'proof_bundle'}),
                           ('fields', values)):
            if rng.random() < 0.55:
                items.append(_result(key + '@' + position, value))
    return items


def _request(operation, cycle, number, workflow, **fields):
    body = {'schema': 'veldo.graph/v1', 'operation': operation, 'cycle_id': cycle,
            'command_id': '%s.%d' % (cycle, number), 'domain_uuid': 'corpus-domain',
            'repository_uuid': 'corpus-repository', 'workflow': workflow}
    body.update(fields)
    return body


SNAPSHOT = {'id': 'snapshot-1', 'version': 1, 'digest': sha('snapshot-1')}


def drive(ask, key, workflow, cycle, rng, definition=None, results=None, limit=14):
    """Drive one cycle to its end with a seeded script; returns the records."""
    records = []

    def exchange(request):
        answer = ask(key, request)
        records.append({'runner': key, 'request': request, 'answer': answer})
        return answer

    answer = exchange(_request('start', cycle, 1, workflow, snapshot=SNAPSHOT))
    number = 1
    while answer.get('outcome') == 'suspended' and number < limit:
        number += 1
        resume = answer['resume']
        roll = rng.random()
        if roll < 0.06:
            exchange(_request('suspend', cycle, number, workflow, resume=resume))
            number += 1
        elif roll < 0.09:
            broken = dict(resume, position='nowhere') if rng.random() < 0.5 else dict(resume, notes='[1]')
            exchange(_request('advance', cycle, number, workflow, snapshot=SNAPSHOT, resume=broken, supplied_results=[]))
            number += 1
        elif roll < 0.11:
            exchange(_request('cancel', cycle, number, workflow, resume=resume))
            return records
        notes = json.loads(resume['notes'])
        given = results(rng, notes) if results else supplied(rng, definition, notes)
        answer = exchange(_request('advance', cycle, number, workflow, snapshot=SNAPSHOT, resume=resume,
                                   supplied_results=given))
    return records


def cycles(ask):
    """Every cycle of the corpus, in order, as records."""
    rng = random.Random(SEED)
    records = []
    # The runtime qualification workload, as control_runtime._workload sends it.
    qualification = {'id': 'veldo-runtime-qualification', 'version': 1, 'digest': sha('qualification')}
    rank = [_result('qualification-rank', {'rank': 7})]
    records += drive(ask, 'qualification:', qualification, 'qualify-cycle', rng, results=lambda r, n: rank)
    records += drive(ask, 'qualification:', qualification, 'qualify-empty', rng, results=lambda r, n: [])
    # The project pipeline, as control_workflow_cycle_pm sends it.
    pm = {'id': 'default_pipeline', 'version': 1, 'digest': sha('default_pipeline')}
    for number in range(6):
        records += drive(ask, 'pm:', pm, 'pm-%d' % number, rng,
                         results=lambda r, n: [_result('dispatch', {'unit': 'unit-pm'})] if r.random() < 0.8 else [])
    # The probe workflows: every failure, the bound, the merge, the fan-out refusals.
    for name in ('loop', 'raise', 'list', 'untyped', 'unnamed', 'named', 'suspend-proposal', 'suspend-nowhere',
                 'nowhere', 'empty', 'tuple', 'fan-wide', 'fan-unsuspended', 'chain', 'fan'):
        workflow = {'id': 'probe-' + name, 'version': 1, 'digest': sha(name)}
        for number in range(3 if name in ('chain', 'fan') else 1):
            records += drive(ask, 'probe:', workflow, 'probe-%s-%d' % (name, number), rng,
                             results=lambda r, n: [_result('r', {'rank': 1})] if r.random() < 0.6 else [])
    records += drive(ask, 'probe:', {'id': 'probe-fan', 'version': 1, 'digest': sha('fan')}, 'probe-fan-fail', rng,
                     results=lambda r, n: [])
    fail = _request('advance', 'probe-fan-fail', 9, {'id': 'probe-fan', 'version': 1, 'digest': sha('fan')},
                    snapshot={'id': 'fail', 'version': 1, 'digest': sha('fail')}, supplied_results=[],
                    resume={'position': 'veldo_parallel', 'step': 1, 'notes': canonical(
                        {'join': 'end', 'branches': {'x': {'position': 'bx', 'last': None},
                                                     'z': {'position': 'bz', 'last': None}}})})
    for notes in ({'join': 'end', 'branches': {'x': {'position': 'bx', 'last': None}}},
                  {'join': 'end', 'branches': {'b%d' % i: {'position': 'bx', 'last': None} for i in range(9)}},
                  {'join': 'gone', 'branches': {'x': {'position': 'bx'}, 'y': {'position': 'by'}}},
                  {'join': 'end', 'branches': {'x': {'position': 'end'}, 'y': {'position': 'end'}}}, None):
        request = json.loads(canonical(fail))
        if notes is not None:
            request['resume']['notes'] = canonical(notes)
            request['snapshot'] = SNAPSHOT
        records.append({'runner': 'probe:', 'request': request, 'answer': ask('probe:', request)})
    # The generated revisions.
    for index in range(GENERATED):
        definition = generate(rng, index)
        text = canonical(definition)
        key = 'revision:' + json.dumps([text, 1])
        workflow = {'id': definition['id'], 'version': 1, 'digest': sha(text)}
        records += drive(ask, key, workflow, 'cycle-%04d' % index, rng, definition=definition)
        if index % 5 == 0:
            wrong = dict(workflow, version=2)
            records += drive(ask, key, wrong, 'cycle-%04d-wrong' % index, rng, definition=definition, limit=1)
    return records


def write(records):
    CORPUS.mkdir(exist_ok=True)
    for old in CORPUS.glob('*.jsonl.gz'):
        old.unlink()
    for start in range(0, len(records), CHUNK):
        lines = ''.join(canonical(dict(r, answer=labelled(r['answer']))) + '\n' for r in records[start:start + CHUNK])
        path = CORPUS / ('exchanges-%03d.jsonl.gz' % (start // CHUNK))
        with gzip.GzipFile(path, 'wb', mtime=0) as out:
            out.write(lines.encode())
        assert path.stat().st_size < 1 << 20
    summary = {'seed': SEED, 'generated_revisions': GENERATED, 'exchanges': len(records),
               'runners': dict(sorted(_count(r['runner'].split(':', 1)[0] for r in records).items())),
               'operations': dict(sorted(_count(r['request']['operation'] for r in records).items())),
               'outcomes': dict(sorted(_count(r['answer']['outcome'] for r in records).items())),
               'failures': dict(sorted(_count(re.sub(r'(gen-|b)[0-9]+(-[0-9]+)?|m[0-9]+|r[0-9]+|f[0-9]+', 'N', r['answer']['failure']['code'] + ': ' + r['answer']['failure']['detail'][:60])
                                              for r in records if r['answer'].get('outcome') == 'failure').items())),
               'fan_out_widths': sorted({len(json.loads(r['answer']['resume']['notes']).get('branches') or {})
                                         for r in records if r['answer'].get('outcome') == 'suspended'} - {0}),
               'files': sorted(p.name for p in CORPUS.glob('*.jsonl.gz'))}
    (CORPUS / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    return summary


def _count(items):
    counts = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return counts


def read():
    records = []
    for path in sorted(CORPUS.glob('exchanges-*.jsonl.gz')):
        with gzip.open(path, 'rt') as source:
            records += [json.loads(line) for line in source]
    return records


def _difference(old, new, where='answer'):
    if type(old) is not type(new):
        return where
    if type(old) is dict:
        for key in sorted(set(old) | set(new)):
            if key not in old or key not in new:
                return where + '.' + key
            found = _difference(old[key], new[key], where + '.' + key)
            if found:
                return found
        return None
    if type(old) is list:
        if len(old) != len(new):
            return where + '[len]'
        for index, (a, b) in enumerate(zip(old, new)):
            found = _difference(a, b, '%s[%d]' % (where, index))
            if found:
                return found
        return None
    if where.endswith('.notes') and type(old) is str:
        try:
            return _difference(json.loads(old), json.loads(new), where + '<json>') or (where if old != new else None)
        except ValueError:
            pass
    return None if old == new else where


def replay(root, python=None, flags=('-I', '-S', '-B')):
    """Replay every recorded request on the step runner; (answers text, first difference or None)."""
    worker = Worker(python or sys.executable, Runners(root, 'steps'), list(flags))
    out, first = [], None
    try:
        for index, record in enumerate(read()):
            answer = labelled(worker.ask(record['runner'], record['request']))
            out.append(canonical(answer))
            if first is None and canonical(answer) != canonical(record['answer']):
                first = {'exchange': index, 'cycle': record['request']['cycle_id'],
                         'command': record['request']['command_id'],
                         'field': _difference(record['answer'], answer)}
    finally:
        worker.close()
    return '\n'.join(out), first


def cross(root, python):
    """Resumes cross both ways: each cycle alternates runners exchange by exchange, LangGraph's resume
    advanced on the step runner and the step runner's on LangGraph, and every answer is compared with
    the other runner's answer to the same request."""
    old = Worker(python, Runners(root, 'langgraph'), ['-I', '-B'])
    new = Worker(sys.executable, Runners(root, 'steps'), ['-I', '-S', '-B'])
    counts = {'langgraph_to_steps': 0, 'steps_to_langgraph': 0, 'differences': []}
    turn = [0]

    def ask(key, request):
        turn[0] += 1
        first, second = (old, new) if turn[0] % 2 else (new, old)
        answer, other = first.ask(key, request), second.ask(key, request)
        if request['operation'] != 'start':
            counts['steps_to_langgraph' if first is old else 'langgraph_to_steps'] += 1
        if canonical(labelled(answer)) != canonical(labelled(other)) and len(counts['differences']) < 5:
            counts['differences'].append({'command': request['command_id'],
                                          'field': _difference(labelled(answer), labelled(other))})
        return answer

    try:
        records = cycles(ask)
    finally:
        old.close()
        new.close()
    counts['exchanges'] = len(records)
    return counts


def main(argv):
    command = argv[1] if len(argv) > 1 else None
    options = dict(zip(argv[2::2], argv[3::2]))
    root = Path(options.get('--root', HERE.parent.parent))
    if command == 'record':
        worker = Worker(options['--python'], Runners(root, 'langgraph'), ['-I', '-B'])
        try:
            print(json.dumps(write(cycles(worker.ask)), indent=1, sort_keys=True))
        finally:
            worker.close()
        return 0
    if command == 'replay':
        _, first = replay(root)
        print(json.dumps({'exchanges': len(read()), 'first_difference': first}, sort_keys=True))
        return 0 if first is None else 1
    if command == 'twice':
        one, _ = replay(root)
        two, _ = replay(root)
        print(json.dumps({'identical': one == two, 'sha256': hashlib.sha256(one.encode()).hexdigest()}))
        return 0 if one == two else 1
    if command == 'cross':
        report = cross(root, options['--python'])
        (HERE / 'crossing.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
        print(json.dumps(report, sort_keys=True))
        return 0 if not report['differences'] else 1
    print(__doc__.split('\n\n')[0])
    return 2


if __name__ == '__main__':
    os.umask(0o022)
    sys.exit(main(sys.argv))
