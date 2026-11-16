#!/usr/bin/env python3
"""The runner that prepares a dispatch and the trusted receiver that launches it (PLAN-0019 W24,
VELDO-0039, R31, R33).

THE RUNNER (Runner.submit, in the scheduler's process). For one admitted unit at one station it
takes the station decision from VELDO-0052's shared eligibility Gate for the holder, reads that no
dispatch holds the unit and station, makes the dispatch identity, reserves that identity's
VELDO-0036 worker slot, resolves the source commit and tree from a real Git repository, and then
PREPARES: control_dispatch commits the COMPLETE contract. Only after that commit is the receiver
invoked. A preparation the authority refuses retires the slot it reserved (nothing was spawned).

THE RECEIVER (`python3 control_launch.py <config>`, a separate trusted process the runner owns; its
config, journal key and this executable are installed outside worker clones, and a worker can select
none of them). It is handed the prepared contract, rechecks the station decision with the
preparation's decision as its ticket (admission and claim are rechecked at the accepting boundary,
not only at selection) and records its ACCEPTANCE, its durable launch record, under the original
dispatch identity. The acceptance transition itself requires the prepared record and the handed
contract's digest to match it, so the receiver launches only what the authority committed. Then,
and only then, it spawns the worker with the adapter's configured argv and exactly the recorded
configuration (never reduced), in the owner's environment plus the adapter's configured one, reads
the spawned process's OS identity and records it (`running`). It reaps the worker, killing its
session at the contract deadline, and records the termination under the same dispatch and process.
A worker's output is hashed and counted, never believed.

LAUNCH RESULTS, always read from the RECORD, never from a reply alone. accepted: the record says
running, with the OS identity stored. refused: nothing ran, by name (a receiver check failed before
acceptance, or the spawn itself failed). unknown: the receiver accepted and no conclusive launch
evidence followed (its answer was lost: it ended or overran its bound). When the receiver ends
without recording, the runner records it: a record still prepared is refused (the receiver spawns
only after its acceptance commits, and it has ended), an accepted one is unknown. An unknown dispatch
keeps its unit and station and is never launched again; a receiver asked to launch a dispatch that is
not prepared refuses and records nothing.

PROCESS IDENTITY. Linux: /proc/<pid>/stat start time (clock ticks since boot) with the boot id.
macOS: `ps -o lstart=` with kern.boottime. A local adapter's identity is read from the spawned pid.
An adapter launched through a transport to another host (the Mac, over SSH, since the authority
and its store stay on this Linux host) sets `identity: reported` and runs the trusted wrapper
(`control_launch.py exec <argv>`) there: the wrapper's first output line names its own identity
before it becomes the engine by exec, so the recorded pid and start time are the engine's. The
receiver, on the authority's host, records it.

CONTAINMENT (VELDO-0040, R43, R44). A local adapter's worker is contained by the host's worker
profile (the config's `profile`, control_containment.py): the receiver qualifies it before its
acceptance, refusing an absent, invalid or unenforceable profile by name, and the one spawn starts the
trusted wrapper (`control_launch.py exec --contained ...`) inside the dispatch's own systemd scope with
every declared cap installed, checks the wrapper is in that group with those controls, and only then
releases it to exec the engine. The reap sleeps until an OS notification (output, the worker's pidfd,
the group's populated event, a stop request from the runner on the receiver's stdin, or the next stop
timer); the worker's exit ends the dispatch, anything left in its group is stopped, and the exit is
recorded only once the group is empty. A group that cannot be emptied is recorded unknown
(`containment_not_empty`), holding its unit. The runner returns the worker slot only on its own kernel
observation that the process is gone and the group empty. Another host's worker (identity reported)
is contained by that host's profile (VELDO-0124).

HEARTBEAT AND RETIREMENT (VELDO-0041, R44). A contained worker's wrapper starts its own heartbeat
(control_heartbeat.py) just before it becomes the engine, on a channel the receiver passes it, so
liveness never waits for a model call. The receiver sleeps on that channel too: each heartbeat renews
the claim the contract binds, and a worker with no heartbeat for the profile's window has uncertain
liveness and is stopped (`heartbeat_missing`). Every stop escalates on the monotonic clock and the
supervision the receiver reports carries its steps on both clocks, its graces and the heartbeat's
account. The runner returns a worker slot through control_retirement.py, which keeps each open
obligation (termination, the outcome, the clone files and the accounting) until it is completed and
releases the slot once. A refused retirement stays pending and is retried when an obligation it waits
on is completed: at once when the retirement service observes the completion (its own clone teardown,
a final accounting report the reservation service accepts), and on the runner's sweep before each
preparation and after each wait, so none is stranded.

SUBSCRIPTION LOGIN AND USAGE (VELDO-0062). An adapter that declares an `engine` (`claude_code` or
`codex`) runs a logged-in subscription CLI. Before acceptance the receiver reads the account the
accepted contract records (its reservation's account) from the store's account records
(control_accounts): an unregistered, paused or disabled account, one of another provider, or one with
no profile on this host is refused by name, as is an adapter whose configured environment names a
login (control_accounts.refused). The engine's environment is the inherited one with every provider's
profile variable and every other login variable removed (by family, and every name the installed
binaries' lists make a login or a setting of the owner's shell, control_accounts.strips), then the
adapter's configured one as configured, and that account's own profile set (CLAUDE_CONFIG_DIR or
CODEX_HOME), never a profile the caller's environment names. After
acceptance, and before anything is spawned, the invocation (initial, retry or follow-on,
control_reservation_runtime.boundary) is checked and reserved against every applicable cap and the
account's reported rate-limit windows through VELDO-0036's InvocationGuard, bounded by the contract
deadline; a refusal is recorded by name and launches nothing. While the worker runs, the usage and
rate-limit windows the CLI's own stream reports (control_engine_claude, control_engine_codex) are
reported as they arrive, their raw lines kept as receipts in a private file and their digests in the
ledger; a cap reached stops the worker. At its end one final report settles the invocation: its count,
the wall time it took and the CLI's conclusive totals, or, when the CLI reported none, the token and
message units stay unknown and their reservation is retained. Timeout, cancellation or a missing
report never release it.

THE ENGINE PROTOCOL (VELDO-0060, VELDO-0061). Every subscription engine module (ENGINES) implements
ENGINE_PROTOCOL with the same signatures, and the receiver drives each through the one path here:
- `bind(adapter, state_root)`, before acceptance: the pinned executable the adapter runs, checked
  against the engine's installed qualification record, or `Refused` by name, so nothing is accepted,
  reserved or spawned. Claude Code's adapter names a qualified version whose pinned copy lies under the
  factory state root (the config's `state_root`); Codex's names the vendor binary inside its package.
- `command(binding, adapter)`: the engine argv. Claude Code's is the adapter's prefix (its clone
  entrance, or a transport's trusted wrapper) followed by the pinned path and the qualified flags;
  Codex's is the adapter's own argv, exactly. The receiver then checks, for every engine, that the argv
  binds what runs (`pinned_argv_problem`): what the trusted wrapper execs (a local adapter's whole argv, a
  reported adapter's argv after its transport's `control_launch.py exec`) is the pinned path itself, or
  the clone entrance (`<python> -B control_clone.py enter <clones> --`, for a local adapter the installed
  one beside this receiver, run by this receiver's own Python) and then the pinned path, followed by its
  qualified flags; anything else, a shell or a package manager's link first among them, is refused by
  name. The engine's environment names the pinned path and digest (VELDO_ENGINE_PATH,
  VELDO_ENGINE_SHA256), and whichever trusted program execs the engine (this wrapper, or the clone
  entrance) re-hashes the file immediately before the exec and refuses a changed one (exit 70, the
  engine never runs). The wrapper compares resolved paths, and passes the two names on to the clone
  entrance only: the engine inherits neither.
- `environment(binding)`: the settings the engine always runs with (DISABLE_AUTOUPDATER), set last in
  its environment; an adapter configuring one of them otherwise is refused by name.
- `Terminal()`: the terminal output decoder, fed what the meter is fed. At the end its document (one
  shape for every engine: schema, engine, verdict, complete, then the engine's own decoded fields,
  bound to the dispatch, invocation, account and pinned executable) is kept in a private file (0600 in
  a 0700 directory, beside the store unless the config names `artifacts`), and its report {path, digest,
  verdict, complete} is sent to the runner before the end. The invocation and the worker slot are
  `completed` only when the document is complete, so a zero exit without a terminal record is never a
  completion: the exit record binds the report's verdict, completeness and digest, and the runner's slot
  and the build and review floor read completion from that record through control_dispatch.completed.
- `Meter` (VELDO-0062), with PROVIDER, CREDENTIALS, SETTINGS and REGISTRATION (the lifecycle operations).
  Its methods are the same for every engine: `feed`, `close`, `final`, `session` and (VELDO-0160)
  `limit()`, the account limit the engine's own stream reported, or None, which settle classifies.
An engine module that does not implement the protocol is refused by name before acceptance.

THE EVERYTHING-OFF BASELINE, THE PAID-API GUARD AND THE ENVIRONMENT STRIP (VELDO-0155, VELDO-0156). The
protocol's `baseline(binding, run, environment, servers=())` is what every engine run adds right after its qualified
flags (`baseline_at`, so an adapter's own trailing arguments stay last): each engine's everything-off
options and its generated configuration, whose files the receiver writes 0600 into the run's own
configuration directory, `<runs>/<digest of the dispatch>/config` (0700, fresh, outside every clone, under
the config's `runs`, else the state root's `runs`, else beside the store), removed with the run once its
engine has ended; `servers` are the dispatch's selected catalog servers, which it adds to that
configuration with their credentials (VELDO-0158). A version or binary whose qualification record does not list the module's baseline is
refused by name before acceptance. `profile_problem(binding, environment, cwd)` and then
`login_problem(binding, environment, cwd)` are checked before acceptance in the engine's own login
environment and working directory (`cwd`: the clone's work tree the clone entrance changes into, this
receiver's own for an engine it execs directly, None for another host's): an account profile holding an
item no switch of the baseline keeps out (Codex's own AGENTS.md) is refused by name, and so is a login
that is not a subscription (`paid_api:...`), nothing accepted, reserved or spawned. For an adapter factory setup
wrote (`account_login` true, VELDO-0185), the account's own login as its engine reports it (`account_login`:
Claude Code's `auth status`, Codex's `login status`) is checked first, and an account not logged in to its
subscription is refused by name (`missing_authority:account_login:<account>`). The protocol's `Guard`
holds the prompt: the receiver writes the engine's input from `Guard.opening(packet)` ((bytes, close):
Claude Code's initialize control request with its input left open, Codex's packet whole and closed),
reads the stream through `Guard.feed`, where a login the engine reports that is not a subscription stops
the worker by name (stop cause `paid_api`, the invocation cancelled, the artifact's `login` naming it)
before the prompt is ever written, and writes each `Guard.release()` (the prompt, once the login is
confirmed; for a role-bound run first its capability probe, VELDO-0127) before closing the input after the
prompt; a stopped run's input is closed with nothing more written. An
account the config's `subscription_tokens` names (account to a 0600 file of this account's own) runs
with that token as CLAUDE_CODE_OAUTH_TOKEN, the one login variable it then carries; the file is opened
once, without following a link, and checked and read on that one descriptor. The receiver's own environment keeps
the SSH agent, the session bus, the Git tokens and its runtime directory, so its systemd-run and
systemctl reach the user manager; it names the run's own empty runtime directory (`<run>/runtime`, never
its own and never the configuration directory) in ENGINE_RUNTIME, and the trusted wrapper, just before
it execs, removes EXEC_STRIPPED and that name and makes the directory the engine's XDG_RUNTIME_DIR
(`engine_environment`). The receiver reports each launch's baseline, the names it removed and never a
value (`baseline` event). VELDO-0173: the role revision a dispatch binds (the contract's capability
configuration `role_revision`, VELDO-0127's) reaches the engine's baseline as the run's `revision`, checked
before acceptance; Claude Code's baseline ends with its launch tool options, and the event names the launch
tool set, the registry tools switched off and the revision, beside the pinned version and digest.

THE EXECUTION RECORD (VELDO-0141). Every run's output is kept, as it is read and in order, as its execution
record (control_execution_record): the engine's standard output line by line (its structured events), the
worker's error stream (piped to this receiver, never discarded) and the trusted wrapper's identity line, each
redacted before it is kept, first of every value in the run's set of resolved credential values (`Resolved`,
filled by RESOLVERS when the worker is spawned: the account's subscription token, and whatever a resolver adds),
then by the secret scanner. After each batch the API is hinted with the last sequence (the configuration's
`record_hint_service`, or legacy `record_hints`), the exit record commits the record's line count, byte count and digest, and once the end is
recorded a last hint marks it ended, before the runner is told. The record lives under the configuration's
`records`, else the factory state root's `records`.

THE CREDENTIALS OF A LINUX RUN (VELDO-0158). A dispatch configuration's `mcp` lists the catalog servers it uses
(server id and revision, VELDO-0144). Immediately before the spawn the receiver reads each listed revision and
resolves exactly the credential references its environment and headers hold from the keystore, through secretref's
keychain scheme (control_credential_delivery); the engine's baseline then delivers them: Claude Code's generated MCP
configuration, values included, in the run's private configuration directory (0700, removed with the run), or, for
Codex, the engine environment under the name the server definition gives each, which the generated `mcp_servers`
table names through `env_vars` or `bearer_token_env_var`. No value is on a command line, in the packet, the contract
or the journal. A credential that does not resolve (keystore locked or unreachable, a reference naming nothing)
refuses the launch as `credential_unavailable:<id>` before anything is spawned, and every value resolved enters the
run's set of resolved values (`keystore_credentials`), a bearer token also without its scheme. A credential named for the
Codex engine environment that collides with a name the engine already has is refused by name
(`invalid_input:mcp_delivery:env_collision:<name>`), never replaces it. The receiver reports the revisions, credential
ids and routes (`credentials` event), never a value. A run directory its receiver could not remove (the receiver died,
or the run's group could not be emptied) is removed by the Runner once the kernel shows the run gone
(`Runner.clear_runs`, after an orphan's release and at every sweep), and the authority service's start sweeps every
directory whose dispatch is settled (`Runner.sweep_runs`); a run still alive keeps its directory until a later pass.

THE LAUNCH PIPE (VELDO-0154). The factory loop in the authority service (control_service.FactoryLoop) owns a
Runner and registers each running dispatch's receiver output, `Launch.fileno()`, in its service loop's poll set.
`Launch.pump()` takes what the pipe holds without waiting and is true once the run's end is seen: the receiver's
`exited` or `unknown` report, or the pipe's end of file when the receiver died without either (`lost`). The loop
then settles the run through `Runner.wait(launch, timeout=0)`, which records a silent receiver's running dispatch
`outcome_unknown` as always, and for a lost receiver `Runner.orphaned` frees the dispatch's ACCOUNT SLOT (its worker
slot and usage reservation stay held, since its outcome is unknown): it makes the stop the dead receiver owed, reads
from the kernel that nothing of the run is left and commits the reservation service's `release_account`.

WHAT IT IS NOT. No recovery of an unknown dispatch, leadership fencing or crash-safe retirement
(Release 2), and no model API. Standard library only.
"""
import contextlib
import copy
import errno
import fnmatch
import hashlib
import math
import importlib.util
import json
import os
from pathlib import Path
import select
import shutil
import queue
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid


