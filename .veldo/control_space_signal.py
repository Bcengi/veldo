#!/usr/bin/env python3
"""Signal: the one entry point an emitting process calls with an event (design sections 3 and 6.1,
VELDO-0301 and VELDO-0331), and the safety rules every removal passes (design section 7, VELDO-0330).

WHAT IS HERE. `signal`, and below it the rules. A call with an event does all of this in the calling
process and returns when it is done. Nothing is left for a later call, and no loop or timer comes back
to it:

  1 the ledger's own signal command marks every item the event ends as due (one journal record);
  2 each of them is carried out or left due, by the installation's switch and the mode of its scope;
  3 the kind registry gives each carried item its action and the order, children first, with rule 6's
     own reading (`inside`) as the look it is given and no other;
  4 a removal is judged by the rules and carried out by its remover, which is rule 7;
  5 the outcome of each carried item is written through the ledger's own commands before the next
     item is looked at.

WHO IS CARRIED OUT. An item the event made due is carried out when the installation's switch is on
(enabled in the space section) and either its scope is in act mode or the item carries the owner's
confirmation:

  switch off                  the call writes due and removes nothing
  act                         the item is carried out
  report, confirmed           the item is carried out: the owner confirmed its removal
  report, not confirmed       the item stays due and nothing else is done to it

The mode is read per item, from the ledger's mode record of that item's scope (the first part of its
owner: its project, its plain repository, or no project; design 4.7). There is no mode of the
installation: two projects that end on one event are judged each by its own record, and a scope with
no record is in report mode.

THE OUTCOMES, one per carried item, written before the call returns:

  removed    the rules passed and the remover removed it. The record holds the event, the emitter, the
             action, the method, the bytes and the free space of its pool before and after
  deferred   a rule refused. The record holds the deferral the rule names, the rule, the event it was
             refused at and the events that retry it. A refusal is a deferral, never an error. The
             item's next event makes it due again and it is judged again from rule 1
  gone       nothing is at the locator and nothing is under the item's marked name: someone removed
             the thing by hand. Read again by the probe at that moment. Not found is the kernel's
             own word and no other (GONE ONLY WHEN NOT FOUND, below)
  removing   the thing is not at its locator and is under its marked name: the remover's answer
             holds left_at (it could not put the folder back), or nothing is at the locator and the
             look under the marked name (the remover's `left`) found it. The record holds left_at. Such an item is never marked
             gone and never deferred: it is not at its path, and reconcile finishes it (design 8.8).
             It is also what a process killed inside a remover leaves, with no left_at
  kept       the table's action removes nothing (keep, measure, mark_contained, pass, or no cell for
             this event), or the action dropped caches and the item stays

THE ITEM IS REMOVING WHILE ITS REMOVER RUNS (design 4.1, VELDO-0345). When rules 1 to 6 have passed
for an action that takes the item away, the outcome removing is written, with the event, the emitter
and the action, and only then is the remover called: the keep step first, then the owning tool. A
remover that is not handed the item (the ledger refused that write) removes nothing, and the item is
deferred as remove_refused. A remover that puts the thing back and refuses (in_use at its second
probe, keep_failed at the keep step or its last look) leaves an item that is whole at its path, and
the item is written deferred with that deferral: the ledger accepts the three deferrals a remover
names for a removing item (VELDO-0345 AC6), so such an item is recorded as what it is and reconcile
does not finish it "to the end" (the review of VELDO-0300, finding 6). A process killed inside the
remover leaves the item removing, and reconcile completes it only with its keep record (design 0.2).
An action that drops caches takes nothing away, and its item stays due while it runs.

GONE ONLY WHEN NOT FOUND. An item is marked gone only when os.lstat said not found (ENOENT) at its
locator and again at its marked name. The probe's `located` reads the locator that way (exists is
False only for not found, and None with what was said for anything else) and the removers' `left`
reads the marked name that way and raises on anything else. A folder above the item that may not be
searched (mode 000, EACCES), a failing disk (EIO) or any other answer is "could not be read": rule 1
refuses, the item is deferred as not_in_ledger with what was said, and it is never gone. A look
under the marked name that raises defers the item as remove_refused. os.path.lexists answers False
for all of these, which once made a present item gone because its parent could not be read.

EVERY ITEM GETS AN OUTCOME. Nothing that raises stops the event. The rules catch what a rule, a
probe or a remover raises. Whatever raises outside them, while one item is carried out (the second
look at the locator, the look under the marked name, a write of the ledger), is caught for that
item alone: it is deferred as remove_refused, refused_by error, with what was raised, and the next
item is carried out. When the kind registry's due raises, no item has an action: every carried item
is deferred as remove_refused, refused_by registry, with what was raised, and none is handed to a
remover. When the deferral itself cannot be written, the call's answer holds the item with outcome
None, what was raised and what was meant, and goes on.

THE CARRIER. Every outcome this call writes holds carrier: {pid, started, seq}, the process that is
carrying the item out (its id and its start time, the probe's `carrier`) and the journal number of
this call's signal record, which is the run of Signal that holds the removal. It is on the removal
record from the moment the item is written removing, before its remover runs. Reconcile
(VELDO-0315 AC5) reads it to tell an item whose carrier is the same live process, which it must leave
alone, from one whose carrier died inside the remover, which it finishes. ONE REMOVER PER ITEM: the
ledger admits one removing write for a due item. A call whose removing write is refused because the
item is not due any more (another process, a second Signal or reconcile, made it removing first)
calls no remover and writes nothing over that record: its entry for the item holds no outcome, the
reason not_due, the state found and held_by, the carrier that holds it.

THE REMOVER'S OWN DEFERRAL IS PASSED THROUGH. Rule 7's refusal is named by the remover: remove_refused
(the tool, or the remover by itself, refused), in_use (its second probe found a user and the item was
put back) and keep_failed (the keep step failed, or the last look found work it did not save or a
tip it did not record). An answer that names none of the three is remove_refused.

AN ITEM THE REGISTRY HOLDS BACK (the action wait: an item inside it holds it, or its inside could not
be read) is deferred as in_use and is never judged or handed to a remover. An item whose table
version the registry does not hold is deferred as remove_refused. A rule, a probe or a remover that
raises is a refusal too: the item is deferred as remove_refused with what was raised, or kept removing
when the thing is under its marked name.

NO CLOCK. This module imports nothing and reads no time, no age and no date. An item is removed
because an event named it, and for no other reason: with the clock moved by any amount and no event,
nothing changes.

THE RULES (design section 7). `rules` judges one removal of one item. The seven rules run in the one
order of ORDER, and the first that refuses ends the run and names the deferral:

  1 ledger        not_in_ledger   the thing at the locator is not the item recorded
  2 protect       protected       the locator is at, above or beneath a protect entry
                                  (a container: or it mounts a protected volume or path, read
                                  from the engine again; mounts that cannot be read refuse.
                                  A Docker object: or the compose folder, compose file or
                                  compose project its labels name now is protected; labels
                                  that cannot be read refuse)
  3 owner_live    in_use          the owning run is not conclusive or its containment group is not
                                  empty; or the owning session's recorded process is the same live one
  4 process_use   in_use          a process, a container or git uses the path; a launcher's scratch
                                  whose lock is held or whose borrowed login is not settled
  5 unique_work   unique_work     the five cases of a worktree; an agent repository's branches
  6 children      in_use          an item inside this one is there in any state but removed or gone,
                                  or something on disk inside it is not recorded, or cannot be read
  7 tool          remove_refused  the owning tool's remove refuses; or in_use or keep_failed, when the
                                  remover names that as its own deferral

The answer is {ok: True, passed} or {ok: False, reason: space_deferred:<deferral>, rule, order,
deferral, found, passed}. Every fact is read by the probes at the moment of the call; none is carried
over from an earlier one. This function writes nothing: `deferral` gives the fields of the item's
deferral record (the rule that refused, the event it was refused at, the events that retry it) for the
caller that writes the outcome.

WHICH RULES A REMOVAL PASSES is APPLIES, by what the removal is for: remove (all seven), discard (the
owner's discard answer: rules 1, 2, 3, 4 and 6, then the tool) and review_scratch (rules 1, 2, 3, 4 and
6). Nothing passes fewer than rules 1 and 2: no event, no Confirm and no Discard removes a protected
thing, and the protect list is the ledger's, read again at every call.

RULE 1 reads what is at the locator, and says missing only for the kernel's not found; a path that
could not be read is refused with unread, what was said. A path must be there and lead to its own text: the recorded path
was resolved when it was declared, so one that now leads elsewhere goes through a link made since. A
worktree's folder must also be a worktree of the repository the item's branches are recorded in (its
agent repository when it lives inside one, else its project's or plain repository's). A Docker name
must be held by the object id the locator records. A volume has no id of its own, so its name must be
held by a volume the engine made at the time the locator records (created_at, VELDO-0306); a volume
recorded with neither is not proven by its name.

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
repository git cannot list. It also looks on disk beneath a worktree and beneath an agent repository
for git repositories nobody recorded (the probe's nested): one in a folder git ignores is no case of
unique work, git's non-forced worktree remove takes it, and its commits exist nowhere else. Each holds
the item, and so does a folder that could not be listed. `inside` is also the look the kind registry's
due is given.

THE TOOL (rule 7) is the callable `tool(identity, record)` the caller gives: the remover. It is called
only after every other rule of the removal has passed, and anything but {ok: True} is its refusal. Its
refusal is named by the deferral its answer holds when that is one of TOOL_DEFERRALS, and remove_refused
otherwise. With no tool the call judges and removes nothing.

NO CARRYING OUT BUT THIS ONE. `signal` once took `carry_out(identity, record)` and handed each
carried item to it with no rule, no look and no outcome. A call that gives it is refused by name,
space_carry_out_refused, before the ledger is asked anything: nothing is made due, and the callable
is never called. Every removal an event causes passes the rules and its remover.

ITEMS LEFT DUE. An item this call leaves due (the switch is off, its scope is in report mode and it
is not confirmed, or the caller gave no probe, registry or remover) is not matched by a later event:
the ledger's signal takes only present, kept and deferred items. Signal does not pick such an item
up at the next event, because a due item may also be one another process is carrying at that
moment, and nothing on a due item says which. They are carried by the owner's Confirm (VELDO-0320)
and by reconcile (VELDO-0315 AC6), which reads the carrier first.

WHAT IS NOT HERE. The modules are given, not imported: the probes, the kind registry and the removers
(with the keep step the removers are given, VELDO-0345). The owner's Confirm, which writes an item's
confirmation, is VELDO-0320. Unique work reserves one VELDO-0318 request; its settled Save and Discard run in the space worker. Review scratch uses the
remover with a fresh rules reader (VELDO-0336). Evidence files a copy holds are VELDO-0347 (their
action has no remover yet and is deferred as remove_refused), and the measuring of a measure cell and the
mark of a contained branch are their own tickets: here each of those items is kept, with the action
named. Reconcile, which finishes a removing item and an item left due by a process that died, is
VELDO-0315.

Standard library only. The ledger is the control_space.Ledger the caller passes in.
"""

