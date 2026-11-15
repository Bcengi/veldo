#!/usr/bin/env python3
"""The Docker adapter: whose a container, a network and a volume is, the snapshot of an engine
context, and the engine's event stream read as a pipe (design section 6.4, VELDO-0306).

WHAT IS HERE. An Adapter on one space ledger, for the engine contexts the installation names:

  snapshot(engine)   reads every container, network and volume of the context with its labels and
                     records each: an item for an object a run owns, a report for one nobody can be
                     shown to own
  start()            for each context, the engine's time, the snapshot, and then the subscription to
                     its event stream since that time
  pipes()            {descriptor: engine}: the output pipe of each context's one client process, for
                     the service loop's poll set (control_service.serve)
  readable(fd)       the poll set found a pipe readable: every whole event line it holds is handled,
                     and end of file takes a new snapshot before a new subscription

THIS MODULE REMOVES NOTHING. It runs no stop, no remove and no prune, and it has no way to delete: the
only commands it gives an engine are ls, inspect, system info and events. A run's objects are removed where
everything is removed: the event is sent through Signal (control_space_signal.signal), the kind
registry gives the order (containers stopped and removed first, then networks, then volumes: design
6.4 and section 5), the safety rules judge each item, and the removers (control_space_remove) name one
object to the engine with no force option. What this module adds to that is the record the removers
need: an item whose locator holds the identity seen when the object was found.

WHOSE AN OBJECT IS (design 6.4, the first two mechanisms). An object belongs to a run when it carries

  the run's label          the engine label veldo.space.run (control_space_remove.RUN_LABEL) whose
                           value is the run's space label, the identity the ledger records the run
                           under (the id of owner.run, or owner.gate for a gate)
  the run's compose name   the label compose stamps, com.docker.compose.project, whose value is
                           compose_project(label): the name derived from the run's label

and the run is one the ledger knows: a run or gate that owns an item which is neither removed nor
gone (`known_runs`), or one the caller's `runs()` names. Such an object is an item owned by that run,
on the context it was found on, made by the ledger's adopt with the rule that proved it (run_label or
compose_project). Every context the installation names is read; an object on the second context is
recorded on the second context.

EVERYTHING ELSE IS A REPORT, NEVER AN ITEM, AND IS NEVER REMOVED. An object with no label and no
compose name of a known run is not attributable: two runs can share an engine, and nothing the engine
says of the object names the process that asked for it. It gets a report record (the ledger's report:
no owner, no ending event), with what was found, why no rule gave it an owner, and the runs that were
live when it appeared. It is never given to the one live run, or to any run. The same holds for

  unknown_run   the object carries the run's label, and the value names no run the ledger knows
  two_runs      its label names one run and its compose name another
  no_identity   the engine showed it without the identity an item is known by (below)

AN OBJECT WITH NO RUN LABEL INSIDE A RECORDED WORKTREE (design 6.4, the last two mechanisms;
VELDO-0307). An object that carries neither the run's label nor a known run's compose name can still be
tied to a worktree by what the engine says of it (`placed`):

  compose's working folder   the label com.docker.compose.project.working_dir: the folder compose ran in
  compose's files            the label com.docker.compose.project.config_files: the files it read
  a bind mount's source      for a container, the host source of each bind mount

When every one of these the object carries leads inside the same recorded worktree, that worktree is
the proposed owner. Which worktree a path is inside is the reconciler's to say
(control_space_reconcile.worktree_inside): by where the path leads, never by a folder's name. Paths
that are split (one inside a worktree and one outside every worktree, or two inside two different
worktrees) are a conflict and give none: the object is a report with no proposed owner and is never
adopted by this rule. A path that cannot be read as a path gives none either. What is then written depends on the mode of the worktree's scope, and the
reconciler's rule reads it (adopt_inside_worktree): in report mode a report that shows the worktree's
owner as the proposed owner, with the label or the mount that gave it, and no item; in act mode an
item adopted with the worktree as its parent, by the rule inside_recorded_worktree. An object the
engine showed without its identity gets no proposal. A report with no proposal says why its paths
gave no worktree (not_placed). The adapter applies this rule only when it was
given the reconciler (`reconcile`); without one such an object is a report with no proposed owner.

MEASURED, 2026-11-14, on both engines of the host (contexts default, engine 29.3.0, and desktop-linux,
29.2.1; compose 5.0.2), with a project made for the check and taken down after it: compose writes both
labels on a container, as absolute paths, and the engine reports a bind mount's source as the host
path. It writes neither label on a network or a volume. So on these engines a container is placed by
this rule and a network or a volume is not: it stays a report with no proposed owner. The labels are
read on every kind all the same, and an engine that writes them gets the adoptions.

THE PROTECT LIST COMES FIRST (design section 7, the protect list; VELDO-0307 AC3). Before anything is
written, proposed or adopted for an object, `covered` reads the protect list in force (the ledger's):

  its name             a name pattern for its type, on an engine the entry names
  its compose project  the label com.docker.compose.project equals a protected project name
  its labelled path    compose's working folder or one of its files is at, above or beneath a protected
                       path, as written or where it leads; a protected path is protected on every engine

A covered object is listed as protected (`protected_objects`) and gets nothing else: no item, no
report, no proposed owner. A report written for it before it was covered is marked gone, a ledger
write that removes nothing. The ledger's adopt and report refuse a protected name or compose project
again, as space_protected. This module asks for both owner labels of every object and puts each one
the object carries in the locator, so a protected compose project is seen whatever else it carries.

IMAGE INVENTORY AND PROVENANCE (VELDO-0328). `images(engine)` reads the images of a context and lists
those the protect list covers: by a name it carries (a tag in full, or its repository without the tag
or the digest), by its compose project label or by its labelled path. The listing alone writes nothing and the object snapshot does not infer image provenance.
`built(engine, tag, label, image_id)` is the creator's completion seam: after its build it names
exactly the tag, the known run and the image identity it built. Only that tag becomes an item, owned
by the run's ticket. An image label alone proves no build: a pull can carry inherited labels.
`pulled(engine, name)` and image pull events record an ownerless report by image identity, once per
engine, with disposition kept and no ending event. A later build completion cannot adopt an image
already recorded as pulled. Unknown tag events never invent a builder. Both seams inspect afresh and
read every name of the image against the protect list before any write. The existing Signal, rules
and remove_tag remover handle the ending event; this adapter still has no removal operation.
Images and networks also inherit the entry of a protected container (VELDO-0341). The image's Id
is compared with the container's Image, so a tag moved since creation does not change which image
is protected. Network names and NetworkID are read from NetworkSettings.Networks. Every such check
lists all containers, including stopped ones, and inspects their current protection. An unread
relationship refuses discovery; the removal probe makes this same read at each attempt. No reverse
relationship protects a run's container merely because its image or network is protected.

A CONTAINER THAT MOUNTS WHAT IS PROTECTED IS PROTECTED (design section 7, the protect list; the review
of VELDO-0306, finding 2). Before a container is recorded its mounts are read from the record the
engine showed: a volume the protect list covers by its name or by its compose project label, or a
bind source at, above or beneath a protected path, makes the container protected, whatever labels it
carries: it gets neither an item nor a report. A container whose mounts could not be read, or one
whose mounted volume could not be asked for while a compose project is protected, is not recorded
either. Rule 2 reads the mounts again before any removal (control_space_signal).

THE IDENTITY IN THE LOCATOR (control_space_remove.IDENTITY; the third review of VELDO-0300, finding
E). A name proves nothing: a volume can be removed and made again under the same name, holding new
data. So each record holds what the engine said of the object when it was found:

  container, network   id, the engine's Id
  volume               created_at, the engine's CreatedAt (an engine gives a volume no Id)
  each                 run_label when the object carries the run's label, compose_project when it
                       carries compose's

An object the engine shows without its Id, or a volume without its CreatedAt, is reported and never
an item: an item that cannot be proved to be its object could only wait.

AN OBJECT MADE AGAIN UNDER A RECORDED NAME. When the engine shows, under the name of a live record,
an object with another Id or another CreatedAt, the recorded object is not there any more. The record
is marked gone (a ledger write that removes nothing) and the object found is judged as a new one, by
its own labels. A record that cannot be marked gone (it is removing or kept) stays, and the object is
left unrecorded: nothing is removed by a record that does not name it, because the removers compare
the identity again.

WHAT COULD NOT BE READ WRITES NOTHING. A context whose list or inspect fails, or answers with
something that is not the JSON records asked for, is unread: the snapshot says so and records
nothing, and nothing is marked gone because it was not listed. A record is marked gone only when its
engine was asked for that one object and answered that it holds no such object. When the known runs
cannot be read, nothing is recorded.

EVENTS. The subscription is one client process per context, `docker --context <engine> events`, whose
output pipe is non-blocking and is read only when the poll set says it is readable. There is no
thread, no timer and no interval: this module imports no clock.

NOTHING MADE BETWEEN THE SNAPSHOT AND THE SUBSCRIPTION IS MISSED (the review of VELDO-0306, finding
3). Before each snapshot, at start and at end of file, the engine is asked for its own time (`system
info`), and the subscription that follows the snapshot is made with `--since` that time: the engine
then prints again every event from before the snapshot's first read on, and goes on with the new
ones. An event of an object the snapshot recorded writes nothing new. A context whose time could not
be read is down: it gets no snapshot and no subscription, because a subscription with no start would
miss what was made meanwhile. Each create, start, stop and destroy
event of a container, a network or a volume makes the adapter ask the engine for that one object and
record it as the snapshot would (a ledger write or a report), or mark its record gone when the engine
no longer holds it. An event of any other action is counted and nothing is asked. A line that is not
an event the adapter can read means something happened that it did not see, so the context is read
again whole.

END OF FILE on the pipe is not an error. The client is reaped, a new snapshot is taken, and only then
is a new subscription made. Two things stop a broken engine from being asked without end: a context
whose new snapshot could not be read is not subscribed again, and neither is one whose stream ended
twice in a row without one byte. Such a context is down, with the reason, until start() is called
again; an event, never a timer, does that.

A CONTEXT THAT IS DOWN IS SAID, NEVER SILENT (the review of VELDO-0306, finding 4). The answer of
start() and of readable() names the context and the reason under `down`, `unread()` returns every
context that is not read now with its reason, and `tell`, when the caller gave one, is called once
for each context that goes down. The service writes it to its observation log (control_service
docker_readable) and shows it as an engine not read (docker_unread).

WHAT IS NOT HERE. Wiring build completion into project-specific build commands.
Reconcile's counts and its record (VELDO-0315). Giving a run its label and its compose
project name in its environment is the receiver's (design 6.3); `given` says what the two are.

Standard library only. The ledger is the control_space.Ledger the caller passes in.
"""
import fnmatch
import hashlib
import json
import os
import subprocess