def _organ(name):
    spec = importlib.util.spec_from_file_location('launch_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SC = _organ('control_clone')
D = _organ('control_dispatch')
ADMISSION = _organ('control_space_admission')
S = D.S
C = _organ('control_containment')
HB = _organ('control_heartbeat')
RT = _organ('control_retirement')
ER = _organ('control_execution_record')
CFG = _organ('control_agent_config')
HANDOFF = _organ('control_agent_config_handoff')
DL = _organ('control_credential_delivery')
# VELDO-0062: the account records (the instance the reservations module reads windows through), the
# invocation seam and each subscription engine's login and usage reports.
ACC = D.RES.ACC
RTM = _organ('control_reservation_runtime')
ENGINES = {'claude_code': _organ('control_engine_claude'), 'codex': _organ('control_engine_codex')}
# VELDO-0185 AC4: the refusal of a dispatch on an account its engine reports not logged in to its subscription.
ACCOUNT_LOGIN = D.RES.POOL.ACCOUNT_LOGIN
# Every name either binary's lists make a login: none reaches any engine, whichever it is, and an
# adapter configuring one is refused. STRIPPED adds each binary's settings of the owner's shell, which
# the inherited environment loses and an adapter may configure.
CREDENTIALS = frozenset().union(*(engine.CREDENTIALS for engine in ENGINES.values()))
STRIPPED = CREDENTIALS.union(*(engine.SETTINGS for engine in ENGINES.values()))
NEVER_CONFIGURED = frozenset().union(*(getattr(engine, 'BASELINE', {}).get('strip_names', ())
                                       for engine in ENGINES.values()))
# What every engine module implements, with the same signatures (THE ENGINE PROTOCOL above).
ENGINE_PROTOCOL = ('PROVIDER', 'CREDENTIALS', 'SETTINGS', 'REGISTRATION', 'Meter', 'Refused', 'bind', 'command',
                   'environment', 'Terminal', 'baseline', 'profile_problem', 'login_problem', 'Guard')
RECEIPTS_SCHEMA = 'veldo.usage_receipts/v1'
ARTIFACT_REPORT = ('path', 'digest', 'verdict', 'complete')
RECEIVER = str(Path(__file__).resolve())
JOURNAL_NAMESPACE = 'veldo-journal'
ACCEPT_SECONDS = 30
WRAPPER_SCHEMA = 'veldo.launch_identity/v1'


def subscription_token(receiver, contract, adapter, environment):
    """The subscription token the receiver resolved for this run's account (VELDO-0155 AC2), if any."""
    return [('subscription_token', receiver.token)] if receiver.token else []


def keystore_credentials(receiver, contract, adapter, environment):
    """VELDO-0158 AC3: every value the receiver resolved from the keystore for this run's selected MCP servers,
    as resolved (an Authorization-style header's also without its scheme, for every engine) and as delivered, all
    of the one kind."""
    delivered = list(DL.values(receiver.credentials)) + list((receiver.delivered or {}).values())
    return [(DL.KIND, value) for value in delivered]


# VELDO-0141: the credential resolvers of a run, each `resolver(receiver, contract, adapter, environment)` ->
# [(kind, value)], called once as the worker is spawned (it may deliver its value into the engine's
# `environment`); every value one returns enters the run's set of resolved values, which the execution
# record replaces before the secret scanner runs. VELDO-0158 AC3 adds the keystore's.
RESOLVERS = [subscription_token, keystore_credentials]


# THE SECRET SCAN AT RUN END AND AT A LANDING CANDIDATE (VELDO-0254 AC2). The one scan entry (secret_scan.scan)
# reads the files a run changed in its workspace (its clone's work tree and scratch, its conversation directory)
# once its end is recorded, and the changed files of a landing candidate before it lands, and REPORTS what it finds,
# masked, to the scan log (the configuration's `secret_scan_log`, else secret-scan.jsonl under the state root, else
# beside the store), from which the running service's channel tells the owner (control_service_channel). It never
# edits a file, stops a run or refuses a landing; a scan that fails is logged there by name, never swallowed. The
# credentials held for the gate, which it also matches by digest, are the outside gate's (VELDO-0251) and reach it
# through `held` once the gate holds them.
SS = _organ('secret_scan')


def secret_scan_log(config):
    """Where a receiver configuration's secret scans are logged (None for a configuration naming no store)."""
    root = config.get('state_root') or (os.path.dirname(config['store']) if config.get('store') else None)
    return config.get('secret_scan_log') or (os.path.join(root, SS.LOG_NAME) if root else None)


def scan_run_end(config, dispatch_id, project, roots, held=(), notify=None, before=None):
    """The run-end trigger: one scan, one report, over the files under the run's workspace roots; with `before`
    ({root: secret_scan.tree_state} as the run started) only the files the run added or changed."""
    def files():
        for root in roots:
            if root and os.path.isdir(root):
                if before is not None:
                    yield from SS.changed_files(root, before.get(root))
                else:
                    yield from SS.tree_files(root)
    return SS.scan('run_end', project, files(), held=held, log=secret_scan_log(config), notify=notify,
                   dispatch=dispatch_id)


def run_roots(receiver, dispatch_id):
    """A run's workspace roots: its clone's work tree and scratch, and its conversation directory."""
    config, roots = getattr(receiver, 'config', None) or {}, []
    if config.get('clones'):
        clones = _organ('control_clone').Clones(receiver.dispatches, space=getattr(receiver, 'space', None),
                                                **config['clones'])
        handle = clones.clone_of(dispatch_id)
        if handle is not None:
            paths = clones._paths(handle)
            roots += [paths.get('work'), (paths.get('scratch') or {}).get(dispatch_id)]
    roots.append(getattr(receiver, 'conversation_directory', None))
    return [r for r in roots if r]


def _project(contract):
    return (contract.get('reservation') or {}).get('project') or contract.get('repository')


def run_end_scan(receiver, dispatch_id, contract):
    """VELDO-0254 AC2: the run-end scan of the files the run changed in its workspace, once its end is recorded. It
    reports only; a scan that fails is logged to the owner's scan log by name and changes nothing about the run."""
    config = getattr(receiver, 'config', None) or {}
    try:
        scan_run_end(config, dispatch_id, _project(contract), run_roots(receiver, dispatch_id),
                     before=getattr(receiver, 'workspace_before', None))
    except Exception as error:
        SS.failed('run_end', _project(contract), error, _failure_log(config), dispatch=dispatch_id)


def report_end(receiver, contract, event):
    """VELDO-0254 AC2: a run whose end is recorded has the files it changed scanned now, so the scan neither delays
    the record nor re-reads what was there before; then its end is reported. VELDO-0308: with a space ledger the
    run's space end (Receiver._space_end: the census, Signal, the release of the hold) is made between the two:
    after the record and the scan, which reads the run's scratch, and before the report, because the runner stops
    this receiver once it reads the end."""
    run_end_scan(receiver, contract['dispatch_id'], contract)
    if getattr(receiver, 'space', None) is not None and hasattr(receiver, '_space_end'):
        end = receiver._space_end(contract['dispatch_id'], contract)
        event = dict(event, space={'sent': end['sent'], 'reason': end['reason'], 'items': end['items'],
                                   'hold': (end['hold'] or {}).get('state')})
    receiver.emit(event)


def _failure_log(config):
    try:
        return secret_scan_log(config)
    except Exception:
        return None


def scan_candidate(config, project, repository, base, head, held=(), notify=None):
    """The landing-candidate trigger: the files `head` adds or changes against `base`, before it lands."""
    return SS.scan('landing_candidate', project, SS.candidate_files(repository, base, head), held=held,
                   log=secret_scan_log(config), notify=notify)


def candidate_scan(config, project, repository, base, head):
    """The landing scan as the build collection runs it: it reports only, and a scan that fails is logged to the
    owner's scan log by name (None is returned) and changes nothing about the landing."""
    try:
        return scan_candidate(config, project, repository, base, head)
    except Exception as error:
        SS.failed('landing_candidate', project, error, _failure_log(config))
        return None


# THE LAUNCH-TIME SCAN (VELDO-0254 AC1). Runs keep today's environment inheritance; what a run is started with is
# scanned instead, whatever reached it (a value inherited from the host, an adapter's literal, anything read from a
# file into the environment or the command): the run's final environment (as the trusted wrapper hands it to the
# engine, engine_environment) and its command line, through the one scan entry with the same formats, just before
# the spawn. A credential found is logged masked and the launch is refused by name,
# credential_delivery_site:environment:<name> or credential_delivery_site:command:<position>. The engine's own
# model login, where the launcher hands it over (the subscription token), is where it belongs and is not a finding,
# nor, until VELDO-0257 removes that path, a VELDO-0158 catalog credential the launcher delivered itself.
def launch_scan(config, dispatch_id, project, environment, argv, own=()):
    """None when the run's final environment and command line hold no credential, else the named refusal."""
    final = engine_environment(dict(environment)) if ENGINE_RUNTIME in environment else dict(environment)
    files = [('environment/' + name, str(value).encode('utf-8', 'surrogateescape'))
             for name, value in sorted(final.items())]
    files += [('command/%d' % at, str(arg).encode('utf-8', 'surrogateescape')) for at, arg in enumerate(argv)]
    report = SS.scan('launch', project, files, log=secret_scan_log(config), dispatch=dispatch_id, own=own)
    if not report['findings']:
        return None
    return 'credential_delivery_site:' + report['findings'][0]['file'].replace('/', ':', 1)


# THE ONE LAUNCHER DECISION (VELDO-0254 AC3). By default a launch starts as today: the host's network, shared
# databases, container tooling and local and loopback services, with no fence, namespace, name resolution change
# or filesystem confinement added. A launch starts in the confined runner of VELDO-0208 (scripts/agent_sandbox.py,
# named with its configuration by the receiver configuration's `confined_runner`: {program, config}) only when it
# is marked risky: by the installation (`risky.installation`), its project (`risky.projects`) or its dispatch (the
# contract's input context `risky`). A risky launch on a host that cannot provide the confined runner is refused as
# confined_runner_unavailable:<reason>; no other launch is ever refused for a confinement reason. Receiver.launch is
# the one caller, for every launch kind it accepts (engine run, conversation turn, workflow step), and names the
# decision on the launch's accepted (or refused) line.
def runner_decision(config, contract):
    """{runner: default | confined, why: None | installation | project | dispatch}."""
    marks = config.get('risky') or {}
    project = (contract.get('reservation') or {}).get('project') or contract.get('repository')
    if marks.get('installation') is True:
        return {'runner': 'confined', 'why': 'installation'}
    if project is not None and project in (marks.get('projects') or ()):
        return {'runner': 'confined', 'why': 'project'}
    if ((contract.get('input') or {}).get('context') or {}).get('risky') is True:
        return {'runner': 'confined', 'why': 'dispatch'}
    return {'runner': 'default', 'why': None}


def confined_runner_problem(config, cache=None):
    """None when this host can start the configured confined runner, else confined_runner_unavailable:<reason>.
    With `cache` (a receiver's own), the host is judged once per configured runner and the answer kept."""
    runner = config.get('confined_runner') or {}
    key = (runner.get('program'), runner.get('config'))
    if cache is not None and key in cache:
        return cache[key]
    problem = _confined_runner_problem(runner)
    if cache is not None:
        cache[key] = problem
    return problem


def _confined_runner_problem(runner):
    program, settings = runner.get('program'), runner.get('config')
    if not isinstance(program, str) or not isinstance(settings, str):
        return 'confined_runner_unavailable:not_configured'
    if not os.path.isfile(program):
        return 'confined_runner_unavailable:program_missing'
    if not os.path.isfile(settings):
        return 'confined_runner_unavailable:config_missing'
    # The helper the runner names, read from its source (never loaded into this process), then the runner's own
    # self-test of the namespace it makes: only a host where both hold provides the confined runner.
    try:
        named = re.search(r"^NAMESPACE_HELPER = Path\('([^']+)'\)$", Path(program).read_text(), re.M)
    except (OSError, UnicodeError):
        named = None
    if named is None:
        return 'confined_runner_unavailable:program_unusable'
    if not os.path.lexists(named.group(1)):
        return 'confined_runner_unavailable:helper_missing'
    try:
        tested = subprocess.run([sys.executable, '-I', '-S', program, 'namespace-selftest'], capture_output=True,
                                timeout=120, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        tested = None
    if tested is None or tested.returncode != 0:
        return 'confined_runner_unavailable:namespace_selftest'
    return None


def runner_refusal(config, decision, cache=None):
    """The named refusal of a launch the decision sends to a confined runner this host cannot provide, else None."""
    return confined_runner_problem(config, cache) if decision['runner'] == 'confined' else None


# The confined runner's agent client (scripts/agent_sandbox.json `clients`) whose files each engine receives.
RUNNER_CLIENTS = {'claude_code': 'claude', 'codex': 'codex'}


def runner_argv(config, decision, argv, worktree, client=None):
    """What the spawn starts: the argv as today, or the same argv inside the confined runner, with `worktree` its
    writable root and `client` the agent client whose files it hands the engine."""
    if decision['runner'] != 'confined':
        return list(argv)
    if not worktree:
        raise C.Refused('confined_runner_unavailable:no_worktree')
    runner = config['confined_runner']
    return [sys.executable, '-I', '-S', runner['program'], '--config', runner['config'],
            *(['--client', client] if client else []), '--worktree', str(worktree), '--', *argv]


def confined_inner(argv):
    """The argv a confined-runner argv starts (runner_argv's shape), else None."""
    at = 6 if len(argv) > 6 and argv[6] == '--client' else 4
    if (len(argv) > at + 5 and argv[1:3] == ['-I', '-S'] and argv[4] == '--config'
            and argv[at + 2] == '--worktree' and argv[at + 4] == '--'):
        return list(argv[at + 5:])
    return None


# OS process identity.

def process_identity(pid):
    """{platform, host, boot_id, pid, start}: what identifies one process across pid reuse."""
    host = socket.gethostname()
    if sys.platform.startswith('linux'):
        stat = Path('/proc/%d/stat' % pid).read_text()
        # Field 22 is the start time; fields after the parenthesized command name start at 3.
        start = stat[stat.rindex(')') + 2:].split()[19]
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        return {'platform': 'linux', 'host': host, 'boot_id': boot, 'pid': pid, 'start': start}
    if sys.platform == 'darwin':
        env = {'PATH': '/bin:/usr/bin:/usr/sbin:/sbin', 'LC_ALL': 'C'}
        start = subprocess.run(['ps', '-o', 'lstart=', '-p', str(pid)], capture_output=True, text=True,
                               timeout=5, env=env).stdout.strip()
        boot = subprocess.run(['sysctl', '-n', 'kern.boottime'], capture_output=True, text=True,
                              timeout=5, env=env).stdout.strip()
        if not start or not boot:
            raise ValueError('process identity unreadable')
        return {'platform': 'darwin', 'host': host, 'boot_id': boot, 'pid': pid, 'start': start}
    raise ValueError('no process identity reader for ' + sys.platform)


# THE ENGINE PROTOCOL's argv check and exec-time re-hash, the same for every engine.

ENTRANCE_MODULE, WRAPPER_MODULE = 'control_clone.py', 'control_launch.py'
ENGINE_PATH, ENGINE_DIGEST = 'VELDO_ENGINE_PATH', 'VELDO_ENGINE_SHA256'
WRAPPER_REFUSED = 70
# VELDO-0155 AC4, VELDO-0156 AC4: what the trusted wrapper removes from the environment it execs an engine
# with (the SSH agent, the session bus, the Git tokens), and the variable naming the engine's own runtime
# directory, which the wrapper makes the engine's XDG_RUNTIME_DIR. The receiver keeps all of them, so its
# own systemd-run and systemctl still reach the user manager.
EXEC_STRIPPED = ('SSH_AUTH_SOCK', 'SSH_AGENT_PID', 'DBUS_SESSION_BUS_ADDRESS', 'GH_TOKEN', 'GITHUB_TOKEN',
                 'SHELL', 'GIT_EDITOR', 'TRACEPARENT', 'TRACESTATE', 'TMUX', 'TMPDIR', 'TMPPREFIX', 'BUN_OPTIONS',
                 'TEMP', 'TMP', 'GIT_CONFIG_PARAMETERS', 'COREPACK_ENABLE_AUTO_PIN',
                 'NoDefaultCurrentDirectoryInExePath',
                 # VELDO-0165: what Claude Code writes into its own environment when unset, for every child.
                 'OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE',
                 # VELDO-0165: what Codex 0.154.0 sets on every command it runs (its unified exec pairs,
                 # proof/VELDO-0165/codex-environment.json); each engine's baseline sets LANG and TERM itself.
                 'NO_COLOR', 'TERM', 'LANG', 'LC_CTYPE', 'LC_ALL', 'COLORTERM', 'PAGER', 'GIT_PAGER', 'GH_PAGER')
ENGINE_RUNTIME = 'VELDO_ENGINE_RUNTIME_DIR'
RUN_CONFIG, RUN_RUNTIME = 'config', 'runtime'
# VELDO-0158: the names of the engine's own environment a credential delivered into it never takes, besides every
# name the receiver's environment, the adapter, the baseline and the account set: a collision is refused by name.
ENGINE_RESERVED = frozenset(('PATH', 'HOME', 'LANG', 'TERM', 'USER', 'LOGNAME', 'SHELL', 'TMPDIR', 'TZ',
                             'XDG_RUNTIME_DIR', 'VELDO_DISPATCH_ID'))
FACTORY_PREFIX = 'VELDO_'
DELIVERY_PREFIX = 'VELDO_MCP_'
TOKEN_VARIABLE = 'CLAUDE_CODE_OAUTH_TOKEN'
SESSION_PREFIXES = ('CLAUDE', 'CLAUDECODE', 'AI_AGENT', 'CODEX')
ENGINE_OVERRIDES = 'VELDO_ENGINE_ENVIRONMENT'


SPACE_ENDED = ('removed', 'gone')  # the states of an item whose thing is no longer on disk
SPACE_SAFE = ('gone', 'clear', 'kept')  # the answers of the look with no ledger that allow a delete
_SPACE = {}


def space_signal(space, event, paths, emitter, ended=False, confirm=False, alone=False, clones=None):
    """VELDO-0303: send `event` through Signal (control_space_signal.signal) for the things at `paths`
    and say what became of each: {path: {item, state, deferral}}. Nothing here deletes anything:
    whatever goes is removed by Signal's removers, after the safety rules and the keep step.

    `space` is what the installation wires in when it has a space ledger: a mapping with ledger (the
    control_space.Ledger) and, under their own names, the arguments Signal is given (probe, kinds,
    remover, free, keep, owner_live, landed, queued, run, proc, borrow_root). The items are the live
    ones the ledger records at or beneath `paths`. The event is signalled once for each owner among
    them, and the subject is every part of that owner. A path the ledger records no live item for
    answers with no item and the deferral not_in_ledger, and nothing is done to it; when the kernel
    says nothing is at that path (not found, and no other answer) it answers gone, for there is
    nothing to remove. Whatever raises removes nothing: every path then answers with the deferral
    remove_refused and what was raised.

    `ended` says the caller has just read from the kernel that the runs owning these items are over:
    rule 3 is answered conclusive for those runs and for no other owner. `confirm` first confirms the
    items still in state declared (a creation that failed part way), so the event reaches them.
    `alone` sends the event for exactly the run's own items and for nothing else of their owner: the
    signal names each item with the version read here (space_named, the ledger's signal that names items),
    and the ledger refuses the whole command, with nothing written, when one of them changed since. The
    run's own items are what the owner's event would reach (present, kept or deferred, ending on the
    event, not marked Keep by the owner), a worktree or an agent repository elsewhere among them, less
    every item of a clone that is not at or beneath `paths`: a clone is never named. One a retirement
    handed to the ledger is the ledger's, and it is left as it is. One that is still live (declared or
    present) is ended by its own teardown, which names exactly the clone's own items at their versions
    (control_clone.space_signal) and nothing else of that owner: it does not hold this send back, and
    this send is not waited for by it. `clones` is what says where the clones are (clones_root). A
    send the ledger refused answers remove_refused for every path, with the ledger's reason."""
    paths = [os.path.normpath(str(path)) for path in paths]
    found = {path: {'item': None, 'state': None, 'deferral': 'not_in_ledger'} for path in paths}

    def beneath(record):
        where = (record.get('locator') or {}).get('path')
        return bool(where) and any(where == path or where.startswith(path + '/') for path in paths)

    try:
        ledger = space['ledger']
        given = {key: value for key, value in space.items() if key != 'ledger'}
        every = ledger.items()
        live = {identity: record for identity, record in every.items()
                if record.get('state') not in SPACE_ENDED and beneath(record)}
        subjects, runs = [], set()
        for identity, record in sorted(live.items()):
            if confirm and record.get('state') == 'declared':
                ledger.confirm(identity)
            owner = dict(record.get('owner') or {})
            if isinstance(owner.get('run'), dict):
                owner['run'] = owner['run'].get('id')
                runs.add(owner['run'])
            if owner and owner not in subjects:
                subjects.append(owner)
        if alone:
            # Exactly the run's own items, each at the version read now; never an item of a clone.
            named = space_named(ledger, event, paths, subjects, clones_root(clones))
            sends = [named] if named['items'] else []
        else:
            sends = subjects
        if ended:
            wired = given.get('owner_live')
            given['owner_live'] = lambda owner: (
                {'conclusive': True, 'group_empty': True} if (owner.get('run') or {}).get('id') in runs
                else wired(owner) if wired else None)
        if 'signal' not in _SPACE:
            _SPACE['signal'] = _organ('control_space_signal').signal
        for subject in sends:
            answer = _SPACE['signal'](ledger, event, subject, emitter=emitter, **given)
            if alone and not (isinstance(answer, dict) and answer.get('ok') is True):
                # One named item changed since it was read: nothing was written, and nothing is sent in its place.
                raise ValueError('the ledger refused the send whole: %s'
                                 % ((answer or {}).get('reason') if isinstance(answer, dict) else answer,))
        for identity, record in live.items():
            where = record['locator']['path']
            if where in found:
                now = ledger.item(identity) or {}
                found[where] = {'item': identity, 'state': now.get('state'),
                                'deferral': (now.get('deferral') or {}).get('rule')
                                if now.get('state') == 'deferred' else None}
        for path in paths:
            if found[path]['item'] is None and space_absent(path):
                found[path] = {'item': None, 'state': 'gone', 'deferral': None}
    except Exception as error:  # noqa: BLE001 - what could not be signalled is not removed
        raised = '%s: %s' % (type(error).__name__, str(error)[:300])
        found = {path: {'item': None, 'state': None, 'deferral': 'remove_refused', 'raised': raised}
                 for path in paths}
    return found


def space_absent(path):
    """Whether the kernel says nothing is at `path`: not found, and nothing else. A path that could
    not be read (a folder above it that may not be searched, a failing disk) is not absent."""
    try:
        os.lstat(path)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return False


def space_refusal(entry):
    """The name of the refusal for a thing Signal did not remove: space_deferred and the rule that
    deferred it; for an item no rule deferred, the state it is in (due in report mode, removing when
    it was left under its marked name, kept, present); not_in_ledger when no item records it."""
    return 'space_deferred:' + str(entry.get('deferral') or entry.get('state') or 'not_in_ledger')


def space_standalone(path, kind, main=None, event='run_finished', ticket=None, skip=()):
    """VELDO-0303: the look before a delete where no ledger is wired (control_space_standalone): the
    unique work probe and the keep step for the thing at `path`, {path, item, state, deferral, said,
    refs}. This module deletes the thing only when the state is one of SPACE_SAFE: nothing is there
    (gone), a folder holds no repository (clear), or the commits of a worktree or a private repository
    are on kept refs in `main` (kept). Anything else stays where it is. Whatever raises removes nothing."""
    try:
        if 'standalone' not in _SPACE:
            _SPACE['standalone'] = _organ('control_space_standalone').standalone
        return _SPACE['standalone'](str(path), kind, main=None if main is None else str(main), event=event,
                                    ticket=ticket, skip=tuple(str(where) for where in skip))
    except Exception as error:  # noqa: BLE001 - what could not be looked at is not removed
        return {'path': str(path), 'item': None, 'state': None, 'deferral': 'remove_refused',
                'said': '%s: %s' % (type(error).__name__, str(error)[:300]), 'refs': {}}


# VELDO-0308: run finished, from the receiver (design section 5, 6.7 and 8.1 steps 6 to 10). Nothing here
# deletes anything.
SPACE_CONCLUSIVE = ('exited', 'refused')  # a dispatch record with a recorded end (VELDO-0041)
SPACE_HELD = ('due', 'deferred', 'removing', 'kept')  # an item an ending event reached and did not remove


def _space_run_of(record):
    return ((record.get('owner') or {}).get('run') or {}).get('id')


def space_run_items(space, dispatch_id):
    """What the ledger holds of the run `dispatch_id` now: {item: {kind, state, deferral}} for every item
    the run owns, each removal outcome as it was written. A ledger that cannot be read answers nothing."""
    try:
        return {identity: {'kind': record.get('kind'), 'state': record.get('state'),
                           'deferral': (record.get('deferral') or {}).get('rule')
                           if record.get('state') == 'deferred' else None}
                for identity, record in sorted(space['ledger'].items().items())
                if _space_run_of(record) == dispatch_id}
    except Exception:  # noqa: BLE001 - a record of what happened, never a reason to stop the end
        return {}


def space_held(space, path):
    """VELDO-0308: whether the ledger already answers for the thing at `path`: {item, state} when the live
    item recorded there is due, deferred, removing or kept, which is where an ending event leaves an item
    it reached and did not remove; None when no live item is there or the one there is declared or present
    (no event has reached it). From then on the item is retried by the ledger's own retries (design
    section 7, Retry) and never by a sweep. Raises when the ledger cannot be read: the caller then sends
    nothing and forgets nothing."""
    where = os.path.normpath(str(path))
    for identity, record in sorted(space['ledger'].items().items()):
        if (record.get('locator') or {}).get('path') == where and record.get('state') not in SPACE_ENDED:
            return {'item': identity, 'state': record.get('state')} if record.get('state') in SPACE_HELD else None
    return None


SPACE_SIGNALLED = ('present', 'kept', 'deferred')  # the states the ledger's signal reaches


def clones_root(clones):
    """VELDO-0308: the folder every clone of this installation is under, as a path, or None for an
    installation without clones. `clones` is the clone provisioner, or the receiver configuration's
    clones section (the arguments of control_clone.Clones). Raises when clones are wired and their folder
    cannot be read: the caller then sends nothing."""
    if not clones:
        return None
    where = clones.get('clones') if isinstance(clones, dict) else getattr(clones, 'clones', None)
    if not where:
        raise ValueError('the clones are wired and their folder is not named')
    return os.path.realpath(str(where))


def _space_beneath(record, places):
    where = (record.get('locator') or {}).get('path')
    return bool(where) and any(where == path or where.startswith(path + '/') for path in places)


def _space_owner(record):
    """An item's owner as a signal's subject has it: every part, a run by its id."""
    found = dict(record.get('owner') or {})
    if isinstance(found.get('run'), dict):
        found['run'] = found['run'].get('id')
    return found


def _space_clones(record, paths, root):
    """Whether an item is a clone's and apart from the things at `paths`: beneath the clones folder `root`
    and not at or beneath `paths`. With no clones folder there is no clone."""
    beneath = _space_beneath

    def within(record):
        return root is not None and beneath(record, [root])

    return not beneath(record, paths) and within(record)


def space_versions(ledger):
    """The version of every entity of the ledger's store now, {identity: version}."""
    return {identity: version for identity, version in ledger.conn.execute('SELECT id, version FROM entities')}


def space_named(ledger, event, paths, subjects, root):
    """VELDO-0308: the subject of an event sent for exactly the run's own items, as the ledger's signal
    that names items takes it: {items: [{item, version}, ...]}. The items are those an event for the
    owners `subjects` would reach (present, kept or deferred, ending on `event`, not marked Keep by the
    owner), less every item of a clone apart from `paths` (_space_clones): a clone is never named, live
    or handed over. The versions are read before the records, so a record that changed between the two
    reads is named at the version it had, and the ledger refuses the whole command. An item that appeared
    between them was not read and is not named."""
    versions = space_versions(ledger)
    named = sorted(identity for identity, record in ledger.items().items()
                   if identity in versions and record.get('state') in SPACE_SIGNALLED and not record.get('owner_keep')
                   and event in ((record.get('ends_on') or {}).get('events') or ())
                   and not _space_clones(record, paths, root)
                   and any(all(_space_owner(record).get(part) == wanted for part, wanted in subject.items())
                           for subject in subjects))
    return {'items': [{'item': identity, 'version': versions[identity]} for identity in named]}


def space_release(space, identity, run=None):
    """VELDO-0308 AC2: release the hold `identity` (design 6.7: at run finished, after Signal). The answer is
    {hold, state, released, refusal}: released is True when this call wrote the release. A hold that is
    released already is left as it is, and a run that was given no hold has none (refusal no_hold).
    Whatever raises releases nothing and is named."""
    out = {'hold': identity, 'state': None, 'released': False, 'refusal': None}
    try:
        ledger = space['ledger']
        held = ledger.hold(identity) if isinstance(identity, str) and identity else None
        if held is None:
            return dict(out, refusal='no_hold')
        if held.get('state') == 'released':
            return dict(out, state='released')
        used = None
        if run is not None:
            used = {pool: 0 for pool in held['needs']}
            for item in ledger.items().values():
                if _space_run_of(item) == run and item.get('pool') in used:
                    size = (item.get('size') or {}).get('bytes')
                    if type(size) is not int:
                        used.pop(item['pool'], None)
                    else:
                        used[item['pool']] += size
        done = ledger.release(identity, used=used)
        if not done.get('ok'):
            return dict(out, state=held.get('state'), refusal=str(done.get('reason')))
        return dict(out, state='released', released=True)
    except Exception as error:  # noqa: BLE001 - a hold that could not be released is named, never assumed
        return dict(out, refusal='%s: %s' % (type(error).__name__, str(error)[:300]))


def space_retry(space, dispatch_id, emitter, but=(), ended=False):
    """VELDO-0308 AC3: judge again, once, the items of the run `dispatch_id` that the ledger holds deferred
    (design section 7, Retry). Run finished is signalled once for each owner among them, as their next
    ending event, and Signal judges each item again from rule 1 and writes its outcome before this
    returns. `ended` says the caller has just read, from the dispatch record and from the kernel, that
    this run is over: rule 3 is then answered conclusive for this run and for no other owner; without
    it rule 3 is left to the answer the installation wired in. `but`
    names paths whose items were sent the event in this same call already (a clone's teardown): an
    owner of an item at or beneath one of them is not signalled again. The answer is {retried, signals,
    states, raised}: the deferred items that were retried, the number of events sent, and the state of
    each as the call returns. A run with no deferred item gets nothing and nothing is written. Nothing
    here deletes anything, and whatever raises removes nothing."""
    out = {'retried': [], 'signals': 0, 'states': {}, 'raised': None}
    try:
        ledger = space['ledger']
        given = {key: value for key, value in space.items() if key != 'ledger'}
        paths = [os.path.normpath(str(path)) for path in but]

        def subject(record):
            owner = dict(record.get('owner') or {})
            if isinstance(owner.get('run'), dict):
                owner['run'] = owner['run'].get('id')
            return owner

        def beneath(record):
            where = (record.get('locator') or {}).get('path')
            return bool(where) and any(where == path or where.startswith(path + '/') for path in paths)

        every = ledger.items()
        sent = [subject(record) for record in every.values() if beneath(record)]
        subjects = []
        for identity, record in sorted(every.items()):
            if record.get('state') != 'deferred' or _space_run_of(record) != dispatch_id:
                continue
            owner = subject(record)
            if owner in sent:
                continue
            out['retried'].append(identity)
            if owner not in subjects:
                subjects.append(owner)
        if not subjects:
            return out
        if ended is True:
            wired = given.get('owner_live')
            given['owner_live'] = lambda owner: (
                {'conclusive': True, 'group_empty': True} if (owner.get('run') or {}).get('id') == dispatch_id
                else wired(owner) if wired else None)
        if 'signal' not in _SPACE:
            _SPACE['signal'] = _organ('control_space_signal').signal
        for owner in subjects:
            _SPACE['signal'](ledger, 'run_finished', owner, emitter=emitter, **given)
            out['signals'] += 1
        out['states'] = {identity: (ledger.item(identity) or {}).get('state') for identity in out['retried']}
    except Exception as error:  # noqa: BLE001 - what could not be retried stays deferred
        out['raised'] = '%s: %s' % (type(error).__name__, str(error)[:300])
    return out


# VELDO-0305: the run census and the run's space environment (design 6.3). Nothing here deletes
# anything: the census declares, confirms and measures, and what it declares goes later by Signal's
# removers, after the safety rules and the keep step.
CENSUS_SECONDS = 600
SPACE_WORKTREES = ('worktree', 'agent_repository')  # the kinds whose folder is a run's worktree
SPACE_STATIONS = ('build', 'review', 'gate')  # the stations the ledger records a run with
SPACE_TEMPORARY = 'TMPDIR'
SPACE_UNAVAILABLE = 'unavailable_service:space_ledger'
# A folder of the run that is on disk and wrongly recorded: a state of a path that every launch of
# the worktree meets again, and never the ledger being out of reach.
SPACE_UNRECORDED = 'invalid_state:space_folder_unrecorded'
SPACE_OTHERWISE = 'invalid_state:space_folder_recorded_otherwise'
SPACE_RUN_DIRECTORY = 'invalid_state:space_folder_run_directory'
SPACE_FOLDER_STATE = 'invalid_state:space_folder_'
SPACE_RUN_SCRATCH = 'run-scratch'  # under the scratch root; never the name the run directories are under
SPACE_COMMIT = re.compile(r'[0-9a-f]{40}([0-9a-f]{24})?\Z')


class _CensusStop(Exception):
    """A read the census could not make: it records nothing."""


def _census_git(where, *argv, feed=None, absent=False):
    """One git read of the census, through the one Git boundary: no GIT_ variable of the caller and
    no system or global configuration reaches it, and no excludes file the repository's own
    configuration names (core.excludesFile is set to nothing on the command line, which is read
    last), so a path only a personal excludes file ignores is an untracked path here. Raises
    _CensusStop when git cannot say; with `absent`, a quiet failure answers None."""
    _git_process = _organ('git_process')
    given = dict(env=dict(os.environ, LC_ALL='C'), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                 timeout=CENSUS_SECONDS)
    given.update({'stdin': subprocess.DEVNULL} if feed is None else {'input': feed})
    try:
        done = _git_process.run(['git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
                                 '-c', 'core.excludesFile=', '-C', str(where)]
                                + [str(word) for word in argv], **given)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise _CensusStop('git could not be run: %s' % type(error).__name__) from None
    if done.returncode:
        if absent and done.returncode == 1 and not done.stderr.strip():
            return None
        raise _CensusStop('git could not read the worktree: '
                          + done.stderr.decode('utf-8', 'replace').strip()[-200:])
    return done.stdout.decode('utf-8', 'surrogateescape')


def _census_negations(top, folder, personal=None):
    """Whether a negation pattern (`!keep.txt`) of an ignore file could match `folder`, a folder of
    the worktree `top` named relative to it, or anything inside it. Git never re-includes a path
    under a folder it excludes, and never reads an ignore file inside one, so it reports `out/`
    whole beside `!out/keep.txt`; but the file says that path is not to be ignored, and so the
    folder is not shown to be build output. Three places are read, committed or not, tracked or not,
    because a negation only ever keeps: every .gitignore on disk from the folder's own directory up
    to the top, the repository's own exclude file `personal` (info/exclude, whose patterns are
    relative to the top), and every .gitignore inside the folder at any depth. The match is wider
    than git's (a star crosses a slash, a pattern with a backslash matches everything, a pattern
    with no slash is tried on every name in the folder wherever its file lies), and wider is the
    safe side. Raises OSError when an ignore file or the folder cannot be read; the caller takes
    that for work."""
    names, anchored = [], []

    def negations(file, place):
        # the negation patterns of one ignore file whose patterns are relative to `place`; True
        # when one of them is an escape this reader does not follow, which could name anything
        try:
            with open(file, 'rb') as handle:
                lines = handle.read().decode('utf-8', 'surrogateescape').splitlines()
        except (FileNotFoundError, NotADirectoryError):
            return False
        for line in lines:
            if not line.startswith('!'):
                continue
            pattern = line[1:].rstrip(' \t\r').rstrip('/')
            if not pattern:
                continue
            if '\\' in pattern:
                return True
            if '/' not in pattern:
                names.append(pattern)
                continue
            pattern = pattern.lstrip('/').replace('**/', '*').replace('/**', '/*')
            pattern = (place + '/' if place else '') + pattern
            fixed = re.split(r'[*?\[]', pattern, maxsplit=1)[0]
            if fixed.startswith(folder + '/') or (folder + '/').startswith(fixed) or fixed == folder:
                anchored.append(pattern)
        return False

    def unread(error):
        raise error

    places = [os.path.dirname(folder)]
    while places[-1]:
        places.append(os.path.dirname(places[-1]))
    for place in places:
        if negations(os.path.join(top, place, '.gitignore'), place):
            return True
    if personal is not None and negations(personal, ''):
        return True
    paths = [folder]
    for found, folders, files in os.walk(os.path.join(top, folder), onerror=unread):
        inside = os.path.relpath(found, top)
        paths.extend(os.path.join(inside, name) for name in folders + files)
        if '.gitignore' in folders + files and negations(os.path.join(found, '.gitignore'), inside):
            return True
    return any(fnmatch.fnmatchcase(os.path.basename(path), pattern) for path in paths for pattern in names) \
        or any(fnmatch.fnmatchcase(path, pattern) for path in paths for pattern in anchored)


def census_read(where, adopted=False, patterns=(), keep=(), start=None):
    """What a run left in the worktree `where`, as git reads it now with every ignored path:
    {build: [folder], kept: [folder], work: [path]}, each relative to the worktree.

    build names every ignored folder git reports as a whole, at any depth and whatever its name,
    that a committed ignore file of the worktree or a pattern the project declares covers. An ignore
    file is the project's when the commit the worktree was recorded as started from (`start`) holds
    it, the worktree's HEAD holds that very content, and so does the file on disk: a rule the run
    added, committed on its own branch or not, covers nothing, so a run that ignores its own results
    folder does not turn it into build output. A worktree with no recorded start commit gets the
    declared patterns only. A per-directory ignore file covers only what lies in its own directory:
    a file git applied from anywhere else (a personal excludes file that happens to be committed)
    covers nothing. And a folder that a negation pattern could reach into is work, whole, whether
    the pattern is in an ignore file above the folder, in info/exclude or in an ignore file inside
    the folder (_census_negations). In a worktree reconcile adopted,
    whose history nobody saw, the ignore files prove nothing and only the declared patterns count.
    kept names the folders a keep entry of the project holds: the entry itself, anything inside it,
    and a folder the entry lies in. They are left out.

    work names everything else that is in no commit and is not build output, and so is unique work
    (design 0.1): an untracked path git does not ignore, an ignored folder that neither a committed
    ignore file nor a declared pattern covers (one only info/exclude ignores, one whose rule cannot
    be traced), and a loose ignored file outside every build output folder. None of them is ever
    recorded as an item. Raises _CensusStop when git cannot say."""
    top = _census_git(where, 'rev-parse', '--show-toplevel').rstrip('\n')
    if os.path.realpath(top) != os.path.realpath(where):
        raise _CensusStop('the folder is not the top of a work tree')
    entries = _census_git(where, 'status', '--porcelain=v1', '-z', '--ignored=matching',
                          '--untracked-files=all').split('\0')[:-1]
    untracked, ignored = [], []
    while entries:
        entry = entries.pop(0)
        state, name = entry[:2], entry[3:]
        if 'R' in state or 'C' in state:
            entries.pop(0)  # the name it was renamed or copied from
        if state == '!!':
            ignored.append(name)
        elif state == '??':
            untracked.append(name)
    folders = [name for name in ignored if name.endswith('/')]
    work = untracked + [name for name in ignored if not name.endswith('/')]  # a loose ignored file is work
    build, kept = [], []
    source, committed, personal = {}, set(), None
    if folders:
        # the repository's own exclude file; a linked worktree reads the one of the common directory
        personal = os.path.join(top, _census_git(where, 'rev-parse', '--git-path', 'info/exclude').rstrip('\n'))
        rules = _census_git(where, 'check-ignore', '-v', '-z', '--stdin',
                            feed=b''.join(os.fsencode(name) + b'\0' for name in folders)).split('\0')[:-1]
        source = {rules[at + 3]: rules[at] for at in range(0, len(rules) - 3, 4)}
        if not adopted and isinstance(start, str) and SPACE_COMMIT.match(start):
            for found in sorted(set(source.values())):
                if os.path.isabs(found) or os.path.basename(found) != '.gitignore':
                    continue  # info/exclude, or a file outside the worktree: a personal rule
                began = _census_git(where, 'rev-parse', '--verify', '--quiet', start + ':' + found, absent=True)
                held = _census_git(where, 'rev-parse', '--verify', '--quiet', 'HEAD:' + found, absent=True)
                if (began is not None and held is not None and began.strip() == held.strip()
                        and held.strip() == _census_git(where, 'hash-object', '--', found).strip()):
                    committed.add(found)
    for folder in folders:
        inside = folder.rstrip('/')
        rule = source.get(folder)
        # a per-directory ignore file reaches only into its own directory
        placed = rule in committed and (os.path.dirname(rule) == ''
                                        or inside.startswith(os.path.dirname(rule) + '/'))
        if any(inside == entry or inside.startswith(entry + '/') or entry.startswith(inside + '/')
               for entry in keep):
            kept.append(inside)
        elif placed or any(
                fnmatch.fnmatchcase(os.path.basename(inside), pattern) for pattern in patterns):
            try:
                negated = _census_negations(top, inside, personal)
            except (OSError, ValueError):
                negated = True  # what could not be read is not shown to be build output
            if negated:
                work.append(folder)
            else:
                build.append(inside)
        else:
            work.append(folder)
    return {'build': sorted(build), 'kept': sorted(kept), 'work': sorted(set(work))}


def _space_live(ledger):
    """The live items of the ledger that have an owner, by the path each is at."""
    return {record['locator']['path']: (identity, record) for identity, record in sorted(ledger.items().items())
            if record.get('state') not in SPACE_ENDED and (record.get('locator') or {}).get('path')
            and record.get('owner') is not None}


def _space_project(ledger, owner):
    """What the project that owns an item declares, or nothing for an owner that is no project."""
    scope = (owner or {}).get('scope') or {}
    for project in ledger.projects:
        if scope.get('type') == 'project' and project.get('project') == scope.get('id'):
            return project
    return {}


def space_census(space, worktree, event, owner=None, also=()):
    """VELDO-0305: the census of a run's worktree at one of the run's events, before Signal (design
    6.3). Every ignored folder git reports in the worktree that a committed ignore file of the project
    or a declared pattern covers (census_read) becomes a build output item inside the worktree's item:
    declared by the census, confirmed, and measured. Then the sizes are written with `event`: each
    build output, the worktree without them, and each folder of `also` (the run's scratch root and
    build root) that a live item records.

    `space` is the mapping space_signal is given; `owner` is the owner a new item gets (the run's),
    and the worktree's own owner when none is given. The answer is {worktree, event, declared, items,
    kept, work, sizes, refused, refusal}: the worktree's item, the items declared now, {path: item}
    of every build output, the folders a keep entry held back, the paths that are unique work, {item:
    bytes} as written, {path: reason} of what the ledger refused, and the reason nothing was read.

    Work is never recorded: an untracked path git does not ignore, an ignored path nothing of the
    project covers and a loose ignored file get no item, so nothing ever removes them as build output,
    and they keep the worktree as unique work (section 7, rule 5 and the remover's last look). A
    worktree no live item records gets nothing (not_in_ledger). Whatever cannot be read records
    nothing, and nothing here raises or deletes."""
    answer = {'worktree': None, 'event': event, 'declared': [], 'items': {}, 'kept': [], 'work': [],
              'sizes': {}, 'refused': {}, 'refusal': None}
    try:
        ledger = space['ledger']
        where = os.path.normpath(str(worktree))
        live = _space_live(ledger)
        held = live.get(where)
        if held is None or held[1].get('kind') not in SPACE_WORKTREES:
            answer['refusal'] = 'not_in_ledger'
            return answer
        identity, record = held
        answer['worktree'] = identity
        project = _space_project(ledger, record.get('owner'))
        read = census_read(where, adopted=bool(record.get('adopted')),
                           patterns=project.get('build_output') or (), keep=project.get('keep') or (),
                           start=record.get('start'))
        answer['kept'], answer['work'] = read['kept'], read['work']
        for inside in read['build']:
            path = os.path.join(where, inside)
            known = live.get(path)
            if known is None:
                made = ledger.declare('build_output', {'path': path}, owner or record['owner'], 'census',
                                      parent=identity)
                if made.get('ok'):
                    made = dict(ledger.confirm(made['item']), item=made['item'])
                if not made.get('ok'):
                    answer['refused'][inside] = str(made.get('reason'))
                    continue
                answer['declared'].append(made['item'])
                answer['items'][path] = made['item']
            elif known[1].get('kind') == 'build_output':
                answer['items'][path] = known[0]
        if 'measure' not in _SPACE:
            _SPACE['measure'] = _organ('control_space_remove').measure
        outputs = 0
        for path, item in sorted(answer['items'].items()):
            try:
                size = _SPACE['measure'](path)
            except Exception:  # noqa: BLE001 - a folder that cannot be measured has no size written
                continue
            outputs += size
            if ledger.measure(item, size, event).get('ok'):
                answer['sizes'][item] = size
        measured = [(where, identity)] + [(os.path.normpath(str(path)), live[os.path.normpath(str(path))][0])
                                          for path in also if os.path.normpath(str(path)) in live]
        for path, item in measured:
            try:
                size = _SPACE['measure'](path) - (outputs if path == where else 0)
            except Exception:  # noqa: BLE001
                continue
            if ledger.measure(item, max(0, size), event).get('ok'):
                answer['sizes'][item] = max(0, size)
    except Exception as error:  # noqa: BLE001 - a census that could not read records nothing more
        answer['refusal'] = 'census_failed'
        answer['said'] = '%s: %s' % (type(error).__name__, str(error)[:300])
    return answer


SPACE_VERDICT = 'verdict_recorded'  # the event a review run's folders wait for (VELDO-0337)
SPACE_VERDICT_STATIONS = ('review',)  # the stations whose run ends with a verdict the floor records


# The kind a review run's own folder is declared with, for the kind every other run's has (VELDO-0337).
SPACE_REVIEW_KINDS = {'scratch': 'review_run_scratch', 'build_output': 'review_run_build_output'}


def space_kind(kind, owner):
    """VELDO-0337: the kind a run's own folder is declared with. Declare takes no end list: an item's end
    events come from its kind in the kind registry alone (design 4.1, 6.1; the lead's decision at
    assembly, as VELDO-0324 decided). A review run's scratch folder and build root are still read while
    its verdict is validated and signed, after its receiver has ended, so they are declared with the
    kinds review_run_scratch and review_run_build_output, which end at verdict recorded, ticket ended
    and project ended and never at run finished. The one writer of the verdict sends verdict recorded
    after its commit (dispatch.py, FloorAuthority.record_review). Run finished then neither names nor
    matches them, from the receiver, a sweep or a retry. A review that ends with no verdict leaves them
    for ticket ended or project ended. Every other run's folders keep their kind."""
    run = (owner or {}).get('run')
    station = run.get('station') if isinstance(run, dict) else None
    if station not in SPACE_VERDICT_STATIONS:
        return kind
    return SPACE_REVIEW_KINDS.get(kind, kind)


def space_run_folders(space, worktree, dispatch_id, station, taken=(), confined=False, run=None):
    """VELDO-0305 AC3: the folders a run is given, each declared in the ledger before it is made and
    before the worker starts: the run's temporary folder, a scratch item under the installation's first
    scratch root, and, for a project that declares build variables, the build root, a build output item
    under the installation's first build root, named after the worktree. Both are owned by the run
    (the worktree's scope and ticket, the run with its station), and a review run's are declared with
    the review run kinds, which end at verdict recorded and never at run finished (space_kind,
    VELDO-0337). The answer is {worktree, item, owner,
    scratch, build, items, environment, refusal, detail}; environment is what the worker is given:
    the temporary folder variable at the scratch folder and each declared build variable at the
    build root. A variable is in it only when its folder has a live item.

    The temporary folder is <first scratch root>/run-scratch/<the dispatch's digest>: a name of its
    own, never the one the run directories are under, and a folder that is, holds or lies in the run
    directory `run` (its generated configuration and its token) is refused as SPACE_RUN_DIRECTORY.

    Declare, make, confirm, in that order (design 6.2). A folder that is already there with no live
    item is never taken over: whatever is in it was not made by this run. That, and a folder a live
    item records as something else, is a state of the path and not of the ledger: the refusal is
    SPACE_UNRECORDED or SPACE_OTHERWISE, and the detail names the folder. The build root of a worktree
    passes from one run of the worktree to the next, so one a live build output item records is used
    as it is. A worktree no live item records, and a station the ledger has no run for, are given
    nothing and the environment stays as it was (detail says which). So is a run in the confined
    runner (`confined`), which has a temporary folder of its own and may write nowhere outside its
    worktree: it gets its owner, for the census, and no folder. A ledger that refuses or cannot
    be reached, a folder that cannot be made, and a build variable that names a variable of the
    launch (`taken`, the reserved names, a factory name) refuse the launch: nothing is pointed at a
    folder the ledger does not record."""
    where = os.path.normpath(str(worktree))
    out = {'worktree': where, 'item': None, 'owner': None, 'scratch': None, 'build': None, 'items': {},
           'environment': {}, 'refusal': None, 'detail': None}
    try:
        ledger = space['ledger']
        if station not in SPACE_STATIONS:
            return dict(out, detail='station')
        live = _space_live(ledger)
        held = live.get(where)
        if held is None or held[1].get('kind') not in SPACE_WORKTREES:
            return dict(out, detail='not_in_ledger')
        out['item'] = held[0]
        base = held[1]['owner']
        owner = {'scope': dict(base['scope']), 'run': {'id': dispatch_id, 'station': station}}
        if base.get('ticket'):
            owner['ticket'] = base['ticket']
        out['owner'] = owner
        if confined:
            return dict(out, detail='confined_runner')
        variables = list(_space_project(ledger, base).get('build_variables') or ())
        for name in variables:
            if (name == SPACE_TEMPORARY or name in ENGINE_RESERVED or name in taken
                    or name.startswith((FACTORY_PREFIX,) + SESSION_PREFIXES)):
                return dict(out, refusal='invalid_input:space_build_variable:' + name,
                            detail='a build variable names a variable of the launch')
        wanted = [('scratch', 'scratch', (ledger.config['scratch_roots']['roots'] or [None])[0],
                   lambda root: run_directory(os.path.join(root, SPACE_RUN_SCRATCH), dispatch_id))]
        if variables:
            wanted.append(('build', 'build_output', (ledger.config['build_roots'] or [None])[0],
                           lambda root: os.path.join(root, '%s-%s' % (
                               os.path.basename(where), hashlib.sha256(where.encode()).hexdigest()[:12]))))
        for name, kind, root, place in wanted:
            if not root:
                return dict(out, refusal=SPACE_UNAVAILABLE, detail='the installation names no %s root' % name)
            path = os.path.normpath(place(str(root)))
            if run:
                own, given = os.path.realpath(str(run)), os.path.realpath(path)
                if own == given or own.startswith(given + os.sep) or given.startswith(own + os.sep):
                    return dict(out, refusal=SPACE_RUN_DIRECTORY,
                                detail='the %s folder %s and the run directory %s are not apart'
                                       % (name, path, os.path.normpath(str(run))))
            known = live.get(path)
            # VELDO-0337: a review run's folder has a kind of its own. The build root passes from run to
            # run of the worktree as it is, whichever of the two build kinds it was declared with.
            declared_as = space_kind(kind, owner)
            if known is not None:
                mine = (known[1]['owner'].get('run') or {}).get('id') == dispatch_id
                if (known[1].get('kind') not in (kind, SPACE_REVIEW_KINDS[kind]) or (name == 'scratch' and not mine)
                        or known[1]['owner'].get('scope') != owner['scope']
                        or os.path.islink(path) or not os.path.isdir(path)):
                    return dict(out, refusal=SPACE_OTHERWISE,
                                detail='the %s folder %s is recorded as something else: %s'
                                       % (name, path, known[0]))
                out[name], out['items'][path] = path, known[0]
                continue
            if os.path.lexists(path):
                return dict(out, refusal=SPACE_UNRECORDED,
                            detail='the %s folder %s is there and no item records it' % (name, path))
            # VELDO-0337: a review run's folders are declared with the review run kinds, which end at its
            # verdict, never at run finished.
            made = ledger.declare(declared_as, {'path': path}, owner, 'seam')
            if not made.get('ok'):
                return dict(out, refusal=SPACE_UNAVAILABLE,
                            detail='declare refused: %s' % (made.get('reason'),))
            out['items'][path] = made['item']
            try:
                os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
                os.mkdir(path, 0o700)
            except OSError as error:
                if space_absent(path):
                    ledger.gone(made['item'])  # the creation failed and nothing is there (design 6.2)
                return dict(out, refusal=SPACE_UNAVAILABLE,
                            detail='the %s folder could not be made: %s' % (name, type(error).__name__))
            confirmed = ledger.confirm(made['item'])
            if not confirmed.get('ok'):
                return dict(out, refusal=SPACE_UNAVAILABLE,
                            detail='confirm refused: %s' % (confirmed.get('reason'),))
            out[name] = path
        out['environment'][SPACE_TEMPORARY] = out['scratch']
        for name in variables:
            out['environment'][name] = out['build']
    except Exception as error:  # noqa: BLE001 - a ledger that cannot be reached gives the run nothing
        return dict(out, environment={}, refusal=SPACE_UNAVAILABLE,
                    detail='%s: %s' % (type(error).__name__, str(error)[:300]))
    return out


def space_environment(environment, values):
    """`environment` with the run's space values set. An engine launch's environment is stripped by
    the trusted wrapper at the exec (engine_environment), the temporary folder variable included, and
    only what ENGINE_OVERRIDES carries is installed again: so the values are written there too."""
    environment = dict(environment)
    environment.update(values)
    if values and ENGINE_OVERRIDES in environment:
        own = json.loads(environment[ENGINE_OVERRIDES])
        own.update(values)
        environment[ENGINE_OVERRIDES] = json.dumps(own, sort_keys=True)
    return environment


def clone_users(clones, dispatches, dispatch_id, space=None):
    """VELDO-0303: the other users of the clone the dispatch `dispatch_id` uses that have not ended, read
    before run finished is signalled for that dispatch's run directory. The event ends every item the run
    owns, and a clone may be among them; a consumer attached to it that has no process at this moment is
    seen by no rule, so the clone would go under it. `clones` is the clone provisioner, or the receiver
    configuration's clones section (the arguments of control_clone.Clones), or None for an installation
    without clones. Returns
    their dispatch identities, in order; a clone that cannot be read answers with the word unread, for
    what cannot be read is in use."""
    if not clones:
        return []
    try:
        provisioner = (_organ('control_clone').Clones(dispatches, space=space, **clones)
                       if isinstance(clones, dict) else clones)
        handle = provisioner.clone_of(dispatch_id)
        manifest = provisioner._manifest(handle.env_id) if handle is not None else None
        if manifest is None:
            return []
        return sorted(user['dispatch_id'] for user in manifest['users'] if user['dispatch_id'] != dispatch_id
                      and not provisioner.user_state(user, manifest['root'])['ended'])
    except Exception:  # noqa: BLE001 - a clone that cannot be read is not ended under its users
        return ['unread']


def runs_root(config):
    """Where a receiver configuration keeps its runs' own directories (VELDO-0155, VELDO-0156): its `runs`, else the
    factory state root's runs, else beside the store."""
    return config.get('runs') or (os.path.join(config['state_root'], 'runs') if config.get('state_root')
                                  else os.path.join(os.path.dirname(config['store']), 'runs'))


def run_directory(runs, dispatch_id):
    """The one directory of a dispatch's run under `runs`, derived from its dispatch identity."""
    return os.path.join(runs, hashlib.sha256(dispatch_id.encode()).hexdigest()[:32])


def engine_environment(environment):
    """THE ENVIRONMENT STRIP: an engine launch's environment (one naming ENGINE_RUNTIME) without the SSH agent,
    the session bus and the Git tokens, and with XDG_RUNTIME_DIR the run's own empty runtime directory, never
    the receiver's. VELDO-0165 also removes every session-prefixed name, then installs only the qualified
    adapter, baseline and account values the receiver carried in ENGINE_OVERRIDES. Other launches are unchanged."""
    environment = _organ('control_git_identity').environment(environment)
    runtime = environment.pop(ENGINE_RUNTIME, None)
    if runtime is None:
        return environment
    for name in list(environment):
        if name in EXEC_STRIPPED or name.startswith(SESSION_PREFIXES):
            environment.pop(name, None)
    handed = environment.pop('VELDO_MEMORY', None)
    environment.update({name: value for name, value in
                        json.loads(environment.pop(ENGINE_OVERRIDES, '{}')).items()
                        if not name.startswith('VELDO_') or name.startswith(DELIVERY_PREFIX)})
    if handed is not None:
        environment['VELDO_MEMORY'] = handed
    environment = _organ('control_git_identity').environment(environment)
    environment['XDG_RUNTIME_DIR'] = runtime
    return environment


def baseline_at(argv, bound, reported=False):
    """Where the engine's baseline options go in `argv`: right after its qualified flags (the argv
    pinned_argv_problem accepted), so an adapter's own trailing arguments stay last."""
    engine = engine_argv(argv, reported) or []
    at = 6 if entrance(engine) else 0
    return len(argv) - len(engine) + at + 1 + len(bound.get('flags') or [])


def engine_argv(argv, reported):
    """What the trusted wrapper execs: a local adapter's whole argv (the receiver starts the wrapper around
    it), a reported adapter's argv after its transport's wrapper (`control_launch.py exec`); None when a
    reported argv names no wrapper."""
    if not reported:
        return custody_worker(argv)
    for at in range(len(argv) - 2, -1, -1):
        if Path(argv[at]).name == WRAPPER_MODULE and argv[at + 1] == 'exec':
            return list(argv[at + 2:])
    return None


def custody_worker(argv):
    """Unwrap only this installation's custody wrapper, with this interpreter."""
    argv = list(argv)
    wrapper = str(Path(__file__).with_name('control_keys_custody.py').resolve())
    if (len(argv) > 6 and os.path.realpath(argv[0]) == os.path.realpath(sys.executable)
            and argv[1:4] == ['-B', wrapper, 'confine'] and '-' * 2 in argv[4:]):
        return argv[argv.index('-' * 2, 4) + 1:]
    return argv


def entrance(engine):
    """Whether an engine argv is the clone entrance's shape: `<python> -B control_clone.py enter <clones> --`
    and then what it execs."""
    return (len(engine) > 6 and engine[1] == '-B' and Path(engine[2]).name == ENTRANCE_MODULE and engine[3] == 'enter'
            and engine[5] == '--')


def pinned_argv_problem(argv, bound, reported=False):
    """None when the argv binds what runs: the engine argv (engine_argv) is the bound pinned path, or the
    clone entrance and then the pinned path, followed by its qualified flags; else the named refusal. A
    local adapter's entrance is the installed one beside this receiver, run by this receiver's own Python."""
    path, flags = bound.get('path'), list(bound.get('flags') or [])
    engine = engine_argv(argv, reported)
    if not isinstance(path, str) or not engine:
        return 'invalid_input:engine_executable'
    at = 0
    if entrance(engine):
        if not reported and Path(engine[2]).resolve() != Path(__file__).resolve().with_name(ENTRANCE_MODULE):
            return 'invalid_input:engine_entrance'
        if not reported and os.path.realpath(engine[0]) != os.path.realpath(sys.executable):
            return 'invalid_input:engine_interpreter'
        at = 6
    if engine[at] != path:
        return 'invalid_input:engine_executable'
    if engine[at + 1:at + 1 + len(flags)] != flags:
        return 'invalid_input:engine_flags'
    return None


def stat_regular(info):
    """Whether an lstat result is a regular file (not a link, a directory or a device)."""
    return (info.st_mode & 0o170000) == 0o100000


def file_digest(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return 'sha256:' + digest.hexdigest()


# The runner: decide, reserve, prepare the complete contract, then invoke the receiver.

def resolve_source(repository_path, revision):
    """The commit and tree `revision` names in a real Git repository."""
    _git_process = _organ('git_process')
    commit = _git_process.run(['git', '-C', str(repository_path), 'rev-parse', revision + '^{commit}'],
                              capture_output=True, text=True, timeout=20)
    tree = _git_process.run(['git', '-C', str(repository_path), 'rev-parse', revision + '^{tree}'],
                            capture_output=True, text=True, timeout=20)
    if commit.returncode or tree.returncode:
        raise D.Refused('invalid_input:source', 'the source revision does not resolve')
    return {'commit': commit.stdout.strip(), 'tree': tree.stdout.strip()}


def receiver_kind_problem(config, contract):
    """Refuse a repository contract at the conversation receiver, and the converse, before spawn."""
    configured = config.get('receiver_kind', 'project')
    offered = contract.get('subject_kind', 'project')
    return None if configured == offered else 'binding_mismatch:conversation_receiver'


class Runner:
    """The scheduler's side of every dispatch. `gate` is VELDO-0052's eligibility Gate, `reservations`
    VELDO-0036's service, `dispatches` a control_dispatch.Dispatches writing as the runner,
    `receiver(contract)` invokes the trusted receiver and returns its Launch, and `clones` is
    VELDO-0042's clone provisioner when dispatches use clones (its teardown retires their files).
    Every slot is returned through `retirements` (VELDO-0041): a refused retirement is kept pending
    and retried when what it waits on is completed, and `sweep()` retries every pending one that is
    due, before each preparation and after each wait. `runs` is where the receiver keeps each run's own
    directories (runs_root of its configuration) and `profile` this host's worker profile: a run whose receiver
    could not remove its directory (it died, or the run's group could not be emptied) has it removed here once
    the kernel shows nothing of the run left (VELDO-0158)."""

    def __init__(self, gate, reservations, dispatches, receiver, *, account, clock=None, clones=None, runs=None,
                 profile=None, space=None, admission=None):
        self.gate, self.reservations, self.dispatches = gate, reservations, dispatches
        # VELDO-0303: the installation's space ledger and what Signal is given (space_signal), or None where
        # the installation has none. With it, a leftover run directory goes through Signal and not by a delete here.
        self.space = space
        self.admission = admission
        self.receiver, self.account = receiver, account
        self.clock = clock or time.time
        self.observations = []
        self.launches = {}
        # VELDO-0154: dispatches whose receiver died, whose account slot waits for their worker to be gone.
        self.orphans = {}
        # VELDO-0158: settled dispatches whose run directory is left, by dispatch: {group, process}.
        self.runs, self.profile = runs, profile
        self.leftovers = {}
        self.clones = clones  # VELDO-0303: read before run finished, for a consumer of the run's clone
        # VELDO-0308 AC3: a pending retirement that is carried out retries its dispatch's deferred items.
        self.retirements = RT.Retirements(reservations, dispatches, clones=clones, clock=self.clock,
                                          observations=self.observations, deferred=self.retry_deferred)

    def retry_deferred(self, dispatch_id, but=()):
        """VELDO-0308 AC3: the retirement service's seam into Signal. When a pending retirement is carried out,
        the items of that dispatch's run the ledger holds deferred are judged again in that call (space_retry).
        With no ledger there is nothing to retry. The consumer first, as at every run finished: while another
        dispatch still uses the run's clone the event is not sent, since it would end the clone under it."""
        if self.space is None:
            return None
        users = clone_users(self.clones, self.dispatches, dispatch_id, self.space)
        if users:
            return {'retried': [], 'signals': 0, 'states': {}, 'raised': None, 'refusal': 'clone_in_use', 'users': users}
        # Rule 3 is answered here only on what is read now: the record has a known end and the kernel shows
        # the worker gone and its group empty. Anything else is left to the answer the installation wired in.
        try:
            record = self.dispatches.record(dispatch_id) or {}
            seen = C.retirement((self.retirements.entries.get(dispatch_id) or {}).get('group'), record.get('process'))
            ended = record.get('state') in RT.CONCLUSIVE and seen['terminated'] is True and seen['cleaned'] is True
        except Exception:  # noqa: BLE001 - a run that cannot be read is not known to have ended
            ended = False
        return space_retry(self.space, dispatch_id, 'runner.retirement', but=but, ended=ended)

    def _slot(self, dispatch_id):
        entity = RES_ENTITY(self.dispatches.domain, dispatch_id)
        row = self.dispatches.conn.execute('SELECT version, digest FROM entities WHERE id=?', (entity,)).fetchone()
        if row is None:
            raise D.Refused('missing_reservation', entity)
        return entity, row[0], row[1]

    def _retire(self, dispatch_id, outcome, basis):
        """Return an ended dispatch's worker slot through the retirement service (VELDO-0041), which
        keeps the dispatch, its reported containment group and every obligation still open until the
        slot is released once. The observation is the runner's own, read from the kernel now (VELDO-0040):
        a live worker or a populated group is refused (worker_alive, cleanup_incomplete) and keeps the
        slot, pending, until an obligation it waits on is completed and the retirement is retried. A
        dispatch the runner asked to stop is accounted as cancelled."""
        launch = self.launches.pop(dispatch_id, None)
        if launch is not None:
            self.retirements.track(dispatch_id, group=getattr(launch, 'group', None),
                                   stop_requested=getattr(launch, 'stop_requested', False),
                                   supervision=getattr(launch, 'supervision', None))
        record = self.dispatches.record(dispatch_id) or {}
        if record.get('state') == 'refused' and self.space is not None:
            bound = (record.get('contract') or {}).get('space')
            if bound:
                space_release(self.space, bound['hold'])
        return self.retirements.retire(dispatch_id, outcome, basis)

    def sweep(self):
        """Retry every pending retirement whose obligations have changed since its last attempt, or whose
        clone can now be removed (VELDO-0041); the dispatches whose slots it released. Each preparation
        and each wait makes one, and a scheduler may make one at any time. It also removes each run directory left
        behind whose run the kernel now shows gone (clear_runs), and first honors every owner's stop request the
        authority committed (honor_stops, VELDO-0131)."""
        self.honor_stops()
        self.clear_runs()
        return self.retirements.sweep()

    def honor_stops(self):
        """VELDO-0131: the existing stop mechanism, requested by the owner's committed stop command. For each
        dispatch of this domain and repository whose stop request waits (control_dispatch.request_stop), the
        Launch this runner holds asks its receiver to stop (Launch.stop: R44's cooperative stop, then the group's
        escalation), and the runner records what the ask returned (stop_result: asked true, or false when it
        holds no receiver of that dispatch to ask). Nothing is recovered, retried or restarted: the worker's end
        is recorded by its receiver as every end is. A request for a dispatch still running that this runner does
        not hold is left waiting: another runner on the same store may hold it and asks it on its own sweep. One
        whose dispatch has ended is recorded not asked, since no receiver is left to ask. The [(dispatch, asked)]
        it recorded, in order."""
        pending = getattr(self.dispatches, 'stop_requests', None)
        if pending is None:
            return []
        done = []
        for dispatch_id, reason in pending():
            launch = self.launches.get(dispatch_id)
            if launch is None and (self.dispatches.record(dispatch_id) or {}).get('state') in D.STOPPABLE:
                continue
            try:
                asked = bool(launch is not None and launch.stop(reason or 'owner_stop'))
            except Exception:  # noqa: BLE001 - a receiver that cannot be asked is recorded as not asked
                asked = False
            try:
                self.dispatches.stop_result(dispatch_id, asked, now=self.clock())
            except D.Refused as error:
                self.observations.append({'operation': 'stop_result', 'dispatch_id': dispatch_id, 'outcome': 'refused',
                                          'refusal': error.code, 'asked': asked})
                continue
            self.observations.append({'operation': 'stop_result', 'dispatch_id': dispatch_id, 'outcome': 'recorded',
                                      'asked': asked})
            done.append((dispatch_id, asked))
        return done

    def _left(self, dispatch_id, group=None, process=None):
        """A settled dispatch whose run directory its receiver may have left: removed once its run is gone."""
        if self.runs and os.path.lexists(run_directory(self.runs, dispatch_id)):
            self.leftovers[dispatch_id] = {'group': group, 'process': process}

    def _once(self, dispatch_id, observation):
        """VELDO-0308: record what a sweep found of the leftover `dispatch_id`, once for each outcome and
        refusal: a leftover that stays as it is adds one observation, and not one at every sweep. One
        that is no leftover (the start sweep's look) is recorded as it is found."""
        entry = self.leftovers.get(dispatch_id)
        if entry is not None:
            seen = entry.setdefault('observed', set())
            what = (observation.get('outcome'), observation.get('refusal'))
            if what in seen:
                return
            seen.add(what)
        self.observations.append(observation)

    def _handed_over(self, dispatch_id, place, at):
        """VELDO-0308: whether the space ledger already holds the run directory `place` (space_held), recorded
        as the observation remove_run with outcome handed_over when it does. True: the caller forgets the
        leftover and sends nothing. False: no ending event has reached it. None: the ledger could not be
        read, and the caller sends nothing and keeps what it knows."""
        try:
            held = space_held(self.space, place)
        except Exception as error:  # noqa: BLE001 - an unread ledger is never taken for "not held"
            self._once(dispatch_id, {'operation': 'remove_run', 'dispatch_id': dispatch_id, 'outcome': 'refused',
                                     'refusal': 'unavailable_service:space_ledger', 'at': at,
                                     'raised': '%s: %s' % (type(error).__name__, str(error)[:300])})
            return None
        if held is None:
            return False
        self.observations.append({'operation': 'remove_run', 'dispatch_id': dispatch_id, 'outcome': 'handed_over',
                                  'at': at, 'space': held})
        return True

    def clear_runs(self):
        """VELDO-0158: remove the run directory of every leftover dispatch whose run the kernel shows gone: its
        recorded process ended, its reported group empty or gone, and no live group of this profile's slice its
        scope. A run still alive, or one whose groups cannot be read, keeps its directory until a later call. The
        dispatches whose directories were removed, in order.

        VELDO-0308: with a space ledger a sweep is no retry. Run finished is sent for a leftover at most once,
        and only while no ending event has reached its run directory (the item is declared or present). A run
        directory the ledger already holds (due, deferred, removing or kept: the receiver, a teardown or an
        earlier sweep sent the event) is handed over: the leftover is dropped, nothing is sent, and the item
        waits for the ledger's own retries (design section 7, Retry). The event names exactly the run's own
        items, each at the version read (space_signal's `alone`), and never an item of a clone: a clone handed
        over is the ledger's, and one still live is its own teardown's, which names the clone's own items and
        nothing else of the owner. Neither holds the event back. A worktree or an agent repository of the run that
        is no clone's is named with the run's folders: run finished is its event too. A leftover that was sent its one
        event and is still there is recorded once (run_finished_sent) and forgotten: no sweep sends it
        another, so it is the ledger's and reconcile's. What a sweep finds of a leftover is recorded once
        for each outcome, never once at every sweep (_once). A ledger that cannot be read sends nothing and
        forgets nothing."""
        removed, live = [], None
        for dispatch_id, entry in sorted(self.leftovers.items()):
            seen = C.retirement(entry['group'], entry['process'])
            if not (seen['terminated'] and seen['cleaned']):
                continue
            if self.profile is not None:
                if live is None:
                    try:
                        status = C.status(self.profile)
                    except Exception:  # noqa: BLE001 - groups that cannot be read keep every directory
                        status = {'qualified': False}
                    live = {g['unit'] for g in status['groups']} if status['qualified'] else False
                if live is False or C.unit_name(dispatch_id) in live:
                    continue
            place = run_directory(self.runs, dispatch_id)
            if self.space is not None:
                # The consumer first: run finished never ends a clone another dispatch still uses.
                users = clone_users(self.clones, self.dispatches, dispatch_id, self.space)
                if users:
                    self._once(dispatch_id, {'operation': 'remove_run', 'dispatch_id': dispatch_id, 'outcome': 'refused',
                                             'refusal': 'clone_in_use', 'users': users})
                    continue
                # VELDO-0308: a run directory an ending event has reached is the ledger's, and no sweep's.
                handed = self._handed_over(dispatch_id, place, 'sweep')
                if handed is not False:
                    if handed:
                        del self.leftovers[dispatch_id]
                    continue
                if entry.get('sent'):
                    # Sent already: once. A live clone of the run does not hold the event back: it is never named.
                    self._once(dispatch_id, {'operation': 'remove_run', 'dispatch_id': dispatch_id, 'outcome': 'refused',
                                             'refusal': 'run_finished_sent', 'with': []})
                    del self.leftovers[dispatch_id]  # sent its one event: never a sweep's again
                    continue
                # VELDO-0303: the kernel test above is rule 3's answer for this run; the rest is Signal's.
                found = space_signal(self.space, 'run_finished', [place], 'runner.sweep', ended=True, clones=self.clones,
                                     alone=True)[os.path.normpath(place)]
                entry['sent'] = found.get('item') is not None
                if found['state'] in SPACE_HELD:
                    # The event reached it and a rule or the mode kept it: the ledger's from now on.
                    del self.leftovers[dispatch_id]
                    self.observations.append({'operation': 'remove_run', 'dispatch_id': dispatch_id,
                                              'outcome': 'handed_over', 'at': 'sweep', 'space': found})
                    continue
                if found['state'] not in SPACE_ENDED:
                    self._once(dispatch_id, {'operation': 'remove_run', 'dispatch_id': dispatch_id, 'outcome': 'refused',
                                             'refusal': space_refusal(found), 'space': found})
                    continue
            else:
                found = _organ('control_space_remove').remove_standalone(place, 'folder')
                if found['state'] not in SPACE_SAFE:
                    self.observations.append({'operation': 'remove_run', 'dispatch_id': dispatch_id, 'outcome': 'refused',
                                              'refusal': space_refusal(found), 'space': found})
                    continue
            if os.path.lexists(place):
                refused = {'operation': 'remove_run', 'dispatch_id': dispatch_id, 'outcome': 'refused'}
                if self.space is not None:
                    self._once(dispatch_id, refused)
                else:
                    self.observations.append(refused)
                continue
            del self.leftovers[dispatch_id]
            self.observations.append({'operation': 'remove_run', 'dispatch_id': dispatch_id, 'outcome': 'removed'})
            removed.append(dispatch_id)
        return removed

    def sweep_runs(self):
        """VELDO-0158: the start sweep. Every run directory under `runs` whose dispatch, of this Runner's domain and
        repository, is settled (exited, refused or unknown) is a leftover, and each whose run the kernel shows gone
        is removed now (clear_runs); one whose run is still alive is kept until a later sweep finds it gone. The
        dispatches whose directories were removed. VELDO-0308: with a space ledger a run directory the ledger
        already holds is no leftover, at start as at every sweep: a restart does not send its event again."""
        if not self.runs or not os.path.isdir(self.runs):
            return []
        present = set(os.listdir(self.runs))
        for (data,) in self.dispatches.conn.execute('SELECT data FROM entities WHERE kind=?', (D.RECORD_KIND,)):
            record = json.loads(data)
            contract = record.get('contract') or {}
            if (contract.get('domain') != self.dispatches.domain or contract.get('repository') != self.dispatches.repository
                    or record.get('state') not in ('exited', 'refused', 'unknown')
                    or not isinstance(record.get('dispatch_id'), str)):
                continue
            if os.path.basename(run_directory(self.runs, record['dispatch_id'])) in present:
                if self.space is not None and self._handed_over(
                        record['dispatch_id'], run_directory(self.runs, record['dispatch_id']), 'start'):
                    continue
                self._left(record['dispatch_id'], process=record.get('process'))
        return self.clear_runs()

    def prepare(self, unit, station, *, holder, source, revision, payload, adapter, configuration,
                deadline, context=None, exclude=()):
        """Decide, reserve and record the complete contract; nothing is invoked. Returns the contract. `exclude`
        names the accounts a login retry's pool passes over (VELDO-0185 AC4)."""
        # Pending retirements first: a slot whose obligations have since completed is released before
        # this preparation reserves another.
        self.sweep()
        now = self.clock()
        try:
            configuration = CFG.bind(self.dispatches.conn, self.dispatches.domain,
                                     self.dispatches.repository, configuration)
        except CFG.Refused as error:
            raise D.Refused(error.code) from None
        decided = dict(context or {}, holder=holder)
        decision = self.gate.require(station, unit, context=decided)
        held = self.dispatches.active(unit, station)
        if held:
            code = 'dispatch_outcome_unknown:' if held['state'] == 'unknown' else 'active_dispatch:'
            raise D.Refused(code + held['dispatch_id'], 'one active dispatch per unit and station')
        record = self.gate.unit_record(unit) or {}
        project = record.get('project')
        if not D._text(project):
            raise D.Refused('missing_authority:project', 'the unit has no accepted project')
        claim = None
        if station in D.CLAIMED_STATIONS and not decision['inputs'].get('team_assignment'):
            entity = D.CLM.claim_id(self.dispatches.repository, unit)
            row = self.dispatches.conn.execute('SELECT data FROM entities WHERE id=?', (entity,)).fetchone()
            data = json.loads(row[0]) if row else {}
            claim = {'entity': entity, 'holder': data.get('holder'), 'generation': data.get('generation')}
        attempt = self.dispatches.attempts(unit, station) + 1
        request = dict(repository=self.dispatches.repository, project=project, unit=unit,
                       station=station, attempt=attempt)
        admission = (self.admission(**request) if self.admission is not None
                     else ADMISSION.prepare(self.space, **request))
        if not admission.get('ok'):
            error = D.Refused(admission.get('code') or admission.get('reason') or 'space_admission_failed')
            error.numbers = admission.get('reason') if isinstance(admission.get('reason'), dict) else None
            raise error
        space = admission.get('space')
        dispatch_id = 'dispatch/%s/%s' % (unit, uuid.uuid4().hex)
        try:
            account = self.account
            if hasattr(account, 'reserve'):
                # VELDO-0160: an account pool (control_account_pool.Pool) chooses the account inside the slot's
                # reservation, reading the pool now: an account registered while work runs takes this dispatch.
                account = account.reserve(self.reservations, 'worker/' + dispatch_id, dispatch_id, project, unit,
                                          adapter=adapter, now=now, **({'exclude': list(exclude)} if exclude else {}))
            else:
                self.reservations.reserve_worker('worker/' + dispatch_id, dispatch_id, account, project, unit, now=now)
            entity, version, slot_digest = self._slot(dispatch_id)
            contract = {
                'schema': D.SCHEMA, 'dispatch_id': dispatch_id, 'domain': self.dispatches.domain,
                'repository': self.dispatches.repository, 'unit': unit, 'station': station,
                'attempt': attempt,
                'source': dict(resolve_source(source, revision), repository_uuid=self.dispatches.repository),
                'input': {'decision': {k: decision[k] for k in ('decision_id', 'station', 'unit', 'domain_uuid',
                                                                'watermark', 'inputs')},
                          'context': decided, 'payload': payload, 'payload_digest': D.digest(payload)},
                'capability': {'adapter': adapter, 'configuration': configuration,
                               'configuration_digest': D.digest(configuration)},
                'reservation': {'entity': entity, 'version': version, 'digest': slot_digest,
                                'account': account, 'project': project},
                'claim': claim, 'deadline': deadline, 'authority_generation': self.dispatches.generation,
                'space': space,
            }
            self.dispatches.prepare(contract, now=now)
        except BaseException:
            active = self.dispatches.active(unit, station)
            promised = ((active or {}).get('contract') or {}).get('space')
            if space is not None and promised != space:
                space_release(self.space, space['hold'])
            self._retire(dispatch_id, 'cancelled', 'never_spawned')
            raise
        return contract

    def prepare_conversation(self, conversation, sequence, *, intake_digest, payload, adapter, configuration,
                             role_revision, deadline, exclude=()):
        """Prepare one repository-free conversation turn on the shared account pool.

        The conversation authority has already checked the owner and waiting turn.  This method takes
        the account slot and records a VELDO-0039 contract before the Line changes that turn to
        dispatched or invokes the receiver.
        """
        self.sweep()
        now = self.clock()
        held = self.dispatches.active(conversation, 'turn')
        if held:
            recovered = False
            if held['state'] == 'unknown':
                row = self.dispatches.conn.execute(
                    'SELECT data FROM entities WHERE kind=?', ('conversation_turn',)).fetchall()
                recovered = any((turn := json.loads(raw)).get('dispatch_id') == held['dispatch_id']
                                and turn.get('state') == 'ended' and turn.get('outcome') == 'outcome_unknown'
                                for (raw,) in row)
                recovered = recovered and bool((self.reservations.worker(held['dispatch_id']) or {}).get('account_released'))
            if not recovered:
                code = 'dispatch_outcome_unknown:' if held['state'] == 'unknown' else 'active_dispatch:'
                raise D.Refused(code + held['dispatch_id'], 'one active turn per conversation')
        dispatch_id = 'dispatch/%s/%s' % (conversation, uuid.uuid4().hex)
        account = self.account.reserve(self.reservations, 'worker/' + dispatch_id, dispatch_id, None, conversation,
                                       adapter=adapter, now=now,
                                       **({'exclude': list(exclude)} if exclude else {}))
        try:
            entity, version, slot_digest = self._slot(dispatch_id)
            records = self.reservations._records()
            context = self.reservations.worker(dispatch_id)['context']
            for policy in self.reservations._policies(context, records):
                cap = policy['caps'].get('wall_seconds')
                if cap is not None:
                    remaining = cap - self.reservations.balances(policy['scope'], policy['subject'], records)['wall_seconds']
                    if remaining <= 0:
                        raise D.RES.Refused('usage_cap:' + policy['scope'] + ':wall_seconds')
                    deadline = min(deadline, now + remaining)
            decision = {'decision_id': 'conversation/%s/%d' % (conversation, sequence), 'station': 'turn',
                        'unit': conversation, 'domain_uuid': self.dispatches.domain, 'watermark': sequence,
                        'inputs': {'conversation': conversation, 'turn': sequence}}
            accepted = copy.deepcopy(role_revision)
            accepted['native_tools'] = [item['name'] for item in role_revision['native_tools']
                                        if item['load'] == 'always']
            bound = {'role_revision': accepted,
                     'mcp': [{key: item[key] for key in ('server', 'revision')}
                             for item in role_revision['mcp'] if item['load'] == 'always']}
            contract = {'schema': D.SCHEMA, 'subject_kind': 'conversation', 'dispatch_id': dispatch_id,
                        'domain': self.dispatches.domain, 'repository': None, 'unit': conversation, 'station': 'turn',
                        'attempt': self.dispatches.attempts(conversation, 'turn') + 1,
                        'source': {'conversation': conversation, 'turn': sequence, 'intake_digest': intake_digest},
                        'input': {'decision': decision, 'context': {'owner': payload.get('owner')},
                                  'payload': payload, 'payload_digest': D.digest(payload)},
                        'capability': {'adapter': adapter, 'configuration': bound,
                                       'configuration_digest': D.digest(bound)},
                        'reservation': {'entity': entity, 'version': version, 'digest': slot_digest,
                                        'account': account, 'project': None},
                        'claim': None, 'deadline': deadline, 'authority_generation': self.dispatches.generation,
                        'space': None}
            self.dispatches.prepare(contract, now=now)
        except BaseException:
            self._retire(dispatch_id, 'cancelled', 'never_spawned')
            raise
        return contract

    def launch_prepared(self, contract):
        """Invoke a contract already prepared by prepare_conversation."""
        launch = self.receiver(contract)
        self.launches[contract['dispatch_id']] = launch
        if launch.owned and (launch.record or {}).get('state') == 'refused':
            self._retire(contract['dispatch_id'], 'cancelled', 'never_spawned')
        return launch

    def cancel_prepared(self, contract, refusal):
        record = self.dispatches.record(contract['dispatch_id']) or {}
        if record.get('state') == 'prepared':
            self.dispatches.refuse(contract['dispatch_id'], record['contract_digest'], refusal,
                                   now=self.clock(), expected_state='prepared')
        self._retire(contract['dispatch_id'], 'cancelled', 'never_spawned')

    def submit(self, unit, station, **kwargs):
        """Prepare the complete contract, then invoke the receiver: the one launch path."""
        contract = self.prepare(unit, station, **kwargs)
        launch = self.receiver(contract)
        self.launches[contract['dispatch_id']] = launch
        if launch.owned and (launch.record or {}).get('state') == 'refused':
            self._retire(contract['dispatch_id'], 'cancelled', 'never_spawned')
        return launch

    def wait(self, launch, timeout=None):
        """Wait for the launched dispatch's terminal record; a conclusive end returns its slot."""
        record = launch.wait(timeout)
        if record and record['state'] == 'exited':
            # The one completion gate (control_dispatch.completed): the exit record's clean exit and, for an
            # engine, the complete artifact it binds (THE ENGINE PROTOCOL).
            clean = D.completed(record)
            if self.space is not None:
                # VELDO-0308: a run directory its receiver sent nothing for (a group it could not read, a work
                # tree of the same owner elsewhere) is the sweep's: it reads the kernel again (clear_runs).
                self._left(record['dispatch_id'], getattr(launch, 'group', None), record.get('process'))
            self._retire(record['dispatch_id'], 'completed' if clean else 'failed', 'worker_reaped')
        elif record and record['state'] == 'unknown':
            # Its outcome is an open obligation: the retirement keeps it, and the slot, until it is known. Its run
            # directory, which a receiver keeps while the run's group is not empty, goes once the run is gone.
            self._left(record['dispatch_id'], getattr(launch, 'group', None), record.get('process'))
            self._retire(record['dispatch_id'], 'unknown', 'outcome_unknown')
        self.launches.pop(launch.dispatch_id, None)
        # This dispatch's end may have completed another's obligation (a group the kernel emptied).
        self.sweep()
        return record

    def orphaned(self, launch):
        """VELDO-0154 AC2: the receiver of a running dispatch died before it reported the run's end (its launch pipe
        reached its end of file), and `wait` has recorded the run `outcome_unknown` under its original dispatch. The
        worker slot stays held with its outcome open and its usage reservation retained (VELDO-0041: an unknown
        outcome is never retired), but the ACCOUNT SLOT is freed for the next dispatch once nothing of the run is
        left: the stop the dead receiver owed is made here (its reported containment group killed, or the worker's
        recorded process, checked by its identity on this boot, sent SIGKILL), and the release is the reservation
        service's `release_account` over the runner's own kernel observation. A release that cannot be made yet
        stays pending in `orphans` and is tried again by `release_orphans`. Returns what `release_orphans` returns."""
        record = self.dispatches.record(launch.dispatch_id) or {}
        if record.get('state') == 'unknown':
            entry = self.retirements.entries.get(launch.dispatch_id) or {}
            self.orphans[launch.dispatch_id] = {'group': getattr(launch, 'group', None) or entry.get('group'),
                                                'process': record.get('process'), 'stopped': False}
            self._left(launch.dispatch_id, self.orphans[launch.dispatch_id]['group'], record.get('process'))
        return self.release_orphans()

    def release_orphans(self):
        """Free the account slot of every dispatch in `orphans` whose worker the kernel now shows gone; the
        released dispatches, in order. A refused release keeps its dispatch pending, named in the observations."""
        released = []
        for dispatch_id, entry in sorted(self.orphans.items()):
            if not entry['stopped']:
                entry['stopped'] = True
                _stop_orphan(entry['group'], entry['process'])
            end = time.monotonic() + ORPHAN_SECONDS
            seen = C.retirement(entry['group'], entry['process'])
            while not (seen['terminated'] and seen['cleaned']) and time.monotonic() < end:
                time.sleep(0.02)
                seen = C.retirement(entry['group'], entry['process'])

            def lifecycle(_dispatch, seen=seen, dispatch_id=dispatch_id):
                state = (self.dispatches.record(dispatch_id) or {}).get('state')
                return dict(seen, state=state, observer=RT.OBSERVER, basis='receiver_lost')
            event = {'operation': 'release_account', 'dispatch_id': dispatch_id, 'request': 'release-account/' + dispatch_id}
            try:
                self.reservations.release_account('release-account/' + dispatch_id, dispatch_id, lifecycle,
                                                  now=self.clock())
            except Exception as error:  # noqa: BLE001 - a refused release keeps the account slot held, by name
                self.observations.append(dict(event, outcome='refused', refusal=getattr(error, 'code', None)
                                              or type(error).__name__))
                continue
            del self.orphans[dispatch_id]
            self.observations.append(dict(event, outcome='released'))
            released.append(dispatch_id)
        # VELDO-0158: a dead receiver removed no run directory; each goes once the kernel shows its run gone.
        self.clear_runs()
        return released


# VELDO-0154: how long the runner waits for the kernel to show an orphaned worker gone after its stop.
ORPHAN_SECONDS = 5.0


def stop_requester(runner):
    """VELDO-0131: an in-process stop of one dispatch through the runner that holds its receiver, as
    control_project.runner_stop asks it: True when that Launch asked its receiver to stop."""
    def stop(dispatch_id, reason):
        launch = runner.launches.get(dispatch_id)
        return bool(launch is not None and launch.stop(reason))
    return stop


def _stop_orphan(group, process):
    """The stop a dead receiver owed its worker: its containment group killed at once (cgroup.kill), or, with no
    group, the recorded process sent SIGKILL through a descriptor of its own, only while its identity (pid, start
    time and boot id) still names it, so a reused pid is never signaled."""
    if isinstance(group, dict) and group.get('cgroup'):
        with contextlib.suppress(OSError):
            (C.CGROUP / group['cgroup'].lstrip('/') / 'cgroup.kill').write_text('1')
        return
    if not isinstance(process, dict) or not isinstance(process.get('pid'), int):
        return
    try:
        fd = os.pidfd_open(process['pid'])
    except OSError:
        return
    try:
        if C.alive(process):
            with contextlib.suppress(OSError):
                signal.pidfd_send_signal(fd, signal.SIGKILL)
    finally:
        os.close(fd)


def RES_ENTITY(domain, dispatch_id):
    return D.RES.entity('worker', [domain, dispatch_id])


# The runner-side end of the receiver's pipe.

class Launch:
    """One invocation of the receiver. `result` is accepted, refused or unknown, read from the record.
    `owned` is False when the receiver refused to launch a dispatch that was not prepared: that
    invocation launched nothing, owns nothing and never writes the record. `group` is the containment
    group the receiver reported (unit, slice and cgroup), `supervision` its account of how the worker
    and its group ended, `heartbeat` the interval and window it watches the worker's heartbeat with
    (VELDO-0041), and `stop()` asks it to stop the dispatch."""

    def __init__(self, child, contract, dispatches, clock, records=None):
        self.child, self.contract, self.dispatches, self.clock = child, contract, dispatches, clock
        self.dispatch_id = contract['dispatch_id']
        self.records = records
        self.pending = b''
        self.messages = []
        self.result = None
        self.refusal = None
        self.owned = True
        self.record = None
        self.group = None
        self.supervision = None
        self.stop_requested = False
        self.ends_by = None
        self.heartbeat = None
        self.artifact = None
        # VELDO-0154: the run's end seen on the launch pipe, and whether it was the pipe's end of file.
        self.ended = False
        self.lost = False
        # VELDO-0350: the receiver's exit status once it is reaped (None before, a negative number when a
        # signal ended it), whether a wait found its output at its end of file (as `lost` says for the pump),
        # and the file its standard error is written to, beside the run's execution record (None when none
        # could be opened).
        self.returncode = None
        self.closed = False
        self.receiver_log = None

    def stop(self, reason='requested'):
        """Ask the receiver to stop this dispatch: R44's cooperative stop, then the group's escalation.
        False when there is no receiver of this dispatch to ask."""
        if not self.owned or self.child is None or self.child.stdin is None:
            return False
        try:
            self.child.stdin.write((json.dumps({'stop': reason}) + '\n').encode())
            self.child.stdin.flush()
        except (OSError, ValueError):
            return False
        self.stop_requested = True
        return True

    def _message(self, deadline):
        if self.child is None:
            return None
        while b'\n' not in self.pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self.child.stdout], [], [], remaining)[0]:
                return None
            chunk = os.read(self.child.stdout.fileno(), 65536)
            if not chunk:
                self.closed = True
                return None
            self.pending += chunk
        return self._take()

    def fileno(self):
        """THE LAUNCH PIPE (VELDO-0154): the receiver's output, which a scheduler's service loop registers in its
        poll set while the dispatch runs; None once its end has been seen, or when no receiver of it runs."""
        if not self.owned or self.child is None or self.child.stdout is None or self.ended:
            return None
        return self.child.stdout.fileno()

    def pump(self, read=True):
        """What the launch pipe holds now, without waiting (VELDO-0154): each whole line already read is taken as
        `_message` takes it and, with `read`, one read of the pipe the poll set found readable. True once the run's
        end is seen: the receiver reported `exited` or `unknown`, or the pipe reached its end of file because the
        receiver ended without reporting either (`lost`, so its run is settled as the receiver's silence is)."""
        if self.ended or self.fileno() is None:
            return self.ended
        if read and b'\n' not in self.pending:
            chunk = os.read(self.child.stdout.fileno(), 65536)
            if not chunk:
                self.ended = self.lost = True
                return True
            self.pending += chunk
        while b'\n' in self.pending:
            message = self._take()
            if message.get('event') in ('exited', 'unknown'):
                self.ended = True
                return True
        return False

    def _take(self):
        line, _, self.pending = self.pending.partition(b'\n')
        try:
            message = json.loads(line)
        except ValueError:
            return {}
        self.messages.append(message)
        if not isinstance(message, dict):
            return {}
        if isinstance(message.get('group'), dict):
            self.group = message['group']
        if message.get('supervision') is not None:
            self.supervision = message['supervision']
        if isinstance(message.get('ends_by'), (int, float)):
            self.ends_by = message['ends_by']
        if isinstance(message.get('heartbeat'), dict):
            self.heartbeat = message['heartbeat']
        if message.get('event') == 'artifact' and isinstance(message.get('artifact'), dict):
            # The engine's artifact report {path, digest, verdict, complete} (THE ENGINE PROTOCOL).
            self.artifact = message['artifact']
        return message

    def _end_receiver(self):
        """Make the receiver's silence conclusive: it is stopped and reaped, so it writes no more."""
        if self.child is None:
            return
        if self.child.poll() is None and (self.closed or self.lost):
            # VELDO-0350: its output reached its end of file, so it is ending by itself: its own exit status
            # is waited for, briefly, before the kill that would replace it.
            with contextlib.suppress(subprocess.TimeoutExpired):
                self.child.wait(timeout=RECEIVER_EXIT_SECONDS)
        if self.child.poll() is None:
            self.child.kill()
        self.child.wait(timeout=10)
        self.returncode = self.child.returncode
        with contextlib.suppress(OSError, ValueError):
            if self.child.stdin is not None:
                self.child.stdin.close()

    def _record_commitment(self):
        """The receiver has been reaped. Bind its final bytes even when it could not report an end."""
        records = self.records
        if records is None:
            database = self.dispatches.conn.execute('PRAGMA database_list').fetchone()[2]
            records = ER.directory({'store': database})
        location = ER.path(records, self.dispatch_id)
        if not os.path.exists(location):
            return ER.Recorder(records, dict(self.contract, contract_digest=D.digest(self.contract)), None).close()
        with open(location, 'rb') as handle:
            data = handle.read()
        return {'lines': max(0, data.count(b'\n') - 1), 'bytes': len(data),
                'digest': 'sha256:' + hashlib.sha256(data).hexdigest()}

    def _settle(self, lost):
        """The launch result from the record. When the receiver ended without a conclusive record it
        is settled here: still prepared is refused (the receiver spawns only after its acceptance
        commits, and it has ended), accepted is unknown (a stop owed, never a second launch). The
        reason of that unknown says whether the receiver itself said it left no end (its exit status)."""
        record = self.dispatches.record(self.dispatch_id)
        state = (record or {}).get('state')
        digest = (record or {}).get('contract_digest')
        if lost and state == 'prepared':
            record = self.dispatches.refuse(self.dispatch_id, digest, 'receiver_unavailable', now=self.clock(),
                                            expected_state='prepared')
        elif lost and state == 'accepted':
            # VELDO-0350 fix 2: a receiver that said itself that it left no end (it failed before its record
            # reached running and exited END_UNRECORDED) is recorded apart from one that died or was killed.
            reason = EVIDENCE_UNRECORDED_REASON if self.returncode == END_UNRECORDED else 'launch_evidence_missing'
            record = self.dispatches.unknown(self.dispatch_id, digest, reason, now=self.clock(),
                                             expected_state='accepted', execution_record=self._record_commitment())
        state = (record or {}).get('state')
        self.record = record
        self.result = {'running': 'accepted', 'exited': 'accepted', 'refused': 'refused'}.get(state, 'unknown')
        self.refusal = (record or {}).get('refusal') if state == 'refused' else None

    def start(self, accept_seconds):
        deadline = time.monotonic() + accept_seconds
        while True:
            message = self._message(deadline)
            if message is None:
                self._end_receiver()
                self._settle(lost=True)
                return self
            refusal = message.get('refusal') if message.get('event') == 'refused' else None
            if isinstance(refusal, str) and refusal.startswith('not_prepared:'):
                # This invocation launched nothing and owns nothing; the record is not its to write.
                self._end_receiver()
                self.owned, self.result, self.refusal = False, 'refused', refusal
                self.record = self.dispatches.record(self.dispatch_id)
                return self
            if message.get('event') in ('running', 'refused', 'unknown', 'exited'):
                self._settle(lost=False)
                if self.result != 'accepted':
                    self._end_receiver()
                return self

    def wait(self, timeout=None):
        """The dispatch's record once the receiver has recorded its end, or unknown if it cannot."""
        if not self.owned:
            return self.dispatches.record(self.dispatch_id)
        # By default the receiver has until the contract deadline, or the later end it announced for a
        # contained worker's stop, and ACCEPT_SECONDS more.
        ends_by = max(self.contract['deadline'], self.ends_by or 0)
        deadline = time.monotonic() + (timeout if timeout is not None else
                                       max(1.0, ends_by - time.time() + ACCEPT_SECONDS))
        if self.result == 'accepted' and (self.record or {}).get('state') == 'running':
            while True:
                message = self._message(deadline)
                if message is None or message.get('event') in ('exited', 'unknown'):
                    break
        self._end_receiver()
        record = self.dispatches.record(self.dispatch_id)
        if record and record['state'] == 'running':
            # The receiver that owned the worker has ended without recording its end. VELDO-0350: one that
            # said so itself (it failed, its end write refused after its retries or never sent, and it exited
            # END_UNRECORDED) is recorded apart from one that was killed, vanished or was stopped here.
            reason = END_UNRECORDED_REASON if self.returncode == END_UNRECORDED else 'outcome_unknown'
            record = self.dispatches.unknown(self.dispatch_id, record['contract_digest'], reason,
                                             now=self.clock(), expected_state='running',
                                             execution_record=self._record_commitment())
        self.record = record
        return record


def receiver_log(records, dispatch_id):
    """VELDO-0350: the file a dispatch's receiver writes its standard error to, beside the run's execution
    record and named as it is. It is no part of that record and of no digest."""
    return ER.path(records, dispatch_id)[:-len('.jsonl')] + '.receiver.log'


def _receiver_errors(records, dispatch_id):
    """The open descriptor of `receiver_log` and its path, or (None, None) when it cannot be opened: a
    launch is never refused for its log."""
    try:
        os.makedirs(str(records), mode=0o700, exist_ok=True)
        place = receiver_log(records, dispatch_id)
        return os.open(place, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600), place
    except (OSError, ValueError, TypeError):
        return None, None


def invoke(config_path, contract, dispatches, *, accept_seconds=ACCEPT_SECONDS, environment=None, clock=None):
    """Hand the prepared contract to the trusted receiver process named by the installed config."""
    errors, place = None, None
    try:
        with open(config_path) as handle:
            config = json.load(handle)
        if not isinstance(config, dict):
            raise ValueError('receiver config must be an object')
        records = ER.directory(config)
        # VELDO-0350: what the receiver writes on standard error is kept beside the run's execution record.
        errors, place = _receiver_errors(records, contract['dispatch_id'])
        child = subprocess.Popen([sys.executable, '-B', RECEIVER, str(config_path)], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL if errors is None else errors,
                                 env=environment)
    except (OSError, ValueError, KeyError, TypeError):
        # No receiver ran, so nothing was launched: a conclusive refusal, never a held unit.
        if errors is not None:
            os.close(errors)
        launch = Launch(None, contract, dispatches, clock or time.time)
        launch._settle(lost=True)
        return launch
    if errors is not None:
        os.close(errors)  # the receiver holds its own
    launch = Launch(child, contract, dispatches, clock or time.time, records=records)
    launch.receiver_log = place
    try:
        # The receiver's stdin stays open as its control channel: Launch.stop writes a stop request on it.
        child.stdin.write((json.dumps({'contract': contract}) + '\n').encode())
        child.stdin.flush()
    except OSError:
        pass
    return launch.start(accept_seconds)


# The receiver process.

def _write_held_input(stdin, data, last, terminal):
    """Mark the prompt before an engine can answer during write or flush."""
    if last and getattr(terminal, 'require_prompt', False):
        terminal.wrote_prompt()
    stdin.write(data)
    stdin.flush()


class Receiver:
    """The trusted launch receiver over the installed configuration: {store, journal_key, principal,
    domain, repository, authority_generation, workspace, host_trust, profile, adapters: {name: {argv,
    environment?, identity?}}}. `host_trust` is this host's installed trust file, whose settlement
    signers the recheck's Gate verifies governing decisions with (VELDO-0069), exactly as the front
    door's Gate does. `profile` is this host's worker profile (control_containment); `control` is the
    runner's channel after its request line (fd, what was already read of it), where it asks for a stop.
    Optional `clone_root` names the launcher's known work root for execution record path membership."""

    def __init__(self, config, emit, control=None, space=None):
        self.config, self.emit = config, emit
        # VELDO-0303: the space ledger and what Signal is given (space_signal), or None where there is none;
        # and what Signal answered for this receiver's run directory.
        self.space, self.run_removal, self.run_dispatch = space, None, None
        # VELDO-0305: what the run was given before its worker started (space_run_folders), and what the
        # census read at its end (space_census).
        self.space_run, self.run_census = None, None
        # VELDO-0308: what this receiver's space end did (_space_end), and whether it sent run finished.
        self.run_end, self.run_sent = None, False
        self.profile = config.get('profile')
        self.qualification = None
        self.supervision = None
        self.control = control
        self.conn = S.open_store(config['store'])
        key = config['journal_key']
        signer = _organ('control_signer')
        receiver_kind = config.get('receiver_kind', 'project')
        repository = config.get('repository') if receiver_kind == 'project' else None
        self.dispatches = D.Dispatches(S, self.conn, domain=config['domain'], repository=repository,
                                       principal=config['principal'], signer=config['principal'],
                                       sign=lambda data: signer.sign_bytes(key, data, JOURNAL_NAMESPACE),
                                       generation=config.get('authority_generation', 1), subject_kind=receiver_kind)
        self.renewals = HB.Renewals(self.dispatches, D)
        self.sign = lambda data: signer.sign_bytes(key, data, JOURNAL_NAMESPACE)
        self.host = config.get('host') or socket.gethostname()
        self.login = None
        self.memory = None
        self.metering = None
        self.binding = None
        self.token = None
        self.run = None
        self.conversation_directory = None
        # VELDO-0254 AC3: the launcher's runner decision for this launch, and this receiver's judgment of its host's
        # confined runner, taken once. AC2: what the run's workspace held as it started.
        self.runner = {'runner': 'default', 'why': None}
        self.confined_checked = {}
        self.workspace_before = None
        # VELDO-0158: the selected MCP servers with their credentials resolved just before the spawn, and the
        # values delivered into the engine environment, by name.
        self.credentials = None
        self.delivered = None
        self.selected = None
        self.role_skills = []
        # VELDO-0141: the contract launched, the run's resolved values and its execution record.
        self.contract = None
        self.resolved = None
        self.recorder = None
        self.committed = None

    def _unstage_skills(self):
        """The role skills staged into the clone's discovery directory are links into the run's own configuration:
        each is removed with the run, so none outlives its target or reaches a later run of the same clone."""
        skills, self.role_skills = self.role_skills, []
        for path in skills:
            if path.is_symlink():
                path.unlink()

    def close(self):
        self._unstage_skills()
        if self.recorder is not None:
            self.recorder.close()
        self.conn.close()

    def _ended(self):
        """The dispatch's end is recorded: the execution record's last hint, marked ended, before the runner is
        told; returns the record's account for the end event the runner reads (VELDO-0141), never a value."""
        if self.recorder is None:
            return None
        self.committed = self.recorder.close()
        self.recorder.hint(True)
        return self.recorder.summary()

    def _record(self, adapter, environment):
        """The run's set of resolved credential values, from every resolver (VELDO-0141), and its execution
        record, opened before the worker exists and bound to its dispatch."""
        contract = self.contract
        self.resolved = ER.Resolved()
        for resolver in RESOLVERS:
            for kind, value in resolver(self, contract, adapter, environment) or ():
                self.resolved.add(kind, value)
        header = {'dispatch_id': contract['dispatch_id'], 'contract_digest': D.digest(contract),
                  'unit': contract['unit'], 'station': contract['station'],
                  'project': contract['reservation']['project'], 'account': contract['reservation']['account'],
                  'host': self.host}
        argv = (self.binding or {}).get('argv', adapter['argv'])
        cwd = self._engine_cwd(argv, contract['dispatch_id'], adapter.get('identity') == 'reported')
        # The clone entrance's dispatch record supplies its work root. Direct launches may name a
        # containing root in trusted receiver config when their cwd is a subdirectory.
        self.resolved.paths = ER.clone_paths(cwd, root=self.config.get('clone_root', cwd))
        self.recorder = ER.Recorder(ER.directory(self.config), header, self.resolved,
                                    hints=self.config.get('record_hints') or (),
                                    hint_service=self.config.get('record_hint_service'))

    def _remove_run(self):
        """The run's own directories are removed once its engine has ended (or never started), before its end is
        recorded; a group that could not be emptied keeps them, since what is left of the run may still use them.
        With a space ledger the removal is Signal's, and nothing is deleted here (VELDO-0303); it is then called
        from the run's space end, after the end is recorded (_space_end, VELDO-0308)."""
        run, self.run = self.run, None
        empty = self._group_empty()
        stays = run is None or empty is False
        given = getattr(self, 'space_run', None) or {}
        if self.space is not None and given.get('worktree') and empty is not False:
            # VELDO-0305: the census of the run's worktree at the run's end, before Signal (design 8.1,
            # step 7): the build output the run left is declared now, so run finished can reach it, and
            # what is work gets no item. It declares and measures and deletes nothing.
            self.run_census = space_census(self.space, given['worktree'], 'run_finished', owner=given.get('owner'),
                                           also=[path for path in (given.get('scratch'), given.get('build')) if path])
        if not stays and self.space is not None:
            # VELDO-0303: the run directory is an item of this dispatch, and run finished removes it through
            # Signal. Rule 3 is answered here only when the group is known to be empty, or the engine never
            # started; a group nobody could read is left to the answer the installation wired in. A directory
            # a rule keeps is deferred on the record, and the sweep sends its next event (clear_runs).
            self._unstage_skills()
            # The consumer first: the event ends every item this run owns, and a clone another dispatch
            # still uses must not be among them. Such a run directory stays, and the sweep comes back.
            users = clone_users(self.config.get('clones'), self.dispatches, self.run_dispatch, self.space)
            if users:
                self.run_removal = {'item': None, 'state': None, 'deferral': 'clone_in_use', 'users': users}
                return
            # VELDO-0308: the event names the run's own items at the versions read, and never an item of a
            # clone. A clone a retirement handed over is the ledger's; one still live is ended by its own
            # teardown, behind its own clone_in_use test, and that teardown names the clone's own items and
            # nothing else of the owner. Neither holds this event back. A worktree or an agent repository of
            # the run that is no clone's is named with the run's folders, as design 6.10 has it.
            # VELDO-0337: a review run's scratch folder and build root are of the review run kinds, which
            # do not end on run finished (space_kind), so this event neither names nor removes them: they
            # wait for verdict recorded, which the writer of the verdict sends.
            folders = [run] + [path for path in (given.get('scratch'),) if path]
            self.run_sent = True
            self.run_removal = space_signal(
                self.space, 'run_finished', folders, 'receiver', clones=self.config.get('clones'),
                ended=empty is True, alone=True)[os.path.normpath(run)]
            if self.run_removal.get('deferral') == 'remove_refused':
                # The send raised or the ledger refused it whole (a named item changed since it was read):
                # nothing was sent. The run directory is the sweep's, which reads the items again.
                self.run_sent = False
        elif not stays:
            self._unstage_skills()
            found = _organ('control_space_remove').remove_standalone(run, 'folder')
            self.run_removal = (None if found['state'] in SPACE_SAFE
                                else dict(found, refusal=space_refusal(found)))

    def _group_empty(self):
        """Whether the run's containment group is empty, as the kernel answered when the receiver settled it:
        True, False while something of the group is still running, or None when nobody could read it. A run
        whose worker was never started has no group and nothing in it. Never the end of the worker's own
        process: a child of it may still hold a file of the run (VELDO-0308 AC1)."""
        return (self.supervision or {}).get('empty', True)

    def _space_end(self, dispatch_id, contract=None):
        """VELDO-0308: the run's end in the space ledger (design 8.1, steps 6 to 10). Run finished has happened
        when the dispatch record is conclusive (exited or refused, read from the store now) and the run's
        containment group is empty (design section 5). Only then, in this order and each written before this
        returns: the census of the run's worktree, Signal with run finished (both in _remove_run, where every
        removal is Signal's, after the safety rules and the keep step), and the release of the run's hold.
        The receiver reports its end, and so exits, only after this has returned.

        A dispatch whose record is not conclusive, or whose group still has a process, is sent nothing:
        nothing of it is judged, its items stay as they are and its hold stays held, because what is left of
        the run may still write. Its run directory is the sweep's (Runner.clear_runs). A group nobody could
        read is not known to be empty and gets the same (reason group_unread): the sweep's kernel test, which
        reads the group again, takes over.

        The hold is the one the contract's space field names (design 6.7), else the one placed under the
        dispatch's own identity. Returns, and keeps in run_end, {dispatch_id, sent, reason, census, removal,
        items, hold}: whether run finished was sent and why not, what the census read, what Signal answered
        for the run directory, the state of every item of the run as the ledger holds it now, and what
        became of the hold."""
        end = {'dispatch_id': dispatch_id, 'sent': False, 'reason': None, 'census': None, 'removal': None,
               'items': {}, 'hold': None}
        self.run_end = end
        space = getattr(self, 'space', None)
        if space is None:
            return end
        try:
            state = (self.dispatches.record(dispatch_id) or {}).get('state')
        except Exception:  # noqa: BLE001 - a record that cannot be read is not conclusive
            state = None
        if state not in SPACE_CONCLUSIVE:
            end['reason'] = 'not_conclusive:%s' % (state,)
        elif self._group_empty() is False:
            end['reason'] = 'group_not_empty'
        elif self._group_empty() is not True:
            # Nobody could read the group: not known to be empty, so not empty (design 0.6).
            end['reason'] = 'group_unread'
        if end['reason'] is not None:
            self._unstage_skills()
            return end
        self.run_sent = False
        self._remove_run()
        end.update(sent=self.run_sent, census=self.run_census, removal=self.run_removal,
                   items=space_run_items(space, dispatch_id))
        if not self.run_sent:
            end['reason'] = ((self.run_removal or {}).get('deferral') if self.run_removal else None) or 'nothing_recorded'
        named = ((contract or {}).get('space') or {}).get('hold') if isinstance((contract or {}).get('space'), dict) else None
        end['hold'] = space_release(space, named or dispatch_id, run=dispatch_id)
        return end

    def _settlement_trust(self, EL):
        """VELDO-0069: the decision settlement signers this receiver's Gate verifies with, derived as the
        production construction of the front door's Gate derives them (control_eligibility.enrolled_gate):
        this host's installed trust, named by the configuration's `host_trust`, read for the configured
        workspace. Missing configuration is a named stop for every unit, before acceptance or spawn;
        a named trust that is absent or unreadable keeps its existing named stop."""
        path = self.config.get('host_trust')
        if not path:
            raise EL.Stopped('host_trust_required:receiver_configuration')
        trust = EL.load_host_trust(path)
        if trust is None:
            raise EL.Stopped('host_trust_required')
        return trust.settlement_trust(self.config.get('workspace'))

    def _recheck(self, contract):
        """The preparation's station decision, rechecked at this accepting boundary as its ticket."""
        if contract.get('subject_kind') == 'conversation':
            conversation = _organ('control_conversation')
            reader = S.open_store(self.config['store'], mode='r')
            try:
                problem = conversation.receiver_check(reader, contract)
                record = conversation._conversation(reader, contract.get('unit'))
                self.conversation_directory = ((record or {}).get('data') or {}).get('directory')
                return problem
            finally:
                reader.close()
        EL = _organ('control_eligibility')
        try:
            settlements = self._settlement_trust(EL)
        except EL.Stopped as error:
            return error.reason
        reader = S.open_store(self.config['store'], mode='r')
        try:
            # The workspace whose architecture the decision judges (VELDO-0053) is the receiver's configured
            # repository checkout; without one the Gate is store-only and refuses.
            gate = EL.Gate(S, reader, domain_uuid=self.config['domain'], repository_uuid=self.config['repository'],
                           authority_generation=self.config.get('authority_generation', 1),
                           workspace=self.config.get('workspace'), settlement_trust=settlements)
            context = dict(contract['input']['context'])
            if contract['claim']:
                context['generation'] = contract['claim']['generation']
            decision = gate.decide(contract['station'], contract['unit'], context=context,
                                   ticket=contract['input']['decision'])
        finally:
            reader.close()
        return None if decision['eligible'] else '; '.join(decision['refusals'])

    def _qualify(self, adapter):
        """This host's worker profile, qualified before acceptance for a local adapter: an absent, invalid
        or unenforceable profile is refused by name and nothing is spawned. Another host's worker
        (identity reported) is contained by that host's profile (VELDO-0124)."""
        if adapter.get('identity', 'local') == 'reported':
            return None
        self.qualification = C.qualify(self.profile)
        return self.qualification['refusal']

    def launch(self, contract):
        dispatch_id = contract['dispatch_id']
        record = self.dispatches.record(dispatch_id)
        self.contract = contract
        if record is None or record['state'] != 'prepared':
            # Not this receiver's to launch: another attempt of it was accepted, refused, ended or is
            # unknown. Nothing is recorded and nothing is spawned.
            self.emit({'event': 'refused', 'refusal': 'not_prepared:%s' % (record or {}).get('state', 'missing')})
            return
        contract_digest = D.digest(contract)
        adapter = self.config.get('adapters', {}).get(contract['capability']['adapter'])
        refusal = None
        kind_problem = receiver_kind_problem(self.config, contract)
        if kind_problem:
            refusal = kind_problem
        elif contract_digest != record['contract_digest']:
            refusal = 'binding_mismatch:contract_digest'
        elif not isinstance(adapter, dict) or (not adapter.get('argv') and adapter.get('engine') != 'claude_code'):
            refusal = 'unregistered_adapter:' + str(contract['capability']['adapter'])
        else:
            refusal = self._recheck(contract)
        if not refusal:
            refusal = self._qualify(adapter)
        if not refusal:
            refusal = self._login(contract, adapter)
        if not refusal:
            refusal = self._bind(adapter, dispatch_id)
        self.memory = None
        if not refusal:
            memory = _organ('control_memory')
            reader = S.open_store(self.config['store'], mode='r')
            try:
                self.memory = memory.handoff(reader, self.host)
            except memory.Refused as error:
                refusal = error.code
            finally:
                reader.close()

        if not refusal:
            # VELDO-0254 AC3: the one launcher decision; only a risky launch can be refused for confinement.
            self.runner = runner_decision(self.config, contract)
            refusal = runner_refusal(self.config, self.runner, self.confined_checked)
            if not refusal and self.runner['runner'] == 'confined' and adapter.get('identity', 'local') == 'reported':
                # The confined runner is this host's; another host's engine cannot be started in it from here.
                refusal = 'confined_runner_unavailable:remote_host'
        if refusal:
            self.dispatches.refuse(dispatch_id, record['contract_digest'], refusal, now=time.time(),
                                   expected_state='prepared')
            self._space_end(dispatch_id, contract)
            self.emit({'event': 'refused', 'refusal': refusal, 'runner': self.runner,
                       'dispatch_id': dispatch_id, 'repository': self.config.get('repository'),
                       'configuration': getattr(self, 'configuration_path', None),
                       'metrics': {'host_trust_required': int(refusal == 'host_trust_required:receiver_configuration'),
                                   'turn_kind_refusals': int(refusal == 'binding_mismatch:conversation_receiver'),
                                   'engine_baseline_refused': int(refusal.startswith('missing_evidence:engine_baseline:'))}})
            return
        me = dict(process_identity(os.getpid()), principal=self.config['principal'])
        try:
            self.dispatches.accept(dispatch_id, contract_digest, me, now=time.time())
        except D.Refused as error:
            current = (self.dispatches.record(dispatch_id) or {}).get('state')
            if current != 'prepared':
                # Another invocation moved it on: not this receiver's to refuse or launch.
                self.emit({'event': 'refused', 'refusal': 'not_prepared:%s' % current})
                return
            self.dispatches.refuse(dispatch_id, record['contract_digest'], error.code, now=time.time(),
                                   expected_state='prepared')
            self._space_end(dispatch_id, contract)
            self.emit({'event': 'refused', 'refusal': error.code})
            return
        acceptance = self.dispatches.receipt(dispatch_id, 'accept')
        self.emit({'event': 'accepted', 'acceptance': acceptance, 'runner': self.runner})
        try:
            worker = self._invoke(contract, acceptance, adapter)
        except SC.SpaceCreationError as error:
            self._not_executed()
            self.dispatches.refuse(dispatch_id, contract_digest, error.code, now=time.time(), expected_state='accepted')
            self._space_end(dispatch_id, contract)
            self.emit({'event': 'refused', 'refusal': error.code})
            return
        except Unfunded as error:
            # Checked and refused before anything was spawned: nothing ran, nothing was reserved.
            self.dispatches.refuse(dispatch_id, contract_digest, error.code, now=time.time(), expected_state='accepted')
            self._space_end(dispatch_id, contract)
            self.emit({'event': 'refused', 'refusal': error.code})
            return
        except C.Refused as error:
            if error.settled:
                self._not_executed()
            self._uncontained(dispatch_id, contract_digest, error)
            return
        except DL.Undeliverable as error:
            # VELDO-0158 AC2: a credential that does not resolve refuses the launch by name before its spawn; the
            # run never starts without its server.
            self._not_executed()
            self.dispatches.refuse(dispatch_id, contract_digest, error.code, now=time.time(), expected_state='accepted')
            self._space_end(dispatch_id, contract)
            self.emit({'event': 'refused', 'refusal': error.code,
                       'credentials': DL.report(dispatch_id, self.credentials, refusal=error, selected=self.selected)})
            return
        except OSError as error:
            self._not_executed()
            refusal = 'spawn_failed:' + errno.errorcode.get(error.errno or 0, type(error).__name__)
            self.dispatches.refuse(dispatch_id, contract_digest, refusal, now=time.time(), expected_state='accepted')
            self._space_end(dispatch_id, contract)
            self.emit({'event': 'refused', 'refusal': refusal})
            return
        carry = b''
        remote = adapter.get('identity', 'local') == 'reported'
        try:
            if remote:
                process, refusal, carry = self._reported(worker, contract)
                if refusal:
                    worker.wait()
                    self._not_executed()
                    self.dispatches.refuse(dispatch_id, contract_digest, refusal, now=time.time(),
                                           expected_state='accepted')
                    self._space_end(dispatch_id, contract)
                    self.emit({'event': 'refused', 'refusal': refusal})
                    return
            else:
                process = process_identity(worker.pid)
        except (OSError, ValueError, IndexError, subprocess.SubprocessError):
            self._stop(worker)
            self.dispatches.unknown(dispatch_id, contract_digest, 'process_identity_unreadable', now=time.time(),
                                    expected_state='accepted',
                                    execution_record=self.recorder.close() if self.recorder else None)
            self.emit({'event': 'unknown'})
            return
        try:
            self.dispatches.run(dispatch_id, contract_digest, process, now=time.time())
        except BaseException:
            # The worker ran with no running record: stop it; the runner records the outcome unknown.
            self._stop(worker)
            raise
        group = getattr(worker, 'group', None)
        watch = getattr(worker, 'heartbeat', None)
        # When this receiver will have recorded the end at the latest: a stop begun at the deadline, its
        # graces and the settling of the group.
        ends_by = contract['deadline'] + (sum(self._graces()) + C.SETTLE_SECONDS if group else 0)
        beat = {'interval_seconds': watch.interval, 'window_seconds': watch.window} if watch else None
        graces = dict(zip(('stop_grace_seconds', 'kill_grace_seconds'), self._graces())) if group else None
        self.emit({'event': 'running', 'process': process, 'ends_by': ends_by, 'heartbeat': beat, 'graces': graces,
                   'group': group.report() if group else None})
        # Set per dispatch before reaping, so the cleanup below never reads a stale or missing group
        # when the reap itself raises.
        self._exit_group = None
        termination = self._reap(worker, contract, carry, process=process, contract_digest=contract_digest)
        try:
            self._finish(termination, contract, contract_digest, process, remote)
        finally:
            if self._exit_group is not None:
                self._exit_group.close()
                self._exit_group = None

    def _finish(self, termination, contract, contract_digest, process, remote):
        dispatch_id = contract['dispatch_id']
        if self.metering is not None:
            # The invocation settles before its end is recorded, so the slot's accounting is complete.
            self.metering.settle(termination, (self.supervision or {}).get('cause'))
            if self.metering.report is not None:
                self.emit({'event': 'artifact', 'artifact': self.metering.report})
        if getattr(self, 'space', None) is None:
            self._remove_run()
        # VELDO-0308 AC1: with a space ledger nothing of the run is judged here, where only the worker's own
        # process is known to have ended. Run finished is sent once the end below is recorded (report_end).
        if remote and termination['deadline_stop']:
            # Stopping the local transport at the deadline does not show the remote engine ended: its
            # outcome is unknown, and the unit and station stay held.
            self.dispatches.unknown(dispatch_id, contract_digest, 'remote_stop_unconfirmed', now=time.time(),
                                    expected_state='running', execution_record=self.committed)
            report_end(self, contract, {'event': 'unknown', 'record': self._ended()})
            return
        supervision = self.supervision
        if remote and supervision['cause'] in ('paid_api', 'configuration_stop'):
            # Nor does stopping it for its login (VELDO-0155, VELDO-0156): the unit and station stay held.
            self.dispatches.unknown(dispatch_id, contract_digest, 'remote_stop_unconfirmed', now=time.time(),
                                    expected_state='running', execution_record=self.committed)
            report_end(self, contract, {'event': 'unknown', 'supervision': supervision, 'record': self._ended()})
            return
        if remote and supervision['cause'] in ('requested', 'usage_cap'):
            # Nor does stopping it on request or at its usage cap: the unit and station stay held.
            self.dispatches.unknown(dispatch_id, contract_digest, 'remote_stop_unconfirmed', now=time.time(),
                                    expected_state='running', execution_record=self.committed)
            report_end(self, contract, {'event': 'unknown', 'supervision': supervision, 'record': self._ended()})
            return
        if supervision['empty'] is False:
            # Something of the worker's group is still running: never recorded as ended.
            self.dispatches.unknown(dispatch_id, contract_digest, 'containment_not_empty', now=time.time(),
                                    expected_state='running', execution_record=self.committed)
            report_end(self, contract, {'event': 'unknown', 'supervision': supervision, 'record': self._ended()})
            return
        report = self.metering.report if self.metering is not None else None
        artifact = {k: report[k] for k in ('verdict', 'complete', 'digest')} if report is not None else None
        # VELDO-0141: the exit commits the execution record's line count, byte count and digest.
        self.dispatches.exit(dispatch_id, contract_digest, process, termination, now=time.time(), artifact=artifact,
                             execution_record=self.committed)
        # Kernel evidence commits the exit first; settlement still reads the retained scope.
        self._conclude_exit()
        report_end(self, contract, {'event': 'exited', 'termination': termination, 'supervision': supervision,
                                    'record': self._ended()})

    def _conclude_exit(self):
        group = self._exit_group
        if group is None:
            return
        result = group.conclude()
        if result in (None, 'unknown'):
            self.supervision.update(manager_result=None, scope_timestamps={},
                                    manager_result_absent_reason='terminal_scope_result_unreadable')
        else:
            self.supervision.update(result=result, manager_result=result,
                                    scope_timestamps=getattr(group, 'timestamps', {}))

    def _login(self, contract, adapter):
        """VELDO-0062: the subscription login of an engine adapter, read before acceptance from the
        account the accepted contract records. None when it may run; else the named refusal."""
        self.login = None
        reserved = sorted(n for n in (adapter.get('environment') or {}) if n.startswith('VELDO_'))
        if reserved:
            return 'invalid_input:adapter_environment:' + reserved[0]
        engine = adapter.get('engine')
        if engine is None:
            return None
        module = ENGINES.get(engine)
        if module is None:
            return 'unregistered_adapter:engine:' + str(engine)
        missing = [name for name in ENGINE_PROTOCOL if not hasattr(module, name)]
        if missing:
            return 'unregistered_adapter:engine_protocol:%s:%s' % (engine, missing[0])
        # What the adapter configures reaches the engine as configured; a login in it is refused by name.
        configured = ACC.refused(adapter.get('environment') or {}, CREDENTIALS)
        if configured:
            return 'invalid_input:adapter_environment:' + configured[0]
        # VELDO-0165 AC2: a name the baseline strips by name (the MCP tool naming switch) is never configured.
        renaming = sorted(set(adapter.get('environment') or {}) & NEVER_CONFIGURED)
        if renaming:
            return 'invalid_input:adapter_environment:' + renaming[0]
        account = contract['reservation']['account']
        record = ACC.read(self.conn, account)
        if record is not None and record.get('provider') != module.PROVIDER:
            return 'invalid_input:account_provider:%s:%s' % (record.get('provider'), module.PROVIDER)
        try:
            ACC.profile(record, self.host)
        except ACC.Refused as error:
            return error.code
        # The engine's local time zone, for a CLI that states a reset in local time (Codex).
        zone = (adapter.get('environment') or {}).get('TZ', os.environ.get('TZ'))
        self.login = {'engine': module, 'account': account, 'record': record, 'zone': zone}
        return None

    def _bind(self, adapter, dispatch_id):
        """THE ENGINE PROTOCOL's one binding path (VELDO-0060, VELDO-0061): the engine's pinned executable,
        its argv and its settings, bound before acceptance. None when it may run; else the named refusal,
        with nothing accepted, reserved or spawned."""
        self.binding = None
        self.token = None
        module = (self.login or {}).get('engine')
        if module is None:
            return None
        try:
            bound = module.bind(adapter, self.config.get('state_root'))
        except module.Refused as error:
            self.emit({'event': 'engine_bind_refused', 'engine': module.PROVIDER, 'refusal': error.code,
                       'metrics': {'binds_refused': 1}})
            return error.code
        try:
            argv = module.command(bound, adapter)
            settings = module.environment(bound)
        except module.Refused as error:
            return error.code
        refusal = pinned_argv_problem(argv, bound, adapter.get('identity', 'local') == 'reported')
        if refusal:
            return refusal
        configured = adapter.get('environment') or {}
        for name in sorted(settings):
            if name in configured and configured[name] != settings[name]:
                return 'invalid_input:adapter_environment:' + name
        # VELDO-0173: the role revision the dispatch binds (VELDO-0127's, in the contract's capability
        # configuration), whose native tools are the launch tool set; checked before acceptance.
        revision = (self.contract['capability'].get('configuration') or {}).get('role_revision')
        if hasattr(module, 'tool_options'):
            try:
                module.tool_options(bound, revision)
            except module.Refused as error:
                return error.code
        try:
            capability = HANDOFF.materialize(
                self.conn, self.contract['domain'], self.contract['repository'], revision,
                {'project': self._engine_cwd(argv, dispatch_id, False),
                 'factory': self.config.get('workspace') or self.config.get('state_root')})
            if capability and revision['engine'] != module.PROVIDER:
                return 'unsupported_configuration:engine'
            if capability and module.PROVIDER == 'claude_code' and set(revision['native_tools']) - set(bound['tools']['registry']):
                return 'unavailable_service:native_tools'
        except HANDOFF.Refused as error:
            return error.code
        self.binding = dict(bound, argv=argv, environment=settings, configured_environment=dict(configured),
                            revision=revision, capability=capability)
        # VELDO-0155, VELDO-0156: the subscription token an account is configured with, the account profile
        # and the login the engine would take in its environment, checked before acceptance: a profile item
        # the baseline cannot keep out, or a login that is not a subscription, is refused by name and no
        # turn is ever sent.
        login_environment = self._login_environment(adapter)
        cwd = self._engine_cwd(argv, dispatch_id, adapter.get('identity', 'local') == 'reported')
        self.token, problem = self._token()
        problem = (problem or self._account_login(module, bound, adapter, login_environment, cwd)
                   or module.profile_problem(self.binding, login_environment, cwd)
                   or module.login_problem(bound, login_environment, cwd))
        if problem:
            self.binding, self.token = None, None
            return problem
        return None

    def _account_login(self, module, bound, adapter, environment, cwd):
        """VELDO-0185 AC4: for an adapter factory setup wrote (`account_login` true), the account's own login
        as its engine reports it (the engine module's `account_login`, the check setup runs), before acceptance:
        an account not logged in to its subscription is refused by name (missing_authority:account_login:<account>),
        nothing accepted, reserved or spawned, so the Line offers the unit on another account. An account whose
        subscription token the configuration names (VELDO-0155 AC2) logs in with that token instead."""
        if adapter.get('account_login') is not True or self.token is not None:
            return None
        check = getattr(module, 'account_login', None)
        kind = check(bound, environment, cwd) if callable(check) else 'unqualified'
        if kind is None:
            return None
        account = self.login['account']
        self.emit({'event': 'account_login_refused', 'engine': module.PROVIDER, 'account': account, 'login': kind,
                   'metrics': {'account_login_refused': 1}})
        return ACCOUNT_LOGIN + account

    def _engine_cwd(self, argv, dispatch_id, reported):
        """The engine's working directory, where a relative path it reads resolves (THE ENGINE PROTOCOL): the
        work tree of the dispatch's clone when the clone entrance execs it (it changes into it), this
        receiver's own when this receiver's wrapper execs it directly; None for another host's engine, or a
        clone that names no single work tree."""
        if (getattr(self, 'contract', None) or {}).get('subject_kind') == 'conversation':
            return self.conversation_directory
        if reported:
            return None
        engine = engine_argv(argv, False)
        if not entrance(engine):
            return os.getcwd()
        clone = _organ('control_clone')
        try:
            return clone.find(engine[4], dispatch_id)[0]['work']
        except (clone.Refused, KeyError, TypeError, OSError):
            return None

    def _login_environment(self, adapter):
        """The engine's login environment as _spawn builds it (VELDO-0062): the inherited one without every
        login, the adapter's configured one, the recorded account's profile."""
        inherited = dict(os.environ)
        inherited = ACC.login_environment(inherited, self.login['record'], self.host, STRIPPED,
                                          adapter.get('environment') or {}, CREDENTIALS)
        inherited['VELDO_ACCOUNT'] = self.login['account']
        return inherited

    def _token(self):
        """(token, refusal): the subscription token of the recorded account, from the file the receiver's
        configuration names for it (`subscription_tokens`, account to an absolute path; VELDO-0155 AC2), which
        reaches the engine as CLAUDE_CODE_OAUTH_TOKEN, the only login variable it then carries. A Claude Code
        account only; the file is a regular file of this account's own that nobody else can read, opened once
        (never through a link, never waiting on a pipe) and checked and read on that one descriptor, so what
        is checked is what is read. (None, None) for none."""
        path = (self.config.get('subscription_tokens') or {}).get((self.login or {}).get('account'))
        if path is None:
            return None, None
        account = self.login['account']
        if self.login['engine'].PROVIDER != 'claude_code':
            return None, 'invalid_input:subscription_token:%s' % account
        refused = 'missing_authority:subscription_token:%s' % account
        try:
            fd = (os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
                  if isinstance(path, str) and os.path.isabs(path) else None)
        except OSError:
            fd = None
        if fd is None:
            return None, refused
        try:
            info = os.fstat(fd)
            if (not stat_regular(info) or info.st_uid != os.geteuid() or info.st_mode & 0o077
                    or info.st_size == 0):
                return None, refused
            data = b''
            for block in iter(lambda: os.read(fd, 65536), b''):
                data += block
        except OSError:
            return None, refused
        finally:
            os.close(fd)
        token = data.decode('utf-8', 'replace').strip()
        return (token, None) if token else (None, refused)

    def _run_directories(self, dispatch_id):
        """The run's own directories (VELDO-0155, VELDO-0156), fresh and 0700, outside every clone: `config`
        holds its generated configuration, `runtime` is the engine's empty XDG_RUNTIME_DIR. Under the
        config's `runs`, else the factory state root's runs, else beside the store."""
        runs = runs_root(self.config)
        run = run_directory(runs, dispatch_id)
        creation = SC.SpaceCreator(getattr(self, 'space', None), SC.space_owner(getattr(self, 'contract', {})))
        with creation.item('scratch', run):
            os.makedirs(runs, mode=0o700, exist_ok=True)
            os.mkdir(run, 0o700)
            self.run, self.run_dispatch = run, dispatch_id
            for name in (RUN_CONFIG, RUN_RUNTIME):
                os.mkdir(os.path.join(run, name), 0o700)
        self.space_items = creation.items
        return {'root': run, 'config': os.path.join(run, RUN_CONFIG), 'runtime': os.path.join(run, RUN_RUNTIME)}

    def _baseline(self, dispatch_id, argv, environment, reported):
        """VELDO-0155, VELDO-0156: the everything-off baseline right after the qualified flags, its generated
        files written 0600 into the run's own configuration directory, the engine's own runtime directory
        named for the wrapper's strip, and the subscription token of an account configured with one. The
        receiver reports what it added and the names removed, never a value."""
        run = dict(self._run_directories(dispatch_id), revision=self.binding.get('revision'),
                   capability=self.binding.get('capability'))
        engine = self.login['engine']
        try:
            extra = engine.baseline(self.binding, run, environment, servers=self.credentials or ())
            self.binding['expected'] = extra.get('expected')
            if extra.get('expected') and engine.PROVIDER == 'claude_code' and self.metering:
                self.metering.login_guard.expected = extra['expected']
                self.metering.terminal.hold_prompt()
        except (engine.Refused, HANDOFF.Refused) as error:
            # VELDO-0158: a credential the engine cannot be handed (a name two servers claim) is never dropped.
            raise DL.Undeliverable(error.code, error.code.split(':', 1)[1], 'delivery_failed') from None
        # The generated files exist before anything reads the configuration naming them: the real Codex loads its
        # whole configuration, the per-run `model_catalog_json` included, for `mcp list` as it does for exec, and
        # refuses to start when that file is missing (VELDO-0127).
        for name, data in sorted(extra['files'].items()):
            Path(run['config'], name).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with os.fdopen(os.open(os.path.join(run['config'], name), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
                           'wb') as handle:
                handle.write(data)
        try:
            if extra.get('expected') and engine.PROVIDER == 'codex':
                listing = HANDOFF.codex_listing(self.binding, extra, environment, run['config'])
                tools = HANDOFF.codex_check_launch(self.binding, extra, environment, run['config'])
                self.emit({'event': 'capability_tools', 'tools': tools})
                self.emit({'event': 'capability_listing', 'listing': [
                    {k: item[k] for k in ('name', 'enabled', 'enabled_tools') if k in item} for item in listing]})
        except (engine.Refused, HANDOFF.Refused) as error:
            raise DL.Undeliverable(error.code, error.code.split(':', 1)[1], 'delivery_failed') from None
        self.role_skills = HANDOFF.stage_skills(run.get('capability'), Path(run['config']))
        at = baseline_at(argv, self.binding, reported)
        argv[at:at] = list(extra['argv'])
        environment.update(extra['environment'])
        token = self.token
        if token is not None:
            environment[TOKEN_VARIABLE] = token
        # Apply the checked adapter configuration after stripping inherited session values.
        own = {n: environment[n] for n in self.binding['configured_environment'] if n in environment}
        own.update(self.binding['environment'])
        own.update(extra['environment'])
        profile_name, profile_directory = ACC.profile(self.login['record'], self.host)
        own[profile_name] = profile_directory
        if token is not None:
            own[TOKEN_VARIABLE] = token
        # VELDO-0158 AC1: a credential the engine environment carries (Codex's), under the name its server's
        # definition gives it; one naming a variable the engine already has (ENGINE_RESERVED, or any name the
        # receiver's environment, the adapter, the baseline or the account sets) is refused by name, never replaces it.
        secrets = extra.get('secrets') or {}
        # Every VELDO_ name belongs to the factory (the launch sets some of them only after this baseline), except
        # the names the engine module generates for delivered header credentials (DELIVERY_PREFIX).
        taken = sorted(n for n in secrets if n in ENGINE_RESERVED or n in own or n in environment
                       or (n.startswith(FACTORY_PREFIX) and not n.startswith(DELIVERY_PREFIX)))
        if taken:
            credential = next(r['credential'] for r in extra['routes'] if r.get('variable') == taken[0])
            raise DL.Undeliverable('invalid_input:mcp_delivery:env_collision:' + taken[0], credential, 'delivery_failed')
        own.update(secrets)
        self.delivered = dict(secrets)
        environment[ENGINE_OVERRIDES] = json.dumps(own, sort_keys=True)
        environment[ENGINE_RUNTIME] = run['runtime']
        self.emit({'event': 'baseline', 'baseline': {
            'dispatch_id': dispatch_id,
            'executable': {k: self.binding[k] for k in ('engine', 'version', 'sha256')},
            'strip_prefixes': list(SESSION_PREFIXES),
            'options': list(extra['argv']), 'environment': sorted(extra['environment']),
            'files': sorted(extra['files']), 'run': {k: run[k] for k in ('root', 'config', 'runtime')},
            'token': token is not None,
            # VELDO-0173: the launch tool set and the registry tools switched off, by name only.
            'tools': extra.get('tools'),
            'capabilities': extra.get('expected'),
            'removed': sorted((set(n for n in os.environ if n not in environment)
                              | set(n for n in environment if n in EXEC_STRIPPED or n.startswith(SESSION_PREFIXES)))
                              - set(own))}})
        if self.credentials:
            # VELDO-0158: each launch's catalog revisions, resolved credential ids and the route each took.
            self.emit({'event': 'credentials', 'credentials': DL.report(dispatch_id, self.credentials, extra['routes'])})
        return argv, environment

    def _invoke(self, contract, acceptance, adapter):
        """Spawn the worker. For a subscription engine the invocation is first checked and reserved
        against every applicable cap and the account's reported windows (VELDO-0036's InvocationGuard,
        whose launch is this spawn), so a refusal launches nothing."""
        dispatch_id = contract['dispatch_id']
        if self.login is None:
            return self._spawn(dispatch_id, acceptance, adapter)
        reservations = D.RES.Reservations(S, self.conn, domain=self.config['domain'],
                                          repository=self.config.get('repository'), principal=self.config['principal'],
                                          authorize=D.RES.service_authority, signer=self.config['principal'],
                                          sign=self.sign, generation=self.config.get('authority_generation', 1),
                                          subject_kind=contract.get('subject_kind', 'project'))
        accounts = ACC.Accounts(S, self.conn, principal=self.config['principal'], signer=self.config['principal'],
                                sign=self.sign, generation=self.config.get('authority_generation', 1))
        spawned = []

        def launch(invocation, configuration):
            # Reserved: from here a spawn that fails is attested not executed, one that starts is metered.
            self.metering = metering
            metering.started()
            spawned.append(self._spawn(dispatch_id, acceptance, adapter))
        metering = Metering(self, contract, reservations, accounts, launch)
        try:
            metering.guard.invoke('call/' + dispatch_id, dispatch_id, metering.invocation, metering.boundary,
                                  max(0.001, contract['deadline'] - time.time()),
                                  contract['capability']['configuration'], now=time.time())
        except (D.RES.Refused, ACC.Refused, S.StoreRefused) as error:
            raise Unfunded('missing_authority:allowance:' + error.code)
        if not spawned:
            raise Unfunded('stale_subject:invocation_replayed')
        return spawned[0]

    def _not_executed(self):
        """A reserved invocation whose engine never started: the receiver attests it (VELDO-0036), and the run's
        own directories go. With a space ledger they go at the run's space end, once the refusal is recorded
        (VELDO-0308 AC1)."""
        if getattr(self, 'space', None) is None:
            self._remove_run()
        metering, self.metering = self.metering, None
        if metering is not None:
            metering.settle(None, None)

    def _uncontained(self, dispatch_id, contract_digest, error):
        """A worker that could not be contained as declared was never released to its engine: refused
        by name, or unknown when its group could not be emptied."""
        if error.settled:
            self.dispatches.refuse(dispatch_id, contract_digest, error.code, now=time.time(), expected_state='accepted')
            self._space_end(dispatch_id, getattr(self, 'contract', None))
            refused = {'event': 'refused', 'refusal': error.code, 'group': error.group}
            if error.code.startswith(SPACE_FOLDER_STATE) and error.detail:
                refused['detail'] = error.detail  # VELDO-0305: the folder the owner has to look at
            self.emit(refused)
        else:
            self.dispatches.unknown(dispatch_id, contract_digest, 'containment_not_empty', now=time.time(),
                                    expected_state='accepted',
                                    execution_record=self.recorder.close() if self.recorder else None)
            self.emit({'event': 'unknown', 'group': error.group})

    def _spawn(self, dispatch_id, acceptance, adapter):
        """THE ONE SPAWN: the adapter's configured argv in its own session, its own pipes (it never
        shares this receiver's reply channel) and an environment naming its dispatch and the journal
        digest of the acceptance it launches under. That digest exists only once the acceptance has
        committed, so a worker's birth environment is evidence the acceptance, and the contract it
        accepted, were recorded before the worker existed. A local adapter's worker is started inside
        its dispatch's own containment group (VELDO-0040); a transport to another host is started as
        configured, and that host's profile contains the engine there."""
        # VELDO-0158: the dispatch's selected MCP servers and their credentials, resolved immediately before the spawn.
        self._resolve_credentials(adapter)
        environment = dict(os.environ)
        if self.login is not None:
            # VELDO-0062: the recorded account's own profile, no other profile and no other login in what
            # the engine inherits; what the adapter configures, as configured.
            environment = ACC.login_environment(environment, self.login['record'], self.host, STRIPPED,
                                                adapter.get('environment') or {}, CREDENTIALS)
            environment['VELDO_ACCOUNT'] = self.login['account']
        else:
            environment.update(adapter.get('environment') or {})
        argv = list(adapter['argv'])
        if self.binding is not None:
            # THE ENGINE PROTOCOL: the bound engine argv and the engine's own settings, last.
            argv = list(self.binding['argv'])
            environment.update(self.binding['environment'])
            # What the trusted program that execs the engine re-hashes immediately before the exec.
            environment[ENGINE_PATH], environment[ENGINE_DIGEST] = self.binding['path'], self.binding['sha256']
            argv, environment = self._baseline(dispatch_id, argv, environment,
                                               adapter.get('identity', 'local') == 'reported')
        environment.pop('VELDO_MEMORY', None)
        if self.memory is not None:
            environment['VELDO_MEMORY'] = json.dumps(self.memory, sort_keys=True)
            _organ('control_memory').record_launch(
                self.config.get('state_root') or str(Path(self.config['store']).parent.parent), dispatch_id, self.memory)
            self.emit(dict(event='memory', dispatch_id=dispatch_id, **self.memory))
        environment['VELDO_DISPATCH_ID'] = dispatch_id
        environment = _organ('control_git_identity').environment(environment)
        environment['VELDO_DISPATCH_ACCEPTANCE'] = acceptance or ''
        cwd = (self.conversation_directory
               if (getattr(self, 'contract', None) or {}).get('subject_kind') == 'conversation' else None)
        if cwd is not None:
            os.makedirs(cwd, mode=0o700, exist_ok=True)
        # VELDO-0305: the run's temporary folder and build root, declared before the worker exists.
        environment = self._space_given(dispatch_id, argv, environment, adapter)
        # VELDO-0141: the run's resolved values and its execution record, before the worker exists; its error
        # stream comes to this receiver, which keeps it in the record.
        self._record(adapter, environment)
        # VELDO-0254 AC3: the same argv, inside the confined runner only when the decision says so: writable in the
        # engine's own working directory (the dispatch's clone work tree, or the conversation directory) and handed
        # the engine's client files.
        config = getattr(self, 'config', None) or {}
        runner = getattr(self, 'runner', None) or {'runner': 'default', 'why': None}
        if runner['runner'] == 'confined':
            reported = adapter.get('identity', 'local') == 'reported'
            argv = runner_argv(config, runner, argv, cwd or self._engine_cwd(argv, dispatch_id, reported),
                               RUNNER_CLIENTS.get((self.binding or {}).get('engine')))
        # VELDO-0254 AC1: what the run starts with, scanned before it starts; a credential refuses the launch.
        project = _project(getattr(self, 'contract', None) or {})
        own = [getattr(self, 'token', None)] + list((getattr(self, 'delivered', None) or {}).values())
        refusal = launch_scan(config, dispatch_id, project, environment, argv, own=own)
        if refusal:
            raise C.Refused(refusal)
        # VELDO-0254 AC2: what the run's workspace holds as it starts, so its end reads only what it changed.
        try:
            self.workspace_before = {root: SS.tree_state(root) for root in run_roots(self, dispatch_id)}
        except Exception as error:
            self.workspace_before = None
            SS.failed('run_end', project, error, _failure_log(config), dispatch=dispatch_id)
        if adapter.get('identity', 'local') != 'reported':
            if cwd is not None:
                return self._contained(dispatch_id, argv, environment, cwd=cwd)
            return self._contained(dispatch_id, argv, environment)
        return subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=environment, cwd=cwd,
                                start_new_session=True, close_fds=True)

    def _space_given(self, dispatch_id, argv, environment, adapter):
        """VELDO-0305 AC3: with a space ledger, the run's temporary folder and build variables point at
        folders the ledger holds before the worker starts (space_run_folders); a folder that could not be
        declared refuses the launch by name, with nothing spawned. Nothing is given to an engine on another
        host, whose folders are not this host's, nor to a run in the confined runner, which gives the
        engine a temporary folder of its own and lets it write nowhere outside its worktree: what such a
        run builds stays in the worktree, where the census reads it."""
        self.space_run = None
        space = getattr(self, 'space', None)
        if space is None:
            return environment
        worktree = self._engine_cwd(argv, dispatch_id, adapter.get('identity', 'local') == 'reported')
        if not worktree:
            return environment
        contract = getattr(self, 'contract', None) or {}
        given = space_run_folders(space, worktree, dispatch_id, contract.get('station'),
                                  taken=tuple(getattr(self, 'delivered', None) or ()),
                                  confined=(getattr(self, 'runner', None) or {}).get('runner') == 'confined',
                                  run=getattr(self, 'run', None))
        self.space_run = given
        if given['refusal']:
            raise C.Refused(given['refusal'], given.get('detail') or '')
        return space_environment(environment, given['environment'])

    def _resolve_credentials(self, adapter):
        """VELDO-0158 AC1, AC2: the catalog servers the dispatch configuration selects, with their credentials
        resolved from the keystore through secretref's keychain scheme (control_credential_delivery), just before
        the spawn. They are delivered only to a Linux engine run, through THE ENGINE PROTOCOL's baseline; a
        selection for any other adapter, or a credential that does not resolve, is Undeliverable by name."""
        self.credentials, self.delivered, self.selected = [], {}, []
        configuration = self.contract['capability']['configuration']
        self.selected = DL.selections(configuration)
        if not self.selected:
            return
        if self.binding is None or adapter.get('identity', 'local') == 'reported':
            raise DL.Undeliverable('invalid_input:mcp_delivery:' + str(self.contract['capability']['adapter']))
        self.credentials = DL.resolve(self.conn, self.config['domain'], configuration)

    def _contained(self, dispatch_id, argv, environment, cwd=None):
        """Start the trusted wrapper inside the dispatch's own containment group with every declared cap
        installed, check it is in that group with those controls, and only then release it to become the
        engine (the same pid). The group is created under the profile's concurrency admission. A worker
        that is not contained as declared is discarded before any engine code runs and refused by name."""
        if self.qualification is None:
            self.qualification = C.qualify(self.profile)
        if not self.qualification['qualified']:
            raise C.Refused(self.qualification['refusal'])
        group = C.Group(self.profile, self.qualification, dispatch_id, environment)
        interval, window = self._heartbeat()
        # The heartbeat channel (VELDO-0041): the wrapper's heartbeat writes it, this receiver reads it.
        channel, beat = os.pipe()
        setup, ready = os.pipe()
        held = dict(group.held(), heartbeat_setup=ready)
        wrapper = [sys.executable, '-B', RECEIVER, 'exec', '--contained', json.dumps(held),
                   '--heartbeat', str(beat), repr(float(interval))] + argv
        try:
            with group.admission():
                try:
                    worker = subprocess.Popen(group.command(wrapper), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE, env=group.environment, cwd=cwd, start_new_session=True,
                                              close_fds=True, pass_fds=(beat, ready))
                finally:
                    os.close(beat)
                    os.close(ready)
                worker.group = group
                try:
                    reported, refusal, _ = self._reported(worker, {'deadline': time.time() + ACCEPT_SECONDS})
                    problems = [refusal] if refusal else group.attach(worker.pid)
                    if not problems and reported.get('pid') != worker.pid:
                        problems = ['spawn_failed:containment:identity']
                    if not problems:
                        group.retain()
                        HB.make_group(group.cgroup)
                        if self.config.get('clones'):
                            clone = _organ('control_clone')
                            provisioner = clone.Clones(self.dispatches, space=self.space, **self.config['clones'])
                            provisioner.record_group(dispatch_id, group.report())
                except (OSError, ValueError, TypeError, KeyError, AttributeError, subprocess.SubprocessError):
                    problems = ['spawn_failed:containment:unavailable']
                if problems:
                    settled = group.discard(worker)
                    if problems[0] == 'spawn_failed:ENOENT' and settled:
                        raise FileNotFoundError(errno.ENOENT, 'no engine: ' + str(argv[0]))
                    raise C.Refused(problems[0], settled=settled, group=group.report())
            try:
                # Fix the placement deadline at the sender's release, after the
                # receiver's separately bounded containment preparation. A wrapper
                # descheduled after release cannot give itself a fresh budget.
                release_deadline = time.monotonic() + HB.SETUP_SECONDS
                worker.stdin.write(('go %r\n' % release_deadline).encode())
                worker.stdin.flush()
            except OSError:
                settled = group.discard(worker)
                raise C.Refused('spawn_failed:containment:release', settled=settled, group=group.report())
            # The wrapper reports only after placement has completed. Until then it
            # cannot be reported running, even when it has left the scope or died.
            # Its startup budget is the absolute deadline sent with this release.
            # The same bound plus reap time and one second of report margin is
            # strictly later, even if the wrapper stalls after release.
            poller = select.poll()
            poller.register(setup, select.POLLIN)
            acknowledged = poller.poll(int((HB.SETUP_SECONDS + HB.SETTLE_SECONDS + 1) * 1000))
            status = os.read(setup, 1) if acknowledged else b''
            if status != b'1':
                reason = ({b'0': 'heartbeat_setup', b'T': 'heartbeat_timeout',
                           b'': 'heartbeat_wrapper_exited'}.get(status, 'heartbeat_setup')
                          if acknowledged else 'heartbeat_report_timeout')
                settled = group.discard(worker)
                raise C.Refused('spawn_failed:containment:' + reason, settled=settled, group=group.report())
        except BaseException:
            os.close(channel)
            raise
        finally:
            os.close(setup)
        worker.heartbeat = HB.Watch(channel, interval, window, time.monotonic())
        return worker

    @staticmethod
    def _reported(worker, contract):
        """(process, refusal, carry) from an adapter launched through the trusted wrapper (a remote
        host reached over the configured transport): the wrapper's FIRST line, written before it
        became the engine, names the OS identity of the process the engine now is, or the named
        refusal of an engine that could not be run. Anything after that line is the worker's output
        (`carry`). A missing, late or malformed line is unreadable, never a guess."""
        pending, end = b'', min(contract['deadline'], time.time() + ACCEPT_SECONDS)
        while b'\n' not in pending:
            remaining = end - time.time()
            if remaining <= 0 or not select.select([worker.stdout], [], [], remaining)[0]:
                raise ValueError('no identity line')
            chunk = os.read(worker.stdout.fileno(), 65536)
            if not chunk:
                raise ValueError('no identity line')
            pending += chunk
        line, _, carry = pending.partition(b'\n')
        message = json.loads(line)
        # VELDO-0141: the wrapper's line is the first line of the run's execution record.
        worker.identity_line = line
        if not isinstance(message, dict) or message.get('schema') != WRAPPER_SCHEMA:
            raise ValueError('not an identity line')
        if D._text(message.get('refused')) and message['refused'].startswith('spawn_failed:'):
            return None, message['refused'], carry
        if D._identity_problems(message.get('process')):
            raise ValueError('malformed identity')
        return message['process'], None, carry

    @staticmethod
    def _stop(worker):
        """Kill a worker at once: its whole containment group when it has one, and its session."""
        group = getattr(worker, 'group', None)
        if group is not None:
            group.kill()
        try:
            os.killpg(worker.pid, signal.SIGKILL)
        except OSError:
            pass
        worker.wait()

    def _settings(self, *names):
        settings = (self.qualification or {}).get('settings') or {}
        return tuple((settings.get(name) or {}).get('value', C.SETTINGS[name]['default']) for name in names)

    def _graces(self):
        return self._settings('stop_grace_seconds', 'kill_grace_seconds')

    def _heartbeat(self):
        """The profile's heartbeat interval and missed-heartbeat window (VELDO-0041)."""
        return self._settings('heartbeat_seconds', 'heartbeat_window_seconds')

    def _renew(self, watch, contract, contract_digest, process, beat):
        """Renew the claim the contract binds on one heartbeat; a refusal is recorded by name."""
        renewed, refusal = self.renewals.renew(contract, contract_digest, process, beat['seq'], time.time())
        beat['renewed'] = renewed
        if renewed:
            watch.renewals['renewed'] += 1
        elif refusal:
            watch.renewals['refused'] = (watch.renewals['refused'] + [{'seq': beat['seq'], 'refusal': refusal}])[-HB.KEEP:]

    def _stop_asked(self, poller=None):
        """Whether the runner asked for a stop in what it has written on the control channel; with a
        poller, what is readable now is read first (end of the channel unregisters it)."""
        if self.control is None:
            return False
        fd, pending = self.control
        if poller is not None:
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                chunk = b''
            if not chunk:
                poller.unregister(fd)
            pending += chunk
        asked = False
        while b'\n' in pending:
            line, _, rest = bytes(pending).partition(b'\n')
            pending[:] = rest
            with contextlib.suppress(ValueError):
                message = json.loads(line)
                asked = asked or (isinstance(message, dict) and bool(message.get('stop')))
        return asked

    def _reap(self, worker, contract, carry=b'', process=None, contract_digest=None):
        """Feed the worker its packet, hash what it prints, and reap it and its group by the contract
        deadline. The loop sleeps in poll until an OS notification or the next timer: the worker's
        output, its pidfd (its exit), its group's populated event, a heartbeat, a stop request on the
        control channel, the deadline, the missed-heartbeat deadline or the next escalation step; nothing
        is polled for liveness. Closing its output does not end a worker: it is still held to the
        contract deadline. Its exit ends the dispatch: whatever is left in its group is stopped (the
        wrapper's own heartbeat, which ends on the worker's exit, is given SETTLE_SECONDS first), and the
        reap ends once the group is empty (or, SETTLE_SECONDS after the kill, declared not empty in the
        supervision). Every stop it begins escalates on the monotonic clock."""
        packet = {'dispatch_id': contract['dispatch_id'], 'unit': contract['unit'], 'station': contract['station'],
                  'source': contract['source'], 'payload': contract['input']['payload'],
                  'configuration': contract['capability']['configuration']}
        metering = self.metering
        # THE ENGINE PROTOCOL's Guard (VELDO-0155 AC3): what is written first, and whether the input then closes;
        # a held prompt is written only once the Guard releases it, and nothing more once the run stops.
        login = metering.login_guard if metering is not None else None
        opening, close = login.opening(json.dumps(packet).encode()) if login is not None \
            else (json.dumps(packet).encode(), True)
        held = queue.Queue()
        input_failed = threading.Event()

        def feed():
            try:
                worker.stdin.write(opening)
                worker.stdin.flush()
                # Each input the Guard releases, in order, until its last (the prompt) or a stop (None);
                # a role-bound run's capability probe comes before the prompt (VELDO-0127).
                last = close
                while not last:
                    later = held.get()
                    if not later:
                        break
                    data, last = later
                    _write_held_input(worker.stdin, data, last, metering.terminal)
            except OSError:
                input_failed.set()
            finally:
                with contextlib.suppress(OSError):
                    worker.stdin.close()
        feeder = threading.Thread(target=feed, daemon=True)
        feeder.start()
        group, watch = getattr(worker, 'group', None), getattr(worker, 'heartbeat', None)
        stop = C.Stop(group, worker.pid, *self._graces()) if group is not None else None
        start = getattr(group, 'start_evidence', {})
        active = start.get('ActiveEnterTimestampMonotonic', 0) / 10 ** 6
        runtime = start.get('RuntimeMaxUSec')
        # The shared manager cannot dispatch RuntimeMaxSec while it reloads. Keep
        # the same activation-based deadline in this receiver's OS-event wait;
        # startup/heartbeat setup must never restart the owner's runtime clock.
        runtime_deadline = active + runtime / 10 ** 6 if active > 0 and runtime is not None else math.inf
        hasher, size, stopped, cause, code, empty = hashlib.sha256(carry), len(carry), False, None, None, None
        settle, emptied, adapter_exit_monotonic = None, (None, None), None
        output, pidfd = worker.stdout.fileno(), os.pidfd_open(worker.pid)
        # VELDO-0141: the worker's error stream, read here like its output, and the run's execution record.
        errors = worker.stderr.fileno() if getattr(worker, 'stderr', None) is not None else None
        recorder = self.recorder
        poller = select.poll()
        poller.register(output, select.POLLIN)
        poller.register(pidfd, select.POLLIN)
        if errors is not None:
            poller.register(errors, select.POLLIN)
        if group is not None:
            poller.register(group.events, select.POLLPRI | select.POLLERR)
        if watch is not None:
            poller.register(watch.fd, select.POLLIN)
        if self.control is not None:
            poller.register(self.control[0], select.POLLIN)

        def begin(reason):
            nonlocal cause, stopped, code
            if cause is not None or code is not None:
                return
            cause, stopped = reason, reason in ('deadline', 'runtime_cap')
            if stop is not None:
                stop.begin(reason, time.monotonic(), True)
            else:
                self._stop(worker)
                code = worker.returncode

        def take(chunk):
            # VELDO-0155, VELDO-0156: a login that is not a subscription stops it by name, and the held prompt
            # goes to the engine only once its login is confirmed and nothing has stopped it.
            if metering is not None and metering.guarded(chunk):
                begin('configuration_stop' if metering.login_stop.startswith('configuration_stop:') else 'paid_api')
            if metering is not None and metering.feed(chunk):
                begin('usage_cap')
            if login is not None and cause is None and code is None:
                prompt = login.release()
                if prompt is not None:
                    held.put((prompt, getattr(login, 'released', True)))
        if recorder is not None:
            # The wrapper's identity line first, then what the engine printed after it.
            if getattr(worker, 'identity_line', None) is not None:
                recorder.line('wrapper', worker.identity_line)
            # VELDO-0127: a role-bound run's recorded launch set and revision, right after the identity line.
            if (self.binding or {}).get('expected') is not None:
                recorder.line('wrapper', json.dumps({'role_capabilities': self.binding['expected'],
                                                     'role_revision_digest': self.binding['revision']['digest']}).encode())
            recorder.feed('engine', carry)
            recorder.batch()
        take(carry)
        try:
            if self._stop_asked():
                begin('requested')
            while True:
                if code is not None and (group is None or not group.populated()):
                    empty, emptied = True, (time.time(), time.monotonic())
                    break
                if stop is not None and stop.stage == 'abandoned':
                    empty = False
                    break
                live = cause is None and code is None
                waits = [contract['deadline'] - time.time()] if live else []
                if live and runtime_deadline != math.inf:
                    waits.append(runtime_deadline - time.monotonic())
                if live and getattr(login, 'init_deadline', None) is not None and not login.released:
                    waits.append(login.init_deadline - time.monotonic())
                waits += [due - time.monotonic() for due in (stop.due if stop is not None else math.inf,
                                                             watch.due() if watch is not None and live else math.inf,
                                                             settle if settle is not None else math.inf)
                          if due != math.inf]
                timeout = max(0, math.ceil(min(waits) * 1000)) if waits else None
                for fd, _ in poller.poll(timeout):
                    if fd == output:
                        chunk = os.read(output, 65536)
                        if not chunk:
                            poller.unregister(output)
                        size += len(chunk)
                        hasher.update(chunk)
                        if recorder is not None:
                            recorder.feed('engine', chunk)
                        take(chunk)
                    elif fd == errors:
                        chunk = os.read(errors, 65536)
                        if not chunk:
                            poller.unregister(errors)
                        elif recorder is not None:
                            recorder.feed('stderr', chunk)
                    elif fd == pidfd:
                        poller.unregister(pidfd)
                        code = worker.wait()
                        adapter_exit_monotonic = time.monotonic()
                        if stop is not None and group.populated():
                            if group.members() or watch is None:
                                stop.adapter_exited(time.monotonic())
                            else:
                                # Only the wrapper's heartbeat is left, and it ends on the worker's exit.
                                settle = time.monotonic() + HB.SETTLE_SECONDS
                    elif group is not None and fd == group.events:
                        group.populated()
                    elif watch is not None and fd == watch.fd:
                        for beat in watch.read(time.monotonic()):
                            self._renew(watch, contract, contract_digest, process, beat)
                        if not watch.open:
                            poller.unregister(watch.fd)
                    elif self.control is not None and fd == self.control[0] and self._stop_asked(poller):
                        begin('requested')
                if recorder is not None:
                    recorder.batch()
                now = time.monotonic()
                if cause is None and code is None and hasattr(login, 'expired') and login.expired(now):
                    metering.login_stop = login.stop
                    begin('configuration_stop')
                if cause is None and code is None and time.time() >= contract['deadline']:
                    begin('deadline')
                elif cause is None and code is None and watch is not None and watch.expired(now):
                    # No heartbeat for the window with the worker still running: its liveness is
                    # uncertain, and it is stopped (the supervision records when and why).
                    watch.lapse(now)
                    begin('heartbeat_missing')
                elif cause is None and code is None and now >= runtime_deadline:
                    begin('runtime_cap')
                elif stop is not None:
                    if settle is not None and now >= settle:
                        settle = None
                        stop.adapter_exited(now)
                    stop.advance(now)
        finally:
            # A prompt still held is never written: the engine's input closes with nothing more on it.
            held.put(None)
            os.close(pidfd)
            if watch is not None:
                os.close(watch.fd)
        # What is left in the pipe, without waiting on a writer that is no longer in the group.
        os.set_blocking(output, False)
        with contextlib.suppress(OSError):
            for chunk in iter(lambda: os.read(output, 65536), b''):
                size += len(chunk)
                hasher.update(chunk)
                if recorder is not None:
                    recorder.feed('engine', chunk)
                if metering is not None:
                    metering.feed(chunk)
        if errors is not None:
            os.set_blocking(errors, False)
            with contextlib.suppress(OSError):
                for chunk in iter(lambda: os.read(errors, 65536), b''):
                    if recorder is not None:
                        recorder.feed('stderr', chunk)
        feeder.join(timeout=1)
        if (metering is not None and getattr(metering.terminal, 'require_prompt', False)
                and (input_failed.is_set() or not metering.terminal.prompt_written)):
            metering.login_stop = metering.login_stop or 'configuration_stop:prompt_write_failed'
            cause = cause or 'configuration_stop'
        if recorder is not None:
            # Role debug qualification and first-turn size remain in the committed execution record.
            debug = Path(self.run) / RUN_CONFIG / 'role-debug.log' if self.run else None
            if debug is not None and debug.is_file():
                recorder.feed('stderr', debug.read_bytes())
            if (metering is not None and metering.first_turn_context is not None
                    and (self.binding or {}).get('capability')):
                # VELDO-0127 AC4: a role-bound run's first-turn context size, which the marker qualification
                # compares; a run bound to no role keeps its identity line as its one wrapper line (VELDO-0141).
                recorder.line('wrapper', json.dumps({'first_turn_context': metering.first_turn_context}).encode())
            # The record's last lines, and what the exit commits of it.
            self.committed = recorder.close()
        code = worker.poll() if code is None else code
        if group is not None:
            # The last populated read can observe an OOM after its memory.events sample.
            group.sample_memory()
        # A successful adapter and an empty group before the installed runtime
        # deadline are kernel evidence of ordinary exit. Commit that exit before
        # waiting for the manager, then read its terminal result while retained.
        kernel_exit = (group is not None and empty and code == 0 and cause is None
                       and stop.cause is None and active > 0 and runtime is not None
                       and adapter_exit_monotonic is not None and emptied[1] < runtime_deadline
                       and getattr(group, 'memory_sampled', False)
                       and getattr(group, 'oom_kill', 0) == 0)
        result = group.conclude() if group is not None and empty and not kernel_exit else None
        manager_result = result
        if kernel_exit:
            result = 'success'
        # systemd-run may report a shell-style 128 + signal exit, as well as a negative signal.
        signaled = code is not None and (code < 0 or 128 < code <= 192)
        stop_times = [step['monotonic'] for step in (stop.steps if stop is not None else [])
                      if step['step'] in ('terminate', 'kill')]
        if signaled and adapter_exit_monotonic is not None:
            stop_times.append(adapter_exit_monotonic)
        runtime_reached = (active > 0 and runtime is not None
                           and any(at >= active + runtime / 10 ** 6 for at in stop_times))
        # Explicit receiver or owner decisions win; an adapter exit is only an inference.
        cause = cause or (stop.cause if stop is not None else None)
        if cause in (None, 'exit'):
            if manager_result == 'oom-kill' or getattr(group, 'oom_kill', 0) > 0:
                cause, result = 'memory_cap', 'oom-kill'
            elif manager_result == 'timeout' or runtime_reached:
                cause, result, stopped = 'runtime_cap', 'timeout', True
            elif (manager_result in (None, 'unknown') and active > 0 and runtime is not None
                  and adapter_exit_monotonic is not None
                  and adapter_exit_monotonic >= active + runtime / 10 ** 6):
                # An ordinary status can be a handled cap signal; missing evidence is not success.
                cause = 'unknown'
            elif code == 0:
                # A clean adapter exit adds no stop cause. Keep any actual cleanup stop.
                cause = stop.cause if stop is not None else None
            elif result == 'unknown':
                cause = 'unknown'
        if cause == 'runtime_cap':
            # Direct enforcement can empty the scope before the manager resumes
            # and records its own timeout. Preserve both observations separately.
            result = 'timeout'
        self.supervision = {'cause': cause,
                            'steps': stop.steps if stop is not None else [], 'empty': empty,
                            'graces': ({'stop_grace_seconds': stop.grace['cooperative'],
                                        'kill_grace_seconds': stop.grace['terminate']} if stop is not None else None),
                            'empty_at': emptied[0], 'empty_monotonic': emptied[1], 'result': result,
                            'scope_timestamps': getattr(group, 'timestamps', {}),
                            'scope_start': start, 'manager_result': manager_result,
                            'adapter_exit_monotonic': adapter_exit_monotonic,
                            'stop_monotonic': min(stop_times) if stop_times else None,
                            'oom_kill': getattr(group, 'oom_kill', 0), 'deadline': contract['deadline'],
                            'group': group.report() if group is not None else None,
                            'heartbeat': watch.summary() if watch is not None else None}
        self._exit_group = group if kernel_exit else None
        if group is not None and empty and not kernel_exit:
            group.close()
        feeder.join(timeout=5)
        worker.stdout.close()
        if errors is not None:
            worker.stderr.close()
        return {'returncode': code if code is not None and code >= 0 else None,
                'signal': -code if code is not None and code < 0 else None,
                'output_digest': 'sha256:' + hasher.hexdigest(), 'output_bytes': size, 'deadline_stop': stopped}


class Unfunded(Exception):
    """An invocation checked and refused before launch (VELDO-0062); `code` names why."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


class Metering:
    """One subscription invocation's usage, from its reservation to its settlement (VELDO-0062).

    The account is the one the accepted contract records. Each line the CLI prints that reports usage
    or a rate-limit window is kept, raw, in the invocation's receipt file (mode 0600 in a 0700
    directory, beside the store unless the config names `receipts`), after a header naming the
    dispatch, invocation, account, project, unit, provider and boundary; the ledger carries each
    line's digest. Usage goes to VELDO-0036 in sequence, and a report that reaches a cap, or that
    cannot be recorded, stops the worker. A window goes to the account record."""

    def __init__(self, receiver, contract, reservations, accounts, launch):
        self.receiver, self.contract = receiver, contract
        self.reservations, self.accounts = reservations, accounts
        self.dispatch_id = contract['dispatch_id']
        self.account = contract['reservation']['account']
        self.engine = receiver.login['engine']
        # A follow-on resumes a CLI session whose earlier turns the CLI may carry into this invocation's
        # report: the meter is given the session's running total the ledger settled last (None when no
        # invocation settled it, or settled it without one), so only the difference is charged, and only
        # when the CLI reports that same session (the meter decides; another session is charged whole).
        payload = (contract.get('input') or {}).get('payload')
        self.resumes = str(payload['resume']) if isinstance(payload, dict) and payload.get('resume') else None
        settled = reservations.session(self.engine.PROVIDER, self.resumes) if self.resumes else None
        self.meter = self.engine.Meter(zone=receiver.login.get('zone'), resumes=self.resumes,
                                       prior=(settled or {}).get('tokens'))
        self.invocation = 'invocation/' + self.dispatch_id
        self.boundary = RTM.boundary(contract)
        self.guard = RTM.InvocationGuard(reservations, self.engine.PROVIDER, launch, self._stop)
        self.sequence = 0
        self.stop = False
        self.errors = []
        self.receipts = []
        self.window_counts = {}
        self.start = None
        self.settled = False
        self.file = None
        # THE ENGINE PROTOCOL: the engine's terminal output, decoded from the same stream, and its report.
        self.terminal = self.engine.Terminal()
        self.report = None
        # VELDO-0155, VELDO-0156: the stream side of the paid-API guard, and the named stop it made.
        self.login_guard = self.engine.Guard()
        if receiver.binding.get('expected') and self.engine.PROVIDER == 'claude_code':
            self.login_guard.expected = receiver.binding['expected']
            self.terminal.hold_prompt()
        self.login_stop = None
        self.context_pending = b''
        self.first_turn_context = None

    def _stop(self, dispatch_id):
        self.stop = True

    def guarded(self, chunk):
        """Whether the engine's stream now shows a login that is not a subscription (the engine's Guard: the
        init event's apiKeySource), which stops the worker by name before its first turn; true once."""
        stop = self.login_guard.feed(chunk)
        if stop and self.login_stop is None:
            self.login_stop = stop
            return True
        return False

    def started(self):
        """Before spawning the engine, declare and open its receipts and start its clock."""
        self.start = time.monotonic()
        directory = Path(self.receiver.config.get('receipts') or Path(self.receiver.config['store']).parent / 'receipts')
        path = directory / (hashlib.sha256(self.invocation.encode()).hexdigest() + '.jsonl')
        creation = SC.SpaceCreator(getattr(self.receiver, 'space', None), SC.space_owner(self.contract))
        with creation.item('evidence', path):
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            self.file = os.fdopen(os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb')
            header = {'schema': RECEIPTS_SCHEMA, 'dispatch_id': self.dispatch_id, 'invocation': self.invocation,
                      'account': self.account, 'project': self.contract['reservation']['project'],
                      'unit': self.contract['unit'], 'provider': self.engine.PROVIDER, 'boundary': self.boundary}
            self.file.write((json.dumps(header, sort_keys=True) + '\n').encode())
            self.file.flush()

        self.space_items = creation.items

    def feed(self, chunk):
        """Whether the worker must stop, after the observations in `chunk`."""
        self.terminal.feed(chunk)
        if self.first_turn_context is None:
            self.context_pending += chunk
            while b'\n' in self.context_pending:
                raw, _, self.context_pending = self.context_pending.partition(b'\n')
                try:
                    event = json.loads(raw)
                    self.first_turn_context = HANDOFF.context_size(event, self.engine.PROVIDER)
                except (ValueError, AttributeError, TypeError):
                    pass
                if self.first_turn_context is not None:
                    self.context_pending = b''
                    break
        for observation in self.meter.feed(chunk):
            self._observe(observation)
        return self.stop

    def _keep(self, line):
        if self.file is not None:
            self.file.write(line + b'\n')
            self.file.flush()

    def _observe(self, observation):
        self._keep(observation['line'])
        self.receipts.append(observation['receipt'])
        now = time.time()
        try:
            if observation['kind'] in ('window', 'clear_rejection'):
                self.accounts.observe('window/%s/%s/%s' % (self.dispatch_id, observation['receipt'][7:23],
                                                           observation['window_id']),
                                      self.account, observation['window_id'], status=observation['status'],
                                      reset_at=observation['reset_at'], utilization=observation['utilization'],
                                      source_dispatch=self.dispatch_id, now=now,
                                      clear_rejection=observation.get('clear_rejection', False))
                if observation['kind'] == 'clear_rejection':
                    return
                key = (observation['window_id'], observation['status'])
                self.window_counts[key] = self.window_counts.get(key, 0) + 1
                self.receiver.emit(dict(event='window_observed', account=self.account,
                                        dispatch_id=self.dispatch_id, invocation=self.invocation,
                                        window=key[0], status=key[1], utilization=observation['utilization'],
                                        reset_at=observation['reset_at'], receipt=observation['receipt'],
                                        metrics={'window_observations': 1}))
                return
            self.sequence += 1
            result = self.guard.observe('usage/%s/%d' % (self.dispatch_id, self.sequence), self.invocation,
                                        self.sequence, observation['usage'], now=now,
                                        receipts=[observation['receipt']])
            self.stop = self.stop or bool(result.get('stop_required'))
        except (D.RES.Refused, ACC.Refused, S.StoreRefused) as error:
            # A report that cannot be recorded fails closed: the worker stops.
            self.errors.append(error.code)
            self.stop = True

    def _artifact(self, termination, cause):
        """The invocation's artifact (THE ENGINE PROTOCOL): the engine's decoded document, bound to its
        dispatch, invocation, account and pinned executable, kept in its private file; its report {path,
        digest, verdict, complete}. A document that cannot be kept is reported with no path: never complete."""
        self.terminal.close()
        executable = self.receiver.binding or {}
        document = dict(self.terminal.document(termination, cause), dispatch_id=self.dispatch_id,
                        invocation=self.invocation, account=self.account,
                        executable={k: executable.get(k) for k in ('engine', 'version', 'path', 'sha256')},
                        login={'source': self.login_guard.source, 'stop': self.login_stop},
                        first_turn_context=self.first_turn_context)
        data = (json.dumps(document, sort_keys=True) + '\n').encode()
        directory = Path(self.receiver.config.get('artifacts') or Path(self.receiver.config['store']).parent / 'artifacts')
        refusal = None
        try:
            path = directory / (hashlib.sha256(self.invocation.encode()).hexdigest() + '.json')
            creation = SC.SpaceCreator(getattr(self.receiver, 'space', None), SC.space_owner(self.contract))
            with creation.item('evidence', path):
                directory.mkdir(mode=0o700, parents=True, exist_ok=True)
                with os.fdopen(os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as handle:
                    handle.write(data)
            self.space_items = dict(getattr(self, 'space_items', {}), **creation.items)
        except (OSError, SC.SpaceCreationError) as error:
            refusal = getattr(error, 'code', None)
            self.errors.append('artifact:' + (refusal or type(error).__name__))
            path = None
        verdict = document['verdict'] if path is not None else 'artifact_unkept'
        report = {'path': str(path) if path else None, 'digest': 'sha256:' + hashlib.sha256(data).hexdigest(),
                  'verdict': verdict, 'complete': verdict == 'complete' and document['complete'] is True}
        if refusal:
            report['refusal'] = refusal
        return report

    def settle(self, termination, cause):
        """The one final report. `termination` None: the engine never started (not executed)."""
        if self.settled:
            return
        self.settled = True
        now = time.time()
        limit = None
        if termination is None:
            usage, outcome = {}, 'not_executed'
        else:
            for observation in self.meter.close():
                self._observe(observation)
            usage = dict(self.meter.final(), invocations=1,
                         wall_seconds=round(time.monotonic() - (self.start or time.monotonic()), 6))
            if termination.get('deadline_stop'):
                outcome = 'timeout'
            elif cause in ('paid_api', 'configuration_stop'):
                outcome = 'cancelled'
            elif cause in ('requested', 'usage_cap', 'heartbeat_missing'):
                outcome = 'cancelled'
            else:
                outcome = 'completed' if termination.get('returncode') == 0 else 'failed'
            self.report = self._artifact(termination, cause)
            if outcome == 'completed' and not self.report['complete']:
                outcome = 'failed'  # a zero exit is a completion only with its terminal record (THE ENGINE PROTOCOL)
            # VELDO-0160: a run its account's limit stopped ends account_limit, with the window and reset.
            outcome, limit = ACC.classify(outcome, self.meter.limit())
        self.sequence += 1
        session = self.meter.session() if termination is not None else None
        try:
            self.guard.observe('usage/%s/%d' % (self.dispatch_id, self.sequence), self.invocation, self.sequence,
                               usage, now=now, final=True, outcome=outcome, receipts=self.receipts, session=session,
                               limit=limit)
        except (D.RES.Refused, ACC.Refused, S.StoreRefused) as error:
            self.errors.append(error.code)
        finally:
            if self.file is not None:
                self.file.close()


def wrap(argv):
    """THE TRUSTED WRAPPER (`control_launch.py exec [--contained <limits>] [--heartbeat <fd> <seconds>]
    <argv>`). Through a transport it is what runs on the far host (the Mac over SSH, for one); on this
    host it is what the dispatch's containment group is created around (VELDO-0040). It writes the OS
    identity of this very process on its first output line and then becomes the engine by exec, so the
    pid and start time it named are the engine's. Contained, it first applies the profile's per-process
    limits, which every descendant inherits, and after its identity line waits for the receiver's
    release: the receiver checks the group and its controls in between, so no engine code runs
    uncontained. Released, it starts its heartbeat on the channel the receiver passed (VELDO-0041,
    control_heartbeat.start) and closes the channel before the exec. An engine that cannot be found is
    refused by name before anything runs. It opens no store: the receiver records what it reports."""
    held, beat = None, None
    if argv[:1] == ['--contained'] and len(argv) > 2:
        held, argv = json.loads(argv[1]), argv[2:]
    if argv[:1] == ['--heartbeat'] and len(argv) > 3:
        # VELDO-0041: the channel the receiver passed and the profile's heartbeat interval.
        beat, argv = (int(argv[1]), float(argv[2])), argv[3:]
    path = shutil.which(argv[0]) if argv else None
    if not path:
        sys.stdout.write(json.dumps({'schema': WRAPPER_SCHEMA, 'refused': 'spawn_failed:ENOENT'}) + '\n')
        sys.stdout.flush()
        os._exit(127)
    if held is not None:
        C.hold(held)
    # Legacy untimed releases and uncontained transports keep the pre-report
    # deadline. A contained receiver supplies its own absolute release deadline.
    heartbeat_deadline = time.monotonic() + HB.SETUP_SECONDS if beat is not None else None
    sys.stdout.write(json.dumps({'schema': WRAPPER_SCHEMA, 'process': process_identity(os.getpid())}) + '\n')
    sys.stdout.flush()
    release = C.released(0) if held is not None else True
    if not release:
        os._exit(125)
    if beat is not None and type(release) is float:
        heartbeat_deadline = release
    if beat is not None:
        # Released: the heartbeat starts now, in a process of its own, and this process closes the
        # channel before it becomes the engine, so liveness never waits on anything the engine does.
        setup = held.get('heartbeat_setup') if held is not None else None
        try:
            HB.start(*beat)
        except OSError as error:
            if setup is not None:
                os.write(setup, b'T' if isinstance(error, TimeoutError) else b'0')
            os._exit(125)
    # The engine starts with the default dispositions of the signals Python ignores, as subprocess does.
    for number in (signal.SIGPIPE, signal.SIGXFSZ):
        signal.signal(number, signal.SIG_DFL)
    environment = dict(os.environ)
    # THE ENGINE PROTOCOL: the names of the exec-time re-hash reach the clone entrance only, never an engine.
    pinned, expected = environment.pop(ENGINE_PATH, None), environment.pop(ENGINE_DIGEST, None)
    # VELDO-0254 AC3: a risky launch's argv is the confined runner around the engine argv; the engine argv inside
    # it is what is judged and re-hashed here, exactly as when this wrapper execs it itself.
    inner = confined_inner(argv)
    target = argv if inner is None else inner
    target_path = path if inner is None else (shutil.which(inner[0]) or inner[0])
    if pinned is not None and entrance(custody_worker(target)):
        environment[ENGINE_PATH], environment[ENGINE_DIGEST] = pinned, expected
    elif pinned is not None and os.path.realpath(target_path) == os.path.realpath(pinned):
        # This wrapper execs the pinned engine itself (however its path is spelled), so it re-hashes the
        # file now, immediately before the exec; a changed one never runs.
        try:
            unchanged = file_digest(target_path) == expected
        except OSError:
            unchanged = False
        if not unchanged:
            sys.stderr.write('wrapper refused: binding_mismatch:engine_digest\n')
            sys.stderr.flush()
            os._exit(WRAPPER_REFUSED)
    # THE ENVIRONMENT STRIP (VELDO-0155, VELDO-0156), applied to what this wrapper execs and to nothing else.
    environment = engine_environment(environment)
    if beat is not None:
        # Check after all preparation, immediately before success and exec. A
        # placement that completed after our budget never authorizes an engine.
        if time.monotonic() >= heartbeat_deadline:
            if setup is not None:
                os.write(setup, b'T')
            os._exit(125)
        if setup is not None:
            os.write(setup, b'1')
            os.close(setup)
    try:
        os.execve(path, argv, environment)
    except OSError:
        os._exit(126)


def _request(fd, seconds):
    """The runner's request, the first line on the receiver's stdin, and what it has written after it
    (the start of the control channel), read from the descriptor itself so nothing is buffered away."""
    pending, end = b'', time.monotonic() + seconds
    while b'\n' not in pending and len(pending) < 1 << 22:
        remaining = end - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            raise ValueError('no request')
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        pending += chunk
    line, _, rest = pending.partition(b'\n')
    return json.loads(line), bytearray(rest)


END_UNRECORDED = 3  # the receiver's exit status when it failed and the dispatch's record shows no end
# What Launch.wait records for a receiver that exited END_UNRECORDED with its dispatch still running: an
# unknown outcome as every other (its code before the colon), and why.
END_UNRECORDED_REASON = 'outcome_unknown:end_unrecorded'
# What Launch.start records for a receiver that exited END_UNRECORDED before its dispatch's record reached
# running: launch evidence missing as for every receiver that ended there, and why.
EVIDENCE_UNRECORDED_REASON = 'launch_evidence_missing:end_unrecorded'
RECEIVER_EXIT_SECONDS = 2  # how long a receiver whose output has ended is given to exit by itself


def end_recorded(receiver, request):
    """VELDO-0350: whether the record of the dispatch a receiver was asked to launch shows an end
    (exited, refused or unknown). False when it shows none, and when it cannot be read: with no
    receiver, no dispatch named in the request, no record, or a read that raises."""
    try:
        dispatch_id = request['contract']['dispatch_id']
        state = (receiver.dispatches.record(dispatch_id) or {}).get('state')
    except Exception:  # noqa: BLE001 - a record that cannot be read shows no end
        return False
    return state in D.STATES and state not in D.STOPPABLE


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'exec':
        wrap(sys.argv[2:])
        return

    def emit(message):
        sys.stdout.write(json.dumps(message) + '\n')
        sys.stdout.flush()
    receiver, request, status = None, None, 0
    try:
        config = json.loads(Path(sys.argv[1]).read_text())
        request, pending = _request(0, 10)
        receiver = Receiver(config, emit, control=(0, pending))
        receiver.configuration_path = str(Path(sys.argv[1]).resolve())
        receiver.launch(request['contract'])
    except (OSError, ValueError, TypeError, KeyError, D.Refused, S.StoreRefused, C.Refused) as error:
        # Nothing conclusive is claimed: the runner reads the record and settles it.
        emit({'event': 'failed', 'error': type(error).__name__})
        # VELDO-0350: a receiver that failed and left no end on the dispatch's record does not end as a
        # clean one does.
        status = 0 if end_recorded(receiver, request) else END_UNRECORDED
        # The receiver's standard error is the run's receiver log (Launch.receiver_log): the error's class and
        # its refusal code, never its text, and what the status means.
        with contextlib.suppress(OSError, ValueError):
            sys.stderr.write('receiver failed: %s %s; the dispatch\'s record shows %s (exit %d)\n' % (
                type(error).__name__, getattr(error, 'code', None) or '-',
                'its end' if status == 0 else 'no end', status))
            sys.stderr.flush()
    finally:
        if receiver is not None:
            receiver.close()
    if status:
        sys.exit(status)


if __name__ == '__main__':
    main()
