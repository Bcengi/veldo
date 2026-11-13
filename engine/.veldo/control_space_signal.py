#!/usr/bin/env python3
"""Signal: the one entry point an emitting process calls with an event (design section 3, VELDO-0331),
and the safety rules every removal passes (design section 7, VELDO-0330).

WHAT IS HERE. The part of Signal that reads the mode, and below it the rules. A call marks the matching
items due through the ledger's own signal command, and then asks, item by item, for the mode of the scope
that item belongs to (the first part of its owner: its project, its plain repository, or no project):

  act      the item is handed to `carry_out`, in the calling process, before the call returns
  report   the item stays due and nothing else is done to it. The event wrote due and removed nothing

The mode is read per item, from the ledger's mode record of that item's scope (design 4.7). There is no
mode of the installation: two projects that end on one event are judged each by its own record, and a
scope with no record is in report mode.

THE RULES (design section 7). `rules` judges one removal of one item. The seven rules run in the one
order of ORDER, and the first that refuses ends the run and names the deferral:

  1 ledger        not_in_ledger   the thing at the locator is not the item recorded
  2 protect       protected       the locator is at, above or beneath a protect entry
  3 owner_live    in_use          the owning run is not conclusive or its containment group is not
                                  empty; or the owning session's recorded process is the same live one
  4 process_use   in_use          a process, a container or git uses the path; a launcher's scratch
                                  whose lock is held or whose borrowed login is not settled
  5 unique_work   unique_work     the five cases of a worktree; an agent repository's branches
  6 children      in_use          an item inside this one is there in any state but removed or gone,
                                  or something on disk inside it is not recorded, or cannot be read
  7 tool          remove_refused  the owning tool's remove refuses

The answer is {ok: True, passed} or {ok: False, reason: space_deferred:<deferral>, rule, order,
deferral, found, passed}. Every fact is read by the probes at the moment of the call; none is carried
over from an earlier one. This function writes nothing: `deferral` gives the fields of the item's
deferral record (the rule that refused, the event it was refused at, the events that retry it) for the
caller that writes the outcome.

WHICH RULES A REMOVAL PASSES is APPLIES, by what the removal is for: remove (all seven), discard (the
owner's discard answer: rules 1, 2, 3, 4 and 6, then the tool) and review_scratch (rules 1, 2, 3, 4 and
6). Nothing passes fewer than rules 1 and 2: no event, no Confirm and no Discard removes a protected
thing, and the protect list is the ledger's, read again at every call.

RULE 1 reads what is at the locator. A path must be there and lead to its own text: the recorded path
was resolved when it was declared, so one that now leads elsewhere goes through a link made since. A
worktree's folder must also be a worktree of the repository the item's branches are recorded in (its
agent repository when it lives inside one, else its project's or plain repository's). A Docker name
must be held by the object id the locator records.

WHAT CANNOT BE READ IS NOT FREE. An engine the client cannot read, a worktree or a repository git
cannot read, a process table that hides processes, a scratch folder that cannot be opened, a run nobody
answers for, an engine that cannot say what id a name has, an agent repository with no shared
repository to compare with: each refuses, by the rule that could not read. A probe's unread, its read
False and its None are in use or unique work, never free. Anything uncertain is deferred, never removed.

A PROCESS THE PROBE MAY NOT READ refuses only when it could reach the item (design section 7, bounded
fail closed). The probe lists every such process by process id and uid, with reach, the reason it could
hold the path: it runs as this user, the path's own permissions let it through, a parent could reach
it, a container mount is a way to the path, or it cannot be judged. A process of another uid that the path's permissions shut out, with none of the rest, has reach
None and does not refuse. The probe reads owner, group and mode with os.stat and each process's uid,
groups and parent from its status file, which every user may read, so it needs no root. It does need
the kernel's process table to show every process: under hidepid the rule refuses.

RULE 6 looks for itself. `inside` reads, at the moment of the call, every item the ledger records inside
this one, by its parent and by its path, in whatever state, and for an agent repository the worktrees
its own git folder registers and that are on disk. A child that is declared, present, due, deferred,
removing or kept holds its parent: removing an agent repository would take a kept worktree and its
uncommitted files with it. So does a registered worktree on disk that no live item records, and a
repository git cannot list. `inside` is also the look the kind registry's due is given.

THE TOOL (rule 7) is the callable `tool(identity, record)` the caller gives: the remover. It is called
only after every other rule of the removal has passed, and anything but {ok: True} is its refusal. With
no tool the call judges and removes nothing.

WHAT IS NOT HERE. `carry_out(identity, record)` is the carrying out of one due item: the remover and
the outcome it writes. Those are VELDO-0300 and 0301, and this module is given the callable. The
installation's switch, an item that carries the owner's confirmation, a deferred item's retry and an item
whose thing is missing are VELDO-0301 and 0320. No clock is read here.

Standard library only. The ledger is the control_space.Ledger the caller passes in.
"""

