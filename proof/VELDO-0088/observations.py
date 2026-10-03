"""Additional VELDO-0088 production boundary observations."""
import json
from pathlib import Path
import sqlite3
import sys
import time


def observe(v):
    check, f, PM, base, cycles, runner, conn = (v[k] for k in
        ('check', 'f', 'PM', 'base', 'cycles', 'runner', 'conn'))
    factory, line, uid = (v[k] for k in ('factory', 'line', 'uid'))
    build = line.latest().get((uid, 'build'))
    check('unit/factory-builder-ticket', 'assignment dispatched its builder with accepted role',
          build and build['contract']['input']['context']['holder'] == 'w-build'
          and build['contract']['capability']['configuration']['role_revision']['role'] == 'team-fixture')
    # The factory advances a successful build directly to its assigned reviewer.
    (base / 'engineering-hold').unlink()
    if build and build['dispatch_id'] in runner.launches:
        runner.wait(runner.launches[build['dispatch_id']], timeout=15)
    (base / 'engineering-hold').write_text('hold')
    v['result_file'].write_text(json.dumps(v['empty']))
    factory.wake('run_end', build['dispatch_id'] if build else None)
    advanced = factory.run()
    review = line.latest().get((uid, 'review'))
    check('unit/one-run-staging', 'factory reaches review with one PM run, one build and one review',
          not advanced['faults'] and review is not None
          and len([r for r in line._rows('dispatch') if r['contract']['station'] == 'coordination'])
          == v['before_dispatches'] + 1
          and len([r for r in line._rows('dispatch') if r['contract']['unit'] == uid]) == 2)
    # The real reviewer is held while a PM run, owner answer and completion overlap.
    v['result_file'].write_text(json.dumps(v['empty']))
    rid, receipt = f['present']('combined-88', {'kind': 'pm', 'ref': 'proj-a',
        'digest': PM.SN.digest(b'combined')}, 'Accept the combined input?')
    (base / 'hold').write_text('hold')
    held = cycles.start('proj-a', cycles.inputs('proj-a'))
    before = len(cycles.records('proj-a'))
    answered = f['answer'](receipt, 'accept')
    after_answer = cycles.inputs('proj-a')
    (base / 'engineering-hold').unlink()
    if review and review['dispatch_id'] in runner.launches:
        runner.wait(runner.launches[review['dispatch_id']], timeout=15)
    after_both = cycles.inputs('proj-a')
    cycles.pass_once()
    check('cycle/combined-inputs', 'both accepted events coalesce behind one active cycle',
          answered.get('outcome') == 'settled' and after_both != after_answer
          and cycles.pending.get('proj-a') == after_both
          and len([r for r in cycles.records('proj-a') if r['state'] not in PM.FINAL]) == 1)
    if held.get('dispatch') in runner.launches:
        runner.wait(runner.launches[held['dispatch']], timeout=15)
    (base / 'hold').unlink()
    cycles.pass_once()
    active = [r for r in cycles.records('proj-a') if r['state'] not in PM.FINAL]
    check('cycle/combined-inputs', 'exactly one follow-up binds both new accepted inputs',
          len(active) == 1 and len(cycles.records('proj-a')) == before + 1
          and active[0]['input_key'] == after_both and active[0]['watermark'] > held['watermark'])
    for r in active:
        if r.get('dispatch') in runner.launches:
            runner.wait(runner.launches[r['dispatch']], timeout=15)
    cycles.pass_once()
    check('cycle/combined-inputs', 'consumed owner answer and completion do not loop', not cycles.pass_once())
    fetched = json.loads((base / 'ticket-fetch.json').read_text()) if (base / 'ticket-fetch.json').is_file() else {}
    check('unit/factory-builder-ticket', 'builder invoked its catalog server for the exact ticket',
          fetched.get('request', {}).get('params') == {'name': 'jira.get', 'arguments': {'key': 'BCG-123'}}
          and fetched.get('pid') != __import__('os').getpid()
          and v['L'].D.completed(v['dispatches'].record(build['dispatch_id']) if build else None))
    factory.wake('run_end', build['dispatch_id'] if build else None)
    report = factory.run()
    review = line.latest().get((uid, 'review'))
    print('  VELDO-0088 detail: engineering:', report['refused'], report['faults'])
    if review and review['dispatch_id'] in runner.launches:
        runner.wait(runner.launches[review['dispatch_id']], timeout=15)
        review = v['dispatches'].record(review['dispatch_id'])
    check('unit/independent-review', 'a distinct assigned reviewer completes a separate ordinary run',
          review and v['L'].D.completed(review)
          and review['contract']['input']['context']['reviewer'] == 'w-rev1'
          and review['contract']['input']['context']['holder'] == 'w-build'
          and review['contract']['input']['payload']['follows'] == build['dispatch_id']
          and review['contract']['source']['commit'] == build['contract']['source']['commit'])
    check('unit/independent-review', 'gate refuses a builder reviewing its own assignment',
          not v['gate'].decide('review', uid, context={'holder': 'w-build', 'reviewer': 'w-build'})['eligible'])
    check('unit/independent-review', 'one build and one review consume the staged unit',
          len([r for r in line._rows('dispatch') if r['contract']['unit'] == uid]) == 2)
    waiting_value = dict(v['empty'], owner_questions=['Choose the next step.'],
        proposals=[dict(name='ask-owner', type='question', command=v['question'])])
    waiting = v['run'](waiting_value)
    worker_id = v['L'].D.RES.entity('worker', [v['domain'], waiting['dispatch']])
    worker = PM.row(conn, worker_id)
    check('cycle/waiting-release', 'waiting on a person has an exited worker and released slot',
          waiting['state'] == 'waiting_owner'
          and f['inbox'].read(f['I'].assignment_id(v['repository'], 'question-88')) is not None
          and v['dispatches'].record(waiting['dispatch'])['state'] == 'exited'
          and worker and worker['data'].get('retired') is True)
    for receipt in cycles.records('proj-a'):
        snapshot = PM.SN.load(v['S'], conn, receipt['snapshot']['id'], v['domain'], v['repository'])
        dispatched = v['dispatches'].record(receipt['dispatch']) if receipt.get('dispatch') else None
        check('cycle/receipts', receipt['cycle'],
              receipt['project'] == 'proj-a' and receipt['domain'] == v['domain']
              and receipt['repository'] == v['repository']
              and receipt['accepted_commit'] == snapshot['accepted_commit']
              and receipt['watermark'] == snapshot['watermark']
              and receipt['input_versions'] == snapshot['inputs']
              and receipt['workflow'] == PM.WORKFLOW
              and PM.row(conn, 'pm-cycle:' + receipt['cycle'])['data'] == receipt
              and dispatched and receipt['reservation'] == dispatched['contract']['reservation']
              and dispatched['contract']['input']['payload']['snapshot'] == snapshot
              and PM.SN.digest(PM.SN.canonical(receipt['input_members'])) == receipt['input_key'])
    attacks(v)


