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
that is not a subscription (`paid_api:...`), nothing accepted, reserved or spawned. The protocol's `Guard`
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
`record_hints`), the exit record commits the record's line count, byte count and digest, and once the end is
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
import errno
import hashlib
import math
import importlib.util
import json
import os
from pathlib import Path
import select
import shutil
import queue
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


D = _organ('control_dispatch')
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
    runtime = environment.pop(ENGINE_RUNTIME, None)
    if runtime is None:
        return environment
    for name in list(environment):
        if name in EXEC_STRIPPED or name.startswith(SESSION_PREFIXES):
            environment.pop(name, None)
    environment.update(json.loads(environment.pop(ENGINE_OVERRIDES, '{}')))
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
                 profile=None):
        self.gate, self.reservations, self.dispatches = gate, reservations, dispatches
        self.receiver, self.account = receiver, account
        self.clock = clock or time.time
        self.observations = []
        self.launches = {}
        # VELDO-0154: dispatches whose receiver died, whose account slot waits for their worker to be gone.
        self.orphans = {}
        # VELDO-0158: settled dispatches whose run directory is left, by dispatch: {group, process}.
        self.runs, self.profile = runs, profile
        self.leftovers = {}
        self.retirements = RT.Retirements(reservations, dispatches, clones=clones, clock=self.clock,
                                          observations=self.observations)

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
        return self.retirements.retire(dispatch_id, outcome, basis)

    def sweep(self):
        """Retry every pending retirement whose obligations have changed since its last attempt, or whose
        clone can now be removed (VELDO-0041); the dispatches whose slots it released. Each preparation
        and each wait makes one, and a scheduler may make one at any time. It also removes each run directory left
        behind whose run the kernel now shows gone (clear_runs)."""
        self.clear_runs()
        return self.retirements.sweep()

    def _left(self, dispatch_id, group=None, process=None):
        """A settled dispatch whose run directory its receiver may have left: removed once its run is gone."""
        if self.runs and os.path.lexists(run_directory(self.runs, dispatch_id)):
            self.leftovers[dispatch_id] = {'group': group, 'process': process}

    def clear_runs(self):
        """VELDO-0158: remove the run directory of every leftover dispatch whose run the kernel shows gone: its
        recorded process ended, its reported group empty or gone, and no live group of this profile's slice its
        scope. A run still alive, or one whose groups cannot be read, keeps its directory until a later call. The
        dispatches whose directories were removed, in order."""
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
            shutil.rmtree(place, ignore_errors=True)
            if os.path.lexists(place):
                self.observations.append({'operation': 'remove_run', 'dispatch_id': dispatch_id, 'outcome': 'refused'})
                continue
            del self.leftovers[dispatch_id]
            self.observations.append({'operation': 'remove_run', 'dispatch_id': dispatch_id, 'outcome': 'removed'})
            removed.append(dispatch_id)
        return removed

    def sweep_runs(self):
        """VELDO-0158: the start sweep. Every run directory under `runs` whose dispatch, of this Runner's domain and
        repository, is settled (exited, refused or unknown) is a leftover, and each whose run the kernel shows gone
        is removed now (clear_runs); one whose run is still alive is kept until a later sweep finds it gone. The
        dispatches whose directories were removed."""
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
                self._left(record['dispatch_id'], process=record.get('process'))
        return self.clear_runs()

    def prepare(self, unit, station, *, holder, source, revision, payload, adapter, configuration,
                deadline, context=None):
        """Decide, reserve and record the complete contract; nothing is invoked. Returns the contract."""
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
        dispatch_id = 'dispatch/%s/%s' % (unit, uuid.uuid4().hex)
        account = self.account
        if hasattr(account, 'reserve'):
            # VELDO-0160: an account pool (control_account_pool.Pool) chooses the account inside the slot's
            # reservation, reading the pool now: an account registered while work runs takes this dispatch.
            account = account.reserve(self.reservations, 'worker/' + dispatch_id, dispatch_id, project, unit,
                                      adapter=adapter, now=now)
        else:
            self.reservations.reserve_worker('worker/' + dispatch_id, dispatch_id, account, project, unit, now=now)
        try:
            entity, version, slot_digest = self._slot(dispatch_id)
            contract = {
                'schema': D.SCHEMA, 'dispatch_id': dispatch_id, 'domain': self.dispatches.domain,
                'repository': self.dispatches.repository, 'unit': unit, 'station': station,
                'attempt': self.dispatches.attempts(unit, station) + 1,
                'source': dict(resolve_source(source, revision), repository_uuid=self.dispatches.repository),
                'input': {'decision': {k: decision[k] for k in ('decision_id', 'station', 'unit', 'domain_uuid',
                                                                'watermark', 'inputs')},
                          'context': decided, 'payload': payload, 'payload_digest': D.digest(payload)},
                'capability': {'adapter': adapter, 'configuration': configuration,
                               'configuration_digest': D.digest(configuration)},
                'reservation': {'entity': entity, 'version': version, 'digest': slot_digest,
                                'account': account, 'project': project},
                'claim': claim, 'deadline': deadline, 'authority_generation': self.dispatches.generation,
            }
            self.dispatches.prepare(contract, now=now)
        except BaseException:
            self._retire(dispatch_id, 'cancelled', 'never_spawned')
            raise
        return contract

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
        if self.child.poll() is None:
            self.child.kill()
        self.child.wait(timeout=10)
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
        commits, and it has ended), accepted is unknown (a stop owed, never a second launch)."""
        record = self.dispatches.record(self.dispatch_id)
        state = (record or {}).get('state')
        digest = (record or {}).get('contract_digest')
        if lost and state == 'prepared':
            record = self.dispatches.refuse(self.dispatch_id, digest, 'receiver_unavailable', now=self.clock(),
                                            expected_state='prepared')
        elif lost and state == 'accepted':
            record = self.dispatches.unknown(self.dispatch_id, digest, 'launch_evidence_missing', now=self.clock(),
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
            # The receiver that owned the worker has ended without recording its end.
            record = self.dispatches.unknown(self.dispatch_id, record['contract_digest'], 'outcome_unknown',
                                             now=self.clock(), expected_state='running',
                                             execution_record=self._record_commitment())
        self.record = record
        return record


def invoke(config_path, contract, dispatches, *, accept_seconds=ACCEPT_SECONDS, environment=None, clock=None):
    """Hand the prepared contract to the trusted receiver process named by the installed config."""
    try:
        with open(config_path) as handle:
            config = json.load(handle)
        if not isinstance(config, dict):
            raise ValueError('receiver config must be an object')
        records = ER.directory(config)
        child = subprocess.Popen([sys.executable, '-B', RECEIVER, str(config_path)], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=environment)
    except (OSError, ValueError, KeyError, TypeError):
        # No receiver ran, so nothing was launched: a conclusive refusal, never a held unit.
        launch = Launch(None, contract, dispatches, clock or time.time)
        launch._settle(lost=True)
        return launch
    launch = Launch(child, contract, dispatches, clock or time.time, records=records)
    try:
        # The receiver's stdin stays open as its control channel: Launch.stop writes a stop request on it.
        child.stdin.write((json.dumps({'contract': contract}) + '\n').encode())
        child.stdin.flush()
    except OSError:
        pass
    return launch.start(accept_seconds)


# The receiver process.

class Receiver:
    """The trusted launch receiver over the installed configuration: {store, journal_key, principal,
    domain, repository, authority_generation, workspace, host_trust, profile, adapters: {name: {argv,
    environment?, identity?}}}. `host_trust` is this host's installed trust file, whose settlement
    signers the recheck's Gate verifies governing decisions with (VELDO-0069), exactly as the front
    door's Gate does. `profile` is this host's worker profile (control_containment); `control` is the
    runner's channel after its request line (fd, what was already read of it), where it asks for a stop.
    Optional `clone_root` names the launcher's known work root for execution record path membership."""

    def __init__(self, config, emit, control=None):
        self.config, self.emit = config, emit
        self.profile = config.get('profile')
        self.qualification = None
        self.supervision = None
        self.control = control
        self.conn = S.open_store(config['store'])
        key = config['journal_key']
        signer = _organ('control_signer')
        self.dispatches = D.Dispatches(S, self.conn, domain=config['domain'], repository=config['repository'],
                                       principal=config['principal'], signer=config['principal'],
                                       sign=lambda data: signer.sign_bytes(key, data, JOURNAL_NAMESPACE),
                                       generation=config.get('authority_generation', 1))
        self.renewals = HB.Renewals(self.dispatches, D)
        self.sign = lambda data: signer.sign_bytes(key, data, JOURNAL_NAMESPACE)
        self.host = config.get('host') or socket.gethostname()
        self.login = None
        self.metering = None
        self.binding = None
        self.token = None
        self.run = None
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
                                    hints=self.config.get('record_hints') or ())

    def _remove_run(self):
        """The run's own directories are removed once its engine has ended (or never started), before its end is
        recorded; a group that could not be emptied keeps them, since what is left of the run may still use them."""
        run, self.run = self.run, None
        if run is not None and (self.supervision or {}).get('empty') is not False:
            # Before the end is reported: the runner stops this receiver once it reads the end, so a link left
            # for close() alone could survive into the clone (VELDO-0127).
            self._unstage_skills()
            shutil.rmtree(run, ignore_errors=True)

    def _settlement_trust(self, EL):
        """VELDO-0069: the decision settlement signers this receiver's Gate verifies with, derived as the
        production construction of the front door's Gate derives them (control_eligibility.enrolled_gate):
        this host's installed trust, named by the configuration's `host_trust`, read for the configured
        workspace. A configuration naming no host trust trusts no settlement, so every governing decision
        blocks; a named trust that is absent or unreadable is a named stop (control_eligibility.Stopped)."""
        path = self.config.get('host_trust')
        if path is None:
            return None
        trust = EL.load_host_trust(path)
        if trust is None:
            raise EL.Stopped('host_trust_required')
        return trust.settlement_trust(self.config.get('workspace'))

    def _recheck(self, contract):
        """The preparation's station decision, rechecked at this accepting boundary as its ticket."""
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
        if contract_digest != record['contract_digest']:
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
        if refusal:
            self.dispatches.refuse(dispatch_id, record['contract_digest'], refusal, now=time.time(),
                                   expected_state='prepared')
            self.emit({'event': 'refused', 'refusal': refusal,
                       'metrics': {'engine_baseline_refused': int(refusal.startswith('missing_evidence:engine_baseline:'))}})
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
            self.emit({'event': 'refused', 'refusal': error.code})
            return
        acceptance = self.dispatches.receipt(dispatch_id, 'accept')
        self.emit({'event': 'accepted', 'acceptance': acceptance})
        try:
            worker = self._invoke(contract, acceptance, adapter)
        except Unfunded as error:
            # Checked and refused before anything was spawned: nothing ran, nothing was reserved.
            self.dispatches.refuse(dispatch_id, contract_digest, error.code, now=time.time(), expected_state='accepted')
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
            self.emit({'event': 'refused', 'refusal': error.code,
                       'credentials': DL.report(dispatch_id, self.credentials, refusal=error, selected=self.selected)})
            return
        except OSError as error:
            self._not_executed()
            refusal = 'spawn_failed:' + errno.errorcode.get(error.errno or 0, type(error).__name__)
            self.dispatches.refuse(dispatch_id, contract_digest, refusal, now=time.time(), expected_state='accepted')
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
        termination = self._reap(worker, contract, carry, process=process, contract_digest=contract_digest)
        if self.metering is not None:
            # The invocation settles before its end is recorded, so the slot's accounting is complete.
            self.metering.settle(termination, (self.supervision or {}).get('cause'))
            if self.metering.report is not None:
                self.emit({'event': 'artifact', 'artifact': self.metering.report})
        self._remove_run()
        if remote and termination['deadline_stop']:
            # Stopping the local transport at the deadline does not show the remote engine ended: its
            # outcome is unknown, and the unit and station stay held.
            self.dispatches.unknown(dispatch_id, contract_digest, 'remote_stop_unconfirmed', now=time.time(),
                                    expected_state='running', execution_record=self.committed)
            self.emit({'event': 'unknown', 'record': self._ended()})
            return
        supervision = self.supervision
        if remote and supervision['cause'] in ('paid_api', 'configuration_stop'):
            # Nor does stopping it for its login (VELDO-0155, VELDO-0156): the unit and station stay held.
            self.dispatches.unknown(dispatch_id, contract_digest, 'remote_stop_unconfirmed', now=time.time(),
                                    expected_state='running', execution_record=self.committed)
            self.emit({'event': 'unknown', 'supervision': supervision, 'record': self._ended()})
            return
        if remote and supervision['cause'] in ('requested', 'usage_cap'):
            # Nor does stopping it on request or at its usage cap: the unit and station stay held.
            self.dispatches.unknown(dispatch_id, contract_digest, 'remote_stop_unconfirmed', now=time.time(),
                                    expected_state='running', execution_record=self.committed)
            self.emit({'event': 'unknown', 'supervision': supervision, 'record': self._ended()})
            return
        if supervision['empty'] is False:
            # Something of the worker's group is still running: never recorded as ended.
            self.dispatches.unknown(dispatch_id, contract_digest, 'containment_not_empty', now=time.time(),
                                    expected_state='running', execution_record=self.committed)
            self.emit({'event': 'unknown', 'supervision': supervision, 'record': self._ended()})
            return
        report = self.metering.report if self.metering is not None else None
        artifact = {k: report[k] for k in ('verdict', 'complete', 'digest')} if report is not None else None
        # VELDO-0141: the exit commits the execution record's line count, byte count and digest.
        self.dispatches.exit(dispatch_id, contract_digest, process, termination, now=time.time(), artifact=artifact,
                             execution_record=self.committed)
        self.emit({'event': 'exited', 'termination': termination, 'supervision': supervision, 'record': self._ended()})

    def _login(self, contract, adapter):
        """VELDO-0062: the subscription login of an engine adapter, read before acceptance from the
        account the accepted contract records. None when it may run; else the named refusal."""
        self.login = None
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
            capability = HANDOFF.materialize(self.conn, self.contract['domain'], self.contract['repository'],
                                            revision, {'project': self._engine_cwd(argv, dispatch_id, False),
                                                       'factory': self.config.get('workspace')})
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
        problem = (problem or module.profile_problem(self.binding, login_environment, cwd)
                   or module.login_problem(bound, login_environment, cwd))
        if problem:
            self.binding, self.token = None, None
            return problem
        return None

    @staticmethod
    def _engine_cwd(argv, dispatch_id, reported):
        """The engine's working directory, where a relative path it reads resolves (THE ENGINE PROTOCOL): the
        work tree of the dispatch's clone when the clone entrance execs it (it changes into it), this
        receiver's own when this receiver's wrapper execs it directly; None for another host's engine, or a
        clone that names no single work tree."""
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
        os.makedirs(runs, mode=0o700, exist_ok=True)
        run = run_directory(runs, dispatch_id)
        os.mkdir(run, 0o700)
        self.run = run
        for name in (RUN_CONFIG, RUN_RUNTIME):
            os.mkdir(os.path.join(run, name), 0o700)
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
                                          repository=self.config['repository'], principal=self.config['principal'],
                                          authorize=D.RES.service_authority, signer=self.config['principal'],
                                          sign=self.sign, generation=self.config.get('authority_generation', 1))
        accounts = ACC.Accounts(S, self.conn, principal=self.config['principal'], signer=self.config['principal'],
                                sign=self.sign, generation=self.config.get('authority_generation', 1))
        spawned = []

        def launch(invocation, configuration):
            # Reserved: from here a spawn that fails is attested not executed, one that starts is metered.
            self.metering = metering
            spawned.append(self._spawn(dispatch_id, acceptance, adapter))
            metering.started()
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
        own directories go."""
        self._remove_run()
        metering, self.metering = self.metering, None
        if metering is not None:
            metering.settle(None, None)

    def _uncontained(self, dispatch_id, contract_digest, error):
        """A worker that could not be contained as declared was never released to its engine: refused
        by name, or unknown when its group could not be emptied."""
        if error.settled:
            self.dispatches.refuse(dispatch_id, contract_digest, error.code, now=time.time(), expected_state='accepted')
            self.emit({'event': 'refused', 'refusal': error.code, 'group': error.group})
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
        environment['VELDO_DISPATCH_ID'] = dispatch_id
        environment['VELDO_DISPATCH_ACCEPTANCE'] = acceptance or ''
        # VELDO-0141: the run's resolved values and its execution record, before the worker exists; its error
        # stream comes to this receiver, which keeps it in the record.
        self._record(adapter, environment)
        if adapter.get('identity', 'local') != 'reported':
            return self._contained(dispatch_id, argv, environment)
        return subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=environment, start_new_session=True, close_fds=True)

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

    def _contained(self, dispatch_id, argv, environment):
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
        wrapper = [sys.executable, '-B', RECEIVER, 'exec', '--contained', json.dumps(group.held()),
                   '--heartbeat', str(beat), repr(float(interval))] + argv
        try:
            with group.admission():
                try:
                    worker = subprocess.Popen(group.command(wrapper), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE, env=group.environment, start_new_session=True,
                                              close_fds=True, pass_fds=(beat,))
                finally:
                    os.close(beat)
                worker.group = group
                try:
                    reported, refusal, _ = self._reported(worker, {'deadline': time.time() + ACCEPT_SECONDS})
                    problems = [refusal] if refusal else group.attach(worker.pid)
                    if not problems and reported.get('pid') != worker.pid:
                        problems = ['spawn_failed:containment:identity']
                    if not problems:
                        HB.make_group(group.cgroup)
                        if self.config.get('clones'):
                            clone = _organ('control_clone')
                            provisioner = clone.Clones(self.dispatches, **self.config['clones'])
                            provisioner.record_group(dispatch_id, group.report())
                except (OSError, ValueError, TypeError, KeyError, AttributeError, subprocess.SubprocessError):
                    problems = ['spawn_failed:containment:unavailable']
                if problems:
                    settled = group.discard(worker)
                    if problems[0] == 'spawn_failed:ENOENT' and settled:
                        raise FileNotFoundError(errno.ENOENT, 'no engine: ' + str(argv[0]))
                    raise C.Refused(problems[0], settled=settled, group=group.report())
            try:
                worker.stdin.write(b'go\n')
                worker.stdin.flush()
            except OSError:
                settled = group.discard(worker)
                raise C.Refused('spawn_failed:containment:release', settled=settled, group=group.report())
        except BaseException:
            os.close(channel)
            raise
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
                    worker.stdin.write(data)
                    worker.stdin.flush()
                    if last and getattr(metering.terminal, 'require_prompt', False):
                        metering.terminal.wrote_prompt()
            except OSError:
                input_failed.set()
            finally:
                with contextlib.suppress(OSError):
                    worker.stdin.close()
        feeder = threading.Thread(target=feed, daemon=True)
        feeder.start()
        group, watch = getattr(worker, 'group', None), getattr(worker, 'heartbeat', None)
        stop = C.Stop(group, worker.pid, *self._graces()) if group is not None else None
        hasher, size, stopped, cause, code, empty = hashlib.sha256(carry), len(carry), False, None, None, None
        settle, emptied = None, (None, None)
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
            cause, stopped = reason, reason == 'deadline'
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
        result = group.conclude() if group is not None and empty else None
        if cause is None and result in ('timeout', 'oom-kill'):
            # systemd stopped the group at a cap: the runtime cap is a deadline, the memory cap is not.
            cause = {'timeout': 'runtime_cap', 'oom-kill': 'memory_cap'}[result]
            stopped = cause == 'runtime_cap'
        self.supervision = {'cause': cause or (stop.cause if stop is not None else None),
                            'steps': stop.steps if stop is not None else [], 'empty': empty,
                            'graces': ({'stop_grace_seconds': stop.grace['cooperative'],
                                        'kill_grace_seconds': stop.grace['terminate']} if stop is not None else None),
                            'empty_at': emptied[0], 'empty_monotonic': emptied[1], 'result': result,
                            'group': group.report() if group is not None else None,
                            'heartbeat': watch.summary() if watch is not None else None}
        if group is not None and empty:
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
        """The engine exists: open its receipt file and start its clock."""
        self.start = time.monotonic()
        directory = Path(self.receiver.config.get('receipts') or Path(self.receiver.config['store']).parent / 'receipts')
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = directory / (hashlib.sha256(self.invocation.encode()).hexdigest() + '.jsonl')
        self.file = os.fdopen(os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb')
        header = {'schema': RECEIPTS_SCHEMA, 'dispatch_id': self.dispatch_id, 'invocation': self.invocation,
                  'account': self.account, 'project': self.contract['reservation']['project'],
                  'unit': self.contract['unit'], 'provider': self.engine.PROVIDER, 'boundary': self.boundary}
        self.file.write((json.dumps(header, sort_keys=True) + '\n').encode())
        self.file.flush()

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
        try:
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            path = directory / (hashlib.sha256(self.invocation.encode()).hexdigest() + '.json')
            with os.fdopen(os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as handle:
                handle.write(data)
        except OSError as error:
            self.errors.append('artifact:' + type(error).__name__)
            path = None
        verdict = document['verdict'] if path is not None else 'artifact_unkept'
        return {'path': str(path) if path else None, 'digest': 'sha256:' + hashlib.sha256(data).hexdigest(),
                'verdict': verdict, 'complete': verdict == 'complete' and document['complete'] is True}

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
    sys.stdout.write(json.dumps({'schema': WRAPPER_SCHEMA, 'process': process_identity(os.getpid())}) + '\n')
    sys.stdout.flush()
    if held is not None and not C.released(0):
        os._exit(125)
    if beat is not None:
        # Released: the heartbeat starts now, in a process of its own, and this process closes the
        # channel before it becomes the engine, so liveness never waits on anything the engine does.
        HB.start(*beat)
    # The engine starts with the default dispositions of the signals Python ignores, as subprocess does.
    for number in (signal.SIGPIPE, signal.SIGXFSZ):
        signal.signal(number, signal.SIG_DFL)
    environment = dict(os.environ)
    # THE ENGINE PROTOCOL: the names of the exec-time re-hash reach the clone entrance only, never an engine.
    pinned, expected = environment.pop(ENGINE_PATH, None), environment.pop(ENGINE_DIGEST, None)
    if pinned is not None and entrance(custody_worker(argv)):
        environment[ENGINE_PATH], environment[ENGINE_DIGEST] = pinned, expected
    elif pinned is not None and os.path.realpath(path) == os.path.realpath(pinned):
        # This wrapper execs the pinned engine itself (however its path is spelled), so it re-hashes the
        # file now, immediately before the exec; a changed one never runs.
        try:
            unchanged = file_digest(path) == expected
        except OSError:
            unchanged = False
        if not unchanged:
            sys.stderr.write('wrapper refused: binding_mismatch:engine_digest\n')
            sys.stderr.flush()
            os._exit(WRAPPER_REFUSED)
    # THE ENVIRONMENT STRIP (VELDO-0155, VELDO-0156), applied to what this wrapper execs and to nothing else.
    environment = engine_environment(environment)
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


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'exec':
        wrap(sys.argv[2:])
        return

    def emit(message):
        sys.stdout.write(json.dumps(message) + '\n')
        sys.stdout.flush()
    receiver = None
    try:
        config = json.loads(Path(sys.argv[1]).read_text())
        request, pending = _request(0, 10)
        receiver = Receiver(config, emit, control=(0, pending))
        receiver.launch(request['contract'])
    except (OSError, ValueError, TypeError, KeyError, D.Refused, S.StoreRefused, C.Refused) as error:
        # Nothing conclusive is claimed: the runner reads the record and settles it.
        emit({'event': 'failed', 'error': type(error).__name__})
    finally:
        if receiver is not None:
            receiver.close()


if __name__ == '__main__':
    main()