SCHEMA = 'veldo.control_space_signal/v1'


REMOVALS = ('remove', 'stop_then_remove', 'remove_tag')  # the actions that take the item away
TOOLED = REMOVALS + ('drop_caches', 'remove_held')  # the actions a remover carries out, through the rules
NAMED = 20  # the most entries of one list written into an outcome


CARRY_OUT_REFUSED = 'space_carry_out_refused'


def signal(ledger, event, subject, carry_out=None, principal=None, command_id=None, probe=None, kinds=None,
           remover=None, emitter=None, free=None, keep=None, owner_live=None, landed=(), queued=None, run=None,
           proc=None, borrow_root=None):
    """Mark every item the event ends as due, carry out those that may be carried out, and write each
    outcome, all before returning.

    `probe`, `kinds` and `remover` are the control_space_probe, control_space_kinds and
    control_space_remove modules; without all three nothing is carried out and every item stays due.
    `emitter` names the process that called (written into each outcome). `free(pool record)` and
    `keep(identity, record)` are the removers' own parameters, the reader of free space and the keep
    step; `owner_live`, `landed`, `run`, `proc` and `borrow_root` are the rules'; `queued` is the kind
    registry's. `carry_out` is refused: a call that gives it writes nothing (above).

    Returns the ledger's answer with carried (the items carried out), left (the items left due),
    outcomes (one entry per carried item: item, action, outcome, and for a deferral its name and rule)
    and counts (removed, gone, kept, removing, left, and deferred by deferral)."""
    if carry_out is not None:
        return {'ok': False, 'reason': CARRY_OUT_REFUSED, 'event': event, 'items': [],
                'detail': 'Signal hands no item to a caller\'s own callable: every removal passes the rules '
                          'and its remover'}
    result = ledger.signal(event, subject, principal=principal, command_id=command_id)
    if not result['ok']:
        return result
    enabled = ledger.config.get('enabled') is True
    carried, left = [], []
    for identity in result['items']:
        record = ledger.item(identity) or {}
        if enabled and record.get('state') == 'due' and (
                ledger.acts((record.get('owner') or {}).get('scope')) or record.get('confirmed')):
            carried.append(identity)
        else:
            left.append(identity)
    if probe is None or kinds is None or remover is None:
        carried, left = [], left + carried
    groups = {event: carried}
    if event == 'admission_requested':
        groups = {}
        for identity in carried:
            ending = ledger.item(identity)['due']['event']
            groups.setdefault(ending, []).append(identity)
    outcomes = []
    for ending, selected in groups.items():
        if selected:
            outcomes.extend(_carry(ledger, probe, kinds, remover, ending, selected, emitter=emitter, free=free,
                keep=keep, owner_live=owner_live, landed=landed, queued=queued, run=run, proc=proc,
                seq=result.get('seq'), borrow_root=borrow_root))
    counts = {'removed': 0, 'gone': 0, 'kept': 0, 'removing': 0, 'left': len(left), 'deferred': {}}
    for entry in outcomes:
        if entry['outcome'] == 'deferred':
            counts['deferred'][entry['deferral']] = counts['deferred'].get(entry['deferral'], 0) + 1
        elif entry['outcome'] in counts:
            counts[entry['outcome']] += 1
    return dict(result, carried=carried, left=left, outcomes=outcomes, counts=counts)


