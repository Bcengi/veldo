"""Offline catalog and resource-reader probes on the loopback stand-in only."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(binary):
    H = load('probe_handoff', ROOT / '.veldo/control_agent_config_handoff.py')
    LB = load('probe_loopback', HERE / 'loopback.py')
    E = load('probe_evidence', HERE / 'evidence.py')
    qualified = H.X.load_qualification()
    assert H.X._file_digest(binary) == qualified['sha256']
    resources = ['list_mcp_resource_templates', 'list_mcp_resources', 'read_mcp_resource']
    reports = []
    with tempfile.TemporaryDirectory(prefix='v127-catalog-probe-') as temp:
        for model in ('gpt-6-astra', 'gpt-5.5'):
            revision = {'native_tools':['shell', 'update_plan'], 'settings':{'model':model}}
            capability = {'revision':revision, 'instructions':'Reply ready.', 'skills':[]}
            inventory = {'jira':{'tools':['jira_search']}}
            catalog = H.codex_model(qualified, revision)
            cfg = H.X.generated()
            cfg['mcp_servers'] = {'jira':{'enabled_tools':['jira_search']}}
            H.codex(cfg, capability, inventory, Path(temp), catalog=catalog)
            wanted = H.expected(capability, inventory)
            cases = [('catalog', copy.deepcopy(cfg))]
            if model == 'gpt-6-astra':
                disabled = copy.deepcopy(cfg)
                disabled['mcp_servers']['jira']['disabled_tools'] = resources
                cases.append(('server-disabled-tools', disabled))
                flags = copy.deepcopy(cfg)
                for name in resources:
                    flags['tools.' + name] = {'enabled':False}
                cases.append(('resource-tool-config', flags))
                excluded = copy.deepcopy(cfg)
                excluded['features.code_mode'] = {'excluded_tool_namespaces':resources}
                cases.append(('excluded-resource-names', excluded))
                omit = copy.deepcopy(cfg)
                omit['mcp_servers']['jira']['omit_tools_from'] = resources
                cases.append(('server-omit-names', omit))
                omit_modes = copy.deepcopy(cfg)
                omit_modes['mcp_servers']['jira']['omit_tools_from'] = ['code_mode', 'deferred', 'direct']
                cases.append(('server-omit-modes', omit_modes))
            for label, configuration in cases:
                result = LB.capture(binary, configuration, catalog=catalog)
                observations = [E.wire_observation(r['body'], wanted, H) for r in result['requests']]
                reports.append({'model':model, 'case':label, 'returncode':result['returncode'],
                    'observations':observations, 'stderr_tail':result.get('stderr','')[-1500:],
                    'request_digests':[hashlib.sha256(json.dumps(r['body'],sort_keys=True).encode()).hexdigest()
                                       for r in result['requests']]})
                if label == 'catalog':
                    result.update(expected=wanted, observations=observations, model_catalog=catalog)
                    (HERE / ('catalog-loopback-' + model + '.json')).write_text(json.dumps(result,indent=1)+'\n')
                    if result['requests']:
                        (HERE / ('request-' + ('code' if model == 'gpt-6-astra' else 'direct') + '.json')).write_text(
                            json.dumps(result['requests'][0]['body'],indent=1)+'\n')
                print(model, label, result['returncode'], [o['unexpected'] for o in observations], flush=True)
    data = Path(binary).read_bytes()
    terms = ['add_mcp_resource_tools', 'RawMcpServerConfig', 'omit_tools_from', 'disabled_tools',
             'excluded_tool_namespaces', 'resources_enabled', 'disable_resources', 'mcp_resource_tools']
    strings = {t:{'count':len(list(re.finditer(re.escape(t.encode()),data)))} for t in terms}
    record = {'binary_sha256':qualified['sha256'], 'model_catalog_digest':qualified['model_catalog_digest'],
              'network':'loopback stand-in only; empty temporary HOME and CODEX_HOME; Landlock TCP restriction',
              'string_search':strings, 'probes':reports,
              'remaining_case_c':resources,
              'scope':'Resource readers can access only resources of the role configured MCP servers. No suppression established.'}
    (HERE / 'resource-investigation.json').write_text(json.dumps(record,indent=1)+'\n')


if __name__ == '__main__':
    main(sys.argv[1])
