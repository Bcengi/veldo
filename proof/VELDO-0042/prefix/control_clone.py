"""Stand-in for `.veldo/control_clone.py` as it did not exist at 18ecd6f.

At the pre-change commit there was no isolated-worker-clone provisioner: no clone at an accepted
commit, no per-repository pinned object cache, no worker write confinement. This stand-in supplies
only the two names the current suite touches during setup, `Clones` and `Refused`, and refuses every
provision, so the suite runs to its end and each row reds by its own assertion (the capability is
absent), never by a raise. It contains nothing else: it is the VELDO-0040 `prefix/` precedent for a
module that does not exist at the commit under test.
"""


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__(code + (': ' + detail if detail else ''))
        self.code, self.detail = code, detail


class Clones:
    def __init__(self, dispatches, *, clones, caches, protected=(), writable=(), clock=None):
        self.dispatches = dispatches

    def create(self, contract):
        raise Refused('capability_absent', 'no isolated worker clones at 18ecd6f')