def _plain(value, depth=0):
    """A value as plain data an outcome can hold: text, numbers, lists and dictionaries, a long list
    cut at NAMED entries, anything else as its text."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if depth > 6:
        return str(value)[:300]
    if isinstance(value, dict):
        return {str(key): _plain(item, depth + 1) for key, item in value.items() if key != 'commands'}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = sorted(value, key=str) if isinstance(value, (set, frozenset)) else list(value)
        return [_plain(item, depth + 1) for item in items[:NAMED]]
    return str(value)[:300]


def _raised(error):
    return '%s: %s' % (type(error).__name__, str(error)[:300])


def _carrier(probe, seq):
    """Who carries the items of this call: the running process as the probe reads it, {pid, started},
    and seq, the journal number of the call's signal record. A probe that cannot say leaves pid and
    started None, with what was raised: a carrier nobody could read is not a dead one."""
    try:
        held = dict(probe.carrier())
    except Exception as error:  # noqa: BLE001 - the carrier is a record, never a reason to stop the event
        held = {'pid': None, 'started': None, 'unread': _raised(error)}
    return dict(held, seq=seq)


def _carry(ledger, probe, kinds, remover, event, carried, emitter=None, free=None, keep=None, owner_live=None,
           landed=(), queued=None, run=None, proc=None, borrow_root=None, seq=None):
    """Carry out the due items `carried`, in the kind registry's order, and write the outcome of each.
    Returns one entry per item, whatever raised on the way."""
    # A reconciliation view selects items; safety still sees every project and child.
    ledger = getattr(ledger, 'removal_ledger', ledger)
    def look(identity, record):
        return inside(ledger, probe, identity, record, run)

    given = {'emitter': emitter, 'free': free, 'keep': keep, 'owner_live': owner_live, 'landed': landed,
             'run': run, 'proc': proc, 'borrow_root': borrow_root, 'carrier': _carrier(probe, seq)}
    try:
        entries = {entry['item']: entry
                   for entry in kinds.due(event, list(ledger.items().items()), queued=queued, look=look)}
    except Exception as error:  # noqa: BLE001 - a registry that raises defers every item and removes none
        return [_stopped(ledger, event, identity, None, given, error, 'registry') for identity in carried]
    order = [identity for identity in entries if identity in carried]
    order += [identity for identity in carried if identity not in entries]
    outcomes = []
    for identity in order:
        entry = entries.get(identity) or {'action': None}
        with ledger.item_lock(identity):
            try:
                outcomes.append(_carry_one(ledger, probe, remover, event, identity, entry, given))
            except Exception as error:  # noqa: BLE001 - an item that raises is deferred; the others are carried out
                outcomes.append(_stopped(ledger, event, identity, entry.get('action'), given, error, 'error'))
    return outcomes


def _stopped(ledger, event, identity, action, given, error, where):
    """The outcome of an item whose carrying out raised outside the rules: deferred as remove_refused,
    refused_by `where` (error, or registry), with what was raised. Nothing is removed by this. When
    the deferral cannot be written either, the entry says so and holds no outcome."""
    done = {'item': identity, 'action': action, 'outcome': None, 'raised': _raised(error)}
    try:
        record = ledger.item(identity) or {}
        if record.get('state') not in ('due', 'removing'):
            return dict(done, reason='not_due')
        wrote = ledger.outcome(identity, 'deferred', {
            'event': event, 'emitter': _plain(given['emitter']), 'action': action, 'carrier': given['carrier'],
            'rule': DEFERRAL['tool'], 'refused_by': where, 'order': None,
            'retry': list((record.get('ends_on') or {}).get('events') or ()), 'found': {'raised': done['raised']}})
    except Exception as second:  # noqa: BLE001 - a ledger that raises too: the entry is all there is
        return dict(done, refused=_raised(second), meant='deferred')
    if not wrote.get('ok'):
        return dict(done, refused=wrote.get('reason'), meant='deferred')
    return dict(done, outcome='deferred', deferral=DEFERRAL['tool'], rule=where)


def _missing(probe, record, run):
    """Whether nothing is at the item's locator, read again now. A Docker object is missing only when
    its engine was read and said it holds no such object. A path is missing only when the kernel
    said not found: exists is False for that alone, and a path that could not be read (exists None,
    with unread) is not missing."""
    facts = probe.located(record['kind'], record['locator'], run)
    if 'engine' in facts:
        return facts['read'] is True and facts['id'] is None and facts['said'] is not None
    return facts['exists'] is False and not facts.get('unread')


def _carry_one(ledger, probe, remover, event, identity, entry, given):
    """Carry out one due item by the registry's entry for it, and write its outcome."""
    action = entry.get('action')
    record = ledger.item(identity)
    done = {'item': identity, 'action': action, 'outcome': None}
    if record is None or record.get('state') != 'due':
        return dict(done, reason='not_due')
    if (record.get('disposition') or {}).get('state') == 'authorized':
        result = disposition(ledger, probe, remover, identity, **given)
        current = ledger.item(identity) or {}
        return dict(done, outcome=current.get('state'), result=result,
                    deferral=(current.get('deferral') or {}).get('rule'))
    facts = {'event': event, 'emitter': _plain(given['emitter']), 'action': action, 'carrier': given['carrier']}
    retry = list((record.get('ends_on') or {}).get('events') or ())

    def write(outcome, more, **noted):
        wrote = (ledger.gone(identity) if outcome == 'gone'
                 else ledger.outcome(identity, outcome, dict(facts, **more)))
        if not wrote.get('ok'):
            return dict(done, refused=wrote.get('reason'), meant=outcome, **noted)
        return dict(done, outcome=outcome, **noted)

    if action == 'wait':
        held = bool(entry.get('held_by')) or entry.get('reason') in ('children_not_read', 'children_not_passed')
        name = DEFERRAL['children'] if held else DEFERRAL['tool']
        return write('deferred', {'rule': name, 'refused_by': 'registry', 'order': None, 'retry': retry,
                                  'reason': entry.get('reason') or 'held', 'held_by': _plain(entry.get('held_by'))},
                     deferral=name, rule='registry')
    if action not in TOOLED:
        return write('kept', {})

    seen = {}

    def tool(identity, record):
        if action in REMOVALS:
            # Rules 1 to 6 have passed: the decision to remove is recorded before the remover runs.
            began = ledger.outcome(identity, 'removing', dict(facts))
            if not began.get('ok'):
                seen['not_begun'] = True
                seen['said'] = {'ok': False, 'deferral': DEFERRAL['tool'],
                                'said': 'the ledger did not record the removal: %s' % (began.get('reason'),)}
                return seen['said']
        review = {}
        if entry.get('first') == REVIEW_SCRATCH:
            def review_check():
                current = ledger.item(identity)
                if (not current or current.get('state') != 'removing' or current.get('owner_keep')
                        or current.get('owner') != record.get('owner')
                        or current.get('locator') != record.get('locator')):
                    return {'ok': False, 'deferral': 'in_use', 'found': 'the recorded item changed'}
                return rules(ledger, probe, identity, current, purpose=REVIEW_SCRATCH,
                             owner_live=given['owner_live'], run=given['run'], proc=given['proc'],
                             borrow_root=given['borrow_root'])
            review['review_check'] = review_check
        seen['said'] = remover.remove(ledger, probe, identity, record, action=action, free=given['free'],
                                      keep=given['keep'], run=given['run'], proc=given['proc'], **review)
        return seen['said']

    try:
        judged = rules(ledger, probe, identity, record, purpose=REMOVE, tool=tool, owner_live=given['owner_live'],
                       landed=given['landed'], run=given['run'], proc=given['proc'],
                       borrow_root=given['borrow_root'])
    except Exception as error:  # noqa: BLE001 - what could not be judged is refused, never removed
        judged = {'ok': False, 'rule': 'error', 'order': None, 'deferral': DEFERRAL['tool'],
                  'found': {'raised': _raised(error)}}
    if judged['ok']:
        said = seen.get('said') or {}
        scratch = {'review_scratch': said['review_scratch']} if 'review_scratch' in said else {}
        return write('removed' if action in REMOVALS else 'kept',
                     dict({key: _plain(said.get(key)) for key in ('method', 'bytes', 'bytes_source', 'pool',
                                                             'pool_free_before', 'pool_free_after', 'freed',
                                                             'host')}, **scratch))
    if seen.get('not_begun'):
        # The ledger admits one removing write for an item. When it refused this one because the item
        # is not due any more, another carrier holds the removal: nothing is written over its record.
        now = ledger.item(identity) or {}
        if now.get('state') != 'due':
            return dict(done, reason='not_due', state=now.get('state'),
                        held_by=(now.get('removal') or {}).get('carrier'))
    found = judged.get('found') or {}
    said = found.get('said') if judged['rule'] == 'tool' and isinstance(found.get('said'), dict) else {}
    path = record['locator'].get('path') if record.get('kind') in DISK_KINDS else None
    # The remover's own word, or the look under the marked name when nothing is at the locator. A thing
    # still at its path is not left anywhere, whatever sits at its marked name.
    left_at = said.get('left_at') or (
        remover.left(path, identity) if path and _missing(probe, record, given['run']) else None)
    refusal = {'rule': judged['deferral'], 'refused_by': judged['rule'], 'order': judged['order'],
               'retry': retry, 'found': _plain(found)}
    if said.get('review_scratch') is not None:
        refusal['review_scratch'] = said['review_scratch']
    if left_at and (judged['rule'] in ('tool', 'error') or found.get('missing') is True):
        return write('removing', dict(refusal, left_at=left_at), left_at=left_at, deferral=judged['deferral'],
                     rule=judged['rule'])
    if judged['rule'] == 'ledger' and found.get('missing') is True and _missing(probe, record, given['run']):
        return write('gone', {})
    result = write('deferred', refusal, deferral=judged['deferral'], rule=judged['rule'])
    if (result.get('outcome') == 'deferred' and judged['deferral'] == 'unique_work'
            and record['kind'] == 'worktree'
            and event in ('ticket_ended', 'project_ended', 'worktree_abandoned', 'released', 'run_finished')):
        # The deferral is written. A request that cannot be built is said and leaves it deferred:
        # the next event asks again, and nothing is removed meanwhile. A review worktree gets no
        # request of its own: it joins its scope's review group of the day (VELDO-0340).
        try:
            asked = _request(ledger, probe, remover, identity, record, given['landed'], given['run'])
        except Exception as error:
            result['request_refusal'] = _raised(error)
            return result
        result['decision_request'] = asked
        publish = getattr(ledger, 'disposition_publish', None)
        if asked.get('ok') and publish is not None:
            result['presentation'] = publish(identity)
    return result


