#!/usr/bin/env python3
"""Extract the report formats and credential tables of the installed CLIs, VELDO-0062.

Reads only the two binaries' bytes: the schema Claude Code embeds for its stream JSON (the zod
objects its SDK message types are built from) and the literals Codex's Rust binary carries for its
`exec --json` events, its usage-limit message and its credential variables. Nothing is executed, no
model runs, nothing logs in and no profile, credential or configuration file is opened.

    python3 -B proof/VELDO-0062/extract_formats.py [--claude PATH] [--codex PATH]      # write
    python3 -B proof/VELDO-0062/extract_formats.py --check [--claude PATH] [--codex PATH]

Writes proof/VELDO-0062/cli-formats.json. With --check it writes nothing and exits 1 when a fresh
extraction differs from the committed table: after a CLI update that is the signal to regenerate the
table, and the suite's fixture rows then say which fake line no longer matches.

The anchors below are the exact text each table starts from in these versions (Claude Code 2.1.281,
Codex 0.154.0). A version that moved one fails here by name rather than yielding a guessed table.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'cli-formats.json'
DEFAULT_CLAUDE = Path.home() / '.local/share/claude/versions/2.1.281'
DEFAULT_CODEX = Path('/home/dmitry/.nvm/versions/node/v22.22.0/lib/node_modules/@openai/codex/node_modules/'
                     '@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex')


class Moved(Exception):
    pass


def _digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return 'sha256:' + h.hexdigest()


# ---------------------------------------------------------------- Claude Code: the embedded zod schema

# The minified zod helpers of this build, each confirmed by a use only that helper fits.
ZOD = {'d': 'object', 'z': 'enum', 'R': 'literal', 'k': 'number', 'o': 'string', 'O': 'boolean', 'ae': 'any',
       'C': 'array', 'me': 'record', 'Fe': 'union', '_': 'string', 'Mf': 'any'}
ZOD_CONFIRM = ('num_turns:k().int()', 'session_id:o()', 'type:R("assistant")', 'is_error:O()',
               'modelUsage:me(o(),', 'status:z(["allowed","allowed_warning","rejected"])')
SPACE = re.compile(r'\s*')
TOKEN = re.compile(r'\s*(?:(?P<str>"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|`(?:[^`\\]|\\.)*`)|(?P<num>-?\d+(?:\.\d+)?)'
                   r'|(?P<id>[A-Za-z_$][A-Za-z0-9_$]*)|(?P<arrow>=>)|(?P<p>[()\[\]{},.:!?+\-*/<>=&|]))')


class Js:
    """A tokenizer and a recursive reader of zod expressions over the binary's text."""

    def __init__(self, text):
        self.text = text
        self.cache = {}

    def _sites(self, name, suffix):
        key = (name, suffix)
        if key not in self.cache:
            self.cache[key] = list(re.finditer(r'(?<![A-Za-z0-9_$.])' + re.escape(name) + suffix, self.text))
        return self.cache[key]

    def array(self, name, near):
        """The string values of `name=[...]` nearest `near`, or None."""
        sites = self._sites(name, r'=\[("(?:[^"\\]|\\.)*"(?:,"(?:[^"\\]|\\.)*")*)\]')
        if not sites:
            return None
        best = min(sites, key=lambda m: abs(m.start() - near))
        return json.loads('[' + best.group(1) + ']')

    def tokens(self, at):
        while True:
            m = TOKEN.match(self.text, at)
            if not m:
                raise Moved('untokenizable text at %d: %r' % (at, self.text[at:at + 40]))
            kind = m.lastgroup
            yield kind, m.group(kind), m.end()
            at = m.end()

    def definition(self, name, near):
        """The body of `name=f(()=>BODY)` or `name=d(...)` nearest `near` (minified names repeat)."""
        sites = self._sites(name, r'=(f\(\(\)=>)?(?=[A-Za-z_$])')
        if not sites:
            raise Moved('no definition of ' + name)
        best = min(sites, key=lambda m: abs(m.start() - near))
        return best.end(), bool(best.group(1))


