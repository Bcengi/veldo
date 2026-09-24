"""STAND-IN, proof/VELDO-0050/red.py only. 91fb549 has no proof service and no control_proof.py. This
names what suite 64 calls and does nothing: no observation or bundle is stored, nothing resolves, no
refusal is named and no error class is known."""
SCHEMA = None


class Refused(Exception):
    def __init__(self, code, detail="", codes=None):
        self.code, self.detail, self.codes = code, detail, list(codes or [code])
        super().__init__(code)


def taxonomy(code):
    return None


class ProofService:
    def __init__(self, store, conn, **kwargs):
        self.counts = {"accepted": 0, "refused": 0}

    def record_observation(self, observation, unit=None):
        return None

    def accept(self, unit, **kwargs):
        return None

    def bundle(self, unit, commit):
        return None

    def status(self):
        return dict(self.counts, proven=[], pending=[])


def resolve(store, conn, **kwargs):
    raise Refused("absent", "no proof service at 91fb549")
