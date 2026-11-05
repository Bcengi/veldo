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
     payload commit, tree, old tip and the unit revision the approvals were checked for, the old tip
     being the candidate's recorded watermark, never a tip read now;
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
     further attempt. Only a completed publication goes on to completion. A publication refused
     because another push moved the trunk (VELDO-0148: `stale-subject` at the listing, `trunk-moved`
     after it) names the watermark, the tip found now and that classification; it ends this dispatch,
     and the land station (control_landing_station) re-lands the unit under a new one. A refusal of
     the subject for a missing grant alone names the exact subject a fresh grant would be bound to.

Landing.complete then decides success from the remote's own answer, re-read from the remote now (the
receiver's ref must be exactly the candidate commit), re-derives every link of the R76 evidence chain
from its own authority (the implementation commit and proof digest from Git, the reviewed source and
proof digests from the floor, the old tip, candidate and tree from the recorded publication, the tested
tree from the gate observation, and the publication record itself as the final receipt), and commits
the revision_landed completion receipt for the exact unit and dispatch in ONE store transaction whose
transition refuses unless the publication it names is still the confirmed one, the receipt's revision
is the revision that publication carries, and the unit is still at it. A unit whose revision moved
after its publication refuses by name (stale_subject:landing/revision) and writes nothing: the receipt
is always about the revision that was approved and published, never the revision current at
completion. Only then does it run the VELDO-0051 projection (control_event_projection), which alone
derives spec.shipped from that receipt; a refused projection makes the completion not ok, named.

THE LANDING DESTINATION (VELDO-0235). Each landing runs under its project's landing destination
(control_project.landing_destination, land_and_push when the record has none). land_and_push is every
step above, byte for byte. land_locally keeps every check before publication (step 2) and replaces steps
3 to 5 and the remote re-read: the candidate's objects are copied into the project's own repository (the
land configuration's `repository`) with pack-objects and unpack-objects, the publication is a
compare-and-swap of its local refs/heads/<trunk> from the recorded watermark (its local tip when the
candidate was built) to the candidate commit (`git update-ref <ref> <new> <old>`, atomic under the ref
lock), recorded by this module as the dispatch's publication `effect:<dispatch>` (accepted before the swap,
then completed with its one destination at the tip, or refused), and completion re-reads that local ref and
commits the same revision_landed receipt. No remote is listed, fetched or pushed, the executor is not
called and no push credential is read. A local trunk that moved after the watermark is a refused
publication, `stale-subject` when found before the swap and `trunk-moved` when the swap itself loses, so the
land station re-lands it (VELDO-0148), and the moved trunk is never overwritten. The destination is bound:
an approval whose subject names another destination (one without the field names land_and_push) refuses
the publication as stale_subject:landing/destination, as does a destination changed since the land
dispatch began; when that and an older tree are all a grant lacks, the refusal names the exact subject a
fresh grant binds, its destination included for land_locally.

A CHECKED-OUT TRUNK (VELDO-0260). Before the swap, a local landing reads the repository's own working-tree list
(`git worktree list --porcelain -z`) and takes every working tree, the main one and every linked one, whose HEAD
is the symbolic ref refs/heads/<trunk>; a detached HEAD, another branch and a bare repository are not taken. The
set, each tree's path and whether it was clean, is recorded in the accepted publication effect. Clean means no
staged or unstaged change to a tracked file and no merge, rebase or cherry-pick in progress; a tree that is not
clean refuses the publication before anything moves as trunk_checkout_dirty:<working tree>, its local changes
named by path and count, never by content. Each clean tree is then moved from the old tip to the candidate by a
two-tree merge (`git read-tree -m -u <old> <new>`), which touches only the files the two commits differ in and
leaves untracked and ignored files as they were, and the ref is swapped. A tree that cannot be moved (its index
locked, a file that cannot be written) refuses as trunk_checkout_unmovable:<working tree>, and a swap that loses
(trunk-moved) puts every tree it moved back on the old tip. Both refusals end the land dispatch as trunk_moved,
so the land station re-lands it (VELDO-0148), and each carries the brief the owner reads: the working tree, and
that the landing waits until it is clean. A repository where no tree has the trunk checked out lands exactly as
above, with no working tree read or written.

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
           'unresolved_dependency': 'missing_evidence', 'trunk_checkout_dirty': 'stale_subject',
           'trunk_checkout_unmovable': 'unavailable_service'}