class Reader:
    def __init__(self, js, depth):
        self.js = js
        self.depth = depth
        self.seen = []

    def parse(self, at, depth=None):
        """(schema, end) of the zod expression starting at `at`."""
        depth = self.depth if depth is None else depth
        stream = self.js.tokens(at)
        kind, value, end = next(stream)
        if kind == 'str':
            return {'type': 'literal', 'value': json.loads('"%s"' % value[1:-1]) if value[0] != '`' else value[1:-1]}, end
        if kind != 'id':
            raise Moved('expected a zod call at %d, found %r' % (at, value))
        name = value
        kind, value, end = next(self.js.tokens(end))
        if value != '(':
            raise Moved('expected a call of %s at %d' % (name, at))
        args, end = self.arguments(end, depth, name)
        schema = self.build(name, args, at, depth)
        return self.modifiers(schema, end, depth)

    def arguments(self, at, depth, name):
        """The raw argument spans of a call whose '(' ends at `at`; returns (list of (start, text)), end."""
        level, start, spans = 0, at, []
        stream = self.js.tokens(at)
        for kind, value, end in stream:
            if kind == 'p' and value in '([{':
                level += 1
            elif kind == 'p' and value in ')]}':
                if level == 0:
                    if self.js.text[start:end - 1].strip():
                        spans.append(start)
                    return spans, end
                level -= 1
            elif kind == 'p' and value == ',' and level == 0:
                spans.append(start)
                start = end
        raise Moved('unterminated call of ' + name)

    def modifiers(self, schema, at, depth):
        schema = dict(schema)
        while True:
            kind, value, end = next(self.js.tokens(at))
            if value != '.':
                return schema, at
            kind, method, end = next(self.js.tokens(end))
            kind, value, end2 = next(self.js.tokens(end))
            if value != '(':
                return schema, at
            spans, end = self.arguments(end2, depth, method)
            if method == 'optional':
                schema['optional'] = True
            elif method == 'nullable':
                schema['nullable'] = True
            elif method == 'nullish':
                schema['optional'] = schema['nullable'] = True
            elif method == 'int':
                schema['int'] = True
            at = end

    def build(self, name, spans, at, depth):
        kind = ZOD.get(name)
        if kind == 'object':
            return {'type': 'object', 'fields': self.fields(spans[0], depth)}
        if kind == 'enum':
            start = SPACE.match(self.js.text, spans[0]).end()
            if self.js.text[start] != '[':
                # z(NAME): the values are the array NAME names; unresolved, any string.
                kind_, ref, _ = next(self.js.tokens(start))
                m = self.js.array(ref, at)
                return {'type': 'enum', 'values': m, 'ref': ref} if m is not None else {'type': 'string', 'ref': ref}
            body = self.js.text[start:self.js.text.index(']', start) + 1]
            return {'type': 'enum', 'values': json.loads(body)}
        if kind == 'literal':
            kind_, value, end = next(self.js.tokens(spans[0]))
            if kind_ == 'str':
                return {'type': 'literal', 'value': value[1:-1]}
            if value == '!':
                kind_, value, _ = next(self.js.tokens(end))
                return {'type': 'literal', 'value': value == '0'}
            return {'type': 'literal', 'value': value}
        if kind in ('number', 'string', 'boolean', 'any'):
            return {'type': kind}
        if kind == 'array':
            return {'type': 'array', 'items': self.parse(spans[0], depth)[0]}
        if kind == 'record':
            return {'type': 'record', 'values': self.parse(spans[1], depth)[0]}
        if kind == 'union':
            found, pos = [], spans[0] + 1
            while True:
                kind_, value, end = next(self.js.tokens(pos))
                if value == ']':
                    break
                schema, pos = self.parse(pos, depth)
                found.append(schema)
                kind_, value, end = next(self.js.tokens(pos))
                pos = end if value == ',' else pos
            return {'type': 'union', 'anyOf': found}
        if name == 'f':
            return {'type': 'any'}
        # A reference to another definition: resolve it while depth remains.
        if depth <= 0 or name in self.seen:
            return {'type': 'any', 'ref': name}
        self.seen.append(name)
        try:
            body, lazy = self.js.definition(name, at)
            schema, _ = self.parse(body, depth - 1)
        except (Moved, StopIteration):
            schema = {'type': 'any', 'ref': name}
        finally:
            self.seen.pop()
        return dict(schema, ref=name)

    def fields(self, at, depth):
        """The fields of an object literal starting with '{' at `at`."""
        found = {}
        kind, value, pos = next(self.js.tokens(at))
        if value != '{':
            raise Moved('expected an object literal at %d' % at)
        while True:
            kind, key, end = next(self.js.tokens(pos))
            if key == '}':
                return found
            if kind == 'str':
                key = key[1:-1]
            kind, colon, end = next(self.js.tokens(end))
            if colon != ':':
                raise Moved('expected a field at %d' % end)
            schema, pos = self.parse(end, depth)
            found[key] = schema
            kind, value, end = next(self.js.tokens(pos))
            if value == ',':
                pos = end