SCHEMA = 'veldo.control_space_signal/v1'


def signal(ledger, event, subject, carry_out, principal=None, command_id=None):
    """Mark every item the event ends as due, then carry out those of a scope in act mode and leave
    those of a scope in report mode due. Returns the ledger's answer with two lists added: carried (the
    items handed to `carry_out`) and left (the items left due)."""
    result = ledger.signal(event, subject, principal=principal, command_id=command_id)
    if not result['ok']:
        return result
    carried, left = [], []
    for identity in result['items']:
        record = ledger.item(identity) or {}
        if record.get('state') == 'due' and ledger.acts((record.get('owner') or {}).get('scope')):
            carry_out(identity, record)
            carried.append(identity)
        else:
            left.append(identity)
    return dict(result, carried=carried, left=left)


# ---------------------------------------------------------------------------------------------
# The safety rules (design section 7).
# ---------------------------------------------------------------------------------------------

# The one order. The first rule that refuses names the deferral.
ORDER = ('ledger', 'protect', 'owner_live', 'process_use', 'unique_work', 'children', 'tool')
DEFERRAL = {'ledger': 'not_in_ledger', 'protect': 'protected', 'owner_live': 'in_use', 'process_use': 'in_use',
            'unique_work': 'unique_work', 'children': 'in_use', 'tool': 'remove_refused'}

REMOVE, DISCARD, REVIEW_SCRATCH = 'remove', 'discard', 'review_scratch'
# The rules a removal passes, by what it is for. The order is always ORDER's.
APPLIES = {
    REMOVE: ORDER,
    DISCARD: ('ledger', 'protect', 'owner_live', 'process_use', 'children', 'tool'),
    REVIEW_SCRATCH: ('ledger', 'protect', 'owner_live', 'process_use', 'children'),
}

DISK_KINDS = ('worktree', 'agent_repository', 'build_output', 'scratch', 'evidence')
NOT_HOLDING_STATES = ('removed', 'gone')
REVIEW_SCRATCH_CASE = 3  # an untracked file git does not ignore: not unique work in a review worktree


def _scope_repository(ledger, record):
    """The repository the declarations name for the item's scope: its plain repository, or its
    project's. None when they name none."""
    scope = (record.get('owner') or {}).get('scope') or {}
    if scope.get('type') == 'plain_repository':
        return scope.get('id')
    for project in ledger.projects:
        if scope.get('type') == 'project' and project.get('project') == scope.get('id'):
            return project.get('repository')
    return None


def _agent_repository(ledger, record):
    """The agent repository item a worktree lives inside, or None."""
    parent = ledger.item(record['parent']) if record.get('parent') else None
    return parent if parent is not None and parent.get('kind') == 'agent_repository' else None


def _is_review_worktree(record):
    """The row worktree_review_run of the kind registry: a worktree added detached inside a review run."""
    owner = record.get('owner') or {}
    run = owner.get('run') or {}
    return (record.get('kind') == 'worktree' and run.get('station') == 'review'
            and not owner.get('ticket') and not record.get('branch'))


