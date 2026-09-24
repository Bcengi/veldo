#!/usr/bin/env python3
"""Record the second review's defect rows RED against 9421af6's production modules; verification is the full gate.

Runs this tree's suite with the four modules the fixes changed (control_alias.py,
control_document.py, control_store.py, control_readset.py) taken from commit 9421af6 (the code the
second review reproduced its defects against) and every other module from this tree, and writes
red-at-9421af6.json: every row, which rows failed, and the suite's own observations of each defect.
A row counts as recorded RED only when the suite ran to completion, so the row failed its
assertion rather than raising.

ENTRY-POINT SHIMS, and only entry points. The fixes added two call shapes 9421af6 does not have, so
the suite could not reach its rows at all against the old code. Each old module is given, appended
after its own code, exactly the entry point the suite calls and nothing that checks anything:

  control_readset.py   attach_revisions(...).accept(...) writes the accepted revision the way
                       9421af6's callers did, with the store's generic upsert_entity.
  control_document.py  Publisher(service, root, verify=..., host_identity=...) and
                       read_published(..., verify=..., host_identity=..., domain_uuid=...) accept and
                       drop the enrollment arguments, which 9421af6 had no use for.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'proof/VELDO-0037'
REVIEWED = '9421af6'
MODULES = ('control_alias.py', 'control_document.py', 'control_store.py', 'control_readset.py')
DEFECT_ROWS = ('aliases/floor-from-every-accepted-revision', 'aliases/floor-counts-every-carrier',
               'publication/bound-by-enrollment', 'aliases/owned-on-every-connection',
               'aliases/owned-whatever-registration-order')
# The refusal the old per-connection guard raised is named allocation_owned; the store's rule names
# it entity_owned, so this earlier row's expected code changed with the fix and it reds for that.
RENAMED_ROWS = ('aliases/generic-writes-refused',)

SHIMS = {
    'control_readset.py': '''

# --- red-record shim (entry point only): 9421af6 wrote accepted revisions with upsert_entity ----
class Revisions:
    def __init__(self, store, conn, domain_uuid, repositories):
        self.store, self.conn, self.domain_uuid = store, conn, domain_uuid

    def accept(self, revision_id, repository_uuid, commit, principal, documents=None, statuses=None, **signing):
        version = SN.entity(self.store, self.conn, revision_id)['version']
        command_id = 'revision.accept:%s:%d:%s' % (revision_id, version, commit)
        return self.store.execute(self.conn, {
            'command_id': command_id, 'principal': principal, 'operation': 'upsert_entity',
            'parameters': {'entity_id': revision_id, 'kind': 'accepted_revision', 'data': {
                'domain_uuid': self.domain_uuid, 'repository_uuid': repository_uuid, 'commit': commit,
                'documents': dict(documents or {}), 'statuses': dict(statuses or {})}},
            'expected_versions': {revision_id: version}, 'artifact_digests': [], 'nonce': command_id + '/nonce'}, **signing)


def attach_revisions(store, conn, domain_uuid, repositories):
    return Revisions(store, conn, domain_uuid, repositories)
''',
    'control_document.py': '''

# --- red-record shim (entry points only): 9421af6 took no enrollment arguments ----------------
_RecordedPublisher = Publisher


class Publisher(_RecordedPublisher):
    def __init__(self, service, root, verify=None, host_identity=None):
        super().__init__(service, root)


_recorded_read_published = read_published


def read_published(store, conn, repository, alias, root, verify=None, host_identity=None, domain_uuid=None):
    return _recorded_read_published(store, conn, repository, alias, root)
''',
}


def main():
    suite = ROOT / 'scripts/suites/59_veldo_0037_aliases.py'
    source = suite.read_text()
    digests = {}
    with tempfile.TemporaryDirectory(prefix='veldo-0037-red-') as directory:
        for name in MODULES:
            body = subprocess.run(['git', '-C', str(ROOT), 'show', '%s:.veldo/%s' % (REVIEWED, name)],
                                  capture_output=True, check=True).stdout
            digests[name] = hashlib.sha256(body).hexdigest()
            (Path(directory) / name).write_bytes(body + SHIMS.get(name, '').encode())
            anchor = 'ROOT / ".veldo" / "%s"' % name
            if source.count(anchor) != 1:
                raise RuntimeError('suite production-copy anchor moved: ' + anchor)
            source = source.replace(anchor, '__import__("pathlib").Path(%r)' % str(Path(directory) / name))
        rows = []
        namespace = {'ROOT': ROOT, '__file__': str(suite), 'expect': lambda name, ok: rows.append([name, bool(ok)])}
        exec(compile(source, str(suite), 'exec'), namespace)   # an exception here records nothing
    failed = [name for name, ok in rows if not ok]
    defects = namespace['_s37_observations']['defects']
    record = {'reviewed_commit': subprocess.run(['git', '-C', str(ROOT), 'rev-parse', REVIEWED], capture_output=True,
                                                text=True, check=True).stdout.strip(),
              'module_sha256': digests, 'shims': SHIMS, 'suite_sha256': hashlib.sha256(suite.read_bytes()).hexdigest(),
              'completed': True, 'rows': rows, 'failed_rows': failed,
              'defect_rows_red': {row: row in failed for row in DEFECT_ROWS},
              'renamed_rows_red': {row: row in failed for row in RENAMED_ROWS},
              'defect_observations': {key: defects.get(key) for key in (
                  'revisions', 'carriers', 'enrollment', 'connections', 'registration-order', 'generic')},
              'verification': 'Diagnostic record; only bash scripts/verify.sh verifies the change.'}
    (OUT / 'red-at-9421af6.json').write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + '\n')
    print(json.dumps({'failed_rows': failed, 'all_defect_rows_red': all(record['defect_rows_red'].values())}))
    return 0 if set(failed) == set(DEFECT_ROWS) | set(RENAMED_ROWS) else 1


if __name__ == '__main__':
    sys.exit(main())
