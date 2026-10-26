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
              path (control_effect_executor_adoption.adopt with this decision), all of it the adoption
              effect's own: its lock and its INTERRUPTED rule, the scaffold commit the answered proposal
              names, its checks before the push, the signed binding and the hand-off.
  lock        otherwise the run holds the adoption effect's lock for the repository (hold; another live
              run refuses stale_subject:provisioning_in_progress); a record this decision left
              `provisioning` with no enrollment is a run that ended, written `failed` with
              unknown_outcome:interrupted at the step it names (what it made stays, for the owner); any other
              record refuses stale_subject:already_provisioned.
  record      the repository record, `provisioning`, origin `created`, naming the identity, the directory,
              the remote, the decision and the project.
  checks      before any directory is made, every refusal the adoption's end would make from this host and
              the store alone (preflight, the adoption effect's own checks): this host's trust and the
              adoption signer's key among its enrollment signers (signature), the identity binding (identity,
              check only), the store's binding of the repository (binding) and the configured generation
              (signature).
  directory, init, scaffold, author, commit, remote, push
              control_repository_creation's steps, each recorded with what it established (the initial
              commit, the remote GitHub created) and observed with its outcome. Before GitHub is asked for the
              remote, the repository's own configuration is judged as the adoption judges it before its push
              (control_repository_provisioner.refuse_commands and refuse_transport_config, the identity
              transport's own judge), so no remote is created for a push that would be refused (failed at
              `remote`).
  identity, signature, binding
              the adoption's end (enroll): the one identity, the binding the adoption signer signs for this
              decision alone, pinned to this store, host and generation, verified under this host's trust,
              and the store's binding; the record then names the binding's digest.
  take on     the record handed to the running authority service over its authenticated socket, exactly as
              an adopted one (control_effect_executor_adoption.take_on): the service judges it again and
              answers synchronously, the record `active` before the answer comes back. Nothing waits or
              polls; a service that is not running leaves it `provisioning`, reported
              not_taken_on:authority_unavailable, for the next instance to take on at its start.

Any fault in these steps writes the record `failed` with its named reason and the step it failed at
(`failed_step`), and no later step runs; a failed repository is never reported ready. Every observation
names the repository, the identity, the decision and the step, never a token, a key or a signature.
Standard library only.
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
P, R, S, CM, CE, EL = AD.P, AD.R, AD.S, AD.CM, AD.CE, AD.EL
SCHEMA = 'veldo.provisioner/v1'
FIELDS = AD.FIELDS + ('github_api',)
EFFECT = 'repository_provisioning'
# Every named refusal a step raises: the creation steps' and the adoption's (each organ loads its own copy of
# control_repository), and an enrollment's.
REFUSALS = (R.Refused, CR.Refused, CE.EnrollmentRefused)


def _code(error):
    """The named code of a step's failure: a creation step's refusal its own, else the adoption effect's naming
    (a refusal's own code, an enrollment refusal's as signature_refused, anything else unknown_outcome:<type>)."""
    if isinstance(error, CR.Refused):
        return error.code
    return AD._code(error)


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