def _rule_ledger(ledger, probe, identity, record, given):
    kind, locator = record['kind'], record['locator']
    facts = probe.located(kind, locator, given['run'])
    if 'engine' in facts:
        if not facts['read']:
            return {'unread': facts['said'], 'engine': facts['engine']}
        if facts['id'] is None or locator.get('id') is None or facts['id'] != locator['id']:
            return {'recorded_id': locator.get('id'), 'id': facts['id'], 'missing': facts['id'] is None}
        return None
    at = facts['resolved'] if facts['exists'] and not facts['link'] else None
    if at != facts['path']:
        return {'path': facts['path'], 'resolved': facts['resolved'], 'link': facts['link'],
                'missing': not facts['exists']}
    if kind == 'worktree':
        agent = _agent_repository(ledger, record)
        recorded = agent['locator']['path'] if agent else _scope_repository(ledger, record)
        expected = probe.repository(recorded, given['run']) if recorded else None
        if expected is None or facts['repository'] != expected:
            return {'path': facts['path'], 'repository': facts['repository'], 'recorded_repository': expected}
    return None


def _rule_protect(ledger, probe, identity, record, given):
    facts = probe.protected(record['kind'], record['locator'], ledger.protect)
    return {'entry': facts['entry'], 'how': facts['how']} if facts['protected'] else None


def _rule_owner_live(ledger, probe, identity, record, given):
    owner = record.get('owner') or {}
    recorded = record.get('process')
    if recorded is not None:
        if not isinstance(recorded, dict) or 'pid' not in recorded or 'started' not in recorded:
            return {'process': recorded, 'unread': 'the recorded process has no id and start time'}
        seen = probe.process(recorded['pid'], given['proc']) if given['proc'] else probe.process(recorded['pid'])
        if seen is not None and seen['live'] and seen['start'] == recorded['started']:
            return {'process': seen}
    if owner.get('run') or owner.get('gate'):
        read = given['owner_live'](owner) if given['owner_live'] else None
        if not isinstance(read, dict) or read.get('conclusive') is not True or read.get('group_empty') is not True:
            return {'run': owner.get('run'), 'gate': owner.get('gate'), 'read': read}
    return None


def _rule_process_use(ledger, probe, identity, record, given):
    if record['kind'] not in DISK_KINDS:
        return None
    path = record['locator']['path']
    reads = {'run': given['run']}
    if given['proc']:
        reads['proc'] = given['proc']
    facts = probe.in_use(path, ledger.engines, **reads)
    unread = facts['unread']
    reaching = [entry for entry in unread['processes'] if entry.get('reach') is not None]
    if (facts['in_use'] or reaching or unread['engines'] or unread['table'] is not None
            or unread['git'] is not None or not facts['git']['read']):
        return {'processes': facts['processes'], 'containers': facts['containers'], 'git': facts['git'],
                'unread': dict(unread, processes=reaching)}
    if record['kind'] == 'scratch':
        held = probe.scratch(path, given['borrow_root'])
        if held['in_use'] or not held['read']:
            return {'scratch': held}
    return None


def _rule_unique_work(ledger, probe, identity, record, given):
    kind = record['kind']
    if kind not in ('worktree', 'agent_repository'):
        return None
    path = record['locator']['path']
    if kind == 'agent_repository' or _agent_repository(ledger, record):
        shared = _scope_repository(ledger, record)
        if shared is None:
            return {'unread': 'the declarations name no shared repository for this item'}
    else:
        shared = None
    if kind == 'agent_repository':
        facts = probe.agent_repository(path, shared, given['run'])
        if facts['read'] is not True or facts['unique_work'] is None:
            return {'unread': facts.get('said')}
        if facts['unique_work'] is not False:
            return {'not_across': facts['not_across'], 'more': facts['more'], 'refs': facts['refs'],
                    'stashes': facts['stashes']}
        return None
    facts = probe.unique_work(path, given['landed'], shared, given['run'])
    if facts['read'] is not True or facts['unique_work'] is None:
        return {'unread': facts.get('said')}
    cases = [case for case in facts['cases']
             if not (case == REVIEW_SCRATCH_CASE and _is_review_worktree(record))]
    if cases:
        return {'cases': cases, 'branch': facts['branch'], 'commit': facts['commit'],
                'modified': facts['modified'], 'staged': facts['staged'], 'untracked': facts['untracked'],
                'operation': facts['operation'], 'unlanded': facts['unlanded'], 'more': facts['more']}
    return None


