#!/usr/bin/env python3
"""Batch landing: several reviewed units of one project assembled onto its trunk in one candidate, gated
once, every red inventoried, and landed together on one owner approval (VELDO-0239).

WHY. A unit is gated and landed by itself (VELDO-0057, VELDO-0148, VELDO-0235). A project whose full gate
takes an hour would then gate many times a day, and two units that each add a migration with the same
number collide on the trunk. A batch gates once for everything finished, sends each red back to the units
it names, and lands the batch as one compare-and-swap.

THE COMMAND. The owner starts a batch of one project: the Telegram message `/batch <project>` (read by
control_intake, batch_command below) or the same text sent from the UI's project view. The batch takes
every unit of that project whose independent review has passed and that has not landed (eligible), in
review-completion order. Every production intake hands the command to control_batch_service.Starter,
which records the owner's request in the authority store; the project's line runs it
(control_batch_service.BatchLine).

THE AUTHORITY (Authority). A batch reads its authority from the authority store and from nowhere else,
as the single-unit landing does (control_landing.Landing.subject): a unit's review is its floor record's
handoff (VELDO-0049) bound to the exact reviewed commit, its landing is a revision_landed receipt in the
store (the completion reader, or a batch receipt for the unit's revision), and the batch approval is the
owner's settled answer (VELDO-0064 inbox, VELDO-0068 settlement: an answered assignment the inbox admits,
the owner's own signed answer) to the question asked for exactly this subject. A caller's dict is never
an approval and a caller's review state is never a review.

ASSEMBLY (Batch.assemble). A new isolated clone (VELDO-0042's shape: `git init` with no template, the
caller's object store borrowed through alternates, no remote, no worktree link, a detached checkout) holds
the trunk watermark: the published trunk tip fetched once (land_and_push), or the local trunk tip read and
never written (land_locally). Each unit's reviewed commit is merged in order with --no-ff. The shared
append-only files and projections are resolved as the lander resolves them (lander.UNION_PATHS,
lander.PROJECTIONS); any other conflict leaves that unit out as `conflict:<unit>` and the batch goes on.
After each merge the project's renumber hook, when the project names one, runs in the clone with the
watermark and the merge commit as its two arguments; whatever it changes is committed as a separate
renumber commit and recorded with every file it renamed (old and new name). The factory itself renames no
file. A hook that exits non-zero leaves the unit just merged out as `hook_failed:renumber:<unit>` (the
clone is reset to before its merge). A project with no hook merges with no renumbering. The projections are
regenerated once from the merged tree; the clone's HEAD is the batch tip. A batch with no reviewed unit,
or with every unit left out, is `empty` and runs nothing.

THE GATE (Batch.gate). The batch tip is gated by ONE run of the trusted installation's gate in candidate
mode (VELDO-0058 control_verification.observe_gate), which takes the host lock itself (VELDO-0220: exit 75
means it did not start, nothing is recorded as a run). Every stage the gate's catalog declares is read
from the observation, green or red, whatever any other stage did: nothing stops at the first red. The
inventory names each red with its stage, each failing check the stage reports, and the units whose changes
(their merge, and the names their renumber commit gave) touch a path the check names, or none. It goes to
the owner (`tell`) and into the batch record, and each named unit is returned to its own fix round
(`fix_round`). Nothing of a red batch lands.

THE APPROVAL (Batch.approval_request, Batch.land). One approval request, asked as an inbox question to
the project's owner (Authority.ask), shows every unit with its review, the renumber commits, the gate
observation and the project's landing destination (VELDO-0235). Its bound subject is the batch tip and the
unit list (with the watermark, project and destination). Batch.land reads the settled answer for exactly
that subject from the store: none yet is `missing_authority:approval/batch` (asked once); a settled grant
for another subject this batch asked is refused `stale_subject:batch` and the owner is asked again. Any other approval a unit already needs (a protected path) is the caller's
`requirements(unit)`, still asked; the batch approval never replaces it. A red batch asked to land is
refused `missing_evidence:gate`.

PUBLICATION. One compare-and-swap of the trunk from the watermark to the batch tip: a push leased on the
watermark (land_and_push), or `git update-ref <trunk> <tip> <watermark>` in the project repository
(land_locally). The trunk is re-read afterwards whatever the swap answered, and classified by what was
found there: at the tip the batch landed and each unit gets its revision_landed receipt naming the batch,
written to the store; at the watermark the swap failed by name (unavailable_service:git/push or
git/update-ref) and the batch stays green; a trunk that cannot be read is unknown_outcome:batch/trunk.
A trunk found anywhere else moved after the watermark and ends the batch `trunk_moved`; Batch.reland re-merges the same
units on the new trunk, re-runs the hook and the gate, and the owner is asked again (VELDO-0148).

A single unit's landing is not touched: it never reads or writes a batch record.

OBSERVABILITY. Each batch's record (schema veldo.batch/v1, written to `records` when given) holds its
project, watermark, units in merge order with their reviewed and merge commits, units left out and why,
every hook run with its exit status and renames, the tip, the gate observation, the inventory, the
approval and the landing receipts; every step is also an `observe` event. metrics() counts batches by
outcome, units per batch, units left out by reason, reds per batch and gate seconds per batch.

Pure stdlib; Git only through the shared boundary (git_process)."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid


def _sibling(alias, name):
    spec = importlib.util.spec_from_file_location(alias, str(Path(__file__).resolve().with_name(name)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_git_process = _sibling('veldo_git_process', 'git_process.py')
_ORGANS = {}


def _organ(name):
    if name not in _ORGANS:
        _ORGANS[name] = _sibling('veldo_batch_' + name, name + '.py')
    return _ORGANS[name]


SCHEMA = 'veldo.batch/v1'
REQUEST_SCHEMA = 'veldo.batch_approval_request/v1'
RECEIPT_SCHEMA = 'veldo.batch_receipt/v1'
LANDED = 'revision_landed'
LAND_AND_PUSH, LAND_LOCALLY = 'land_and_push', 'land_locally'
OUTCOMES = ('empty', 'green', 'red', 'landed', 'trunk_moved', 'refused')
WATERMARK_REF = 'refs/veldo/batch/watermark'
GIT_SECONDS = 120
HOOK_SECONDS = 600
NOT_STARTED_EXIT = 75
STALE = 'stale_subject:batch'
RED = 'missing_evidence:gate'
MISSING_APPROVAL = 'missing_authority:approval/batch'
STOPPED = 'missing_authority:approval/batch/stopped'
UNREAD = 'unknown_outcome:batch/trunk'
APPROVAL_SUBJECT = 'batch_approval'
APPROVAL_CHOICES = ('grant', 'stop')
RECEIPT_KIND = 'batch_receipt'
FIX_KIND = 'batch_fix_round'
FLOOR_KIND = 'floor_unit'
ASK_SECONDS = 7 * 86400
READS = 2
# The owner's command: `/batch <project>` (a bot suffix, `/batch@bot`, is Telegram's own form).
COMMAND = re.compile(r'^/batch(?:@[A-Za-z0-9_]{1,64})?[ \t]+([A-Za-z0-9][A-Za-z0-9_.-]{0,127})[ \t]*$')
# A failing check a stage reports: a line of its output that starts FAIL, FAILED or ERROR.
FAILING = re.compile(r'^\s*(?:\[?(?:FAIL|FAILED|ERROR)\]?)(?::|\s)\s*(.+?)\s*$')
TAXONOMY = {'conflict': 'stale_subject', 'hook_failed': 'unavailable_service', 'stale_subject': 'stale_subject',
            'missing_evidence': 'missing_evidence', 'missing_authority': 'missing_authority',
            'invalid_input': 'invalid_input', 'unavailable_service': 'unavailable_service',
            'trunk_moved': 'stale_subject', 'not_started': 'unavailable_service', 'unknown_outcome': 'unknown_outcome'}


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__(code + (': ' + detail if detail else ''))
        self.code, self.detail = code, detail


def taxonomy(code):
    """The error class of a refusal code; a code with no class is an unknown outcome, never success."""
    return TAXONOMY.get(str(code).split(':', 1)[0], 'unknown_outcome')


def _hex(value):
    return isinstance(value, str) and len(value) in (40, 64) and set(value) <= set('0123456789abcdef')


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def digest(value):
    return 'sha256:' + hashlib.sha256(canonical(value)).hexdigest()


def batch_command(text):
    """The project the owner's `/batch <project>` names, or None when `text` is not that command."""
    if not isinstance(text, str):
        return None
    found = COMMAND.match(text.strip())
    return found.group(1) if found else None