def provision(config, decision, *, clock=time.time, signer=None, client=None, send=None):
    """Run the provisioning the settled decision `decision` names (module docstring). Returns {ok, reason,
    repository, state, step, ...} and the observations made; never raises for a named refusal. ok is the
    provisioning itself (the record is not failed); reason is None only once the running service took the
    repository on. `client` is the GitHub REST client to use (one is made with the identity's token when None);
    `send` reaches the running service (control_client.send when None)."""
    events = []
    result = {'ok': False, 'request': decision, 'observations': events}
    conn = S.open_store(config['store'])
    journal = (config['journal']['principal'], AD._ssh_signer(config['journal']['key'], 'veldo-journal'))
    generation = config.get('authority_generation') or 1
    base = {'operation': 'provision', 'effect': EFFECT, 'request': decision, 'at': clock()}
    held = None
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
        if proposal['mode'] == 'adopt':
            # The adoption effect holds its own lock and judges its own record (VELDO-0161 INTERRUPTED).
            conn.close()
            adopted = AD.adopt(dict(config, schema=AD.SCHEMA), decision, clock=clock, signer=signer, send=send)
            events.extend(adopted['observations'])
            return dict(adopted, observations=events, path='adoption')
        held = AD.hold(config, repository)
        if held is None:
            code = 'stale_subject:provisioning_in_progress'
            AD._observe(config, events, dict(base, outcome='refused', refusal=code, reason=R.reason(code)))
            return dict(result, reason=code, repository=repository)
        existing = R.read(conn, repository)
        if (existing is not None and existing.get('state') == 'provisioning' and not existing.get('enrollment')
                and existing.get('request') == decision):
            # INTERRUPTED, as an adoption's: this run holds the lock, so the run that wrote it ended.
            code, step = 'unknown_outcome:interrupted', ((existing.get('history') or [{}])[-1]).get('step')
            R.write(S, conn, journal, repository, 'failed', step=step or 'settled', at=clock(), generation=generation,
                    reason=code, failed_step=step or 'settled')
            AD._observe(config, events, dict(base, outcome='refused', refusal=code, reason=R.reason(code), step=step))
            return dict(result, reason=code, repository=repository, state='failed', step=step, path='creation')
        if existing is not None:
            code = 'stale_subject:already_provisioned'
            AD._observe(config, events, dict(base, outcome='refused', refusal=code, reason=R.reason(code)))
            return dict(result, reason=code, repository=repository)
        remote = {'url': proposal['remote']['url'], 'owner': None, 'default_branch': CR.BRANCH,
                  'visibility': proposal['remote']['visibility']}
        R.write(S, conn, journal, repository, 'provisioning', step='settled', at=clock(), generation=generation,
                origin='created', domain_uuid=config['domain_uuid'], name=proposal['remote']['name'],
                identity=proposal['identity'], path=proposal['directory'], remote=remote, request=decision,
                settlement=judged['settlement_id'], project=proposal['project'], scaffold_commit=None,
                base_commit=None, enrollment=None, reason=None, failed_step=None)
        step = ['directory']
        run = {'base_commit': None}
        try:
            identity = P.identity_record(conn, config['domain_uuid'], proposal['identity'])
            run = {'config': config, 'proposal': proposal, 'identity': identity, 'decision': decision,
                   'base_commit': None, 'client': client,
                   'observe': lambda event: AD._observe(config, events, dict(event, at=clock()))}
            if PP.directory_state(proposal['directory']) == 'repository':
                raise R.Refused('stale_subject:directory_is_a_repository', 'the answered proposal creates it')
            # Every refusal the end of the adoption would make from the store and this host alone, before any
            # directory is made or GitHub is asked (VELDO-0161's checks that change nothing).
            trust, key = preflight(config, conn, proposal, identity, generation, step)
            for name in CR.STEPS:
                step[0] = name
                if name == 'remote':
                    # The repository's own configuration, judged as the adoption judges it before its push: nothing
                    # a local step would run and nothing the identity transport refuses at the push, before
                    # GitHub is asked to create anything.
                    P.refuse_commands(proposal['directory'])
                    P.refuse_transport_config(proposal['directory'], proposal['remote']['url'])
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
            binding = enroll(config, conn, journal, generation, events, decision, adoption, identity, trust, key,
                             signer, clock, step)
            step[0] = 'enrolled'
            digest = CE.binding_digest(binding)
            R.write(S, conn, journal, repository, 'provisioning', step='enrolled', at=clock(), generation=generation,
                    remote=remote, enrollment=digest)
        except Exception as error:  # noqa: BLE001 - every fault ends the record failed, by name (VELDO-0161)
            code = _code(error)
            state = 'failed'
            try:
                R.write(S, conn, journal, repository, 'failed', step=step[0], at=clock(), generation=generation,
                        remote=remote, reason=code, failed_step=step[0])
            except Exception:  # noqa: BLE001 - reported as it stands
                state = (R.read(conn, repository) or {}).get('state')
            AD._observe(config, events, dict(base, outcome='refused', refusal=code, reason=R.reason(code),
                                             step=step[0]))
            return dict(result, reason=code, repository=repository, state=state, step=step[0], path='creation')
        AD._observe(config, events, dict(base, outcome='enrolled', binding_digest=digest, at=clock()))
        # The running service takes it on, and answers (VELDO-0161 TAKING IT ON).
        refusal = AD.take_on(config, adoption, decision, trust, send)
        state = (R.read(conn, repository) or {}).get('state')
        done = dict(result, ok=state in ('provisioning', 'active'), repository=repository, state=state,
                    binding_digest=digest, path='creation', base_commit=run['base_commit'])
        if state == 'active':
            AD._observe(config, events, dict(base, outcome='created', binding_digest=digest, at=clock()))
            return dict(done, reason=None)
        code = refusal or 'not_taken_on:' + str(state)
        AD._observe(config, events, dict(base, outcome='waiting' if state == 'provisioning' else 'refused',
                                         refusal=code, reason=R.reason(code), at=clock()))
        return dict(done, reason=code)
    finally:
        if held is not None:
            os.close(held)
        conn.close()