SCHEMA = 'veldo.control_space_docker/v1'

RUN_LABEL = 'veldo.space.run'  # control_space_remove.RUN_LABEL: the run's label on an object
COMPOSE_PROJECT = 'com.docker.compose.project'  # the label compose stamps on what it creates
COMPOSE_WORKING_DIR = 'com.docker.compose.project.working_dir'  # the folder compose ran in
COMPOSE_CONFIG_FILES = 'com.docker.compose.project.config_files'  # the files compose read, comma separated
INSIDE_WORKTREE = 'inside_recorded_worktree'  # control_space_reconcile.RULE: the rule of an adoption by a path
IMAGES = ('image', 'ls', '--quiet', '--no-trunc')
# The protect list's entry type that holds the name patterns of each kind of object.
PROTECT_NAME = {'container': 'container', 'network': 'network', 'volume': 'volume', 'image': 'image'}
LABEL_VARIABLE, COMPOSE_VARIABLE = 'VELDO_SPACE_LABEL', 'COMPOSE_PROJECT_NAME'

KINDS = ('container', 'network', 'volume')
# How each kind is listed, what names one object to inspect, and the locator field of its identity.
LISTED = {
    'container': ('container', 'ls', '--all', '--quiet', '--no-trunc'),
    'network': ('network', 'ls', '--quiet', '--no-trunc'),
    'volume': ('volume', 'ls', '--quiet'),
}
IDENTITY = {'container': ('id', 'Id'), 'network': ('id', 'Id'), 'volume': ('created_at', 'CreatedAt')}
# The networks an engine makes for itself. They are no run's, the engine refuses to remove them, and
# they are not reported.
ENGINE_NETWORKS = ('bridge', 'host', 'none')
EVENTS = ('events', '--format', '{{json .}}', '--filter', 'type=container', '--filter', 'type=network',
          '--filter', 'type=volume', '--filter', 'type=image')
SINCE = '--since'  # the option that makes the engine print again what happened from a time on
ENGINE_TIME = ('system', 'info', '--format', '{{.SystemTime}}')  # the engine's own time, read by its client
ACTIONS = ('create', 'start', 'stop', 'destroy')  # the events that become a ledger write or a report
ENDED = ('removed', 'gone')  # the states of a record whose thing is no longer there
SECONDS = 600  # the longest one read of an engine may take
CHUNK = 65536
NAMED = 20  # the most names written into one record
BARREN = 2  # a stream that ended this many times in a row without one byte is not started again
PLAIN = frozenset('abcdefghijklmnopqrstuvwxyz0123456789')


