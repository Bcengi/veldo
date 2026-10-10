"""Authority adapter for the Mac host seam, VELDO-0039/0036/0062/0124.

The authority keeps its store and keys on Linux. Supply a trusted Supervisor host
endpoint (transport/routing belongs to VELDO-0125), not worker supplied lifecycle
reports. Every initial, retry and follow-on invocation takes InvocationGuard's
pre-call reservation. Missing usage is deliberately left reserved for the existing
0062 settlement path; an OS exit cannot invent usage or successful work.
"""
import importlib.util
from pathlib import Path
import time


def organ(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


D = organ('control_dispatch')
RR = organ('control_reservation_runtime')
ACC = organ('control_accounts')
P = organ('project_runner_macos_profile')
ENGINES = (organ('control_engine_claude'), organ('control_engine_codex'))
CREDENTIALS = frozenset().union(*(e.CREDENTIALS for e in ENGINES))
STRIPPED = CREDENTIALS.union(*(e.SETTINGS for e in ENGINES))


class Receiver:
    """Invoked after the ordinary Runner prepares a complete admitted contract.

recheck is the authority's current eligibility check, evaluated before acceptance.
cleanup removes this dispatch's clone only after the host observed its whole group
empty, returning True only once clone files/pins are gone. Neither is worker code.
"""
    def __init__(self, dispatches, reservations, accounts, host, receiver_identity, *, recheck, cleanup,
                 clock=time.time):
        self.dispatches, self.reservations, self.accounts, self.host = dispatches, reservations, accounts, host
        self.identity, self.recheck, self.cleanup, self.clock = receiver_identity, recheck, cleanup, clock
        self.runs = {}

    def start(self, contract, clone, scratch):
        dispatch, digest = contract['dispatch_id'], D.digest(contract)
        record = self.dispatches.record(dispatch)
        if record is None or record['state'] != 'prepared':
            raise P.Refused('stale_version:not_prepared')
        if record['contract_digest'] != digest:
            raise P.Refused('binding_mismatch:contract_digest')
        try:
            refusal = self.recheck(contract)
            if refusal:
                raise P.Refused(refusal)
            engine = contract['capability']['adapter']
            account = self.accounts.get(contract['reservation']['account'])
            if not account or account['provider'] != engine:
                raise P.Refused('binding_mismatch:account_provider')
            host = self.host.os.facts()['host']
            variable, login = ACC.profile(account, host)
            configured = contract['capability']['configuration'].get('environment', {})
            environment = ACC.login_environment({'PATH': '/usr/bin:/bin:/usr/sbin:/sbin'}, account, host,
                                                 STRIPPED, configured, CREDENTIALS)
            # Run scoped HOME and TMPDIR: no engine falls back to the owner's home via getpwuid.
            environment.update(self.host.run_environment(dispatch, scratch), VELDO_DISPATCH_ID=dispatch)
            request = dict(contract=contract, contract_digest=digest, acceptance='preflight', engine=engine,
                           clone=clone, scratch=scratch, login_profile=login, environment=environment)
            self.host.preflight(request)
        except Exception as error:
            self.dispatches.refuse(dispatch, digest, getattr(error, 'code', 'unsupported_configuration:host'),
                                   now=self.clock(), expected_state='prepared')
            raise
        self.dispatches.accept(dispatch, digest, self.identity, now=self.clock())
        request['acceptance'] = self.dispatches.receipt(dispatch, 'accept')
        request['environment']['VELDO_DISPATCH_ACCEPTANCE'] = request['acceptance']
        invocation = 'invocation/' + dispatch
        started = []

        def launch(identity, configuration):
            started.append(self.host.start(request))

        guard = RR.InvocationGuard(self.reservations, engine, launch,
                                   lambda identity: self.runs[identity]['run'].stop('allowance')
                                   if identity in self.runs else None)
        try:
            receipt = guard.invoke('macos-call/' + dispatch, dispatch, invocation, RR.boundary(contract),
                                   min(self.host.profile['runtime_seconds'], contract['deadline'] - self.clock()),
                                   contract['capability']['configuration'], now=self.clock())
            if receipt['replayed'] or not started:
                raise P.Refused('unknown_outcome:invocation_replayed')
            run = started[0]
            self.runs[dispatch] = dict(run=run, guard=guard, invocation=invocation, contract=contract)
            self.dispatches.run(dispatch, digest, run.process, now=self.clock())
            return run
        except Exception:
            if started:
                started[0].stop('authority_observation_failed')
                started[0].wait()
            self.dispatches.unknown(dispatch, digest, 'outcome_unknown', now=self.clock(), expected_state='accepted')
            raise

    def wait(self, dispatch):
        entry = self.runs[dispatch]
        result = entry['run'].wait()
        digest = D.digest(entry['contract'])
        if result['state'] == 'exited':
            # An exited provider without an artifact is never a completed build.
            self.dispatches.exit(dispatch, digest, result['process'], result['termination'], now=self.clock(),
                                 artifact=dict(verdict='incomplete', complete=False, digest=P.digest(None)))
        else:
            self.dispatches.unknown(dispatch, digest, 'outcome_unknown', now=self.clock(), expected_state='running')
        return result

    def retire(self, dispatch):
        run = self.runs[dispatch]['run']

        def lifecycle(identity):
            seen = run.retirement()
            if identity != dispatch or self.dispatches.record(dispatch)['state'] != 'exited':
                seen['outcome_known'] = False
            if not seen['outcome_known']:
                raise P.Refused('unknown_outcome:retirement')
            if seen['terminated'] and seen['cleaned'] and seen['outcome_known']:
                seen['cleaned'] = self.cleanup(dispatch) is True
            seen['outcome'] = 'cancelled'
            return seen

        result = self.reservations.retire('macos-retire/' + dispatch, dispatch, lifecycle, now=self.clock())
        run.release()
        return result