def inside(ledger, probe, identity, record, run=None):
    """What is inside the item `identity` now, as {identity: state}: every item the ledger records
    with this one as its parent, or at a path beneath this one's, in whatever state; and, for an agent
    repository, each worktree its own git folder registers that is on disk and that no item which is
    neither removed nor gone records, under the name path:<its path> with the state unrecorded
    (on_disk when it cannot be said whether the folder is there). A repository git cannot list is
    there under path:<its path> with the state unread. This is rule 6's reading and the look the kind
    registry's due is given: look=lambda identity, record: inside(ledger, probe, identity, record)."""
    path = (record.get('locator') or {}).get('path') if record.get('kind') in DISK_KINDS else None
    found, recorded = {}, set()
    for child, other in ledger.items().items():
        where = (other.get('locator') or {}).get('path') if other.get('kind') in DISK_KINDS else None
        if where and other.get('state') not in NOT_HOLDING_STATES:
            recorded.add(where)
        if child != identity and (other.get('parent') == identity or (
                path and where and where != path and where.startswith(path.rstrip('/') + '/'))):
            found[child] = other.get('state')
    if record.get('kind') == 'agent_repository' and path:
        listed = probe.worktrees(path, run)
        if not listed['read']:
            found['path:' + path] = 'unread'
        for tree in listed['worktrees']:
            if tree['there'] is not False and tree['path'] not in recorded:
                found['path:' + tree['path']] = 'unrecorded' if tree['there'] else 'on_disk'
    return found


def _rule_children(ledger, probe, identity, record, given):
    held_by = {child: state for child, state in inside(ledger, probe, identity, record, given['run']).items()
               if state not in NOT_HOLDING_STATES}
    return {'items': sorted(held_by), 'states': held_by} if held_by else None


def _rule_tool(ledger, probe, identity, record, given):
    said = given['tool'](identity, record)
    return None if isinstance(said, dict) and said.get('ok') is True else {'said': said}


RULES = {'ledger': _rule_ledger, 'protect': _rule_protect, 'owner_live': _rule_owner_live,
         'process_use': _rule_process_use, 'unique_work': _rule_unique_work, 'children': _rule_children,
         'tool': _rule_tool}


def rules(ledger, probe, identity, record, purpose=REMOVE, tool=None, owner_live=None, landed=(), run=None,
          proc=None, borrow_root=None):
    """Judge one removal of the item `identity`, whose ledger record is `record`, by the safety rules
    in their order, and stop at the first that refuses.

    `probe` is the control_space_probe module. `purpose` is what the removal is for (APPLIES). `tool`
    is rule 7, the remover: tool(identity, record) -> {ok: True, ...} or its refusal; with none, the
    call judges and nothing is removed. `owner_live(owner)` answers for the item's owning run or gate
    with {conclusive, group_empty}; with no answer the run is not known to have ended, and rule 3
    refuses. `landed` holds the source commits of completed landings (rule 5). `run`, `proc` and
    `borrow_root` are the probes' own parameters: the client runner, the process table and the
    launcher's journal root."""
    if purpose not in APPLIES:
        raise ValueError('not a purpose of removal: %r' % (purpose,))
    given = {'tool': tool, 'owner_live': owner_live, 'landed': landed, 'run': run, 'proc': proc,
             'borrow_root': borrow_root}
    passed = []
    for order, name in enumerate(ORDER, 1):
        if name not in APPLIES[purpose] or (name == 'tool' and tool is None):
            continue
        found = RULES[name](ledger, probe, identity, record, given)
        if found is not None:
            return {'ok': False, 'reason': 'space_deferred:' + DEFERRAL[name], 'item': identity,
                    'purpose': purpose, 'rule': name, 'order': order, 'deferral': DEFERRAL[name],
                    'found': found, 'passed': passed}
        passed.append(name)
    return {'ok': True, 'item': identity, 'purpose': purpose, 'passed': passed}


def deferral(refusal, event, record):
    """The facts of an item's deferral record (design 4.1) for a refusal `rules` returned: the deferral
    the first refusing rule names, that rule, the event it was refused at and the events that retry it,
    which are the item's own ending events. The ledger's outcome command adds the number of attempts."""
    return {'rule': refusal['deferral'], 'refused_by': refusal['rule'], 'order': refusal['order'],
            'event': event, 'retry': list((record.get('ends_on') or {}).get('events') or ())}
