#!/usr/bin/env python3
"""The space ledger: the item, pool, hold, reconcile and mode records in the control store (VELDO-0297,
VELDO-0331).

WHAT THIS MODULE IS. The one record of what Veldo has on disk and in Docker, kept as entities of the
existing control store, and the only writer of them. Every write is one registered command of the store:
one transaction, one signed journal record, no second database. The journal record holds the whole item
(its kind, owner, locator and state), so paths and object names are recorded and file contents never are.

THE RECORDS, each an entity kind this module owns (design 4.1 to 4.4 and 4.7):

  space_item       space:item:<new id>. One per thing. kind, host, pool, locator, parent, owner, creator,
                   adopted, branch, start, process, state, ends_on, size, confirmed, deferral, removal, report,
                   and kept once a keep record was written.
  space_pool       space:pool:<host>:<name>. type (filesystem or engine_image), device, engine, floor,
                   returns_space, backing.
  space_hold       space:hold:<identity>. scope, needs and source per pool, state, reason, used, retry_asked,
                   freed.
  space_reconcile  space:reconcile:<new id>. What started it, the roots and engines read, and the counts.
  space_mode       space:mode:<scope>. scope, mode (report or act), since, history.
  space_run        space:run:<identity>. The run or gate identity the authority issued, and the principal
                   it was issued to (VELDO-0326).
  space_packet     space:packet:<principal>:<nonce>. One signed packet a host principal sent: its digest,
                   when it was issued and seen, and what became of it (VELDO-0326).
  space_event      space:event:<new id>. A hook's type, subject, emitter and journal order; received
                   until the child records consumed with the exact items made due (VELDO-0323).

ONLY THIS MODULE WRITES THEM. Attaching declares the eight kinds and their id prefixes with the store's
declare_owners, bound to this file's bytes. From then on the store's generic entity command is refused
entity_owned for them on every connection, and so is any other command.

AN ITEM'S STATES AND THE ONLY MOVES (design 4.1):

  declare            nothing to declared
  confirm            declared to present
  signal             present, kept or deferred to due; never an item the owner marked Keep, unless the
                     signal names that item and is the owner's Abandon of it (THE OWNER'S KEEP, below)
  outcome removing   due to removing (the rules passed; the decision to remove is recorded)
  outcome removed    due or removing to removed; refused for a worktree and an agent repository that
                     has no keep record (space_no_keep_record), or whose keep record was written
                     before the item last became due or removing (space_keep_stale)
  outcome deferred   due to deferred; removing to deferred only with one of the three deferrals a remover
                     names (TOOL_REFUSALS: remove_refused, in_use, keep_failed; design section 7 rule 7),
                     which are read while the remover runs
  outcome kept       due to kept. A removing item is removed to the end: the decision was recorded
  outcome removing   written again for a removing item only to record where its thing was left (left_at)
  keep               writes the keep record of a due or removing worktree or agent repository; moves nothing
  keep branch        records the kept branch a settled Discard made for a removing, detached worktree as a
                     branch item in state kept (THE KEPT BRANCH OF A DISCARD, below); moves the worktree nowhere
  gone               declared, present, due or deferred to gone
  adopt              nothing (or a report record) to present, adopted
  measure, rebranch  write fields and move nothing

Every other move is refused as space_item_state:<the state the item is in>, with nothing written.

DECLARE REFUSES, each by name, with nothing written:

  space_protected:<entry>   the locator is on the protect list. A path is protected when it is at, above
                            or beneath a protected path; a Docker object when its name matches a pattern
                            for its type on its engine, or its compose project is a protected one.
                            An image pattern with no tag and no digest covers every tag and every
                            digest of its repository; one with a tag or a digest covers that one only.
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

CALLERS PASS RESOLVED PATHS. A path named through a linked root is refused, never recorded under where
it leads, and the same rule holds for the repository a worktree's branches are in (its project's or plain
repository's declared repository): a worktree whose repository is declared through a link is refused at
declare and adopt as space_locator_link, so rebranch never meets a repository it would have to refuse.
Declared by its resolved path, the repository is the one its branch items are recorded under. The roots
are resolved once, when the ledger is built: a root that becomes a link later is seen by a new ledger.

KNOWN ROOTS are the roots the declarations name: each project's and each plain repository's worktree
root, the state root, the scratch roots and the build roots. They come from what the declarations reader
returned (control_space_config.read and read_project); this module opens no declaration itself.

THE POOL of a disk item is the filesystem pool whose device identity is the device the item's path is on,
so two paths on one filesystem count against one pool. A Docker item counts against its engine's image
pool when the engine has one, else against the pool its caller names.

THE KEEP RECORD (VELDO-0345, design 0.2, 0.3, 4.1 and 6.1). Before a worktree or a private repository is
removed, every commit it reaches is on a kept ref in its main repository and, where the removal saves one,
its uncommitted files are in a snapshot under the state root. keep writes that on the item, as kept:

  repository   the main repository: the one the declarations name for the item's scope, never a private
               repository
  path         the path the item had
  refs         {kept ref: commit}, each under refs/veldo/kept/<ticket>/<item>/<attempt>/ (kept_prefix,
               then the number of the keep attempt that wrote the ref)
  snapshots    one entry per snapshot attempt: path, number, size and the digest of its manifest
  attempt      the keep attempt this removal stands on: {number, head}, the number of the attempt whose
               refs the last keep write named and the commit the Ledger itself read as the item's HEAD
               then (each None for an item with no commit at all). None from the moment the item is
               marked due, or written removing, until its keep step writes again

THE LEDGER READS WHAT IT RECORDS. keep trusts nothing its caller says. Inside the command's own transaction
it reads the main repository with git, through the one Git boundary, and refuses a ref that is not there
at the commit named (space_keep_ref:<ref>); it refuses a repository that is not the one the declarations
name for the item or is not at its path (space_keep_repository), one that is, or lies inside, an agent
repository (space_keep_private), a snapshot path that is not the numbered folder of that item in the
snapshot store (space_keep_snapshot), and a manifest whose bytes do not have the digest named
(space_keep_manifest). An item that is not due or removing is space_item_state:<state>.

THE LEDGER READS THE ITEM'S HEAD ITSELF. keep runs git in the item, at its locator, and reads the commit
HEAD names. That commit must be the one the write names as <attempt>/head, a ref the Ledger has just read
in the main repository: a write without it is space_keep_head, and so is an empty record for an item
that has a HEAD commit. Only an item git reads no HEAD commit in may have a record with no kept head. An
item git cannot read at its locator is space_keep_item. The refs of one write are those of one attempt.

A KEEP RECORD IS OF ONE REMOVAL. signal, which marks the item due, and the outcome removing for a due
item both clear the record's attempt; only a keep write sets it. The outcome removed is refused,
space_keep_stale, while it is clear. So a record an earlier attempt wrote, before the item was deferred
and went on changing, never stands for a later removal: a process killed after removing was written and
before its keep step leaves a record that neither the Ledger nor control_space_keep.verify accepts.

A KEEP WRITE ADDS AND NEVER REMOVES. For an item that has a record, the refs and the attempt are added to
it. A ref the record holds at another commit is space_keep_ref_moved:<ref>, an attempt number the record
holds with other figures is space_keep_snapshot_replaced, and nothing a keep command is given takes a ref
or an attempt off the record. The journal holds each version.

THE KEPT BRANCH OF A DISCARD (VELDO-0343, design 6.5). A detached worktree can hold a commit no ref
reaches. Before the discard remover removes such a worktree it creates a branch at the checked-out commit,
and keep_branch records that branch as a branch item in state kept, with its name (the locator's ref),
its commit (start, and kept_branch.commit) and the worktree it was made for (kept_branch.worktree). The
Ledger trusts nothing its caller says: inside the command's transaction it reads, through the one Git
boundary, the worktree's HEAD and the branch in the main repository of the worktree's scope (never in
an agent repository, which is private and is removed later: design 0.2, VELDO-0343 fix round 1), and
refuses a branch that is not there at that commit (space_keep_branch_ref), a commit that is not the
worktree's HEAD (space_keep_branch_head), a worktree that is on a branch (space_keep_branch_attached),
and a worktree that is not removing under an authorized Discard (space_keep_branch_state). A branch
item already at the locator is written kept when it is declared, present or kept, with the same fields;
in any other state the command is refused. It is a record of a ref write: it makes no commit, removes
nothing, and writes no event record.

THE OWNER'S KEEP IS ABSOLUTE (design 0.4, VELDO-0312 fix round). The state kept is two things: an item
whose table action at its last event removes nothing (a worktree measured at run finished, a branch),
which the next event must reach, and an item the owner answered Keep for, which nothing may reach. So
the owner's Keep is its own mark on the item, owner_keep: {by, at, and what the writer says of the answer}.
It is written by the outcome kept whose facts hold owner_keep, and by nothing a host principal may sign
(space_not_permitted:space_disposition). An item that holds the mark is never made due by a signal that
names an owner, whatever the event: run finished, verdict recorded, landed, contained, ticket ended,
project ended, worktree abandoned, released or session ended. Signal is the only command that writes due,
so a retry, a Confirm, a sweep and a reconcile, which all make an item due through it, do not reach the
item either. Only one command ends it: a signal of worktree abandoned whose subject names that exact
item, at the version the owner saw, and says it is the owner's Abandon of that item (owner_abandon:
{item, at}). The mark is then cleared, who abandoned it is written on the item (abandoned), and the item
is due and meets every rule again: one with unique work is deferred and stays until the owner's Discard,
which saves first. A named item that holds the mark and is not that exact item refuses the whole command
as space_owner_keep:<item>.

THE LEDGER CHECKS THE OWNER ITSELF (VELDO-0312 fix round 2). The mark and the Abandon are not trusted to
their caller. The transition that writes owner_keep, and the one that takes an owner_abandon, each read
the membership of this store inside the command's own transaction, with the control_membership module
beside this file, and refuse not_authorized unless the command the store is running is the one this
Ledger sent for it (such a command given to the store directly is refused, whoever it names) and its
principal is an active person member holding project_owner whose scope covers the space scope, at the
time the request gives as `at`: the owner of the mode switch. So the authority's own principal, a person
who is not the owner, a service and a command with no principal write no Keep and end none, whoever
calls. Who is written on the item (owner_keep.by, abandoned.by) is that verified principal and nothing
else: a request that carries a `by` of its own is refused as invalid input. What is not checked here is
a signature of the owner over the command: the Abandon's signature is the API edge's, verified by the API
authority, and the owner's signed Keep is the disposition command of VELDO-0318 (its AC4), which is
verified as set_mode verifies the mode switch.

A SIGNAL THAT NAMES ITEMS (VELDO-0312 fix round; a capability of the ledger, for every sender). The
subject of a signal is either the parts of an owner, and then every item of that owner the event ends
is made due, or a list of items: {items: [{item, version}, ...]}, each with the version its sender read.
The ledger then acts on exactly those items and on nothing else of their owners. The command is refused
whole, with nothing written, when a named item is not an item (space_no_item), is at another version
than the one named (space_item_version:<item>), is not present, kept or deferred
(space_item_state:<state>), does not end on the event (space_item_event:<item>), or holds the owner's
Keep (space_owner_keep:<item>). The store commits against the versions named, so an item that changes
between the read and the commit refuses too. A host principal signs no such signal.

THE SNAPSHOT STORE IS PROTECTED IN EVERY INSTALLATION. <state root>/space-saved is on this Ledger's protect
list whatever the declarations say: it is put there by the Ledger and not by a file. So declare, adopt and
report refuse a locator at, above or beneath it as space_protected, and rule 2 refuses any removal there.

WHAT IS NOT HERE. The lifecycle table is the kind registry's (VELDO-0298); this module is given it as
plain data and copies an item's events from it at declaration, with its version. Rules, probes and
removers, and the wrong-proposal and review group records are separate tickets. The Ledger reads no
clock: accept and set_mode are given the time. The sending side stamps a packet with the time its caller
gives it; only the command line entry reads a clock, once, for that.

MODE (VELDO-0331, design 2, 4.7 and 6.1). Report or act is one value per scope: each project, each plain
repository, and no project. It is a record of this store and of nothing else: space:mode:project:<id>,
space:mode:plain_repository:<its repository> and space:mode:no_project. A scope with no record is in
report mode, which is not an error. There is no mode of the installation and no file holds one.

The only entry is set_mode, and it takes the owner's signed command and nothing less: the packet
{command, signature} whose command names the principal, the operation space_mode, the scope and the new
mode, its own command id and its nonce. The signature is verified against the principal's active key in
this store's keyring, and the principal must be an active person member holding project_owner whose scope
covers the space scope. Anyone else is refused not_authorized, a host principal by the rule above as
space_not_permitted:space_mode, and a scope the declarations do not name as space_unknown_scope, each
with nothing written. The command commits against the versions of the membership and the key it was
checked with, and consumes the owner's nonce, so a packet sent again writes nothing.

A switch is one journal record. The mode record holds the scope, the mode, since (when the current mode
began and the owner's signed command that set it) and history: every switch, the current one last, each
with from, to, when and the owner's command with its signature. A switch back to report is accepted at
once, whatever the scope's state. A command for the mode the scope is already in is accepted and writes
nothing.

THE LEDGER CHECKS THE MODE COMMAND ITSELF. set_mode is not trusted by the transition that writes the
record. Inside the command's own transaction the transition reads the membership and the keyring of this
store with the control_membership module beside this file, and refuses not_authorized unless: the command
the store is running is the one this Ledger sent for it (a space_mode command given to the store directly
is refused, whoever it names); its principal, command id and nonce are the signed command's own; that
principal is the owner as above; and the signature verifies over the signed command. So a space_mode
command from the authority, or from anyone, with a signature that is not the owner's writes nothing.

ACT IS REFUSED UNTIL ITS CONDITIONS ARE BUILT. What a switch to act requires is two later tickets:
three clean report days (VELDO-0332) and no unconfirmed pending group (VELDO-0339). ACT_CONDITIONS names
each condition with the ticket that builds its check. A Ledger is given the checks it has as act_checks,
{condition: check(scope)}, where a check returns None or the reason it refuses. The transition refuses a
switch to act as space_act_unbuilt:<the tickets whose check is missing> while any is missing, and as
space_act_refused:<condition> when a check refuses. Nothing in this repository installs a check yet, so
no scope can be put in act; each of the two tickets installs its own and so removes its part of the
refusal. A switch back to report reads none of this.

A HOLD KEEPS ITS SCOPE (design 6.7). The hold record holds the scope the run belongs to. For a run or
gate the authority issued with a scope (issue's scope), the hold takes that scope and a different one
named with the hold is refused space_hold_scope; otherwise it is the scope place_hold is given, else no
project. A host principal's packet names no scope. admit reads the mode of the hold's own scope inside
its transaction and refuses the answer advised for a hold of a scope in act mode as
space_answer_mode:act: an act-mode run waits, it is never started on advice.

WHO READS THE MODE. mode_of and acts answer for one scope. Signal (control_space_signal.py), admission
(control_space_admission.py) and reconcile's adoption rule (control_space_reconcile.py) each ask for the
scope the item or the run belongs to, never for the installation.

WHO SIGNS A COMMAND (VELDO-0326, design 6.11). A git hook and a gate helper write to the ledger without
the owner's key. Two host principals exist for that, each with its own key, made when the service is
installed and kept under keys/ in the installation folder, and each enrolled by the owner's signed
enroll_principal as a service whose scope is the one named scope "space" (which covers no repository, so
the store's generic commands stay refused for both):

  space-observer   the hooks. It may sign declare and confirm for a worktree, a branch, an agent
                   repository and a session's scratch; rebranch; event; and the read behind covers.
  space-runner     the gate space helper and the run wrapper. What space-observer may, and for the run or
                   gate issued to it: declare, confirm, measure, hold, admit, release, signal and outcome.
                   It signals only run finished and verdict recorded, and only for exactly that run or
                   gate.

A RUN OR GATE IS THE RUNNER'S ONLY WHEN THE AUTHORITY ISSUED IT TO THE RUNNER. issue() is the authority's
command: it makes the identity (a label the caller may give, then a part nobody can predict) and writes
the record space:run:<identity> naming the principal it is issued to. No host principal signs issue. The
rule reads that record and nothing else, so who names a run first decides nothing: space-runner is
refused a hold, a declare and a signal for an identity nobody issued to it (a dispatch's unit, station and
attempt, however predictable), and an item space-observer declares into a run makes nobody its owner.

Every other command is refused from both as space_not_permitted:<the command's name>, with nothing
written, and so is every owner action: adopt, abandon (worktree abandoned sent as a signal is
space_abandon), confirm of a group, reconcile, marking a proposal wrong, the mode switch, a change to the
protect list and an answer to a space disposition request (the owner's Keep written with an outcome is
one: space_disposition). The rule is a list of what each may sign, so a
command a later ticket adds is refused until this list names it.

accept() takes the packet a hook or helper sent: it verifies the signature against the principal's active
key in the store's own membership and keyring, then applies the rule, then runs the command with the
principal recorded on the journal record. Each refusal is in the observations with the principal and the
command's name.

A PACKET EXPIRES AND IS TAKEN ONCE. The signed command carries issued_at, the time it was signed, and its
nonce. accept refuses a packet whose issued_at is more than PACKET_AGE (300 seconds, five minutes) behind
the time it is given as space_packet_expired, and one more than PACKET_SKEW (60 seconds) ahead of it as
space_packet_ahead. Every packet whose signature verified and whose time is inside the bound leaves the
record space:packet:<principal>:<nonce>, whatever became of it: an accepted command writes it in its own
transaction (and the store's nonces table consumes the packet's nonce), a refused one and an accepted one
that wrote nothing are recorded by the Ledger's own command. A nonce that has a record is refused as
space_packet_replayed, so a packet that was refused is never accepted later, whatever changed since.
The one exception is the honest resend: the same packet, sent again after it was accepted, is answered
with the original answer and replayed true, and writes nothing. The same packet is the same nonce and the
same content (principal, operation, parameters and command id); the time it was signed at is not part of
that, so a sender that kept a packet through an outage signs it again under its nonce and learns what
became of it. The resend is bounded like every packet: bytes older than the bound are
space_packet_expired, whatever the record says. The record is kept, so the nonce is refused for good to
every other command, not only inside the bound; the bound is what stops a packet nobody delivered in
time.

Standard library only. The store is the control_store module the caller passes in, and accept is given the
control_membership module the same way.
"""
import contextlib
import fcntl
import stat
import threading
import fnmatch
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import uuid

