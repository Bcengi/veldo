#!/usr/bin/env python3
"""The space ledger: the item, pool, hold and reconcile records in the control store (VELDO-0297).

WHAT THIS MODULE IS. The one record of what Veldo has on disk and in Docker, kept as entities of the
existing control store, and the only writer of them. Every write is one registered command of the store:
one transaction, one signed journal record, no second database. The journal record holds the whole item
(its kind, owner, locator and state), so paths and object names are recorded and file contents never are.

THE RECORDS, each an entity kind this module owns (design 4.1 to 4.4):

  space_item       space:item:<new id>. One per thing. kind, host, pool, locator, parent, owner, creator,
                   adopted, branch, start, process, state, ends_on, size, confirmed, deferral, removal, report.
  space_pool       space:pool:<host>:<name>. type (filesystem or engine_image), device, engine, floor,
                   returns_space, backing.
  space_hold       space:hold:<identity>. needs and source per pool, state, reason, used, retry_asked, freed.
  space_reconcile  space:reconcile:<new id>. What started it, the roots and engines read, and the counts.

ONLY THIS MODULE WRITES THEM. Attaching declares the four kinds and their id prefixes with the store's
declare_owners, bound to this file's bytes. From then on the store's generic entity command is refused
entity_owned for them on every connection, and so is any other command.

AN ITEM'S STATES AND THE ONLY MOVES (design 4.1):

  declare            nothing to declared
  confirm            declared to present
  signal             present, kept or deferred to due
  outcome removing   due to removing (the rules passed; the decision to remove is recorded)
  outcome removed    due or removing to removed
  outcome deferred   due to deferred; removing to deferred only when the rule that refused is the owning
                     tool's own refusal (remove_refused, design section 7 rule 7), which is read while the
                     remover runs
  outcome kept       due to kept. A removing item is removed to the end: the decision was recorded
  gone               declared, present, due or deferred to gone
  adopt              nothing (or a report record) to present, adopted
  measure, rebranch  write fields and move nothing

Every other move is refused as space_item_state:<the state the item is in>, with nothing written.

DECLARE REFUSES, each by name, with nothing written:

  space_protected:<entry>   the locator is on the protect list. A path is protected when it is at, above
                            or beneath a protected path; a Docker object when its name matches a pattern
                            for its type on its engine, or its compose project is a protected one.
  space_outside_roots       a path outside every known root, a branch of a repository nobody declared,
                            or a Docker object on an engine the installation does not name.
  space_locator_taken:<id>  a second live item at the same locator. Live is every state but removed and
                            gone.
  space_locator_parent      the path has a .. segment. It is never collapsed as text: behind a link the
                            folder it names is not the one the text names.
  space_locator_link        the path goes through a link: resolved, it is not the text that would be
                            recorded.

LOCATORS ARE COMPARED IN ONE CANONICAL FORM, never as the text a caller wrote: a path is normalized
(a trailing separator, a doubled one and a dot segment change nothing), so two spellings of one path are
one locator. Only those three are normalized as text.

A PATH IS RESOLVED BEFORE IT GETS A RECORD. declare, adopt and report resolve the path (the part of it
that exists; the rest is kept as written) and read the resolved path against the protect list and the
known roots, whose own paths are resolved the same way when the ledger is built. A path that resolves at,
above or beneath a protected path is space_protected; one that resolves outside every known root is
space_outside_roots; any other path that resolves to something else than its text is space_locator_link.
So a protected thing gets no item record through a link (design section 7), the recorded path is the
resolved one, and two locators that resolve to one folder are never two live items. The ledger rule at
removal (design section 7 rule 1) reads the same thing again, for a link made after the declaration.

KNOWN ROOTS are the roots the declarations name: each project's and each plain repository's worktree
root, the state root, the scratch roots and the build roots. They come from what the declarations reader
returned (control_space_config.read and read_project); this module opens no declaration itself.

THE POOL of a disk item is the filesystem pool whose device identity is the device the item's path is on,
so two paths on one filesystem count against one pool. A Docker item counts against its engine's image
pool when the engine has one, else against the pool its caller names.

WHAT IS NOT HERE. The lifecycle table is the kind registry's (VELDO-0298); this module is given it as
plain data and copies an item's events from it at declaration, with its version. Rules, probes and
removers, the judgement behind admit, and the event, mode, wrong-proposal and review group records are
later tickets. No clock is read anywhere in this module: accept is given the time.

WHO SIGNS A COMMAND (VELDO-0326, design 6.11). A git hook and a gate helper write to the ledger without
the owner's key. Two host principals exist for that, each with its own key, made when the service is
installed and kept under keys/ in the installation folder, and each enrolled by the owner's signed
enroll_principal as a service whose scope is the one named scope "space" (which covers no repository, so
the store's generic commands stay refused for both):

  space-observer   the hooks. It may sign declare and confirm for a worktree, a branch, an agent
                   repository and a session's scratch; rebranch; event; and the read behind covers.
  space-runner     the gate space helper and the run wrapper. What space-observer may, and for the run or
                   gate it started: declare, confirm, measure, hold, admit, release, signal and outcome.
                   It signals only run finished and verdict recorded, and only for exactly that run or
                   gate.

A run or gate is the runner's when the first journal record that named it (its hold, or the first item
declared for it) was signed as space-runner. The journal's own principal column is the evidence; nothing
the caller says is.

Every other command is refused from both as space_not_permitted:<the command's name>, with nothing
written, and so is every owner action: adopt, abandon (worktree abandoned sent as a signal is
space_abandon), confirm of a group, reconcile, marking a proposal wrong, the mode switch, a change to the
protect list and an answer to a space disposition request. The rule is a list of what each may sign, so a
command a later ticket adds is refused until this list names it.

accept() takes the packet a hook or helper sent: it verifies the signature against the principal's active
key in the store's own membership and keyring, then applies the rule, then runs the command with the
principal recorded on the journal record. Each refusal is in the observations with the principal and the
command's name. A signed command names its own command id, so a packet sent twice writes once.

Standard library only. The store is the control_store module the caller passes in, and accept is given the
control_membership module the same way.
"""
import fnmatch
import json
import os
import sqlite3
import subprocess
import sys
import uuid

SCHEMA = 'veldo.control_space/v1'
OWNER = 'space_ledger'

ITEM_KIND, POOL_KIND, HOLD_KIND, RECONCILE_KIND = 'space_item', 'space_pool', 'space_hold', 'space_reconcile'
ITEM_PREFIX, POOL_PREFIX, HOLD_PREFIX, RECONCILE_PREFIX = ('space:item:', 'space:pool:', 'space:hold:',
                                                           'space:reconcile:')

DISK_KINDS = ('worktree', 'agent_repository', 'build_output', 'scratch', 'evidence')
DOCKER_KINDS = ('container', 'volume', 'network', 'image_tag')
KINDS = DISK_KINDS + ('branch',) + DOCKER_KINDS
# The protect list's entry type that holds the name patterns of each Docker kind.
PROTECT_TYPE = {'container': 'container', 'volume': 'volume', 'network': 'network', 'image_tag': 'image'}

STATES = ('declared', 'present', 'due', 'deferred', 'removing', 'removed', 'gone', 'kept')
LIVE = ('declared', 'present', 'due', 'deferred', 'removing', 'kept')
SIGNALLED = ('present', 'kept', 'deferred')
OUTCOMES = ('removing', 'removed', 'deferred', 'kept')
# The one deferral a removing item can still get: the owning tool's refusal (design section 7, rule 7).
TOOL_REFUSAL = 'remove_refused'
GONE_FROM = ('present', 'declared', 'due', 'deferred')
REBRANCHED = ('present', 'kept', 'deferred')

SCOPES = ('project', 'plain_repository', 'no_project')
STATIONS = ('build', 'review', 'gate')
OWNER_PARTS = ('ticket', 'gate', 'lane', 'session')
CREATORS = ('seam', 'hook', 'record', 'wrapper', 'census', 'reconcile')

POOL_TYPES = ('filesystem', 'engine_image')
HOLD_STATES = ('waiting', 'advised', 'admitted', 'released')
HOLD_ANSWERS = ('waiting', 'advised', 'admitted')
HOLD_SOURCES = ('declared', 'measured', 'default')
REASON_FIELDS = ('pool', 'need', 'free', 'held', 'floor')
RECONCILE_STARTS = ('service_start', 'console', 'cli')
RECONCILE_COUNTS = ('matched', 'adopted', 'reported', 'gone', 'completed')

