"""VELDO-0232 AC1: the committed extractor of Antigravity's CLI (agy), run by .veldo/qualify.py.

    python3 proof/VELDO-0232/extract_agy.py --antigravity <binary> [--out <tables>]

Reads the binary's own bytes and its own `--version` and `--help` output (run in an empty HOME, with no account,
no prompt and no model call) and writes agy-tables.json beside itself (or `--out`):

- version: what `--version` prints; options and subcommands: what `--help` lists.
- stream: the event types the binary's changelog names for stream-json ("typed `init`, `step_update`, and
  terminal `result` events"), the step types (the CortexStepType enum's values in its protobuf descriptor, a
  length-prefixed name followed by its number, lower-cased without the CORTEX_STEP_TYPE_ prefix), the finished
  reasons the changelog names for `finished_reason`, the result's usage fields it names, and the exit codes.
- tool_registry: the harness's tools (every field of antigravity.localharness typed <Name>ToolConfig or
  ToolSearchConfig, in its descriptor) and the step types that are themselves tools (a subagent's, an MCP call).
- credentials: each name of the login and paid-path table the binary's bytes hold, and the LLM gateway family's
  names; session_environment: the names in the families a parent Antigravity session sets (evidence only).
- limits: the plan refusal texts the bytes hold, each with its window, and whether the individual quota text is
  the binary's (it is the server's on 1.5.0).
- load_places: the account folder's and the clone's places the bytes name, where the binary loads instructions,
  rules, skills, plugins, hooks and MCP servers from, and the entries it keeps there that load nothing.
- init_sign_in: the init event field that names the sign-in kind, or null when the bytes name none (limit L3).
Standard library only.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
STEP_PREFIX = b'CORTEX_STEP_TYPE_'
HARNESS = rb'\.antigravity\.localharness\.'
# The login and paid-path names (AC4) the extractor looks for, and the gateway family.
CREDENTIAL_NAMES = ('GEMINI_API_KEY', 'GOOGLE_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_GENAI_USE_VERTEXAI',
                    'GOOGLE_CLOUD_PROJECT', 'GOOGLE_CLOUD_LOCATION', 'GOOGLE_GEMINI_BASE_URL', 'AGY_ADC_AUTH',
                    'AGY_BUSINESS_PAYGO_TIER')
GATEWAY = b'AGY_LLM_GATEWAY_'
# The gateway family's words: a name is the family prefix and these words joined by underscores.
GATEWAY_WORDS = ('API', 'KEY', 'CA', 'CERT', 'CLIENT', 'HEADERS', 'MODELS', 'PROXY', 'URL', 'TIER', 'FLASH', 'LITE',
                 'PRO', 'WIRE', 'PROTOCOL')
SESSION = rb'ANTIGRAVITY_|AGY_|JETSKI_'
REFUSALS = (('Your AI credits balance is too low to continue.', 'ai_credits'),)
QUOTA_TEXT = 'Individual quota reached'
# The step types that are tools of their own beside the harness's configured ones.
STEP_TOOLS = ('invoke_subagent', 'browser_subagent', 'mcp_tool')
# The account folder's places (relative to the engine's HOME) and the clone's: each kept only when the bytes name
# it. `inert` entries are the binary's own bookkeeping in that place, which load nothing into a run.
PROFILE_PLACES = (('.gemini/GEMINI.md', ()), ('.gemini/AGENTS.md', ()),
                  ('.gemini/config', ('projects', '.migrated', 'mcp_config.json', 'config.json')),
                  ('.gemini/config/mcp_config.json', ()), ('.gemini/antigravity-cli/hooks.json', ()))
CLONE_PLACES = (('GEMINI.md', ()), ('AGENTS.md', ()), ('.agents', ()), ('.agent', ()))
# Kept out by an option of the qualified flags: the binary's own built-in skills (skill expansion off in print mode).
KEPT_OUT = (('.gemini/antigravity-cli/builtin', '--disable-slash-commands'),)


def run(binary, *args):
    with tempfile.TemporaryDirectory(prefix='veldo-agy-extract-') as home:
        done = subprocess.run([str(binary)] + list(args), capture_output=True, text=True, timeout=60, cwd=home,
                              stdin=subprocess.DEVNULL,
                              env={'PATH': '/usr/bin:/bin', 'HOME': home, 'LANG': 'C.UTF-8', 'TMPDIR': home,
                                   'AGY_CLI_DISABLE_AUTO_UPDATE': '1'})
    return done.stdout + done.stderr


def descriptor_names(data, prefix):
    """The enum value names of a protobuf descriptor that start with `prefix`: field 1 (0x0a, a length byte, the
    name) followed by field 2 (0x10, the number)."""
    found = set()
    for hit in re.finditer(rb'\x0a([\x01-\x7f])(' + re.escape(prefix) + rb')', data):
        size, start = hit.group(1)[0], hit.start(2)
        name = data[start:start + size]
        if re.fullmatch(re.escape(prefix) + rb'[A-Z0-9_]+', name) and data[start + size:start + size + 1] == b'\x10':
            found.add(name[len(prefix):].decode().lower())
    return found


def harness_tools(data):
    """The fields of antigravity.localharness typed <Name>ToolConfig (or ToolSearchConfig): the harness's tools."""
    found = set()
    for hit in re.finditer(HARNESS + rb'([A-Za-z]+ToolConfig|ToolSearchConfig)R', data):
        head = data[max(0, hit.start() - 96):hit.start()]
        at = head.rfind(b'\x0a')
        while at >= 0:
            size = head[at + 1] if at + 1 < len(head) else 0
            name = head[at + 2:at + 2 + size]
            if re.fullmatch(rb'[a-z_]+', name) and head[at + 2 + size:at + 3 + size] == b'\x18':
                found.add(name.decode()[:-len('_config')] if name.endswith(b'_config') else name.decode())
                break
            at = head.rfind(b'\x0a', 0, at)
    return found