CLAUDE_EVENTS = {
    # event name: the exact text its zod object starts with in this build.
    'system/init': 'd({type:R("system"),subtype:R("init"),',
    'assistant': 'd({type:R("assistant"),message:',
    'result/success': 'd({type:R("result"),subtype:R("success"),',
    'result/error': 'd({type:R("result"),subtype:z(["error_during_execution"',
    'rate_limit_event': 'd({type:R("rate_limit_event"),',
}

# Claude Code's credential and provider tables, each by the exact text of its first entries, with the
# decision this work takes for it. `strip`: every name it lists never reaches the engine. `keep`: its
# names are not a model login of either CLI once the provider switches are stripped (general cloud or
# tool secrets a worker's own tools use), so only those a strip prefix already covers are removed.
CLAUDE_TABLES = [
    ('auth_credentials', '["ANTHROPIC_API_KEY","ANTHROPIC_AUTH_TOKEN","CLAUDE_CODE_OAUTH_TOKEN","AWS_BEARER_TOKEN_BEDROCK"',
     'strip', 'the credential variables a first-party or provider login reads'),
    ('provider_selection', '["CLAUDE_CODE_USE_BEDROCK","CLAUDE_CODE_USE_VERTEX","CLAUDE_CODE_USE_FOUNDRY","CLAUDE_CODE_USE_ANTHROPIC_AWS"',
     'strip', 'the switches that move Claude Code off the subscription to another provider, with their companions'),
    ('aws_selection', '["CLAUDE_CODE_USE_BEDROCK","CLAUDE_CODE_USE_ANTHROPIC_AWS","CLAUDE_CODE_USE_MANTLE"]',
     'strip', 'the AWS-hosted provider switches'),
    ('aws_bearer', '["AWS_BEARER_TOKEN_BEDROCK","ANTHROPIC_AWS_API_KEY"]', 'strip', 'the AWS-hosted provider keys'),
    ('skip_provider_auth', '["CLAUDE_CODE_SKIP_BEDROCK_AUTH","CLAUDE_CODE_SKIP_VERTEX_AUTH"', 'strip',
     'the switches that skip a provider login'),
    ('anthropic_secrets', '["ANTHROPIC_API_KEY","ANTHROPIC_AUTH_TOKEN","ANTHROPIC_CUSTOM_HEADERS","CLAUDE_CODE_OAUTH_TOKEN",'
     '"CLAUDE_CODE_OAUTH_REFRESH_TOKEN"', 'strip', "Claude Code's own list of Anthropic secrets (with their INPUT_ forms)"),
    ('session_tokens', 'new Set(["CLAUDE_CODE_SESSION_ACCESS_TOKEN","CLAUDE_CODE_OAUTH_TOKEN"])', 'strip',
     'the session tokens a hosted or claimed session authenticates with'),
    ('claimed_session_tokens', 'new Set(["CLAUDE_CODE_OAUTH_TOKEN","CLAUDE_CODE_SESSION_ACCESS_TOKEN","CLAUDE_CODE_HOST_SESSION_ID"])',
     'strip', 'the tokens a claimed spare session is handed'),
    ('api_key_pair', 'new Set(["ANTHROPIC_AUTH_TOKEN","ANTHROPIC_API_KEY"])', 'strip', 'the API key and bearer token'),
    ('bedrock_wizard', 'new Set(["AWS_BEARER_TOKEN_BEDROCK","AWS_SECRET_ACCESS_KEY","AWS_SESSION_TOKEN"])', 'keep',
     'the Bedrock setup wizard\'s AWS credentials: AWS_BEARER_TOKEN_BEDROCK is stripped by auth_credentials; the general '
     'AWS keys are the worker\'s tools\' own cloud login and reach no model once the CLAUDE_CODE_USE_ switches are gone'),
    ('tool_secret_scrub', '["ANTHROPIC_API_KEY","CLAUDE_CODE_OAUTH_TOKEN","CLAUDE_CODE_ARTIFACTS_API_TOKEN"', 'keep',
     'the secrets Claude Code scrubs from its own tool children (package registries, CI, cloud, webhooks): tool '
     'credentials, not a model login'),
]
ENV_ARRAY = re.compile(r'(?:new Set\()?\[("[A-Z0-9_]+"(?:,"[A-Z0-9_]+")*)\]\)?')


