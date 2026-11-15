"""VELDO-0333: timing retention follows checkout existence, never a file's age.

Only shared ROOT and expect are consumed. Both production copies run against temporary
stores and fixture checkout directories. No gate stage or host store is used. The clock is
fixed for resource reads; the pruning row refuses clock and directory-entry time reads.
The old files contain markers checked byte for byte after both recording entry points.
"""


def _v333_suite():
    import ast
    import contextlib
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import tempfile
    import types
    from unittest import mock

    sources = {
        'canon': ROOT / "engine/scripts" / "gate_legs.py",
        'copy': ROOT / "scripts" / "gate_legs.py",
    }
    now, day = 2000000000, 86400
    rows = {}

    def check(row, detail, condition):
        rows.setdefault(row, []).append((detail, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def planted(store, name, content, age=31):
        path = store / name
        raw = json.dumps(content).encode()
        path.write_bytes(raw)
        os.utime(path, (now - age * day, now - age * day))
        return path, raw

    def unchanged(pair):
        path, raw = pair
        return path.is_file() and path.read_bytes() == raw

    def forbidden(*args, **kwargs):
        raise AssertionError('prune read a clock or a timing file time')

    with tempfile.TemporaryDirectory(prefix='veldo-0333-') as directory:
        top = Path(directory)
        checkout = top / 'authority'
        checkout.mkdir()
        missing = top / 'missing-checkout'
        for label, source in sources.items():
            gl = load('v333_' + label, source)
            gl.HERE = checkout / 'scripts'
            for writer in ('time', 'resources'):
                store = top / (label + '-' + writer)
                store.mkdir()
                old = planted(store, '1' * 32 + '.json',
                              {'authority': str(checkout), 'marker': 'old measurement stays'})
                gone = planted(store, '2' * 32 + '.json', {'authority': str(missing)}, age=0)
                pending = planted(store, '.pending-abandoned',
                                  {'authority': str(missing), 'marker': 'unfinished write stays'})
                bad = planted(store, '3' * 32 + '.json', ['unreadable authority'])
                foreign = planted(store, 'notes.txt', {'marker': 'not a timing file'})
                link = store / ('4' * 32 + '.json')
                link.symlink_to(foreign[0])
                with mock.patch.object(gl.time, 'time', return_value=now), \
                        contextlib.redirect_stdout(io.StringIO()) as said:
                    if writer == 'time':
                        ok = gl.record_time(store, 'digest', 'confined', 12.3, 'run')
                        target = gl._times_file(store, 'digest')
                        check('ac2/write-completes', label + ' timing write succeeds', ok is True)
                    else:
                        gl.record_resources(store, 'digest', 'unit.confined', 2,
                                            {'metrics_source': 'cgroup-v2-anon-sampled-50ms',
                                             'cpu_seconds': 3, 'peak_anon_bytes': 4096})
                        target = gl._resources_file(store, 'digest', 'unit.confined')
                check('ac1/old-live-file-stays', label + '/' + writer + ' old bytes retained', unchanged(old))
                check('ac2/missing-checkout-removed', label + '/' + writer + ' missing checkout cleaned',
                      not gone[0].exists())
                check('ac2/write-completes', label + '/' + writer + ' just-written file retained',
                      target.is_file() and json.loads(target.read_text())['authority'] == str(checkout))
                check('ac3/pending-untouched', label + '/' + writer + ' pending bytes retained', unchanged(pending))
                check('ac3/unreadable-and-foreign-stay', label + '/' + writer + ' unrelated files retained',
                      unchanged(bad) and unchanged(foreign) and link.is_symlink())
                check('ac3/missing-checkout-only-message', label + '/' + writer + ' cleanup reason',
                      said.getvalue().strip() == 'unit: removed 1 leg-time file from %s (authority checkout gone)' % store)

            store = top / (label + '-direct')
            store.mkdir()
            kept = planted(store, '5' * 32 + '.json', {'authority': str(missing)})
            gone = planted(store, '6' * 32 + '.json', {'authority': str(missing)})
            with contextlib.redirect_stdout(io.StringIO()):
                removed = gl.prune_times(store, keep=kept[0])
            check('ac2/keep-always-spared', label + ' explicit keep with missing checkout retained',
                  unchanged(kept) and removed == [gone[0].name] and not gone[0].exists())

            live = planted(store, '7' * 32 + '.json', {'authority': str(checkout)})
            gone = planted(store, '8' * 32 + '.json', {'authority': str(missing)})
            entries = list(os.scandir(store))
            entries = [types.SimpleNamespace(name=e.name, path=e.path, is_file=e.is_file, stat=forbidden)
                       for e in entries]
            with mock.patch.object(gl, 'time', types.SimpleNamespace(time=forbidden, monotonic=forbidden)), \
                    mock.patch.object(gl.os, 'scandir', return_value=entries), \
                    contextlib.redirect_stdout(io.StringIO()):
                try:
                    removed = gl.prune_times(store, keep=kept[0])
                    no_reads = removed == [gone[0].name] and unchanged(live) and unchanged(kept)
                except AssertionError:
                    no_reads = False
            check('ac3/no-clock-or-file-time', label + ' pruning succeeds with time readers refused', no_reads)

            unread = planted(store, '9' * 32 + '.json', {'authority': str(checkout)})
            real_stat = Path.stat

            def cannot_read(path, *args, **kwargs):
                if path == checkout:
                    raise PermissionError('fixture checkout probe refused')
                return real_stat(path, *args, **kwargs)

            with mock.patch.object(Path, 'stat', cannot_read), contextlib.redirect_stdout(io.StringIO()):
                gl.prune_times(store, keep=kept[0])
            check('ac3/unreadable-and-foreign-stay', label + ' unreadable checkout is not absence',
                  unchanged(unread) and unchanged(live))

            module = ast.parse(source.read_text())
            prune = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'prune_times')
            descriptions = ((ast.get_docstring(module) or '') + '\n' + (ast.get_docstring(prune) or '')).lower()
            check('ac3/descriptions', label + ' describes checkout absence only',
                  'authority checkout' in descriptions and 'older than' not in descriptions
                  and 'store_max_age_days' not in descriptions and 'untouched for' not in descriptions)
            check('ac3/no-clock-or-file-time', label + ' no time attributes in pruning source',
                  not any(isinstance(n, ast.Attribute) and
                          (n.attr.startswith(('st_mtime', 'st_atime', 'st_ctime', 'st_birthtime'))
                           or (isinstance(n.value, ast.Name) and n.value.id == 'time'))
                          for n in ast.walk(prune)))

            store = top / (label + '-read')
            store.mkdir()
            path = gl._resources_file(store, 'digest', 'unit.confined')
            item = {'authority': str(checkout), 'digest': 'digest', 'node': 'unit.confined',
                    'cpu_rate': 1.5, 'peak_anon_bytes': 4096}
            for age in (29, 30, 31):
                pair = planted(store, path.name, item, age=age)
                with mock.patch.object(gl.time, 'time', return_value=now):
                    found = gl.read_resources(store, 'digest', 'unit.confined')
                check('ac4/read-age-bound', label + ' measurement at %d days' % age,
                      found == (None if age > 30 else item))
                check('ac4/read-keeps-file', label + ' read retains %d-day bytes' % age, unchanged(pair))
            reader = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'read_resources')
            constants = [n.id for n in ast.walk(reader) if isinstance(n, ast.Name) and 'AGE_DAYS' in n.id]
            check('ac4/read-named-bound', label + ' bound says read and remains 30 days',
                  constants == ['RESOURCE_READ_MAX_AGE_DAYS'] and getattr(gl, 'RESOURCE_READ_MAX_AGE_DAYS', None) == 30)

        check('ac3/canon', 'canon and synced copy agree',
              sources['canon'].read_bytes() == sources['copy'].read_bytes())

    for row, observations in rows.items():
        failures = [detail for detail, ok in observations if not ok]
        expect('VELDO-0333 ' + row + (': ' + '; '.join(failures) if failures else ''), not failures)


_v333_suite()