SCHEMA = 'veldo.control_space/v1'
OWNER = 'space_ledger'
_git_process = None  # the one Git boundary, the sibling of this file, loaded when keep first reads a ref

ITEM_KIND, POOL_KIND, HOLD_KIND, RECONCILE_KIND = 'space_item', 'space_pool', 'space_hold', 'space_reconcile'
ITEM_PREFIX, POOL_PREFIX, HOLD_PREFIX, RECONCILE_PREFIX = ('space:item:', 'space:pool:', 'space:hold:',
                                                           'space:reconcile:')
MODE_KIND, MODE_PREFIX = 'space_mode', 'space:mode:'
# VELDO-0326: the run or gate identity the authority issued to a principal, and the record of a signed
# packet a host principal sent.
RUN_KIND, RUN_PREFIX = 'space_run', 'space:run:'
PACKET_KIND, PACKET_PREFIX = 'space_packet', 'space:packet:'
EVENT_KIND, EVENT_PREFIX = 'space_event', 'space:event:'
CONSUMED = 'space_consumed'
EVENT_TYPES = ('ref_changed', 'session_started', 'session_ended', 'released')
# A signed packet is refused when it was issued more than PACKET_AGE seconds before the time accept is
# given (five minutes), or more than PACKET_SKEW seconds after it.
PACKET_AGE, PACKET_SKEW = 300, 60
PACKET_OUTCOMES = ('accepted', 'refused')
# Mode per scope (design 4.7). A scope with no record is in report mode.
REPORTING, ACTING = 'report', 'act'
MODES = (REPORTING, ACTING)
# Who signs the mode switch: the owner, a person member holding this role.
MODE_SIGNER_TYPE, MODE_SIGNER_ROLE = 'person', 'project_owner'
# What a switch to act requires, and the ticket that builds each check. A switch to act is refused while
# the Ledger has no check for one of them; the ticket that lands installs its check (Ledger act_checks).
ACT_CONDITIONS = (('clean_report_days', 'VELDO-0332'), ('no_unconfirmed_pending_group', 'VELDO-0339'))
NO_PROJECT = {'type': 'no_project'}

# VELDO-0337 (the lead's decision at assembly, design 4.1/6.1): a review run's scratch folder and build
# root are kinds of their own, whose end events the kind registry gives: verdict recorded, ticket ended
# and project ended, never run finished. Declare takes no end list.
REVIEW_RUN_KINDS = ('review_run_scratch', 'review_run_build_output')
DISK_KINDS = ('worktree', 'agent_repository', 'build_output', 'scratch', 'evidence') + REVIEW_RUN_KINDS
DOCKER_KINDS = ('container', 'volume', 'network', 'image_tag')
KINDS = DISK_KINDS + ('branch',) + DOCKER_KINDS
# The protect list's entry type that holds the name patterns of each Docker kind.
PROTECT_TYPE = {'container': 'container', 'volume': 'volume', 'network': 'network', 'image_tag': 'image'}

STATES = ('declared', 'present', 'due', 'deferred', 'removing', 'removed', 'gone', 'kept')
LIVE = ('declared', 'present', 'due', 'deferred', 'removing', 'kept')
SIGNALLED = ('present', 'kept', 'deferred')
OUTCOMES = ('removing', 'removed', 'deferred', 'kept')
# The deferrals a removing item can still get: the three a remover names (design section 7, rule 7;
# VELDO-0345 AC6). The tool refused; the second probe found a user and the thing was put back; the keep
# step failed, or the last look found work it did not save.
TOOL_REFUSALS = ('remove_refused', 'in_use', 'keep_failed')
# The keep record (VELDO-0345): the kinds that hold commits, where kept refs live in a main repository,
# and the snapshot store under the state root with the name of an attempt's manifest.
KEEP_KINDS = ('worktree', 'agent_repository')
KEPT_REFS = 'refs/veldo/kept/'
SNAPSHOT_STORE = 'space-saved'
MANIFEST = 'manifest.json'
GIT_SECONDS = 600
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
KEEP = 'space_keep'
REQUEST = 'space_disposition_request'
KEEP_BRANCH = 'space_keep_branch'
ITEM_OPERATIONS = (DECLARE, CONFIRM, MEASURE, SIGNAL, OUTCOME, ADOPT, REPORT, GONE, REBRANCH, KEEP,
                   REQUEST, 'space_disposition', KEEP_BRANCH)
# Issue is the authority's: the run or gate identity a principal may then hold, declare for and signal.
ISSUE = 'space_issue'
OPERATIONS = ITEM_OPERATIONS + (POOL, HOLD, ADMIT, RELEASE, RECONCILE, ISSUE)
# The Ledger's own record of a packet that was refused, or accepted and wrote nothing. Nobody sends it.
PACKET = 'space_packet'
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
    EVENT: ('type', 'subject', 'emitter'),
    DECLARE: ('kind', 'locator', 'owner', 'creator', 'parent', 'start', 'branch', 'process', 'pool', 'form'),
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


