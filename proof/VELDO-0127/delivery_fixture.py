"""Isolated delivery cases; each worker owns its factory, faults and observations.

VELDO-0261: every row the run judges is registered before any case runs, from the qualified models, the
classified capabilities and the stop and save cases, never from what ran. Every production call of a case
runs inside that case's capture, so a refusal or an exception reds that case's rows and the next case still
runs; a row no judgment reached is red as "not reached" with the step and exception that stopped it. Every
capture keeps the exception whole (Failure) and the row's detail carries it.
"""
import ast
import importlib.util
import http.server
import json
from pathlib import Path
import tempfile
import time
import traceback
from types import SimpleNamespace

STOPS = (('missing', 'codex_missing_tool'), ('extra', 'codex_unexpected_tool'), ('mcp', 'codex_missing_tool'))


class ObservationServer(http.server.HTTPServer):
    """Standard loopback server with a shorter test teardown polling interval."""

    def serve_forever(self, poll_interval=0.01):
        return super().serve_forever(poll_interval=poll_interval)


class Failure(str):
    """A caught exception as a case compares it (its refusal code, else its type name), kept whole: its repr,
    and so every row detail that shows it, carries the fixture step it was raised in, its type, its code when
    it has one, its full message and its formatted traceback (one line, its lines joined by ' | ')."""

    def __new__(cls, error, step):
        code = getattr(error, 'code', None)
        self = super().__new__(cls, code if isinstance(code, str) and code else type(error).__name__)
        trace = ''.join(traceback.format_exception(error))
        self.whole = ('step ' + step + ': ' + type(error).__name__
                      + (' code ' + str(code) if code is not None else '') + ' message ' + repr(str(error))
                      + ' traceback ' + ' | '.join(line.rstrip() for line in trace.splitlines() if line.strip()))
        return self

    def __repr__(self):
        return self.whole


def codex_capabilities(path):
    """The classified Codex capabilities, read from the production module's own literal without running it."""
    for node in ast.parse(Path(path).read_text()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'CODEX_CAPABILITIES' for t in node.targets):
            return set(ast.literal_eval(node.value))
    raise LookupError('CODEX_CAPABILITIES is not a literal in ' + str(path))


def plan(models, capabilities):
    """[(case, rows)] in the order the run judges them: the rows this run registers before any case runs."""
    cases = []
    for model in models:
        cases.append((model + '/none', ['delivery/' + model + '/none']))
        cases += [(model + '/' + tool, ['delivery/' + model + '/' + tool]) for tool in sorted(capabilities)]
        cases.append((model + '/jira', ['delivery/' + model + '/jira']))
        cases += [(model + '/stop-' + defect, ['stop/' + model + '/' + defect]) for defect, _ in STOPS]
        cases.append((model + '/search-mcp', ['save/' + model + '/search-mcp']))
    return cases