def compose_project(label):
    """The compose project name of the run whose space label is `label`: a name compose accepts, made
    of the label's plain characters and a part of the label's digest, so that two labels never share
    a name and nobody's own project has it by chance."""
    text = str(label)
    plain = ''.join(char if char in PLAIN else '-' for char in text.lower()).strip('-')[:32].strip('-')
    return 'veldo-%s-%s' % (plain or 'run', hashlib.sha256(text.encode('utf-8', 'surrogatepass')).hexdigest()[:16])


def given(label):
    """What a run is given so that what it creates is its own (design 6.3 and 6.4): the environment
    that carries its space label and its compose project name, and the option that puts the run's
    label on an object Veldo itself creates."""
    return {'environment': {LABEL_VARIABLE: str(label), COMPOSE_VARIABLE: compose_project(label)},
            'label': RUN_LABEL + '=' + str(label), 'option': ['--label', RUN_LABEL + '=' + str(label)]}


def known_runs(ledger):
    """The runs and gates the ledger knows, as {space label: owner}: each run or gate that owns an
    item which is neither removed nor gone, with the scope, the ticket, the lane and the run or gate
    of that owner. The space label is the run's id, or the gate's. A run with no project owns no
    Docker object (the ledger accepts no project for a session's scratch alone)."""
    found = {}
    for identity, record in sorted(ledger.items().items()):
        owner = record.get('owner')
        if not isinstance(owner, dict) or record.get('state') in ENDED:
            continue
        scope = owner.get('scope') or {}
        if scope.get('type') not in ('project', 'plain_repository'):
            continue
        run = owner.get('run') if isinstance(owner.get('run'), dict) else None
        label = run.get('id') if run else owner.get('gate')
        if not isinstance(label, str) or not label:
            continue
        mine = {'scope': dict(scope)}
        for part in ('ticket', 'lane'):
            if owner.get(part) is not None:
                mine[part] = owner[part]
        if run:
            mine['run'] = dict(run)
        else:
            mine['gate'] = owner['gate']
        if label not in found or len(mine) > len(found[label]):
            found[label] = mine
    return found


def _run(argv, cwd=None):
    """Run the engine's client and return (exit code, output). A client that is missing or does not
    end in time gives (None, what happened)."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    environment['LC_ALL'] = 'C'
    try:
        done = subprocess.run([str(word) for word in argv], cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=SECONDS)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return None, type(error).__name__ + ': ' + str(error)[:200]
    if done.returncode:
        return done.returncode, done.stderr.decode('utf-8', 'replace').strip()[-300:]
    return 0, done.stdout.decode('utf-8', 'replace')


def events_argv(engine, since=None, own=None):
    """The client command that prints the events of `engine`, one JSON record a line: from the engine
    time `since` on when one is given, and of the objects that carry the label `own` alone when one
    is given."""
    argv = ['docker', '--context', str(engine)] + list(EVENTS)
    if own:
        argv += ['--filter', 'label=' + str(own)]
    if since:
        argv += [SINCE, str(since)]
    return argv


def _spawn(engine, since=None):
    """Start the one client process that prints the events of `engine` from the engine time `since`."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    environment['LC_ALL'] = 'C'
    return subprocess.Popen(events_argv(engine, since), env=environment,
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            close_fds=True)


def _text(value):
    return value if isinstance(value, str) and value else None


def _said(error):
    return '%s: %s' % (type(error).__name__, str(error)[:300])


def absent(kind, code, out):
    """Whether the engine itself answered that it holds no such object. Only the engine's own answer
    counts: a client that could not reach the engine names a missing socket in much the same words."""
    text = str(out).lower()
    if code in (None, 0) or 'error response from daemon' not in text:
        return False
    return ('no such ' + kind) in text or (kind == 'network' and 'network ' in text and ' not found' in text)


def labels_of(kind, shown):
    """The labels the engine shows on an object: a container's are in its configuration."""
    held = (shown.get('Config') or {}).get('Labels') if kind in ('container', 'image') else shown.get('Labels')
    return held if isinstance(held, dict) else {}


def locator_of(engine, kind, shown):
    """The locator of the object the engine showed, with the identity seen now and each owner label it
    carries, or None when the engine gave it no name. The identity is absent from the locator when
    the engine did not give it."""
    name = _text(shown.get('Name'))
    if kind == 'container' and name:
        name = _text(name.lstrip('/'))
    if name is None:
        return None
    locator = {'engine': engine, 'name': name}
    field, key = IDENTITY[kind]
    if _text(shown.get(key)):
        locator[field] = shown[key]
    labels = labels_of(kind, shown)
    if _text(labels.get(RUN_LABEL)):
        locator['run_label'] = labels[RUN_LABEL]
    if _text(labels.get(COMPOSE_PROJECT)):
        locator['compose_project'] = labels[COMPOSE_PROJECT]
    return locator


def _beneath(path, root):
    return path.startswith(root.rstrip('/') + '/')


def mount_protected(engine, shown, protect, volume=None):
    """Whether a container mounts what the protect list covers: (entry, mount), (None, None) when it
    mounts nothing protected, or ('unread', why) when that could not be told. `shown` is the
    container's inspect record and `protect` the protect list in force, [{type, value, engines}].
    `volume(name)` returns the inspect record of a volume of this engine, or None when the engine
    could not show it; it is asked only while a compose project is protected on this engine."""
    mounts = shown.get('Mounts')
    if not isinstance(mounts, list) or not all(isinstance(mount, dict) for mount in mounts):
        return 'unread', 'the engine showed the container without its mounts'
    entries = [entry for entry in protect if engine in entry.get('engines', ())]
    composed = [entry['value'] for entry in entries if entry['type'] == 'compose_project']
    for mount in mounts:
        name, source = mount.get('Name'), mount.get('Source')
        if mount.get('Type') == 'volume' or (isinstance(name, str) and name):
            if not (isinstance(name, str) and name):
                return 'unread', 'a volume mount has no name'
            for entry in entries:
                if entry['type'] == 'volume' and fnmatch.fnmatchcase(name, entry['value']):
                    return 'volume:' + entry['value'], name
            if composed:
                held = volume(name) if volume is not None else None
                if not isinstance(held, dict):
                    return 'unread', 'the mounted volume %s could not be read' % name
                labels = held.get('Labels')
                project = labels.get(COMPOSE_PROJECT) if isinstance(labels, dict) else None
                if project in composed:
                    return 'compose_project:' + project, name
        elif mount.get('Type') == 'bind':
            if not (isinstance(source, str) and source.startswith('/')):
                return 'unread', 'a bind mount has no source path'
            # A protected path is protected on every engine (rule 2 for a path reads no engine): the
            # snapshot store, which the Ledger adds with no engine, is covered like a configured path.
            for entry in protect:
                if entry['type'] != 'path':
                    continue
                for mine in {os.path.normpath(source), os.path.realpath(source)}:
                    for theirs in {os.path.normpath(entry['value']), os.path.realpath(entry['value'])}:
                        if mine == theirs or _beneath(mine, theirs) or _beneath(theirs, mine):
                            return 'path:' + entry['value'], source
    return None, None