def changelog_words(data, pattern):
    hit = re.search(pattern, data, re.S)
    return re.findall(rb'`([a-z_]+)`', hit.group(0)) if hit else []


def gateway(data):
    """The gateway family's names: the prefix and the family's words joined by underscores, longest first."""
    words = b'|'.join(re.escape(w.encode()) for w in sorted(GATEWAY_WORDS, key=len, reverse=True))
    names = set()
    for hit in re.finditer(re.escape(GATEWAY) + rb'((?:' + words + rb')(?:_(?:' + words + rb'))*)', data):
        names.add((GATEWAY + hit.group(1)).decode())
    return names


def session_names(data):
    """The names in the families a parent Antigravity session sets, cut where a family prefix starts a new literal
    (evidence only: the prefixes decide the strip)."""
    names = set()
    for hit in re.finditer(rb'(?<![A-Z0-9_])(?:' + SESSION + rb')[A-Z0-9_]*', data):
        for piece in re.split(rb'(?<!_)(?=' + SESSION + rb')', hit.group(0)):
            # A piece longer than any one name is literals packed together, and is dropped.
            if re.fullmatch(rb'(?:' + SESSION + rb')[A-Z0-9_]*[A-Z0-9]', piece) and len(piece) <= 64:
                names.add(piece.decode())
    return names


def tables(binary):
    data = Path(binary).read_bytes()
    version = re.search(r'[0-9]+(?:\.[0-9]+){1,3}', run(binary, '--version'))
    help_text = run(binary, '--help')
    options = sorted(set(re.findall(r'^\s{2}(--?[a-z][a-z-]*)\s', help_text, re.M)))
    commands = help_text.split('Available subcommands:', 1)[1] if 'Available subcommands:' in help_text else ''
    subcommands = sorted(set(re.findall(r'^\s{2}([a-z][a-z-]*)\s', commands, re.M)))
    events = [w.decode() for w in changelog_words(data, rb'emits typed `[a-z_]+`[^.]*?terminal `[a-z_]+` events')]
    reasons = [w.decode() for w in changelog_words(data, rb'`finished_reason` field.*?omitted when')
               if w != b'finished_reason' and not w.startswith(b'output')]
    steps = descriptor_names(data, STEP_PREFIX)
    registry = harness_tools(data) | {s for s in STEP_TOOLS if s in steps}
    credentials = {n: n.encode() in data for n in CREDENTIAL_NAMES}
    credentials.update({n: True for n in gateway(data)})
    sign_in = None  # The 1.5.0 bytes name no sign-in field of the init event (limit L3); a later reader adds one.
    return {
        'schema': 'veldo.antigravity_tables/v1', 'spec_id': 'VELDO-0232',
        'version': version.group(0) if version else None,
        'options': options, 'subcommands': subcommands,
        'stream': {'events': events, 'step_types': sorted(steps), 'finished_reasons': reasons,
                   'usage_fields': ['input_tokens', 'output_tokens'] + (
                       ['cache_read_tokens'] if b'json:"cache_read_tokens"' in data else []),
                   'exit_codes': {'0': 'complete', '1': 'usage_error', '2': 'usage_error', '3': 'agent_error'},
                   'agy_error': b'AGY_ERROR' in data},
        'tool_registry': sorted(registry),
        'credentials': dict(sorted(credentials.items())),
        'session_environment': sorted(session_names(data)),
        'limits': {'refusals': [[text, window] for text, window in REFUSALS if text.encode() in data],
                   'quota': {'text': QUOTA_TEXT, 'in_binary': QUOTA_TEXT.encode() in data}},
        'load_places': {
            'profile': [{'path': p, 'inert': list(inert)} for p, inert in PROFILE_PLACES
                        if p.encode() in data or (p + '/').encode() in data],
            'clone': [{'path': p, 'inert': list(inert)} for p, inert in CLONE_PLACES
                      if p.encode() in data or (p + '/').encode() in data],
            'kept_out': [{'path': p, 'option': o} for p, o in KEPT_OUT if o in options]},
        'init_sign_in': sign_in,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='Extract the qualified tables of an Antigravity CLI binary.')
    parser.add_argument('--antigravity', required=True, help='the binary')
    parser.add_argument('--out', default=str(HERE / 'agy-tables.json'))
    args = parser.parse_args(argv)
    found = tables(args.antigravity)
    if not found['version'] or not found['options'] or not found['stream']['events'] or not found['tool_registry']:
        raise SystemExit('extract_agy: %s is not a readable Antigravity CLI' % args.antigravity)
    Path(args.out).write_text(json.dumps(found, indent=1, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
