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
  checks      everything that changes nothing, before anything is moved or pushed: exactly the scaffold
              commit the proposal names (control_repository_provisioner.scaffold_problems), or with none the
              substrate present at the branch tip; the remote the repository is configured with
              (invalid_input:remote_not_configured); no command in the repository's own configuration
              (invalid_input:repository_command:<key>); no binding the repository already carries
              (invalid_input:already_enrolled); this host's trust loads (signature_refused:host_trust) and
              names the adoption signer's key among its enrollment signers (signature_refused:not_enrolled;
              a missing key is not enrolled).
  scaffold    with a scaffold commit named: the default branch fast-forwarded to it and the commit pushed
              through the identity profile (push_refused:remote; push_unconfirmed:remote when Git accepted
              the push and the remote's branch does not read back as the commit).
  identity    the repository bound to its one identity (VELDO-0142 configure_identities; never changed).
  signature   the binding written by control_enrollment.enroll, signed by the adoption signer, which judges
              the decision again itself, pins this store, host and generation, and journals the signature
              (signature_refused:<why>); the binding must verify under this host's trust as the adoption
              signer's.
  binding     the store binds the repository for the domain (control_store.bind_repositories).

Any other fault in these steps ends the record `failed` with unknown_outcome:<type>, so no record is left
`provisioning` by an error. The ref the scaffold commit was recorded under is removed once the push is done
or the adoption refused.

TAKING IT ON. The record, `provisioning` with its binding's digest, is then handed to the running authority
service over its authenticated socket (control_client.send from the adopted repository's own workspace, the
packet {operation: take_on, repository_uuid, request} signed with the journal key in TAKE_ON_NAMESPACE),
which verifies all of it again and answers synchronously (control_service.Service.take_on_request): the
repository's receiver configuration is added and the record becomes `active`, in the same process, before
the answer comes back. Nothing waits or polls. A service that is not running leaves the record
`provisioning`, reported not_taken_on:authority_unavailable, and the next instance takes it on at its start;
a service that refuses it writes it `failed` with not_taken_on:<why>.

Every observation names the repository, the identity, the decision and the commit, never a token, a key or
a signature. Standard library only.
"""
import contextlib
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
CC = organ('control_client')
# How long the running service may take to answer a take-on request.
TAKE_ON_SECONDS = 60
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
                              capture_output=True, timeout=30, env=R._quiet_env())
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


def _code(error):
    """The named code of a step's failure: a refusal's own, an enrollment refusal's as signature_refused, and
    anything else unknown_outcome:<type>."""
    if isinstance(error, R.Refused):
        return error.code
    if isinstance(error, CE.EnrollmentRefused):
        return 'signature_refused:' + str(getattr(error, 'reason', None) or 'enrollment')
    return 'unknown_outcome:' + type(error).__name__


def take_on(config, proposal, request, trust, send=None):
    """Hand the record of the adopted repository to the running service and return its answer's refusal
    code, or None when the service took it on (TAKING IT ON). `send` is control_client.send's shape."""
    send = CC.send if send is None else send
    packet = {'operation': R.TAKE_ON_OPERATION, 'repository_uuid': proposal['repository'], 'request': request}
    try:
        response = send(proposal['path'], packet, CE, trust.verifier(R.SIGNER_PRINCIPAL, proposal['path']),
                        _ssh_signer(config['journal']['key'], R.TAKE_ON_NAMESPACE), trust.host_identity,
                        timeout=TAKE_ON_SECONDS)
    except CC.RoutingRefused as error:
        return 'not_taken_on:' + str(error.reason)
    except OSError:
        # No local socket could be made to reach it: no running service answers here.
        return 'not_taken_on:authority_unavailable'
    if not isinstance(response, dict) or not response.get('accepted'):
        return 'not_taken_on:' + str((response or {}).get('reason') if isinstance(response, dict) else 'malformed')
    answer = response.get('result') if isinstance(response.get('result'), dict) else {}
    if answer.get('ok') is True:
        return None
    reason = str(answer.get('reason') or 'refused')
    return reason if reason.startswith('not_taken_on:') else 'not_taken_on:' + reason


def adopt(config, request, *, clock=time.time, signer=None, send=None):
    """Run the adoption the settled decision `request` names (module docstring). Returns {ok, reason,
    repository, state, ...} and the observations made; never raises. ok is the adoption itself (the record
    is not failed); reason is None only once the running service took it on. `signer` is the AdoptionSigner
    to ask (one is made from the configuration's key when None); `send` reaches the running service
    (control_client.send when None)."""
    events = []
    result = {'ok': False, 'request': request, 'observations': events}
    base = {'operation': 'adopt', 'request': request, 'at': clock()}
    try:
        conn = S.open_store(config['store'])
    except Exception as error:  # noqa: BLE001 - a store that does not open is a named outcome
        code = 'unknown_outcome:' + type(error).__name__
        _observe(config, events, dict(base, outcome='refused', refusal=code, reason=R.reason(code)))
        return dict(result, reason=code)
    journal = (config['journal']['principal'], _ssh_signer(config['journal']['key'], 'veldo-journal'))
    generation = config.get('authority_generation') or 1
    ids = {'domain_uuid': config['domain_uuid'], 'store_uuid': config['store_uuid'], 'store_path': config['store']}
    repository, written = None, False
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
        written = True
        step = 'remote'
        try:
            record = P.identity_record(conn, config['domain_uuid'], proposal['identity'])
            checked = P.check_remote(record, proposal['remote'], repository=repository, request=request,
                                     observe=lambda event: _observe(config, events, dict(event, at=clock())))
            remote['owner'] = checked['owner']
            # 3. Every check that changes nothing, before anything is moved or pushed.
            step = 'scaffold'
            problems = P.scaffold_problems(proposal)
            if problems:
                raise R.Refused(problems[0])
            P.check_configured_remote(proposal['path'], proposal['default_branch'], proposal['remote'])
            P.refuse_commands(proposal['path'])
            if P.enrolled(proposal['path']):
                raise R.Refused('invalid_input:already_enrolled', proposal['path'])
            step = 'signature'
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
            # 4. The scaffold: exactly the commit he answered, laid when he was asked, pushed now.
            step = 'scaffold'
            if proposal['scaffold_commit'] is not None:
                P.advance(proposal)
                P.push(proposal, record)
                _observe(config, events, dict(base, operation='scaffold_push', outcome='pushed', remote_owner=checked['owner'],
                                              at=clock()))
                P.remove_scaffold_ref(proposal['path'], repository)
            # 5. The one identity, recorded, never changed.
            step = 'identity'
            try:
                R.GI.configure_identities(conn, config['domain_uuid'], [record],
                                          {repository: {'path': proposal['path'], 'identity': proposal['identity']}})
            except R.GI.Refused as error:
                raise R.Refused(error.code) from None
            # 6. The binding, signed by the adoption signer for this decision alone.
            step = 'signature'
            pinned = dict(ids, host_identity=trust.host_identity, authority_generation=generation)
            signer = signer or R.AdoptionSigner(key, S, CM, conn, pinned, journal, clock=clock)
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
            # 7. The store binds it.
            step = 'binding'
            try:
                S.bind_repositories(conn, config['domain_uuid'], {repository: proposal['path']})
            except S.StoreRefused as error:
                raise R.Refused(error.code) from None
            digest = CE.binding_digest(binding)
            step = 'enrolled'
            R.write(S, conn, journal, repository, 'provisioning', step='enrolled', at=clock(), generation=generation,
                    remote=remote, enrollment=digest)
        except Exception as error:  # noqa: BLE001 - every fault ends the record failed, by name
            code = _code(error)
            P.remove_scaffold_ref(proposal['path'], repository)
            state = 'failed'
            try:
                R.write(S, conn, journal, repository, 'failed', step=step, at=clock(), generation=generation,
                        remote=remote, reason=code)
            except Exception:  # noqa: BLE001 - reported as it stands
                state = (R.read(conn, repository) or {}).get('state')
            _observe(config, events, dict(base, outcome='refused', refusal=code, reason=R.reason(code), step=step))
            return dict(result, reason=code, repository=repository, state=state)
        _observe(config, events, dict(base, outcome='enrolled', binding_digest=digest, at=clock()))
        # 8. The running service takes it on, and answers.
        refusal = take_on(config, proposal, request, trust, send)
        state = (R.read(conn, repository) or {}).get('state')
        done = dict(result, ok=state in ('provisioning', 'active'), repository=repository, state=state,
                    binding_digest=digest, scaffold_commit=proposal['scaffold_commit'])
        if state == 'active':
            _observe(config, events, dict(base, outcome='adopted', binding_digest=digest, at=clock()))
            return dict(done, reason=None)
        code = refusal or 'not_taken_on:' + str(state)
        _observe(config, events, dict(base, outcome='waiting' if state == 'provisioning' else 'refused',
                                      refusal=code, reason=R.reason(code), at=clock()))
        return dict(done, reason=code)
    except Exception as error:  # noqa: BLE001 - never raises: a fault before or after the steps is named
        code = 'unknown_outcome:' + type(error).__name__
        _observe(config, events, dict(base, outcome='refused', refusal=code, reason=R.reason(code)))
        state = None
        if written:
            with contextlib.suppress(Exception):
                state = (R.read(conn, repository) or {}).get('state')
        return dict(result, reason=code, repository=repository, state=state)
    finally:
        conn.close()


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
    result = adopt(config, argv[1])
    print(json.dumps({k: v for k, v in result.items() if k != 'observations'}, sort_keys=True))
    return 0 if result.get('state') == 'active' else 1


if __name__ == '__main__':
    sys.exit(main())
