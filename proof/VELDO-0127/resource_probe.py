"""Qualify the owner-approved MCP resource rule on loopback with empty profiles."""
import copy
import importlib.util
import json
from pathlib import Path
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
    H = load('resource_handoff', ROOT / '.veldo/control_agent_config_handoff.py')
    LB = load('resource_loopback', HERE / 'loopback.py')
    E = load('resource_evidence', HERE / 'evidence.py')
    qualified = H.X.load_qualification()
    assert H.X._file_digest(binary) == qualified['sha256']
    source = json.loads((HERE / 'codex-live.json').read_text())['runs'][0]
    reports = []
    with tempfile.TemporaryDirectory(prefix='v127-resource-probe-') as temp:
        for model in ('gpt-6-astra', 'gpt-5.5'):
            for selected in (True, False):
                revision = copy.deepcopy(source['revision'])
                revision['settings']['model'] = model
                if not selected:
                    revision['mcp'] = []
                capability = {'revision':revision, 'skills':[],
                              'instructions':source['configuration']['developer_instructions']}
                inventory = {'jira':{'tools':['jira_search']}} if selected else {}
                cfg = H.X.generated()
                cfg['mcp_servers'] = {'jira':{'enabled_tools':['jira_search']}} if selected else {}
                catalog = H.codex_model(qualified, revision)
                H.codex(cfg, capability, inventory, Path(temp), catalog=catalog)
                wanted = H.expected(capability, inventory)
                result = LB.capture(binary, cfg, catalog=catalog)
                observations = [E.wire_observation(r['body'], wanted, H) for r in result['requests']]
                result.update(expected=wanted, observations=observations, model_catalog=catalog,
                              production=E.production(ROOT), selected_server=selected,
                              owner_decision='Telegram 29400/29401, 2026-09-28')
                name = 'resources-' + model + ('-selected' if selected else '-none') + '.json'
                (HERE / name).write_text(json.dumps(result, indent=1) + '\n')
                report = {'model':model, 'selected_server':selected, 'record':name,
                          'returncode':result['returncode'], 'observations':observations,
                          'exact_equality':result['returncode'] == 0 and bool(observations)
                              and all(o['stop'] is None and o['actual'] == o['expected'] for o in observations)}
                reports.append(report)
                print(json.dumps(report), flush=True)
    (HERE / 'resource-qualification.json').write_text(json.dumps({
        'owner_decision':'Telegram 29400/29401, 2026-09-28',
        'binary_sha256':qualified['sha256'], 'cases':reports,
        'rule':'Exactly three resource readers with a selected MCP server; none without one.',
        'network':'127.0.0.1 stand-in; empty temporary HOME and CODEX_HOME; Landlock TCP restriction'
    }, indent=1) + '\n')


if __name__ == '__main__':
    main(sys.argv[1])