def disposition(ledger, probe, remover, identity, free=None, owner_live=None, run=None, proc=None, **unused):
    """Carry a signed, settled disposition in the space worker, under the item lock.

    A refusal spends this authorization. A later event can raise a fresh request;
    it can never silently retry the old Discard against a new file list.
    """
    if ledger.config.get('enabled') is not True:
        return {'ok': False, 'reason': 'space_disabled'}
    with ledger.item_lock(identity):
        record = ledger.item(identity) or {}
        decision = record.get('disposition') or {}
        if record.get('state') != 'due' or decision.get('state') != 'authorized':
            return {'ok': False, 'reason': 'space_disposition_state'}
        choice = decision.get('choice')
        if choice not in ('save', 'discard'):
            return {'ok': False, 'reason': 'space_disposition_choice'}
        effect, owner = ledger.disposition_effect(identity, decision['request'])
        # The settled answer is this action for this item: a group pick, or the member pick that
        # names this member's index (VELDO-0342).
        if ledger.settled_action(effect, decision) != choice or owner != decision['by']:
            return {'ok': False, 'reason': 'space_disposition_unsettled'}
        facts = {'event': (record.get('due') or {}).get('event'), 'action': choice, 'carrier': _carrier(probe, None)}
        said = {}
        def tool(item, current):
            began = ledger.outcome(item, 'removing', facts)
            if not began.get('ok'):
                return {'ok': False, 'deferral': 'remove_refused', 'said': began}
            said.update(remover.remove(ledger, probe, item, current, action=choice, free=free,
                                       run=run, proc=proc))
            return said
        judged = rules(ledger, probe, identity, record, purpose=DISCARD, tool=tool,
                       owner_live=owner_live, run=run, proc=proc)
        if judged['ok']:
            return ledger.outcome(identity, 'removed', dict(facts, **said))
        found = judged.get('found') or {}
        said = found.get('said') if isinstance(found.get('said'), dict) else {}
        if said.get('left_at'):
            return ledger.outcome(identity, 'removing', dict(facts, left_at=said['left_at']))
        result = ledger.outcome(identity, 'deferred', dict(facts, rule=judged['deferral'],
                                found=_plain(found), retry=[]))
        if result.get('ok'):
            current = ledger.item(identity)
            try:
                result['decision_request'] = _request(ledger, probe, remover, identity, current,
                                                      unused.get('landed') or (), run)
            except Exception as error:
                result['request_refusal'] = _raised(error)
        return result


