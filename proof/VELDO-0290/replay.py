#!/usr/bin/env python3
"""VELDO-0290 AC4: replay the declared suites' baseline controls beside real bulk mutant jobs.

    python3 proof/VELDO-0290/replay.py plan            what each arm would run; runs no worker
    python3 proof/VELDO-0290/replay.py quiet           the declared controls alone, one at a time
    python3 proof/VELDO-0290/replay.py off             ceiling off: claims admitted to full capacity
    python3 proof/VELDO-0290/replay.py on              ceiling on, at gate_graph.json's value
    python3 proof/VELDO-0290/replay.py on --ceiling 9  ceiling on, at another value
    python3 proof/VELDO-0290/replay.py verdict         replay.json from the three summaries

The run is outside the gate and takes no lock: the caller holds the host gate lock. It makes its
own delegated user scope the way the gate does (gate_host.make_scope, the gate's memory limit), a
scratch ledger in this process (gate_schedule.Ledger) and the coordinator's own Workers and
Admission, so a worker is launched, confined, metered and cleaned up exactly as in the stage.

One round is one Workers.run call over one baseline control of every declared suite that has a
registered case, and a set of bulk jobs: real mutant jobs of cases of undeclared suites. Rounds
repeat until the arm has its control runs (150 by default). In the off arm nothing is declared to
the coordinator, so the order is the one given (a control, then a share of the bulk, and so on)
and no claim is wall_clock, as at 646ff7c8. In the on arm the coordinator orders and claims by the
manifest, as it now does in the gate.

Claims come from the measured resource store by case identity, whichever checkout recorded them,
since the stage's load depends on them; a case with no record gets its suite's median, then the
median of all, then one core and 1 GiB. The summary says how many claims came from where.

Each mode writes replay-<mode>.summary.json beside this file. Worker output is hashed, measured
and deleted. Any failed row of a declared control counts as a timing-row failure: the replay
cannot tell rows apart, so it names every failed row.
"""
import argparse
import collections
import contextlib
import importlib.util
import json
import math
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
PROOF = Path(__file__).resolve().parent
MODES = ('quiet', 'off', 'on')
# AC4: the stage's load as the landing-c flake analysis of 2026-11-11 recorded it, and the margins
# of the stall fraction bars.
LOAD_PEAK_CPU, LOAD_BUSY_CORES = 19.4, 10.3
ON_MARGIN, OFF_MARGIN = 0.02, 0.05


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def figures(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return dict(count=0)
    rank = max(1, math.ceil(0.95 * len(values)))  # nearest rank
    return dict(count=len(values), minimum=round(values[0], 3), median=round(statistics.median(values), 3),
                p95=round(values[rank - 1], 3), maximum=round(values[-1], 3))


def scrub(value):
    """No path of this host's checkout or home in a kept file."""
    if isinstance(value, str):
        return value.replace(str(ROOT), '<root>').replace(str(Path.home()), '<home>')
    if isinstance(value, dict):
        return {key: scrub(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [scrub(item) for item in value]
    return value


def measured_claims(gate):
    """{identity: (claim, suite)} from the resource store, the newest record of each identity."""
    now, newest = time.time(), {}
    for path in Path(gate.CASE_TIMES).glob('*.json'):
        try:
            item = json.loads(path.read_text())
            runs = gate.resource_samples(item, now)
        except (OSError, ValueError, TypeError):
            continue
        if not runs or not isinstance(item.get('identity'), str):
            continue
        at = max(run['at'] for run in runs)
        if item['identity'] not in newest or at > newest[item['identity']][0]:
            newest[item['identity']] = (at, gate.resource_claim(runs), item.get('suite'))
    return {identity: (claim, suite) for identity, (_at, claim, suite) in newest.items()}


class Claims:
    def __init__(self, gate):
        self.measured = measured_claims(gate)
        by_suite = collections.defaultdict(list)
        for claim, suite in self.measured.values():
            by_suite[suite].append(claim)
        median = lambda claims: {r: statistics.median(c[r] for c in claims) for r in ('cpu', 'memory')}
        self.suites = {suite: median(claims) for suite, claims in by_suite.items()}
        self.everything = median([c for c, _s in self.measured.values()]) if self.measured else None
        self.sources = collections.Counter()

    def claim(self, case):
        if case['identity'] in self.measured:
            claim, source = self.measured[case['identity']][0], 'measured'
        elif case['suite'] in self.suites:
            claim, source = self.suites[case['suite']], 'suite_median'
        elif self.everything is not None:
            claim, source = self.everything, 'all_median'
        else:
            claim, source = dict(cpu=1.0, memory=2**30), 'default'
        self.sources[source] += 1
        return dict(cpu=claim['cpu'], memory=claim['memory'], source=source, keys=[])


def plan(gate, legs, bulk_per_round, want_controls):
    """The controls (one case of every declared suite that has one) and the bulk pool."""
    inventory = gate.inventory_local(ROOT)
    declared = gate.SuiteResources.from_root(ROOT).wall_clock
    leg = legs.mutation_leg()
    claims = Claims(gate)
    groups = collections.defaultdict(list)
    for case in inventory:
        groups[gate.control_group(case)].append(case)
    controls, skipped, seen = [], {}, set()
    for case in inventory:
        suite = case['suite']
        if suite not in declared or suite in seen:
            continue
        seen.add(suite)
        try:
            gate.in_leg(leg, case)
        except gate.Refused as error:
            skipped[suite] = error.code
            continue
        members = [claims.claim(member) for member in groups[gate.control_group(case)]]
        controls.append((case, dict(cpu=max(m['cpu'] for m in members), memory=max(m['memory'] for m in members),
                                    source='group_largest', keys=[])))
    for suite in sorted(declared - seen):
        skipped[suite] = 'no registered case'
    pool = collections.defaultdict(list)
    for case in inventory:
        if case['suite'] in declared:
            continue
        try:
            gate.in_leg(leg, case)
        except gate.Refused:
            continue
        pool[case['suite']].append(case)
    bulk, depth = [], 0
    while any(len(cases) > depth for cases in pool.values()):  # round robin over the suites
        bulk += [cases[depth] for cases in pool.values() if len(cases) > depth]
        depth += 1
    rounds = max(1, math.ceil(want_controls / max(1, len(controls))))
    return dict(inventory=len(inventory), declared=sorted(declared), controls=controls, skipped=skipped,
                bulk=bulk, bulk_per_round=bulk_per_round, rounds=rounds, leg=leg, claims=claims)


class Scratch:
    """The ledger client of a coordinator, answered by a ledger in this process as the scheduler's
    channel answers."""
    def __init__(self, ledger):
        self.ledger, self.last_reply = ledger, {}

    def acquire(self, name, cpu, memory, manager='none', ports=(), host_lock='none', wall_clock=False):
        claim = dict(cpu=cpu, memory=memory, manager=manager, ports=list(ports))
        if wall_clock:
            claim['wall_clock'] = True
        granted = self.ledger.acquire(name, claim, mutation=True)
        self.last_reply = self.ledger.answer(granted, name)
        return granted

    def release(self, name):
        if name in self.ledger.waiting:
            self.ledger.withdraw(name)
        else:
            self.ledger.release(name)
        self.last_reply = self.ledger.answer(True, name)

    def close(self):
        pass


def run(mode, arguments):
    gate = load(ROOT / 'scripts/check_gate_mutations.py')
    scheduler = load(ROOT / 'scripts/gate_schedule.py')
    ownership = load(ROOT / 'scripts/mutation_ownership.py')
    host = load(ROOT / 'scripts/gate_host.py')
    legs = load(ROOT / 'scripts/gate_legs.py')
    validator = load(ROOT / '.veldo/validate.py')
    planned = plan(gate, legs, 0 if mode == 'quiet' else arguments.bulk,
                   arguments.quiet_runs if mode == 'quiet' else arguments.controls)
    if not planned['controls']:
        raise SystemExit('no declared suite has a registered case')
    config = host.load()
    if config['scope'] is None:
        raise SystemExit('scripts/gate_host.json declares no scope; the meter needs a delegated one')
    load_before = list(os.getloadavg())
    _name, cgroup = host.make_scope(config['scope'], state={})
    os.environ['VELDO_GATE_SCOPE'] = cgroup
    graph = json.loads((ROOT / 'scripts/gate_graph.json').read_text())
    capacity = scheduler.capacities(graph, cgroup, ROOT / 'scripts/suites/manifest.json')
    floor = graph['mutation_floor']
    ceiling = None
    if mode == 'on':
        ceiling = arguments.ceiling if arguments.ceiling is not None else graph['wall_clock_ceiling']['cpu']
    ledger = scheduler.Ledger(capacity, floor, ceiling=ceiling)
    ledger.acquire('root', dict(cpu=0, memory=0, manager='none', ports=[]), mutation=True)
    admission = gate.Admission(Scratch(ledger), capacity, floor, lambda name: ownership.WorkerMeter(cgroup, name))
    common = gate.common_directory(ROOT)
    files = gate.read_inputs(ROOT, common)
    head = gate.git(ROOT, common, 'rev-parse', 'HEAD')
    results, errors, walls, discarded = {}, [], [], []
    with tempfile.TemporaryDirectory(prefix='v290-replay-') as temporary:
        directory = Path(temporary)
        frozen, logs = directory / 'input', directory / 'logs'
        gate.snapshot(ROOT, common, frozen, files, head)
        logs.mkdir()
        workers = gate.Workers(time.monotonic() + arguments.budget,
                               parallel=1 if mode == 'quiet' else gate.worker_count(), admission=admission)
        workers.leg = planned['leg']
        workers.resources = gate.SuiteResources.from_root(frozen)
        if mode != 'on':
            # Nothing is declared to the coordinator: no wall_clock claim and the order as given.
            workers.resources.wall_clock = set()
        job = lambda case, kind, claim: dict(case=case, mode=kind, budget_seconds=gate.WORKER_CEILING, claim=claim)
        started = time.monotonic()
        with open(directory / 'ledger.log', 'w') as lines, contextlib.redirect_stdout(lines):
            for number in range(planned['rounds']):
                controls = [('control-%d:%s' % (number, case['suite']), job(case, 'baseline', claim))
                            for case, claim in planned['controls']]
                size = planned['bulk_per_round']
                chosen = [planned['bulk'][(number * size + n) % len(planned['bulk'])] for n in range(size)] \
                    if planned['bulk'] else []
                bulk = [('bulk-%d-%d:%s' % (number, n, case['identity']),
                         job(case, 'mutant', planned['claims'].claim(case))) for n, case in enumerate(chosen)]
                share, order = len(bulk) // len(controls), []
                for n, control in enumerate(controls):
                    order.append(control)
                    order += bulk[n * share:(n + 1) * share]
                order += bulk[len(controls) * share:]
                began = time.monotonic()
                try:
                    workers.run(dict(order), logs, frozen,
                                on_result=lambda name, completed: results.__setitem__(name, completed))
                except Exception as error:  # A worker error ends the round; the next one still runs.
                    errors.append(dict(round=number, error=getattr(error, 'code', type(error).__name__),
                                       detail=str(error)[:400]))
                walls.append(round(time.monotonic() - began, 1))
        wall = time.monotonic() - started
        state = ledger.ceiling_state()
        for path in sorted(p for p in [*logs.iterdir(), directory / 'ledger.log'] if p.is_file()):
            discarded.append((str(path.relative_to(directory)), path.read_bytes()))
    events = {event['name']: event for event in admission.events}
    controls, bulk_stalls, cpu_seconds = [], [], 0.0
    for outcome in workers.outcomes:
        cpu_seconds += outcome.get('measurement', {}).get('cpu_seconds', 0)
        if not outcome['name'].startswith('control-'):
            bulk_stalls.append(outcome.get('stall_seconds'))
            continue
        observation = ((results.get(outcome['name']) or {}).get('result') or {}).get('observation') or {}
        event = events.get(outcome['name'], {})
        controls.append(dict(
            name=outcome['name'], leg=outcome.get('leg'), elapsed=round(outcome['elapsed'], 3),
            stall_seconds=outcome.get('stall_seconds'),
            cpu_seconds=outcome.get('measurement', {}).get('cpu_seconds'),
            rows=observation.get('count'), failed_rows=observation.get('failed_rows'),
            error=outcome.get('error'), cores_granted_at_admission=(event.get('granted') or {}).get('cpu'),
            waited_seconds=event.get('waited_seconds'), ceiling_in_force=event.get('ceiling_in_force')))
    failed = [dict(control=c['name'], rows=c['failed_rows']) for c in controls if c['failed_rows']]
    deciding = dict(
        arm=mode, ceiling_cpu=ceiling, capacity=capacity, mutation_floor=floor, parallel=workers.parallel,
        rounds=planned['rounds'], control_runs=len(controls),
        controls_with_result=sum(c['failed_rows'] is not None for c in controls),
        controls_per_round=len(planned['controls']), bulk_jobs_per_round=planned['bulk_per_round'],
        bulk_runs=len(bulk_stalls), failed_rows=failed, timing_row_failure=bool(failed),
        worker_errors=[dict(name=o['name'], error=o['error'], detail=o.get('detail', '')[:300])
                       for o in workers.outcomes if 'error' in o],
        round_errors=errors,
        control_stall_seconds=figures([c['stall_seconds'] for c in controls]),
        controls_without_stall=sum(c['stall_seconds'] is None for c in controls),
        bulk_stall_seconds=figures(bulk_stalls), peak_workers=workers.peak,
        stage_wall_seconds=round(wall, 1), round_wall_seconds=walls,
        seconds_under_ceiling=round(state['seconds'], 1) if state else 0.0,
        peak_granted=admission.peak, mean_busy_cores=round(cpu_seconds / max(wall, 1e-6), 2),
        claim_sources=dict(planned['claims'].sources), suites_skipped=planned['skipped'],
        host_load_before=load_before, host_load_after=list(os.getloadavg()), controls=controls)
    path = PROOF / ('replay-%s.summary.json' % mode)
    validator.write_proof_summary(path, 'python3 proof/VELDO-0290/replay.py ' + ' '.join(sys.argv[1:]),
                                  scrub(deciding), discarded=discarded, root=ROOT, timing=True)
    print('%s: %d control runs, %d with failed rows, stall %s, wall %.0f s, peak %d workers, %s'
          % (mode, len(controls), len(failed), deciding['control_stall_seconds'], wall, workers.peak, path.name))
    return 0


def verdict():
    """AC4's rule over the three summaries, as amended 2026-11-11: load by the off arm's peak claim
    and busy cores, stall by its share of a control's elapsed time. Writes replay.json."""
    validator = load(ROOT / '.veldo/validate.py')
    arms, missing = {}, []
    for mode in MODES:
        path = PROOF / ('replay-%s.summary.json' % mode)
        if path.is_file():
            arms[mode] = json.loads(path.read_text())
        else:
            missing.append(path.name)
    if missing:
        raise SystemExit('missing: ' + ', '.join(missing))
    part = {mode: arms[mode]['deciding'] for mode in MODES}
    # A control's stall fraction is its stall_seconds divided by its elapsed seconds.
    fractions = {mode: figures([c['stall_seconds'] / c['elapsed'] for c in part[mode]['controls']
                                if c.get('stall_seconds') is not None and c.get('elapsed')])
                 for mode in MODES}
    p95 = {mode: fractions[mode].get('p95') for mode in MODES}
    seconds = {mode: part[mode]['control_stall_seconds'].get('p95') for mode in MODES}
    enough = (part['off']['control_runs'] >= 150 and part['on']['control_runs'] >= 150
              and part['quiet']['control_runs'] >= 20 and None not in p95.values()
              and all(fractions[mode]['count'] == part[mode]['control_runs'] for mode in MODES))
    complete = all(part[mode]['controls_with_result'] == part[mode]['control_runs']
                   and not part[mode]['round_errors'] for mode in MODES)
    peak = (part['off'].get('peak_granted') or {}).get('cpu')
    busy = part['off'].get('mean_busy_cores')
    reached = peak is not None and busy is not None and peak >= LOAD_PEAK_CPU and busy >= LOAD_BUSY_CORES
    on_holds = (enough and not part['on']['timing_row_failure'] and p95['on'] <= p95['quiet'] + ON_MARGIN)
    off_shows = enough and (part['off']['timing_row_failure']
                            or (p95['off'] >= 3 * p95['on'] and p95['off'] >= p95['on'] + OFF_MARGIN))
    if not enough or not complete:
        outcome = ('incomplete: an arm has too few control runs, a control without a result or a stall figure, '
                   'or a failed round')
    elif not reached:
        outcome = 'the off arm did not reach the stage\'s load; the fix is not claimed'
    elif not off_shows:
        outcome = 'the replay found no starvation that the ceiling removes; the fix is not claimed'
    elif on_holds:
        outcome = 'the off arm reached the stage\'s load; the fix is shown at this ceiling'
    else:
        outcome = 'the off arm shows the starvation and the on arm does not hold: the ceiling is not low enough'
    keep = ('arm', 'ceiling_cpu', 'control_runs', 'controls_with_result', 'failed_rows', 'timing_row_failure',
            'control_stall_seconds', 'peak_workers', 'stage_wall_seconds', 'seconds_under_ceiling',
            'peak_granted', 'mean_busy_cores', 'bulk_runs', 'round_errors', 'worker_errors', 'claim_sources')
    deciding = dict(
        outcome=outcome, fix_shown=bool(enough and complete and reached and on_holds and off_shows),
        ceiling_cpu=part['on']['ceiling_cpu'],
        rule=dict(load='the off arm\'s peak CPU granted at least %s of 20 cores and its mean busy cores at least %s'
                       % (LOAD_PEAK_CPU, LOAD_BUSY_CORES),
                  stall_fraction='a control\'s stall_seconds divided by its elapsed seconds',
                  on_arm='no timing-row failure, and its 95th percentile stall fraction at most %s above the '
                         'quiet reference\'s' % ON_MARGIN,
                  off_arm='a timing-row failure, or its 95th percentile stall fraction at least 3 times the on '
                          'arm\'s and at least %s above it' % OFF_MARGIN,
                  counts='at least 150 control runs in each arm and 20 in the quiet reference'),
        checks=dict(enough_runs=enough, every_control_has_a_result=complete, off_arm_reached_load=bool(reached),
                    off_peak_granted_cpu=None if peak is None else round(peak, 2), off_mean_busy_cores=busy,
                    on_arm_holds=bool(on_holds), off_arm_shows=bool(off_shows), stall_fraction_p95=p95,
                    stall_p95_seconds=seconds),
        arms={mode: dict({key: part[mode].get(key) for key in keep}, control_stall_fraction=fractions[mode])
              for mode in MODES},
        sources={mode: dict(file='proof/VELDO-0290/replay-%s.summary.json' % mode,
                            command=arms[mode]['command'], commit=arms[mode]['environment'].get('commit'),
                            load=arms[mode]['environment'].get('load')) for mode in MODES})
    validator.write_proof_summary(PROOF / 'replay.json', 'python3 proof/VELDO-0290/replay.py verdict', deciding,
                                  discarded=[], root=ROOT, timing=True)
    print('replay verdict: ' + outcome)
    return 0


def show_plan(arguments):
    gate, legs = load(ROOT / 'scripts/check_gate_mutations.py'), load(ROOT / 'scripts/gate_legs.py')
    planned = plan(gate, legs, arguments.bulk, arguments.controls)
    for case in planned['bulk'][:arguments.bulk]:
        planned['claims'].claim(case)
    print(json.dumps(dict(
        inventory=planned['inventory'], declared_suites=len(planned['declared']),
        controls_per_round=len(planned['controls']), rounds=planned['rounds'],
        control_runs=planned['rounds'] * len(planned['controls']), suites_skipped=planned['skipped'],
        bulk_pool=len(planned['bulk']), bulk_jobs_per_round=arguments.bulk,
        control_cores_claimed=round(sum(claim['cpu'] for _case, claim in planned['controls']), 2),
        claim_sources=dict(planned['claims'].sources),
        controls=[case['identity'] for case, _claim in planned['controls']]), indent=1))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('mode', choices=('plan', 'verdict') + MODES)
    parser.add_argument('--controls', type=int, default=150, help='control runs wanted in an arm')
    parser.add_argument('--quiet-runs', type=int, default=20, help='control runs wanted in the quiet reference')
    parser.add_argument('--bulk', type=int, default=150, help='bulk mutant jobs in each round')
    parser.add_argument('--ceiling', type=float, help='the on arm\'s ceiling, when not gate_graph.json\'s')
    parser.add_argument('--budget', type=float, default=6 * 3600, help='seconds one mode may take in all')
    arguments = parser.parse_args()
    if arguments.mode == 'plan':
        return show_plan(arguments)
    if arguments.mode == 'verdict':
        return verdict()
    return run(arguments.mode, arguments)


if __name__ == '__main__':
    sys.exit(main())