def claude(path):
    raw = Path(path).read_bytes()
    text = raw.decode('latin-1')
    for confirm in ZOD_CONFIRM:
        if confirm not in text:
            raise Moved('zod helper use moved: ' + confirm)
    js = Js(text)
    events = {}
    for name, anchor in CLAUDE_EVENTS.items():
        if text.count(anchor) != 1:
            raise Moved('%s: anchor found %d times' % (name, text.count(anchor)))
        schema, _ = Reader(js, depth=4).parse(text.index(anchor))
        events[name] = schema
    tables = []
    for name, anchor, decision, reason in CLAUDE_TABLES:
        at = text.find(anchor)
        if at < 0:
            raise Moved('credential table moved: ' + name)
        m = ENV_ARRAY.match(text, at)
        names = re.findall(r'"([A-Z0-9_]+)"', m.group(1))
        tail = text[m.end():m.end() + 80]
        if name == 'anthropic_secrets' and '.flatMap((e)=>[e,`INPUT_${e}`])' in tail:
            names = names + ['INPUT_' + n for n in names]
        tables.append({'name': name, 'decision': decision, 'reason': reason, 'offset': at, 'names': names})
    endpoints = text.find('[{endpoint:"ANTHROPIC_BASE_URL"')
    if endpoints < 0:
        raise Moved('provider endpoint table moved')
    block = text[endpoints:text.index('}]', endpoints) + 2]
    tables.append({'name': 'provider_endpoints', 'decision': 'strip', 'offset': endpoints,
                   'reason': 'the base URLs that point Claude Code at another endpoint, with their selections and companions',
                   'names': sorted(set(re.findall(r'"([A-Z_][A-Z0-9_]+)"', block)))})
    notes = {}
    for name, start in (('result.usage', 'MAIN AGENT LOOP ONLY'), ('result.modelUsage', 'Per-model totals for every')):
        at = text.find(start)
        if at < 0:
            raise Moved('usage note moved: ' + name)
        note = text[at:text.index('"', at)]
        notes[name] = note.replace('\\u2014', '-').replace('\\u2013', '-')[:600]
    version = Path(path).resolve().name
    return {'binary': str(Path(path).resolve()), 'version': version, 'sha256': _digest(path),
            'source': 'the zod schema of the SDK stream messages embedded in the binary (print mode, stream JSON)',
            'events': events, 'notes': notes, 'credential_tables': tables}


