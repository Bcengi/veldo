"""PRE-FIX STAND-IN, used only by proof/VELDO-0039/red.py. It is NOT production code.

What the repository had at d95a809 for the dispatch authority: nothing. No dispatch record, no
contract, no schema of states or transitions, no hold on a unit and station. This module gives the
suite the same names over that absence: every read finds nothing, every observation is accepted and
changes nothing, and the error taxonomy is VELDO-0052's (the only one d95a809 had). The claim organ
is d95a809's own control_claim.
"""
import importlib.util
from pathlib import Path


def _organ(name):
    spec = importlib.util.spec_from_file_location('prefix_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = _organ('control_store')
CLM = _organ('control_claim')
EL = _organ('control_eligibility')
STATES = ()
TRANSITIONS = {}
HOLDING = ()
STOP = None
Refused = EL.Refused


def taxonomy(code):
    return EL.taxonomy(code)


def digest(value):
    return S.digest_of(value)


def record_id(dispatch_id):
    return 'dispatch:' + str(dispatch_id)


def contract_problems(contract):
    return ['contract']


class Dispatches:
    def __init__(self, store, conn, *, domain, repository, principal, signer, sign, generation=1, observe=None):
        self.store, self.conn, self.domain, self.repository = store, conn, domain, repository
        self.principal, self.generation = principal, generation

    def record(self, dispatch_id):
        return None

    def version(self, dispatch_id):
        return 0

    def active(self, unit, station):
        return None

    def attempts(self, unit, station):
        return 0

    def receipt(self, dispatch_id, action):
        return None

    def status(self):
        return {'accepted': 0, 'refused': 0, 'pending': [], 'stopped': [], 'states': {}}

    def prepare(self, contract, *, now):
        return None

    def accept(self, dispatch_id, contract_digest, receiver, *, now):
        return None

    def run(self, dispatch_id, contract_digest, process, *, now):
        return None

    def exit(self, dispatch_id, contract_digest, process, termination, *, now):
        return None

    def refuse(self, dispatch_id, contract_digest, refusal, *, now, expected_state=None):
        return None

    def unknown(self, dispatch_id, contract_digest, reason, *, now, expected_state=None):
        return None
