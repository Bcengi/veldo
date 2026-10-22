"""The adoption effect (VELDO-0161): a repository the owner names, adopted under one identity on his settled
answer, for the running authority service to take on without a restart.

    python3 control_effect_executor_adoption.py <adoption configuration> <request id>

The configuration (veldo.adoption_effect/v1, this account's own 0600 file, outside every worker clone,
never taken from a worker) names the store and its coordinates, this host's trust, the journal signer and
the adoption signer's key (control_factory_setup lays both down in the protected key directory), the
scaffold templates and the observation log.

THE ORDER, each step recorded on the repository record, stopping by name at the first failure:

  settlement  the request must be a settled owner decision naming one repository for adoption
              (control_repository.settled). This is checked FIRST: without it nothing is written, no
              record is made, nothing is pushed and the adoption signer is never asked
              (no_settled_decision:<why>).
  record      the repository record, `provisioning`, naming the identity, path, remote, the decision and
              the scaffold commit (a repository already recorded refuses stale_subject:already_adopted).
  remote      VELDO-0153's owner check of the proposal's remote against the identity (binding_mismatch:
              remote_owner).
  scaffold    with a scaffold commit named: exactly that commit (control_repository_provisioner.
              scaffold_problems), the default branch fast-forwarded to it and the commit pushed through the
              identity profile (push_refused:remote); with none: the substrate present at the branch tip.
  identity    the repository bound to its one identity (VELDO-0142 configure_identities; never changed).
  signature   the binding written by control_enrollment.enroll, signed by the adoption signer, which judges
              the decision again itself and journals the signature (signature_refused:<why>); the binding
              must verify under this host's trust as the adoption signer's.
  binding     the store binds the repository for the domain (control_store.bind_repositories).

The record then waits, `provisioning`, for the running service, which verifies all of it again and takes
the repository on (control_service.Service.take_on): it adds the repository's receiver configuration and
the record becomes `active`, in the same process. With `wait`, adopt() reports the record's state after at
most that many seconds; a repository the running service did not take on in that time is reported
not_taken_on:timeout and left `provisioning` for the service.

Every observation names the repository, the identity, the decision and the commit, never a token, a key or
a signature. Standard library only.
"""
import json
import os
from pathlib import Path
import stat
import sys
import time

import importlib.util


