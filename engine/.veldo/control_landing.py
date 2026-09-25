#!/usr/bin/env python3
"""Exact-tip publication and the confirmed completion receipt (PLAN-0019 W42, VELDO-0057, R76).

WHAT THIS MODULE IS. The landing's effect boundary and its completion writer. GitLandOps.finalize
(lander.py) hands it the candidate VELDO-0056 built and VELDO-0058's installed gate verified from
outside, once the authority's policy and the gate observation are accepted, together with the unit's
land dispatch. Landing.publish then, in order:

  1. stops, with no new attempt, when this dispatch already has a recorded publication (its recorded
     answer is final) or when another publication of the unit has no conclusive answer (unknown or
     still in flight): an unconfirmed publication never authorizes another one;
  2. re-reads the current authority and the EXACT subject at the effect boundary (subject): the
     domain's authority record and generation; the candidate commit's tree from Git, which must be
     the candidate's recorded tree and the tree the gate observation tested; the proof manifest at
     the evidence commit, whose digest must be the recorded proof digest and which must name the
     recorded implementation commit; the floor's handoff, whose reviewed source and proof must be
     exactly the evidence commit and that proof digest; every dependency landed now, by the one
     completion reader (control_eligibility), with its current store version and digest; and each
     approval the unit requires, granted for the unit's current revision and bound to exactly this
     subject (tree, source, proof and dependency versions). Any difference refuses by name, before
     anything is written or moved;
  3. copies the candidate's objects into the effect executor's configured publication clone under
     refs/veldo/landing/, and writes the VELDO-0028 effect contract and permission for this dispatch:
     payload commit, tree and old tip, the old tip being the candidate's recorded watermark, never a
     tip read now;
  4. asks the VELDO-0028 protected effect executor to publish. Its publication is a compare-and-swap
     of that exact old tip: it lists every destination and requires the ref at the old tip, then pushes
     with git's force-with-lease option naming the ref and the old tip. The swap is atomic AT THE
     REMOTE: the push sends the old value with the update and the remote's receive-pack applies it in
     a ref transaction that verifies the ref still holds that value under the ref lock, so a tip that
     moved between the check and the update refuses rather than being overwritten. The executor
     records the answer in the journal under `effect:<dispatch>`: completed with every destination at
     the tip, refused before anything reached a destination, or unknown;
  5. reads that recorded answer back from the store. Refused is a failed publication: named, nothing
     completed. Unknown (or no answer) is a stop under the original dispatch: nothing completed, no
     further attempt. Only a completed publication goes on to completion.

Landing.complete then decides success from the remote's own answer, re-read from the remote now (the
receiver's ref must be exactly the candidate commit), re-derives every link of the R76 evidence chain
from its own authority (the implementation commit and proof digest from Git, the reviewed source and
proof digests from the floor, the old tip, candidate and tree from the recorded publication, the tested
tree from the gate observation, and the publication record itself as the final receipt), and commits
the revision_landed completion receipt for the exact unit and dispatch in ONE store transaction whose
transition refuses unless the publication it names is still the confirmed one and the unit is still at
the receipt's revision. Only then does it run the VELDO-0051 projection (control_event_projection),
which alone derives spec.shipped from that receipt.

WHAT IT IS NOT. Release 1 function only: a lost or ambiguous publication stays stopped under its
original identity with no recovery (Release 2), the receipt is replicated only into the local signed
journal (off-host replication is Release 2), and a remote tip that moves between the publication and
the re-read leaves the landing unconfirmed rather than inferred. Standard library only.

EXPLICIT COORDINATES. The store connection, the domain, the repository, the executor's configuration
path and receiver, the lander's effect identity and key, the floor authority and the destination root
of the projection are arguments; nothing is routed from the current directory or a module's ROOT.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time


def _sibling(name):
    spec = importlib.util.spec_from_file_location('veldo_landing_' + name, Path(__file__).resolve().with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_git_process = _sibling('git_process')
CC = _sibling('completion_contract')
PJ = _sibling('control_event_projection')
_ORGANS = {}


def _organ(name):
    """A sibling loaded on first use (the executor adapter and the completion reader)."""
    if name not in _ORGANS:
        _ORGANS[name] = _sibling(name)
    return _ORGANS[name]


SCHEMA = 'veldo.landing/v1'
LANDED = 'revision_landed'
RECEIPT_KIND = 'completion_receipt'
EFFECT_KIND = 'protected_effect'
OPERATION = 'record_landing_receipt'
WRITES = ('entities', 'journal', 'commands', 'nonces')
STATION = 'land'
LANDING_REF = 'refs/veldo/landing/'
MANIFEST_PATH = 'proof/%s/manifest.json'
# Release 1: the receipt is committed in the local signed journal; off-host replication is Release 2.
REPLICATION = 'local-journal'
BINDINGS = ('domain_uuid', 'repository_uuid', 'unit', 'station', 'sandbox', 'dispatch_id', 'kind', 'target')
SUBJECT_FIELDS = ('tree', 'source', 'proof', 'dependencies')
GIT_SECONDS = 120
TAXONOMY = ('invalid_input', 'missing_authority', 'stale_subject', 'unavailable_service', 'missing_evidence',
            'unknown_outcome')
ALIASES = {'binding_mismatch': 'stale_subject', 'stale_authority': 'stale_subject', 'not_handed_off': 'missing_authority',
           'unresolved_dependency': 'missing_evidence'}
# The executor's conclusive refusals, by the class each is (a refusal made before anything was pushed).
EXECUTOR_REFUSALS = {'stale-subject': 'stale_subject', 'missing-evidence': 'missing_evidence',
                     'missing-authority': 'missing_authority', 'foreign-authority': 'missing_authority',
                     'unauthenticated-worker': 'missing_authority', 'revoked': 'missing_authority',
                     'revoked-reviewer': 'missing_authority', 'stale-authority': 'stale_subject',
                     'stale-handle': 'stale_subject', 'expired-contract': 'stale_subject',
                     'effect-service-unavailable': 'unavailable_service'}


def taxonomy(code):
    """The error class of a refusal code; a code with no class is an unknown outcome, never success."""
    head = str(code).split(':', 1)[0]
    head = ALIASES.get(head, head)
    return head if head in TAXONOMY else 'unknown_outcome'


def executor_code(refusal, where='publication'):
    """The named refusal of an executor answer: its class, where it was made, and the executor's word."""
    word = refusal if isinstance(refusal, str) and refusal else 'unanswered'
    return '%s:%s/%s' % (EXECUTOR_REFUSALS.get(word, 'invalid_input'), where, word)