def floor_id(repository, unit):
    return 'floor:' + json.dumps([repository, unit], separators=(',', ':'))


def receipt_id(batch, unit):
    return 'batch-receipt:%s:%s' % (batch, unit)


def approval_alias(subject_digest):
    """The inbox alias of the owner's question for one batch subject: one question per subject."""
    return 'batch-approval-' + hashlib.sha256(str(subject_digest).encode()).hexdigest()[:24]


class Authority:
    """What a batch reads from the authority store, and the only writer of what it records there.

    `store` and `conn` are control_store and the service's connection; `inbox` the repository's VELDO-0064
    Inbox on that connection (control_assignment), or None for a reader that asks nothing; `signer`/`sign`
    the journal signer of this service's commands, `command_sign(bytes)` the same principal's signature of
    an inbox command (AC.SIGNATURE_NAMESPACE)."""

    def __init__(self, store, conn, inbox=None, *, domain, repository, signer, sign, command_sign=None,
                 generation=1, store_uuid=None, clock=time.time):
        if not all(_text(v) for v in (domain, repository, signer)):
            raise Refused('invalid_input:authority', 'the domain, repository and signer are named')
        self.store, self.conn, self.inbox = store, conn, inbox
        self.domain, self.repository, self.signer, self.sign = domain, repository, signer, sign
        self.command_sign, self.generation, self.clock = command_sign, generation, clock
        self.store_uuid = store_uuid or ((getattr(inbox, 'ids', None) or {}).get('store_uuid'))

    # Reads.

    def _row(self, identity):
        row = self.conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
        return {'id': identity, 'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None

    def _kind(self, kind):
        return [{'id': i, 'version': v, 'data': json.loads(t)} for i, v, t in self.conn.execute(
            'SELECT id, version, data FROM entities WHERE kind=? ORDER BY id', (kind,))]

    def _written_at(self, identity):
        """The journal sequence of the last write of `identity`: the order the store committed it in."""
        pattern = '%' + json.dumps(identity)[1:-1] + '%'
        latest = 0
        for seq, after in self.conn.execute('SELECT seq, after_versions FROM journal WHERE after_versions LIKE ? '
                                            'ORDER BY seq', (pattern,)):
            try:
                if identity in json.loads(after):
                    latest = seq
            except ValueError:
                continue
        return latest

    def unit(self, unit):
        row = self._row(unit) if _text(unit) else None
        if not row or row['kind'] != 'execution_unit' or row['data'].get('repository_uuid') != self.repository:
            return None
        return row['data']

    def review(self, unit):
        """The unit's independent review from the store: its floor record handed off (VELDO-0049), with the
        reviewed commit it is bound to and the order it completed in; None when it has not passed."""
        if self.unit(unit) is None:
            return None
        row = self._row(floor_id(self.repository, unit))
        data = row['data'] if row and row['kind'] == FLOOR_KIND else {}
        handoff = data.get('handoff') if isinstance(data.get('handoff'), dict) else {}
        commit = (handoff.get('source') or {}).get('commit')
        if data.get('state') != 'handoff' or not _hex(commit):
            return None
        return {'state': 'passed', 'commit': commit, 'reviewers': list(handoff.get('reviewers') or []),
                'attempt': handoff.get('attempt'), 'floor_version': row['version'],
                'completed_at': self._written_at(row['id'])}

    def landed(self, unit):
        """Whether the unit's current revision has landed: a batch receipt for it in the store, or the
        completion reader's revision_landed (VELDO-0057). A reading that fails is never 'not landed'."""
        data = self.unit(unit)
        if data is None:
            return True
        revision = data.get('revision')
        for row in self._kind(RECEIPT_KIND):
            r = row['data']
            if r.get('unit') == unit and r.get('repository') == self.repository and r.get('revision') == revision \
                    and r.get('fact') == LANDED:
                return True
        try:
            gate = _organ('control_eligibility').Gate(self.store, self.conn, domain_uuid=self.domain,
                                                      repository_uuid=self.repository, workspace=None)
            return bool(gate.landed(unit))
        except Exception:  # noqa: BLE001 - an unreadable landing is never taken as not landed
            return True

    def project(self, name):
        row = self._row('project:' + str(name))
        return row['data'] if row and row['kind'] == 'project' else None

    def units_of(self, project):
        """Every unit of `project` in this repository, [{unit, commit}] with the commit its review is bound
        to: the store's own list, for the owner's command."""
        found = []
        for row in self._kind('execution_unit'):
            data = row['data']
            if data.get('repository_uuid') != self.repository:
                continue
            name, _record = _organ('control_landing').unit_project(self.conn, row['id'])
            if name != project:
                continue
            review = self.review(row['id'])
            if review is not None:
                found.append({'unit': row['id'], 'commit': review['commit']})
        return found

    def _assignment(self, subject_digest):
        return _organ('control_assignment').assignment_id(self.repository, approval_alias(subject_digest))

    def approval(self, subject):
        """The owner's settled answer to the batch question for exactly `subject`, read from the store:
        {ruling, subject_digest, by, assignment, version}, or None while there is none. Only an answer the
        inbox admits (the owner's own signed answer, VELDO-0064 and VELDO-0068) counts."""
        if self.inbox is None or not isinstance(subject, dict):
            return None
        d = digest(subject)
        aid = self._assignment(d)
        item = self.inbox.read(aid)
        data = (item or {}).get('data') or {}
        if not item or data.get('subject') != {'kind': APPROVAL_SUBJECT, 'ref': subject.get('batch'), 'digest': d}:
            return None
        if not self.inbox.admit(aid).get('admitted'):
            return None
        answer = data.get('answer') or {}
        return {'ruling': answer.get('ruling'), 'subject_digest': d, 'by': data.get('owner'), 'assignment': aid,
                'version': item.get('version'), 'answer': digest(answer.get('command') or {})}

    def asked(self, subject_digest):
        return self.inbox is not None and self.inbox.read(self._assignment(subject_digest)) is not None

    # Writes.

    def ask(self, request):
        """Open the owner's question for this request's subject (once per subject). The project owner is read
        from the store; the question is signed as this service's principal."""
        if self.inbox is None or not callable(self.command_sign):
            raise Refused('unavailable_service:inbox', 'no inbox to ask the owner through')
        if self.asked(request['subject_digest']):
            return {'ok': True, 'repeated': True}
        owner = (self.project(request['project']) or {}).get('owner')
        if not _text(owner):
            raise Refused('missing_authority:project_owner', str(request['project']))
        I = _organ('control_assignment')
        alias = approval_alias(request['subject_digest'])
        key = 'batch-ask/' + request['subject_digest'][len('sha256:'):][:32]
        content = {'kind': 'decision', 'owner': owner, 'scope': [self.repository],
                   'deadline': time.strftime(I.DEADLINE_FORMAT, time.gmtime(self.clock() + ASK_SECONDS)),
                   'budget': {'invocations': 1}, 'brief': request['brief'][:4000], 'choices': list(APPROVAL_CHOICES),
                   'subject': {'kind': APPROVAL_SUBJECT, 'ref': request['batch'], 'digest': request['subject_digest']}}
        command = {'operation': 'open', 'alias': alias, 'principal': self.signer, 'command_id': key, 'nonce': key,
                   'domain_uuid': self.domain, 'repository_uuid': self.repository, 'store_uuid': self.store_uuid,
                   'assignment': content}
        opened = self.inbox.apply({'command': command, 'signature': self.command_sign(self.store.canonical_bytes(command))})
        if not opened.get('ok'):
            raise Refused('unavailable_service:inbox/' + str(opened.get('reason')))
        return opened

    def _upsert(self, identity, kind, data):
        current = self._row(identity)
        if current is not None and current['data'] == data:
            return current
        command_id = 'batch/%s' % digest([identity, data])[len('sha256:'):][:32]
        self.store.execute(self.conn, {
            'command_id': command_id, 'principal': self.signer, 'operation': 'upsert_entity',
            'parameters': {'entity_id': identity, 'kind': kind, 'data': data},
            'expected_versions': {identity: current['version'] if current else 0}, 'artifact_digests': [],
            'nonce': command_id + '/nonce'}, self.signer, self.sign, self.generation)
        return self._row(identity)

    def write_receipt(self, receipt):
        data = dict(receipt, repository=self.repository, revision=(self.unit(receipt['unit']) or {}).get('revision'))
        return self._upsert(receipt_id(receipt['batch'], receipt['unit']), RECEIPT_KIND, data)

    def receipts(self, unit=None):
        return [r['data'] for r in self._kind(RECEIPT_KIND)
                if r['data'].get('repository') == self.repository and (unit is None or r['data'].get('unit') == unit)]

    def fix_round(self, batch, unit, commit, reds):
        """The unit returned to its own fix round, recorded with the reds that name it."""
        return self._upsert('batch-fix:%s:%s' % (batch, unit), FIX_KIND, {
            'unit': unit, 'commit': commit, 'batch': batch, 'repository': self.repository, 'reds': reds})


def eligible(authority, units):
    """The units a batch takes, in review-completion order: each whose independent review, read from the
    authority store, has passed for exactly the commit named, and that has not landed. A unit is {unit,
    commit}; any review a caller attaches is ignored and replaced by the store's."""
    if not isinstance(authority, Authority):
        raise Refused('missing_authority:batch', 'a batch reads its units\' reviews from the authority store')
    picked = []
    for entry in units or ():
        if not isinstance(entry, dict) or not _text(entry.get('unit')) or not _hex(entry.get('commit')):
            continue
        review = authority.review(entry['unit'])
        if review is None or review['commit'] != entry['commit'] or authority.landed(entry['unit']):
            continue
        picked.append({'unit': entry['unit'], 'commit': entry['commit'], 'review': review})
    return sorted(picked, key=lambda e: (e['review']['completed_at'], e['unit']))


def stages_of(observation):
    """Every stage the gate's catalog declares, in order, each {stage, result, checks}: result is pass,
    FAIL or None (never reported), and checks are the failing checks the stage's own output reports (the
    stage itself when it names none). Every stage is read, whatever any other stage did."""
    catalog = (observation or {}).get('catalog') or {}
    required = catalog.get('required') or []
    results = catalog.get('results') or {}
    lines = ((observation or {}).get('stdout') or '').splitlines()
    found = []
    for name in required:
        result = results.get(name)
        entry = {'stage': name, 'result': result, 'checks': []}
        if result != 'pass':
            section, inside = [], False
            for line in lines:
                if line == '== ' + name:
                    inside, section = True, []
                elif inside and (line.startswith('== ') or line.startswith('   %s: ' % name)):
                    inside = False
                elif inside:
                    section.append(line)
            for line in section:
                failing = FAILING.match(line)
                if failing:
                    entry['checks'].append({'check': failing.group(1)[:300], 'text': line.strip()[:500]})
            if not entry['checks']:
                entry['checks'].append({'check': name, 'text': '%s: %s' % (name, result or 'not reported')})
        found.append(entry)
    return found


class Batch:
    """One batch of one project. `repo_root` is the project repository (read; written only by a local
    landing's compare-and-swap), `trunk` and `remote` its trunk and remote, `destination` its landing
    destination (VELDO-0235). `hook` is the project's renumber hook, an argv list run in the clone with the
    watermark and the merge commit appended, or None. `identity` is the (name, email) every commit the
    batch makes carries; `push_identity` the VELDO-0153 identity record a push runs under, if any.
    `installation` is the trusted gate's directory (by default the watermark's own, laid down from Git
    objects outside the clone). `authority` is the Authority every review, landing and approval is read
    from and every receipt and fix round is written to. `tell(kind, payload)` reaches the owner,
    `fix_round(unit, reds)` is told of each unit returned to its fix round (after the store records it),
    `requirements(unit)` names every other approval a unit still lacks."""

    def __init__(self, repo_root, *, project, identity, authority, trunk='main', remote='origin',
                 destination=LAND_AND_PUSH, hook=None, push_identity=None, installation=None, workspace_root=None,
                 records=None, observe=None, tell=None, fix_round=None, requirements=None,
                 clock=time.time, gate_timeout=None, follows=None):
        if not isinstance(authority, Authority):
            raise Refused('missing_authority:batch', 'a batch reads and writes its authority through the store')
        if destination not in (LAND_AND_PUSH, LAND_LOCALLY):
            raise Refused('invalid_input:landing_destination', str(destination))
        if hook is not None and (not isinstance(hook, (list, tuple)) or not hook or not all(_text(a) for a in hook)):
            raise Refused('invalid_input:hook', 'a renumber hook is an argv list')
        if not (isinstance(identity, (list, tuple)) and len(identity) == 2 and all(_text(x) for x in identity)):
            raise Refused('invalid_input:identity', 'the batch commits under a named identity')
        self.repo_root, self.project, self.identity = str(repo_root), project, tuple(identity)
        self.trunk, self.remote, self.destination = trunk, remote, destination
        self.hook = list(hook) if hook else None
        self.push_identity, self.installation = push_identity, installation
        self.workspace_root = str(workspace_root) if workspace_root is not None else None
        self.records = Path(records) if records is not None else None
        self.observe = observe or (lambda event: None)
        self.authority = authority
        self.tell = tell or (lambda kind, payload: None)
        self.fix_round = fix_round or (lambda unit, reds: None)
        self.requirements = requirements or (lambda unit: [])
        # Every subject this batch asked the owner for, across re-assembly: a settled grant of one of them
        # that is not the current subject is a stale grant, refused by name.
        self.asked_subjects = []
        self.clock, self.gate_timeout, self.follows = clock, gate_timeout, follows
        self.gate_runs = 0
        self.record = None
        self.events = []
        self._units = None

    # Git through the one boundary.

    def _git(self, repo, *args, ok=(0,), identity=None, profile='isolated', text=True, remote_url=None):
        try:
            result = _git_process.run(['git', '-C', str(repo), *args], capture_output=True, text=text,
                                      timeout=GIT_SECONDS, stdin=subprocess.DEVNULL, identity=identity,
                                      profile=profile,
                                      push_identity=self.push_identity if profile == 'identity' else None,
                                      remote_url=remote_url if profile == 'identity' else None)
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            raise Refused('unavailable_service:git/' + args[0], type(error).__name__)
        if ok is not None and result.returncode not in ok:
            raise Refused('unavailable_service:git/' + args[0], (result.stderr or '').strip()[:300])
        return result

    def _head(self):
        return self._git(self.clone, 'rev-parse', 'HEAD').stdout.strip()

    @property
    def clone(self):
        return (self.record or {}).get('clone')

    # Records and events.

    def _event(self, operation, outcome, refusal=None, **fields):
        r = self.record or {}
        event = dict({'schema': SCHEMA, 'operation': operation, 'batch': r.get('id'), 'project': self.project,
                      'watermark': r.get('watermark'), 'tip': r.get('tip'), 'outcome': outcome,
                      'at': self.clock()}, **fields)
        if refusal is not None:
            event.update(refusal=refusal, taxonomy=taxonomy(refusal))
        self.events.append(event)
        if self.record is not None:
            self.record.setdefault('log', []).append({k: v for k, v in event.items() if k != 'schema'})
            self._write()
        self.observe(event)
        return event

    def _write(self):
        if self.records is None or self.record is None:
            return
        self.records.mkdir(parents=True, exist_ok=True)
        path = self.records / (self.record['id'] + '.json')
        body = json.dumps(self.record, sort_keys=True, indent=1).encode()
        temporary = path.with_suffix('.json.tmp')
        temporary.write_bytes(body)
        os.replace(temporary, path)

    def snapshot(self):
        return json.loads(json.dumps(self.record)) if self.record is not None else None

    # Assembly.

    def _watermark(self, clone):
        if self.destination == LAND_AND_PUSH:
            url = self._git(self.repo_root, 'config', '--get', 'remote.%s.url' % self.remote).stdout.strip()
            if not url:
                raise Refused('unavailable_service:git/remote', 'the remote has no url')
            if '://' not in url and not os.path.isabs(url) and ':' not in url.split('/', 1)[0]:
                url = str((Path(self.repo_root) / url).resolve())
            self._git(clone, 'fetch', '-q', '--no-tags', '--no-write-fetch-head', url,
                      '+refs/heads/%s:%s' % (self.trunk, WATERMARK_REF),
                      profile='identity' if self.push_identity else 'isolated', remote_url=url)
            self.record['remote_url'] = url
        else:
            local = self._git(self.repo_root, 'rev-parse', '--verify', 'refs/heads/%s^{commit}' % self.trunk).stdout.strip()
            self._git(clone, 'update-ref', WATERMARK_REF, local)
        return self._git(clone, 'rev-parse', '--verify', WATERMARK_REF + '^{commit}').stdout.strip()

    def _isolated_clone(self):
        common = self._git(self.repo_root, 'rev-parse', '--path-format=absolute', '--git-common-dir').stdout.strip()
        objects = Path(common) / 'objects'
        if not objects.is_dir():
            raise Refused('unavailable_service:git/objects', 'the project repository has no object store')
        clone = Path(tempfile.mkdtemp(prefix='veldo-batch-', dir=self.workspace_root))
        self.record['clone'] = str(clone)
        self._git(clone, 'init', '-q', '--template=')
        info = clone / '.git' / 'objects' / 'info'
        info.mkdir(parents=True, exist_ok=True)
        (info / 'alternates').write_text(str(objects) + '\n')
        return clone

    def _left_out(self, entry, code, **fields):
        self.record['left_out'].append(dict({'unit': entry['unit'], 'commit': entry['commit'], 'reason': code}, **fields))
        self._event('leave_out', 'refused', code, unit=entry['unit'])

    def _reset(self, before):
        self._git(self.clone, 'merge', '--abort', ok=None)
        self._git(self.clone, 'reset', '-q', '--hard', before)
        self._git(self.clone, 'clean', '-q', '-fdx')

    def _merge(self, entry):
        """Merge one unit's reviewed commit. True when merged; False when it conflicted (reset)."""
        LD = _organ('lander')
        before = self._head()
        merged = self._git(self.clone, 'merge', '--no-ff', '--no-edit', '-m',
                           'Batch %s: merge %s at %s' % (self.record['id'], entry['unit'], entry['commit'][:12]),
                           entry['commit'], ok=None, identity=self.identity)
        if merged.returncode == 0:
            return before
        conflicts = [p for p in self._git(self.clone, 'diff', '--name-only', '--diff-filter=U', '-z').stdout.split('\0') if p]
        real = [p for p in conflicts if p not in LD.UNION_PATHS and p not in LD.REGEN_PATHS]
        resolved = bool(conflicts) and not real
        for path in conflicts if resolved else ():
            if path in LD.UNION_PATHS:
                stages = {}
                for line in self._git(self.clone, 'ls-files', '-u', '-z', '--', path).stdout.split('\0'):
                    if '\t' in line:
                        parts = line.split('\t', 1)[0].split()
                        stages[parts[2]] = parts[1]
                if '2' not in stages or '3' not in stages:
                    resolved = False
                    break
                with tempfile.TemporaryDirectory() as td:
                    names = {}
                    for stage, label in (('1', 'base'), ('2', 'ours'), ('3', 'theirs')):
                        names[label] = os.path.join(td, label)
                        body = (self._git(self.clone, 'cat-file', 'blob', stages[stage], text=False).stdout
                                if stage in stages else b'')
                        Path(names[label]).write_bytes(body)
                    union = self._git(self.clone, 'merge-file', '-p', '--union', names['ours'], names['base'],
                                      names['theirs'], ok=None, text=False)
                    if union.returncode != 0:
                        resolved = False
                        break
                    (Path(self.clone) / path).write_bytes(union.stdout)
            else:
                self._git(self.clone, 'checkout', '--ours', '--', path)
            self._git(self.clone, 'add', '--', path)
        if not resolved:
            self._reset(before)
            self._left_out(entry, 'conflict:' + entry['unit'], paths=sorted(real or conflicts)[:20])
            return None
        self._git(self.clone, 'commit', '--no-edit', '-q', identity=self.identity)
        return before

    def _renumber(self, entry, merge):
        """Run the project's renumber hook after one merge; its changes are a separate renumber commit.
        Returns the hook run's record, or None when it failed (the caller leaves the unit out)."""
        watermark = self.record['watermark']
        env = dict(_git_process.clean_env(profile='isolated'), PYTHONDONTWRITEBYTECODE='1',
                   VELDO_BATCH=self.record['id'], VELDO_BATCH_UNIT=entry['unit'])
        started = self.clock()
        try:
            run = subprocess.run(self.hook + [watermark, merge], cwd=self.clone, capture_output=True, text=True,
                                 stdin=subprocess.DEVNULL, env=env, timeout=HOOK_SECONDS)
            code, out = run.returncode, (run.stdout + run.stderr)
        except subprocess.TimeoutExpired:
            code, out = None, 'timed out'
        except OSError as error:
            code, out = None, type(error).__name__
        run_record = {'unit': entry['unit'], 'merge': merge, 'hook': list(self.hook), 'exit': code,
                      'output': (out or '')[-2000:], 'started_at': started, 'finished_at': self.clock(),
                      'commit': None, 'renamed': [], 'changed': []}
        self.record['hook_runs'].append(run_record)
        if code != 0:
            self._event('renumber', 'refused', 'hook_failed:renumber:' + entry['unit'], unit=entry['unit'], exit=code)
            return None
        self._git(self.clone, 'add', '-A')
        staged = self._git(self.clone, 'diff', '--cached', '--quiet', ok=(0, 1))
        if staged.returncode == 1:
            self._git(self.clone, 'commit', '-q', '-m', 'Batch %s: renumber after %s (project hook)'
                      % (self.record['id'], entry['unit']), identity=self.identity)
            commit = self._head()
            status = self._git(self.clone, 'diff', '--name-status', '-M', '-z', merge, commit).stdout.split('\0')
            renamed, changed, i = [], [], 0
            while i < len(status) and status[i]:
                kind = status[i]
                if kind.startswith('R') or kind.startswith('C'):
                    renamed.append({'old': status[i + 1], 'new': status[i + 2]})
                    changed.extend([status[i + 1], status[i + 2]])
                    i += 3
                else:
                    changed.append(status[i + 1])
                    i += 2
            run_record.update(commit=commit, renamed=renamed, changed=sorted(set(changed)))
        self._event('renumber', 'accepted', unit=entry['unit'], exit=code, commit=run_record['commit'],
                    renamed=run_record['renamed'])
        return run_record

    def _project_trees(self):
        LD = _organ('lander')
        for path, generator in LD.PROJECTIONS:
            if (Path(self.clone) / generator).is_file():
                run = subprocess.run([sys.executable, '-B', generator], cwd=self.clone, capture_output=True,
                                     text=True, timeout=HOOK_SECONDS, stdin=subprocess.DEVNULL,
                                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
                if run.returncode != 0:
                    raise Refused('unavailable_service:projection/' + path, (run.stderr or run.stdout).strip()[:300])
                self._git(self.clone, 'add', '--', path)
        if self._git(self.clone, 'diff', '--cached', '--quiet', ok=(0, 1)).returncode == 1:
            self._git(self.clone, 'commit', '-q', '-m', 'Batch %s: project %s' % (
                self.record['id'], ', '.join(p for p, _g in LD.PROJECTIONS)), identity=self.identity)

    def assemble(self, units):
        """Assemble every eligible unit onto the trunk watermark in one candidate (see the module text)."""
        self.discard()
        self._units = [{'unit': u.get('unit'), 'commit': u.get('commit')} for u in units or () if isinstance(u, dict)]
        picked = eligible(self.authority, self._units)
        self.record = {'schema': SCHEMA, 'id': 'batch-' + uuid.uuid4().hex[:16], 'project': self.project,
                       'trunk': self.trunk, 'destination': self.destination, 'follows': self.follows,
                       'hook': list(self.hook) if self.hook else None, 'state': 'new', 'watermark': None,
                       'tip': None, 'units': [], 'left_out': [], 'hook_runs': [], 'gate': None,
                       'inventory': None, 'approval': None, 'landing': None, 'receipts': [],
                       'started_at': self.clock()}
        if not picked:
            self.record['state'] = 'empty'
            self._event('assemble', 'empty')
            return self.snapshot()
        try:
            clone = self._isolated_clone()
            watermark = self._watermark(clone)
            self._git(clone, 'checkout', '-q', '--detach', watermark)
            self.record['watermark'] = watermark
            for entry in picked:
                kind = self._git(clone, 'cat-file', '-t', entry['commit'], ok=None)
                if kind.returncode != 0 or kind.stdout.strip() != 'commit':
                    self._left_out(entry, 'missing_evidence:' + entry['unit'])
                    continue
                before = self._merge(entry)
                if before is None:
                    continue
                merge = self._head()
                paths = [p for p in self._git(clone, 'diff', '--name-only', '-z', before, merge).stdout.split('\0') if p]
                hook_run = None
                if self.hook:
                    hook_run = self._renumber(entry, merge)
                    if hook_run is None:
                        self._reset(before)
                        self._left_out(entry, 'hook_failed:renumber:' + entry['unit'])
                        continue
                renames = (hook_run or {}).get('renamed') or []
                self.record['units'].append({
                    'unit': entry['unit'], 'commit': entry['commit'], 'merge': merge,
                    'renumber': (hook_run or {}).get('commit'), 'review': entry.get('review'),
                    'paths': sorted(set(paths) | {r['new'] for r in renames})})
                self._event('merge', 'accepted', unit=entry['unit'], commit=entry['commit'], merge=merge)
            if not self.record['units']:
                self.record['state'] = 'empty'
                self._event('assemble', 'empty')
                return self.snapshot()
            self._project_trees()
            dirty = self._git(clone, 'status', '--porcelain', '--untracked-files=all').stdout
            if dirty.strip():
                raise Refused('invalid_input:batch/dirty', 'the assembled batch is not clean')
            self.record.update(state='assembled', tip=self._head())
        except Refused as error:
            self.record.update(state='refused', refusal=error.code)
            self._event('assemble', 'refused', error.code, detail=error.detail)
            return self.snapshot()
        self._event('assemble', 'accepted', units=[u['unit'] for u in self.record['units']],
                    left_out=[(u['unit'], u['reason']) for u in self.record['left_out']])
        return self.snapshot()

    # The gate.

    def _attribute(self, text):
        return sorted(u['unit'] for u in self.record['units'] if any(p and p in text for p in u['paths']))

    def gate(self):
        """Gate the batch tip once and inventory every red (see the module text)."""
        r = self.record
        if r is None or r.get('state') != 'assembled':
            return {'ok': False, 'refusal': 'invalid_input:batch', 'state': (r or {}).get('state')}
        CV = _organ('control_verification')
        directory = Path(tempfile.mkdtemp(prefix='veldo-batch-observation-', dir=self.workspace_root))
        r['observation_dir'] = str(directory)
        started = self.clock()
        try:
            installation = self.installation
            if installation is None:
                installation = CV.installation_at(self.clone, r['watermark'], directory / 'installed')
            self.gate_runs += 1
            observation, reference = CV.observe_gate(self.clone, installation, directory / 'gate', bind_refs=True,
                                                     timeout=self.gate_timeout)
        except CV.Refused as error:
            r['gate'] = {'green': False, 'refusals': [error.code], 'seconds': self.clock() - started}
            r.update(state='red', inventory=[{'stage': None, 'check': error.code, 'units': []}])
            self._event('gate', 'red', error.code)
            self.tell('inventory', {'batch': r['id'], 'project': self.project, 'inventory': r['inventory']})
            return {'ok': False, 'refusal': error.code}
        seconds = self.clock() - started
        if observation.get('exit') == NOT_STARTED_EXIT:
            # VELDO-0220: the host lock was held and the gate ran nothing: no run, nothing recorded as one.
            self.gate_runs -= 1
            self._event('gate', 'not_started', exit=NOT_STARTED_EXIT)
            return {'ok': False, 'not_started': True}
        stages = stages_of(observation)
        inventory = []
        for stage in stages:
            if stage['result'] == 'pass':
                continue
            for check in stage['checks']:
                inventory.append({'stage': stage['stage'], 'check': check['check'],
                                  'units': self._attribute(check['text'])})
        green = observation.get('green') is True and not inventory
        if not green and not inventory:
            inventory = [{'stage': None, 'check': code, 'units': []} for code in observation.get('refusals') or [RED]]
        r['gate'] = {'green': green, 'exit': observation.get('exit'), 'terminal': observation.get('terminal'),
                     'observation': reference, 'stages': [{'stage': s['stage'], 'result': s['result']} for s in stages],
                     'refusals': observation.get('refusals'), 'seconds': seconds, 'commit': observation.get('commit')}
        r['inventory'] = inventory
        r['state'] = 'green' if green else 'red'
        self._event('gate', r['state'], None if green else RED, reds=len(inventory), seconds=seconds)
        if not green:
            self.tell('inventory', {'batch': r['id'], 'project': self.project, 'tip': r['tip'], 'inventory': inventory})
            named = {}
            for red in inventory:
                for unit in red['units']:
                    named.setdefault(unit, []).append(red)
            commits = {u['unit']: u['commit'] for u in r['units']}
            for unit, reds in sorted(named.items()):
                self.authority.fix_round(r['id'], unit, commits.get(unit), reds)
                self.fix_round(unit, reds)
                self._event('fix_round', 'returned', unit=unit, reds=len(reds))
        return {'ok': green, 'inventory': inventory, 'stages': r['gate']['stages']}

    # The approval.

    def subject(self):
        """What the batch approval binds: the batch tip and the unit list, with the watermark, project and
        destination they were assembled for."""
        r = self.record or {}
        return {'batch': r.get('id'), 'project': self.project, 'destination': self.destination,
                'watermark': r.get('watermark'), 'tip': r.get('tip'),
                'units': [[u['unit'], u['commit']] for u in r.get('units') or []]}

    def approval_request(self):
        """The one approval request of a green batch, asked through `ask` (VELDO-0068)."""
        r = self.record or {}
        words = _organ('control_landing').destination_words(self.destination, self.remote, self.trunk)
        subject = self.subject()
        request = {'schema': REQUEST_SCHEMA, 'batch': r.get('id'), 'project': self.project,
                   'units': [{'unit': u['unit'], 'commit': u['commit'], 'review': u.get('review')}
                             for u in r.get('units') or []],
                   'renumber_commits': [{'unit': h['unit'], 'commit': h['commit'], 'renamed': h['renamed']}
                                        for h in r.get('hook_runs') or [] if h.get('exit') == 0],
                   'gate': {k: (r.get('gate') or {}).get(k) for k in ('green', 'terminal', 'observation', 'stages')},
                   'destination': self.destination, 'destination_words': words,
                   'subject': subject, 'subject_digest': digest(subject)}
        brief = ['Land batch %s of %s together: %d unit(s), one compare-and-swap of %s.'
                 % (r.get('id'), self.project, len(request['units']), self.trunk)]
        brief += ['- %s at %s' % (u['unit'], u['commit'][:12]) for u in request['units']]
        brief += ['Renumbered after %s: %s' % (h['unit'], ', '.join('%s -> %s' % (x['old'], x['new']) for x in h['renamed']))
                  for h in request['renumber_commits'] if h['renamed']]
        brief.append('Gate: %s.' % ((r.get('gate') or {}).get('terminal') or 'not run'))
        brief.append('Destination: %s.' % words)
        request['brief'] = '\n'.join(brief)
        return request

    def request_approval(self):
        r = self.record
        if r is None or r.get('state') != 'green':
            return {'ok': False, 'refusal': RED}
        request = self.approval_request()
        r['approval'] = {'asked': [request['subject_digest']], 'granted': None}
        self._ask(request)
        return {'ok': True, 'request': request}

    def _ask(self, request):
        if request['subject'] not in self.asked_subjects:
            self.asked_subjects.append(request['subject'])
        self.authority.ask(request)
        self._event('approval', 'asked', subject=request['subject_digest'])

    def _refuse_land(self, code, **fields):
        r = self.record
        r.setdefault('land_refusals', []).append(code)
        self._event('land', 'refused', code, **fields)
        return dict({'ok': False, 'refusal': code, 'outcome': 'refused'}, **fields)

    def land(self, grant=None):
        """Land a green batch on the owner's settled approval, read from the store for exactly this batch's
        subject (a `grant` the caller passes is never authority and is not read): one compare-and-swap of
        the trunk from the watermark to the tip, then a receipt per unit naming the batch."""
        r = self.record
        if r is None or r.get('state') != 'green':
            return self._refuse_land(RED, state=(r or {}).get('state'))
        subject = self.subject()
        grant = self.authority.approval(subject)
        if grant is None or grant.get('ruling') != APPROVAL_CHOICES[0]:
            stale = any((self.authority.approval(other) or {}).get('ruling') == APPROVAL_CHOICES[0]
                        for other in self.asked_subjects if other != subject)
            asked = self.approval_request()
            if not r.get('approval'):
                r['approval'] = {'asked': [], 'granted': None}
            if asked['subject_digest'] not in r['approval']['asked']:
                r['approval']['asked'].append(asked['subject_digest'])
            if grant is not None:
                return self._refuse_land(STOPPED, ruling=grant.get('ruling'))
            if not self.authority.asked(asked['subject_digest']):
                self._ask(asked)
            return self._refuse_land(STALE if stale else MISSING_APPROVAL, asked=asked['subject_digest'])
        r['approval'] = dict(r.get('approval') or {'asked': []}, granted={
            'subject_digest': grant['subject_digest'], 'by': grant.get('by'), 'assignment': grant['assignment'],
            'version': grant.get('version'), 'answer': grant.get('answer')})
        missing = []
        for unit in r['units']:
            missing.extend(self.requirements(dict(unit)) or [])
        if missing:
            return self._refuse_land(missing[0], missing=missing)
        CV = _organ('control_verification')
        accepted = CV.accept((r.get('gate') or {}).get('observation'), self.clone, r['tip'], bind_refs=True)
        if accepted:
            return self._refuse_land(accepted[0], acceptance=accepted)
        try:
            swapped, found = self._swap()
        except Refused as error:
            return self._refuse_land(error.code)
        if not swapped:
            r.update(state='trunk_moved', landing={'outcome': 'trunk_moved', 'watermark': r['watermark'], 'found': found})
            self._event('land', 'trunk_moved', 'trunk_moved:' + self.trunk, found=found)
            return {'ok': False, 'outcome': 'trunk_moved', 'found': found}
        now = self.clock()
        r['landing'] = {'outcome': 'landed', 'watermark': r['watermark'], 'tip': r['tip'],
                        'confirmed': {'ref': 'refs/heads/' + self.trunk, 'commit': found, 'read_at': now},
                        'destination': self.destination}
        for unit in r['units']:
            receipt = {'schema': RECEIPT_SCHEMA, 'fact': LANDED, 'unit': unit['unit'], 'commit': unit['commit'],
                       'merge': unit['merge'], 'batch': r['id'], 'project': self.project, 'tip': r['tip'],
                       'trunk': self.trunk, 'destination': self.destination, 'confirmed': r['landing']['confirmed']}
            r['receipts'].append(receipt)
            self.authority.write_receipt(receipt)
        r['state'] = 'landed'
        self._event('land', 'landed', units=[u['unit'] for u in r['units']])
        return {'ok': True, 'outcome': 'landed', 'tip': r['tip'], 'receipts': list(r['receipts'])}

    def _read_trunk(self, url=None, profile='isolated'):
        """The trunk as it is now, read with no expectation of success: (commit or None, read at all)."""
        ref = 'refs/heads/' + self.trunk
        for _attempt in range(READS):
            if self.destination == LAND_AND_PUSH:
                listed = self._git(self.clone, 'ls-remote', url, ref, ok=None, profile=profile, remote_url=url)
                if listed.returncode == 0:
                    words = (listed.stdout or '').split()
                    return (words[0] if words else None), True
            else:
                found = self._git(self.repo_root, 'rev-parse', '--verify', '--quiet', ref, ok=None)
                if found.returncode in (0, 1):
                    return ((found.stdout or '').strip() or None), True
        return None, False

    def _swap(self):
        """(swapped, trunk found): the one compare-and-swap from the watermark to the tip, then the trunk
        re-read and classified by what was found: the tip is landed; the watermark after a failed swap is that
        swap's failure by name (Refused); a trunk that cannot be read is unknown (Refused); anything else is a
        moved trunk."""
        r, ref = self.record, 'refs/heads/' + self.trunk
        if self.destination == LAND_AND_PUSH:
            url = r['remote_url']
            profile = 'identity' if self.push_identity else 'isolated'
            push = self._git(self.clone, 'push', '-q', '--force-with-lease=%s:%s' % (ref, r['watermark']), url,
                             '%s:%s' % (r['tip'], ref), ok=None, profile=profile, remote_url=url)
            swap = push
            found, read = self._read_trunk(url, profile)
            operation = 'push'
        else:
            staging = 'refs/veldo/batch/' + r['id']
            self._git(self.clone, 'push', '-q', self.repo_root, '%s:%s' % (r['tip'], staging))
            try:
                swap = self._git(self.repo_root, 'update-ref', ref, r['tip'], r['watermark'], ok=None)
            finally:
                self._git(self.repo_root, 'update-ref', '-d', staging, ok=None)
            found, read = self._read_trunk()
            operation = 'update-ref'
        if not read:
            raise Refused(UNREAD, 'the trunk could not be read after the swap (%s exit %s)' % (operation, swap.returncode))
        if found == r['tip']:
            return True, found
        if found == r['watermark']:
            raise Refused('unavailable_service:git/' + operation, (swap.stderr or '').strip()[:300]
                          or 'the swap failed and the trunk is still at the watermark')
        return False, found

    def reland(self):
        """VELDO-0148 for a batch: the trunk moved after the watermark, so the same units are merged again
        on the new trunk, the hook runs again and the gate runs again; the owner is asked again."""
        previous = self.record
        if previous is None or previous.get('state') != 'trunk_moved':
            return {'ok': False, 'refusal': 'invalid_input:batch'}
        units = [dict(u) for u in self._units or ()]
        self.follows = previous['id']
        record = self.assemble(units)
        if record['state'] != 'assembled':
            return {'ok': False, 'record': record}
        gated = self.gate()
        if gated.get('ok'):
            self.request_approval()
        return dict(gated, record=self.snapshot())

    def discard(self):
        """Remove the batch clone and its observation directory."""
        r = self.record or {}
        for key in ('clone', 'observation_dir'):
            if r.get(key) and os.path.isdir(r[key]):
                shutil.rmtree(r[key], ignore_errors=True)


def run(batch, units):
    """The owner's command, end to end up to the approval: assemble, gate once, and ask when green."""
    record = batch.assemble(units)
    if record['state'] != 'assembled':
        return {'outcome': record['state'], 'record': record}
    gated = batch.gate()
    if gated.get('not_started'):
        return {'outcome': 'not_started', 'record': batch.snapshot()}
    if gated.get('ok'):
        batch.request_approval()
    return {'outcome': batch.record['state'], 'record': batch.snapshot()}


def metrics(records):
    """Batches by outcome, units per batch, units left out by reason, reds per batch and gate seconds per batch."""
    by_outcome, left_out, units, reds, seconds = {}, {}, {}, {}, {}
    for record in records or ():
        state = record.get('state')
        by_outcome[state] = by_outcome.get(state, 0) + 1
        units[record.get('id')] = len(record.get('units') or [])
        reds[record.get('id')] = len(record.get('inventory') or [])
        seconds[record.get('id')] = (record.get('gate') or {}).get('seconds')
        for entry in record.get('left_out') or []:
            reason = entry['reason'].split(':', 1)[0] if not entry['reason'].startswith('hook_failed') else 'hook_failed:renumber'
            left_out[reason] = left_out.get(reason, 0) + 1
    return {'batches': by_outcome, 'units_per_batch': units, 'left_out_by_reason': left_out,
            'reds_per_batch': reds, 'gate_seconds_per_batch': seconds}