# ---------------------------------------------------------------- Codex: the Rust binary's literals

CODEX_EXEC_RUN = (b'ItemCompletedEventThreadStartedEventthread_idTurnCompletedEventusagein_progresscompletedfailed'
                  b'aggregated_outputexit_codemessagecontent_metastructured_contentinput_tokenscached_input_tokens'
                  b'cache_write_input_tokensoutput_tokensreasoning_output_tokens')
CODEX_TAGS_RUN = (b'ThreadEventThreadStartedthread.startedTurnStartedturn.startedTurnCompletedturn.completedTurnFailed'
                  b'turn.failedItemStarteditem.startedItemUpdateditem.updatedItemCompleteditem.completederror')
CODEX_LIMIT = {
    'message': b"You've hit your usage limit",
    'retry_at': (b' Try again at ', b' or try again at '),
    'retry_later': (b' Try again later.', b' or try again later.'),
    'formats': (b'%-I:%M %p', b'%b %-d', b', %Y %-I:%M %p'),
    'suffixes': b'stndrdth',
}
# Each Codex credential table as (name, the literal before it, its packed names, the literal after it,
# decision, reason): the three pieces must be adjacent in the binary.
CODEX_TABLES = [
    ('auth_env', b'auth.json', b'OPENAI_API_KEYCODEX_API_KEYCODEX_ACCESS_TOKEN', b'no Codex credentials were found',
     'strip', 'the auth variables Codex reads instead of its stored login'),
    ('agent_identity', b'managed MCP requirements do not permit the TUI task-tools server',
     b'CODEX_ACCESS_TOKENOPENAI_FEDERATION_RULE_IDOPENAI_IDENTITY_TOKEN_FILE', b'auth.json', 'strip',
     'the agent identity login'),
    ('bedrock_provider', b'AWS profile name must not be empty.',
     b'AWS_BEARER_TOKEN_BEDROCKAWS_ACCESS_KEY_IDAWS_SECRET_ACCESS_KEY', b'No AWS credentials found', 'keep',
     'the Bedrock provider credentials: AWS_BEARER_TOKEN_BEDROCK is stripped (a model key both CLIs name); the '
     'general AWS keys are the worker\'s tools\' own cloud login, and Codex selects Bedrock only through the '
     'model_provider of the owner-prepared profile'),
    ('exec_server_scrub', b'OPTIONSGETPUTDELETETRACECONNECTPATCH',
     b'OPENAI_FEDERATION_RULE_IDOPENAI_IDENTITY_TOKEN_FILEOPENAI_API_KEYCODEX_API_KEYCODEX_ACCESS_TOKEN'
     b'CODEX_CONNECTORS_TOKENAWS_ACCESS_KEY_IDAWS_SECRET_ACCESS_KEYAWS_SESSION_TOKENAZURE_CLIENT_SECRET'
     b'AZURE_FEDERATED_TOKEN_FILEGOOGLE_APPLICATION_CREDENTIALS', b'codex.exec_server.http_request', 'keep',
     'the secrets the exec server withholds from remote requests: its OpenAI and Codex names are stripped by prefix, '
     'the cloud names are tool credentials'),
    ('shell_env_scrub', b'*KEY**TOKEN*',
     b'CODEX_EXEC_SERVER_NOISE_AUTH_TOKENNODE_REPL_AUTH_TOKENOPENAI_FEDERATION_RULE_IDOPENAI_IDENTITY_TOKEN_FILE',
     b'non-metadata optional permissions', 'keep',
     'the default exclusions of Codex\'s shell environment policy for its tool children: its Codex and OpenAI names are '
     'stripped by prefix, NODE_REPL_AUTH_TOKEN is a tool\'s own'),
]
ENV_NAME_START = re.compile(rb'(?<=[A-Z0-9])(?=(?:OPENAI|CODEX|AWS|AZURE|GOOGLE|NODE)_)')