def attacks(v):
    """Run hostile node bodies inside the actual LangGraph child, over generated files only."""
    PM, base, G, check = (v[k] for k in ('PM', 'base', 'G', 'check'))
    source = (v['mods'] / 'control_graph_langgraph.py').read_text()
    extension = (v['mods'] / 'control_graph_pm.py').read_text()
    database = base / 'attack.sqlite'
    with sqlite3.connect(database) as db:
        v['conn'].backup(db)
        original = db.execute('SELECT data FROM entities WHERE id=?', (v['uid'],)).fetchone()
    marker = base / 'shell-marker'
    attempts = {
        'shell': "subprocess.run([sys.executable, '-c', " + repr('from pathlib import Path; Path(' + repr(str(marker)) + ').touch()') + "]) ",
        'SQL priority': 'sqlite3.connect(' + repr(str(database)) + ").execute(" + repr("UPDATE entities SET data=json_set(data, '$.priority', 9) WHERE id='" + v['uid'] + "'") + " ).connection.commit()",
        'store read': 'open(' + repr(str(v['f']['db'])) + ", 'rb').read(16)",
        'invented role': "return {'role': 'priority_owner', 'next': None}",
        'direct priority output': "return {'priority': 9, 'next': None}",
    }
    for name, code in attempts.items():
        # Imports happen before entry, just as they do in the installed runner.
        injected = 'import subprocess,sqlite3,sys\n' + extension.replace(
            '    def step(view):\n', '    def step(view):\n        ' + code + '\n')
        runner = base / ('attack-' + name.replace(' ', '-') + '.py')
        runner.write_text(source.replace("\nif __name__ == '__main__':\n", '\n' + injected + "\nif __name__ == '__main__':\n"))
        runtime = dict(v['runtime'], runner=str(runner))
        graph = G.Adapter(runtime, v['domain'], v['repository'], evidence=G.runtime_evidence())
        receipt = v['staged']
        answer = graph.start('attack-' + name.replace(' ', '-'), 'attack-command', receipt['snapshot'], receipt['workflow'])
        check('proposal/graph-process', name + ' is refused inside the child',
              answer['outcome'] == 'failure' and answer['runtime']['name'] == 'langgraph')
    with sqlite3.connect(database) as db:
        unchanged = db.execute('SELECT data FROM entities WHERE id=?', (v['uid'],)).fetchone() == original
    check('proposal/graph-process', 'no shell side effect or direct priority change', not marker.exists() and unchanged)
