"""Isolated delivery cases; each worker owns its factory, faults and observations."""
import importlib.util
import http.server
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace


class ObservationServer(http.server.HTTPServer):
    """Standard loopback server with a shorter test teardown polling interval."""

    def serve_forever(self, poll_interval=0.01):
        return super().serve_forever(poll_interval=poll_interval)


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
        catalog = wire.fixture('catalog-fixture.json')
        entries = {m['slug']: m for m in json.loads(catalog.read_text())['models']}
        # The models whose bundled entry offers the experimental clock and asynchronous input, per qualified version.
        experimental = {'0.154.0': {'gpt-6-astra'},
                        '0.162.0': {'gpt-6-astra', 'gpt-6.1-sol', 'gpt-6-sol', 'gpt-6-luna'}}[wire.VERSION]
        try:
            f = factory.factory(ROOT, base, PRODUCTION, lambda _: wire.engine_source(catalog, fault))
            L, X, C = f.L, f.X, f.config_api
            # Only the server scheduling fixture changes. The production handler,
            # binary invocation, observation reader and exact comparison all run.
            # Keep this proxy local to this factory's handoff module, not global.
            L.HANDOFF.http = SimpleNamespace(server=SimpleNamespace(
                HTTPServer=ObservationServer, BaseHTTPRequestHandler=http.server.BaseHTTPRequestHandler))
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
                tier = entries[model].get('default_service_tier')
                if tier is not None:
                    # A model whose catalog picks a service tier itself (0.162.0's gpt-6-sol) stops before any run.
                    check('stop/' + model + '/service-tier', save_error is None and observed is None
                          and error == 'configuration_stop:codex_service_tier:%s:%s' % (model, tier), str(error))
                    continue
                expected = L.HANDOFF.codex_expected_tools(wanted, {}) if wanted else []
                check('delivery/' + model + '/none', error is None and observed == expected,
                      str((error, observed, expected)))
                # With no server selected, a tool beyond the expected set still refuses the launch, whatever the
                # version's reader rule (owner Telegram 32962 allows the three readers only).
                got, stop, _ = launch(baseline, 'extra') if save_error is None else (None, save_error, {})
                check('stop/' + model + '/extra-no-server', stop == 'configuration_stop:codex_unexpected_tool'
                      and got is None, str(stop))
                for tool in sorted(C.CODEX_CAPABILITIES):
                    row = 'delivery/' + model + '/' + tool
                    d = definition(model, [tool])
                    accepted, save_error = attempt(lambda: f.save(d))
                    # Independent pinned-model support expectation, never computed
                    # from the production refusal under test.
                    unsupported = ((tool in ('clock', 'request_user_input_async') and model not in experimental)
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
            # Whichever binary is selected: 0.162.0's retained catalog stops gpt-6-sol on the tier it picks itself
            # and takes gpt-6.1-sol, whose entry picks none.
            catalog_0162 = json.loads((TREE / 'proof/VELDO-0127/codex-0.162.0/catalog-fixture.json').read_text())
            bound_0162 = {'model_catalog': catalog_0162, 'model_catalog_digest': X.catalog_digest(catalog_0162)}
            for model, wanted in (('gpt-6-sol', 'configuration_stop:codex_service_tier:gpt-6-sol:priority'),
                                  ('gpt-6.1-sol', None)):
                chosen, stop = attempt(lambda: L.HANDOFF.codex_model(bound_0162, {'settings': {'model': model},
                                                                                  'native_tools': []}))
                check('catalog/service-tier', stop == wanted and (stop is not None or [
                    m['slug'] for m in chosen['models']] == [model]), str((model, stop)))
            # Whichever binary is selected: each qualified version's own record decides the readers. Independent
            # oracle: a selected server grants the three (owner Telegram 29400/29401); with none, only a Code Mode
            # model on 0.162.0 expects them (32962); 0.154.0 and models outside Code Mode expect none.
            readers = ['list_mcp_resource_templates', 'list_mcp_resources', 'read_mcp_resource']
            records = {v: json.loads((TREE / ('proof/VELDO-0061/codex-qualification-%s.json' % v)).read_text())
                       for v in ('0.154.0', '0.162.0')}
            def bound_for(version, rule=None):
                record = records[version]
                return {'version': version, 'model_tool_modes': record['model_tool_modes'],
                        'mcp_resource_rule': record['mcp_resource_rule'] if rule is None else rule}
            for version, model, servers, want in [
                    ('0.154.0', 'gpt-6-astra', [], []), ('0.154.0', 'gpt-5.6-sol', [], []), ('0.154.0', 'gpt-5.5', [], []),
                    ('0.154.0', 'gpt-6-astra', ['jira'], readers), ('0.154.0', 'gpt-5.5', ['jira'], readers),
                    ('0.162.0', 'gpt-6.1-sol', [], readers), ('0.162.0', 'gpt-6-astra', [], readers),
                    ('0.162.0', 'gpt-5.5', [], []), ('0.162.0', 'gpt-6.1-sol', ['jira'], readers),
                    ('0.162.0', 'gpt-5.5', ['jira'], readers)]:
                got, stop = attempt(lambda: L.HANDOFF.codex_resource_readers(
                    bound_for(version), {'mcp_servers': servers, 'model': model}))
                check('readers/' + version, stop is None and sorted(got or []) == want,
                      str((model, servers, stop, got)))
            # A rule that is not its version's own binds nothing, in the record and at the launch.
            for version, other in (('0.154.0', '0.162.0'), ('0.162.0', '0.154.0')):
                foreign = records[other]['mcp_resource_rule']
                _, stop = attempt(lambda: L.HANDOFF.codex_resource_readers(
                    bound_for(version, foreign), {'mcp_servers': [], 'model': 'gpt-6-astra'}))
                _, record_stop = attempt(lambda: X.qualified_baseline(None, dict(records[version], mcp_resource_rule=foreign)))
                check('readers/foreign-rule', stop == record_stop == 'missing_evidence:codex_mcp_resource_rule',
                      str((version, stop, record_stop)))
            # 0.162.0, Code Mode, no server: the readers compare equal; any other tool still refuses; a reader
            # missing is still a missing tool.
            wanted = {'tools': [], 'mcp_servers': [], 'model': 'gpt-6.1-sol'}
            wanted['resource_readers'], _ = attempt(lambda: L.HANDOFF.codex_resource_readers(bound_for('0.162.0'), wanted))
            body = {'tools': [{'type': 'function', 'name': n} for n in ['exec', 'wait'] + readers]}
            other = {'tools': body['tools'] + [{'type': 'function', 'name': 'view_image'}]}
            short = {'tools': body['tools'][:-1]}
            check('readers/other-tool', L.HANDOFF.codex_tool_difference(body, wanted) is None
                  and L.HANDOFF.codex_tool_difference(other, wanted) == 'configuration_stop:codex_unexpected_tool'
                  and L.HANDOFF.codex_tool_difference(short, wanted) == 'configuration_stop:codex_missing_tool',
                  str(wanted))
        except Exception as error:
            check('delivery/completed', False, 'raised ' + type(error).__name__ + ': ' + str(error)[:180])
        finally:
            if f:
                for connection in f.connections:
                    connection.close()
    return rows
