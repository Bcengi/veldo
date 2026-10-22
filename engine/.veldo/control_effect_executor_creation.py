"""The repository provisioner (VELDO-0143 AC2): the repository a settled new-project decision names, created
or adopted under its one identity, as a registered protected effect.

    python3 control_effect_executor_creation.py <provisioner configuration> <decision id>

REGISTERED. EFFECTS names the one effect this executor runs, `repository_provisioning`; the running
authority service starts it (control_service PROTECTED_EFFECTS) for a decision control_project_proposal
judges settled, as the trusted supervisor side, never a worker, and a worker can name neither the
configuration nor the decision's evidence. The configuration (veldo.provisioner/v1, this account's own
0600 file outside every worker clone) is the adoption effect's (VELDO-0161) with the REST origin the
remote is created through (GitHub's own; a loopback stand-in for a disposable remote).

THE ORDER, each step recorded on the repository record, stopping by name at the first failure:

  settlement  the decision must be settled (control_project_proposal.settled). This is checked FIRST:
              without it no record is written, no directory is touched, nothing is created or pushed and
              the adoption signer is never asked (no_settled_decision:<why>).
  adoption    a decision whose proposal found the directory already a Git repository takes the adoption
              path (control_effect_executor_adoption.adopt with this decision): the scaffold commit the
              answered proposal names, the remote owner checked, the signed binding.
  record      otherwise the repository record, `provisioning`, origin `created`, naming the identity, the
              directory, the remote, the decision and the project.
  directory, init, scaffold, author, commit, remote, push
              control_repository_creation's steps, each recorded with what it established (the initial
              commit, the remote GitHub created) and observed with its outcome.
  identity, signature, binding
              the adoption's end (control_effect_executor_adoption.enroll): the one identity, the binding
              the adoption signer signs for this decision alone, the store binding.

A refusal writes the record `failed` with its reason and the step it failed at (`failed_step`), and no later
step runs; a failed repository is never reported ready. The record then waits, `provisioning`, for the
running service to take it on (VELDO-0161 AC2), exactly as an adopted one does. Every observation names the
repository, the identity, the decision and the step, never a token, a key or a signature. Standard library
only.
"""
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('creation_effect_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AD = organ('control_effect_executor_adoption')
CR = organ('control_repository_creation')
PP = organ('control_project_proposal')
P, R, S, CM, CE = AD.P, AD.R, AD.S, AD.CM, AD.CE
SCHEMA = 'veldo.provisioner/v1'
FIELDS = AD.FIELDS + ('github_api',)
EFFECT = 'repository_provisioning'
# Every named refusal a step raises: the creation steps' and the adoption's (each organ loads its own copy of
# control_repository), and an enrollment's.
REFUSALS = (R.Refused, CR.Refused, CE.EnrollmentRefused)


def _directory(run):
    return CR.directory(run['proposal'], run['identity'])


def _init(run):
    return CR.init(run['proposal'], run['identity'])


def _scaffold(run):
    return CR.scaffold(run['proposal'], run['identity'], templates=run['config']['templates'])


def _author(run):
    return CR.author(run['proposal'], run['identity'])


def _commit(run):
    return CR.commit(run['proposal'], run['identity'])


def _remote(run):
    return CR.remote(run['proposal'], run['identity'], origin=run['config']['github_api'], observe=run['observe'],
                     repository=run['proposal']['repository'], request=run['decision'], client=run.get('client'))


def _push(run):
    return CR.push(run['proposal'], run['identity'], run['base_commit'])


# The steps in their order (control_repository_creation.STEPS), each {name: function(run) -> what it
# established}.
STEP_FUNCTIONS = {'directory': _directory, 'init': _init, 'scaffold': _scaffold, 'author': _author,
                  'commit': _commit, 'remote': _remote, 'push': _push}


def load_config(path):
    """The provisioner configuration: the adoption effect's checks (this account's own regular 0600 file),
    of SCHEMA with its fields."""
    try:
        info = os.lstat(str(path))
        config = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        raise R.Refused('invalid_input:config:unreadable', str(path)) from None
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise R.Refused('invalid_input:config:mode', str(path))
    if not isinstance(config, dict) or config.get('schema') != SCHEMA or set(config) != set(FIELDS):
        raise R.Refused('invalid_input:config:schema', str(path))
    return config


def provision(config, decision, *, wait=0.0, clock=time.time, signer=None, client=None):
    """Run the provisioning the settled decision `decision` names (module docstring). Returns {ok, reason,
    repository, state, step, ...} and the observations made; never raises for a named refusal. `client` is
    the GitHub REST client to use (one is made with the identity's token when None)."""
    events = []
    result = {'ok': False, 'request': decision, 'observations': events}
    conn = S.open_store(config['store'])
    journal = (config['journal']['principal'], AD._ssh_signer(config['journal']['key'], 'veldo-journal'))
    generation = config.get('authority_generation') or 1
    base = {'operation': 'provision', 'effect': EFFECT, 'request': decision, 'at': clock()}
    try:
        # The settled decision, before anything is written, made or asked for.
        try:
            judged = PP.settled(S, CM, conn, decision)
        except PP.Refused as error:
            AD._observe(config, events, dict(base, outcome='refused', refusal=error.code, reason=R.reason(error.code),
                                             step='settlement'))
            return dict(result, reason=error.code, step='settlement')
        proposal = judged['proposal']
        repository = proposal['repository']
        base.update(repository=repository, identity=proposal['identity'], settlement=judged['settlement_id'],
                    project=proposal['project'], path=proposal['directory'], mode=proposal['mode'])
        if R.read(conn, repository) is not None:
            code = 'stale_subject:already_provisioned'
            AD._observe(config, events, dict(base, outcome='refused', refusal=code, reason=R.reason(code)))
            return dict(result, reason=code, repository=repository)
    except BaseException:
        conn.close()
        raise
    if proposal['mode'] == 'adopt':
        conn.close()
        adopted = AD.adopt(dict(config, schema=AD.SCHEMA), decision, wait=wait, clock=clock, signer=signer)
        for event in adopted['observations']:
            events.append(event)
        return dict(adopted, observations=events, path='adoption')
    try:
        remote = {'url': proposal['remote']['url'], 'owner': None, 'default_branch': CR.BRANCH,
                  'visibility': proposal['remote']['visibility']}
        R.write(S, conn, journal, repository, 'provisioning', step='settled', at=clock(), generation=generation,
                origin='created', domain_uuid=config['domain_uuid'], name=proposal['remote']['name'],
                identity=proposal['identity'], path=proposal['directory'], remote=remote, request=decision,
                settlement=judged['settlement_id'], project=proposal['project'], scaffold_commit=None,
                base_commit=None, enrollment=None, reason=None, failed_step=None)
        context = AD.Context(config, conn, journal, generation, events, base, clock)
        step = ['directory']
        try:
            identity = P.identity_record(conn, config['domain_uuid'], proposal['identity'])
            run = {'config': config, 'proposal': proposal, 'identity': identity, 'decision': decision,
                   'base_commit': None, 'client': client,
                   'observe': lambda event: AD._observe(config, events, dict(event, at=clock()))}
            if PP.directory_state(proposal['directory']) == 'repository':
                raise R.Refused('stale_subject:directory_is_a_repository', 'the answered proposal creates it')
            for name in CR.STEPS:
                step[0] = name
                done = STEP_FUNCTIONS[name](run) or {}
                fields = {}
                if name == 'commit':
                    run['base_commit'] = fields['base_commit'] = done['base_commit']
                if name == 'remote':
                    remote.update(owner=done['owner'], id=done.get('id'))
                    fields['remote'] = remote
                R.write(S, conn, journal, repository, 'provisioning', step=name, at=clock(), generation=generation,
                        **fields)
                AD._observe(config, events, dict(base, operation='provision_step', step=name, outcome='done',
                                                 at=clock(), **{k: v for k, v in done.items() if k in ('base_commit',
                                                                                                     'owner', 'tip')}))
            adoption = R.settled(S, CM, conn, decision)['proposal']
            binding = AD.enroll(context, decision, adoption, identity, step, signer)
        except REFUSALS as error:
            return dict(context.failed(result, repository, remote, step[0], error), path='creation')
        return dict(context.enrolled(result, repository, remote, binding, adoption, wait), path='creation',
                    base_commit=run['base_commit'])
    finally:
        conn.close()


EFFECTS = {EFFECT: provision}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        sys.stderr.write('usage: control_effect_executor_creation.py <provisioner configuration> <decision id>\n')
        return 2
    try:
        config = load_config(argv[0])
    except R.Refused as error:
        print(json.dumps({'ok': False, 'reason': error.code}))
        return 1
    result = provision(config, argv[1], wait=30.0)
    print(json.dumps({k: v for k, v in result.items() if k != 'observations'}, sort_keys=True))
    return 0 if result.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main())