def _is_time(value):
    """A time: a finite number. Not-a-number compares false with every bound, so it is refused here."""
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and value == value and value not in (float('inf'), float('-inf')))


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
    for a branch, {engine, name} for a Docker kind, with what is known of: id (the engine's Id of the
    object; for an image tag, of the image the tag named), created_at (the engine's CreatedAt of a volume),
    run_label (the value of the run's label on it) and compose_project. The removers remove a Docker object
    only when these prove it is the one recorded (control_space_remove.IDENTITY)."""
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
    if (not {'engine', 'name'} <= set(locator) <= {'engine', 'name', 'id', 'compose_project',
                                                      'created_at', 'run_label'}
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


def image_repository(name):
    """(repository, whether a tag or a digest follows it) of an image name or pattern. The digest is
    what follows @; the tag is what follows the last colon when no / comes after it, so the port of a
    registry is no tag."""
    plain, _, digest = name.partition('@')
    tagged = ':' in plain and '/' not in plain.rsplit(':', 1)[1]
    return (plain.rsplit(':', 1)[0] if tagged else plain), bool(tagged or digest)


def name_matches(kind, name, pattern):
    """Whether a protect pattern for the type of `kind` covers the name of an object. An image pattern
    with no tag and no digest covers every tag and every digest of the repository it names; one that
    names a tag or a digest covers that one only. Every other name is matched in full."""
    if fnmatch.fnmatchcase(name, pattern):
        return True
    if kind != 'image_tag' or image_repository(pattern)[1]:
        return False
    return fnmatch.fnmatchcase(image_repository(name)[0], pattern)


def protected_by(kind, locator, protect, resolve=None):
    """The protect entry that covers a canonical locator, as type:value, or None. With `resolve`, each
    protected path is read where it leads (for a locator that was resolved the same way)."""
    if kind in DOCKER_KINDS:
        for entry in protect:
            if locator['engine'] not in entry['engines']:
                continue
            if entry['type'] == PROTECT_TYPE[kind] and name_matches(kind, locator['name'], entry['value']):
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


def snapshot_store(state_root):
    """The snapshot store of an installation: the folder under the state root where what was never
    committed is saved before a removal (design 0.3)."""
    return os.path.join(canonical_path(state_root), SNAPSHOT_STORE)


REFUSED_IN_REF = frozenset(' ~^:?*[\\/')


def kept_part(text):
    """One part of a kept ref's name, and of a folder's name in the snapshot store, made from `text`:
    every character git refuses in a ref name is replaced by '-' (design 0.2)."""
    part = ''.join('-' if c in REFUSED_IN_REF or ord(c) < 32 or ord(c) == 127 else c for c in str(text))
    while '..' in part:
        part = part.replace('..', '.-')
    part = part.replace('@{', '@-')
    if part.startswith('.'):
        part = '-' + part[1:]
    if part.endswith('.lock'):
        part = part[:-5] + '-lock'
    if part.endswith('.'):
        part = part[:-1] + '-'
    return part if part and part != '@' else '-'


def kept_parts(identity, record):
    """(ticket, item): the two parts that name an item's kept refs and its folder in the snapshot store.
    ticket is the item's ticket; for an item with no ticket, run- and the run's label when a run owns it,
    otherwise the word none. item is the item's identifier in the ledger, without its prefix."""
    owner = record.get('owner') if isinstance(record.get('owner'), dict) else {}
    run = owner.get('run') if isinstance(owner.get('run'), dict) else {}
    ticket = owner.get('ticket') if _is_str(owner.get('ticket')) else (
        'run-' + run['id'] if _is_str(run.get('id')) else 'none')
    own = identity[len(ITEM_PREFIX):] if identity.startswith(ITEM_PREFIX) else identity
    return kept_part(ticket), kept_part(own)


def kept_prefix(identity, record):
    """refs/veldo/kept/<ticket>/<item>/: what every kept ref of the item begins with."""
    return KEPT_REFS + '%s/%s/' % kept_parts(identity, record)


def _one_attempt(refs, prefix):
    """The number of the keep attempt the refs of one keep write belong to: each is named
    <prefix><n>/<what>, with one n from 1 for all of them. None for a write that names no ref."""
    numbers = set()
    for name in refs:
        number, _, what = name[len(prefix):].partition('/')
        if not (number.isascii() and number.isdigit() and number[0] != '0' and what):
            raise _invalid('refs', 'each kept ref under %s<attempt>/, the attempt numbered from 1' % prefix)
        numbers.add(int(number))
    if len(numbers) > 1:
        raise _invalid('refs', 'the kept refs of one attempt: these are of attempts %s'
                       % ', '.join(str(number) for number in sorted(numbers)))
    return numbers.pop() if numbers else None


def _new_removal(record):
    """A removal of the item begins: its keep record, when it has one, is of no attempt until the
    keep step writes again. Nothing else of the record is touched."""
    if record.get('kept'):
        record['kept'] = dict(record['kept'], attempt=None)


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


def _checked_items(subject):
    """The subject of a signal that names items: {items: [{item, version}, ...]} and, for the owner's
    Abandon of one of them, owner_abandon: {item, at}: the item and the time the sender read. Who the
    owner is comes from the command's verified principal, never from the subject: a `by` is refused.
    Returns it in its recorded form."""
    if not set(subject) <= {'items', 'owner_abandon'}:
        raise _invalid('subject', 'a list of items names no part of an owner')
    named = subject['items']
    if not isinstance(named, list) or not named or not all(
            isinstance(one, dict) and set(one) == {'item', 'version'} and _is_str(one['item'])
            and type(one['version']) is int and one['version'] > 0 for one in named):
        raise _invalid('subject.items', 'a list of {item, version}, each version the one its sender read')
    if len({one['item'] for one in named}) != len(named):
        raise _invalid('subject.items', 'each item once')
    out = {'items': [{'item': one['item'], 'version': one['version']} for one in named]}
    abandon = subject.get('owner_abandon')
    if abandon is not None:
        if not isinstance(abandon, dict) or set(abandon) != {'item', 'at'} or not _is_time(abandon['at']) \
                or abandon['item'] not in [one['item'] for one in named]:
            raise _invalid('subject.owner_abandon', 'the item abandoned, one of those named, and the time '
                           'read; who abandoned it is the command\'s principal')
        out['owner_abandon'] = {'item': abandon['item'], 'at': abandon['at']}
    return out


def _checked_subject(subject):
    if isinstance(subject, dict) and 'items' in subject:
        return _checked_items(subject)
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
        raise _invalid('lifecycle', 'a version, the events, and the events each kind ends on')
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


def run_id(identity):
    """The identity of the record of an issued run or gate."""
    return RUN_PREFIX + identity


def packet_content(command):
    """What makes a packet the same packet when it is sent again: its command without the time it was
    signed at. The nonce, the principal, the operation, the parameters and the command id are all in it."""
    return {key: value for key, value in command.items() if key != 'issued_at'}


def packet_id(principal, nonce):
    """The identity of the record of one signed packet: its principal and its nonce."""
    return PACKET_PREFIX + principal + ':' + nonce


def checked_scope(scope):
    """A scope in its recorded form: exactly one of project, plain repository and no project, with an
    identity for the first two. A plain repository is named by its repository, in the canonical form."""
    if not isinstance(scope, dict) or scope.get('type') not in SCOPES:
        raise _invalid('scope', 'exactly one of project, plain_repository and no_project')
    if scope['type'] == 'no_project':
        if set(scope) != {'type'}:
            raise _invalid('scope', 'no project has no identity')
        return {'type': 'no_project'}
    if set(scope) != {'type', 'id'} or not _is_str(scope['id']):
        raise _invalid('scope', 'a project or plain repository scope names its identity')
    identity = canonical_path(scope['id']) if scope['type'] == 'plain_repository' else scope['id']
    return {'type': scope['type'], 'id': identity}


def mode_id(scope):
    """The identity of a scope's mode record. `scope` is in its recorded form."""
    return MODE_PREFIX + scope['type'] + (':' + scope['id'] if 'id' in scope else '')


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
    `act_checks` is {condition: check(scope)} for the conditions of ACT_CONDITIONS that are built; with
    one missing, no scope is switched to act.

    Every command returns {'ok': True, ...} or {'ok': False, 'reason': <name>, 'detail': ...}."""

    def __init__(self, store, conn, journal_signer, sign, *, config, state_root, lifecycle, host, projects=(),
                 authority_generation=1, device=device_of, new_id=None, act_checks=None):
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
        self.state_root = canonical_path(state_root)
        # The snapshot store is protected in every installation: by the Ledger, not by a file.
        self.snapshot_store = snapshot_store(state_root)
        self.protect = protect_list(config, self.projects) + [
            {'type': 'path', 'value': self.snapshot_store, 'engines': []}]
        self.lifecycle = checked_lifecycle(lifecycle)
        self.device = device
        self.new_id = new_id or (lambda: uuid.uuid4().hex)
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        self.refused_declares = {}
        # The packet accept is running, when it is: _send writes its record with the command.
        self._packet = None
        self.act_checks = dict(act_checks or {})
        # The command _send has given the store, while the store runs it: the mode transition reads who
        # sent it. The membership module beside this file, loaded when the mode transition first runs.
        self._outer, self._membership_module = None, None
        transitions = {DECLARE: self._t_declare, CONFIRM: self._t_confirm, MEASURE: self._t_measure,
                       SIGNAL: self._t_signal, OUTCOME: self._t_outcome, ADOPT: self._t_adopt,
                       REPORT: self._t_report, GONE: self._t_gone, REBRANCH: self._t_rebranch,
                       POOL: self._t_pool, HOLD: self._t_hold, ADMIT: self._t_admit, RELEASE: self._t_release,
                       RECONCILE: self._t_reconcile, MODE: self._t_mode, ISSUE: self._t_issue,
                       PACKET: self._t_packet, KEEP: self._t_keep,
                       REQUEST: self._t_disposition_request, DISPOSITION: self._t_disposition,
                       KEEP_BRANCH: self._t_keep_branch,
                       EVENT: self._t_event, CONSUMED: self._t_consumed}
        # A command a host principal may send writes the record of its packet in its own transaction.
        for operation in COMMAND_PARAMETERS:
            transitions[operation] = self._with_packet(transitions[operation])
        # The mode switch is the owner's action and not one of OPERATIONS, the commands the authority sends.
        for operation in OPERATIONS + (MODE, PACKET, EVENT, CONSUMED):
            conn.command_registry[operation] = {'transaction_transition': transitions[operation], 'writes': WRITES}
        store.declare_owners(conn, OWNER,
                             kinds={ITEM_KIND: ITEM_OPERATIONS, POOL_KIND: (POOL,),
                                    HOLD_KIND: (HOLD, ADMIT, RELEASE, OUTCOME, RECONCILE), RECONCILE_KIND: (RECONCILE,),
                                    MODE_KIND: (MODE,), RUN_KIND: (ISSUE,), EVENT_KIND: (EVENT, CONSUMED),
                                    PACKET_KIND: tuple(COMMAND_PARAMETERS) + (PACKET,)},
                             prefixes={ITEM_PREFIX: ITEM_OPERATIONS, POOL_PREFIX: (POOL,),
                                       HOLD_PREFIX: (HOLD, ADMIT, RELEASE, OUTCOME, RECONCILE), RECONCILE_PREFIX: (RECONCILE,),
                                       MODE_PREFIX: (MODE,), RUN_PREFIX: (ISSUE,), EVENT_PREFIX: (EVENT, CONSUMED),
                                       PACKET_PREFIX: tuple(COMMAND_PARAMETERS) + (PACKET,)},
                             module=__file__)

    # Reads.

    def event_record(self, identity):
        return self._row(identity, EVENT_KIND)[1]

    def events(self):
        """Hook records in journal order, independent of clocks and random identifiers."""
        return [(identity, json.loads(data)) for identity, data in self.conn.execute(
            'SELECT id, data FROM entities WHERE kind=? ORDER BY json_extract(data, "$.received"), id',
            (EVENT_KIND,))]

    def event(self, type, subject, emitter, principal=None, command_id=None):
        identity = EVENT_PREFIX + self.new_id()
        answer = self._send(EVENT, dict(event=identity, type=type, subject=subject, emitter=emitter),
                            {identity: 0}, principal, command_id, {'event': identity})
        if answer['ok']:
            answer['event'] = identity
        return answer

    def consumed(self, identity, result, principal=None, command_id=None):
        return self._send(CONSUMED, dict(event=identity, result=result),
                          {identity: self._row(identity, EVENT_KIND)[0]}, principal, command_id,
                          {'event': identity})

    def _t_event(self, conn, params, before):
        identity, kind = params.get('event'), params.get('type')
        subject, emitter = params.get('subject'), params.get('emitter')
        if not _is_str(identity) or not identity.startswith(EVENT_PREFIX) or identity in before:
            raise _invalid('event', 'a new event identity')
        if kind not in EVENT_TYPES or not isinstance(subject, dict):
            raise _invalid('event', 'a hook event type and its subject')
        # The event verb stands for released alone (design 6.9), under its own emitter and under the
        # hook name its spooled entries carry: neither route records another kind.
        if (not isinstance(emitter, dict) or emitter.get('host') != self.host
                or not ((_is_str(emitter.get('hook'))
                         and (kind == 'released' or emitter['hook'] != 'event'))
                        or (kind == 'released' and emitter.get('verb') == 'event'))):
            raise _invalid('emitter', 'the hook and this host')
        if kind == 'ref_changed':
            if set(subject) != {'repository', 'ref', 'old', 'new'}:
                raise _invalid('subject', 'repository, ref, old and new')
            locator = canonical_locator('branch', {k: subject[k] for k in ('repository', 'ref')})
            if locator != self._resolved('branch', locator):
                raise Refused('space_locator_link', 'the repository path traverses a link')
            if not inside_roots('branch', locator, self.resolved_roots, self.engines):
                raise Refused('space_outside_roots', 'the repository is not declared')
            if protected_by('branch', locator, self.protect):
                raise Refused('space_protected', 'the repository is protected')
            for field in ('old', 'new'):
                value = subject[field]
                if not (field == 'old' and value is None) and not (
                        isinstance(value, str) and len(value) in (40, 64)
                        and all(c in '0123456789abcdef' for c in value)):
                    raise _invalid(field, 'a commit hash')
            subject = dict(subject, **locator)
        elif kind in ('session_started', 'session_ended'):
            if (set(subject) != {'session', 'cwd', 'pid', 'started'} or not _is_str(subject['session'])
                    or type(subject['pid']) is not int or subject['pid'] <= 0
                    or type(subject['started']) is not int or subject['started'] < 0):
                raise _invalid('subject', 'session, cwd, pid and started')
            path = canonical_path(subject['cwd'])
            if path != resolved_path(path):
                raise Refused('space_locator_link', 'the working folder traverses a link')
            subject = dict(subject, cwd=path)
        elif kind == 'released':
            if (set(subject) != {'paths'} or not isinstance(subject['paths'], list)
                    or not subject['paths']):
                raise _invalid('subject', 'released names a nonempty list of paths')
            paths, names = [], []
            for path in subject['paths']:
                path = _absolute(path, 'subject.paths')
                if path != resolved_path(path):
                    raise Refused('space_locator_link', 'the released path traverses a link: ' + path)
                matches = [(name, item) for name, item in self.items().items()
                           if item.get('locator', {}).get('path') == path and item['state'] in LIVE]
                if len(matches) != 1:
                    raise Refused('space_release_no_item:' + path, 'released needs one live item at this path')
                name, item = matches[0]
                if item['creator'] not in ('hook', 'record') or item['kind'] not in ('worktree', 'agent_repository'):
                    raise Refused('space_release_creator:' + name, 'released is only for a hook or record creation')
                self._admissible(item['kind'], item['locator'], name)
                if name not in names:
                    paths.append(path)
                    names.append(name)
            # Bind the observation to these identities, never to a later occupant of the path.
            subject = {'paths': paths, 'items': names}
        received = conn.execute('SELECT COALESCE(MAX(seq), 0) + 1 FROM journal').fetchone()[0]
        return {identity: {'kind': EVENT_KIND, 'data': dict(type=kind, subject=subject,
            emitter=dict(emitter), state='received', received=received, result=None)}}

    def _t_consumed(self, conn, params, before):
        identity, record = self._stored(params, before, 'event', EVENT_KIND, 'space_no_event')
        if record['state'] != 'received':
            raise Refused('space_event_consumed', 'the event was already consumed')
        result = params.get('result')
        if not isinstance(result, dict) or not isinstance(result.get('items'), list):
            raise _invalid('result', 'the items made due and the worker result')
        record.update(state='consumed', result=result)
        return {identity: {'kind': EVENT_KIND, 'data': record}}

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

    def hold_snapshot(self, identity):
        """Version and data from one read, for admission's compare-and-write."""
        return self._row(hold_id(identity), HOLD_KIND)

    def reconcile_record(self, identity):
        return self._row(identity, RECONCILE_KIND)[1] if _is_str(identity) else None

    def issued(self, identity):
        """The record of a run or gate identity the authority issued, or None."""
        return self._row(run_id(identity), RUN_KIND)[1] if _is_str(identity) else None

    def issued_to(self, identity):
        """The principal a run or gate identity was issued to. None when nobody issued it."""
        record = self.issued(identity)
        return record['principal'] if record else None

    def packet(self, principal, nonce):
        """The record of the packet a principal sent with this nonce, or None."""
        if not _is_str(principal) or not _is_str(nonce):
            return None
        return self._row(packet_id(principal, nonce), PACKET_KIND)[1]

    def holds(self):
        """Every hold as {identity: record}, the identity as place_hold was given it."""
        return {row[0][len(HOLD_PREFIX):]: json.loads(row[1]) for row in self.conn.execute(
            'SELECT id, data FROM entities WHERE kind=? ORDER BY id', (HOLD_KIND,))}

    def mode_record(self, scope):
        """The mode record of one scope, or None when the scope has none."""
        try:
            return self._row(mode_id(checked_scope(scope)), MODE_KIND)[1]
        except Refused:
            return None

    def mode_of(self, scope):
        """report or act: the mode of this one scope. A scope with no record is in report mode, and so
        is anything that is not a scope (a report record has no owner)."""
        record = self.mode_record(scope)
        return record['mode'] if record else REPORTING

    def acts(self, scope):
        """Whether this one scope is in act mode."""
        return self.mode_of(scope) == ACTING

    def modes(self):
        """Every mode record as {identity: record}. A scope that is not here is in report mode."""
        return {row[0]: json.loads(row[1]) for row in self.conn.execute(
            'SELECT id, data FROM entities WHERE kind=? ORDER BY id', (MODE_KIND,))}

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

    def _send(self, operation, parameters, versions, principal, command_id, about, nonce=None):
        if operation in (OUTCOME, RELEASE, RECONCILE):
            # Declare the waiting set, then check it again inside the write transaction.
            # A concurrent admission or new hold retries only this optimistic snapshot.
            original = dict(versions)
            while True:
                waiting = {identity: version for identity, version, raw in self.conn.execute(
                    'SELECT id, version, data FROM entities WHERE kind=?', (HOLD_KIND,))
                    if json.loads(raw)['state'] == 'waiting'}
                result = self._send_once(operation, parameters, dict(waiting, **original),
                                         principal, command_id, about, nonce)
                if result.get('reason') not in ('stale_version', 'space_holds_changed'):
                    return result
                if any(self.conn.execute('SELECT version FROM entities WHERE id=?', (key,)).fetchone()
                       != ((version,) if version else None) for key, version in original.items()):
                    return result
        return self._send_once(operation, parameters, versions, principal, command_id, about, nonce)

    def _send_once(self, operation, parameters, versions, principal, command_id, about, nonce=None):
        packet = self._packet
        if packet is not None and principal == packet['principal'] and operation == packet['operation']:
            # The command of a signed packet: its record is written in this transaction, against the
            # version of a nonce nobody has seen, and the store consumes the packet's own nonce.
            parameters = dict(parameters, packet=dict(packet))
            versions = dict(versions, **{packet_id(packet['principal'], packet['nonce']): 0})
            nonce = packet['nonce']
        command = {'command_id': command_id or 'space:' + uuid.uuid4().hex,
                   'principal': principal or self.journal_signer, 'operation': operation,
                   'parameters': parameters, 'expected_versions': versions, 'artifact_digests': [],
                   'nonce': nonce or uuid.uuid4().hex}
        observation = dict(about, schema=SCHEMA, operation=operation, command_id=command['command_id'],
                           principal=command['principal'])
        self._outer = command
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
        finally:
            self._outer = None
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
                pool=None, principal=None, command_id=None, form=None):
        """Create an item in state declared, with pool and ends_on filled in. Returns its identity."""
        return self._create(DECLARE, kind, locator, owner, creator, parent, start, branch, process, pool, None,
                            principal, command_id, form)

    def adopt(self, kind, locator, owner, rule, parent=None, start=None, branch=None, process=None, pool=None,
              principal=None, command_id=None):
        """Create an item in state present with adopted true, for a thing reconcile found; `rule` is the
        rule that proved the owner. A report record at the locator becomes the item. The same refusals
        as declare."""
        return self._create(ADOPT, kind, locator, owner, 'reconcile', parent, start, branch, process, pool, rule,
                            principal, command_id)

    def _create(self, operation, kind, locator, owner, creator, parent, start, branch, process, pool, rule,
                principal, command_id, form=None):
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
                      'pool': pool, 'device': device, 'rule': rule, 'form': form}
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

    @contextlib.contextmanager
    def item_lock(self, identity):
        """Serialize recovery and removal from their fresh read through the final outcome."""
        held = getattr(self, '_removal_locks', None)
        if held is None:
            held = self._removal_locks = {}
        key = (os.getpid(), threading.get_ident(), identity)
        if key in held:
            yield
            return
        root = os.open(self.state_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            try:
                os.mkdir('space-item-locks', 0o700, dir_fd=root)
            except FileExistsError:
                pass
            directory = os.open('space-item-locks', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
            try:
                info = os.fstat(directory)
                if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
                    raise ValueError('unsafe space item lock directory')
                name = hashlib.sha256(identity.encode()).hexdigest() + '.lock'
                fd = os.open(name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            finally:
                os.close(directory)
        finally:
            os.close(root)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
                raise ValueError('unsafe space item lock')
            fcntl.flock(fd, fcntl.LOCK_EX)
            held[key] = fd
            try:
                yield
            finally:
                del held[key]
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def outcome(self, item, outcome, facts=None, principal=None, command_id=None):
        """Write what became of a due or removing item: removing, removed, deferred or kept, with the
        facts (the removal fields for removed, the deferral fields for deferred). A removing item is
        removed, or deferred with one of the three deferrals a remover names (TOOL_REFUSALS); nothing
        else. A worktree and an agent repository are removed only with a keep record."""
        return self._item_command(OUTCOME, item, {'outcome': outcome, 'facts': facts or {}}, principal, command_id)

    def kept_prefix(self, item):
        """What every kept ref of the item begins with, or None when there is no such item."""
        record = self.item(item)
        return kept_prefix(item, record) if record else None

    def request_disposition(self, item, proposal, head):
        """Reserve one immutable request on the deferred item, before publishing it.

        A retry uses the same request until a settled removal has refused. That refusal
        retires its authorization; the next request has its own number and file list.
        `head` is the commit the worktree was at when the terms were read (None for a HEAD
        with no commit). It is recorded beside the terms: Save and Discard run only there.
        """
        record = self.item(item) or {}
        prior = record.get('disposition') or {}
        if prior and prior.get('state') != 'refused':
            return {'ok': True, 'request': prior, 'replayed': True}
        result = self._item_command(REQUEST, item, {'proposal': proposal, 'head': head}, None, None)
        if result.get('ok'):
            result['request'] = self.item(item)['disposition']
        return result

    def _t_disposition_request(self, conn, params, before):
        identity, record = self._stored(params, before)
        prior = record.get('disposition') or {}
        if record['state'] != 'deferred' or record['kind'] != 'worktree' or record.get('owner_keep'):
            raise Refused('space_disposition_state', 'a deferred worktree without an owner Keep')
        if prior and prior.get('state') != 'refused':
            raise Refused('space_disposition_exists', 'the item already has its request')
        proposal = params.get('proposal')
        settlement = _sibling('control_request_settlement')
        try:
            settlement.space_presentation(proposal)
        except settlement.Refused as error:
            raise Refused(error.code, error.detail) from error
        tree = proposal['worktrees'][0]
        if tree['item'] != identity or tree['path'] != record['locator']['path']:
            raise Refused('space_disposition_item', 'the request names this worktree')
        head = params.get('head')
        if 'head' not in params or head is not None and not (
                _is_str(head) and len(head) in (40, 64) and not set(head) - set('0123456789abcdef')):
            raise _invalid('head', 'the commit the worktree was at when the terms were read, or null')
        number = prior.get('number', 0) + 1
        request = {'number': number, 'alias': 'space-disposition-' + hashlib.sha256(identity.encode()).hexdigest()[:32] + '-' + str(number),
                   'proposal': proposal, 'head': head, 'state': 'requested'}
        record['disposition_history'] = list(record.get('disposition_history') or []) + ([prior] if prior else [])
        record['disposition'] = request
        record['deferral'] = dict(record.get('deferral') or {}, decision_request=request['alias'])
        return {identity: {'kind': ITEM_KIND, 'data': record}}

    def disposition(self, packet, membership, now):
        """One owner-signed command: deferred to kept, or due for a settled Save/Discard.

        Neither a caller's principal string nor the authority's journal signature is
        the owner's signature. The transition verifies the packet again in the store.
        """
        command = packet.get('command') if isinstance(packet, dict) else None
        try:
            self._disposition_command(command)
            if not _is_time(now):
                raise _invalid('now', 'the time the caller read')
            self._mode_signer(command, packet.get('signature'), now, self._membership())
            params = command['parameters']
            identity = params['item']
            version, record = self._row(identity, ITEM_KIND)
            if record is None:
                raise Refused('space_no_item', identity)
            if version != params['version']:
                raise Refused('stale_version', identity)
            return self._send(DISPOSITION, {'item': identity, 'packet': packet, 'at': now},
                              {identity: version}, command['principal'], command['command_id'],
                              {'item': identity}, command['nonce'])
        except Refused as error:
            return self._refuse(DISPOSITION, error, {}, (command or {}).get('principal'))

    def _disposition_command(self, command):
        parameters = command.get('parameters') if isinstance(command, dict) else None
        if (not isinstance(parameters, dict) or command.get('operation') != DISPOSITION
                or set(parameters) != {'item', 'version', 'request'}
                or not all(_is_str(command.get(key)) for key in ('principal', 'command_id', 'nonce'))
                or not _is_str(parameters['item']) or not _is_str(parameters['request'])
                or type(parameters['version']) is not int):
            raise _invalid('command', 'a signed disposition naming item, version and settled request')

    def disposition_effect(self, identity, request_id):
        """Read the settled choice from this store, never from command parameters."""
        record = self.item(identity) or {}
        request = record.get('disposition') or {}
        _, assignment = self._row(request_id, 'assignment')
        reference = (assignment or {}).get('settlement') or {}
        _, settled = self._row(reference.get('settlement_id'), 'request_settlement')
        _, effect = self._row(reference.get('effect_id'), 'settlement_effect')
        if (not assignment or assignment.get('state') != 'SATISFIED' or not settled or not effect
                or settled.get('request_id') != request_id or effect.get('request_id') != request_id
                or effect.get('settlement_id') != settled.get('settlement_id')
                or effect.get('touchpoint') != 'space_disposition' or effect.get('ruling') != 'approve'
                or effect.get('choice') not in ('accept save', 'accept keep', 'accept discard')
                or effect.get('choice') != settled.get('choice')
                or effect.get('proposal') != request.get('proposal')
                or (effect.get('target') or {}).get('ref') != identity
                or assignment.get('alias') != request.get('alias')
                or settled.get('principals') != [assignment.get('owner')]):
            raise Refused('space_disposition_unsettled', 'a settled answer to this item request is required')
        return effect, assignment['owner']

    def _t_disposition(self, conn, params, before):
        identity, record = self._stored(params, before)
        packet, at = params.get('packet'), params.get('at')
        if packet is None:
            outer = self._outer
            if (outer is None or outer['parameters'] is not params or outer['principal'] != self.journal_signer):
                raise Refused('not_authorized', 'only the authority applies settled filesystem effects')
            effect, owner = self.disposition_effect(identity, params.get('request'))
            if effect['choice'] == 'accept keep':
                raise Refused('not_authorized', 'Keep requires the owner signed packet')
            return self._disposition_change(identity, record, effect, owner, params['request'])
        command = packet.get('command') if isinstance(packet, dict) else None
        self._disposition_command(command)
        outer = self._outer
        if (outer is None or outer['parameters'] is not params
                or any(outer[key] != command[key] for key in ('principal', 'command_id', 'nonce'))
                or command['parameters']['item'] != identity
                or command['parameters']['version'] != before[identity]['version']):
            raise Refused('not_authorized', 'the disposition is the owner signed packet')
        self._mode_signer(command, packet.get('signature'), at, self._membership())
        effect, owner = self.disposition_effect(identity, command['parameters']['request'])
        if owner != command['principal']:
            raise Refused('not_authorized', 'the answering owner signs the disposition')
        return self._disposition_change(identity, record, effect, owner, command['parameters']['request'])

    def authorize_disposition(self, identity, request):
        return self._item_command(DISPOSITION, identity, {'request': request}, None, None)

    def _disposition_change(self, identity, record, effect, owner, request):
        if record['state'] != 'deferred' or (record.get('disposition') or {}).get('state') != 'requested':
            raise Refused('space_disposition_state', 'the request has already been applied')
        choice = effect['choice'].split(' ')[1]
        record['disposition'] = dict(record['disposition'], state='authorized', choice=choice,
                                     request=request, by=owner)
        if choice == 'keep':
            record['owner_keep'] = {'by': owner}
            record['state'] = 'kept'
            record['disposition']['state'] = 'kept'
        else:
            record['state'] = 'due'
            _new_removal(record)
        return {identity: {'kind': ITEM_KIND, 'data': record}}

    def publish_disposition(self, identity, settlement, inbox, presenter, requester, owner):
        """Publish the reserved request with the ordinary signed terms and inbox path.

        Each durable boundary has a deterministic identity. A worker lost between
        terms, opening and framing resumes the same request on reconnect.
        """
        request = (self.item(identity) or {}).get('disposition') or {}
        alias, proposal = request.get('alias'), request.get('proposal')
        if not alias or request.get('state') != 'requested':
            return {'ok': False, 'reason': 'space_disposition_state'}
        st = _sibling('control_request_settlement')
        principal, sign = requester
        ids = inbox.ids
        def packet(operation, **fields):
            command = dict(ids, operation=operation, principal=principal, command_id=alias + ':' + operation,
                           nonce=alias + ':' + operation, **fields)
            return {'command': command, 'signature': sign(self.store.canonical_bytes(command))}
        tid = st.terms_id(ids['repository_uuid'], alias)
        _, terms = self._row(tid, st.TERMS_KIND)
        if terms is None:
            result = settlement.terms(packet('terms', terms=alias, touchpoint='space_disposition',
                target={'kind': 'space_item', 'ref': identity, 'digest': st.digest(proposal)},
                proposal=proposal, required_roles=[], quorum=None))
            if result.get('outcome') != 'recorded':
                return {'ok': False, 'reason': result.get('reason')}
            _, terms = self._row(tid, st.TERMS_KIND)
        rid = presenter.inbox_request(alias)
        _, assignment = self._row(rid, 'assignment')
        if assignment is None:
            content = st.space_presentation(proposal)
            content.update(owner=owner, scope=['space'], deadline='2099-01-01T00:00:00Z',
                           budget={'owner_minutes': 1},
                           subject={'kind': st.SUBJECT_KIND, 'ref': tid, 'digest': st.digest(terms)})
            result = inbox.apply(packet('open', alias=alias, assignment=content))
            if not result.get('ok'):
                return result
        result = presenter.frame(packet('frame', alias=alias, request_version=1,
                                        risk_statement=st.SPACE_DISCARD))
        return {'ok': result.get('outcome') == 'accepted', 'request': rid, 'framing': result}

    def snapshot_folder(self, item):
        """The item's own folder in the snapshot store, <state root>/space-saved/<ticket>/<item>, or None
        when there is no such item. Each attempt is a numbered folder in it."""
        record = self.item(item)
        return os.path.join(self.snapshot_store, *kept_parts(item, record)) if record else None

    def main_repository(self, item):
        """The main repository of a worktree or an agent repository item: the repository the declarations
        name for its scope, which is never a private repository (design section 0). None when they name
        none, and for any other item."""
        record = self.item(item)
        return self._main_of(record) if record and record.get('kind') in KEEP_KINDS else None

    def keep(self, item, repository, refs, snapshot=None, principal=None, command_id=None):
        """Write the keep record of a due or removing worktree or agent repository: its main
        repository, each kept ref with its commit, and the snapshot attempt {path, number, size, manifest}
        when one was written. The Ledger reads each ref and the manifest itself before it writes. For an
        item that has a record the refs and the attempt are added; none is replaced or removed."""
        return self._item_command(KEEP, item, {'repository': repository, 'refs': refs, 'snapshot': snapshot},
                                  principal, command_id)

    def keep_branch(self, item, branch, commit, principal=None, command_id=None):
        """Record the kept branch `branch`, which a settled Discard made at `commit` for the removing,
        detached worktree `item`, as a branch item in state kept (VELDO-0343). The Ledger reads the
        worktree's HEAD and the branch itself before it writes. Returns the branch item under
        branch_item."""
        record = self.item(item) if _is_str(item) else None
        branch_item, also = None, {}
        if record is not None and _is_str(branch):
            repository = self._main_of(record)
            held = self._at(locator_key('branch', {'repository': repository, 'ref': branch})) if repository else None
            if held is not None:
                branch_item, also = held[0], {held[0]: held[1]}
            else:
                branch_item = item_id(self.new_id())
                also = {branch_item: 0}
        result = self._item_command(KEEP_BRANCH, item, {'branch': branch, 'commit': commit,
                                                        'branch_item': branch_item}, principal, command_id, also)
        if result['ok']:
            result['branch_item'] = branch_item
        return result

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
        removal order is the kind registry's. An item the owner marked Keep is never one of them.

        A subject that names items, {items: [{item, version}, ...]}, marks exactly those items and nothing
        else, and is refused whole when one of them changed, is in no state a signal reaches, does not
        end on the event or holds the owner's Keep; with owner_abandon: {item, at} and the event
        worktree abandoned it ends the Keep of that one item (the module's A SIGNAL THAT NAMES ITEMS),
        and then `principal` must be the owner, which the transition reads from this store itself."""
        about = {'item': None, 'event': event, 'subject': subject}
        try:
            if event not in self.lifecycle['events'] and event != 'admission_requested':
                raise Refused('space_unknown_event', 'not an event of the lifecycle table')
            subject = self._retry_subject(subject) if event == 'admission_requested' else _checked_subject(subject)
            self.permit(principal, SIGNAL, {'event': event, 'subject': subject})
        except Refused as refusal:
            return self._refuse(SIGNAL, refusal, about, principal)
        try:
            if event == 'admission_requested':
                versions = {key: self._row(key, ITEM_KIND)[0] for key, value in self.items().items()
                            if self._retry_item(value, subject['pool'])}
            elif 'items' in subject:
                versions = {one['item']: one['version'] for one in subject['items']}
                self._named(event, subject, {identity: self._row(identity, ITEM_KIND) for identity in versions})
            else:
                versions = {identity: version for identity, version, _record in self._matching(event, subject)}
        except Refused as refusal:
            return self._refuse(SIGNAL, refusal, about, principal)
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

    def place_hold(self, identity, needs, source, principal=None, command_id=None, scope=None):
        """Write a hold in state waiting with the needs per pool and where each need came from. The hold
        records the scope the run belongs to: the scope its run or gate was issued with, else `scope`,
        else no project."""
        about = {'item': None, 'hold': identity}
        if not _is_str(identity):
            return self._refuse(HOLD, _invalid('hold', 'a hold identity'), about)
        parameters = {'hold': hold_id(identity), 'needs': needs, 'source': source}
        if scope is not None:
            parameters['scope'] = scope
        return self._send(HOLD, parameters, {hold_id(identity): self._row(hold_id(identity), HOLD_KIND)[0]},
                          principal, command_id, about)

    def admit(self, identity, answer, reason=None, used=None, retry_asked=None, principal=None, command_id=None,
              expected_version=None):
        """Write the answer admission gave for a waiting hold: admitted, advised or waiting, with the
        reason as numbers for waiting and advised. The judgement is admission's; this records it, and
        refuses advised for a hold whose scope is in act mode."""
        return self._hold_command(ADMIT, identity, {'answer': answer, 'reason': reason, 'used': used,
                                                    'retry_asked': retry_asked}, principal, command_id, expected_version)

    def release(self, identity, used=None, principal=None, command_id=None):
        """waiting, advised or admitted to released."""
        return self._hold_command(RELEASE, identity, {'used': used}, principal, command_id)

    def _hold_command(self, operation, identity, parameters, principal, command_id, expected_version=None):
        about = {'item': None, 'hold': identity}
        if not _is_str(identity):
            return self._refuse(operation, _invalid('hold', 'a hold identity'), about)
        entity = hold_id(identity)
        version = self._row(entity, HOLD_KIND)[0] if expected_version is None else expected_version
        result = self._send(operation, dict(parameters, hold=entity), {entity: version},
                            principal, command_id, about)
        if result['ok']:
            result['state'] = self.hold(identity)['state']
        return result

    def issue(self, to, label=None, principal=None, command_id=None, scope=None):
        """Issue a run or gate identity to the principal `to`: the authority's command, and the only way
        a host principal comes to have a run. The identity is `label` (what the run is, when the caller
        names it) and then a part this Ledger makes that nobody can predict. Returns it under run.
        `scope` is the scope the run belongs to, when the authority names it: the run's hold takes it."""
        about = {'item': None, 'issued_to': to, 'label': label}
        if not _is_str(to) or (label is not None and not _is_str(label)):
            return self._refuse(ISSUE, _invalid('issue', 'the principal it is issued to, and a label or none'),
                                about, principal)
        identity = '%s:%s' % (label or 'run', self.new_id())
        parameters = {'run': run_id(identity), 'identity': identity, 'principal': to, 'label': label,
                      'issued_by': principal or self.journal_signer}
        if scope is not None:
            parameters['scope'] = scope
        result = self._send(ISSUE, parameters, {run_id(identity): 0}, principal, command_id,
                            dict(about, run=identity))
        if result['ok']:
            result['run'] = identity
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

    # Mode per scope (design 4.7 and 6.1).

    def _known_scope(self, scope):
        """The scope in its recorded form, when the declarations name it: a bound project, a plain
        repository of the installation, or no project."""
        scope = checked_scope(scope)
        if scope['type'] == 'project' and not any(project.get('project') == scope['id']
                                                  for project in self.projects):
            raise Refused('space_unknown_scope', 'no bound project has this identity')
        if scope['type'] == 'plain_repository' and scope['id'] not in [
                canonical_path(plain['repository']) for plain in self.config['plain_repositories']]:
            raise Refused('space_unknown_scope', 'the installation names no such plain repository')
        return scope

    def set_mode(self, packet, membership, now):
        """Switch one scope to act or back to report, by the owner's signed command and by nothing else.
        `packet` is {command, signature}; the command holds principal, operation space_mode, parameters
        {scope, mode}, its own command_id and its nonce. `membership` is the control_membership module;
        `now` is the time the caller read. A switch back to report is accepted at once. What is checked
        here is checked again by the transition, which trusts no caller; a switch to act is refused there
        while a check of ACT_CONDITIONS is not built."""
        command = packet.get('command') if isinstance(packet, dict) else None
        signature = packet.get('signature') if isinstance(packet, dict) else None
        command = command if isinstance(command, dict) else {}
        principal, parameters = command.get('principal'), command.get('parameters')
        parameters = parameters if isinstance(parameters, dict) else {}
        about = {'item': None, 'scope': parameters.get('scope'), 'from': None, 'to': parameters.get('mode')}
        try:
            if not command or not isinstance(signature, str) or not signature.isascii():
                raise _invalid('packet', 'a command mapping and its ASCII signature')
            self.permit(principal, MODE, parameters)
            self._mode_command(command)
            if not _is_time(now):
                raise _invalid('now', 'the time the caller read')
            state, member, key = self._mode_signer(command, signature, now, membership)
            scope = self._known_scope(parameters['scope'])
            if parameters['mode'] not in MODES:
                raise _invalid('mode', 'one of ' + ', '.join(MODES))
        except Refused as refusal:
            return self._refuse(MODE, refusal, about, principal if _is_str(principal) else None)
        entity = mode_id(scope)
        version, record = self._row(entity, MODE_KIND)
        old, new = (record['mode'] if record else REPORTING), parameters['mode']
        about.update(scope=scope, **{'from': old})
        if old == new:
            return self._observed({'ok': True, 'seq': None, 'replayed': False, 'changed': False, 'scope': scope,
                                   'mode': old},
                                  dict(about, schema=SCHEMA, operation=MODE, command_id=command['command_id'],
                                       principal=principal))
        key_entity = key.get('key_id')
        versions = {entity: version, principal: member.get('entity_version', 0),
                    key_entity: (state['entities'].get(key_entity) or {}).get('version', 0)}
        result = self._send(MODE, {'mode_record': entity, 'scope': scope, 'from': old, 'to': new, 'at': now,
                                   'command': {'command': command, 'signature': signature}},
                            versions, principal, command['command_id'], about, command['nonce'])
        if result['ok']:
            # What the store holds now: a packet sent again is answered from the first commit.
            result.update(changed=not result['replayed'], scope=scope, mode=self.mode_of(scope))
        return result

    def _mode_command(self, command):
        """Refuse a command that is not the shape of the owner's mode command."""
        parameters = command.get('parameters') if isinstance(command, dict) else None
        if (not isinstance(parameters, dict) or command.get('operation') != MODE
                or set(parameters) != {'scope', 'mode'}
                or not all(_is_str(command.get(field)) for field in ('principal', 'command_id', 'nonce'))):
            raise _invalid('command', 'the mode command: a principal, a scope and a mode, a command id and a nonce')

    def _mode_signer(self, command, signature, now, membership):
        """The owner behind one mode command, read from this store: (authority state, member, key).
        Refused not_authorized unless the command's principal is an active person member holding
        project_owner whose scope covers the space scope, and `signature` is that principal's, under its
        active key, over the command. set_mode calls this before it sends, and the transition calls it
        again inside the transaction."""
        contract, principal = membership.AC, command['principal']
        state = membership.authority_state(self.store, self.conn)
        member = contract.membership_entry(state['membership'], principal)
        active, why = contract.active_member(member, now)
        key = contract.active_key(state['keyring'], principal, now) if active else None
        if (not active or key is None or member.get('principal_type') != MODE_SIGNER_TYPE
                or MODE_SIGNER_ROLE not in (member.get('roles') or [])
                or not membership.scope_covers(member.get('scope'), SCOPE)):
            raise Refused('not_authorized', why or 'the mode switch is the owner\'s signed command')
        if not isinstance(signature, str) or not signature.isascii() or not contract.ssh_keygen_verify(
                self.store.canonical_bytes(command), signature,
                contract.allowed_signers_line(principal, key['public_key'], NAMESPACE), principal, NAMESPACE)[0]:
            raise Refused('not_authorized', 'the command signature is not the owner\'s')
        return state, member, key

    def _owner(self, params, at, what):
        """The owner behind the command the store is running, for the owner's Keep and the owner's Abandon
        (the module's THE LEDGER CHECKS THE OWNER ITSELF): the principal of that command, when the command
        is the one this Ledger sent with these very parameters and that principal is an active person
        member holding project_owner whose scope covers the space scope at `at`. Refused not_authorized
        otherwise. Called by the transition, inside the transaction; `what` names the act refused."""
        outer = self._outer
        if outer is None or outer['parameters'] is not params:
            raise Refused('not_authorized', what + ' is sent through this Ledger, as the owner\'s own command')
        if not _is_time(at):
            raise _invalid('at', 'the time the sender read')
        membership, principal = self._membership(), outer['principal']
        contract = membership.AC
        member = contract.membership_entry(membership.authority_state(self.store, self.conn)['membership'], principal)
        active, why = contract.active_member(member, at)
        if (not active or member.get('principal_type') != MODE_SIGNER_TYPE
                or MODE_SIGNER_ROLE not in (member.get('roles') or [])
                or not membership.scope_covers(member.get('scope'), SCOPE)):
            raise Refused('not_authorized', why or what + ' is the owner\'s: %s is not the owner' % (principal,))
        return principal

    def _membership(self):
        """The control_membership module beside this file: what the mode transition reads the owner
        with, whatever module its caller was given."""
        if self._membership_module is None:
            self._membership_module = _sibling('control_membership')
        return self._membership_module

    def _act_refusal(self, scope):
        """Why this scope is not switched to act: the tickets whose check is not built, else the first
        built check that refuses. None when every condition has a check and each allows it."""
        unbuilt = [ticket for condition, ticket in ACT_CONDITIONS if not callable(self.act_checks.get(condition))]
        if unbuilt:
            return Refused('space_act_unbuilt:' + ','.join(unbuilt),
                           'no scope is switched to act until the checks of %s exist' % ' and '.join(unbuilt))
        for condition, _ticket in ACT_CONDITIONS:
            why = self.act_checks[condition](scope)
            if why is not None:
                return Refused('space_act_refused:' + condition, str(why))
        return None

    # Who signs a command (design 6.11).

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
        if operation == OUTCOME and isinstance(parameters.get('facts'), dict) and 'owner_keep' in parameters['facts']:
            name = DISPOSITION  # the owner's Keep is an answer to a disposition request: no host principal's

        def refuse(why):
            return Refused('space_not_permitted:%s' % name, '%s may not sign it: %s' % (principal, why))
        if name not in MAY_SIGN[principal]:
            raise refuse('an owner action' if name in OWNER_ACTIONS else 'not a command of this principal')
        runner = principal == RUNNER

        def own(runs):
            # A run or gate is the runner's only by the record the authority issued it with.
            return runner and bool(runs) and all(self.issued_to(run) == RUNNER for run in runs)
        if operation == DECLARE:
            owner = parameters.get('owner')
            if self._observed_thing(parameters.get('kind'), owner):
                return
            if not own(self._runs_of(owner)):
                raise refuse('the thing is neither one a hook records nor of a run or gate issued to it')
        elif operation in (CONFIRM, REBRANCH, MEASURE, OUTCOME):
            record = self.item(parameters.get('item')) or {}
            if operation in (CONFIRM, REBRANCH) and self._observed_thing(record.get('kind'), record.get('owner')):
                return
            if not own(self._runs_of(record.get('owner'))):
                raise refuse('the item is not of a run or gate issued to it')
        elif operation in (HOLD, ADMIT, RELEASE):
            identity = parameters.get('hold')
            run = identity[len(HOLD_PREFIX):] if _is_str(identity) and identity.startswith(HOLD_PREFIX) else None
            if not own([run] if run else []):
                raise refuse('the hold is not of a run or gate the authority issued to it')
        elif operation == SIGNAL:
            subject = parameters.get('subject')
            if parameters.get('event') not in RUNNER_EVENTS:
                raise refuse('it signals only ' + ' and '.join(RUNNER_EVENTS))
            if not (isinstance(subject, dict) and len(subject) == 1 and set(subject) <= {'run', 'gate'}
                    and own(list(subject.values()))):
                raise refuse('the subject is not exactly a run or gate issued to it')

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
        if operation == EVENT:
            return self.event(given.pop('type', None), given.pop('subject', None), given.pop('emitter', None),
                              **given)
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
        active service member whose scope covers the space scope; then the packet's time and its nonce;
        then the rule, then the command. `membership` is the control_membership module; `now` is the
        time the caller read, on the store's own clock.

        The command carries issued_at and nonce. One issued more than PACKET_AGE seconds before `now`
        is space_packet_expired, one more than PACKET_SKEW ahead of it space_packet_ahead. A nonce this
        store has a record of is space_packet_replayed, except the same packet sent again after it was
        accepted: the same nonce and the same content (packet_content), signed at any time inside the
        bound. That is answered with the original answer, replayed true, and writes nothing."""
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
            issued_at, nonce = command.get('issued_at'), command.get('nonce')
            if (not _is_str(operation) or not _is_str(command.get('command_id')) or not _is_str(nonce)
                    or any(c.isspace() for c in nonce) or not _is_time(issued_at)):
                raise _invalid('command', 'an operation, a command id, a nonce and the time it was issued')
            if not _is_time(now):
                raise _invalid('now', 'the time the caller read')
            if now - issued_at > PACKET_AGE:
                raise Refused('space_packet_expired', 'issued more than %d seconds ago: sign it again' % PACKET_AGE)
            if issued_at - now > PACKET_SKEW:
                raise Refused('space_packet_ahead', 'issued more than %d seconds ahead of this clock' % PACKET_SKEW)
        except Refused as refusal:
            return self._refuse(operation if _is_str(operation) else None, refusal, {'item': None},
                                principal if _is_str(principal) else None)
        digest, content = self.store.digest_of(command), self.store.digest_of(packet_content(command))
        seen = self.packet(principal, nonce)
        if seen is not None:
            if seen['outcome'] == 'accepted' and (seen['digest'] == digest or seen.get('content') == content):
                # The resend of a packet that was accepted, the same bytes or signed again under its
                # nonce: the original answer, nothing written.
                return self._observed(dict(self._original(seen, command), replayed=True),
                                      {'item': None, 'schema': SCHEMA, 'operation': operation,
                                       'command_id': command['command_id'], 'principal': principal})
            return self._refuse(operation, Refused('space_packet_replayed', 'this nonce was seen: sign a new packet'),
                                {'item': None}, principal)
        pending = {'principal': principal, 'nonce': nonce, 'digest': digest, 'content': content,
                   'command_id': command['command_id'],
                   'operation': operation, 'issued_at': issued_at, 'seen': now}
        self._packet = pending
        try:
            result = self.apply(command)
        finally:
            self._packet = None
        if self.packet(principal, nonce) is None:
            self._remember(pending, result)
        return result

    def _remember(self, pending, result):
        """Record a packet whose command committed nothing: one that was refused, or accepted with
        nothing to write. The record is the Ledger's own command; when the store cannot take it the
        answer stands and nothing is recorded."""
        record = dict(pending, outcome='accepted' if result['ok'] else 'refused', refusal=result.get('reason'),
                      answer={key: value for key, value in result.items() if key != 'replayed'} if result['ok']
                      else None, wrote=None)
        entity = packet_id(pending['principal'], pending['nonce'])
        try:
            self.store.execute(self.conn, {
                'command_id': 'space:packet:' + uuid.uuid4().hex, 'principal': self.journal_signer,
                'operation': PACKET, 'parameters': {'packet': entity, 'record': record},
                'expected_versions': {entity: 0}, 'artifact_digests': [], 'nonce': uuid.uuid4().hex},
                self.journal_signer, self.sign, self.authority_generation)
        except (self.store.StoreRefused, sqlite3.Error):
            pass

    def _original(self, seen, command):
        """The answer an accepted packet was given, from its record: the answer itself when its command
        wrote nothing, else rebuilt from what its transaction wrote."""
        if seen.get('answer') is not None:
            return dict(seen['answer'])
        row = self.conn.execute('SELECT seq FROM commands WHERE command_id=?', (seen['command_id'],)).fetchone()
        answer = {'ok': True, 'seq': row[0] if row else None}
        wrote, operation = seen.get('wrote') or {}, seen['operation']
        parameters = command.get('parameters') if isinstance(command.get('parameters'), dict) else {}
        items = sorted(identity for identity in wrote if identity.startswith(ITEM_PREFIX))
        if operation == SIGNAL:
            answer['items'] = items
        elif operation == EVENT:
            answer['event'] = next((identity for identity in wrote if identity.startswith(EVENT_PREFIX)), None)
        elif operation in (ADMIT, RELEASE):
            target = parameters.get('hold')
            target = target if _is_str(target) and target.startswith(HOLD_PREFIX) else hold_id(target)
            answer['state'] = (wrote.get(target) or {}).get('state')
        elif operation != HOLD:
            item = parameters.get('item') if operation != DECLARE else (items[0] if items else None)
            answer.update(item=item, state=(wrote.get(item) or {}).get('state'))
            if operation == DECLARE:
                answer['pool'] = (wrote.get(item) or {}).get('pool')
            if operation == REBRANCH:
                answer['branch_item'] = next((identity for identity in items if identity != item), None)
        return answer

    def _with_packet(self, transition):
        """The transition of a command a host principal may send, writing the record of the packet it
        came in with in the same transaction. A command that came in no packet is run as it is."""
        def run(conn, params, before):
            changes = transition(conn, params, before)
            packet = params.get('packet')
            if packet is None:
                return changes
            entity = packet_id(packet['principal'], packet['nonce'])
            if entity in before:
                raise Refused('space_packet_replayed', 'this nonce was seen: sign a new packet')
            wrote = {identity: {'state': change['data'].get('state'), 'pool': change['data'].get('pool')}
                     for identity, change in changes.items()}
            return dict(changes, **{entity: {'kind': PACKET_KIND, 'data': dict(
                packet, outcome='accepted', refusal=None, answer=None, wrote=wrote)}})
        return run

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
            # An item the owner marked Keep is never matched by an owner's signal, whatever the event.
            if (record['state'] in SIGNALLED and not record.get('owner_keep')
                    and event in record['ends_on']['events'] and owner_matches(record['owner'], subject)):
                out.append((identity, version, record))
        return out

    def _named(self, event, subject, rows):
        """The items a signal names, as (identity, record) in the order named, each judged: `rows` is
        {identity: (version, record or None)} as read. Refuses the whole signal by the first item that is
        not one, changed, is in no state a signal reaches, does not end on the event, or holds the
        owner's Keep and is not the one item the owner's Abandon names."""
        abandon = subject.get('owner_abandon')
        if abandon is not None and event != ABANDON_EVENT:
            raise Refused('space_owner_abandon_event', 'the owner\'s Abandon is the event ' + ABANDON_EVENT)
        out = []
        for one in subject['items']:
            identity = one['item']
            version, record = rows.get(identity) or (0, None)
            if record is None:
                raise Refused('space_no_item', 'no such record: %r' % (identity,))
            if version != one['version']:
                raise Refused('space_item_version:' + identity, 'the item is at version %r, the signal names %r'
                              % (version, one['version']))
            if record['state'] not in SIGNALLED:
                raise Refused('space_item_state:' + record['state'], 'a signal reaches a present, kept or '
                              'deferred item: %s' % identity)
            if event not in record['ends_on']['events']:
                raise Refused('space_item_event:' + identity, 'the item does not end on ' + event)
            if record.get('owner_keep') and not (abandon is not None and abandon['item'] == identity):
                raise Refused('space_owner_keep:' + identity, 'the owner marked this item Keep: only the '
                              'owner\'s Abandon of this item ends that')
            out.append((identity, dict(record)))
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

    def _main_of(self, record):
        """The repository the declarations name for an item's scope, in its canonical form, or None."""
        scope = (record.get('owner') or {}).get('scope') or {}
        if scope.get('type') == 'plain_repository' and _is_str(scope.get('id')):
            return canonical_path(scope['id'])
        for project in self.projects:
            if scope.get('type') == 'project' and project.get('project') == scope.get('id'):
                return canonical_path(project['repository'])
        return None

    def _private(self, repository):
        """The live agent repository item that `repository` is, or lies inside, or None."""
        for identity, record in self.items().items():
            if record.get('kind') == 'agent_repository' and record.get('state') in LIVE:
                path = record['locator']['path']
                if repository == path or beneath(repository, path):
                    return identity
        return None

    def _kept_refs(self, repository, prefix):
        """{ref: commit} of the refs of `repository` under `prefix`, read now by git through the one
        Git boundary. Raises Refused when the repository is not at its path or git cannot read it."""
        global _git_process
        if _git_process is None:
            _git_process = _sibling('git_process')
        if resolved_path(repository) != repository or not os.path.isdir(repository):
            raise Refused('space_keep_repository', 'the main repository is not at its path: ' + repository)
        try:
            done = _git_process.run(['git', '-C', repository, 'for-each-ref',
                                     '--format=%(objectname) %(refname)', prefix],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=GIT_SECONDS)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            raise Refused('space_keep_repository', 'git could not read the main repository: %s' % error)
        if done.returncode:
            raise Refused('space_keep_repository', 'git could not read the main repository: '
                          + done.stderr.decode('utf-8', 'replace').strip()[-300:])
        lines = done.stdout.decode('utf-8', 'surrogateescape').split('\n')[:-1]
        return {name: commit for commit, _, name in (line.partition(' ') for line in lines)}

    def _item_branch(self, path):
        """The branch HEAD names in the item at `path`, as a full ref, or None when it is detached, read
        now by git through the one Git boundary. Raises Refused when git cannot say."""
        global _git_process
        if _git_process is None:
            _git_process = _sibling('git_process')
        try:
            done = _git_process.run(['git', '-C', path, 'symbolic-ref', '--quiet', 'HEAD'],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=GIT_SECONDS)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            raise Refused('space_keep_item', 'git could not read the item: %s' % error)
        out = done.stdout.decode('utf-8', 'replace').strip()
        said = done.stderr.decode('utf-8', 'replace').strip()
        if done.returncode == 0 and out:
            return out
        if done.returncode == 1 and not out and not said and os.path.isdir(path):
            return None
        raise Refused('space_keep_item', 'git could not read the branch of the item: ' + said[-300:])

    def _item_head(self, path):
        """The commit HEAD names in the item at `path`, read now by git through the one Git boundary, or
        None when git reads the item and its HEAD names no commit. Raises Refused when git cannot read
        the item there: what could not be read is never taken for an item with no commit."""
        global _git_process
        if _git_process is None:
            _git_process = _sibling('git_process')
        try:
            done = _git_process.run(['git', '-C', path, 'rev-parse', '--verify', '--quiet', 'HEAD^{commit}'],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=GIT_SECONDS)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            raise Refused('space_keep_item', 'git could not read the item: %s' % error)
        out = done.stdout.decode('utf-8', 'replace').strip()
        said = done.stderr.decode('utf-8', 'replace').strip()
        if done.returncode == 0 and out:
            return out
        if done.returncode == 1 and not out and not said and os.path.isdir(path):
            return None
        raise Refused('space_keep_item', 'git could not read the item at its locator: ' + (said[-300:] or path))

    def _checked_snapshot(self, identity, record, snapshot):
        """The snapshot attempt a keep command names, read from the store by the Ledger itself."""
        if not isinstance(snapshot, dict) or set(snapshot) != {'path', 'number', 'size', 'manifest'}:
            raise _invalid('snapshot', 'the path, the number, the size and the manifest digest of one attempt')
        number, path = snapshot['number'], snapshot['path']
        if not _is_bytes(number) or number < 1 or not _is_bytes(snapshot['size']) or not _is_str(snapshot['manifest']):
            raise _invalid('snapshot', 'an attempt number from 1, a size and a digest')
        folder = os.path.join(self.snapshot_store, *kept_parts(identity, record))
        if path != os.path.join(folder, str(number)):
            raise Refused('space_keep_snapshot', 'not a numbered folder of this item in the snapshot store')
        try:
            if resolved_path(path) != path or not os.path.isdir(path):
                raise Refused('space_keep_snapshot', 'the attempt is not a folder at its own path')
            manifest = os.path.join(path, MANIFEST)
            descriptor = os.open(manifest, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            with os.fdopen(descriptor, 'rb') as file:
                digest = hashlib.sha256(file.read()).hexdigest()
        except OSError as error:
            raise Refused('space_keep_snapshot', 'the attempt could not be read: %s' % error)
        if digest != snapshot['manifest']:
            raise Refused('space_keep_manifest', 'the manifest of the attempt does not have the digest named')
        return {'path': path, 'number': number, 'size': snapshot['size'], 'manifest': digest}

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
        form = params.get('form')
        if form is not None and (kind != 'agent_repository' or form not in
                                 ('agent', 'worker_clone', 'batch_clone', 'candidate_workspace')):
            raise _invalid('form', 'a known agent repository form')
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
        if kind == 'worktree':
            repository = self._repository_of({'parent': parent, 'owner': owner})
            if repository is not None and resolved_path(repository) != repository:
                raise Refused('space_locator_link', 'the repository of this worktree is declared through a link: '
                                                    'declare the repository by its resolved path')
        return {'kind': kind, 'host': params['host'], 'pool': self._pool_for(kind, canonical, params.get('device'),
                                                                             params.get('pool')),
                'locator': canonical, 'key': key, 'parent': parent, 'owner': owner, 'creator': params['creator'],
                'adopted': adopted, 'branch': params.get('branch'), 'start': params.get('start'), 'form': form,
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

    def _retry_subject(self, subject):
        if not isinstance(subject, dict) or set(subject) != {'pool'} or subject['pool'] not in self.config['pools']:
            raise _invalid('subject', 'the pool requesting admission')
        return dict(subject)

    def _retry_item(self, record, pool):
        return (record.get('state') == 'deferred' and record.get('pool') == pool
                and not record.get('owner_keep')
                and (record.get('due') or {}).get('event') in record['ends_on']['events'])

    def _t_signal(self, conn, params, before):
        event = params.get('event')
        if event == 'admission_requested':
            subject = self._retry_subject(params.get('subject'))
            changes = {}
            for identity, old in before.items():
                record = dict(old['data'])
                if old['kind'] == ITEM_KIND and self._retry_item(record, subject['pool']):
                    record['state'] = 'due'
                    _new_removal(record)
                    changes[identity] = {'kind': ITEM_KIND, 'data': record}
            return changes
        if event not in self.lifecycle['events']:
            raise Refused('space_unknown_event', 'not an event of the lifecycle table')
        changes = {}
        subject = _checked_subject(params.get('subject'))
        if 'items' in subject:
            # Exactly the items named, each read in this transaction at the version the store checked.
            rows = {one['item']: (before[one['item']]['version'], dict(before[one['item']]['data'])
                                  if before[one['item']]['kind'] == ITEM_KIND else None)
                    for one in subject['items'] if one['item'] in before}
            abandon = subject.get('owner_abandon')
            named = self._named(event, subject, rows)
            # Who abandons is the owner this store's membership names, whoever the caller is.
            by = self._owner(params, abandon['at'], 'the owner\'s Abandon') if abandon is not None else None
            for identity, record in named:
                record['state'] = 'due'
                record['due'] = {'event': event}
                if abandon is not None and abandon['item'] == identity:
                    # Only here is the owner's Keep ended: by the owner's Abandon of this exact item.
                    record['abandoned'] = {'by': by, 'at': abandon['at'],
                                           'ended_keep': record.get('owner_keep') or None}
                    record['owner_keep'] = None
                    if record.get('disposition'):
                        record['disposition'] = dict(record['disposition'], state='refused')
                _new_removal(record)
                changes[identity] = {'kind': ITEM_KIND, 'data': record}
            return changes
        for identity, _version, record in self._matching(event, subject):
            record['state'] = 'due'
            record['due'] = {'event': event}
            _new_removal(record)
            changes[identity] = {'kind': ITEM_KIND, 'data': record}
        return changes

    def _freed(self, before, pools, exclude=None):
        waiting = {hold_id(key): value for key, value in self.holds().items()
                   if value['state'] == 'waiting' and set(value['needs']).intersection(pools)
                   and hold_id(key) != exclude}
        if any(key not in before for key in waiting):
            raise Refused('space_holds_changed', 'a waiting hold appeared before the freeing write')
        return {key: {'kind': HOLD_KIND, 'data': dict(value, freed=True)}
                for key, value in waiting.items()}

    def _t_outcome(self, conn, params, before):
        identity, record = self._stored(params, before)
        outcome, facts = params.get('outcome'), params.get('facts')
        if outcome not in OUTCOMES or not isinstance(facts, dict):
            raise _invalid('outcome', 'one of %s, with the facts' % ', '.join(OUTCOMES))
        if record['state'] not in ('due', 'removing'):
            raise Refused('space_item_state:' + record['state'], 'outcome is written for an item that is due or removing')
        if outcome == 'removing' and record['state'] != 'due' and not (
                record['state'] == 'removing' and _is_str(facts.get('left_at'))):
            raise Refused('space_item_state:' + record['state'], 'removing follows due; it is written again '
                          'only to record where the thing was left')
        if record['state'] == 'removing' and (outcome == 'kept' or (
                outcome == 'deferred' and facts.get('rule') not in TOOL_REFUSALS)):
            raise Refused('space_item_state:removing', 'a removing item is removed to the end; it is deferred '
                          'only with a deferral its remover names: ' + ', '.join(TOOL_REFUSALS))
        if outcome == 'removed' and record['kind'] in KEEP_KINDS and not record.get('kept'):
            raise Refused('space_no_keep_record', 'a worktree and a private repository are removed only after '
                          'their commits were recorded: the item has no keep record')
        if outcome == 'removed' and record['kind'] in KEEP_KINDS and not (record.get('kept') or {}).get('attempt'):
            raise Refused('space_keep_stale', 'the keep record was written before the item last became due or '
                          'removing: it is not the record of this removal')
        if outcome == 'removing' and record['state'] == 'due':
            _new_removal(record)
        if outcome == 'deferred':
            if not _is_str(facts.get('rule')):
                raise _invalid('facts.rule', 'the rule that refused')
            attempts = (record.get('deferral') or {}).get('attempts', 0) + 1
            record['deferral'] = dict(facts, attempts=attempts)
            if record.get('disposition'):
                record['deferral']['decision_request'] = record['disposition']['alias']
        elif outcome == 'removed':
            record['removal'] = dict(facts)
            record['confirmed'] = None
        elif outcome == 'removing':
            record['removal'] = dict(facts)
        if outcome == 'kept' and record['kind'] == 'branch' and facts.get('action') == 'mark_contained':
            record['contained'] = dict(facts)
        if 'owner_keep' in facts:
            mark = facts['owner_keep']
            if outcome != 'kept' or not isinstance(mark, dict) or 'by' in mark or not _is_time(mark.get('at')):
                raise _invalid('facts.owner_keep', 'use the owner signed space_disposition command')
            raise Refused('not_authorized', 'owner Keep requires the signed space_disposition command')
        if outcome == 'deferred' and (record.get('disposition') or {}).get('state') == 'authorized':
            record['disposition'] = dict(record['disposition'], state='refused')
        record['state'] = outcome
        pools = set()
        if outcome == 'removed':
            if type(facts.get('freed')) is int and facts['freed'] > 0:
                pools.add(record['pool'])
            host = facts['host'] if isinstance(facts.get('host'), dict) else {}
            backing = (self.pool(record['pool']) or {}).get('backing')
            if backing and host.get('pool') == backing and type(host.get('freed')) is int and host['freed'] > 0:
                pools.add(backing)
        return dict(self._freed(before, pools), **{identity: {'kind': ITEM_KIND, 'data': record}})

    def _t_keep(self, conn, params, before):
        identity, record = self._stored(params, before)
        if record['kind'] not in KEEP_KINDS:
            raise Refused('space_keep_kind', 'a keep record is written for a worktree or an agent repository')
        if record['state'] not in ('removing', 'due'):
            raise Refused('space_item_state:' + record['state'], 'keep is written for an item that is due or removing')
        repository, refs = params.get('repository'), params.get('refs')
        if not _is_str(repository) or self._main_of(record) != repository:
            raise Refused('space_keep_repository', 'not the repository the declarations name for this item')
        private = self._private(repository)
        if private is not None:
            raise Refused('space_keep_private', 'a main repository is never a private repository: ' + private)
        prefix = kept_prefix(identity, record)
        if not isinstance(refs, dict) or not all(
                _is_str(name) and name.startswith(prefix) and len(name) > len(prefix) and _is_str(commit)
                for name, commit in refs.items()):
            raise _invalid('refs', 'each kept ref of this item, under %s, with its commit' % prefix)
        prior = record.get('kept') or {'repository': repository, 'path': record['locator']['path'], 'refs': {},
                                       'snapshots': []}
        if prior['repository'] != repository:
            raise Refused('space_keep_repository', 'the keep record names another main repository')
        number = _one_attempt(refs, prefix)
        found = self._kept_refs(repository, prefix) if refs else {}
        merged = dict(prior['refs'])
        for name in sorted(refs):
            if found.get(name) != refs[name]:
                raise Refused('space_keep_ref:' + name, 'the main repository does not hold this ref at the commit '
                              'named: %s' % (found.get(name),))
            if merged.get(name, refs[name]) != refs[name]:
                raise Refused('space_keep_ref_moved:' + name, 'the keep record holds this ref at another commit')
            merged[name] = refs[name]
        snapshots = [dict(entry) for entry in prior['snapshots']]
        if params.get('snapshot') is not None:
            attempt = self._checked_snapshot(identity, record, params['snapshot'])
            same = [entry for entry in snapshots if entry['number'] == attempt['number']]
            if same and same[0] != attempt:
                raise Refused('space_keep_snapshot_replaced', 'the keep record holds this attempt with other figures')
            if not same:
                snapshots = sorted(snapshots + [attempt], key=lambda entry: entry['number'])
        head = self._item_head(record['locator']['path'])
        if head is not None and refs.get('%s%d/head' % (prefix, number or 0)) != head:
            raise Refused('space_keep_head', 'the item\'s HEAD is %s, and the write names no kept head of its '
                          'attempt at that commit' % head)
        record['kept'] = {'repository': repository, 'path': prior['path'], 'refs': merged, 'snapshots': snapshots,
                          'attempt': {'number': number, 'head': head}}
        return {identity: {'kind': ITEM_KIND, 'data': record}}

    def _t_keep_branch(self, conn, params, before):
        identity, record = self._stored(params, before)
        decision = record.get('disposition') or {}
        if (record['kind'] != 'worktree' or record['state'] != 'removing'
                or decision.get('state') != 'authorized' or decision.get('choice') != 'discard'):
            raise Refused('space_keep_branch_state', 'a kept branch is recorded for a worktree that is removing '
                          'under an authorized Discard')
        branch, commit = params.get('branch'), params.get('commit')
        if not _is_str(branch) or branch.startswith('refs/') or not (
                _is_str(commit) and len(commit) in (40, 64) and not set(commit) - set('0123456789abcdef')):
            raise _invalid('branch', 'the short name of the kept branch, and its commit')
        # The main repository, for an agent's worktree too: an agent repository is private and is
        # removed later, so a kept branch is never read or recorded there (design 0.2).
        repository = self._main_of(record)
        if repository is None:
            raise Refused('space_keep_branch_repository', 'no main repository is known for this worktree')
        path = record['locator']['path']
        if self._item_head(path) != commit:
            raise Refused('space_keep_branch_head', 'the commit is not the one checked out in the worktree')
        if self._item_branch(path) is not None:
            raise Refused('space_keep_branch_attached', 'the worktree is on a branch: its branch holds the commit')
        name = 'refs/heads/' + branch
        if self._kept_refs(repository, name).get(name) != commit:
            raise Refused('space_keep_branch_ref', 'the repository does not hold the branch at the commit named')
        canonical = {'repository': repository, 'ref': branch}
        fields = {'commit': commit, 'worktree': identity, 'request': decision.get('alias')}
        held = self._at(locator_key('branch', canonical))
        new = params.get('branch_item')
        if held is not None:
            if new != held[0] or new not in before or held[2]['state'] not in ('declared', 'present', 'kept'):
                raise Refused('space_keep_branch_item', 'the branch item at this locator changed, or is in the '
                              'state ' + held[2]['state'])
            item = dict(before[new]['data'], state='kept', kept_branch=fields)
        else:
            if not _is_str(new) or not new.startswith(ITEM_PREFIX) or new in before:
                raise _invalid('branch_item', 'a new item identity for the branch')
            item = dict(self._new_item(
                {'item': new, 'kind': 'branch', 'host': record['host'], 'locator': canonical,
                 'owner': record['owner'], 'creator': record['creator'], 'start': commit,
                 'device': self.device(repository)}, 'kept', False), kept_branch=fields)
        record['kept_branch'] = {'branch': branch, 'commit': commit, 'item': new}
        return {identity: {'kind': ITEM_KIND, 'data': record}, new: {'kind': ITEM_KIND, 'data': item}}

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
        # The scope the run belongs to: the one its run or gate was issued with, before the one named.
        issued = (self._row(run_id(identity[len(HOLD_PREFIX):]), RUN_KIND)[1] or {}).get('scope')
        named = self._known_scope(params['scope']) if params.get('scope') is not None else None
        if issued is not None and named is not None and named != issued:
            raise Refused('space_hold_scope', 'the run was issued with another scope')
        return {identity: {'kind': HOLD_KIND, 'data': {'scope': issued or named or dict(NO_PROJECT),
                                                       'needs': needs, 'source': source, 'state': 'waiting',
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
        # The mode of the hold's own scope, read in this transaction: an act-mode run is never advised.
        if answer == 'advised' and self.acts(record.get('scope') or NO_PROJECT):
            raise Refused('space_answer_mode:' + ACTING, 'a run of a scope in act mode waits; it is not advised')
        record['state'], record['reason'] = answer, reason
        record['freed'] = False
        if params.get('used') is not None:
            record['used'] = self._per_pool(params['used'], 'used')
        if params.get('retry_asked') is True:
            record['retry_asked'] = True
        return {identity: {'kind': HOLD_KIND, 'data': record}}

    def _t_release(self, conn, params, before):
        identity, record = self._stored(params, before, 'hold', HOLD_KIND, 'space_no_hold')
        if record['state'] == 'released':
            raise Refused('space_hold_state:released', 'the hold is released already')
        # Only a promise that was counted frees anything: an admitted or advised hold, on the pools
        # where it still held bytes (its need above what its own items used at the last measurement).
        # A waiting hold held nothing, so its release marks no other hold (design 6.7).
        held = record.get('used') or {}
        pools = {pool for pool, need in record['needs'].items()
                 if record['state'] in ('admitted', 'advised') and need > held.get(pool, 0)}
        if params.get('used') is not None:
            record['used'] = self._per_pool(params['used'], 'used')
        record['state'] = 'released'
        return dict(self._freed(before, pools, exclude=identity),
                    **{identity: {'kind': HOLD_KIND, 'data': record}})

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
        return dict(self._freed(before, self.config['pools']), **{identity: {'kind': RECONCILE_KIND, 'data': {
            'started_by': params['started_by'], 'roots': list(params['roots']), 'engines': list(params['engines']),
            'counts': dict(counts)}}})

    def _t_issue(self, conn, params, before):
        entity, identity, principal = params.get('run'), params.get('identity'), params.get('principal')
        if not _is_str(identity) or entity != run_id(identity) or entity in before:
            raise _invalid('run', 'a new run or gate identity')
        if not _is_str(principal) or not _is_str(params.get('issued_by')):
            raise _invalid('issue', 'the principal it is issued to and the one that issued it')
        if params['issued_by'] in HOST_PRINCIPALS:
            raise Refused('space_not_permitted:' + ISSUE, 'no host principal issues a run')
        data = {'run': identity, 'principal': principal, 'label': params.get('label'),
                'issued_by': params['issued_by']}
        if params.get('scope') is not None:
            data['scope'] = self._known_scope(params['scope'])
        return {entity: {'kind': RUN_KIND, 'data': data}}

    def _t_packet(self, conn, params, before):
        entity, record = params.get('packet'), params.get('record')
        if (not isinstance(record, dict) or not _is_str(record.get('principal')) or not _is_str(record.get('nonce'))
                or entity != packet_id(record['principal'], record['nonce'])
                or record.get('outcome') not in PACKET_OUTCOMES):
            raise _invalid('packet', 'the record of one packet, under its principal and nonce')
        if entity in before:
            raise Refused('space_packet_replayed', 'this nonce was seen')
        return {entity: {'kind': PACKET_KIND, 'data': dict(record)}}

    def _t_mode(self, conn, params, before):
        scope = self._known_scope(params.get('scope'))
        entity, old, new, at, packet = (params.get('mode_record'), params.get('from'), params.get('to'),
                                        params.get('at'), params.get('command'))
        if entity != mode_id(scope):
            raise _invalid('mode_record', 'the mode record of this scope')
        prior = before.get(entity)
        if prior is not None and prior['kind'] != MODE_KIND:
            raise _invalid('mode_record', 'the mode record of this scope')
        if new not in MODES or not _is_time(at):
            raise _invalid('mode', 'one of %s, and when' % ', '.join(MODES))
        signed_command = packet.get('command') if isinstance(packet, dict) else None
        self._mode_command(signed_command)
        if (signed_command['parameters']['mode'] != new
                or checked_scope(signed_command['parameters']['scope']) != scope):
            raise _invalid('command', 'the owner\'s signed command for this scope and mode')
        # Who sent it. The store hands a transition the parameters of the command it is running, so the
        # command this Ledger sent is the one being run only when these are its very parameters; a
        # space_mode command given to the store by anyone else has none. Its principal, id and nonce must
        # be the signed command's own: the owner is on the journal record and the owner's nonce is spent.
        outer = self._outer
        if (outer is None or outer['parameters'] is not params
                or any(outer[field] != signed_command[field] for field in ('principal', 'command_id', 'nonce'))):
            raise Refused('not_authorized', 'the mode command is sent by the owner who signed it, as that command')
        # The owner and the signature, read from this store inside this transaction.
        self._mode_signer(signed_command, packet.get('signature'), at, self._membership())
        current = prior['data']['mode'] if prior else REPORTING
        if old != current:
            raise Refused('space_mode_moved:' + current, 'the scope is no longer in the mode the switch was read from')
        if new == current:
            raise Refused('space_mode_unchanged:' + current, 'the scope is in this mode already')
        refusal = self._act_refusal(scope) if new == ACTING else None
        if refusal is not None:
            raise refusal
        switch = {'from': old, 'to': new, 'at': at, 'command': dict(packet)}
        history = list(prior['data']['history']) if prior else []
        return {entity: {'kind': MODE_KIND, 'data': {
            'scope': scope, 'mode': new, 'since': {'at': at, 'command': dict(packet)},
            'history': history + [switch]}}}


# ---------------------------------------------------------------------------------------------
# The sending side: a hook or a helper signs as its host principal, never as the owner.
# ---------------------------------------------------------------------------------------------

def key_path(principal, folder):
    """Where a host principal's key is kept in the installation folder."""
    return os.path.join(folder, KEYS_FOLDER, principal)


def signed(principal, operation, parameters, folder, canonical, issued_at, command_id=None, nonce=None):
    """The packet {command, signature} for one command, signed with the host principal's own key from
    the installation folder `folder`. `canonical` gives the bytes a command is signed over (the store's
    canonical_bytes); `issued_at` is the time the caller read, which the Ledger bounds the packet's age
    by. Each packet has a nonce of its own. A sender that sends a packet again after its age bound
    signs it again with the packet's own `nonce` and `command_id`: the Ledger answers that with the
    original answer. Refused by name when the principal is not a host principal or its key does not
    sign; the owner's key is never read."""
    if principal not in HOST_PRINCIPALS:
        raise Refused('not_authorized', 'not a host principal of the space ledger')
    if not _is_str(operation) or not isinstance(parameters, dict):
        raise _invalid('command', 'an operation and a mapping of parameters')
    if not _is_time(issued_at):
        raise _invalid('issued_at', 'the time the packet is signed at')
    if nonce is not None and (not _is_str(nonce) or any(c.isspace() for c in nonce)):
        raise _invalid('nonce', 'the nonce of the packet that is sent again')
    key = key_path(principal, folder)
    command = {'principal': principal, 'operation': operation, 'parameters': parameters,
               'command_id': command_id or 'space:' + uuid.uuid4().hex, 'nonce': nonce or uuid.uuid4().hex,
               'issued_at': issued_at}
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
    spec = importlib.util.spec_from_file_location(
        'veldo_space_' + name, os.path.join(os.path.dirname(os.path.abspath(__file__)), name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None, stdin=None, stdout=None, stderr=None):
    """veldo space sign --as <host principal> [--installation <folder>]: read one command
    {operation, parameters} on standard input and print the packet signed as that host principal, stamped
    with the time it is signed at. The Ledger refuses it once it is older than PACKET_AGE seconds, so it
    is sent at once. A command that carries the command_id and nonce of a packet signed before is that
    packet signed again: the Ledger answers it with the original answer. The installation folder is the one the installation reader resolves. Exit 1 with the
    refusal's name when there is no installation, no key, or the principal is not a host principal."""
    import argparse
    import time
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
                        _sibling('control_store').canonical_bytes, time.time(), command.get('command_id'),
                        command.get('nonce'))
    except Refused as refusal:
        stderr.write('veldo space: refused %s\n' % refusal.code)
        return 1
    stdout.write(json.dumps(packet, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