def organ(name):
    spec = importlib.util.spec_from_file_location('adoption_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P = organ('control_repository_provisioner')
R = P.R
CE = R.CE
S = organ('control_store')
CM = organ('control_membership')
EL = organ('control_eligibility')
SCHEMA = 'veldo.adoption_effect/v1'
FIELDS = ('schema', 'store', 'domain_uuid', 'store_uuid', 'authority_generation', 'host_trust', 'journal',
          'adoption_signer', 'templates', 'observations')


def load_config(path):
    """The adoption configuration, refused unless it is this account's own regular 0600 file of SCHEMA."""
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


def _ssh_signer(key, namespace):
    import subprocess

    def sign(data):
        done = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', namespace], input=data,
                              capture_output=True, timeout=30,
                              env={k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')})
        if done.returncode:
            raise R.Refused('unavailable_service:journal_key', 'the journal key did not sign')
        return done.stdout.decode()
    return sign


def _observe(config, events, event):
    events.append(event)
    if config.get('observations'):
        fd = os.open(config['observations'], os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_CLOEXEC, 0o600)
        with os.fdopen(fd, 'a') as handle:
            handle.write(json.dumps(event, sort_keys=True, default=str) + '\n')


def adopt(config, request, *, wait=0.0, clock=time.time, signer=None):
    """Run the adoption the settled decision `request` names (module docstring). Returns {ok, reason,
    repository, state, ...} and the observations made; never raises for a named refusal. `signer` is the
    AdoptionSigner to ask (one is made from the configuration's key when None)."""
    events = []
    result = {'ok': False, 'request': request, 'observations': events}
    conn = S.open_store(config['store'])
    journal = (config['journal']['principal'], _ssh_signer(config['journal']['key'], 'veldo-journal'))
    generation = config.get('authority_generation') or 1
    ids = {'domain_uuid': config['domain_uuid'], 'store_uuid': config['store_uuid'], 'store_path': config['store']}
    base = {'operation': 'adopt', 'request': request, 'at': clock()}
    repository = None
    try:
        # 1. The settled decision, before anything is written or any signature is asked for.
        try:
            decision = R.settled(S, CM, conn, request)
        except R.Refused as error:
            _observe(config, events, dict(base, outcome='refused', refusal=error.code, reason=R.reason(error.code)))
            return dict(result, reason=error.code)
        proposal = decision['proposal']
        repository = proposal['repository']
        base.update(repository=repository, identity=proposal['identity'], settlement=decision['settlement_id'],
                    path=proposal['path'], scaffold_commit=proposal['scaffold_commit'])
        if R.read(conn, repository) is not None:
            code = 'stale_subject:already_adopted'
            _observe(config, events, dict(base, outcome='refused', refusal=code, reason=R.reason(code)))
            return dict(result, reason=code, repository=repository)
        # 2. The record, provisioning.
        remote = {'url': proposal['remote'], 'owner': None, 'default_branch': proposal['default_branch']}
        R.write(S, conn, journal, repository, 'provisioning', step='settled', at=clock(), generation=generation,
                domain_uuid=config['domain_uuid'], name=proposal['name'], identity=proposal['identity'],
                path=proposal['path'], remote=remote, request=request, settlement=decision['settlement_id'],
                scaffold_commit=proposal['scaffold_commit'], base_commit=proposal['base_commit'], enrollment=None,
                reason=None)
        step = 'remote'
        try:
            record = P.identity_record(conn, config['domain_uuid'], proposal['identity'])
            checked = P.check_remote(record, proposal['remote'], repository=repository, request=request,
                                     observe=lambda event: _observe(config, events, dict(event, at=clock())))
            remote['owner'] = checked['owner']
            # 3. The scaffold: exactly the commit he answered, laid when he was asked, pushed now.
            step = 'scaffold'
            commit = proposal['scaffold_commit']
            if commit is None:
                problems = P.scaffold_problems(proposal)
                if problems:
                    raise R.Refused(problems[0])
            else:
                problems = P.scaffold_problems(proposal)
                if problems:
                    raise R.Refused(problems[0])
                P.advance(proposal)
                P.push(proposal, record)
                _observe(config, events, dict(base, operation='scaffold_push', outcome='pushed', remote_owner=checked['owner'],
                                              at=clock()))
            if P.enrolled(proposal['path']):
                raise R.Refused('invalid_input:already_enrolled', proposal['path'])
            # 4. The one identity, recorded, never changed.
            step = 'identity'
            try:
                R.GI.configure_identities(conn, config['domain_uuid'], [record],
                                          {repository: {'path': proposal['path'], 'identity': proposal['identity']}})
            except R.GI.Refused as error:
                raise R.Refused(error.code) from None
            # 5. The binding, signed by the adoption signer for this decision alone.
            step = 'signature'
            trust = EL.load_host_trust(config['host_trust'])
            if trust is None:
                raise R.Refused('signature_refused:host_trust')
            key = config['adoption_signer']['key']
            if not R.enrolled(Path(trust.enrollment_signers).read_text(), key):
                raise R.Refused('signature_refused:not_enrolled', 'the adoption signer is not among this host\'s '
                                'enrollment signers')
            signer = signer or R.AdoptionSigner(key, S, CM, conn, ids, journal, clock=clock)
            try:
                binding = CE.enroll(proposal['path'], config['domain_uuid'], config['store_uuid'], config['store'],
                                    trust.host_identity, generation, signer.signer(request), R.SIGNER_PRINCIPAL,
                                    clock(), repository_uuid=repository)
            finally:
                for event in signer.observations:
                    _observe(config, events, event)
                signer.observations[:] = []
            problems = CE.verify_binding(proposal['path'], binding, trust.verifier(R.SIGNER_PRINCIPAL, proposal['path']),
                                         trust.host_identity, config['domain_uuid'], config['store_uuid'], generation)
            if problems:
                raise R.Refused('signature_refused:verify:' + problems[0][0])
            # 6. The store binds it.
            step = 'binding'
            try:
                S.bind_repositories(conn, config['domain_uuid'], {repository: proposal['path']})
            except S.StoreRefused as error:
                raise R.Refused(error.code) from None
        except (R.Refused, CE.EnrollmentRefused) as error:
            code = getattr(error, 'code', None) or 'signature_refused:' + getattr(error, 'reason', 'enrollment')
            R.write(S, conn, journal, repository, 'failed', step=step, at=clock(), generation=generation,
                    remote=remote, reason=code)
            _observe(config, events, dict(base, outcome='refused', refusal=code, reason=R.reason(code), step=step))
            return dict(result, reason=code, repository=repository, state='failed')
        digest = CE.binding_digest(binding)
        R.write(S, conn, journal, repository, 'provisioning', step='enrolled', at=clock(), generation=generation,
                remote=remote, enrollment=digest)
        _observe(config, events, dict(base, outcome='enrolled', binding_digest=digest, at=clock()))
        state = _await(conn, repository, wait)
        if state != 'active':
            code = 'not_taken_on:timeout' if state == 'provisioning' else 'not_taken_on:' + str(
                (R.read(conn, repository) or {}).get('reason'))
            _observe(config, events, dict(base, outcome='waiting' if state == 'provisioning' else 'refused',
                                          refusal=code, reason=R.reason(code), at=clock()))
            return dict(result, ok=state == 'provisioning' and not wait, reason=None if not wait else code,
                        repository=repository, state=state, binding_digest=digest,
                        scaffold_commit=proposal['scaffold_commit'])
        _observe(config, events, dict(base, outcome='adopted', binding_digest=digest, at=clock()))
        return dict(result, ok=True, reason=None, repository=repository, state=state, binding_digest=digest,
                    scaffold_commit=proposal['scaffold_commit'])
    finally:
        conn.close()


def _await(conn, repository, wait):
    """The record's state once the running service took it on, failed it, or `wait` seconds passed."""
    deadline = time.monotonic() + max(0.0, float(wait or 0))
    while True:
        state = (R.read(conn, repository) or {}).get('state')
        if state != 'provisioning' or time.monotonic() >= deadline:
            return state
        time.sleep(0.05)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        sys.stderr.write('usage: control_effect_executor_adoption.py <adoption configuration> <request id>\n')
        return 2
    try:
        config = load_config(argv[0])
    except R.Refused as error:
        print(json.dumps({'ok': False, 'reason': error.code}))
        return 1
    result = adopt(config, argv[1], wait=30.0)
    print(json.dumps({k: v for k, v in result.items() if k != 'observations'}, sort_keys=True))
    return 0 if result.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main())
