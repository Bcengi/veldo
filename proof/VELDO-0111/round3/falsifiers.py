"""Mutate scratch sources only; each completed targeted row must become false."""
import difflib
from pathlib import Path
import tempfile
from drive import HERE, SOURCE, run

source = SOURCE.read_text()
cases = {
    'phantom-unix': (
        "        if len(fields) == 7:\n            return None",
        "        if len(fields) == 7:\n            return dict(unix_name_hex='00', sockaddr_hex='010000')",
        ('unix',), 'census/unix-binding-is-real'),
    'drop-autobind': (
        "            return dict(unix_name_hex=(b'\\0' + name[1:]).hex(),",
        "            return None\n            return dict(unix_name_hex=(b'\\0' + name[1:]).hex(),",
        ('unix',), 'census/unix-binding-is-real'),
    'other-family-service': (
        '                    if not bound:\n                        failure(self.r, "implicit_address",',
        '                    if not bound:\n                        self.expose(pid, obj, "implicit_receive_binding", address)\n                        failure(self.r, "implicit_address",',
        ('unix',), 'census/unix-binding-is-real'),
    'silence-family': (
        "            failure(self.r, 'family_not_qualified', obj['not_qualified']['reason'])",
        "            pass  # swallowed family boundary",
        ('families',), 'census/family-qualification-boundary'),
    'uncovered-state': (
        '            r["state"] = "drained"',
        '            r["state"] = "sealing"\n            r["state"] = "drained"',
        ('states',), 'census/fault-state-coverage'),
}
for label, (old, new, groups, target) in cases.items():
    assert source.count(old) == 1, label
    mutant = source.replace(old, new)
    (HERE / (label + '.diff')).write_text(''.join(difflib.unified_diff(
        source.splitlines(True), mutant.splitlines(True), fromfile='lifecycle_census.py', tofile='mutant.py')))
    with tempfile.TemporaryDirectory(prefix='v111-round3-') as scratch:
        path = Path(scratch) / 'lifecycle_census.py'
        path.write_text(mutant)
        rows = run(label + '-red', path, groups)
    assert rows[target] is False, (label, rows)
    rows = run(label + '-green', groups=groups)
    assert all(rows.values()), (label, rows)