class Refused(Exception):
    """A named refusal. `codes` holds every reason, `code` the first."""

    def __init__(self, codes, detail=''):
        codes = [codes] if isinstance(codes, str) else list(dict.fromkeys(codes))
        super().__init__('%s: %s' % (codes[0], detail) if detail else codes[0])
        self.codes, self.code, self.detail = codes, codes[0], detail


def _text(value):
    return isinstance(value, str) and value.strip() != ''


def _hex(value):
    return isinstance(value, str) and len(value) in (40, 64) and set(value) <= set('0123456789abcdef')


def _digest(body):
    return 'sha256:' + hashlib.sha256(body).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def _unit_id(unit):
    if isinstance(unit, dict):
        return unit.get('spec') if _text(unit.get('spec')) else None
    return unit if _text(unit) else None


def receipt_id(unit, dispatch):
    """The confirmed-landing receipt's identity: one landing of one unit through one dispatch."""
    return 'receipt:%s:%s:%s' % (LANDED, unit, hashlib.sha256(dispatch.encode()).hexdigest()[:16])


def _same_place(a, b):
    """Whether two remote addresses name the same destination: equal, or the same local path."""
    if a == b:
        return True
    local = [isinstance(x, str) and '://' not in x and not (':' in x.split('/', 1)[0]) for x in (a, b)]
    return all(local) and os.path.realpath(a) == os.path.realpath(b)


def _receipt_transition(store, params, before):
    """The one write of a confirmed landing: the receipt, only while the publication it names is still
    the confirmed publication of exactly this unit and dispatch, the unit is still at the receipt's
    revision, and no receipt of this landing exists."""
    refused = store.StoreRefused
    rid, eid, sid = params['receipt_id'], params['effect_id'], params['unit']
    receipt = params['receipt']
    landing = receipt.get('publication_receipt') or {}
    effect = before.get(eid)
    if rid in before:
        raise refused('transition_refused', 'the landing already has its receipt')
    if not effect or effect.get('kind') != EFFECT_KIND or effect.get('version') != params['effect_version']:
        raise refused('transition_refused', 'the publication is not the one confirmed')
    data = effect.get('data') or {}
    payload = data.get('payload') or {}
    if (data.get('kind') != 'publication' or data.get('dispatch_id') != params['dispatch'] or data.get('unit') != sid
            or (data.get('domain_uuid'), data.get('repository_uuid')) != (params['domain'], params['repository'])
            or not PJ.confirmed(data) or payload.get('commit') != landing.get('candidate_commit')
            or payload.get('old_tip') != landing.get('old_remote_tip') or landing.get('dispatch_id') != params['dispatch']
            or landing.get('unit_id') != sid):
        raise refused('transition_refused', 'the receipt does not name the confirmed publication')
    unit = before.get(sid) or {}
    if unit.get('kind') != 'execution_unit' or (unit.get('data') or {}).get('revision') != (receipt.get('subject') or {}).get('revision'):
        raise refused('transition_refused', 'the unit is not at the receipt\'s revision')
    return {rid: {'kind': RECEIPT_KIND, 'data': receipt}}