def _request(ledger, probe, remover, identity, record, landed, run):
    """Reserve the item's request, or for a review worktree its place in the day's review group:
    its terms, and the commit the worktree was at when they were read.
    The commit is read first, so a commit made while the lists are read leaves a request whose
    recorded commit is not the worktree's, and Save and Discard refuse it."""
    head = remover.disposition_head(record['locator']['path'])
    commits = _unlanded(ledger, probe, remover, record, landed, run)
    if commits is None:
        raise ValueError('the worktree cannot be read for its unlanded commits')
    proposal = remover.disposition_proposal(ledger, identity, record, commits)
    if _is_review_worktree(record):
        # One request per scope and day for review worktrees: the member's own entry of the terms
        # goes to the group, and the Ledger reads the day of this deferral.
        return ledger.request_group(identity, proposal['worktrees'][0], head)
    return ledger.request_disposition(identity, proposal, head)


def _unlanded(ledger, probe, remover, record, landed, run):
    """The unlanded commits a disposition request names, read as rule 5 reads them: against the
    shared repository for an agent's worktree, against the other refs of its own otherwise."""
    shared = _scope_repository(ledger, record) if _agent_repository(ledger, record) else None
    return remover.disposition_commits(probe, record['locator']['path'], landed, shared, run)


# ---------------------------------------------------------------------------------------------
# The safety rules (design section 7).
# ---------------------------------------------------------------------------------------------