def run(ROOT, TREE, PRODUCTION, models):
    """{'rows': {row: [(passed, detail)]}, 'registered': [row], 'slowest': {case: (step, seconds)}}."""
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    rows, slowest = {}, {}
    where = ['registration', None]  # the fixture step running now, and the case it belongs to
    begun = [time.monotonic()]

    def at(step):
        """Enter a fixture step; the step it ends is timed against its case's slowest."""
        now = time.monotonic()
        if where[1] is not None and (where[1] not in slowest or now - begun[0] > slowest[where[1]][1]):
            slowest[where[1]] = (where[0], round(now - begun[0], 3))
        where[0], begun[0] = step, now

    def attempt(fn, step):
        at(step)
        try:
            return fn(), None
        except Exception as error:
            return None, Failure(error, step)

    def check(row, condition, detail=''):
        rows.setdefault(row, []).append((bool(condition), '' if condition else detail))
        if not condition:
            print('  VELDO-0127 ' + row + ' detail: ' + detail)
    capabilities = codex_capabilities(PRODUCTION['control_agent_config.py'])
    cases = plan(models, capabilities)
    registered = [row for _, names in cases for row in names]
    stopped = [None]  # the setup failure that stopped every case, when one did

    def case(name, body):
        """Run one case inside its own capture: an exception reds its rows with the whole failure."""
        names = dict(cases)[name]
        at('case')
        where[1] = name
        try:
            body()
        except Exception as error:
            failure = Failure(error, where[0])
            for row in names:
                check(row, False, 'not reached: case ' + name + ' stopped at ' + repr(failure))
        finally:
            at('case end')
            where[1] = None
    f = None
    with tempfile.TemporaryDirectory(prefix='v127-delivery-') as temp:
        base = Path(temp)
        fault = base / 'fault'
        try:
            at('fixture modules')
            wire = load('v127_wire', TREE / 'proof/VELDO-0127/wire_fixture.py')
            factory = load('v127_delivery_factory', TREE / 'proof/VELDO-0127/factory.py')
            at('catalog fixture')
            catalog = TREE / 'proof/VELDO-0127/catalog-fixture.json'
            supported = {m['slug']: set(m.get('experimental_supported_tools') or ())
                         for m in json.loads(catalog.read_text())['models']}
            experimental = {'clock': 'clock', 'request_user_input_async': 'send_user_message_async'}
            at('factory')
            f = factory.factory(ROOT, base, PRODUCTION, lambda _: wire.engine_source(catalog, fault))
            L, X, C = f.L, f.X, f.config_api
            at('capabilities')
            if set(C.CODEX_CAPABILITIES) != capabilities:
                raise LookupError('registered capabilities %s differ from the loaded %s'
                                  % (sorted(capabilities), sorted(C.CODEX_CAPABILITIES)))
            # Only the server scheduling fixture changes. The production handler,
            # binary invocation, observation reader and exact comparison all run.
            # Keep this proxy local to this factory's handoff module, not global.
            at('handoff proxy')
            L.HANDOFF.http = SimpleNamespace(server=SimpleNamespace(
                HTTPServer=ObservationServer, BaseHTTPRequestHandler=http.server.BaseHTTPRequestHandler))
            at('engine bind')
            bound = X.bind({'executable': str(f.vendored), 'qualification': str(f.codex_qualification)})
        except Exception as error:
            stopped[0] = Failure(error, where[0])
            check('delivery/setup', False, repr(stopped[0]))
        else:
            check('delivery/setup', True)
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
                at('configuration bind')
                configuration = C.bind(f.writer, f.DOMAIN, f.REPOSITORY, {'role': d['role']})
                revision = configuration['role_revision']
                capability, refusal = attempt(lambda: L.HANDOFF.materialize(
                    f.writer, f.DOMAIN, f.REPOSITORY, revision, {'project': f.src, 'factory': base}), 'materialize')
                if refusal:
                    return None, refusal, {}
                receiver = object.__new__(L.Receiver)
                receiver.config = {'runs': str(base / 'runs')}
                receiver.binding = dict(bound, revision=revision, capability=capability,
                                        configured_environment={}, environment={})
                receiver.login = {'engine': X, 'record': f.accounts.get('acct-x1')}
                receiver.host, receiver.token, receiver.metering = f.HOST, None, None
                at('credential resolve')
                receiver.credentials = L.DL.resolve(f.writer, f.DOMAIN, configuration, keystore=f.keystore)
                events = []
                receiver.emit = events.append
                serial[0] += 1
                _, error = attempt(lambda: receiver._baseline('wire-run-' + str(serial[0]),
                                   [str(f.vendored)] + list(X.FLAGS), dict(f.inherited), False), 'receiver baseline')
                observed = next((e['tools'] for e in events if e.get('event') == 'capability_tools'), None)
                return observed, error, receiver.binding.get('expected')

            def expected_tools(wanted):
                at('expected tools')
                return L.HANDOFF.codex_expected_tools(wanted, {}) if wanted else []

            # Universe from the shipped qualification; names from the accepted writer.
            # Every observation is emitted by Receiver._baseline after the pinned
            # binary sends its real definitions to the production loopback endpoint.
            for model in models:
                empty = {'observed': None}

                def none_case(model=model):
                    baseline = definition(model, [])
                    _, save_error = attempt(lambda: f.save(baseline), 'save')
                    observed, error, wanted = launch(baseline) if save_error is None else (None, save_error, {})
                    empty['observed'] = observed
                    expected = expected_tools(wanted)
                    check('delivery/' + model + '/none', error is None and observed == expected,
                          repr((error, observed, expected)))
                case(model + '/none', none_case)
                for tool in sorted(capabilities):
                    def tool_case(model=model, tool=tool):
                        row = 'delivery/' + model + '/' + tool
                        d = definition(model, [tool])
                        accepted, save_error = attempt(lambda: f.save(d), 'save')
                        # Independent pinned-model support expectation, never computed
                        # from the production refusal under test.
                        # VELDO-0230: a model's support is the qualified catalog's own experimental list.
                        unsupported = ((tool in experimental and experimental[tool] not in supported.get(model, ()))
                                       or tool == 'tool_search')
                        if unsupported:
                            check(row, accepted is None and save_error ==
                                  'unsupported_configuration:codex_tool:' + model + ':' + tool, repr(save_error))
                        else:
                            got, stop, wanted = launch(d) if accepted else (None, save_error, {})
                            expected = expected_tools(wanted)
                            check(row, stop is None and got == expected, repr((stop, got, expected)))
                        at('ungranted names')
                        mapped = {L.HANDOFF.codex_name(n) for n in X.NATIVE_TOOL_MAPPING.get(tool, [tool])}
                        observed = empty['observed']
                        check(row, observed is not None and not mapped.intersection(observed),
                              'ungranted tool must be absent from the observed empty role')
                    case(model + '/' + tool, tool_case)

                jira = {'accepted': None, 'save_error': 'not saved', 'd': None}

                def jira_case(model=model):
                    d = jira['d'] = definition(model, ['update_plan'], True)
                    jira['accepted'], jira['save_error'] = attempt(lambda: f.save(d), 'save')
                    got, stop, wanted = launch(d) if jira['accepted'] else (None, jira['save_error'], {})
                    expected = expected_tools(wanted)
                    check('delivery/' + model + '/jira', stop is None and got == expected
                          and 'mcp__jira__jira_search' in (got or []), repr((stop, got)))
                case(model + '/jira', jira_case)
                for defect, reason in STOPS:
                    def stop_case(model=model, defect=defect, reason=reason):
                        got, stop, _ = (launch(jira['d'], defect) if jira['accepted']
                                        else (None, jira['save_error'], {}))
                        check('stop/' + model + '/' + defect, stop == 'configuration_stop:' + reason
                              and got is None, repr(stop))
                    case(model + '/stop-' + defect, stop_case)

                def search_case(model=model):
                    d = definition(model, ['tool_search'], True)
                    _, stop = attempt(lambda: f.save(d), 'save')
                    check('save/' + model + '/search-mcp', stop ==
                          'unsupported_configuration:codex_tool:' + model + ':tool_search', repr(stop))
                case(model + '/search-mcp', search_case)
        finally:
            if f:
                for connection in f.connections:
                    connection.close()
        for row in registered:
            if row not in rows:
                check(row, False, 'not reached: ' + (repr(stopped[0]) if stopped[0] is not None
                                                     else 'the run ended before its case'))
    return {'rows': rows, 'registered': registered, 'slowest': slowest}