class Landing:
    """The exact-tip publication and confirmed completion of one repository's landings.

    store, conn   control_store and the lander's trusted writer connection to it.
    domain, repository  the coordinates; the executor's configuration must name the same ones and the
                  same store.
    effects       the VELDO-0028 executor's configuration path (installed outside every worker clone);
                  target the publication receiver in it (its trusted clone, remote and ref).
    principal, connection_key  the lander's effect identity and the private key it authenticates with.
    floor         the VELDO-0049 floor authority (record(unit) -> the unit's floor record).
    events_root   the repository whose .veldo/events.jsonl the VELDO-0051 projection publishes.
    signer, sign  the journal signer of this service's commands; generation the authority generation.
    call          the executor adapter (control_effect_executor.call by default).
    observe       receives one record per operation."""

    def __init__(self, store, conn, *, domain, repository, effects, target, principal, connection_key,
                 floor, events_root, signer, sign, generation=1, call=None, observe=None, clock=None,
                 deadline_seconds=600, reviewer_group='review', worker_group='landing'):
        if not all(_text(v) for v in (domain, repository, target, principal, signer)):
            raise Refused('invalid_input:coordinates', 'the domain, repository, receiver, principal and signer are named')
        self.store, self.conn = store, conn
        self.domain, self.repository, self.target, self.principal = domain, repository, target, principal
        self.connection_key, self.floor = connection_key, floor
        self.signer, self.sign, self.generation = signer, sign, generation
        self.events_root = str(events_root)
        self.observe = observe or (lambda event: None)
        self.clock = clock or time.time
        self.deadline_seconds = deadline_seconds
        self.reviewer_group, self.worker_group = reviewer_group, worker_group
        self.counts = {'accepted': 0, 'refused': 0}
        self.config_path = str(effects)
        try:
            config = json.loads(Path(effects).read_text())
            receiver = config['receivers'][target]
        except (OSError, ValueError, KeyError, TypeError):
            raise Refused('invalid_input:effects', 'the executor configuration names no such receiver') from None
        self.database = [path for _, name, path in conn.execute('PRAGMA database_list') if name == 'main'][0]
        if not _text(config.get('store')) or os.path.realpath(config['store']) != os.path.realpath(self.database):
            raise Refused('invalid_input:effects/store', 'the executor records into another store')
        if (config.get('domain_uuid'), config.get('repository_uuid')) != (domain, repository):
            raise Refused('missing_authority:effects/coordinates', 'the executor serves another domain or repository')
        if (not isinstance(receiver, dict) or receiver.get('kind') != 'publication' or 'argv' in receiver
                or not all(_text(receiver.get(k)) for k in ('repository', 'remote', 'ref'))):
            raise Refused('invalid_input:effects/receiver', 'the receiver is not a Git publication')
        self.clone, self.remote, self.ref = receiver['repository'], receiver['remote'], receiver['ref']
        self.call = call or _organ('control_effect_executor').call
        store = self.store
        conn.command_registry[OPERATION] = {'transition': lambda params, before: _receipt_transition(store, params, before),
                                            'writes': WRITES}

    # Reads.

    def _row(self, identity):
        row = self.conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
        return {'id': identity, 'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None

    def _kind(self, kind):
        return [{'id': i, 'version': v, 'digest': d, 'data': json.loads(t)} for i, v, d, t in self.conn.execute(
            'SELECT id, version, digest, data FROM entities WHERE kind=? ORDER BY id', (kind,))]

    def _effect(self, dispatch):
        row = self._row('effect:' + dispatch)
        return row if row and row['kind'] == EFFECT_KIND else None

    def _outstanding(self, sid):
        """The dispatches of this unit's publications with no conclusive answer: neither confirmed nor
        refused before anything reached a destination."""
        out = []
        for row in self._kind(EFFECT_KIND):
            d = row['data']
            if (d.get('kind') == 'publication' and d.get('unit') == sid and d.get('domain_uuid') == self.domain
                    and d.get('repository_uuid') == self.repository and d.get('status') != 'refused'
                    and not PJ.confirmed(d)):
                out.append(d.get('dispatch_id'))
        return out

    def _gate(self):
        EL = _organ('control_eligibility')
        return EL.Gate(self.store, self.conn, domain_uuid=self.domain, repository_uuid=self.repository, workspace=None)

    def _git(self, repo, *args, profile='isolated', text=True):
        try:
            return _git_process.run(['git', '-C', str(repo), *args], capture_output=True, text=text, timeout=GIT_SECONDS,
                                    stdin=subprocess.DEVNULL, profile=profile)
        except (OSError, subprocess.SubprocessError) as error:
            raise Refused('unavailable_service:git/' + args[0], type(error).__name__) from None

    def _tree(self, repo, commit):
        found = self._git(repo, 'rev-parse', '--verify', '--quiet', commit + '^{tree}')
        return found.stdout.strip() if found.returncode == 0 else None

    def _ancestor(self, repo, older, newer):
        return self._git(repo, 'merge-base', '--is-ancestor', older, newer).returncode == 0

    def _manifest(self, repo, sid, evidence):
        """(digest, manifest) of the unit's proof manifest at the evidence commit, from Git."""
        found = self._git(repo, 'cat-file', 'blob', '%s:%s' % (evidence, MANIFEST_PATH % sid), text=False)
        if found.returncode:
            return None, None
        try:
            manifest = json.loads(found.stdout)
        except ValueError:
            manifest = None
        return _digest(found.stdout), manifest if isinstance(manifest, dict) else None

    def _observation(self, candidate):
        """(observation, reference) of the gate's external observation the candidate names, its bytes
        checked against the recorded digest."""
        reference = (candidate.get('gate') or {}).get('observation')
        if not isinstance(reference, dict) or not _text(reference.get('path')):
            raise Refused('missing_evidence:gate/observation')
        try:
            body = Path(reference['path']).read_bytes()
        except OSError:
            raise Refused('missing_evidence:gate/observation') from None
        if _digest(body) != reference.get('digest'):
            raise Refused('binding_mismatch:gate/observation')
        try:
            observation = json.loads(body)
        except ValueError:
            raise Refused('invalid_input:gate/observation') from None
        return observation, reference

    def _handoff(self, sid):
        record = self.floor.record(sid) if self.floor is not None else None
        if not isinstance(record, dict):
            raise Refused('missing_authority:floor_record')
        if record.get('state') != 'handoff':
            raise Refused('not_handed_off:%s' % record.get('state'))
        return record.get('handoff') or {}

    def _remote_tip(self):
        """The remote's own answer now: the commit the receiver's ref holds there, or None."""
        found = self._git(self.clone, 'ls-remote', '--', self.remote, self.ref, profile='network')
        if found.returncode:
            return None
        lines = [line.split('\t') for line in found.stdout.splitlines() if line.strip()]
        tips = [value for value, name in lines if name == self.ref]
        return tips[0] if len(tips) == 1 else None

    # The exact subject at the effect boundary (AC2).

    def subject(self, sid, candidate):
        """The exact subject this publication would land, re-read now; Refused naming every difference
        between it and the current authority, approvals, review, proof, tested tree and dependencies."""
        unit = self._row(sid)
        if not unit or unit['kind'] != 'execution_unit' or unit['data'].get('repository_uuid') != self.repository:
            raise Refused('missing_authority:unit')
        data = unit['data']
        codes = []
        authority = self._row('authority:' + self.domain)
        if not authority or authority['data'].get('state') != 'active':
            codes.append('missing_authority:authority')
        elif authority['data'].get('generation') != self.generation:
            codes.append('stale_authority')
        fields = {f: candidate.get(f) for f in ('commit', 'tree', 'watermark', 'evidence', 'implementation')}
        bad = sorted(f for f, v in fields.items() if not _hex(v))
        if bad or not _text((candidate.get('proof') or {}).get('digest')) or not _text(candidate.get('workspace')):
            raise Refused(['invalid_input:candidate/' + f for f in bad] or ['invalid_input:candidate'])
        if not _same_place(candidate.get('remote_url'), self.remote):
            codes.append('missing_authority:publication/remote')
        workspace = candidate['workspace']
        tree = self._tree(workspace, fields['commit'])
        if tree is None or tree != fields['tree']:
            codes.append('stale_subject:candidate/tree')
        if not (self._ancestor(workspace, fields['watermark'], fields['commit'])
                and self._ancestor(workspace, fields['evidence'], fields['commit'])
                and self._ancestor(workspace, fields['implementation'], fields['evidence'])):
            codes.append('stale_subject:candidate/ancestry')
        proof, manifest = self._manifest(workspace, sid, fields['evidence'])
        if proof is None or proof != candidate['proof']['digest']:
            codes.append('binding_mismatch:proof')
        if (manifest or {}).get('commit') != fields['implementation']:
            codes.append('binding_mismatch:proof/implementation')
        try:
            observation, reference = self._observation(candidate)
            tested = (observation.get('candidate') or {}).get('tree')
            if observation.get('commit') != fields['commit']:
                codes.append('binding_mismatch:gate/commit')
            if tested != tree:
                codes.append('binding_mismatch:gate/tree')
            if observation.get('green') is not True:
                codes.append('missing_evidence:gate')
        except Refused as error:
            codes.extend(error.codes)
            reference = None
        handoff = {}
        try:
            handoff = self._handoff(sid)
            if (handoff.get('source') or {}).get('commit') != fields['evidence']:
                codes.append('binding_mismatch:review/source')
            if (handoff.get('proof') or {}).get('digest') != candidate['proof']['digest']:
                codes.append('binding_mismatch:review/proof')
        except Refused as error:
            codes.extend(error.codes)
        dependencies = {}
        gate = self._gate() if data.get('depends_on') else None
        for dep in data.get('depends_on') or []:
            row = self._row(dep)
            if not row or not gate.landed(dep):
                codes.append('unresolved_dependency:' + dep)
            if row:
                dependencies[dep] = {'version': row['version'], 'digest': row['digest']}
        exact = {'tree': tree, 'source': fields['evidence'], 'proof': proof, 'dependencies': dependencies}
        approvals = self._kind('approval')
        for name in data.get('approvals_required') or []:
            granted = [a['data'] for a in approvals if a['data'].get('unit') == sid and a['data'].get('name') == name
                       and a['data'].get('state') == 'granted' and a['data'].get('revision') == data.get('revision')]
            if not granted:
                codes.append('missing_authority:approval/' + name)
                continue
            differences = []
            for approval in granted:
                bound = approval.get('subject') if isinstance(approval.get('subject'), dict) else {}
                differences.append([f for f in SUBJECT_FIELDS if bound.get(f) != exact[f]])
            closest = min(differences, key=len)
            codes.extend('binding_mismatch:approval/%s/%s' % (name, f) for f in closest)
        if codes:
            raise Refused(codes)
        return dict(exact, unit=sid, revision=data.get('revision'), commit=fields['commit'], old_tip=fields['watermark'],
                    implementation=fields['implementation'], observation=reference,
                    reviewers=list(handoff.get('reviewers') or []))

    # The publication (AC1, AC3).

    def _command(self, operation, params, expected):
        body = dict(params, operation=operation)
        command_id = 'landing/' + hashlib.sha256(_canonical(body)).hexdigest()[:32]
        return self.store.execute(self.conn, {'command_id': command_id, 'principal': self.signer, 'operation': operation,
                                              'parameters': params, 'expected_versions': expected,
                                              'artifact_digests': [], 'nonce': command_id + '/nonce'},
                                  self.signer, self.sign, self.generation)

    def _upsert(self, identity, kind, data):
        current = self._row(identity)
        self._command('upsert_entity', {'entity_id': identity, 'kind': kind, 'data': data},
                      {identity: current['version'] if current else 0})
        return self._row(identity)

    def _transfer(self, candidate, dispatch):
        """The candidate's objects into the publication clone, under a ref of this landing's own."""
        ref = LANDING_REF + hashlib.sha256(dispatch.encode()).hexdigest()[:24]
        moved = self._git(candidate['workspace'], 'push', '-q', '--no-verify', str(self.clone),
                          '+%s:%s' % (candidate['commit'], ref))
        if moved.returncode or self._tree(self.clone, candidate['commit']) != candidate['tree']:
            raise Refused('unavailable_service:git/transfer', (moved.stderr or '').strip()[:300])

    def _authorize(self, sid, candidate, dispatch, subject):
        """The VELDO-0028 contract and permission of this dispatch's publication: the exact commit, the
        tested tree and the RECORDED old tip, never a tip read now."""
        now = self.clock()
        cid, pid = 'contract/' + dispatch, 'permit/' + dispatch
        contract = {'domain_uuid': self.domain, 'repository_uuid': self.repository, 'unit': sid, 'station': STATION,
                    'sandbox': candidate.get('id') or 'candidate', 'dispatch_id': dispatch, 'kind': 'publication',
                    'target': self.target, 'worker': self.principal, 'status': 'accepted',
                    'deadline': now + self.deadline_seconds, 'permission_id': pid,
                    'payload': {'commit': subject['commit'], 'tree': subject['tree'], 'old_tip': subject['old_tip']}}
        written = self._upsert(cid, 'effect_contract', contract)
        reviewer = subject['reviewers'][0] if subject['reviewers'] else None
        self._upsert(pid, 'effect_permission', {
            'contract_digest': written['digest'], 'authorized': True, 'obligations': [],
            'expires_at': now + self.deadline_seconds, 'subscription_allowed': False, 'remaining_calls': 0,
            'gate_passed': True, 'gate_tree': subject['tree'], 'review_passed': True, 'reviewer': reviewer,
            'reviewer_group': self.reviewer_group, 'worker_group': self.worker_group, 'approval_current': True,
            'subject_digest': _digest(_canonical({k: subject[k] for k in SUBJECT_FIELDS}))})
        return contract

    def _execute(self, contract):
        """Issue a handle and execute through the executor; its answer is read back from the store."""
        request = {f: contract[f] for f in BINDINGS}
        request.update(contract_id='contract/' + contract['dispatch_id'], operation='issue')
        try:
            issued = self.call(self.config_path, request, self.principal, self.connection_key)
        except Exception as error:  # noqa: BLE001 - an adapter that cannot answer issued nothing
            raise Refused('unavailable_service:effects/issue', type(error).__name__) from None
        if not isinstance(issued, dict) or issued.get('accepted') is not True or not _text(issued.get('handle')):
            raise Refused(executor_code((issued or {}).get('refusal') if isinstance(issued, dict) else None, 'effects'))
        request.update(operation='execute', handle=issued['handle'])
        try:
            return self.call(self.config_path, request, self.principal, self.connection_key)
        except Exception as error:  # noqa: BLE001 - the recorded answer decides, read back below
            return {'accepted': None, 'raised': type(error).__name__}

    def _recorded(self, unit, candidate, dispatch, effect):
        """The recorded answer of this dispatch's publication, which is final: refused is a failed
        publication, anything but a confirmed one a stop; a confirmed one goes on to completion."""
        data = effect['data']
        if data.get('status') == 'refused':
            raise Refused(executor_code(data.get('refusal')), 'the publication was refused before anything was pushed')
        if not PJ.confirmed(data):
            raise Refused('unknown_outcome:publication/' + str(data.get('status')),
                          'stopped under dispatch %s; no further attempt' % dispatch)
        return self.complete(unit, candidate)

    def publish(self, unit, candidate):
        """Publish the accepted candidate of `unit` ({spec, dispatch, ...}) by exact-tip compare-and-swap,
        then complete it. Returns {ok, outcome, refusal, refusals, taxonomy, unit, dispatch, published,
        receipt, projection}: outcome landed, refused (nothing written or moved), failed (the executor
        refused before pushing), or unknown (a stop under the original dispatch)."""
        sid = _unit_id(unit)
        dispatch = unit.get('dispatch') if isinstance(unit, dict) else None
        try:
            if sid is None or not _text(dispatch):
                raise Refused('invalid_input:dispatch', 'the unit and its land dispatch are named')
            if not isinstance(candidate, dict) or candidate.get('unit') != sid:
                raise Refused('invalid_input:candidate', 'the candidate is this unit\'s')
            recorded = self._effect(dispatch)
            if recorded is not None:
                return self._recorded(unit, candidate, dispatch, recorded)
            outstanding = [d for d in self._outstanding(sid) if d != dispatch]
            if outstanding:
                raise Refused('unknown_outcome:publication/outstanding',
                              'publication %s of this unit has no conclusive answer' % outstanding[0])
            subject = self.subject(sid, candidate)
            self._transfer(candidate, dispatch)
            contract = self._authorize(sid, candidate, dispatch, subject)
            answer = self._execute(contract)
            effect = self._effect(dispatch)
            if effect is None:
                # Nothing was accepted, so nothing reached a destination: a conclusive refusal.
                raise Refused(executor_code((answer or {}).get('refusal') if isinstance(answer, dict) else None))
            return self._recorded(unit, candidate, dispatch, effect)
        except Refused as error:
            return self._refuse('publish', sid, dispatch, candidate, error)
        except (self.store.StoreRefused, self.store.sqlite3.Error) as error:
            return self._refuse('publish', sid, dispatch, candidate,
                                Refused('unavailable_service:store', getattr(error, 'code', type(error).__name__)))

    # Completion (AC4).

    def chain(self, sid, candidate, dispatch, effect):
        """Every link of the R76 evidence chain, re-derived from its own authority; Refused naming each
        link that does not hold. The remote's own answer is re-read now."""
        codes = []
        data = effect['data']
        payload = data.get('payload') or {}
        fields = {f: candidate.get(f) for f in ('commit', 'tree', 'watermark', 'evidence', 'implementation')}
        if not all(_hex(v) for v in fields.values()) or not _text((candidate.get('proof') or {}).get('digest')):
            raise Refused('invalid_input:candidate')
        if payload.get('commit') != fields['commit']:
            codes.append('binding_mismatch:landing/candidate')
        if payload.get('old_tip') != fields['watermark']:
            codes.append('binding_mismatch:landing/old_tip')
        if payload.get('tree') != fields['tree']:
            codes.append('binding_mismatch:landing/tree')
        # Git: the publication clone holds every object of the landed candidate.
        if self._tree(self.clone, fields['commit']) != fields['tree']:
            codes.append('stale_subject:candidate/tree')
        proof, manifest = self._manifest(self.clone, sid, fields['evidence'])
        if proof is None or proof != candidate['proof']['digest']:
            codes.append('binding_mismatch:proof')
        if (manifest or {}).get('commit') != fields['implementation']:
            codes.append('binding_mismatch:implementation')
        if not (self._ancestor(self.clone, fields['implementation'], fields['evidence'])
                and self._ancestor(self.clone, fields['evidence'], fields['commit'])
                and self._ancestor(self.clone, fields['watermark'], fields['commit'])):
            codes.append('binding_mismatch:ancestry')
        handoff = {}
        try:
            handoff = self._handoff(sid)
            if (handoff.get('source') or {}).get('commit') != fields['evidence']:
                codes.append('binding_mismatch:review/source')
            if (handoff.get('proof') or {}).get('digest') != candidate['proof']['digest']:
                codes.append('binding_mismatch:review/proof')
        except Refused as error:
            codes.extend(error.codes)
        observation, reference = {}, {}
        try:
            observation, reference = self._observation(candidate)
            if observation.get('commit') != fields['commit'] or observation.get('green') is not True:
                codes.append('binding_mismatch:gate/commit')
            if (observation.get('candidate') or {}).get('tree') != fields['tree']:
                codes.append('binding_mismatch:gate/tree')
        except Refused as error:
            codes.extend(error.codes)
        tip = self._remote_tip()
        if tip != fields['commit']:
            codes.append('unknown_outcome:confirmation')
        if codes:
            raise Refused(codes)
        scrub = getattr(_organ('control_effect_executor'), 'scrubbed_url', lambda url: url)
        confirmation = {'remote': scrub(self.remote), 'ref': self.ref, 'commit': tip, 'read_at': self.clock()}
        return {
            'implementation_commit': fields['implementation'], 'proof_digest': candidate['proof']['digest'],
            'reviewed_source_digest': _digest(_canonical(handoff.get('source') or {})),
            'reviewed_source': (handoff.get('source') or {}).get('commit'),
            'reviewed_proof_digest': (handoff.get('proof') or {}).get('digest'),
            'reviewers': list(handoff.get('reviewers') or []),
            'old_remote_tip': fields['watermark'], 'candidate_commit': fields['commit'], 'tested_tree': fields['tree'],
            'evidence_commit': fields['evidence'],
            'gate_invocation': {'observation_digest': reference.get('digest'), 'command': observation.get('command'),
                                'verifier': (observation.get('gate') or {}).get('digest')},
            'gate_output_location': reference.get('path'),
            'unit_id': sid, 'dispatch_id': dispatch, 'remote_confirmation': confirmation,
            'replication_receipt': REPLICATION,
            'publication_effect': {'id': effect['id'], 'version': effect['version'], 'digest': effect['digest'],
                                   'evidence': data.get('evidence')}}

    def complete(self, unit, candidate):
        """Commit the confirmed-landing receipt of `unit`'s dispatch, then run the VELDO-0051 projection.
        Only a publication the executor recorded as completed at every destination, re-read at the
        remote as the exact candidate, with every link of its evidence chain holding, completes."""
        sid = _unit_id(unit)
        dispatch = unit.get('dispatch') if isinstance(unit, dict) else None
        try:
            if sid is None or not _text(dispatch) or not isinstance(candidate, dict):
                raise Refused('invalid_input:dispatch')
            effect = self._effect(dispatch)
            if effect is None:
                raise Refused('missing_evidence:publication', 'dispatch %s published nothing' % dispatch)
            data = effect['data']
            if data.get('status') == 'refused':
                raise Refused(executor_code(data.get('refusal')))
            if not PJ.confirmed(data):
                raise Refused('unknown_outcome:publication/' + str(data.get('status')))
            if (data.get('kind') != 'publication' or data.get('dispatch_id') != dispatch or data.get('unit') != sid
                    or (data.get('domain_uuid'), data.get('repository_uuid')) != (self.domain, self.repository)):
                raise Refused('binding_mismatch:publication/unit', 'dispatch %s published another unit' % dispatch)
            unit_row = self._row(sid)
            if not unit_row or unit_row['kind'] != 'execution_unit':
                raise Refused('missing_authority:unit')
            rid = receipt_id(sid, dispatch)
            existing = self._row(rid)
            if existing is None:
                landing = self.chain(sid, candidate, dispatch, effect)
                subject = {'id': sid, 'revision': unit_row['data'].get('revision')}
                receipt = {'fact': LANDED, 'subject': subject, 'publication_receipt': landing,
                           'remote_confirmation': landing['remote_confirmation'], 'replicated': REPLICATION,
                           'spec_shipped_event': PJ.shipped_event_id(self.domain, self.repository, sid, dispatch)}
                problems = CC.fact_problems(LANDED, receipt, subject) + CC.landing_receipt_problems(landing)
                if problems:
                    raise Refused('invalid_input:receipt', '; '.join(problems))
                self._command(OPERATION, {'receipt_id': rid, 'receipt': receipt, 'effect_id': effect['id'],
                                          'effect_version': effect['version'], 'unit': sid, 'dispatch': dispatch,
                                          'domain': self.domain, 'repository': self.repository},
                              {rid: 0, effect['id']: effect['version'], sid: unit_row['version']})
            projection = self.project()
        except Refused as error:
            return self._refuse('complete', sid, dispatch, candidate, error)
        except (self.store.StoreRefused, self.store.sqlite3.Error) as error:
            return self._refuse('complete', sid, dispatch, candidate,
                                Refused('unavailable_service:store', getattr(error, 'detail', type(error).__name__)))
        self.counts['accepted'] += 1
        self._emit('complete', sid, dispatch, candidate, outcome='accepted', receipt=rid, projection=projection)
        return {'ok': True, 'outcome': 'landed', 'unit': sid, 'dispatch': dispatch, 'published': True,
                'receipt': rid, 'projection': projection, 'refusal': None, 'refusals': []}

    def project(self):
        """Run the VELDO-0051 projection over the journal into the destination's event log."""
        try:
            report = PJ.Projection(self.store, self.database, domain=self.domain, repository=self.repository,
                                   root=self.events_root, observe=self.observe).publish()
        except PJ.Refused as error:
            return {'refused': error.code, 'taxonomy': PJ.taxonomy(error.code)}
        return {'watermark': report['watermark'], 'published': report['published'], 'duplicates': report['duplicates']}

    # Observability.

    def _refuse(self, operation, sid, dispatch, candidate, error):
        self.counts['refused'] += 1
        effect = self._effect(dispatch) if _text(dispatch) else None
        status = (effect or {}).get('data', {}).get('status')
        published = True if effect and PJ.confirmed(effect['data']) else (False if effect is None or status == 'refused' else None)
        kind = taxonomy(error.code)
        outcome = 'unknown' if kind == 'unknown_outcome' else ('failed' if status == 'refused' else 'refused')
        self._emit(operation, sid, dispatch, candidate, outcome=outcome, refusal=error.code, refusals=error.codes,
                   taxonomy=kind, detail=error.detail)
        return {'ok': False, 'outcome': outcome, 'unit': sid, 'dispatch': dispatch, 'published': published,
                'refusal': error.code, 'refusals': list(error.codes), 'taxonomy': kind, 'detail': error.detail,
                'receipt': None}

    def _emit(self, operation, sid, dispatch, candidate, **fields):
        c = candidate if isinstance(candidate, dict) else {}
        self.observe(dict({'schema': SCHEMA, 'operation': operation, 'domain': self.domain,
                           'repository': self.repository, 'unit': sid, 'request': dispatch,
                           'accepted_versions': {k: c.get(k) for k in ('watermark', 'commit', 'tree') if c.get(k)}},
                          **fields))

    def status(self):
        """Metrics: accepted and refused operations, the publications of this repository with no
        conclusive answer (pending, each a stop), and the landings not yet projected."""
        pending = sorted(row['data'].get('dispatch_id') for row in self._kind(EFFECT_KIND)
                         if row['data'].get('kind') == 'publication' and row['data'].get('repository_uuid') == self.repository
                         and row['data'].get('status') != 'refused' and not PJ.confirmed(row['data']))
        try:
            unprojected = PJ.Projection(self.store, self.database, domain=self.domain, repository=self.repository,
                                        root=self.events_root).status()['pending_events']
        except PJ.Refused as error:
            unprojected = [error.code]
        return dict(self.counts, pending=pending, unprojected=unprojected)