# The executor's conclusive refusals, by the class each is (a refusal made before anything was pushed).
EXECUTOR_REFUSALS = {'stale-subject': 'stale_subject', 'missing-evidence': 'missing_evidence',
                     'missing-authority': 'missing_authority', 'foreign-authority': 'missing_authority',
                     'unauthenticated-worker': 'missing_authority', 'revoked': 'missing_authority',
                     'revoked-reviewer': 'missing_authority', 'stale-authority': 'stale_subject',
                     'stale-handle': 'stale_subject', 'expired-contract': 'stale_subject',
                     'effect-service-unavailable': 'unavailable_service', 'trunk-moved': 'stale_subject'}
# VELDO-0148: the executor's refusals that mean another push moved the trunk: at its listing (the trunk no
# longer at the watermark) or between the listing and the push (the lease lost to a commit that does not
# contain the candidate). A publication refused so is followed by a re-land (control_landing_station).
TRUNK_MOVED = ('stale-subject', 'trunk-moved')
# VELDO-0260: a local publication refused for a working tree that has the trunk checked out: one with local
# changes, or one that cannot be moved. Each is re-landed under VELDO-0148 as a trunk that moved is.
CHECKOUT_DIRTY, CHECKOUT_UNMOVABLE = 'trunk_checkout_dirty', 'trunk_checkout_unmovable'
CHECKOUT_REFUSALS = (CHECKOUT_DIRTY, CHECKOUT_UNMOVABLE)
RELAND = TRUNK_MOVED + CHECKOUT_REFUSALS
# The operations in progress that make a working tree not clean, by the marker each leaves in its Git directory.
IN_PROGRESS = (('merge', 'MERGE_HEAD'), ('rebase', 'rebase-merge'), ('rebase', 'rebase-apply'),
               ('cherry-pick', 'CHERRY_PICK_HEAD'))
# The changed paths a record names at most (their count is always whole).
CHANGED_PATHS = 20
# VELDO-0235: the two landing destinations a project names, the refusal of an approval or a land bound to another
# one, and the command that records a local publication.
LAND_AND_PUSH, LAND_LOCALLY = 'land_and_push', 'land_locally'
DESTINATIONS = (LAND_AND_PUSH, LAND_LOCALLY)
DESTINATION_CODE = 'stale_subject:landing/destination'
LOCAL_OPERATION = 'record_local_publication'
# The refusals of the subject that only a grant for the re-merged tree (or, VELDO-0235, for the project's
# current destination) answers (VELDO-0148 AC3).
APPROVAL_CODES = ('binding_mismatch:approval/', DESTINATION_CODE)


def destination_words(destination, remote=None, trunk=None):
    """The destination as the owner reads it in every landing brief and the project view (VELDO-0235)."""
    if destination == LAND_LOCALLY:
        return 'land locally on %s, nothing pushed' % (trunk or 'the trunk')
    return 'land and push to %s' % (remote or 'the remote')


def unit_project(conn, unit):
    """The project record of an execution unit, read on `conn`: its `project` name, or the end of its chain
    (backlog item, objective, project_uuid). (name, data) or (None, None)."""
    def row(identity):
        found = conn.execute('SELECT kind, data FROM entities WHERE id=?', (identity,)).fetchone() if _text(identity) else None
        return (found[0], json.loads(found[1])) if found else (None, None)
    kind, data = row(unit)
    data = data if kind == 'execution_unit' and isinstance(data, dict) else {}
    name = data.get('project') if _text(data.get('project')) else None
    if name is None:
        kind, item = row(data.get('backlog_item_uuid'))
        kind, objective = row((item or {}).get('objective_uuid')) if kind == 'backlog_item' else (None, None)
        pid = (objective or {}).get('project_uuid') if kind == 'objective' else None
        name = pid[len('project:'):] if _text(pid) and pid.startswith('project:') else None
    kind, project = row('project:' + name) if name else (None, None)
    return (name, project) if kind == 'project' and isinstance(project, dict) else (name, None)


def unit_destination(conn, unit):
    """{project, destination, command_id}: the landing destination of the unit's project now (land_and_push
    when it has no project record or the record names none) and the command that last set it."""
    name, project = unit_project(conn, unit)
    # The project service's own reading of its record, the one place a record without the field is read.
    value = _organ('control_project').landing_destination(project or {})
    changes = (project or {}).get('landing_destination_history') or []
    return {'project': name, 'destination': value if value in DESTINATIONS else None,
            'command_id': (changes[-1] or {}).get('command_id') if changes else None}