def labelled_paths(labels):
    """The paths compose stamped on an object: [(how, path)], the folder it ran in and each file it
    read. A label the object does not carry gives nothing."""
    found = []
    folder = labels.get(COMPOSE_WORKING_DIR)
    if isinstance(folder, str) and folder.strip():
        found.append(('compose_working_dir', folder.strip()))
    files = labels.get(COMPOSE_CONFIG_FILES)
    if isinstance(files, str):
        found += [('compose_config_file', name.strip()) for name in files.split(',') if name.strip()]
    return found


def placed(kind, shown):
    """Every path the engine says of an object that can tie it to a worktree: [(how, path)]. The
    paths compose stamped on it, and for a container the host source of each bind mount."""
    found = labelled_paths(labels_of(kind, shown))
    if kind == 'container':
        mounts = shown.get('Mounts')
        for mount in mounts if isinstance(mounts, list) else ():
            if isinstance(mount, dict) and mount.get('Type') == 'bind':
                found.append(('bind_source', mount.get('Source')))
    return found


def image_names(shown):
    """The names an image carries: each tag and each digest name in full, and the repository of each
    without the tag or the digest. A protect entry that names a digest covers the image by the digest
    name, as the Ledger and rule 2 at removal read it."""
    names = []
    for field in ('RepoTags', 'RepoDigests'):
        held = shown.get(field)
        for name in held if isinstance(held, list) else ():
            if not (isinstance(name, str) and name):
                continue
            plain = name.split('@')[0]
            if ':' in plain and '/' not in plain.rsplit(':', 1)[1]:
                plain = plain.rsplit(':', 1)[0]
            names += [name]
            names += [plain] if plain else []
    return sorted(set(names))


def covered(engine, kind, names, labels, protect):
    """The protect entry that covers an object, with what it was found by: (type:value, by), or
    (None, None). `names` are the names the object carries, `labels` its labels and `protect` the
    protect list in force. By its name, by its compose project label or by its labelled path. When
    nothing covers it and a labelled path is not an absolute path, the answer is ('unread', what was
    said): such a path cannot be placed, so the object is not known to be free, and the caller writes
    nothing for it."""
    for entry in protect:
        if engine not in entry.get('engines', ()):
            continue
        if entry['type'] == PROTECT_NAME[kind] and any(fnmatch.fnmatchcase(name, entry['value']) for name in names):
            return entry['type'] + ':' + entry['value'], 'name'
        if entry['type'] == 'compose_project' and labels.get(COMPOSE_PROJECT) == entry['value']:
            return entry['type'] + ':' + entry['value'], 'compose_project'
    unplaced = None
    for how, path in labelled_paths(labels):
        if not path.startswith('/'):
            unplaced = unplaced or 'a labelled path (%s) is not absolute: %s' % (how, path[:200])
            continue
        # A protected path is protected on every engine, as it is for a mount.
        for entry in protect:
            if entry['type'] != 'path':
                continue
            for mine in {os.path.normpath(path), os.path.realpath(path)}:
                for theirs in {os.path.normpath(entry['value']), os.path.realpath(entry['value'])}:
                    if mine == theirs or _beneath(mine, theirs) or _beneath(theirs, mine):
                        return 'path:' + entry['value'], how
    if unplaced is not None:
        return 'unread', unplaced
    return None, None


def owner_of(locator, runs):
    """Whose the object at `locator` is, by its labels alone: (space label, owner, rule), or
    (None, None, why) when no rule gives it an owner. `runs` is {space label: owner}. Nothing but the
    object's own two labels is read: how many runs are live decides nothing."""
    label, compose = locator.get('run_label'), locator.get('compose_project')
    by_label = label if label is not None and label in runs else None
    by_compose = None
    if compose is not None:
        named = sorted(known for known in runs if compose_project(known) == compose)
        by_compose = named[0] if len(named) == 1 else None
    if label is not None and by_label is None:
        return None, None, 'unknown_run'
    if by_label is not None and by_compose is not None and by_label != by_compose:
        return None, None, 'two_runs'
    if by_label is not None:
        return by_label, runs[by_label], 'run_label'
    if by_compose is not None:
        return by_compose, runs[by_compose], 'compose_project'
    return None, None, 'no_label'


def related_protection(engine, kind, shown, protect, run):
    """Read protection inherited by an image or network from a container, now.

    The image is compared by immutable Id, never by a tag that may have moved. Every
    container is read, stopped ones included. An unread relationship refuses the
    answer. Protection travels from a container to its image and networks only.
    Returns (entry, reason), (None, None), or ('unread', reason).
    """
    if kind not in ('image', 'network'):
        return None, None

    def inspect(one_kind, name):
        code, out = run(['docker', '--context', str(engine), one_kind, 'inspect', str(name)])
        if code != 0:
            return None
        try:
            records = json.loads(out)
        except (ValueError, TypeError):
            return None
        return records[0] if (isinstance(records, list) and len(records) == 1
                              and isinstance(records[0], dict)) else None

    identity = _text(shown.get('Id'))
    if identity is None:
        return 'unread', 'the related object has no identity'
    code, out = run(['docker', '--context', str(engine)] + list(LISTED['container']))
    if code != 0:
        return 'unread', 'the containers could not be listed'
    unread = None
    for name in sorted(set(str(out).split())):
        container = inspect('container', name)
        if container is None:
            unread = 'a container could not be read: ' + name
            continue
        if kind == 'image':
            source = _text(container.get('Image'))
            if source is None:
                unread = 'a container has no image identity: ' + name
                continue
            attached = source == identity
        else:
            settings = container.get('NetworkSettings')
            networks = settings.get('Networks') if isinstance(settings, dict) else None
            if not isinstance(networks, dict) or not all(isinstance(row, dict) for row in networks.values()):
                unread = 'a container has no readable networks: ' + name
                continue
            attached = any(row.get('NetworkID') == identity or network == shown.get('Name')
                           for network, row in networks.items())
        if not attached:
            continue
        locator = locator_of(engine, 'container', container)
        if locator is None:
            unread = 'a container has no name: ' + name
            continue
        entry, by = covered(engine, 'container', [locator['name']], labels_of('container', container), protect)
        if entry in (None, 'unread'):
            mounted, mount = mount_protected(engine, container, protect, lambda value: inspect('volume', value))
            if mounted not in (None, 'unread'):
                entry, by = mounted, 'mount'
            elif entry == 'unread' or mounted == 'unread':
                unread = by if entry == 'unread' else mount
                continue
        if entry is not None:
            return entry, 'protected_container:' + locator['name']
    return ('unread', unread) if unread is not None else (None, None)


