"""Isolated delivery cases; each worker owns its factory, faults and observations."""
import importlib.util
import json
from pathlib import Path
import tempfile


def run(ROOT, TREE, PRODUCTION, models):
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    def attempt(fn):
        try:
            return fn(), None
        except Exception as error:
            return None, getattr(error, 'code', type(error).__name__)
    rows = {}
    def check(row, condition, detail=''):
        rows.setdefault(row, []).append(bool(condition))
        if not condition:
            print('  VELDO-0127 ' + row + ' detail: ' + detail)
    wire = load('v127_wire', TREE / 'proof/VELDO-0127/wire_fixture.py')
    factory = load('v127_delivery_factory', TREE / 'proof/VELDO-0127/factory.py')
    f = None
    with tempfile.TemporaryDirectory(prefix='v127-delivery-') as temp:
        base = Path(temp)
        fault = base / 'fault'
        catalog = TREE / 'proof/VELDO-0127/catalog-fixture.json'
        try:
            f = factory.factory(ROOT, base, PRODUCTION, lambda _: wire.engine_source(catalog, fault))
            L, X, C = f.L, f.X, f.config_api
            bound = X.bind({'executable': str(f.vendored), 'qualification': str(f.codex_qualification)})
            serial = [0]
            def definition(model, grants, mcp=False):
                serial[0] += 1
                d = f.role('codex', 'wire-role-' + str(serial[0]))
                d.update(skills=[], instructions=[])
                d['settings']['model'] = model
                d['native_tools'] = [{'name': n, 'load': 'always'} for n in grants]
                if not mcp:
                    d['mcp'] = []
                return d
            def launch(d, defect=''):
                fault.write_text(defect)
                configuration = C.bind(f.writer, f.DOMAIN, f.REPOSITORY, {'role': d['role']})
                revision = configuration['role_revision']
                capability, refusal = attempt(lambda: L.HANDOFF.materialize(
                    f.writer, f.DOMAIN, f.REPOSITORY, revision, {'project': f.src, 'factory': base}))
                if refusal:
                    return None, refusal, {}
                receiver = object.__new__(L.Receiver)
                receiver.config = {'runs': str(base / 'runs')}
                receiver.binding = dict(bound, revision=revision, capability=capability,
                                        configured_environment={}, environment={})
                receiver.login = {'engine': X, 'record': f.accounts.get('acct-x1')}
                receiver.host, receiver.token, receiver.metering = f.HOST, None, None
                receiver.credentials = L.DL.resolve(f.writer, f.DOMAIN, configuration, keystore=f.keystore)
                events = []
                receiver.emit = events.append
                serial[0] += 1
                _, error = attempt(lambda: receiver._baseline('wire-run-' + str(serial[0]),
                                   [str(f.vendored)] + list(X.FLAGS), dict(f.inherited), False))
                observed = next((e['tools'] for e in events if e.get('event') == 'capability_tools'), None)
                return observed, error, receiver.binding.get('expected')

            # Universe from the shipped qualification; names from the accepted writer.
            # Every observation is emitted by Receiver._baseline after the pinned
            # binary sends its real definitions to the production loopback endpoint.
            for model in models:
                baseline = definition(model, [])
                _, save_error = attempt(lambda: f.save(baseline))
                observed, error, wanted = launch(baseline) if save_error is None else (None, save_error, {})
                expected = L.HANDOFF.codex_expected_tools(wanted, {}) if wanted else []
                check('delivery/' + model + '/none', error is None and observed == expected,
                      str((error, observed, expected)))
                for tool in sorted(C.CODEX_CAPABILITIES):
                    row = 'delivery/' + model + '/' + tool
                    d = definition(model, [tool])
                    accepted, save_error = attempt(lambda: f.save(d))
                    # Independent pinned-model support expectation, never computed
                    # from the production refusal under test.
                    unsupported = ((tool in ('clock', 'request_user_input_async') and model != 'gpt-6-astra')
                                   or tool == 'tool_search')
                    if unsupported:
                        check(row, accepted is None and save_error ==
                              'unsupported_configuration:codex_tool:' + model + ':' + tool, str(save_error))
                    else:
                        got, stop, wanted = launch(d) if accepted else (None, save_error, {})
                        expected = L.HANDOFF.codex_expected_tools(wanted, {}) if wanted else []
                        check(row, stop is None and got == expected, str((stop, got, expected)))
                    mapped = {L.HANDOFF.codex_name(n) for n in X.NATIVE_TOOL_MAPPING.get(tool, [tool])}
                    check(row, observed is not None and not mapped.intersection(observed),
                          'ungranted tool must be absent from the observed empty role')

                d = definition(model, ['update_plan'], True)
                accepted, save_error = attempt(lambda: f.save(d))
                got, stop, wanted = launch(d) if accepted else (None, save_error, {})
                check('delivery/' + model + '/jira', stop is None and got == L.HANDOFF.codex_expected_tools(wanted, {})
                      and 'mcp__jira__jira_search' in (got or []), str((stop, got)))
                for defect, reason in [('missing', 'codex_missing_tool'), ('extra', 'codex_unexpected_tool'),
                                       ('mcp', 'codex_missing_tool')]:
                    got, stop, _ = launch(d, defect) if accepted else (None, save_error, {})
                    check('stop/' + model + '/' + defect, stop == 'configuration_stop:' + reason
                          and got is None, str(stop))
                d = definition(model, ['tool_search'], True)
                _, stop = attempt(lambda: f.save(d))
                check('save/' + model + '/search-mcp', stop ==
                      'unsupported_configuration:codex_tool:' + model + ':tool_search', str(stop))
        except Exception as error:
            check('delivery/completed', False, 'raised ' + type(error).__name__ + ': ' + str(error)[:180])
        finally:
            if f:
                for connection in f.connections:
                    connection.close()
    return rows