def binding(subject):
    """What an approval binds of a subject: its SUBJECT_FIELDS, and its destination when that is land_locally
    (a binding without one names land_and_push, so today's grants keep their bytes)."""
    bound = {f: subject.get(f) for f in SUBJECT_FIELDS}
    if subject.get('destination', LAND_AND_PUSH) != LAND_AND_PUSH:
        bound['destination'] = subject['destination']
    return bound


def binding_differences(bound, exact):
    """The fields an approval's bound subject differs from the exact one in, `destination` among them."""
    bound = bound if isinstance(bound, dict) else {}
    found = [f for f in SUBJECT_FIELDS if bound.get(f) != exact.get(f)]
    if bound.get('destination', LAND_AND_PUSH) != exact.get('destination', LAND_AND_PUSH):
        found.append('destination')
    return found


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


def checkout_outcome(data):
    """VELDO-0260: the working-tree outcome of one local publication record, or None for any other: none checked
    out, moved with the trunk, refused for local changes, refused as unmovable, restored after a lost swap, or left
    (refused for another reason before anything moved)."""
    if not isinstance(data, dict) or data.get('destination_kind') != LAND_LOCALLY or not isinstance(data.get('checkouts'), list):
        return None
    trees = data['checkouts']
    if data.get('refusal') == CHECKOUT_DIRTY:
        return 'refused_local_changes'
    if data.get('refusal') == CHECKOUT_UNMOVABLE:
        return 'refused_unmovable'
    if any(c.get('outcome') == 'restored' for c in trees):
        return 'restored_after_lost_swap'
    if not trees:
        return 'none_checked_out'
    if data.get('status') == 'completed' and all(c.get('outcome') == 'moved' for c in trees):
        return 'moved_with_trunk'
    return 'left' if data.get('status') == 'refused' else None


def checkout_brief(word, tree, trunk, changes=None, reason=None):
    """VELDO-0260: the landing brief the owner reads for a refusal of a working tree that has the trunk checked out."""
    if word == CHECKOUT_DIRTY:
        changes = changes or {}
        why = 'has %s checked out with local changes (%d %s: %s)' % (
            trunk, changes.get('count') or 0, 'file' if changes.get('count') == 1 else 'files',
            ', '.join(changes.get('paths') or []) or 'an operation in progress')
    else:
        why = 'has %s checked out and cannot be moved with it (%s)' % (trunk, reason or 'unknown')
    return ('The working tree %s %s. Nothing moved: the landing waits until it is clean and is re-landed then.'
            % (tree, why))


def _local_transition(store, params, before):
    """VELDO-0235: the record of a local publication, `effect:<dispatch>`: `accept` writes it before the swap,
    while nothing is recorded under the dispatch; `finish` ends that accepted record, completed with its one
    destination at the tip or refused, and nothing else."""
    refused = store.StoreRefused
    eid, data, action = params.get('effect_id'), params.get('data'), params.get('action')
    current = before.get(eid)
    if not isinstance(data, dict) or data.get('kind') != 'publication' or data.get('destination_kind') != LAND_LOCALLY \
            or eid != 'effect:' + str(data.get('dispatch_id')):
        raise refused('transition_refused', 'a local publication of one dispatch')
    if action == 'accept':
        if current is not None or data.get('status') != 'accepted':
            raise refused('transition_refused', 'the dispatch already has a publication')
    elif action == 'finish':
        held = (current or {}).get('data') or {}
        if (not current or current.get('kind') != EFFECT_KIND or held.get('status') != 'accepted'
                or held.get('destination_kind') != LAND_LOCALLY or data.get('status') not in ('completed', 'refused')
                or {k: held.get(k) for k in ('dispatch_id', 'unit', 'domain_uuid', 'repository_uuid', 'payload', 'local')}
                != {k: data.get(k) for k in ('dispatch_id', 'unit', 'domain_uuid', 'repository_uuid', 'payload', 'local')}):
            raise refused('transition_refused', 'not the accepted local publication of this dispatch')
    else:
        raise refused('transition_refused', 'accept or finish')
    return {eid: {'kind': EFFECT_KIND, 'data': data}}