class Adapter:
    """The Docker adapter on one ledger.

    `engines` are the contexts read; the default is every context the installation names. `run(argv,
    cwd)` runs the engine's client and returns (exit code, output). `runs()` returns {space label:
    owner} for runs the ledger does not show yet; they are added to `known_runs`. `spawn(engine,
    since)` starts the client that prints a context's events from the engine time `since` on and
    returns its process, whose stdout is the pipe. `pool` names the pool a Docker item counts against
    on an engine that has no image pool. `tell(engine, why)` is called for each context that goes down.
    `reconcile` is the reconciler (control_space_reconcile): with it, an object with no run label
    inside a recorded worktree is proposed to that worktree or adopted by it; without it, it is a
    report with no proposed owner.

    observations holds one entry for each object recorded or reported, each event handled and each
    snapshot and subscription, in order."""

    def __init__(self, ledger, engines=None, run=None, runs=None, spawn=None, pool=None, tell=None,
                 reconcile=None):
        self.ledger = ledger
        self.engines = list(ledger.engines if engines is None else engines)
        self.run, self.spawn, self.more_runs, self.pool = run or _run, spawn or _spawn, runs, pool
        self.tell, self.reconcile = tell, reconcile
        self.protected = {}  # (engine, kind, name): what the protect list covers, as it was last seen
        self.streams = {}  # engine: {process, fd, buffer, bytes}
        self.down = {}  # engine: why it has no subscription
        self.barren = {}  # engine: how many streams in a row ended without one byte
        self.observations = []

    # What is known.

    def runs(self):
        """{space label: owner}: the runs the ledger knows and the ones the caller names."""
        found = dict(known_runs(self.ledger))
        if self.more_runs is not None:
            for label, owner in dict(self.more_runs()).items():
                if isinstance(label, str) and label and isinstance(owner, dict):
                    found.setdefault(label, owner)
        return found

    def _note(self, what, **facts):
        entry = dict(facts, schema=SCHEMA, what=what)
        self.observations.append(entry)
        return entry

    def _client(self, engine, *argv):
        return self.run(['docker', '--context', str(engine)] + [str(word) for word in argv])

    def _down(self, engine, said):
        """The context has no subscription from now on, and it is said: in the observations, to the
        caller's `tell`, and in every answer that names the context."""
        self.down[engine] = said
        self._note('down', engine=engine, said=said)
        if self.tell is not None:
            try:
                self.tell(engine, said)
            except Exception:  # noqa: BLE001 - a listener that fails never ends the adapter
                pass

    def unread(self):
        """{engine: why}: every context that is not read now. Its objects are not being recorded."""
        return dict(self.down)

    def engine_time(self, engine):
        """The engine's own time, as its client prints it, or None when it could not be read."""
        code, out = self._client(engine, *ENGINE_TIME)
        words = str(out).split() if code == 0 else []
        return words[0] if len(words) == 1 and words[0][:1].isdigit() else None

    def protected_objects(self):
        """Every object the protect list covered when it was last seen: [{engine, kind, name, id,
        entry, by}], in order. A protected object is here and has no record."""
        return [dict(self.protected[key]) for key in sorted(self.protected)]

    def _listed(self, engine, kind, name, identity, entry, by):
        self.protected[(engine, kind, name)] = {'engine': engine, 'kind': kind, 'name': name, 'id': identity,
                                                'entry': entry, 'by': by}

    def images(self, engine):
        """Read the images of one context and list those the protect list covers. Nothing is written
        for any image. Returns {engine, read, said, images, protected}; with read False nothing was
        listed."""
        answer = {'engine': engine, 'read': False, 'said': None, 'images': 0, 'protected': []}
        code, out = self._client(engine, *IMAGES)
        if code != 0:
            answer['said'] = str(out)[:300] or 'the client gave no answer'
            return answer
        names = sorted(set(str(out).split()))
        records, said = self._records(engine, 'image', names) if names else ([], None)
        if records is None:
            answer['said'] = said
            return answer
        for shown in records:
            carried = image_names(shown)
            identity = _text(shown.get('Id'))
            name = carried[0] if carried else identity
            if name is None:
                continue
            entry, by = covered(engine, 'image', carried, labels_of('image', shown), list(self.ledger.protect or ()))
            if entry is None:
                entry, by = related_protection(engine, 'image', shown, list(self.ledger.protect or ()), self.run)
            unplaced = entry == 'unread'
            if unplaced:
                # Not known to be free and not known to be covered: said, and the listing is left as it was.
                self._note('refused', refusal='labels_unread: ' + str(by), engine=engine, kind='image',
                           name=name, id=identity)
                continue
            if entry is None:
                # Two images of one repository are listed under one name: an image nothing covers
                # takes away only its own listing, never the listing of another image.
                if (self.protected.get((engine, 'image', name)) or {}).get('id') == identity:
                    self.protected.pop((engine, 'image', name), None)
                continue
            self._listed(engine, 'image', name, identity, entry, by)
            answer['protected'].append(name)
            self._note('protected', refusal='space_protected:' + entry, by=by, engine=engine, kind='image',
                       name=name, id=identity)
        answer.update(read=True, images=len(records))
        return answer

    def _image(self, engine, name):
        """Read one named image and its protect status, without writing a record."""
        if engine not in self.engines or not _text(name) or name.startswith('-'):
            return None, 'refused'
        records, said = self._records(engine, 'image', [name])
        if records is None:
            self._note('unread', engine=engine, kind='image', name=name, said=said)
            return None, 'unread'
        shown = records[0]
        config = shown.get('Config')
        labels = config.get('Labels') if isinstance(config, dict) else None
        readable = (isinstance(config, dict) and 'Labels' in config
                    and (labels is None or (isinstance(labels, dict)
                         and all(isinstance(key, str) and isinstance(value, str)
                                 for key, value in labels.items())))
                    and all(field in shown and (shown[field] is None or
                            (isinstance(shown[field], list) and all(_text(name) for name in shown[field])))
                            for field in ('RepoTags', 'RepoDigests')))
        if not readable:
            self._note('unread', engine=engine, kind='image', name=name,
                       said='the image names or labels could not be read')
            return None, 'unread'
        if not _text(shown.get('Id')):
            return None, 'refused'
        entry, by = covered(engine, 'image', image_names(shown), labels_of('image', shown),
                            list(self.ledger.protect or ()))
        if entry is not None:
            if entry != 'unread':
                self._listed(engine, 'image', name, shown['Id'], entry, by)
            self._note('refused' if entry == 'unread' else 'protected', engine=engine,
                       kind='image', name=name, refusal=entry, by=by)
            return None, 'refused' if entry == 'unread' else 'protected'
        return shown, None

    def built(self, engine, tag, label, image_id):
        """A trusted creator completed a build of this exact tag and image for a known run.

        Never infer this from an image's labels or from a tag event. Another ticket's tags on the
        same image get no item. Replayed completions cannot change an item's owner or revive Keep.
        """
        shown, refusal = self._image(engine, tag)
        if refusal:
            return refusal
        if (tag not in (shown.get('RepoTags') or ()) or tag == shown['Id']
                or shown['Id'] != image_id):
            return 'refused'
        runs, said = self._known(engine)
        owner = runs.get(label) if runs is not None else None
        if not owner or not owner.get('ticket'):
            self._note('refused', engine=engine, kind='image', name=tag, refusal=said or 'unknown_ticket')
            return 'refused'
        labels = labels_of('image', shown)
        if labels.get(RUN_LABEL) not in (None, label):
            return 'refused'
        if self._held(engine, 'image_tag', name=shown['Id']) is not None:
            return 'held'  # an image recorded as pulled stays kept
        locator = {'engine': engine, 'name': tag, 'id': shown['Id']}
        if labels.get(RUN_LABEL):
            locator['run_label'] = labels[RUN_LABEL]
        if labels.get(COMPOSE_PROJECT):
            locator['compose_project'] = labels[COMPOSE_PROJECT]
        held = self._held(engine, 'image_tag', name=tag)
        if held is not None:
            prior = held[1]
            return ('matched' if prior.get('owner') == owner and prior.get('locator') == locator
                    else 'held')
        wrote = self.ledger.adopt('image_tag', locator, owner, 'built_tag', pool=self.pool)
        self._note('adopted' if wrote.get('ok') else 'refused', engine=engine, kind='image_tag',
                   name=tag, id=shown['Id'], run=label, item=wrote.get('item'), refusal=wrote.get('reason'))
        return 'adopted' if wrote.get('ok') else 'refused'

    def pulled(self, engine, name):
        """A pull's image is a durable ownerless report, once per image identity per engine.

        Kept is a report disposition, not an owned lifecycle item. Labels inherited from the image
        cannot assign it to the pulling run. Replays, other tags and adapter restarts reuse it.
        """
        shown, refusal = self._image(engine, name)
        if refusal:
            return refusal
        identity = shown['Id']
        if self._held(engine, 'image_tag', name=identity) is not None:
            return 'matched'
        locator = {'engine': engine, 'name': identity, 'id': identity}
        found = {'why': 'pulled_image', 'disposition': 'kept', 'engine': engine, 'id': identity}
        wrote = self.ledger.report('image_tag', locator, found, pool=self.pool)
        self._note('kept' if wrote.get('ok') else 'refused', engine=engine, kind='image',
                   name=name, id=identity, item=wrote.get('item'), refusal=wrote.get('reason'))
        return 'kept' if wrote.get('ok') else 'refused'

    def _mounts(self, engine, shown):
        """mount_protected for a container of `engine`, against the ledger's protect list."""
        def volume(name):
            records, _said_ = self._records(engine, 'volume', [name])
            return records[0] if records else None
        return mount_protected(engine, shown, list(self.ledger.protect or ()), volume)

    def _records(self, engine, kind, names):
        """The inspect records of `names`, or (None, what was said)."""
        code, out = self._client(engine, kind, 'inspect', *names)
        if code != 0:
            return None, str(out)[:300] or 'the client gave no answer'
        try:
            records = json.loads(out)
        except ValueError:
            return None, 'the inspect records are not JSON'
        if (not isinstance(records, list) or len(records) != len(names)
                or not all(isinstance(record, dict) for record in records)):
            return None, 'the engine did not show one record for each object listed'
        return records, None

    def _read(self, engine):
        """Every container, network and volume of one context: ({kind: [inspect record]}, None), or
        (None, what was said) when any of it could not be read. An object removed between the list
        and the inspect fails the inspect of all, so each kind is read twice at most."""
        found = {}
        for kind in KINDS:
            said = None
            for _attempt in (1, 2):
                code, out = self._client(engine, *LISTED[kind])
                if code != 0:
                    said = str(out)[:300] or 'the client gave no answer'
                    continue
                names = str(out).split()
                records, said = (self._records(engine, kind, names) if names else ([], None))
                if records is not None:
                    found[kind] = records
                    break
            if kind not in found:
                return None, '%s: %s' % (kind, said)
        return found, None

    def _held(self, engine, kind, name=None, identity=None):
        """The record that is neither removed nor gone at this engine, kind and name, or with this
        engine Id: (identity, record) or None."""
        for item, record in sorted(self.ledger.items().items()):
            locator = record.get('locator') or {}
            if (record.get('kind') == kind and record.get('state') not in ENDED and locator.get('engine') == engine
                    and ((name is not None and locator.get('name') == name)
                         or (identity is not None and locator.get('id') == identity))):
                return item, record
        return None

    # Recording one object.

    def _record(self, engine, kind, shown, runs):
        """Record the object the engine showed: an item when its labels name a known run; with the
        reconciler, a proposal to the recorded worktree it is inside, or an item of that worktree in
        act mode; a report otherwise. Returns what was done: matched, adopted, proposed, reported,
        protected, held or refused. An object the protect list covers, and a container that mounts
        what is protected, is listed as protected, and nothing is written for it."""
        locator = locator_of(engine, kind, shown)
        if locator is None:
            self._note('unnamed', engine=engine, kind=kind, id=_text(shown.get('Id')))
            return 'refused'
        if kind == 'network' and locator['name'] in ENGINE_NETWORKS:
            return 'matched'
        field = IDENTITY[kind][0]
        facts = {'engine': engine, 'kind': kind, 'name': locator['name'], 'id': locator.get('id'),
                 'created_at': locator.get('created_at')}
        if kind == 'container':
            entry, mount = self._mounts(engine, shown)
            if entry == 'unread':
                self._note('refused', refusal='mounts_unread: ' + str(mount), **facts)
                return 'refused'
            if entry is not None:
                # It mounts what is protected: neither an item nor a report, whatever it carries.
                self._listed(engine, kind, locator['name'], locator.get('id'), entry, 'mount')
                held = self._held(engine, kind, name=locator['name'])
                if held is not None and held[1].get('owner') is None:
                    self.ledger.gone(held[0])
                self._note('protected', refusal='space_protected:' + entry, mount=mount, **facts)
                return 'protected'
        entry, by = covered(engine, kind, [locator['name']], labels_of(kind, shown), list(self.ledger.protect or ()))
        if entry is None and kind == 'network':
            entry, by = related_protection(engine, kind, shown, list(self.ledger.protect or ()), self.run)
        if entry == 'unread':
            # A labelled path that cannot be placed: as with mounts that cannot be read, nothing is
            # written for the object, and it gets no owner and no proposal.
            self._note('refused', refusal='labels_unread: ' + str(by), **facts)
            return 'refused'
        held = self._held(engine, kind, name=locator['name'])
        if entry is not None:
            # The protect list comes first: no item, no report and no proposed owner, whatever it carries.
            self._listed(engine, kind, locator['name'], locator.get('id'), entry, by)
            if held is not None and held[1].get('owner') is None:
                self.ledger.gone(held[0])  # a report from before it was covered: withdrawn, nothing removed
            self._note('protected', refusal='space_protected:' + entry, by=by, **facts)
            return 'protected'
        self.protected.pop((engine, kind, locator['name']), None)
        if held is not None:
            item, record = held
            same = field in locator and (record.get('locator') or {}).get(field) == locator[field]
            if same and record.get('owner') is not None:
                return 'matched'
            if not same and field in locator and (record.get('locator') or {}).get(field) is not None:
                # Another object under the recorded name: the recorded one is not there any more.
                gone = self.ledger.gone(item)
                self._note('made_again', item=item, ok=gone.get('ok'), refusal=gone.get('reason'), **facts)
                if not gone.get('ok'):
                    return 'held'
                held = None
            elif not same and record.get('owner') is not None:
                # An item somebody recorded without the identity: it is theirs, and it stays as it is.
                return 'held'
        label, owner, rule = owner_of(locator, runs)
        if owner is not None and field not in locator:
            label, owner, rule = None, None, 'no_identity'
        worktree, how, path = None, None, None
        if owner is None and rule == 'no_label' and self.reconcile is not None:
            # No run label: the one worktree its compose labels and bind sources all lead inside, if any.
            worktree, how, path = self.reconcile.worktree_inside(self.ledger, placed(kind, shown))
            if worktree is not None and field not in locator:
                worktree, how, rule = None, None, 'no_identity'
        found = {'why': rule, 'engine': engine, 'id': locator.get('id'), 'name': locator['name'],
                 'created_at': locator.get('created_at'), 'run_label': locator.get('run_label'),
                 'compose_project': locator.get('compose_project'),
                 'live_runs': sorted(runs)[:NAMED], 'more_runs': max(0, len(runs) - NAMED)}
        if worktree is None and how is not None:
            # why its paths gave no worktree: outside, conflict (a split) or path_unread
            found['not_placed'] = how
        before = (held[1].get('report') or {}).get('found', {}) if held is not None else {}
        if owner is not None:
            wrote = self.ledger.adopt(kind, locator, owner, rule, pool=self.pool)
            done = 'adopted'
        elif worktree is not None:
            rule = INSIDE_WORKTREE
            proposed = ((self.ledger.item(worktree) or {}).get('owner') or {})
            if (before.get('why') == rule and before.get('worktree') == worktree and before.get('path') == path
                    and not self.ledger.acts(proposed.get('scope'))):
                return 'matched'  # proposed to this worktree before, and its project still reports
            wrote = self.reconcile.adopt_inside_worktree(
                self.ledger, kind, locator, worktree, dict(found, why=rule, placed_by=how, path=path),
                pool=self.pool)
            done = 'adopted' if wrote.get('adopted') else 'proposed'
            facts = dict(facts, worktree=worktree, placed_by=how, path=path, proposed_owner=proposed)
        else:
            if before.get('why') == rule:
                return 'matched'  # the same object, reported before, and still nobody's
            wrote = self.ledger.report(kind, locator, found, pool=self.pool)
            done = 'reported'
        if not wrote.get('ok'):
            reason = str(wrote.get('reason'))
            done = 'protected' if reason.startswith('space_protected') else 'refused'
            self._note(done, refusal=reason, **facts)
            return done
        self._note(done, item=wrote.get('item'), run=label, rule=rule, **facts)
        return done

    def _known(self, engine):
        try:
            return self.runs(), None
        except Exception as error:  # noqa: BLE001 - runs nobody could read: nothing is recorded
            return None, _said(error)

    def snapshot(self, engine):
        """Read one context whole and record what it holds. Returns {engine, read, said, objects,
        counts}; with read False nothing was written."""
        answer = {'engine': engine, 'read': False, 'said': None, 'objects': 0, 'counts': {}}
        found, said = self._read(engine)
        runs = None
        if found is not None:
            runs, said = self._known(engine)
        if found is None or runs is None:
            answer['said'] = said
            self._note('snapshot', engine=engine, read=False, said=said)
            return answer
        for kind in KINDS:
            for shown in found[kind]:
                done = self._record(engine, kind, shown, runs)
                answer['counts'][done] = answer['counts'].get(done, 0) + 1
                answer['objects'] += 1
        answer['read'] = True
        self._note('snapshot', engine=engine, read=True, objects=answer['objects'], counts=dict(answer['counts']))
        return answer

    def observe(self, engine, kind, name):
        """Ask the engine for one object, by its name or its Id, and record it as the snapshot would;
        mark its record gone when the engine answers that it holds no such object. Returns what was
        done: one of _record's answers, gone, absent (no such object and no record) or unread."""
        code, out = self._client(engine, kind, 'inspect', name)
        if code == 0:
            try:
                records = json.loads(out)
            except ValueError:
                records = None
            if not (isinstance(records, list) and len(records) == 1 and isinstance(records[0], dict)):
                self._note('unread', engine=engine, kind=kind, name=name, said='the inspect record is not one record')
                return 'unread'
            runs, said = self._known(engine)
            if runs is None:
                self._note('unread', engine=engine, kind=kind, name=name, said=said)
                return 'unread'
            return self._record(engine, kind, records[0], runs)
        if not absent(kind, code, out):
            self._note('unread', engine=engine, kind=kind, name=name, said=str(out)[:300])
            return 'unread'
        held = self._held(engine, kind, name=name, identity=name)
        if held is None:
            return 'absent'
        gone = self.ledger.gone(held[0])
        self._note('gone', engine=engine, kind=kind, name=name, item=held[0], ok=gone.get('ok'),
                   refusal=gone.get('reason'))
        return 'gone' if gone.get('ok') else 'held'

    # The event stream.

    def subscribe(self, engine, since=None):
        """Start the client that prints the events of `engine` from the engine time `since` on, and
        hold its output pipe, non-blocking. Returns the descriptor, or None when the client could not
        be started (the context is then down). start() and the end of a stream give the time they
        read before their snapshot."""
        self.unsubscribe(engine)
        try:
            process = self.spawn(engine, since)
            fd = process.stdout.fileno()
            os.set_blocking(fd, False)
        except Exception as error:  # noqa: BLE001 - a client that does not start is a context that is down
            self._down(engine, _said(error))
            return None
        self.streams[engine] = {'process': process, 'fd': fd, 'buffer': b'', 'bytes': 0}
        self.down.pop(engine, None)
        self._note('subscribe', engine=engine, since=since)
        return fd

    def unsubscribe(self, engine):
        """End the subscription of `engine`, when it has one: the pipe is closed and the client reaped."""
        stream = self.streams.pop(engine, None)
        if stream is None:
            return
        process = stream['process']
        try:
            process.stdout.close()
        except Exception:  # noqa: BLE001 - a pipe that is closed already
            pass
        try:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=5)
        except Exception:  # noqa: BLE001 - a client that does not end is left to the kernel
            pass

    def start(self):
        """For each context that has no subscription: the engine's time, the snapshot, then the
        subscription since that time. Returns {engine: the snapshot's answer}; the answer of a
        context that is down names why under `down`."""
        done = {}
        for engine in self.engines:
            if engine in self.streams:
                continue
            self.barren[engine] = 0
            since = self.engine_time(engine)
            if since is None:
                # No start for the subscription: what is made meanwhile would be missed.
                self._down(engine, 'the time of the engine could not be read')
                done[engine] = {'engine': engine, 'read': False, 'said': self.down[engine], 'objects': 0,
                                'counts': {}, 'down': self.down[engine]}
                continue
            done[engine] = self.snapshot(engine)
            self.subscribe(engine, since)
            if engine in self.down:
                done[engine]['down'] = self.down[engine]
        return done

    def stop(self):
        for engine in list(self.streams):
            self.unsubscribe(engine)

    def pipes(self):
        """{descriptor: engine}: the event pipe of every context that has a subscription."""
        return {stream['fd']: engine for engine, stream in self.streams.items()}

    def readable(self, fd):
        """The poll set found the pipe `fd` readable. Everything it holds now is taken; each whole
        line is one event. At end of file a new snapshot is taken, and then a new subscription is
        made. Returns what was handled; it never raises."""
        engine = self.pipes().get(fd)
        if engine is None:
            return {'engine': None, 'events': 0, 'ended': False}
        try:
            return self._readable(engine)
        except Exception as error:  # noqa: BLE001 - a stream that cannot be read is ended, never read in a loop
            self.unsubscribe(engine)
            self._down(engine, _said(error))
            return {'engine': engine, 'events': 0, 'ended': True, 'said': self.down[engine],
                    'down': self.down[engine]}

    def _readable(self, engine):
        stream = self.streams[engine]
        ended = False
        while True:
            try:
                chunk = os.read(stream['fd'], CHUNK)
            except BlockingIOError:
                break
            except InterruptedError:
                continue
            if not chunk:
                ended = True
                break
            stream['bytes'] += len(chunk)
            stream['buffer'] += chunk
        lines = stream['buffer'].split(b'\n')
        stream['buffer'] = lines.pop()
        handled, unreadable = 0, 0
        for line in lines:
            if not line.strip():
                continue
            if self.event(engine, line) is None:
                unreadable += 1
            else:
                handled += 1
        if unreadable and not ended:
            self.snapshot(engine)  # something happened that was not seen: the context is read again
        if ended:
            self._ended(engine, stream)
        answer = {'engine': engine, 'events': handled, 'unreadable': unreadable, 'ended': ended}
        if engine in self.down:
            answer['down'] = self.down[engine]  # said to the caller: the context is not read any more
        return answer

    def _ended(self, engine, stream):
        """End of file on a context's pipe: the engine's time, a new snapshot, and then a new
        subscription since that time."""
        self.barren[engine] = 0 if stream['bytes'] else self.barren.get(engine, 0) + 1
        self.unsubscribe(engine)
        self._note('end_of_file', engine=engine, bytes=stream['bytes'])
        since = self.engine_time(engine)
        if since is None:
            self._down(engine, 'the time of the engine could not be read after the end of the stream')
            return
        taken = self.snapshot(engine)
        if not taken['read']:
            self._down(engine, 'the snapshot after the end of the stream could not be read: %s' % taken['said'])
        elif self.barren[engine] >= BARREN:
            self._down(engine, 'the event stream ended %d times in a row without one byte' % self.barren[engine])
        else:
            self.subscribe(engine, since)

    def event(self, engine, line):
        """Handle one line of a context's event stream. Returns what was done with it, or None when
        the line is not an event that could be read."""
        try:
            event = json.loads(line.decode('utf-8', 'replace') if isinstance(line, bytes) else line)
        except ValueError:
            event = None
        actor = event.get('Actor') if isinstance(event, dict) else None
        kind, action = (event.get('Type'), event.get('Action')) if isinstance(event, dict) else (None, None)
        name = _text(actor.get('ID')) if isinstance(actor, dict) else None
        if kind == 'image' and name is not None and isinstance(action, str):
            # Pull events carry no trustworthy caller identity. A tag event is not proof of a build.
            return self.pulled(engine, name) if action == 'pull' else 'ignored'
        if kind not in KINDS or not isinstance(action, str) or name is None:
            if isinstance(event, dict) and isinstance(kind, str) and kind not in KINDS and isinstance(action, str):
                return 'ignored'  # an event of a type this adapter did not ask for
            self._note('unreadable_event', engine=engine, line=str(line)[:200])
            return None
        if action not in ACTIONS:
            return 'ignored'
        done = self.observe(engine, kind, name)
        self._note('event', engine=engine, kind=kind, action=action, name=name, done=done)
        return done