def preflight(config, conn, proposal, identity, generation, step):
    """The adoption's checks that change nothing (control_effect_executor_adoption THE ORDER, checks), for a
    repository not made yet: this host's trust loads and names the adoption signer's key among its enrollment
    signers, the identity binding, the store's binding of the repository and the configured generation against
    the store's. `step` holds the name of the step each check is the refusal of, for the failure record.
    Returns the trust and the adoption signer's key."""
    repository, path = proposal['repository'], proposal['directory']
    step[0] = 'signature'
    trust = EL.load_host_trust(config['host_trust'])
    if trust is None:
        raise R.Refused('signature_refused:host_trust')
    key = config['adoption_signer']['key']
    try:
        signers = Path(trust.enrollment_signers).read_text()
    except OSError:
        raise R.Refused('signature_refused:host_trust', 'the enrollment signers do not read') from None
    if not R.enrolled(signers, key):
        raise R.Refused('signature_refused:not_enrolled', 'the adoption signer is not among this host\'s '
                        'enrollment signers')
    step[0] = 'identity'
    try:
        R.GI.configure_identities(conn, config['domain_uuid'], [identity],
                                  {repository: {'path': path, 'identity': proposal['identity']}}, check_only=True)
    except R.GI.Refused as error:
        raise R.Refused(error.code) from None
    step[0] = 'binding'
    if S.bound_repository(conn, config['domain_uuid'], repository) not in (None, os.path.realpath(path)):
        raise R.Refused('repository_binding_conflict', 'the store binds the repository at another path')
    step[0] = 'signature'
    if generation < R.store_generation(conn):
        raise R.Refused('signature_refused:scope:generation', 'the configured generation is below the store\'s')
    return trust, key


def enroll(config, conn, journal, generation, events, decision, adoption, identity, trust, key, signer, clock, step):
    """The adoption's end for the created repository (control_effect_executor_adoption THE ORDER, identity,
    signature, binding): the one identity, the binding the adoption signer signs for the settled decision alone,
    pinned to this store, host and generation and verified under this host's trust, and the store's binding.
    `step` holds the current step's name for the failure record. Returns the binding."""
    repository, path = adoption['repository'], adoption['path']
    step[0] = 'identity'
    if P.enrolled(path):
        raise R.Refused('invalid_input:already_enrolled', path)
    try:
        R.GI.configure_identities(conn, config['domain_uuid'], [identity],
                                  {repository: {'path': path, 'identity': adoption['identity']}})
    except R.GI.Refused as error:
        raise R.Refused(error.code) from None
    step[0] = 'signature'
    ids = {'domain_uuid': config['domain_uuid'], 'store_uuid': config['store_uuid'], 'store_path': config['store'],
           'host_identity': trust.host_identity, 'authority_generation': generation}
    signer = signer or R.AdoptionSigner(key, S, CM, conn, ids, journal, clock=clock)
    try:
        binding = CE.enroll(path, config['domain_uuid'], config['store_uuid'], config['store'], trust.host_identity,
                            generation, signer.signer(decision), R.SIGNER_PRINCIPAL, clock(), repository_uuid=repository)
    finally:
        for event in signer.observations:
            AD._observe(config, events, event)
        signer.observations[:] = []
    problems = CE.verify_binding(path, binding, trust.verifier(R.SIGNER_PRINCIPAL, path), trust.host_identity,
                                 config['domain_uuid'], config['store_uuid'], generation)
    if problems:
        raise R.Refused('signature_refused:verify:' + problems[0][0])
    step[0] = 'binding'
    try:
        S.bind_repositories(conn, config['domain_uuid'], {repository: path})
    except S.StoreRefused as error:
        raise R.Refused(error.code) from None
    return binding


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
    result = provision(config, argv[1])
    print(json.dumps({k: v for k, v in result.items() if k != 'observations'}, sort_keys=True))
    return 0 if result.get('state') == 'active' else 1


if __name__ == '__main__':
    sys.exit(main())