def _receipt_transition(store, params, before):
    """The one write of a confirmed landing: the receipt, only while the publication it names is still
    the confirmed publication of exactly this unit and dispatch, the receipt's revision is the one that
    publication carries, the unit is still at it, and no receipt of this landing exists."""
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
    revision = (receipt.get('subject') or {}).get('revision')
    if revision != payload.get('revision'):
        raise refused('transition_refused', 'the receipt is not about the revision that was published')
    unit = before.get(sid) or {}
    if unit.get('kind') != 'execution_unit' or (unit.get('data') or {}).get('revision') != revision:
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
    observe       receives one record per operation.
    destination   VELDO-0235: the project's landing destination this landing runs under (land_and_push by
                  default); with land_locally, `local` names the project's repository and its trunk."""

    def __init__(self, store, conn, *, domain, repository, effects, target, principal, connection_key,
                 floor, events_root, signer, sign, generation=1, call=None, observe=None, clock=None,
                 deadline_seconds=600, reviewer_group='review', worker_group='landing', destination=LAND_AND_PUSH,
                 local=None):
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
        if destination not in DESTINATIONS:
            raise Refused('invalid_input:landing_destination', 'land_and_push or land_locally')
        self.destination = destination
        if destination == LAND_LOCALLY:
            # The project's own repository and its local trunk are the publication's one destination.
            if not isinstance(local, dict) or not all(_text(local.get(k)) for k in ('repository', 'trunk')):
                raise Refused('invalid_input:landing_destination/local', 'the repository and trunk a local landing moves')
            self.clone, self.remote, self.ref = str(local['repository']), None, 'refs/heads/' + local['trunk']
            self.trunk = local['trunk']
        self.call = call or _organ('control_effect_executor').call
        store = self.store
        conn.command_registry[OPERATION] = {'transition': lambda params, before: _receipt_transition(store, params, before),
                                            'writes': WRITES}
        conn.command_registry[LOCAL_OPERATION] = {
            'transition': lambda params, before: _local_transition(store, params, before), 'writes': WRITES}

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

    def _git(self, repo, *args, profile='isolated', text=True, push_identity=None, remote_url=None):
        try:
            return _git_process.run(['git', '-C', str(repo), *args], capture_output=True, text=text, timeout=GIT_SECONDS,
                                    stdin=subprocess.DEVNULL, profile=profile,
                                    push_identity=push_identity, remote_url=remote_url)
        except ValueError as error:
            raise Refused(getattr(error, 'code', 'invalid_input:git_profile')) from None
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
        identities = _organ('control_git_identity')
        try:
            identity = identities.resolve(self.conn, self.domain, self.repository)
        except identities.Refused as error:
            raise Refused(error.code) from None
        remote = self.remote
        if '://' not in remote and not remote.startswith('git@'):
            configured = self._git(self.clone, 'config', '--get-all', 'remote.' + remote + '.pushurl')
            if configured.returncode == 1:
                configured = self._git(self.clone, 'config', '--get-all', 'remote.' + remote + '.url')
            targets = configured.stdout.splitlines()
            if configured.returncode or len(targets) != 1:
                raise Refused('invalid_input:push_destinations')
            remote = targets[0]
        found = self._git(self.clone, 'ls-remote', '--', remote, self.ref, profile='identity',
                          push_identity=identity, remote_url=remote)
        if found.returncode:
            return None
        lines = [line.split('\t') for line in found.stdout.splitlines() if line.strip()]
        tips = [value for value, name in lines if name == self.ref]
        return tips[0] if len(tips) == 1 else None

    def _local_tip(self):
        """VELDO-0235: the commit the project's local trunk holds now, or None."""
        found = self._git(self.clone, 'rev-parse', '--verify', '--quiet', self.ref + '^{commit}')
        value = found.stdout.strip()
        return value if found.returncode == 0 and _hex(value) else None

    def _checkouts(self):
        """VELDO-0260: every working tree of the project's repository whose HEAD is the symbolic ref of the trunk,
        from the repository's own working-tree list, each with whether it is clean against its HEAD: no staged or
        unstaged change to a tracked file and no merge, rebase or cherry-pick in progress. Local changes are named
        by path and count, never by content."""
        listed = self._git(self.clone, 'worktree', 'list', '--porcelain', '-z')
        if listed.returncode:
            raise Refused('unavailable_service:git/worktree', (listed.stderr or '')[:300])
        entries, entry = [], {}
        for field in listed.stdout.split('\0'):
            if not field:
                if entry:
                    entries.append(entry)
                entry = {}
                continue
            key, _, value = field.partition(' ')
            entry[key] = value
        if entry:
            entries.append(entry)
        found = []
        for entry in entries:
            if 'bare' in entry or entry.get('branch') != self.ref or not _text(entry.get('worktree')):
                continue
            found.append(self._checkout_state(entry['worktree']))
        return found

    def _checkout_state(self, path):
        """VELDO-0260: one working tree holding the trunk: its path, whether it is clean, and what makes it not."""
        state = {'path': path}
        status = self._git(path, '--no-optional-locks', 'status', '--porcelain=v1', '-z', '--untracked-files=no',
                           '--ignore-submodules=none')
        if status.returncode:
            state.update(clean=None, reason='status: ' + (status.stderr or '').strip()[:200])
            return state
        fields, changed, i = status.stdout.split('\0'), [], 0
        while i < len(fields):
            item = fields[i]
            i += 1
            if len(item) < 4:
                continue
            changed.append(item[3:])
            if item[0] in 'RC':
                i += 1
        in_progress = []
        for name, marker in IN_PROGRESS:
            where = self._git(path, 'rev-parse', '--git-path', marker)
            target = where.stdout.strip()
            if where.returncode == 0 and target and os.path.exists(os.path.join(path, target)) and name not in in_progress:
                in_progress.append(name)
        state['clean'] = not changed and not in_progress
        if changed:
            state['changes'] = {'count': len(changed), 'paths': sorted(changed)[:CHANGED_PATHS]}
        if in_progress:
            state['in_progress'] = in_progress
        return state

    def _move_checkout(self, path, old, new):
        """VELDO-0260: move one clean working tree from `old` to `new` by a two-tree merge that touches only the files
        the two commits differ in. None when moved, else why it could not be."""
        self._git(path, 'update-index', '-q', '--refresh')
        moved = self._git(path, 'read-tree', '-m', '-u', old, new)
        return None if moved.returncode == 0 else ((moved.stderr or '').strip()[:200] or 'read-tree failed')

    def _copy_objects(self, candidate):
        """VELDO-0235: every object the candidate holds beyond the watermark into the project's repository, by
        pack-objects and unpack-objects (nothing is pushed or fetched)."""
        wanted = ('%s\n^%s\n' % (candidate['commit'], candidate['watermark'])).encode()
        try:
            packed = _git_process.run(['git', '-C', str(candidate['workspace']), 'pack-objects', '--revs', '--stdout',
                                       '-q'], input=wanted, capture_output=True, timeout=GIT_SECONDS)
            unpacked = _git_process.run(['git', '-C', self.clone, 'unpack-objects', '-q'], input=packed.stdout,
                                        capture_output=True, timeout=GIT_SECONDS) if packed.returncode == 0 else packed
        except (OSError, subprocess.SubprocessError) as error:
            raise Refused('unavailable_service:git/transfer', type(error).__name__) from None
        if unpacked.returncode or self._tree(self.clone, candidate['commit']) != candidate['tree']:
            raise Refused('unavailable_service:git/transfer', (unpacked.stderr or b'').decode('utf-8', 'replace')[:300])

    def _local_record(self, action, data):
        eid = 'effect:' + data['dispatch_id']
        current = self._row(eid)
        self._command(LOCAL_OPERATION, {'action': action, 'effect_id': eid, 'data': data},
                      {eid: current['version'] if current else 0})
        return self._row(eid)

    def _publish_locally(self, sid, candidate, dispatch, subject):
        """VELDO-0235: the compare-and-swap of the project's local trunk from the recorded watermark to the
        candidate, recorded as this dispatch's publication. Returns the recorded effect."""
        self._copy_objects(candidate)
        payload = {'commit': subject['commit'], 'tree': subject['tree'], 'old_tip': subject['old_tip'],
                   'revision': subject['revision']}
        # VELDO-0260: the working trees that have the trunk checked out, recorded before the swap.
        found = self._checkouts()
        accepted = {'kind': 'publication', 'destination_kind': LAND_LOCALLY, 'dispatch_id': dispatch, 'unit': sid,
                    'domain_uuid': self.domain, 'repository_uuid': self.repository, 'station': STATION,
                    'status': 'accepted', 'payload': payload, 'local': {'repository': self.clone, 'ref': self.ref},
                    'checkouts': [{'path': c['path'], 'clean': c['clean']} for c in found]}
        self._local_record('accept', accepted)
        trees = [dict(c, outcome='left') for c in found]
        before = self._local_tip()
        dirty = next((c for c in trees if c['clean'] is False), None)
        unreadable = next((c for c in trees if c['clean'] is None), None)
        if before != payload['old_tip']:
            # The local trunk moved since the watermark, found before the swap: nothing is moved.
            ended = dict(accepted, status='refused', refusal='stale-subject', evidence=None,
                         observed={'tip': before})
        elif dirty is not None or unreadable is not None:
            # VELDO-0260: a tree holding the trunk with local changes (or one that cannot be read) refuses before
            # anything moves.
            tree = dirty or unreadable
            word = CHECKOUT_DIRTY if dirty is not None else CHECKOUT_UNMOVABLE
            tree['outcome'] = 'refused'
            ended = dict(accepted, status='refused', refusal=word, evidence=None,
                         observed={'tip': before, 'working_tree': tree['path'], 'changes': tree.get('changes'),
                                   'in_progress': tree.get('in_progress'), 'reason': tree.get('reason')})
        else:
            # VELDO-0260: each clean tree moves with the trunk; one that cannot puts the others back and refuses.
            moved, stuck = [], None
            for tree in trees:
                why = self._move_checkout(tree['path'], payload['old_tip'], payload['commit'])
                if why is not None:
                    stuck = tree
                    tree.update(outcome='refused', reason=why)
                    break
                tree['outcome'] = 'moved'
                moved.append(tree)
            swapped = after = None
            if stuck is None:
                swapped = self._git(self.clone, 'update-ref', '-m', 'veldo land ' + dispatch, self.ref,
                                    payload['commit'], payload['old_tip'])
                after = self._local_tip()
            if stuck is None and swapped.returncode == 0 and after == payload['commit']:
                ended = dict(accepted, status='completed', completed=True,
                             destination={'local_repository': self.clone,
                                          'destinations': [{'url': self.clone, 'ref': self.ref, 'outcome': 'at-tip'}]},
                             evidence={'local_commit': payload['commit'], 'tree': payload['tree'],
                                       'old_tip': payload['old_tip'], 'new_tip': after})
            else:
                for tree in moved:
                    why = self._move_checkout(tree['path'], payload['commit'], payload['old_tip'])
                    if why is None:
                        tree['outcome'] = 'restored'
                    else:
                        tree.update(outcome='restore_failed', reason=why)
                if stuck is not None:
                    ended = dict(accepted, status='refused', refusal=CHECKOUT_UNMOVABLE, evidence=None,
                                 observed={'tip': self._local_tip(), 'working_tree': stuck['path'],
                                           'reason': stuck['reason']})
                else:
                    # The swap lost to a commit that moved the trunk under the ref lock; it was not overwritten.
                    ended = dict(accepted, status='refused', refusal='trunk-moved', evidence=None,
                                 observed={'tip': after})
        ended['checkouts'] = trees
        effect = self._local_record('finish', ended)
        self.observe({'schema': SCHEMA, 'operation': 'local_publication', 'domain': self.domain,
                      'repository': self.repository, 'unit': sid, 'request': dispatch, 'destination': LAND_LOCALLY,
                      'ref': self.ref, 'old_tip': payload['old_tip'], 'new_tip': self._local_tip(),
                      'outcome': ended['status'], 'refusal': ended.get('refusal'), 'effect': 'effect:' + dispatch,
                      'checkouts': trees, 'checkout_outcome': checkout_outcome(ended)})
        return effect

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
        if self.destination == LAND_AND_PUSH and not _same_place(candidate.get('remote_url'), self.remote):
            codes.append('missing_authority:publication/remote')
        # VELDO-0235: the project's destination now is the one this landing runs under, and the one its
        # approvals must be bound to.
        target = unit_destination(self.conn, sid)['destination']
        if target != self.destination:
            codes.append(DESTINATION_CODE)
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
        if target != LAND_AND_PUSH:
            exact['destination'] = target
        approvals = self._kind('approval')
        replacements = []
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
                # VELDO-0235: and the destination it was granted for (a binding without one names land_and_push).
                if bound.get('destination', LAND_AND_PUSH) != target:
                    differences[-1].append('destination')
            closest = min(differences, key=len)
            codes.extend(DESTINATION_CODE if f == 'destination' else 'binding_mismatch:approval/%s/%s' % (name, f)
                         for f in closest)
            if closest == ['tree']:
                replacements.append(name)
            elif closest and set(closest) <= {'tree', 'destination'}:
                # VELDO-0235: a grant for another destination is answered by a fresh grant, as an older tree's is.
                replacements.append(name)
        if codes:
            error = Refused(codes)
            if replacements and set(codes) == {'binding_mismatch:approval/%s/tree' % name for name in replacements}:
                # Every problem must be only an older tree's prior grant at this revision.
                error.subject = dict(exact, unit=sid, revision=data.get('revision'),
                                     approvals=replacements)
            elif replacements and DESTINATION_CODE in codes and set(codes) <= {
                    'binding_mismatch:approval/%s/tree' % name for name in replacements} | {DESTINATION_CODE}:
                # VELDO-0235: only an older tree's or another destination's prior grant: the exact subject to ask for.
                error.subject = dict(exact, unit=sid, revision=data.get('revision'), approvals=replacements)
            raise error
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
        tested tree, the RECORDED old tip (never a tip read now) and the unit revision the approvals were
        granted for, which is the revision a completion of this publication lands."""
        now = self.clock()
        cid, pid = 'contract/' + dispatch, 'permit/' + dispatch
        contract = {'domain_uuid': self.domain, 'repository_uuid': self.repository, 'unit': sid, 'station': STATION,
                    'sandbox': candidate.get('id') or 'candidate', 'dispatch_id': dispatch, 'kind': 'publication',
                    'target': self.target, 'worker': self.principal, 'status': 'accepted',
                    'deadline': now + self.deadline_seconds, 'permission_id': pid,
                    'payload': {'commit': subject['commit'], 'tree': subject['tree'], 'old_tip': subject['old_tip'],
                                'revision': subject['revision']}}
        written = self._upsert(cid, 'effect_contract', contract)
        reviewer = subject['reviewers'][0] if subject['reviewers'] else None
        self._upsert(pid, 'effect_permission', {
            'contract_digest': written['digest'], 'authorized': True, 'obligations': [],
            'expires_at': now + self.deadline_seconds, 'subscription_allowed': False, 'remaining_calls': 0,
            'gate_passed': True, 'gate_tree': subject['tree'], 'review_passed': True, 'reviewer': reviewer,
            'reviewer_group': self.reviewer_group, 'worker_group': self.worker_group, 'approval_current': True,
            'subject_digest': _digest(_canonical(dict({k: subject[k] for k in SUBJECT_FIELDS}, revision=subject['revision'])))})
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
            word = data.get('refusal')
            if word in CHECKOUT_REFUSALS:
                # VELDO-0260: a working tree that has the trunk checked out held the landing; it is re-landed once
                # the tree is clean (VELDO-0148), and the brief names the tree.
                seen = data.get('observed') or {}
                tree = seen.get('working_tree')
                brief = checkout_brief(word, tree, getattr(self, 'trunk', None), seen.get('changes'), seen.get('reason'))
                error = Refused('%s:%s' % (word, tree), brief)
                error.observed = {'classification': word, 'watermark': (data.get('payload') or {}).get('old_tip'),
                                  'tip': self._local_tip(), 'working_tree': tree, 'changes': seen.get('changes'),
                                  'in_progress': seen.get('in_progress'), 'brief': brief}
                raise error
            if word not in TRUNK_MOVED:
                raise Refused(executor_code(word), 'the publication was refused before anything was pushed')
            # VELDO-0148: the trunk moved, at the listing or after it; the tip found now is recorded
            # with its classification.
            error = Refused(executor_code(word), 'the trunk moved from the watermark; nothing was published')
            error.observed = {'classification': word, 'watermark': (data.get('payload') or {}).get('old_tip'),
                              'tip': self._local_tip() if self.destination == LAND_LOCALLY else self._remote_tip()}
            raise error
        if not PJ.confirmed(data):
            raise Refused('unknown_outcome:publication/' + str(data.get('status')),
                          'stopped under dispatch %s; no further attempt' % dispatch)
        return self.complete(unit, candidate)

    def publish(self, unit, candidate):
        """Publish the accepted candidate of `unit` ({spec, dispatch, ...}) by exact-tip compare-and-swap,
        then complete it. Returns {ok, outcome, refusal, refusals, taxonomy, unit, dispatch, published,
        receipt, projection}: outcome landed, refused (nothing written or moved), failed (the executor
        refused before pushing), or unknown (a stop under the original dispatch). A landed outcome whose
        projection was refused is not ok and names the projection's refusal."""
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
            if self.destination == LAND_LOCALLY:
                return self._recorded(unit, candidate, dispatch, self._publish_locally(sid, candidate, dispatch, subject))
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
        tip = self._local_tip() if self.destination == LAND_LOCALLY else self._remote_tip()
        if tip != fields['commit']:
            codes.append('unknown_outcome:confirmation')
        if codes:
            raise Refused(codes)
        if self.destination == LAND_LOCALLY:
            # VELDO-0235: the local ref's own answer, re-read now.
            confirmation = {'destination': LAND_LOCALLY, 'repository': self.clone, 'ref': self.ref, 'commit': tip,
                            'read_at': self.clock()}
        else:
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
        remote as the exact candidate, with every link of its evidence chain holding, and whose unit is
        still at the revision it published, completes; ok only when the projection also ran."""
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
                published = (data.get('payload') or {}).get('revision')
                if unit_row['data'].get('revision') != published:
                    raise Refused('stale_subject:landing/revision', 'revision %r was published; the unit is at %r'
                                  % (published, unit_row['data'].get('revision')))
                subject = {'id': sid, 'revision': published}
                landing = self.chain(sid, candidate, dispatch, effect)
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
        if 'refused' in projection:
            # The receipt is committed and the landing is a fact, but spec.shipped was not derived: not
            # ok, named; a later complete of this dispatch runs the projection again.
            code = '%s:projection/%s' % (projection['taxonomy'], str(projection['refused']).split(':', 1)[-1])
            self.counts['refused'] += 1
            self._emit('complete', sid, dispatch, candidate, outcome='refused', receipt=rid, refusal=code,
                       refusals=[code], taxonomy=projection['taxonomy'], projection=projection)
            return {'ok': False, 'outcome': 'landed', 'unit': sid, 'dispatch': dispatch, 'published': True,
                    'receipt': rid, 'projection': projection, 'refusal': code, 'refusals': [code],
                    'taxonomy': projection['taxonomy'], 'detail': 'the landing is recorded; its projection was refused'}
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
        mine = (effect or {}).get('data') or {}
        if effect is not None and (mine.get('kind') != 'publication' or mine.get('unit') != sid
                                   or (mine.get('domain_uuid'), mine.get('repository_uuid')) != (self.domain, self.repository)):
            # Another unit's publication under this dispatch is never reported as this unit's.
            effect = None
        status = (effect or {}).get('data', {}).get('status')
        published = True if effect and PJ.confirmed(effect['data']) else (False if effect is None or status == 'refused' else None)
        kind = taxonomy(error.code)
        outcome = 'unknown' if kind == 'unknown_outcome' else ('failed' if status == 'refused' else 'refused')
        # VELDO-0148: a refused publication's watermark, the tip found and its classification, and the exact
        # subject a refusal for a missing grant names.
        extra = {k: getattr(error, k) for k in ('observed', 'subject') if getattr(error, k, None) is not None}
        self._emit(operation, sid, dispatch, candidate, outcome=outcome, refusal=error.code, refusals=error.codes,
                   taxonomy=kind, detail=error.detail, **extra)
        return dict({'ok': False, 'outcome': outcome, 'unit': sid, 'dispatch': dispatch, 'published': published,
                     'refusal': error.code, 'refusals': list(error.codes), 'taxonomy': kind, 'detail': error.detail,
                     'receipt': None}, **extra)

    def _emit(self, operation, sid, dispatch, candidate, **fields):
        c = candidate if isinstance(candidate, dict) else {}
        self.observe(dict({'schema': SCHEMA, 'operation': operation, 'domain': self.domain,
                           'repository': self.repository, 'unit': sid, 'request': dispatch,
                           'accepted_versions': {k: c.get(k) for k in ('watermark', 'commit', 'tree') if c.get(k)}},
                          **fields))

    def status(self):
        """Metrics: accepted and refused operations, the publications of this repository with no
        conclusive answer (pending, each a stop), the publications refused because the trunk moved, by
        the executor's word (VELDO-0148: stale-subject at the listing, trunk-moved after it), and the
        landings not yet projected."""
        mine = [row['data'] for row in self._kind(EFFECT_KIND)
                if row['data'].get('kind') == 'publication' and row['data'].get('repository_uuid') == self.repository]
        pending = sorted(data.get('dispatch_id') for data in mine
                         if data.get('status') != 'refused' and not PJ.confirmed(data))
        moved = {word: sum(data.get('status') == 'refused' and data.get('refusal') == word for data in mine)
                 for word in TRUNK_MOVED}
        try:
            unprojected = PJ.Projection(self.store, self.database, domain=self.domain, repository=self.repository,
                                        root=self.events_root).status()['pending_events']
        except PJ.Refused as error:
            unprojected = [error.code]
        # VELDO-0260: the local landings by working-tree outcome.
        checkouts = {}
        for data in mine:
            outcome = checkout_outcome(data)
            if outcome is not None:
                checkouts[outcome] = checkouts.get(outcome, 0) + 1
        return dict(self.counts, pending=pending, trunk_moved=moved, unprojected=unprojected, checkouts=checkouts)
