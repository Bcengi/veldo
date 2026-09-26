#!/usr/bin/env python3
"""Extract the everything-off baseline of the installed Codex vendor binary, VELDO-0156.

Reads only the binary's bytes (nothing is executed, no model runs, nothing logs in, no profile,
credential or configuration file is opened) and writes proof/VELDO-0156/codex-baseline.json: the two
exec options, the configuration keys the generated configuration sets with the values each takes and
its default, the messages `login status` prints for each login, the message the engine refuses a login
with when the ChatGPT login method is forced, and the gate each planted profile or clone item passes
through. The fake engine of scripts/suites/81_veldo_0156_codex_baseline.py loads what it may load from
this table, never from the module under test.

    python3 -B proof/VELDO-0156/extract_baseline.py [--codex PATH]            # write
    python3 -B proof/VELDO-0156/extract_baseline.py --check [--codex PATH]    # compare, exit 1 on a change

Every anchor is the exact text of 0.154.0 and must occur in the binary.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'codex-baseline.json'
DEFAULT_CODEX = Path.home() / ('.nvm/versions/node/v22.22.0/lib/node_modules/@openai/codex/node_modules/@openai/'
                               'codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex')
VERSION = '0.154.0'

OPTIONS = {
    '--ignore-user-config': 'ignore_user_configIGNORE_USER_CONFIGDo not load `$CODEX_HOME/config.toml`; auth still uses '
                            '`CODEX_HOME`ignore-user-config',
    '--ignore-rules': 'ignore_rulesIGNORE_RULESDo not load user or project execpolicy `.rules` filesignore-rules',
    '-c': 'Override a configuration value that would otherwise be loaded from `~/.codex/config.toml`',
    '--disable': 'Disable a feature (repeatable). Equivalent to `-c features.<name>=false`',
}
# The features the baseline turns off with `--disable`: apps, the login's ChatGPT connectors (the binary's
# codex_apps server, which needs the backend login), on by default (`codex features list`).
FEATURES = {'apps': {'value': False, 'default': True, 'anchors': ['ChatGPT connectors require Codex backend auth']}}
# The account profile's own instruction files, read by the binary's codex-home loader into every prompt.
PROFILE_INSTRUCTIONS = {'files': ['AGENTS.override.md', 'AGENTS.md'],
                        'anchors': ['codex-home/src/instructions/mod.rs', 'Failed to read global AGENTS.md instructions from `',
                                    'AGENTS.override.mdAGENTS.md']}
CONFIGURATION = {
    'project_doc_max_bytes': {'value': 0, 'default': 32768, 'anchors': ['project_doc_max_bytes = 32768',
                                                                          'project doc exceeds remaining budget; truncating']},
    'forced_login_method': {'value': 'chatgpt', 'values': ['chatgpt', 'api'], 'default': None,
                            'anchors': ['ForcedLoginMethodchatgptapi']},
    'cli_auth_credentials_store': {'value': 'file', 'values': ['file', 'keyring', 'ephemeral'], 'default': 'file',
                                   'anchors': ['cli_auth_credentials_store = "file"',
                                               'AuthCredentialsStoreModekeyringephemeral']},
    'skills.bundled.enabled': {'value': False, 'default': True,
                               'anchors': ['BundledSkillsConfigSkillConfigSkillsConfigbundledinclude_instructions',
                                           '# Image Generation Skill']},
    'skills.include_instructions': {'value': False, 'default': True,
                                    'anchors': ['bundledinclude_instructionsmax_context_tokensconfig', '<skills_instructions>']},
}
# Each a line of its own (the API key's followed by the key's masked form).
LOGIN_STATUS = ['Not logged in\n', 'Logged in using ChatGPT\n', 'Logged in using an API key - ',
                'Logged in using access token\n', 'Logged in using personal access token\n',
                'Logged in using Amazon Bedrock API key\n', 'Logged in using Amazon Bedrock AWS access keys\n',
                'Logged in using workload identity\n']
REFUSAL = 'ChatGPT login is required, but an API key is currently being used. Logging out.'
GATES = {
    'user_config': {'where': 'the profile config.toml', 'kept_out_by': ['ignore_user_config']},
    'rules': {'where': 'the profile rules/*.rules and the clone .codex/rules/*.rules', 'kept_out_by': ['ignore_rules']},
    'project_doc': {'where': 'the clone AGENTS.md', 'kept_out_by': ['project_doc_max_bytes']},
    'hooks': {'where': 'hooks in the profile config.toml', 'kept_out_by': ['ignore_user_config', 'generated_without_hooks']},
    'skills': {'where': 'the skills section listing every skill of the profile skills/ (and the bundled skills the '
                        'binary installs into its .system), HOME/.agents/skills, the clone .agents/skills and '
                        '.codex/skills', 'kept_out_by': ['skills.include_instructions']},
    'bundled_skills': {'where': 'the bundled skills the binary installs into the profile skills/.system, listed or '
                                'named in the prompt', 'kept_out_by': ['skills.bundled.enabled']},
    'named_skills': {'where': 'a skill named in the prompt ($name) from the profile skills/, HOME/.agents/skills, the '
                              'clone .agents/skills and .codex/skills, from the working directory up to its project '
                              'root', 'kept_out_by': [],
                     'refused': 'invalid_input:engine_profile:skills/<entry>, invalid_input:engine_home:'
                                '.agents/skills/<entry>, invalid_input:engine_clone:<place>/<entry>'},
    'connectors': {'where': 'the login\'s ChatGPT connectors (the apps feature)', 'kept_out_by': ['disable_apps']},
    'profile_instructions': {'where': 'the profile AGENTS.override.md, else AGENTS.md', 'kept_out_by': [],
                             'refused': 'invalid_input:engine_profile:<file>'},
}
HOOK_EVENTS = 'pre_tool_usepermission_requestpost_tool_usepre_compactpost_compactsession_startsession_end'


class Moved(Exception):
    pass


def _digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return 'sha256:' + h.hexdigest()


def extract(path):
    data = Path(path).read_bytes()

    def found(anchor, what):
        count = data.count(anchor.encode())
        if not count:
            raise Moved('%s: not in the binary: %s' % (what, anchor[:80]))
        return {'text': anchor, 'count': count}
    return {'binary': str(path), 'version': VERSION, 'sha256': _digest(path),
            'options': {name: found(anchor, name) for name, anchor in OPTIONS.items()},
            'configuration': {key: dict({k: v for k, v in entry.items() if k != 'anchors'},
                                        anchors=[found(a, key) for a in entry['anchors']])
                              for key, entry in CONFIGURATION.items()},
            'login_status': [found(message, 'login status') for message in LOGIN_STATUS],
            'engine_refusal': found(REFUSAL, 'engine refusal'),
            'hook_events': found(HOOK_EVENTS, 'hook events'),
            'features': {name: dict({k: v for k, v in entry.items() if k != 'anchors'},
                                    anchors=[found(a, name) for a in entry['anchors']])
                         for name, entry in FEATURES.items()},
            'profile_instructions': dict(files=PROFILE_INSTRUCTIONS['files'],
                                         anchors=[found(a, 'profile instructions')
                                                  for a in PROFILE_INSTRUCTIONS['anchors']]),
            'gates': GATES,
            'observed': ['the binary\'s own offline renderer (render_offline.py, codex-rendered.json): the profile '
                         'AGENTS.override.md, else AGENTS.md, is in the prompt under the baseline and no switch '
                         'removes it; skills.include_instructions false removes every skill; --disable apps turns '
                         'the apps feature off',
                         'the binary\'s own model request captured on loopback (capture_mentions.py, '
                         'codex-mentions.json): a skill named in the prompt loads its SKILL.md whatever '
                         'skills.include_instructions says, from the profile, HOME/.agents and the clone under every '
                         'switch tried; skills.bundled.enabled false keeps the bundled set out',
                         'hooks.json beside a configuration layer (the review\'s app-server hooks/list, '
                         '2026-09-26): the profile\'s is discovered untrusted, its trust lives in the profile '
                         'config.toml, which --ignore-user-config does not load']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--codex', default=str(DEFAULT_CODEX))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    try:
        table = extract(args.codex)
    except Moved as error:
        sys.stderr.write('moved: %s\n' % error)
        return 1
    text = json.dumps(table, indent=1, sort_keys=True) + '\n'
    if args.check:
        same = OUT.is_file() and OUT.read_text() == text
        print('codex-baseline.json %s' % ('matches the binary' if same else 'differs from the binary'))
        return 0 if same else 1
    OUT.write_text(text)
    print('wrote %s (%d options, %d configuration keys, %d login messages)'
          % (OUT, len(table['options']), len(table['configuration']), len(table['login_status'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
