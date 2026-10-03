"""Regression observations for the independent review of VELDO-0088."""
import copy
import json
import time


def observe(v):
    check, f, cycles, factory, line = (v[k] for k in ('check', 'f', 'cycles', 'factory', 'line'))
    staged = v['staged']
    check('review/pm-principal', 'production Line.run signs staffing as its distinct enrolled PM',
          line.service.principal != staged['manager'] and staged['state'] == 'proposed'
          and staged.get('unit_assignment', {}).get('assigned_by') == staged['manager'])
    units = ['VELDO-8802', 'VELDO-8803']
    engines = line.engines
    line.engines = {}
    for index, unit in enumerate(units):
        objective = v['OB'].read(v['conn'], v['oid'])
        feature = v['objectives'].apply(v['command']('pm', 'propose_feature', objective=v['oid'],
            objective_version=objective['version'], feature='follow-' + str(index),
            title='Another unit for BCG-123', scope=['design']))
        backlog = cycles.services['backlog']
        taken = backlog.apply(v['command']('pm', 'take', feature=feature.get('feature_id'), work_class='PRODUCT_CHANGE'))
        doc = copy.deepcopy(v['doc'])
        for proposal in doc['proposals']:
            command = proposal['command']
            if 'item' in command:
                command['item'] = taken.get('item_id')
            if proposal['type'] == 'decomposition':
                command['unit']['unit'] = unit
                command['unit']['source']['id'] = feature.get('feature_id')
            if proposal['type'] == 'assignment':
                command['unit'] = unit
        # The first document publishes a new unit but claims the earlier staged one.
        doc['decomposition'][0]['unit'] = v['uid'] if index == 0 else unit
        v['reservations'].configure('ceiling/' + unit, 'unit', unit,
            dict(capacity=2, invocations=4, wall_seconds=500), now=time.time())
        v['result_file'].write_text(json.dumps(doc))
        factory.wake('accepted_feature')
        factory.run()
        active = [r for r in cycles.records('proj-a') if r['state'] not in v['PM'].FINAL]
        if active and active[0].get('dispatch') in v['runner'].launches:
            v['runner'].wait(v['runner'].launches[active[0]['dispatch']], timeout=15)
        factory.wake('run_end')
        factory.run()
        result = max(cycles.records('proj-a'), key=lambda r: r['watermark'])
        print('  VELDO-0088 detail: review publication:', unit, result['state'], result.get('refusal'))
        if index == 0:
            check('review/current-publication', 'an earlier READY assigned unit cannot stand in for this publication',
                  result['state'] == 'refused' and result.get('refusal') == 'missing_evidence:cycle_publication'
                  and not result.get('elaboration')
                  and any(p['type'] == 'decomposition' and p['result'].get('unit', {}).get('unit') == unit
                          and p['result'].get('ok') for p in result['proposals']))
        else:
            check('review/current-publication', 'the matching new publication can finish elaboration',
                  result['state'] == 'proposed' and result.get('elaboration', {}).get('state') == 'done')
    for station in ('build', 'review'):
        line.engines = {}
        v['result_file'].write_text(json.dumps(v['empty']))
        factory.wake('adapter_unavailable')
        refused = factory.run()
        check('review/' + station + '-refusal', 'each assigned unit is considered despite an unavailable adapter',
              not refused['faults'] and all(any(r.get('unit') == unit and r.get('station') == station
                  and r.get('refusals') == ['unavailable_service:engineering_adapter']
                  for r in refused['refused']) for unit in units))
        line.engines = engines
        factory.wake('adapter_restored')
        resumed = factory.run()
        check('review/' + station + '-refusal', 'both units launch when their adapter is available',
              not resumed['faults'] and all(any(r.get('unit') == unit and r.get('station') == station
                  for r in resumed['offered']) for unit in units))
        for unit in units:
            attempt = line.latest().get((unit, station))
            if attempt and attempt['dispatch_id'] in v['runner'].launches:
                v['runner'].wait(v['runner'].launches[attempt['dispatch_id']], timeout=15)


def budget(v):
    f, cycles, factory, check = (v[k] for k in ('f', 'cycles', 'factory', 'check'))
    limit = f['entity']('project:proj-a')['data']['coordination_budget']['invocations']
    for unused in range(limit - len(cycles.records('proj-a')) - 1):
        v['run'](v['empty'])
    _, receipt = f['present']('budget-pending', {'kind': 'pm', 'ref': 'proj-a',
        'digest': v['PM'].SN.digest(b'budget-pending')}, 'Choose the remaining scope.')
    (v['base'] / 'hold').write_text('hold')
    held = cycles.start('proj-a', cycles.inputs('proj-a'))
    answered = f['answer'](receipt, 'accept')
    factory.wake('owner_answer')
    pending = factory.run()
    check('review/pending-budget', 'new accepted input is pending at the last allowed cycle',
          answered.get('outcome') == 'settled' and not pending['faults'] and 'proj-a' in cycles.pending)
    if held.get('dispatch') in v['runner'].launches:
        v['runner'].wait(v['runner'].launches[held['dispatch']], timeout=15)
    (v['base'] / 'hold').unlink()
    factory.wake('run_end')
    finished = factory.run()
    events = [json.loads(s) for s in (v['base'] / 'service-events.jsonl').read_text().splitlines()]
    print('  VELDO-0088 detail: pending budget:', len(cycles.records('proj-a')), pending['faults'], finished['faults'])
    check('review/pending-budget', 'exhausted follow-up is observed without aborting the factory pass',
          not finished['faults'] and len(cycles.records('proj-a')) == limit
          and any(e.get('operation') == 'pm_start' and e.get('project') == 'proj-a'
                  and e.get('refusal') == 'budget_exceeded:coordination' for e in events))
