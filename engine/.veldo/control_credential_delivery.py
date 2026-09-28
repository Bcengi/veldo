"""The credentials of one Linux run, resolved from the keystore just before its spawn (VELDO-0158).

A dispatch configuration names the MCP servers it uses as catalog revisions (`mcp`: a list of
{server, revision}, VELDO-0144 AC1; VELDO-0127 later fills it from the role's accepted revision).
`resolve` reads each listed revision's `mcp_server` record from the store and resolves exactly the
credential references in its environment and headers, each a secretref `keychain:<name>` naming a
`credential` record, through secretref's keychain scheme (the Secret Service adapter of
control_credential_keystore). A literal is passed as it is and resolves nothing; a server not listed
contributes nothing, so no run receives another server's credential.

What it returns holds every value in a secretref handle, which prints its reference only; the engine
module reveals each one where it delivers it (THE ENGINE PROTOCOL's baseline): Claude Code's generated
MCP configuration in the run's private directory, or the Codex engine environment. A credential that
does not resolve is `Undeliverable` by name (`credential_unavailable:<id>`), with the reason the error
taxonomy distinguishes, so the launch is refused and the run never starts without its server.
"""
import importlib.util
import json
from pathlib import Path


def organ(name):
    spec = importlib.util.spec_from_file_location('delivery_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MC = organ('control_mcp_catalog')
KS = organ('control_credential_keystore')
SR = organ('secretref')
# The dispatch configuration's field naming its MCP selections, and the kind its values carry in the
# run's set of resolved values (VELDO-0141), which names them in the execution record's markers.
SELECTIONS = 'mcp'
KIND = 'mcp_credential'
ROUTES = ('private_file', 'engine_environment')
REASONS = ('keystore_locked', 'keystore_unreachable', 'reference_not_found', 'delivery_failed')


class Undeliverable(Exception):
    """A launch refused by name before its spawn; `credential` and `reason` are for the report, never a value."""

    def __init__(self, code, credential=None, reason=None):
        self.code, self.credential, self.reason = code, credential, reason
        super().__init__(code)


def selections(configuration):
    """[(server, revision)] the dispatch configuration selects, in order; [] when it names none."""
    chosen = (configuration or {}).get(SELECTIONS) if isinstance(configuration, dict) else None
    if chosen is None:
        return []
    if not isinstance(chosen, list):
        raise Undeliverable('invalid_input:mcp_selection')
    out = []
    for item in chosen:
        if (not isinstance(item, dict) or set(item) != {'server', 'revision'} or not MC.identifier(item['server'])
                or type(item['revision']) is not int or item['revision'] < 1
                or item['server'] in [server for server, _ in out]):
            raise Undeliverable('invalid_input:mcp_selection')
        out.append((item['server'], item['revision']))
    return out


def _credential(conn, reference):
    """The live `credential` record a reference names, or None (absent, another reference, or deleted)."""
    name = reference.split(':', 1)[1]
    if not name.startswith('veldo/'):
        return None
    row = MC.entity(conn, 'credential:' + name[len('veldo/'):])
    data = row['data'] if row and row['kind'] == 'credential' else {}
    return data if data.get('reference') == reference and not data.get('deleted') else None


def _reason(error):
    code = getattr(error, 'code', '') or ''
    return code.split(':', 1)[1] if code in ('unavailable_service:keystore_locked',
                                              'unavailable_service:keystore_unreachable') else 'reference_not_found'


def resolve(conn, domain, configuration, keystore=None):
    """The selected servers with their credentials resolved, in selection order:
    [{id, revision, transport, command, arguments, url, environment, headers}], where each environment or
    header item is {'literal': text} or {'credential': id, 'handle': SecretHandle}. Undeliverable by name
    when a selection is malformed, a revision is not recorded or a credential does not resolve."""
    keystore = keystore or KS.SecretService()
    resolved, servers = {}, []
    for server, revision in selections(configuration):
        row = MC.entity(conn, MC.revision_id(domain, server, revision))
        if row is None or row['kind'] != MC.KIND or row['data'].get('id') != server:
            raise Undeliverable('missing_evidence:mcp_server:%s:%d' % (server, revision))
        d = row['data']
        if d['transport'] == 'http' and d['environment']:
            # An http server is reached by its url and headers; an environment it names reaches nothing.
            raise Undeliverable('invalid_input:mcp_delivery:%s' % server)
        out = dict({k: d[k] for k in ('transport', 'command', 'arguments', 'url')}, id=server, revision=revision,
                   environment={}, headers={})
        for field in ('environment', 'headers'):
            for name, item in sorted(d[field].items()):
                if 'literal' in item:
                    out[field][name] = {'literal': item['literal']}
                    continue
                reference = item['reference']
                record = _credential(conn, reference)
                identity = record['id'] if record else reference.split(':', 1)[1]
                if record is None:
                    raise Undeliverable('credential_unavailable:' + identity, identity, 'reference_not_found')
                if reference not in resolved:
                    try:
                        resolved[reference] = SR.resolve_for_runtime(reference, keystore)
                    except (KS.Refused, SR.SecretError) as error:
                        raise Undeliverable('credential_unavailable:' + identity, identity, _reason(error)) from None
                out[field][name] = {'credential': identity, 'handle': resolved[reference]}
        servers.append(out)
    return servers


def values(servers):
    """Every resolved value of a run's servers, as the engine receives it, for the run's set (VELDO-0141)."""
    out = []
    for server in servers or ():
        for field in ('environment', 'headers'):
            for item in server[field].values():
                if 'handle' in item:
                    out.append(item['handle'].reveal())
    return out


def report(dispatch_id, servers, routes=None, refusal=None):
    """What the receiver reports of a launch's credentials: the catalog revisions and credential ids it
    resolved, the route each took, or its named refusal; never a value."""
    credentials = sorted({item['credential'] for s in servers or () for f in ('environment', 'headers')
                          for item in s[f].values() if 'credential' in item})
    event = {'dispatch_id': dispatch_id, 'servers': [{'id': s['id'], 'revision': s['revision']} for s in servers or ()],
             'credentials': credentials, 'routes': list(routes or [])}
    if refusal is not None:
        event.update(refusal=refusal.code, credential=refusal.credential, reason=refusal.reason)
    event['metrics'] = {'launch_with_credentials': int(bool(credentials) and refusal is None),
                        'credentials_resolved': len(credentials) if refusal is None else 0,
                        'credential_unavailable': ({refusal.credential: 1}
                                                   if refusal is not None and refusal.credential else {})}
    return json.loads(json.dumps(event))