def _split(run):
    return [part.decode() for part in ENV_NAME_START.split(run) if part]


def codex(path):
    raw = Path(path).read_bytes()
    for run in (CODEX_EXEC_RUN, CODEX_TAGS_RUN):
        if run not in raw:
            raise Moved('codex exec event literals moved')
    limit = {}
    for key, value in CODEX_LIMIT.items():
        for piece in (value if isinstance(value, tuple) else (value,)):
            if piece not in raw:
                raise Moved('codex usage-limit literal moved: %r' % piece)
    limit = {'message': CODEX_LIMIT['message'].decode(),
             'retry_at': [p.decode() for p in CODEX_LIMIT['retry_at']],
             'retry_later': [p.decode() for p in CODEX_LIMIT['retry_later']],
             'formats': ['%-I:%M %p', '%b %-d{suffix}, %Y %-I:%M %p'],
             'suffixes': ['st', 'nd', 'rd', 'th'],
             'source': "protocol error Display: the message, then ' Try again at <local time>.' (same day: %-I:%M %p; "
                       "else %b %-d<suffix>, %Y %-I:%M %p) or ' Try again later.' with no reset"}
    tables = []
    for name, before, run, after, decision, reason in CODEX_TABLES:
        at = raw.find(before + run + after)
        if at < 0:
            raise Moved('codex credential table moved: ' + name)
        tables.append({'name': name, 'decision': decision, 'reason': reason, 'offset': at + len(before),
                       'names': _split(run)})
    usage = {name: {'type': 'number', 'int': True, 'optional': True}
             for name in ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens', 'output_tokens',
                          'reasoning_output_tokens')}
    error = {'type': 'object', 'fields': {'message': {'type': 'string'}}}
    events = {
        'thread.started': {'thread_id': {'type': 'string'}},
        'turn.started': {},
        'turn.completed': {'usage': {'type': 'object', 'fields': usage}},
        'turn.failed': {'error': error},
        'item.started': {'item': {'type': 'any'}},
        'item.updated': {'item': {'type': 'any'}},
        'item.completed': {'item': {'type': 'any'}},
        'error': {'message': {'type': 'string'}},
    }
    events = {name: {'type': 'object', 'fields': dict({'type': {'type': 'literal', 'value': name}}, **fields)}
              for name, fields in events.items()}
    package = Path(path).resolve()
    version = None
    for parent in package.parents:
        manifest = parent / 'package.json'
        if manifest.is_file() and parent.name == 'codex':
            version = json.loads(manifest.read_text()).get('version')
            break
    return {'binary': str(package), 'version': version, 'sha256': _digest(path),
            'source': "the serde names of codex-exec's ThreadEvent (tag 'type') and its payload structs, packed in the "
                      "binary's literals; the strings show field names, not which are always present, so every usage "
                      "field is marked optional",
            'events': events, 'usage_limit': limit, 'credential_tables': tables}


def extract(claude_path, codex_path):
    return {'schema': 'veldo.cli-formats/v1', 'spec_id': 'VELDO-0062',
            'generated_by': 'proof/VELDO-0062/extract_formats.py (reads the binaries\' bytes only)',
            'claude_code': claude(claude_path), 'codex': codex(codex_path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--claude', default=str(DEFAULT_CLAUDE))
    parser.add_argument('--codex', default=str(DEFAULT_CODEX))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    table = extract(args.claude, args.codex)
    text = json.dumps(table, indent=1, sort_keys=True) + '\n'
    if args.check:
        same = OUT.is_file() and OUT.read_text() == text
        print('cli-formats.json %s the installed binaries' % ('matches' if same else 'DIFFERS FROM'))
        return 0 if same else 1
    OUT.write_text(text)
    print('wrote %s (%d bytes)' % (OUT.relative_to(HERE.parents[1]), len(text)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