# The one order. The first rule that refuses names the deferral.
ORDER = ('ledger', 'protect', 'owner_live', 'process_use', 'unique_work', 'children', 'tool')
DEFERRAL = {'ledger': 'not_in_ledger', 'protect': 'protected', 'owner_live': 'in_use', 'process_use': 'in_use',
            'unique_work': 'unique_work', 'children': 'in_use', 'tool': 'remove_refused'}
# What the remover means by its own refusal (VELDO-0300). Rule 7's deferral is the one it names.
TOOL_DEFERRALS = ('remove_refused', 'in_use', 'keep_failed')

REMOVE, DISCARD, REVIEW_SCRATCH = 'remove', 'discard', 'review_scratch'
# The rules a removal passes, by what it is for. The order is always ORDER's.
APPLIES = {
    REMOVE: ORDER,
    DISCARD: ('ledger', 'protect', 'owner_live', 'process_use', 'children', 'tool'),
    REVIEW_SCRATCH: ('ledger', 'protect', 'owner_live', 'process_use', 'children'),
}

DISK_KINDS = ('worktree', 'agent_repository', 'build_output', 'scratch', 'evidence', 'review_run_scratch',
              'review_run_build_output')
HOLDS_REPOSITORIES = ('worktree', 'agent_repository')  # the kinds a nested repository is looked for in
NOT_HOLDING_STATES = ('removed', 'gone')
REVIEW_SCRATCH_CASE = 3  # an untracked file git does not ignore: not unique work in a review worktree


