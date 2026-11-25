"""Host-relative reservations and explicit fail-closed native qualification policy."""


def _v364_checks():
    import contextlib
    import importlib.util
    import io
    import json

    def load(path):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    scheduler = load(ROOT / "scripts" / "gate_schedule.py")
    qualification = load(ROOT / "scripts" / "qualify_mutation_host.py")
    graph = json.loads((ROOT / 'scripts/gate_graph.json').read_text())
    node = graph['nodes']['mutation']
    configured = graph['mutation_floor']

    def row(name, passed):
        expect('VELDO-0365 host-relative/' + name, passed)

    def capacity(cpu=8, memory=15 * 2**30):
        return dict(cpu=cpu, memory=memory, manager=16)

    def claim(cpu=1, memory=2**30, manager='none'):
        return dict(cpu=cpu, memory=memory, manager=manager, ports=[])

    def refused(action):
        try:
            action()
        except scheduler.Refused:
            return True
        return False

    try:
        small = scheduler.Ledger(capacity(), configured)
        admitted = small.floor == dict(cpu=8, memory=9 * 2**30)
    except scheduler.Refused:
        admitted = False
    row('eight-core', admitted)
    if admitted:
        aggregate, _ = scheduler.node_claim(node, None, capacity())
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                granted = small.acquire('mutation', aggregate, mutation=True)
            except scheduler.Refused:
                granted = False
                small.acquire('mutation', dict(claim(8, 9 * 2**30, 'exclusive'), host_lock='shared'), mutation=True)
            small.handoff('mutation', node['coordinator'])
            grants = [small.acquire('worker%d' % i, claim(), mutation=True) for i in range(8)]
            worker_bad = refused(lambda: small.demand(claim(9)))
            combined_bad = refused(lambda: small.acquire('root-plus-child', claim(8), mutation=True))
        row('aggregate-and-mix', granted and aggregate['cpu'] == 8 and grants == [True]*7+[False]
            and all(small.totals()[r] <= small.capacity[r] for r in small.capacity))
        row('worker-too-large', worker_bad and combined_bad)
        # Full manager capacity remains a real claim, never fitted to CPU availability.
        row('manager-unchanged', small.demand(claim(.1, 1, 'exclusive'))['manager'] == 16)
    else:
        for name in ('aggregate-and-mix', 'worker-too-large', 'manager-unchanged'):
            row(name, False)
    independent = scheduler.Ledger(capacity())
    with contextlib.redirect_stdout(io.StringIO()):
        held = independent.acquire('holder', dict(claim(manager='shared'), ports=[12345], host_lock='shared'))
        blocked = [not independent.acquire('manager-exclusive', claim(manager='exclusive')),
                   not independent.acquire('port-collision', dict(claim(), ports=[12345])),
                   not independent.acquire('lock-exclusive', dict(claim(), host_lock='exclusive'))]
    row('exclusions-retained', held and all(blocked))
    large = scheduler.Ledger(capacity(20), configured)
    old = scheduler.startup_estimate(node['estimate'])
    fitted, _ = scheduler.node_claim(node, None, capacity(20))
    row('large-host-identical', large.floor == configured
        and {r: fitted[r] for r in ('cpu', 'memory')} == old)
    limited = scheduler.Ledger(capacity(memory=3 * 2**30), configured)
    row('memory-and-overhead', limited.floor == dict(cpu=8, memory=3 * 2**30)
        and refused(lambda: scheduler.node_claim(node, None, capacity(cpu=.25)))
        and refused(lambda: limited.demand(claim(memory=4 * 2**30))))
    row('malformed-floor', all(refused(lambda floor=floor: scheduler.Ledger(capacity(), floor))
        for floor in ({'cpu': -1, 'memory': 1}, {'cpu': float('nan'), 'memory': 1}, {'cpu': 1})))
    good = {n: {'passed': True} for n in qualification.REQUIRED}
    bad = []
    for name in qualification.REQUIRED:
        bad.extend([dict(good, **{name: {'passed': False}}), {k: v for k, v in good.items() if k != name}])
    row('qualification-fail-closed', qualification.qualified(good)
        and not any(qualification.qualified(checks) for checks in bad)
        and not qualification.qualified({}))


_v364_checks()
