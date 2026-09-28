#!/usr/bin/env python3
"""Extract the everything-off baseline of the installed Claude Code binary, VELDO-0155.

Reads only the binary's bytes (nothing is executed, no model runs, nothing logs in, no profile,
credential or configuration file is opened) and writes proof/VELDO-0155/claude-baseline.json: every
option, environment switch and setting the baseline uses, each with the exact text of the binary that
declares or reads it; the gate each profile source passes through (which switch keeps which item out,
as the binary's own code decides it); the bundled skills; the init event's apiKeySource values; the
Anthropic profile store the engine reads ahead of the claude.ai login; and the stream JSON input
protocol the receiver speaks (the initialize control request, its answer and the login it reports, the
user message the prompt is written as). The fake engines of
scripts/suites/80_veldo_0155_claude_baseline.py, 78_veldo_0060_claude_adapter.py and
75_veldo_0062_accounts.py take what they load and how they answer from this table, never from the module
under test.

    python3 -B proof/VELDO-0155/extract_baseline.py [--claude PATH]            # write
    python3 -B proof/VELDO-0155/extract_baseline.py --check [--claude PATH]    # compare, exit 1 on a change

Every anchor is the exact text of 2.1.281 and must occur in the binary; a version that moved one fails
here by name rather than yielding a guessed table.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'claude-baseline.json'
FORMATS = HERE.parent / 'VELDO-0062' / 'cli-formats.json'
DEFAULT_CLAUDE = Path.home() / '.local/share/claude/versions/2.1.281'
VERSION = '2.1.281'

# Each option of the baseline, as the main command declares it, and the two it deliberately does not use.
OPTIONS = {
    '--setting-sources': '.option("--setting-sources <sources>","Comma-separated list of setting sources to load (user, project, local).")',
    '--settings': '"--settings <file-or-json>"',
    '--strict-mcp-config': '.option("--strict-mcp-config","Only use MCP servers from --mcp-config, ignoring all other MCP configurations",()=>!0)',
    '--mcp-config': '"--mcp-config <configs...>"',
    '--disable-slash-commands': '.option("--disable-slash-commands","Disable all skills",()=>!0)',
    # VELDO-0141: the stream options every run adds so partial messages and subagent text reach the stream.
    '--include-partial-messages': '.option("--include-partial-messages","Include partial message chunks as they arrive (only works with --print and --output-format=stream-json)",()=>!0)',
    '--forward-subagent-text': '.option("--forward-subagent-text","Forward subagent text and thinking blocks as assistant/user messages with parent_tool_use_id set (only works with --print and --output-format=stream-json)",()=>!0)',
}
NOT_USED = {
    '--bare': 'Anthropic auth is strictly ANTHROPIC_API_KEY or apiKeyHelper via --settings (OAuth and keychain are never read)',
    '--safe-mode': 'claude.ai connectors are not loaded in this Claude Code session (safe mode)',
}
# What the binary reads for each switch.
SWITCHES = {
    'setting_sources': {'kind': 'option', 'name': '--setting-sources', 'value': '',
                        'anchors': ['function KIr(e){if(e==="")return[];',
                                    'function d$n(){let r=vD("--setting-sources");if(r!==void 0)g(r);',
                                    'let t=new Set(e);t.add("flagSettings"),t.add("policySettings");']},
    'strict_mcp_config': {'kind': 'option', 'name': '--strict-mcp-config',
                          'anchors': ['ns=(wt||uo()||Vn()?Promise.resolve({servers:{}}):wO(',
                                      'function HZe(){return!VI()&&!d2e()&&!uo()}']},
    'disable_slash_commands': {'kind': 'option', 'name': '--disable-slash-commands',
                               'anchors': ['Ce=this.disableSlashCommands?this.noCommands:']},
    'disable_claude_mds': {'kind': 'environment', 'name': 'CLAUDE_CODE_DISABLE_CLAUDE_MDS', 'value': '1',
                           'anchors': ['function aH(){return Boolean(a.CLAUDE_CODE_DISABLE_CLAUDE_MDS||',
                                       'async function set(e,n,r){if(a.CLAUDE_CODE_DISABLE_CLAUDE_MDS)return[];']},
    'disable_auto_memory': {'kind': 'environment', 'name': 'CLAUDE_CODE_DISABLE_AUTO_MEMORY', 'value': '1',
                            'anchors': ['let e=process.env.CLAUDE_CODE_DISABLE_AUTO_MEMORY;if(Oe(e))return"off";',
                                        'if(Va()){if(n={auto:Qs()}']},
    'disable_all_hooks': {'kind': 'setting', 'name': 'disableAllHooks', 'value': True,
                          'anchors': ['let t=Un();if(t.disableAllHooks===!0)return o?.hooks??{};return t.hooks??{}']},
    # VELDO-0141: the two stream options (boolean; each honored only with --print and stream JSON output,
    # which the qualified flags carry): partial message chunks, and subagent text and thinking forwarded as
    # messages with parent_tool_use_id set, without which a subagent's work is hidden from the stream.
    'include_partial_messages': {'kind': 'option', 'name': '--include-partial-messages',
                                 'anchors': ['if(ie){if(!Ze||ze!=="stream-json"){if(ko)return Yt("Error: --include-partial-messages requires --print and --output-format=stream-json.");ie=!1}}']},
    'forward_subagent_text': {'kind': 'option', 'name': '--forward-subagent-text',
                              'anchors': ['if(_e){if(!Ze||ze!=="stream-json"){if(vo)return Yt("Error: --forward-subagent-text requires --print and --output-format=stream-json.");_e=!1}}',
                                          'forwardSubagentText:n.options.forwardSubagentText??!1']},
}
# The gate every planted item passes through, as the binary decides it: the switches that each keep it
# out on their own. An item listed with two is kept out by either, so dropping one of them loads nothing.
GATES = {
    'settings': {'where': 'the profile settings.json (user source) and the clone .claude/settings.json and '
                          'settings.local.json (project and local sources)',
                 'kept_out_by': ['setting_sources'],
                 'anchors': ['function pr(e){return us().includes(e)}']},
    'mcp_profile': {'where': 'the profile .claude.json mcpServers (user scope) and the clone .mcp.json (project scope)',
                    'kept_out_by': ['setting_sources', 'strict_mcp_config'],
                    'anchors': ['let r={project:"projectSettings",user:"userSettings",local:"localSettings"};'
                                'if(e in r&&!(e==="local"?f5e():pr(r[e])))return{servers:OP(),errors:[]};']},
    'mcp_claudeai': {'where': 'the claude.ai connectors of the account profile\'s login',
                     'kept_out_by': ['strict_mcp_config'],
                     'anchors': ['function HZe(){return!VI()&&!d2e()&&!uo()}',
                                 'let di=Ze&&!oe&&HZe()?jbe(w)']},
    'skill_profile': {'where': 'the profile skills/ (user source) and the clone .claude/skills/ (project source)',
                      'kept_out_by': ['setting_sources', 'disable_slash_commands'],
                      'anchors': ['pr("userSettings")&&!_?NP(r,"userSettings","skills",n)']},
    'skill_bundled': {'where': 'the skills the binary bundles',
                      'kept_out_by': ['disable_slash_commands'],
                      'anchors': ['Ce=this.disableSlashCommands?this.noCommands:']},
    'instructions_profile': {'where': 'the profile CLAUDE.md (user) and the clone CLAUDE.md (project)',
                             'kept_out_by': ['setting_sources', 'disable_claude_mds'],
                             'anchors': ['Pe=pr("userSettings"),Le=we(),De=$8("User")',
                                         'We=pw("projectSettings"),st=pw("localSettings")']},
    'memory': {'where': 'the profile projects/<project>/memory/MEMORY.md (auto memory)',
               'kept_out_by': ['disable_auto_memory'],
               'anchors': ['function By(){if(Ar())return"off";if(gC())return"off";']},
    'hooks_profile': {'where': 'hooks in the profile settings.json and the clone .claude/settings.json',
                      'kept_out_by': ['setting_sources', 'disable_all_hooks'],
                      'anchors': ['let t=Un();if(t.disableAllHooks===!0)return o?.hooks??{};return t.hooks??{}']},
}
# The login the init event cannot show: the Anthropic profile store and its precedence over claude.ai.
PROFILE = {
    'store': 'let n=e.XDG_CONFIG_HOME?.trim();if(n)return{dir:g(n,"anthropic"),space:"home"};let s=e.HOME?.trim();'
             'return s?{dir:g(s,".config","anthropic"),space:"home"}:null',
    'types': 'if(n==="oidc_federation"||n==="user_oauth")return"profile-implicit"',
    'precedence': 'if(Oc())return{source:"profile",hasToken:!0};let r=un();if(_N(r?.scopes)&&r?.accessToken)'
                  'return{source:"claude.ai",hasToken:!0}',
    'init_source': 'function zrn(){return Yf().source}',
    'no_key': 'let g=pBn();if(g)return g;return{key:null,source:"none"}',
}
# THE INPUT PROTOCOL (stream JSON input, VELDO-0155 AC3): the initialize control request the receiver sends
# first, whose answer carries the login (`account`, the binary's Kfe(): apiKeySource set only when an API key
# is in use, the same Yf() whose source the init event reports; tokenSource the token login Mc() found,
# unless it is a claude.ai subscription (subscriptionType instead) or an Anthropic profile (neither);
# apiProvider the backend, a subscription only on firstParty); the prompt is then written as a user message.
INPUT = {
    'requires': 'if(me==="stream-json"&&ze!=="stream-json")return Yt("Error: --input-format=stream-json requires '
                'output-format=stream-json.");if(me==="stream-json"&&!Te())return Yt("Error: --input-format=stream-json '
                'requires --print.");',
    'control_request': 'Ax=f(()=>Yo("type",[d({type:R("control_request"),request_id:o(),request:kx()}),O1n(),M1n()]))',
    'initialize': 'ssn=f(()=>d({subtype:R("initialize"),hooks:me(GR(),C(nF())).optional()',
    'control_response': 'O1n=f(()=>d({type:R("control_response"),response:Fe([_Y(),mY()])})',
    'success': '_Y=f(()=>d({subtype:R("success"),request_id:o()',
    'error': 'mY=f(()=>d({subtype:R("error"),request_id:o()',
    'answer': 'ie=Kfe(),z=g().toolPermissionContext.mode',
    'account': 'account:{email:ie?.email,organization:ie?.organization,subscriptionType:ie?.subscription,'
               'tokenSource:ie?.tokenSource,apiKeySource:ie?.apiKeySource,apiProvider:He()}',
    'account_login': 'function Kfe(){if(He()!=="firstParty")return;let{source:n}=Mc(),r={};',
    'account_key': 'let{key:s,source:g}=Yf();if(s)r.apiKeySource=g;',
    'providers': 'apiProvider:z(["firstParty","bedrock","vertex","foundry","anthropicAws","anthropicGoogleCloud",'
                 '"mantle","gateway"])',
    'user': 'XR=f(()=>d({type:R("user"),message:J0(),parent_tool_use_id:o().nullable()',
    'answered': 's.enqueue({type:"control_response",response:{subtype:"success",request_id:r,response:Pe,',
    'account_token': 'if(n==="CLAUDE_CODE_OAUTH_TOKEN"||n==="CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR")r.tokenSource=n;'
                     'else if(pt())r.subscription=wBn();else if(n!=="profile")r.tokenSource=n;',
    'token_sources': 'function Mc(){if(uo()){if(D_())return{source:"apiKeyHelper",hasToken:!0};return{source:"none",'
                     'hasToken:!1}}if(hH()&&!_Ht())return{source:"ANTHROPIC_AUTH_TOKEN",hasToken:!0};'
                     'if(a.CLAUDE_CODE_OAUTH_TOKEN)return{source:"CLAUDE_CODE_OAUTH_TOKEN",hasToken:!0};if(OI()){'
                     'if(q4("CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR"))return{source:"CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR",'
                     'hasToken:!0};return{source:"CCR_OAUTH_TOKEN_FILE",hasToken:!0}}if(D_()&&!In())return{source:'
                     '"apiKeyHelper",hasToken:!0};if(Oc())return{source:"profile",hasToken:!0};let r=un();'
                     'if(_N(r?.scopes)&&r?.accessToken)return{source:"claude.ai",hasToken:!0};return{source:"none",'
                     'hasToken:!1}}',
    'subscriptions': 'function wBn(){switch(tr()){case"enterprise":return"Claude Enterprise";case"team":return'
                     '"Claude Team";case"max":return"Claude Max";case"pro":return"Claude Pro";default:return"Claude API"}}',
}
BUNDLED = re.compile(r'Vo\(\{name:"([a-z][a-z0-9-]*)",(?:menuDescription|description):')


class Moved(Exception):
    pass


def _digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return 'sha256:' + h.hexdigest()


def extract(path):
    text = Path(path).read_bytes().decode('latin-1')

    def found(anchor, what):
        count = text.count(anchor)
        if not count:
            raise Moved('%s: not in the binary: %s' % (what, anchor[:80]))
        return {'text': anchor, 'count': count}
    table = {'binary': str(path), 'version': VERSION, 'sha256': _digest(path),
             'options': {name: found(anchor, name) for name, anchor in OPTIONS.items()},
             'not_used': {name: found(anchor, name) for name, anchor in NOT_USED.items()},
             'switches': {}, 'gates': {}, 'profile': {},
             'input_protocol': {name: found(anchor, 'input ' + name) for name, anchor in INPUT.items()}}
    protocol = table['input_protocol']

    def values(name, pattern):
        return list(dict.fromkeys(re.findall(pattern, INPUT[name])))
    protocol['providers'] = dict(protocol['providers'], values=values('providers', r'"([A-Za-z]+)"'),
                                 subscription='firstParty')
    # Kfe()'s tokenSource: every source Mc() returns but an Anthropic profile's; the one the receiver
    # configures is the account's own subscription token.
    protocol['token_sources'] = dict(protocol['token_sources'], subscription_token='CLAUDE_CODE_OAUTH_TOKEN',
                                     values=[v for v in values('token_sources', r'source:"([^"]+)"') if v != 'profile'])
    protocol['subscriptions'] = dict(protocol['subscriptions'], values=values('subscriptions', r'return"([^"]+)"'))
    protocol['flags'] = ['--input-format', 'stream-json']
    for name, entry in SWITCHES.items():
        table['switches'][name] = dict({k: v for k, v in entry.items() if k != 'anchors'},
                                       anchors=[found(a, name) for a in entry['anchors']])
    for name, entry in GATES.items():
        table['gates'][name] = dict({k: v for k, v in entry.items() if k != 'anchors'},
                                    anchors=[found(a, name) for a in entry['anchors']])
    for name, anchor in PROFILE.items():
        table['profile'][name] = found(anchor, 'profile ' + name)
    table['profile']['types'] = dict(table['profile']['types'], values=['user_oauth', 'oidc_federation'])
    bundled = sorted(set(BUNDLED.findall(text)))
    if 'update-config' not in bundled:
        raise Moved('bundled skills: update-config is not registered')
    table['bundled_skills'] = bundled
    formats = json.loads(FORMATS.read_text())['claude_code']
    sources = formats['events']['system/init']['fields']['apiKeySource']['values']
    if formats['sha256'] != table['sha256'] or 'none' not in sources:
        raise Moved('the apiKeySource values are not this binary\'s')
    table['api_key_sources'] = list(sources)
    return table


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--claude', default=str(DEFAULT_CLAUDE))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    try:
        table = extract(args.claude)
    except Moved as error:
        sys.stderr.write('moved: %s\n' % error)
        return 1
    text = json.dumps(table, indent=1, sort_keys=True) + '\n'
    if args.check:
        same = OUT.is_file() and OUT.read_text() == text
        print('claude-baseline.json %s' % ('matches the binary' if same else 'differs from the binary'))
        return 0 if same else 1
    OUT.write_text(text)
    print('wrote %s (%d switches, %d gates, %d bundled skills)' % (OUT, len(table['switches']), len(table['gates']),
                                                                    len(table['bundled_skills'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