# The labels that say whose a Docker object is, as (locator field, label): control_space_remove.OWNER_LABELS.
OWNER_LABELS = (('run_label', 'veldo.space.run'), ('compose_project', 'com.docker.compose.project'))


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
        if kind == 'volume' and locator.get('id') is None and locator.get('created_at'):
            # An engine gives a volume no Id (VELDO-0306): the volume under the name is the one recorded
            # when the engine shows one made at the recorded time. A recorded time that differs is a
            # volume made again; one the engine does not hold is missing.
            # CreatedAt is to the second, so a volume made again inside it has the same one (the review
            # of VELDO-0306, finding 5): each owner label the record holds is compared with the labels
            # the engine shows now. A volume that does not carry them is not the one recorded.
            made = facts.get('created_at')
            shown = facts.get('labels') if isinstance(facts.get('labels'), dict) else {}
            other = sorted(label for field, label in OWNER_LABELS
                           if field in locator and shown.get(label) != locator[field])
            if facts['said'] is None and made == locator['created_at'] and not other:
                return None
            return {'recorded_created_at': locator['created_at'], 'created_at': made,
                    'missing': facts['said'] is not None, 'labels_differ': other}
        if facts['id'] is None or locator.get('id') is None or facts['id'] != locator['id']:
            return {'recorded_id': locator.get('id'), 'id': facts['id'], 'missing': facts['id'] is None}
        return None
    at = facts['resolved'] if facts['exists'] and not facts['link'] else None
    if at != facts['path']:
        # missing is the kernel's not found and nothing else: a path that could not be read is unread.
        return {'path': facts['path'], 'resolved': facts['resolved'], 'link': facts['link'],
                'missing': facts['exists'] is False and not facts.get('unread'), 'unread': facts.get('unread')}
    if kind == 'worktree':
        agent = _agent_repository(ledger, record)
        recorded = agent['locator']['path'] if agent else _scope_repository(ledger, record)
        expected = probe.repository(recorded, given['run']) if recorded else None
        if expected is None or facts['repository'] != expected:
            return {'path': facts['path'], 'repository': facts['repository'], 'recorded_repository': expected}
    return None