DECLARE, CONFIRM, MEASURE, SIGNAL, OUTCOME, ADOPT, REPORT, GONE, REBRANCH = (
    'space_declare', 'space_confirm', 'space_measure', 'space_signal', 'space_outcome', 'space_adopt',
    'space_report', 'space_gone', 'space_rebranch')
POOL, HOLD, ADMIT, RELEASE, RECONCILE = ('space_pool', 'space_hold', 'space_admit', 'space_release',
                                         'space_reconcile')
ITEM_OPERATIONS = (DECLARE, CONFIRM, MEASURE, SIGNAL, OUTCOME, ADOPT, REPORT, GONE, REBRANCH)
OPERATIONS = ITEM_OPERATIONS + (POOL, HOLD, ADMIT, RELEASE, RECONCILE)
WRITES = ('entities', 'journal', 'commands', 'nonces')

# Who signs a space command (design 6.11). The two host principals, the one scope both are enrolled
# with, where their keys are kept in the installation folder, and the namespace a command is signed in
# (the authority contract's own).
OBSERVER, RUNNER = 'space-observer', 'space-runner'
HOST_PRINCIPALS = (OBSERVER, RUNNER)
SCOPE = 'space'
KEYS_FOLDER = 'keys'
NAMESPACE = 'veldo-command'
# Commands of later tickets, named here so the rule can say who may sign them.
EVENT, COVERS = 'space_event', 'space_covers'
ABANDON, CONFIRM_GROUP, REJECT, MODE, PROTECT, DISPOSITION = (
    'space_abandon', 'space_confirm_group', 'space_reject', 'space_mode', 'space_protect', 'space_disposition')
# The owner's actions: no host principal signs one.
OWNER_ACTIONS = (ADOPT, ABANDON, CONFIRM_GROUP, RECONCILE, REJECT, MODE, PROTECT, DISPOSITION)
OBSERVER_COMMANDS = (DECLARE, CONFIRM, REBRANCH, EVENT, COVERS)
RUNNER_COMMANDS = OBSERVER_COMMANDS + (MEASURE, HOLD, ADMIT, RELEASE, SIGNAL, OUTCOME)
MAY_SIGN = {OBSERVER: OBSERVER_COMMANDS, RUNNER: RUNNER_COMMANDS}
# What a hook records: these kinds, and scratch a session owns.
OBSERVED_KINDS = ('worktree', 'branch', 'agent_repository')
# The events the runner emits (section 5), and the event that is the owner's Abandon.
RUNNER_EVENTS = ('run_finished', 'verdict_recorded')
ABANDON_EVENT = 'worktree_abandoned'
# The parameters each command a host principal may send is called with.
COMMAND_PARAMETERS = {
    DECLARE: ('kind', 'locator', 'owner', 'creator', 'parent', 'start', 'branch', 'process', 'pool'),
    CONFIRM: ('item',), REBRANCH: ('item', 'branch', 'start'), MEASURE: ('item', 'bytes', 'event'),
    HOLD: ('hold', 'needs', 'source'), ADMIT: ('hold', 'answer', 'reason', 'used', 'retry_asked'),
    RELEASE: ('hold', 'used'), SIGNAL: ('event', 'subject'), OUTCOME: ('item', 'outcome', 'facts')}


class Refused(Exception):
    """A ledger refusal by name; nothing was written."""

    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail = code, detail


def _is_str(value):
    return isinstance(value, str) and value.strip() != ''


