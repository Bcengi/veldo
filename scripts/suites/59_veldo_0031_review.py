"""Regression scenarios from the six independently reproduced VELDO-0031 findings.
Real stores, signatures, IPC, clones and local bare remote refs; no network push.
Each scenario reports assertion failures, including an unexpected runtime exception.
"""
import importlib.util
import multiprocessing as mp
import os
from pathlib import Path
import shutil
import subprocess as sp
import tempfile
import time
import uuid

SRC = ROOT / '.veldo'
PRODUCTION = {
    'claim': ROOT / ".veldo" / "claim.py",
    'control_claim': ROOT / ".veldo" / "control_claim.py",
    'control_claim_client': ROOT / ".veldo" / "control_claim_client.py",
    'lander': ROOT / ".veldo" / "lander.py",
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Fixture:
    def __init__(self, units=('unit', '__land_lock__')):
        self.tmp = tempfile.TemporaryDirectory(prefix='v31r-')
        base = self.base = Path(self.tmp.name)
        mods = base / '.veldo'
        mods.mkdir()
        for n in ('claim', 'control_store', 'control_membership', 'authority_contract', 'control_client',
                  'control_enrollment', 'git_process', 'lander', 'policy_check', 'control_claim',
                  'control_claim_client'):
            shutil.copyfile(PRODUCTION.get(n, SRC / (n + '.py')), mods / (n + '.py'))
        self.mods = mods
        self.C = load('claims31r', mods / 'control_claim.py')
        self.CC = load('client31r', mods / 'control_claim_client.py')
        self.G = load('git31r', mods / 'git_process.py')
        self.S, self.AC, self.CL = self.C.S, self.C.AC, self.C.CL
        self.E, self.IPC = self.CC.E, self.CC.IPC
        keys = self.keys = base / 'keys'
        keys.mkdir()
        self.public = {}
        for w in ('owner', 'worker-a', 'worker-b'):
            sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(keys / w)], check=True, capture_output=True)
            self.public[w] = (keys / (w + '.pub')).read_text().strip()
        origin = base / 'origin'
        origin.mkdir()
        self.git(origin, 'init', '-q')
        self.G.run(['git', '-C', str(origin), 'commit', '-q', '--allow-empty', '-m', 'fixture'],
                   identity=('Fixture', 'fixture@example.invalid'), check=True)
        self.remote = base / 'remote.git'
        self.G.run(['git', 'clone', '-q', '--bare', str(origin), str(self.remote)], check=True)
        self.db = base / 'authority/control.sqlite3'
        self.ids = dict(domain_uuid='claims-domain', store_uuid='claims-store', repository_uuid='claims-repository')
        self.repos = []
        for n in ('a', 'b'):
            repo = base / n
            self.G.run(['git', 'clone', '-q', str(self.remote), str(repo)], check=True)
            self.E.enroll(str(repo), self.ids['domain_uuid'], self.ids['store_uuid'], str(self.db), 'test-host', 1,
                          lambda m: self.sign('owner', m), 'owner', time.time(), repository_uuid=self.ids['repository_uuid'])
            self.repos.append(repo)
        self.conn = self.S.open_store(str(self.db))
        for w in ('worker-a', 'worker-b'):
            self.write(w, 'membership', dict(principal_type='agent_run', roles=[], scope='*'))
            self.write('key-' + w, 'verification_key', dict(principal=w, public_key=self.public[w], effective_at=0))
        self.write('backlog', 'backlog_item', dict(state='PRIORITIZED', repository_uuid=self.ids['repository_uuid']))
        for u in units:
            self.write(u, 'execution_unit', dict(state='READY', repository_uuid=self.ids['repository_uuid'],
                       backlog_item_uuid='backlog', requirements=[], eligible_holders=['worker-a', 'worker-b']))
        self.receiver = self.C.Receiver(self.conn, self.ids, 'owner', lambda m: self.sign('owner', m))
        self.server = None

    def git(self, repo, *args):
        return self.G.check_output(['git', '-C', str(repo), *args], text=True, stderr=sp.DEVNULL)

    def sign(self, who, message):
        return sp.run(['ssh-keygen', '-Y', 'sign', '-f', str(self.keys / who), '-n', self.AC.SIGNATURE_NAMESPACE],
                      input=message, capture_output=True, check=True).stdout.decode()

    def verify(self, message, signature):
        return any(self.AC.ssh_keygen_verify(message, signature, self.AC.allowed_signers_line(w, p), w)[0]
                   for w, p in self.public.items())

    def entities(self):
        return self.S.materialized_state(self.conn)['entities']

    def write(self, eid, kind, data):
        e = self.entities().get(eid, {})
        n = str(uuid.uuid4())
        return self.S.execute(self.conn, dict(command_id='fx-' + n, principal='owner', operation='upsert_entity',
                              parameters=dict(entity_id=eid, kind=kind, data=data),
                              expected_versions={eid: e.get('version', 0)}, artifact_digests=[], nonce='fx-' + n),
                              'owner', lambda m: self.sign('owner', m), 1)

    def packet(self, who, op, unit='unit', generation=0, capabilities=()):
        """The exact packet control_claim_client.Client.request builds."""
        import json
        command = dict(operation=op, unit_id=unit, principal=who, command_id=str(uuid.uuid4()),
                       nonce=str(uuid.uuid4()), generation=generation, capabilities=list(capabilities), **self.ids)
        msg = json.dumps(command, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        return {'command': command, 'signature': self.sign(who, msg)}

    def direct(self, who, op, unit='unit', generation=0):
        return self.receiver.apply(self.packet(who, op, unit, generation))

    # ---- real IPC authority in a forked process ----
    def start_server(self):
        ctx = mp.get_context('fork')
        ready = ctx.Event()
        self.stop = ctx.Event()
        self.address = self.IPC.socket_path_for(self.E.read_binding(str(self.repos[0])))

        def serve():
            conn = self.S.open_store(str(self.db))
            receiver = self.C.Receiver(conn, self.ids, 'owner', lambda m: self.sign('owner', m))
            authority = self.IPC.Authority(self.ids['store_uuid'], self.ids['domain_uuid'], str(self.db), self.E,
                                           self.verify, 'test-host', receiver.apply)
            srv = self.IPC.bind(self.address)
            srv.settimeout(.05)
            ready.set()
            while not self.stop.is_set():
                try:
                    self.IPC.serve_one(srv, authority)
                except TimeoutError:
                    pass
        self.server = ctx.Process(target=serve)
        self.server.start()
        assert ready.wait(10)

    def client(self, i):
        w = ('worker-a', 'worker-b')[i]
        return self.CC.Client(self.repos[i], w, lambda m, w=w: self.sign(w, m), self.verify, 'test-host')

    def close(self):
        if self.server is not None:
            self.stop.set()
            self.server.join(5)
            if self.server.is_alive():
                self.server.terminate()
                self.server.join()
        self.conn.close()
        self.tmp.cleanup()


def review_r1(f):
    bad = [{'command': 'not-a-mapping'}, {'command': ['x']}, [], None]
    for signature in (5, [], {}, None, '\ud800', '\u00e9'):
        packet = f.packet('worker-a', 'inspect')
        packet['signature'] = signature
        bad.append(packet)
    answers = []
    for packet in bad:
        try:
            answers.append(f.receiver.apply(packet).get('reason'))
        except Exception as exc:
            answers.append(type(exc).__name__)
    f.start_server()
    client = f.client(1)
    assert client.claim('unit', 'worker-b')[0]
    # IPC.send rejects lone surrogates while encoding, before reaching the receiver.
    wire_bad = [p for p in bad if not isinstance(p, dict) or p.get('signature') != '\ud800']
    for packet in wire_bad:
        try:
            r = f.IPC.send(str(f.repos[0]), packet, f.E, f.verify,
                           lambda m: f.sign('worker-a', m), 'test-host', timeout=.3)
            answers.append(r['result']['reason'] if r['accepted'] else r['reason'])
        except Exception as exc:
            answers.append(type(exc).__name__)
    alive = f.server.is_alive()
    holder = client.holder('unit') if alive else None
    assert answers == ['malformed_request'] * (len(bad) + len(wire_bad)), answers
    assert alive and holder == 'worker-b'
    assert f.receiver.counts['refused'] == len(bad)
    assert all(r['reason'] == 'malformed_request' for r in f.receiver.observations)


def review_r2(f):
    cid = f.C.claim_id(f.ids['repository_uuid'], 'unit')
    original = f.entities()
    owned = dict(unit_id='unit', backlog_item_uuid='backlog', repository_uuid=f.ids['repository_uuid'],
                 holder='worker-a', generation=1, state='owned', heartbeat_at=f.CL._now())
    observations = []
    # Both missing activation legs, and the reverse (activation without ownership).
    for state, unit, backlog in ((owned, 'READY', 'PRIORITIZED'),
                                 (owned, 'CLAIMED', 'PRIORITIZED'),
                                 ({}, 'RUNNING', 'ACTIVE')):
        f.write(cid, 'claim', state)
        f.write('unit', 'execution_unit', dict(original['unit']['data'], state=unit))
        f.write('backlog', 'backlog_item', dict(original['backlog']['data'], state=backlog))
        before = f.entities()
        for op in ('use', 'inspect', 'claim', 'renew', 'release'):
            who = 'worker-b' if op in ('inspect', 'claim') else 'worker-a'
            r = f.direct(who, op, generation=1)
            observations.append((unit, backlog, op, r['reason']))
        assert f.entities() == before, observations
    assert all(r[-1] == 'ownership_uncertain' for r in observations), observations


def review_r3(f):
    f.start_server()
    client = f.client(0)
    L = load('lander_review', f.mods / 'lander.py')
    cid = f.C.claim_id(f.ids['repository_uuid'], '__land_lock__')
    calls = []
    before = [f.git(r, 'show-ref') for r in (f.repos[0], f.remote)]
    class Ops:
        def sync_main(self): return {'ok': True}
        def reconcile(self, unit): return {'ok': True}
        def gate(self):
            cur = f.entities()[cid]['data']
            f.write(cid, 'claim', dict(cur, heartbeat_at='2999-01-01T00:00:00Z'))
            return {'ok': True}
        def finalize(self, unit):
            calls.append('finalize')
            for r in (f.repos[0], f.remote):
                f.git(r, 'update-ref', 'refs/heads/landed', 'HEAD')
            return {'ok': True}
    # No heartbeat tick: only the immediately-before-finalize use can stop this land.
    reason = None
    try:
        L.Lander('worker-a', Ops(), claims_root=client, hb_interval=60).land()
    except Exception as exc:
        reason = getattr(exc, 'reason', type(exc).__name__)
    assert reason == 'unanswerable' and not calls, (reason, calls)
    assert before == [f.git(r, 'show-ref') for r in (f.repos[0], f.remote)]
    # A real heartbeat stop must be retained even if ownership recovers before finalize.
    cur = f.entities()[cid]['data']
    f.write(cid, 'claim', dict(cur, heartbeat_at=f.CL._now()))
    assert client.release('__land_lock__', 'worker-a')
    import threading
    seen = threading.Event()
    heartbeat = client.heartbeat
    def observed(*args):
        try:
            return heartbeat(*args)
        except Exception:
            seen.set()
            raise
    client.heartbeat = observed
    class HeartbeatOps(Ops):
        def gate(self):
            super().gate()
            # A liveness bound, not a timing claim: it returns the moment the heartbeat observes, and a
            # loaded host (the gate's parallel mutation stage) must not turn a slow thread into a false row.
            assert seen.wait(30), 'heartbeat did not observe uncertain ownership'
            lander._hb_thread.join(10)
            cur = f.entities()[cid]['data']
            f.write(cid, 'claim', dict(cur, heartbeat_at=f.CL._now()))
            return {'ok': True}
    lander = L.Lander('worker-a', HeartbeatOps(), claims_root=client, hb_interval=.01)
    reason = None
    try:
        lander.land()
    except Exception as exc:
        reason = getattr(exc, 'reason', type(exc).__name__)
    assert reason == 'unanswerable' and not calls, (reason, calls)
    assert before == [f.git(r, 'show-ref') for r in (f.repos[0], f.remote)]


def review_r4(f):
    enrolled = f.repos[0] / '.git/veldo'
    unrelated = f.base / 'unrelated'
    unrelated.mkdir()
    prog = ("import importlib.util,sys; s=importlib.util.spec_from_file_location('claim', %r); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            "print(m.claim('unit','worker-a',root=sys.argv[1]))") % str(f.mods / 'claim.py')
    outside = sp.run([__import__('sys').executable, '-c', prog, str(enrolled)],
                     cwd=f.base, capture_output=True, text=True)
    inside = sp.run([__import__('sys').executable, '-c', prog, str(unrelated)],
                    cwd=f.repos[0], capture_output=True, text=True)
    assert outside.returncode != 0 and 'authority_required' in outside.stderr
    assert not (enrolled / 'claims').exists()
    assert inside.returncode == 0 and (unrelated / 'claims/unit.json').exists(), inside.stderr


def review_r5(f):
    r = f.direct('worker-a', 'claim')
    gen = r['claim']['generation']
    cid = f.C.claim_id(f.ids['repository_uuid'], 'unit')
    for op in ('renew', 'release'):
        cur = f.entities()[cid]['data']
        f.write(cid, 'claim', dict(cur, heartbeat_at='2000-01-01T00:00:00Z'))
        assert not f.direct('worker-b', 'claim')['ok']
        assert not f.direct('worker-a', 'use', generation=gen)['ok']
        before = f.entities()
        for who, generation in (('worker-b', gen), ('worker-a', gen + 1)):
            assert not f.direct(who, op, generation=generation)['ok']
        assert f.entities() == before
        result = f.direct('worker-a', op, generation=gen)
        assert result['ok'], (op, result)
    again = f.direct('worker-b', 'claim')
    assert again['ok'] and again['claim']['generation'] == gen + 1


def review_r6(f):
    f.start_server()
    client = f.client(0)
    CL = load('claim_review', f.mods / 'claim.py')
    L = load('lander_review', f.mods / 'lander.py')
    assert f.direct('worker-b', 'claim')['ok']
    cid = f.C.claim_id(f.ids['repository_uuid'], 'unit')
    f.write(cid, 'claim', dict(f.entities()[cid]['data'], heartbeat_at='2999-01-01T00:00:00Z'))
    caught = []
    for caller in (CL, L.CL):
        try:
            caller.claim('unit', 'worker-a', root=client)
        except caller.ClaimStopped as exc:
            caught.append(exc.reason)
        except Exception as exc:
            caught.append(type(exc).__module__)
    assert caught == ['unanswerable', 'unanswerable'], caught
    assert CL.ClaimStopped is L.CL.ClaimStopped is f.CC.CL.ClaimStopped
    f.stop.set()
    f.server.join(5)
    try:
        CL.claim('unit', 'worker-a', root=client)
    except CL.ClaimStopped as exc:
        assert exc.reason == 'authority_unavailable'
    else:
        assert False, 'missing routing stop'


for review_number in range(1, 7):
    review_fixture = Fixture()
    review_error = None
    try:
        globals()['review_r' + str(review_number)](review_fixture)
    except Exception as exc:
        review_error = repr(exc)
    finally:
        review_fixture.close()
    expect('VELDO-0031 review claims/review-r' + str(review_number), review_error is None)
    if review_error:
        print('  review R%d: %s' % (review_number, review_error))