def _rule_protect(ledger, probe, identity, record, given):
    facts = probe.protected(record['kind'], record['locator'], ledger.protect)
    if facts['protected']:
        return {'entry': facts['entry'], 'how': facts['how']}
    if record['kind'] == 'container':
        # A container that mounts what is protected is protected (design section 7; the review of
        # VELDO-0306, finding 2). Its mounts are read from the engine again, now, whatever was seen
        # when it was recorded; mounts that could not be read refuse the removal.
        held = probe.mounts(record['locator'], ledger.protect, given['run'])
        if held['protected']:
            return {'entry': held['entry'], 'how': held['how'], 'mount': held['mount']}
        if not held['read']:
            return {'entry': None, 'how': 'mounts_unread', 'unread': held['said']}
    if 'engine' in record['locator']:
        # A Docker object whose compose folder, compose file or compose project the protect list covers
        # is protected (design section 7; VELDO-0307). The locator holds what was seen when the item was
        # recorded, and the list may have been edited since: the labels are read from the engine again,
        # now, and every entry is read against them. Labels that could not be read refuse the removal.
        stamped = probe.labelled(record['kind'], record['locator'], ledger.protect, given['run'])
        if stamped['protected']:
            return {'entry': stamped['entry'], 'how': stamped['how'], 'path': stamped['path']}
        if not stamped['read']:
            return {'entry': None, 'how': 'labels_unread', 'unread': stamped['said']}
    return None


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
        # The reader's state goes with every deferral for process use: used, absent or refused with
        # the check that failed (VELDO-0344). A process the reader's table judged is in processes,
        # named by process id, task and fact; one that stayed unread carries the reason.
        return {'processes': facts['processes'], 'containers': facts['containers'], 'git': facts['git'],
                'unread': dict(unread, processes=reaching), 'reader': facts.get('reader')}
    if record['kind'] in ('scratch', 'review_run_scratch'):
        held = probe.scratch(path, given['borrow_root'])
        if held['in_use'] or not held['read']:
            return {'scratch': held}
    return None


def _rule_unique_work(ledger, probe, identity, record, given):
    kind = record['kind']
    if kind not in ('worktree', 'agent_repository'):
        return None
    path = record['locator']['path']
    # VELDO-0317: even a review scratch or a disposable worker clone must stay after
    # a no-space end. Read the committed end on every rule path, including reconnect
    # and retirement, before either exception can save and remove its uncommitted work.
    import json
    conn = getattr(ledger, 'conn', None)
    if conn is not None:
        # Only a no-space end records a worktree, and its classification names it: the other
        # dispatch records are passed over in the store and never parsed here.
        for (raw,) in conn.execute("SELECT data FROM entities WHERE kind='dispatch' AND instr(data, 'no_space')"):
            end = json.loads(raw).get('space_end') or {}
            tree = end.get('worktree')
            if tree and (tree == path or tree.startswith(path.rstrip('/') + '/')):
                return {'no_space_worktree': tree, 'classification': end['classification']}
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
    there under path:<its path> with the state unread. For a worktree and for an agent repository,
    also each git repository on disk beneath it that no such item records, ignored by git or not,
    under path:<its path> with the state unrecorded; when a folder beneath it cannot be listed, the
    item itself is there with the state unread. This is rule 6's reading and the look the kind
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
    if record.get('kind') in HOLDS_REPOSITORIES and path:
        beneath = probe.nested(path, recorded)
        if not beneath['read']:
            found['path:' + path] = 'unread'
        for where in beneath['repositories']:
            found.setdefault('path:' + where, 'unrecorded')
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
            named = DEFERRAL[name]
            if name == 'tool' and isinstance(found['said'], dict) and found['said'].get('deferral') in TOOL_DEFERRALS:
                named = found['said']['deferral']
            return {'ok': False, 'reason': 'space_deferred:' + named, 'item': identity,
                    'purpose': purpose, 'rule': name, 'order': order, 'deferral': named,
                    'found': found, 'passed': passed}
        passed.append(name)
    return {'ok': True, 'item': identity, 'purpose': purpose, 'passed': passed}


def deferral(refusal, event, record):
    """The facts of an item's deferral record (design 4.1) for a refusal `rules` returned: the deferral
    the first refusing rule names, that rule, the event it was refused at and the events that retry it,
    which are the item's own ending events. The ledger's outcome command adds the number of attempts."""
    return {'rule': refusal['deferral'], 'refused_by': refusal['rule'], 'order': refusal['order'],
            'event': event, 'retry': list((record.get('ends_on') or {}).get('events') or ())}