def _is_bytes(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _invalid(field, detail):
    return Refused('invalid_input:' + field, detail)


# ---------------------------------------------------------------------------------------------
# Locators: one canonical form, the known roots, the protect list.
# ---------------------------------------------------------------------------------------------

def canonical_path(path):
    """The one form a path is recorded and compared in."""
    return os.path.normpath(path)


def resolved_path(path):
    """Where a path leads: every link in the part of it that exists is followed, and the part that does
    not exist yet is kept as written."""
    return os.path.realpath(path)


def _absolute(value, field):
    if not _is_str(value) or not value.startswith('/'):
        raise _invalid(field, 'an absolute path')
    if '..' in value.split('/'):
        raise Refused('space_locator_parent', 'a locator has no .. segment: %s' % field)
    return canonical_path(value)


def canonical_locator(kind, locator):
    """The locator of an item of `kind` in its canonical form: {path} for a disk kind, {repository, ref}
    for a branch, {engine, name} with id and compose_project when known for a Docker kind."""
    if kind not in KINDS:
        raise _invalid('kind', 'one of ' + ', '.join(KINDS))
    if not isinstance(locator, dict):
        raise _invalid('locator', 'a mapping')
    if kind in DISK_KINDS:
        if set(locator) != {'path'}:
            raise _invalid('locator', 'a disk item is located by its path')
        return {'path': _absolute(locator['path'], 'locator.path')}
    if kind == 'branch':
        if set(locator) != {'repository', 'ref'} or not _is_str(locator['ref']):
            raise _invalid('locator', 'a branch is located by its repository and ref name')
        return {'repository': _absolute(locator['repository'], 'locator.repository'), 'ref': locator['ref']}
    if (not {'engine', 'name'} <= set(locator) <= {'engine', 'name', 'id', 'compose_project'}
            or not all(_is_str(value) for value in locator.values())):
        raise _invalid('locator', 'a Docker object is located by its engine context and name')
    return {key: locator[key] for key in sorted(locator)}


def locator_key(kind, locator):
    """The text two locators of one thing share. `locator` is canonical."""
    if kind in DISK_KINDS:
        return 'path:' + locator['path']
    if kind == 'branch':
        return 'branch:' + locator['repository'] + ':' + locator['ref']
    return 'docker:%s:%s:%s' % (locator['engine'], PROTECT_TYPE[kind], locator['name'])


def beneath(path, root):
    """Whether `path` is inside the folder `root` (and is not `root` itself)."""
    return path.startswith(root.rstrip('/') + '/')


def known_roots(config, projects, state_root):
    """The roots the declarations name, as {'roots': [folder], 'repositories': [repository]}. `config` is
    what the declarations reader returned for the installation; `projects` is one mapping per bound
    project: what read_project returned, with the project's repository added under repository."""
    roots = [canonical_path(state_root)]
    roots += [canonical_path(path) for path in config['scratch_roots']['roots']]
    roots += [canonical_path(path) for path in config['build_roots']]
    repositories = []
    for plain in config['plain_repositories']:
        roots.append(canonical_path(plain['worktree_root']))
        repositories.append(canonical_path(plain['repository']))
    for project in projects:
        roots.append(canonical_path(project['worktree_root']))
        repositories.append(canonical_path(project['repository']))
    return {'roots': sorted(set(roots)), 'repositories': sorted(set(repositories))}


def protect_list(config, projects):
    """Every protect entry in force: the installation's, then each project's additions, once each."""
    entries, have = [], set()
    for source in [config] + list(projects):
        for entry in source.get('protect', ()):
            if (entry['type'], entry['value']) not in have:
                have.add((entry['type'], entry['value']))
                entries.append({'type': entry['type'], 'value': entry['value'], 'engines': list(entry['engines'])})
    return entries


def protected_by(kind, locator, protect, resolve=None):
    """The protect entry that covers a canonical locator, as type:value, or None. With `resolve`, each
    protected path is read where it leads (for a locator that was resolved the same way)."""
    if kind in DOCKER_KINDS:
        for entry in protect:
            if locator['engine'] not in entry['engines']:
                continue
            if entry['type'] == PROTECT_TYPE[kind] and fnmatch.fnmatchcase(locator['name'], entry['value']):
                return entry['type'] + ':' + entry['value']
            if entry['type'] == 'compose_project' and locator.get('compose_project') == entry['value']:
                return entry['type'] + ':' + entry['value']
        return None
    path = locator['path'] if kind in DISK_KINDS else locator['repository']
    for entry in protect:
        if entry['type'] != 'path':
            continue
        value = canonical_path(entry['value'])
        value = resolve(value) if resolve else value
        if path == value or beneath(path, value) or beneath(value, path):
            return 'path:' + entry['value']
    return None


def inside_roots(kind, locator, roots, engines):
    """Whether a canonical locator is inside what the declarations name."""
    if kind in DOCKER_KINDS:
        return locator['engine'] in engines
    if kind == 'branch':
        repository = locator['repository']
        return repository in roots['repositories'] or any(beneath(repository, root) for root in roots['roots'])
    return any(beneath(locator['path'], root) for root in roots['roots'])


def device_of(path):
    """The device identity of the filesystem `path` is on, read at its nearest existing folder."""
    probe = path
    while True:
        try:
            return str(os.stat(probe).st_dev)
        except OSError:
            parent = os.path.dirname(probe)
            if parent == probe:
                return None
            probe = parent


# ---------------------------------------------------------------------------------------------
# Owners.
# ---------------------------------------------------------------------------------------------

def checked_owner(owner, kind):
    """An item's owner in its recorded form. The scope is exactly one of project, plain repository and
    no project, with an identity for the first two; then ticket, run (with its station), gate, lane and
    session where they apply. No project is accepted only for scratch with a session."""
    if not isinstance(owner, dict) or not set(owner) <= {'scope', 'run'} | set(OWNER_PARTS):
        raise _invalid('owner', 'a mapping of scope, ticket, run, gate, lane and session')
    scope = owner.get('scope')
    if not isinstance(scope, dict) or scope.get('type') not in SCOPES:
        raise _invalid('owner.scope', 'exactly one of project, plain_repository and no_project')
    if scope['type'] == 'no_project':
        if set(scope) != {'type'}:
            raise _invalid('owner.scope', 'no project has no identity')
        if kind != 'scratch' or not _is_str(owner.get('session')):
            raise _invalid('owner.scope', 'no project is accepted only for scratch with a session')
        out = {'scope': {'type': 'no_project'}}
    else:
        if set(scope) != {'type', 'id'} or not _is_str(scope['id']):
            raise _invalid('owner.scope', 'a project or plain repository scope names its identity')
        out = {'scope': {'type': scope['type'], 'id': scope['id']}}
    for part in OWNER_PARTS:
        if owner.get(part) is not None:
            if not _is_str(owner[part]):
                raise _invalid('owner.' + part, 'a name')
            out[part] = owner[part]
    run = owner.get('run')
    if run is not None:
        if not isinstance(run, dict) or set(run) != {'id', 'station'} or not _is_str(run['id']) \
                or run['station'] not in STATIONS:
            raise _invalid('owner.run', 'a run is recorded with its id and its station')
        out['run'] = {'id': run['id'], 'station': run['station']}
    return out


def owner_matches(owner, subject):
    """Whether an item's owner matches a signal's subject: every part the subject names is the owner's.
    A run is matched by its id alone."""
    if not isinstance(owner, dict):
        return False
    for part, wanted in subject.items():
        have = owner.get(part)
        if part == 'run':
            have = have.get('id') if isinstance(have, dict) else None
        if have != wanted:
            return False
    return True


def _checked_subject(subject):
    if not isinstance(subject, dict) or not subject or not set(subject) <= {'scope', 'run'} | set(OWNER_PARTS):
        raise _invalid('subject', 'a mapping naming at least one part of an owner')
    out = {}
    for part, value in subject.items():
        if part == 'scope':
            if not isinstance(value, dict) or value.get('type') not in SCOPES:
                raise _invalid('subject.scope', 'a scope')
            out[part] = dict(value)
        elif not _is_str(value):
            raise _invalid('subject.' + part, 'a name')
        else:
            out[part] = value
    return out


def checked_lifecycle(lifecycle):
    """The lifecycle table the kind registry gives, as plain data: its version, its events, and for each
    kind the events an item of that kind ends on."""
    if (not isinstance(lifecycle, dict) or not _is_str(lifecycle.get('version'))
            or not isinstance(lifecycle.get('events'), (list, tuple))
            or not all(_is_str(event) for event in lifecycle['events'])
            or not isinstance(lifecycle.get('ends_on'), dict) or set(lifecycle['ends_on']) != set(KINDS)):
        raise _invalid('lifecycle', 'a version, the events, and the events each of the ten kinds ends on')
    events = list(lifecycle['events'])
    ends_on = {}
    for kind in KINDS:
        listed = lifecycle['ends_on'][kind]
        if not isinstance(listed, (list, tuple)) or any(event not in events for event in listed):
            raise _invalid('lifecycle', 'kind %s ends on events of the table' % kind)
        ends_on[kind] = list(listed)
    return {'version': lifecycle['version'], 'events': events, 'ends_on': ends_on}


def item_id(identifier):
    return ITEM_PREFIX + identifier


def pool_id(host, name):
    return POOL_PREFIX + host + ':' + name


def hold_id(identity):
    return HOLD_PREFIX + identity


# ---------------------------------------------------------------------------------------------
# The Ledger.
# ---------------------------------------------------------------------------------------------

class Ledger:
    """The ledger on one control store connection.

    `store` is the control_store module and `conn` its connection; `sign(bytes) -> text` signs journal
    records as `journal_signer`. `config` is the installation's space section as the declarations reader
    returned it, `projects` one mapping per bound project (read_project's answer with repository added),
    `state_root` the factory state root, `lifecycle` the kind registry's table as plain data, `host` the
    host the things are on. `device(path)` gives the device identity of the filesystem a path is on.

    Every command returns {'ok': True, ...} or {'ok': False, 'reason': <name>, 'detail': ...}."""

    def __init__(self, store, conn, journal_signer, sign, *, config, state_root, lifecycle, host, projects=(),
                 authority_generation=1, device=device_of, new_id=None):
        if not isinstance(config, dict) or config.get('present') is not True:
            raise Refused('space_not_configured', 'the installation has no space section: there is no ledger')
        if not _is_str(host) or ':' in host:
            raise _invalid('host', 'a host name')
        if not _is_str(state_root) or not state_root.startswith('/'):
            raise _invalid('state_root', 'an absolute path')
        self.store, self.conn = store, conn
        self.journal_signer, self.sign, self.authority_generation = journal_signer, sign, authority_generation
        self.config, self.projects, self.host = config, [dict(project) for project in projects], host
        self.roots = known_roots(config, self.projects, state_root)
        self.resolved_roots = {part: sorted({resolved_path(path) for path in paths})
                               for part, paths in self.roots.items()}
        self.engines = list(config['engines'])
        self.protect = protect_list(config, self.projects)
        self.lifecycle = checked_lifecycle(lifecycle)
        self.device = device
        self.new_id = new_id or (lambda: uuid.uuid4().hex)
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        self.refused_declares = {}
        transitions = {DECLARE: self._t_declare, CONFIRM: self._t_confirm, MEASURE: self._t_measure,
                       SIGNAL: self._t_signal, OUTCOME: self._t_outcome, ADOPT: self._t_adopt,
                       REPORT: self._t_report, GONE: self._t_gone, REBRANCH: self._t_rebranch,
                       POOL: self._t_pool, HOLD: self._t_hold, ADMIT: self._t_admit, RELEASE: self._t_release,
                       RECONCILE: self._t_reconcile}
        for operation in OPERATIONS:
            conn.command_registry[operation] = {'transaction_transition': transitions[operation], 'writes': WRITES}
        store.declare_owners(conn, OWNER,
                             kinds={ITEM_KIND: ITEM_OPERATIONS, POOL_KIND: (POOL,),
                                    HOLD_KIND: (HOLD, ADMIT, RELEASE), RECONCILE_KIND: (RECONCILE,)},
                             prefixes={ITEM_PREFIX: ITEM_OPERATIONS, POOL_PREFIX: (POOL,),
                                       HOLD_PREFIX: (HOLD, ADMIT, RELEASE), RECONCILE_PREFIX: (RECONCILE,)},
                             module=__file__)

    # Reads.

    def _row(self, entity_id, kind):
        row = self.conn.execute('SELECT version, data FROM entities WHERE id=? AND kind=?',
                                (entity_id, kind)).fetchone()
        return (row[0], json.loads(row[1])) if row else (0, None)

    def item(self, identity):
        """An item's record, or None."""
        return self._row(identity, ITEM_KIND)[1] if _is_str(identity) else None

    def pool(self, name):
        return self._row(pool_id(self.host, name), POOL_KIND)[1] if _is_str(name) else None

    def hold(self, identity):
        return self._row(hold_id(identity), HOLD_KIND)[1] if _is_str(identity) else None

    def reconcile_record(self, identity):
        return self._row(identity, RECONCILE_KIND)[1] if _is_str(identity) else None

    def items(self):
        """Every item as {identity: record}."""
        return {row[0]: json.loads(row[1]) for row in self.conn.execute(
            'SELECT id, data FROM entities WHERE kind=? ORDER BY id', (ITEM_KIND,))}

    def metrics(self):
        """Items by kind and state, and refused declares by reason."""
        by = {}
        for record in self.items().values():
            states = by.setdefault(record['kind'], {})
            states[record['state']] = states.get(record['state'], 0) + 1
        return {'items': by, 'refused_declares': dict(self.refused_declares)}

    def _at(self, key):
        """(identity, version, record) of the live item at a locator key, or None. Read on this
        connection, so inside a command's transaction it sees what the transaction commits against."""
        rows = self.conn.execute('SELECT id, version, data FROM entities WHERE kind=? AND instr(data, ?) > 0',
                                 (ITEM_KIND, json.dumps(key)))
        for identity, version, data in rows:
            record = json.loads(data)
            if record.get('key') == key and record.get('state') in LIVE:
                return identity, version, record
        return None

    def _pools(self):
        return [json.loads(row[0]) for row in self.conn.execute(
            'SELECT data FROM entities WHERE kind=? AND substr(id, 1, ?)=? ORDER BY id',
            (POOL_KIND, len(pool_id(self.host, '')), pool_id(self.host, '')))]

    # The command path.

    def _send(self, operation, parameters, versions, principal, command_id, about):
        command = {'command_id': command_id or 'space:' + uuid.uuid4().hex,
                   'principal': principal or self.journal_signer, 'operation': operation,
                   'parameters': parameters, 'expected_versions': versions, 'artifact_digests': [],
                   'nonce': uuid.uuid4().hex}
        observation = dict(about, schema=SCHEMA, operation=operation, command_id=command['command_id'],
                           principal=command['principal'])
        try:
            self.permit(command['principal'], operation, parameters)
            committed = self.store.execute(self.conn, command, self.journal_signer, self.sign,
                                           self.authority_generation)
            result = {'ok': True, 'seq': committed['seq'], 'replayed': committed['replayed']}
        except Refused as refusal:
            result = {'ok': False, 'reason': refusal.code, 'detail': refusal.detail}
        except self.store.StoreRefused as refusal:
            result = {'ok': False, 'reason': refusal.code, 'detail': refusal.detail}
        except sqlite3.Error as error:
            result = {'ok': False, 'reason': 'unavailable_service:space_ledger', 'detail': str(error)}
        return self._observed(result, observation)

    def _observed(self, result, observation):
        outcome = 'accepted' if result['ok'] else 'refused'
        self.counts[outcome] += 1
        if not result['ok'] and observation.get('operation') in (DECLARE, ADOPT):
            reason = result['reason'].split(':', 1)[0] if result['reason'].startswith('space_') else result['reason']
            self.refused_declares[reason] = self.refused_declares.get(reason, 0) + 1
        self.observations.append(dict(observation, outcome=outcome, refusal=None if result['ok'] else result['reason']))
        return result

    def _refuse(self, operation, refusal, about, principal=None):
        """A refusal found before any command was sent: nothing reaches the store."""
        return self._observed({'ok': False, 'reason': refusal.code, 'detail': refusal.detail},
                              dict(about, schema=SCHEMA, operation=operation, command_id=None,
                                   principal=principal))

    def _about(self, identity):
        record = self.item(identity) or {}
        return {'item': identity, 'kind': record.get('kind'), 'owner': record.get('owner'),
                'locator': record.get('locator'), 'state': record.get('state')}

    def _item_command(self, operation, identity, parameters, principal, command_id, also=None):
        if not _is_str(identity):
            return self._refuse(operation, _invalid('item', 'an item identity'), {'item': None})
        versions = {identity: self._row(identity, ITEM_KIND)[0]}
        versions.update(also or {})
        result = self._send(operation, dict(parameters, item=identity), versions, principal, command_id,
                            self._about(identity))
        if result['ok']:
            after = self.item(identity)
            result.update(item=identity, state=after['state'])
            self.observations[-1]['state'] = after['state']
        return result

    # Item commands (design 6.1).

    def _placed(self, kind, locator, pool):
        """What declare and adopt read before the command is sent: the canonical locator and the device
        its path is on."""
        canonical = canonical_locator(kind, locator)
        path = canonical.get('path') or canonical.get('repository')
        return canonical, (self.device(path) if path else None), pool

    def declare(self, kind, locator, owner, creator, parent=None, start=None, branch=None, process=None,
                pool=None, principal=None, command_id=None):
        """Create an item in state declared, with pool and ends_on filled in. Returns its identity."""
        return self._create(DECLARE, kind, locator, owner, creator, parent, start, branch, process, pool, None,
                            principal, command_id)

    def adopt(self, kind, locator, owner, rule, parent=None, start=None, branch=None, process=None, pool=None,
              principal=None, command_id=None):
        """Create an item in state present with adopted true, for a thing reconcile found; `rule` is the
        rule that proved the owner. A report record at the locator becomes the item. The same refusals
        as declare."""
        return self._create(ADOPT, kind, locator, owner, 'reconcile', parent, start, branch, process, pool, rule,
                            principal, command_id)

    def _create(self, operation, kind, locator, owner, creator, parent, start, branch, process, pool, rule,
                principal, command_id):
        about = {'item': None, 'kind': kind, 'owner': owner, 'locator': locator, 'state': None}
        try:
            canonical, device, pool = self._placed(kind, locator, pool)
        except Refused as refusal:
            return self._refuse(operation, refusal, about)
        identity = item_id(self.new_id())
        versions = {identity: 0}
        if operation == ADOPT:
            held = self._at(locator_key(kind, canonical))
            if held is not None and held[2].get('owner') is None:
                identity, versions = held[0], {held[0]: held[1]}
        parameters = {'item': identity, 'kind': kind, 'host': self.host, 'locator': canonical, 'owner': owner,
                      'creator': creator, 'parent': parent, 'start': start, 'branch': branch, 'process': process,
                      'pool': pool, 'device': device, 'rule': rule}
        result = self._send(operation, parameters, versions, principal, command_id,
                            dict(about, item=identity, locator=canonical))
        if result['ok']:
            after = self.item(identity)
            result.update(item=identity, state=after['state'], pool=after['pool'])
            self.observations[-1].update(state=after['state'], owner=after['owner'])
        return result

    def confirm(self, item, principal=None, command_id=None):
        """declared to present."""
        return self._item_command(CONFIRM, item, {}, principal, command_id)

    def measure(self, item, size, event, principal=None, command_id=None):
        """Write the item's size: bytes at this measurement and the event it was measured at."""
        return self._item_command(MEASURE, item, {'bytes': size, 'event': event}, principal, command_id)

    def outcome(self, item, outcome, facts=None, principal=None, command_id=None):
        """Write what became of a due or removing item: removing, removed, deferred or kept, with the
        facts (the removal fields for removed, the deferral fields for deferred). A removing item is
        removed, or deferred as remove_refused; nothing else."""
        return self._item_command(OUTCOME, item, {'outcome': outcome, 'facts': facts or {}}, principal, command_id)

    def gone(self, item, principal=None, command_id=None):
        """present, declared, due or deferred to gone: nothing is at the locator any more."""
        return self._item_command(GONE, item, {}, principal, command_id)

    def rebranch(self, item, branch, start, principal=None, command_id=None):
        """Write a worktree item's branch (None when detached) and start commit, and record a branch item
        for the new branch when it has none."""
        record = self.item(item) if _is_str(item) else None
        branch_item, also = None, {}
        if record is not None and _is_str(branch):
            repository = self._repository_of(record)
            if repository is not None and self._at(locator_key('branch', {'repository': repository,
                                                                           'ref': branch})) is None:
                branch_item = item_id(self.new_id())
                also = {branch_item: 0}
        result = self._item_command(REBRANCH, item, {'branch': branch, 'start': start, 'branch_item': branch_item},
                                    principal, command_id, also)
        if result['ok']:
            result['branch_item'] = branch_item
        return result

    def signal(self, event, subject, principal=None, command_id=None):
        """Mark every present, kept or deferred item whose owner matches the subject and that ends on this
        event as due. Returns their identities under items. The order is the ledger's own (by identity);
        removal order is the kind registry's."""
        about = {'item': None, 'event': event, 'subject': subject}
        try:
            if event not in self.lifecycle['events']:
                raise Refused('space_unknown_event', 'not an event of the lifecycle table')
            subject = _checked_subject(subject)
            self.permit(principal, SIGNAL, {'event': event, 'subject': subject})
        except Refused as refusal:
            return self._refuse(SIGNAL, refusal, about, principal)
        versions = {identity: version for identity, version, _record in self._matching(event, subject)}
        if not versions:
            return self._observed({'ok': True, 'items': [], 'seq': None, 'replayed': False},
                                  dict(about, schema=SCHEMA, operation=SIGNAL, command_id=None, principal=None))
        result = self._send(SIGNAL, {'event': event, 'subject': subject}, versions, principal, command_id, about)
        if result['ok']:
            result['items'] = sorted(versions)
            self.observations[-1]['items'] = sorted(versions)
        return result

    def report(self, kind, locator, found, proposed_owner=None, pool=None, principal=None, command_id=None):
        """Create or refresh a report record for a thing reconcile could not give an owner: what was
        found, and the owner a rule proposes when one does. It never writes an owner."""
        about = {'item': None, 'kind': kind, 'owner': None, 'locator': locator, 'state': None}
        try:
            canonical, device, pool = self._placed(kind, locator, pool)
        except Refused as refusal:
            return self._refuse(REPORT, refusal, about)
        held = self._at(locator_key(kind, canonical))
        identity, version = (held[0], held[1]) if held is not None else (item_id(self.new_id()), 0)
        parameters = {'item': identity, 'kind': kind, 'host': self.host, 'locator': canonical, 'found': found,
                      'proposed_owner': proposed_owner, 'pool': pool, 'device': device}
        result = self._send(REPORT, parameters, {identity: version}, principal, command_id,
                            dict(about, item=identity, locator=canonical))
        if result['ok']:
            result.update(item=identity, state=self.item(identity)['state'])
        return result

    # Pool, hold and reconcile commands.

    def set_pool(self, name, type, device=None, engine=None, backing=None, principal=None, command_id=None):
        """Write a pool's record: a filesystem by its device identity, or an engine image by its engine
        context and the filesystem pool its image file is on. The floor is the installation's."""
        identity = pool_id(self.host, name) if _is_str(name) else None
        about = {'item': None, 'pool': name}
        if identity is None or ':' in name:
            return self._refuse(POOL, _invalid('pool', 'a pool name'), about)
        parameters = {'pool': identity, 'name': name, 'type': type, 'device': device, 'engine': engine,
                      'backing': backing}
        return self._send(POOL, parameters, {identity: self._row(identity, POOL_KIND)[0]}, principal, command_id,
                          about)

    def place_hold(self, identity, needs, source, principal=None, command_id=None):
        """Write a hold in state waiting with the needs per pool and where each need came from."""
        about = {'item': None, 'hold': identity}
        if not _is_str(identity):
            return self._refuse(HOLD, _invalid('hold', 'a hold identity'), about)
        return self._send(HOLD, {'hold': hold_id(identity), 'needs': needs, 'source': source},
                          {hold_id(identity): self._row(hold_id(identity), HOLD_KIND)[0]}, principal, command_id,
                          about)

    def admit(self, identity, answer, reason=None, used=None, retry_asked=None, principal=None, command_id=None):
        """Write the answer admission gave for a waiting hold: admitted, advised or waiting, with the
        reason as numbers for waiting and advised. The judgement is admission's; this records it."""
        return self._hold_command(ADMIT, identity, {'answer': answer, 'reason': reason, 'used': used,
                                                    'retry_asked': retry_asked}, principal, command_id)

    def release(self, identity, used=None, principal=None, command_id=None):
        """waiting, advised or admitted to released."""
        return self._hold_command(RELEASE, identity, {'used': used}, principal, command_id)

    def _hold_command(self, operation, identity, parameters, principal, command_id):
        about = {'item': None, 'hold': identity}
        if not _is_str(identity):
            return self._refuse(operation, _invalid('hold', 'a hold identity'), about)
        entity = hold_id(identity)
        result = self._send(operation, dict(parameters, hold=entity), {entity: self._row(entity, HOLD_KIND)[0]},
                            principal, command_id, about)
        if result['ok']:
            result['state'] = self.hold(identity)['state']
        return result

    def reconcile(self, started_by, roots, engines, counts, principal=None, command_id=None):
        """Write one reconcile record: what started it, the roots and engines read, and the counts."""
        identity = RECONCILE_PREFIX + self.new_id()
        result = self._send(RECONCILE, {'reconcile': identity, 'started_by': started_by, 'roots': roots,
                                        'engines': engines, 'counts': counts}, {identity: 0}, principal,
                            command_id, {'item': None, 'reconcile': identity})
        if result['ok']:
            result['reconcile'] = identity
        return result

    # Who signs a command (design 6.11).

    def _starter(self, run):
        """The principal whose command first named a run or gate: the signer of the earliest journal
        record that made its hold or an item it owns. None when nothing names it yet."""
        if not _is_str(run):
            return None
        named = {hold_id(run)} if self.hold(run) is not None else set()
        for identity, record in self.items().items():
            owner = record.get('owner') or {}
            if (owner.get('run') or {}).get('id') == run or owner.get('gate') == run:
                named.add(identity)
        first = None
        for identity in named:
            for seq, principal, after in self.conn.execute(
                    'SELECT seq, principal, after_versions FROM journal WHERE instr(after_versions, ?) > 0 '
                    'ORDER BY seq', (json.dumps(identity),)):
                if json.loads(after).get(identity) == 1:
                    if first is None or seq < first[0]:
                        first = (seq, principal)
                    break
        return first[1] if first else None

    def _runs_of(self, owner):
        """The run and the gate an owner names."""
        owner = owner if isinstance(owner, dict) else {}
        run = owner.get('run')
        return [value for value in (run.get('id') if isinstance(run, dict) else None, owner.get('gate'))
                if _is_str(value)]

    def _observed_thing(self, kind, owner):
        """Whether a thing is one a hook records: a worktree, a branch, an agent repository, or scratch
        a session owns."""
        return kind in OBSERVED_KINDS or (kind == 'scratch' and isinstance(owner, dict)
                                          and _is_str(owner.get('session')))

    def permit(self, principal, operation, parameters):
        """The rule for what a host principal may sign. Raises Refused space_not_permitted:<the command's
        name>; returns for a command it may sign, and for every principal that is not a host principal
        (the authority and the owner are judged where their commands are accepted)."""
        if principal not in HOST_PRINCIPALS:
            return
        parameters = parameters if isinstance(parameters, dict) else {}
        name = ABANDON if operation == SIGNAL and parameters.get('event') == ABANDON_EVENT else operation

        def refuse(why):
            return Refused('space_not_permitted:%s' % name, '%s may not sign it: %s' % (principal, why))
        if name not in MAY_SIGN[principal]:
            raise refuse('an owner action' if name in OWNER_ACTIONS else 'not a command of this principal')
        runner = principal == RUNNER

        def own(runs):
            return runner and bool(runs) and all(self._starter(run) == RUNNER for run in runs)
        if operation == DECLARE:
            owner = parameters.get('owner')
            if self._observed_thing(parameters.get('kind'), owner):
                return
            runs = self._runs_of(owner)
            if not (runner and runs and all(self._starter(run) in (None, RUNNER) for run in runs)):
                raise refuse('the thing is neither one a hook records nor of a run or gate it started')
        elif operation in (CONFIRM, REBRANCH, MEASURE, OUTCOME):
            record = self.item(parameters.get('item')) or {}
            if operation in (CONFIRM, REBRANCH) and self._observed_thing(record.get('kind'), record.get('owner')):
                return
            if not own(self._runs_of(record.get('owner'))):
                raise refuse('the item is not of a run or gate it started')
        elif operation == HOLD:
            identity = parameters.get('hold')
            run = identity[len(HOLD_PREFIX):] if _is_str(identity) and identity.startswith(HOLD_PREFIX) else None
            if not (runner and self._starter(run) in (None, RUNNER)):
                raise refuse('the hold is of a run or gate another principal started')
        elif operation in (ADMIT, RELEASE):
            identity = parameters.get('hold')
            run = identity[len(HOLD_PREFIX):] if _is_str(identity) and identity.startswith(HOLD_PREFIX) else None
            if not own([run] if run else []):
                raise refuse('the hold is not of a run or gate it started')
        elif operation == SIGNAL:
            subject = parameters.get('subject')
            if parameters.get('event') not in RUNNER_EVENTS:
                raise refuse('it signals only ' + ' and '.join(RUNNER_EVENTS))
            if not (isinstance(subject, dict) and len(subject) == 1 and set(subject) <= {'run', 'gate'}
                    and own(list(subject.values()))):
                raise refuse('the subject is not exactly a run or gate it started')

    def apply(self, command):
        """Run one command a host principal signed: the rule by the command's name first, then the
        command, with the principal on its journal record. `command` holds principal, operation,
        parameters and its own command_id."""
        command = command if isinstance(command, dict) else {}
        principal, operation, parameters = command.get('principal'), command.get('operation'), command.get('parameters')
        about = {'item': None}
        try:
            if principal not in HOST_PRINCIPALS:
                raise Refused('not_authorized', 'not a host principal of the space ledger')
            if not _is_str(operation) or not isinstance(parameters, dict) or not _is_str(command.get('command_id')):
                raise _invalid('command', 'an operation, a mapping of parameters and a command id')
            parameters = dict(parameters)
            if _is_str(parameters.get('hold')) and not parameters['hold'].startswith(HOLD_PREFIX):
                parameters['hold'] = hold_id(parameters['hold'])
            self.permit(principal, operation, parameters)
            if operation not in COMMAND_PARAMETERS:
                raise Refused('space_no_command:' + operation, 'this ledger has no such command yet')
            if not set(parameters) <= set(COMMAND_PARAMETERS[operation]):
                raise _invalid('parameters', 'only ' + ', '.join(COMMAND_PARAMETERS[operation]))
        except Refused as refusal:
            return self._refuse(operation if _is_str(operation) else None, refusal, about,
                                principal if _is_str(principal) else None)
        given = dict(parameters, principal=principal, command_id=command['command_id'])

        def strip(identity):
            return identity[len(HOLD_PREFIX):] if _is_str(identity) else identity
        if operation == DECLARE:
            return self.declare(given.pop('kind', None), given.pop('locator', None), given.pop('owner', None),
                                given.pop('creator', None), **given)
        if operation == CONFIRM:
            return self.confirm(given.pop('item', None), **given)
        if operation == REBRANCH:
            return self.rebranch(given.pop('item', None), given.pop('branch', None), given.pop('start', None), **given)
        if operation == MEASURE:
            return self.measure(given.pop('item', None), given.pop('bytes', None), given.pop('event', None), **given)
        if operation == OUTCOME:
            return self.outcome(given.pop('item', None), given.pop('outcome', None), given.pop('facts', None), **given)
        if operation == SIGNAL:
            return self.signal(given.pop('event', None), given.pop('subject', None), **given)
        if operation == HOLD:
            return self.place_hold(strip(given.pop('hold', None)), given.pop('needs', None),
                                   given.pop('source', None), **given)
        if operation == ADMIT:
            return self.admit(strip(given.pop('hold', None)), given.pop('answer', None), **given)
        return self.release(strip(given.pop('hold', None)), **given)

    def accept(self, packet, membership, now):
        """Accept or refuse the packet a hook or a helper sent: {command, signature}. The signature must
        be the command's principal's, under its active key in this store's keyring, and the principal an
        active service member whose scope covers the space scope; then the rule, then the command.
        `membership` is the control_membership module; `now` is the time the caller read."""
        command = packet.get('command') if isinstance(packet, dict) else None
        signature = packet.get('signature') if isinstance(packet, dict) else None
        command = command if isinstance(command, dict) else {}
        principal, operation = command.get('principal'), command.get('operation')
        contract = membership.AC
        try:
            if not command or not isinstance(signature, str) or not signature.isascii():
                raise _invalid('packet', 'a command mapping and its ASCII signature')
            if principal not in HOST_PRINCIPALS:
                raise Refused('not_authorized', 'not a host principal of the space ledger')
            state = membership.authority_state(self.store, self.conn)
            member = contract.membership_entry(state['membership'], principal)
            active, why = contract.active_member(member, now)
            key = contract.active_key(state['keyring'], principal, now) if active else None
            if (not active or key is None
                    or member.get('principal_type') not in contract.BOUNDARIES['command_acceptance']
                    or not membership.scope_covers(member.get('scope'), SCOPE)):
                raise Refused('not_authorized', why or 'membership, key or scope absent')
            if not contract.ssh_keygen_verify(
                    self.store.canonical_bytes(command), signature,
                    contract.allowed_signers_line(principal, key['public_key'], NAMESPACE), principal, NAMESPACE)[0]:
                raise Refused('not_authorized', 'the command signature is not the principal\'s')
        except Refused as refusal:
            return self._refuse(operation if _is_str(operation) else None, refusal, {'item': None},
                                principal if _is_str(principal) else None)
        return self.apply(command)

    # Transitions. Each runs inside the command's own transaction and returns the entities it writes.

    def _stored(self, params, before, key='item', kind=ITEM_KIND, missing='space_no_item'):
        identity = params.get(key)
        record = before.get(identity) if _is_str(identity) else None
        if record is None or record['kind'] != kind:
            raise Refused(missing, 'no such record: %r' % (identity,))
        return identity, dict(record['data'])

    def _matching(self, event, subject):
        out = []
        for identity, version, data in self.conn.execute(
                'SELECT id, version, data FROM entities WHERE kind=? ORDER BY id', (ITEM_KIND,)):
            record = json.loads(data)
            if (record['state'] in SIGNALLED and event in record['ends_on']['events']
                    and owner_matches(record['owner'], subject)):
                out.append((identity, version, record))
        return out

    def _repository_of(self, record):
        """The repository a worktree item's branches are in: its agent repository when it lives inside
        one, else its project's or plain repository's."""
        parent = self.item(record['parent']) if record.get('parent') else None
        if parent is not None and parent['kind'] == 'agent_repository':
            return parent['locator']['path']
        scope = (record.get('owner') or {}).get('scope') or {}
        if scope.get('type') == 'plain_repository':
            return canonical_path(scope['id'])
        for project in self.projects:
            if scope.get('type') == 'project' and project.get('project') == scope['id']:
                return canonical_path(project['repository'])
        return None

    def _pool_for(self, kind, locator, device, named):
        """The name of the pool an item's bytes count against."""
        pools = self._pools()
        if kind in DOCKER_KINDS:
            for pool in pools:
                if pool['type'] == 'engine_image' and pool['engine'] == locator['engine']:
                    return pool['name']
            if _is_str(named) and any(pool['name'] == named for pool in pools):
                return named
            raise Refused('space_no_pool', 'engine %s has no image pool and the caller named none' % locator['engine'])
        for pool in pools:
            if pool['type'] == 'filesystem' and pool['device'] == device:
                return pool['name']
        raise Refused('space_no_pool', 'no filesystem pool has the device this path is on')

    def _resolved(self, kind, canonical):
        """The canonical locator with its path where it leads. A Docker locator has no path."""
        field = 'path' if kind in DISK_KINDS else 'repository' if kind == 'branch' else None
        return canonical if field is None else dict(canonical, **{field: resolved_path(canonical[field])})

    def _admissible(self, kind, canonical, identity=None):
        """The refusals of declare, in the order protect list, known roots, link, second live item.
        The protect list and the roots are read against the locator as written and as resolved."""
        resolved = self._resolved(kind, canonical)
        entry = protected_by(kind, canonical, self.protect)
        if entry is None and kind not in DOCKER_KINDS:
            entry = protected_by(kind, resolved, self.protect, resolved_path)
        if entry is not None:
            raise Refused('space_protected:' + entry, 'the locator is on the protect list')
        if not inside_roots(kind, resolved, self.resolved_roots, self.engines):
            raise Refused('space_outside_roots', 'the locator is outside every known root')
        if resolved != canonical:
            raise Refused('space_locator_link', 'the path goes through a link: it resolves elsewhere')
        key = locator_key(kind, canonical)
        held = self._at(key)
        if held is not None and held[0] != identity:
            raise Refused('space_locator_taken:' + held[0], 'a live item already has this locator')
        return key

    def _new_item(self, params, state, adopted):
        kind = params.get('kind')
        canonical = canonical_locator(kind, params.get('locator'))
        if canonical != params.get('locator'):
            raise _invalid('locator', 'the command carries the canonical locator')
        owner = checked_owner(params.get('owner'), kind)
        if params.get('creator') not in CREATORS:
            raise _invalid('creator', 'one of ' + ', '.join(CREATORS))
        for field in ('start', 'branch'):
            if params.get(field) is not None and not _is_str(params[field]):
                raise _invalid(field, 'a name')
        process = params.get('process')
        if process is not None and (not isinstance(process, dict) or set(process) != {'pid', 'started'}):
            raise _invalid('process', 'a process id and its start time')
        parent = params.get('parent')
        if parent is not None and (self.item(parent) or {}).get('state') not in LIVE:
            raise _invalid('parent', 'a live item')
        key = self._admissible(kind, canonical, params.get('item') if adopted else None)
        return {'kind': kind, 'host': params['host'], 'pool': self._pool_for(kind, canonical, params.get('device'),
                                                                             params.get('pool')),
                'locator': canonical, 'key': key, 'parent': parent, 'owner': owner, 'creator': params['creator'],
                'adopted': adopted, 'branch': params.get('branch'), 'start': params.get('start'),
                'process': process, 'state': state,
                'ends_on': {'version': self.lifecycle['version'], 'events': list(self.lifecycle['ends_on'][kind])},
                'size': None, 'confirmed': None, 'deferral': None, 'removal': None, 'report': None}

    def _fresh(self, params, before):
        identity = params.get('item')
        if not _is_str(identity) or not identity.startswith(ITEM_PREFIX) or params.get('host') != self.host:
            raise _invalid('item', 'a new item identity on this host')
        if identity in before:
            raise Refused('space_item_exists', 'an item has this identity')
        return identity

    def _t_declare(self, conn, params, before):
        identity = self._fresh(params, before)
        return {identity: {'kind': ITEM_KIND, 'data': self._new_item(params, 'declared', False)}}

    def _t_adopt(self, conn, params, before):
        identity = params.get('item')
        prior = before.get(identity) if _is_str(identity) else None
        if prior is None:
            identity = self._fresh(params, before)
        elif prior['kind'] != ITEM_KIND or prior['data'].get('owner') is not None:
            raise Refused('space_item_exists', 'an item has this identity')
        if not _is_str(params.get('rule')):
            raise _invalid('rule', 'the rule that proved the owner')
        record = self._new_item(params, 'present', True)
        record['adoption'] = {'rule': params['rule']}
        if prior is not None:
            record['size'] = prior['data'].get('size')
        return {identity: {'kind': ITEM_KIND, 'data': record}}

    def _t_report(self, conn, params, before):
        identity = params.get('item')
        kind = params.get('kind')
        canonical = canonical_locator(kind, params.get('locator'))
        if canonical != params.get('locator') or params.get('host') != self.host:
            raise _invalid('locator', 'the command carries the canonical locator on this host')
        if not isinstance(params.get('found'), dict):
            raise _invalid('found', 'what was found and why no rule adopted it')
        proposed = params.get('proposed_owner')
        report = {'found': params['found'], 'proposed_owner': None if proposed is None else checked_owner(proposed, kind)}
        prior = before.get(identity) if _is_str(identity) else None
        if prior is not None:
            record = dict(prior['data'])
            if prior['kind'] != ITEM_KIND or record.get('owner') is not None or record.get('state') not in LIVE:
                raise Refused('space_locator_taken:' + identity, 'an item with an owner has this locator')
            record['report'] = report
            return {identity: {'kind': ITEM_KIND, 'data': record}}
        if not _is_str(identity) or not identity.startswith(ITEM_PREFIX):
            raise _invalid('item', 'a new item identity')
        key = self._admissible(kind, canonical)
        return {identity: {'kind': ITEM_KIND, 'data': {
            'kind': kind, 'host': params['host'],
            'pool': self._pool_for(kind, canonical, params.get('device'), params.get('pool')),
            'locator': canonical, 'key': key, 'parent': None, 'owner': None, 'creator': 'reconcile',
            'adopted': False, 'branch': None, 'start': None, 'process': None, 'state': 'present',
            'ends_on': {'version': self.lifecycle['version'], 'events': []},
            'size': None, 'confirmed': None, 'deferral': None, 'removal': None, 'report': report}}}

    def _t_confirm(self, conn, params, before):
        identity, record = self._stored(params, before)
        if record['state'] != 'declared':
            raise Refused('space_item_state:' + record['state'], 'confirm moves an item from declared only')
        record['state'] = 'present'
        return {identity: {'kind': ITEM_KIND, 'data': record}}

    def _t_measure(self, conn, params, before):
        identity, record = self._stored(params, before)
        if not _is_bytes(params.get('bytes')) or not _is_str(params.get('event')):
            raise _invalid('size', 'bytes and the event they were measured at')
        record['size'] = {'bytes': params['bytes'], 'event': params['event']}
        return {identity: {'kind': ITEM_KIND, 'data': record}}

    def _t_signal(self, conn, params, before):
        event = params.get('event')
        if event not in self.lifecycle['events']:
            raise Refused('space_unknown_event', 'not an event of the lifecycle table')
        changes = {}
        for identity, _version, record in self._matching(event, _checked_subject(params.get('subject'))):
            record['state'] = 'due'
            record['due'] = {'event': event}
            changes[identity] = {'kind': ITEM_KIND, 'data': record}
        return changes

    def _t_outcome(self, conn, params, before):
        identity, record = self._stored(params, before)
        outcome, facts = params.get('outcome'), params.get('facts')
        if outcome not in OUTCOMES or not isinstance(facts, dict):
            raise _invalid('outcome', 'one of %s, with the facts' % ', '.join(OUTCOMES))
        if record['state'] not in ('due', 'removing'):
            raise Refused('space_item_state:' + record['state'], 'outcome is written for an item that is due or removing')
        if outcome == 'removing' and record['state'] != 'due':
            raise Refused('space_item_state:' + record['state'], 'removing follows due')
        if record['state'] == 'removing' and (outcome == 'kept' or (
                outcome == 'deferred' and facts.get('rule') != TOOL_REFUSAL)):
            raise Refused('space_item_state:removing', 'a removing item is removed to the end; it is deferred '
                          'only when the owning tool refuses the remove')
        if outcome == 'deferred':
            if not _is_str(facts.get('rule')):
                raise _invalid('facts.rule', 'the rule that refused')
            attempts = (record.get('deferral') or {}).get('attempts', 0) + 1
            record['deferral'] = dict(facts, attempts=attempts)
        elif outcome == 'removed':
            record['removal'] = dict(facts)
            record['confirmed'] = None
        elif outcome == 'removing':
            record['removal'] = dict(facts)
        record['state'] = outcome
        return {identity: {'kind': ITEM_KIND, 'data': record}}

    def _t_gone(self, conn, params, before):
        identity, record = self._stored(params, before)
        if record['state'] not in GONE_FROM:
            raise Refused('space_item_state:' + record['state'], 'gone is written for a declared, present, due or deferred item')
        record['state'] = 'gone'
        return {identity: {'kind': ITEM_KIND, 'data': record}}

    def _t_rebranch(self, conn, params, before):
        identity, record = self._stored(params, before)
        if record['kind'] != 'worktree':
            raise Refused('space_not_a_worktree', 'rebranch is written for a worktree item')
        if record['state'] not in REBRANCHED:
            raise Refused('space_item_state:' + record['state'], 'rebranch is written for a present, kept or deferred worktree')
        branch, start = params.get('branch'), params.get('start')
        if (branch is not None and not _is_str(branch)) or not _is_str(start):
            raise _invalid('branch', 'the new branch, or none when detached, and the new start commit')
        record['branch'], record['start'] = branch, start
        changes = {identity: {'kind': ITEM_KIND, 'data': record}}
        repository = self._repository_of(record) if branch is not None else None
        if repository is not None:
            canonical = {'repository': repository, 'ref': branch}
            if self._at(locator_key('branch', canonical)) is None:
                new = params.get('branch_item')
                if not _is_str(new) or not new.startswith(ITEM_PREFIX) or new in before:
                    raise _invalid('branch_item', 'a new item identity for the branch')
                changes[new] = {'kind': ITEM_KIND, 'data': self._new_item(
                    {'item': new, 'kind': 'branch', 'host': record['host'], 'locator': canonical,
                     'owner': record['owner'], 'creator': record['creator'], 'start': start,
                     'device': self.device(repository)}, 'present', False)}
        return changes

    def _t_pool(self, conn, params, before):
        name, kind = params.get('name'), params.get('type')
        if not _is_str(name) or params.get('pool') != pool_id(self.host, name):
            raise _invalid('pool', 'a pool of this host')
        if name not in self.config['pools']:
            raise Refused('space_unknown_pool:' + name, 'the installation names no such pool')
        if kind not in POOL_TYPES:
            raise _invalid('type', 'one of ' + ', '.join(POOL_TYPES))
        others = [pool for pool in self._pools() if pool['name'] != name]
        record = {'name': name, 'host': self.host, 'type': kind, 'device': None, 'engine': None,
                  'floor': self.config['pools'][name]['floor'], 'returns_space': kind == 'filesystem',
                  'backing': None}
        if kind == 'filesystem':
            if not _is_str(params.get('device')) or params.get('engine') is not None or params.get('backing') is not None:
                raise _invalid('device', 'a filesystem pool has a device identity and nothing else')
            if any(pool['type'] == 'filesystem' and pool['device'] == params['device'] for pool in others):
                raise Refused('space_pool_device_taken', 'two paths on one filesystem are one pool')
            record['device'] = params['device']
        else:
            if params.get('engine') not in self.engines or params.get('device') is not None:
                raise _invalid('engine', 'an engine image pool names an engine context of the installation')
            if any(pool['type'] == 'engine_image' and pool['engine'] == params['engine'] for pool in others):
                raise Refused('space_pool_engine_taken', 'an engine has one image pool')
            if not any(pool['type'] == 'filesystem' and pool['name'] == params.get('backing') for pool in others):
                raise _invalid('backing', 'the filesystem pool the image file is on')
            record['engine'], record['backing'] = params['engine'], params['backing']
        return {params['pool']: {'kind': POOL_KIND, 'data': record}}

    def _per_pool(self, value, field, allowed=None):
        names = {pool['name'] for pool in self._pools()}
        if not isinstance(value, dict) or not set(value) <= names:
            raise _invalid(field, 'a mapping of recorded pool to value')
        for item in value.values():
            if (allowed is None and not _is_bytes(item)) or (allowed is not None and item not in allowed):
                raise _invalid(field, 'bytes per pool' if allowed is None else 'one of ' + ', '.join(allowed))
        return dict(value)

    def _t_hold(self, conn, params, before):
        identity = params.get('hold')
        if not _is_str(identity) or not identity.startswith(HOLD_PREFIX) or identity == HOLD_PREFIX:
            raise _invalid('hold', 'a hold identity')
        if identity in before:
            raise Refused('space_hold_exists', 'a hold has this identity')
        needs = self._per_pool(params.get('needs'), 'needs')
        source = self._per_pool(params.get('source'), 'source', HOLD_SOURCES)
        if not needs or set(needs) != set(source):
            raise _invalid('needs', 'a need and its source for at least one pool')
        return {identity: {'kind': HOLD_KIND, 'data': {'needs': needs, 'source': source, 'state': 'waiting',
                                                       'reason': None, 'used': {}, 'retry_asked': False,
                                                       'freed': False}}}

    def _t_admit(self, conn, params, before):
        identity, record = self._stored(params, before, 'hold', HOLD_KIND, 'space_no_hold')
        answer, reason = params.get('answer'), params.get('reason')
        if answer not in HOLD_ANSWERS:
            raise _invalid('answer', 'one of ' + ', '.join(HOLD_ANSWERS))
        if record['state'] != 'waiting':
            raise Refused('space_hold_state:' + record['state'], 'admit judges a waiting hold')
        if answer == 'admitted':
            if reason is not None:
                raise _invalid('reason', 'an admitted hold has no reason')
        elif (not isinstance(reason, dict) or set(reason) != set(REASON_FIELDS) or reason['pool'] not in record['needs']
              or not all(_is_bytes(reason[field]) for field in REASON_FIELDS if field != 'pool')):
            raise _invalid('reason', 'pool, need, free, held and floor, as numbers')
        record['state'], record['reason'] = answer, reason
        if params.get('used') is not None:
            record['used'] = self._per_pool(params['used'], 'used')
        if params.get('retry_asked') is True:
            record['retry_asked'] = True
        return {identity: {'kind': HOLD_KIND, 'data': record}}

    def _t_release(self, conn, params, before):
        identity, record = self._stored(params, before, 'hold', HOLD_KIND, 'space_no_hold')
        if record['state'] == 'released':
            raise Refused('space_hold_state:released', 'the hold is released already')
        if params.get('used') is not None:
            record['used'] = self._per_pool(params['used'], 'used')
        record['state'] = 'released'
        return {identity: {'kind': HOLD_KIND, 'data': record}}

    def _t_reconcile(self, conn, params, before):
        identity, counts = params.get('reconcile'), params.get('counts')
        if not _is_str(identity) or not identity.startswith(RECONCILE_PREFIX) or identity in before:
            raise _invalid('reconcile', 'a new reconcile identity')
        if params.get('started_by') not in RECONCILE_STARTS:
            raise _invalid('started_by', 'one of ' + ', '.join(RECONCILE_STARTS))
        for field in ('roots', 'engines'):
            if not isinstance(params.get(field), list) or not all(_is_str(value) for value in params[field]):
                raise _invalid(field, 'a list of names')
        if not isinstance(counts, dict) or set(counts) != set(RECONCILE_COUNTS) \
                or not all(_is_bytes(value) for value in counts.values()):
            raise _invalid('counts', 'the counts ' + ', '.join(RECONCILE_COUNTS))
        return {identity: {'kind': RECONCILE_KIND, 'data': {
            'started_by': params['started_by'], 'roots': list(params['roots']), 'engines': list(params['engines']),
            'counts': dict(counts)}}}


# ---------------------------------------------------------------------------------------------
# The sending side: a hook or a helper signs as its host principal, never as the owner.
# ---------------------------------------------------------------------------------------------

def key_path(principal, folder):
    """Where a host principal's key is kept in the installation folder."""
    return os.path.join(folder, KEYS_FOLDER, principal)


def signed(principal, operation, parameters, folder, canonical, command_id=None):
    """The packet {command, signature} for one command, signed with the host principal's own key from
    the installation folder `folder`. `canonical` gives the bytes a command is signed over (the store's
    canonical_bytes). Refused by name when the principal is not a host principal or its key does not
    sign; the owner's key is never read."""
    if principal not in HOST_PRINCIPALS:
        raise Refused('not_authorized', 'not a host principal of the space ledger')
    if not _is_str(operation) or not isinstance(parameters, dict):
        raise _invalid('command', 'an operation and a mapping of parameters')
    key = key_path(principal, folder)
    command = {'principal': principal, 'operation': operation, 'parameters': parameters,
               'command_id': command_id or 'space:' + uuid.uuid4().hex, 'nonce': uuid.uuid4().hex}
    try:
        done = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', key, '-n', NAMESPACE], input=canonical(command),
                              capture_output=True, timeout=30,
                              env={name: value for name, value in os.environ.items()
                                   if name not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')})
    except (OSError, subprocess.TimeoutExpired) as error:
        raise Refused('space_no_key:' + principal, str(error))
    if done.returncode:
        raise Refused('space_no_key:' + principal, 'the key of %s did not sign' % principal)
    return {'command': command, 'signature': done.stdout.decode()}


def _sibling(name):
    import importlib.util
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name + '.py')
    spec = importlib.util.spec_from_file_location('veldo_space_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None, stdin=None, stdout=None, stderr=None):
    """veldo space sign --as <host principal> [--installation <folder>]: read one command
    {operation, parameters} on standard input and print the packet signed as that host principal. The
    installation folder is the one the installation reader resolves. Exit 1 with the refusal's name when
    there is no installation, no key, or the principal is not a host principal."""
    import argparse
    stdin, stdout, stderr = stdin or sys.stdin, stdout or sys.stdout, stderr or sys.stderr
    parser = argparse.ArgumentParser(prog='veldo space')
    verbs = parser.add_subparsers(dest='verb', required=True)
    sign = verbs.add_parser('sign', help='sign one space command as a host principal')
    sign.add_argument('--as', dest='principal', required=True, choices=HOST_PRINCIPALS)
    sign.add_argument('--installation', help='the installation folder (default: the resolved one)')
    args = parser.parse_args(argv)
    try:
        folder = args.installation
        if not folder:
            resolved = _sibling('installation').resolve()
            if not resolved['found']:
                raise Refused('space_no_installation', 'no installation folder: there is no ledger')
            folder = resolved['folder']
        try:
            command = json.loads(stdin.read())
        except ValueError:
            raise _invalid('command', 'one JSON command on standard input')
        if not isinstance(command, dict):
            raise _invalid('command', 'one JSON command on standard input')
        packet = signed(args.principal, command.get('operation'), command.get('parameters'), folder,
                        _sibling('control_store').canonical_bytes, command.get('command_id'))
    except Refused as refusal:
        stderr.write('veldo space: refused %s\n' % refusal.code)
        return 1
    stdout.write(json.dumps(packet, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
