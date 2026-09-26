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

# Claude Code's lists that spread other lists (`...NAME`), each read with every spread resolved to the
# nearest definition of that minified name: (name, the exact text the list starts with, decision, reason,
# exceptions). `strip`: every name is a login, credential, credential or settings redirect, endpoint or
# paid-API switch; it never reaches the engine from the inherited environment and a configured one is
# refused. The exceptions of a strip list name what it holds that is not a login: `keep` names are the
# general proxy, CA, runtime, cloud and home names the worker's own tools need, passed as inherited;
# `setting` names are Claude Code's own non-login settings, stripped from the inherited environment (they
# are the owner's shell's, not the adapter's) but passed when the adapter configures them.
KEEP_PROXY = ('HTTPS_PROXY', 'HTTP_PROXY', 'NO_PROXY', 'ALL_PROXY')
KEEP_RUNTIME = ('NODE_EXTRA_CA_CERTS', 'NODE_TLS_REJECT_UNAUTHORIZED', 'NODE_OPTIONS')
KEEP_CLOUD = ('GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_CLOUD_PROJECT', 'GOOGLE_EXTERNAL_ACCOUNT_ALLOW_EXECUTABLES',
              'GCLOUD_PROJECT', 'CLOUDSDK_CONFIG', 'METADATA_SERVER_DETECTION')
KEEP_CLOUD_PREFIXES = ('AWS_', 'GCE_METADATA_')
KEEP_HOME = ('HOME', 'XDG_CONFIG_HOME', 'APPDATA', 'USERPROFILE', 'HOMEDRIVE', 'HOMEPATH', 'PROGRAMDATA')
CLAUDE_SETTINGS = ('CLAUDE_CODE_PROXY_RESOLVES_HOSTS', 'CLAUDE_CODE_ENABLE_PROXY_AUTH_HELPER',
                   'CLAUDE_CODE_PROXY_AUTH_HELPER_TTL_MS', 'API_FORCE_IDLE_TIMEOUT', 'CLAUDE_CODE_CERT_STORE')


def _sensitive_exceptions(names):
    """The names of Claude Code's sensitive-variable set that are not a login, each with why."""
    found = {}
    for name in names:
        if name in KEEP_PROXY:
            found[name] = {'decision': 'keep', 'reason': 'general proxy: the worker\'s tools reach the network through it'}
        elif name in KEEP_RUNTIME:
            found[name] = {'decision': 'keep', 'reason': 'CA and runtime: the worker\'s tools verify TLS and run node with it'}
        elif (name in KEEP_CLOUD or name.startswith(KEEP_CLOUD_PREFIXES)) and name != 'AWS_BEARER_TOKEN_BEDROCK':
            found[name] = {'decision': 'keep', 'reason': 'cloud: the worker\'s tools\' own cloud login; no model request '
                           'goes through it once the provider switches are stripped'}
        elif name in KEEP_HOME:
            found[name] = {'decision': 'keep', 'reason': 'home: every tool the worker runs needs its home directory'}
        elif name in CLAUDE_SETTINGS:
            found[name] = {'decision': 'setting', 'reason': 'a Claude Code connection setting, not a login'}
    return found


CLAUDE_LISTS = [
    ('sensitive_env', 'var ji=new Set(["HTTPS_PROXY"', 'strip',
     'the variables Claude Code refuses to take from a settings file: its logins, the credential and settings '
     'redirects (CLAUDE_SECURESTORAGE_CONFIG_DIR, CLAUDE_CODE_HOST_CREDS_FILE, the managed and remote settings paths, '
     'the OAuth, bridge and federation overrides), the endpoints and provider switches', _sensitive_exceptions),
    ('fd_tokens', 'Q0t=["CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR"', 'strip',
     'the credentials handed to Claude Code through a file descriptor', None),
    ('session_secrets', 'Z0t=["CLAUDE_CODE_OAUTH_TOKEN",...Q0t', 'strip',
     'the OAuth, bridge, trusted-device and background-session tokens and auth paths', None),
    ('host_creds_env', 'Spo=new Set([...YU,...hW.filter(', 'strip',
     'the variables a CLAUDE_CODE_HOST_CREDS_FILE may set when Claude Code copies it into its environment at start-up',
     None),
    ('model_config', 'z4e=["ANTHROPIC_MODEL"', 'model',
     'the model configuration: stripped from the inherited environment only through the ANTHROPIC_ family, passed '
     'when the adapter configures it (the configured model is a capability, not a login)', None),
    ('custom_model_option', 'Bin=["ANTHROPIC_CUSTOM_MODEL_OPTION"', 'model', 'the custom model option, as model_config',
     None),
    ('not_secrets', 'Gi=new Set(["CLAUDE_CODE_CLIENT_KEY"', 'keep',
     'the names Claude Code itself says look like a secret and are not (its token thresholds and usage settings); '
     'a name here that a strip list also names is stripped', None),
]
# The one filtered spread these lists use, as the binary writes it: Spo takes hW without the first-party
# assumption, the artifact names and the memory API names (Ame is Xo.includes).
HOST_CREDS_FILTER = ('...hW.filter((e)=>e!=="_CLAUDE_CODE_ASSUME_FIRST_PARTY_BASE_URL"&&!e.startsWith("CLAUDE_CODE_ARTIFACT")'
                     '&&!Ame(e))')
AME = 'function Ame(e){return Xo.includes(e)}'


def _js_list(js, at, seen=()):
    """The string values of the array literal whose '[' is the first one at or after `at`, every
    `...NAME` spread resolved to the nearest definition of NAME (and the one filtered spread above)."""
    text = js.text
    start = text.index('[', at)
    names, depth, pos, item = [], 0, start + 1, ''
    items = []
    while True:
        ch = text[pos]
        if ch == '"':
            end = text.index('"', pos + 1)
            item += text[pos:end + 1]
            pos = end + 1
            continue
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            if depth == 0:
                items.append(item)
                break
            depth -= 1
        elif ch == ',' and depth == 0:
            items.append(item)
            item = ''
            pos += 1
            continue
        item += ch
        pos += 1
    for item in (i.strip() for i in items):
        if not item:
            continue
        if re.fullmatch(r'"[A-Za-z0-9_]+"', item):
            names.append(item[1:-1])
        elif item == HOST_CREDS_FILTER:
            if text.count(AME) != 1:
                raise Moved('the memory-name test of the host credentials filter moved')
            memory = _js_list(js, _definition(js, 'Xo', text.index(AME)), seen)
            names += [n for n in _js_list(js, _definition(js, 'hW', at), seen)
                      if n != '_CLAUDE_CODE_ASSUME_FIRST_PARTY_BASE_URL' and not n.startswith('CLAUDE_CODE_ARTIFACT')
                      and n not in memory]
        elif re.fullmatch(r'\.\.\.[A-Za-z_$][A-Za-z0-9_$]*', item):
            ref = item[3:]
            if ref in seen:
                raise Moved('a list spreads itself: ' + ref)
            names += _js_list(js, _definition(js, ref, at), seen + (ref,))
        else:
            raise Moved('an unread list item at %d: %r' % (start, item[:80]))
    return names


def _definition(js, name, near):
    """The offset of the nearest `NAME=[` or `NAME=new Set([` (minified names repeat)."""
    sites = js._sites(name, r'=(?:new Set\()?\[')
    if not sites:
        raise Moved('no list named ' + name)
    return min(sites, key=lambda m: abs(m.start() - near)).start()


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
    for name, anchor, decision, reason, exceptions in CLAUDE_LISTS:
        if text.count(anchor) != 1:
            raise Moved('%s: anchor found %d times' % (name, text.count(anchor)))
        at = text.index(anchor)
        names = list(dict.fromkeys(_js_list(js, at)))
        if len(names) < 2 or not all(re.fullmatch(r'[A-Z_][A-Z0-9_]*', n) for n in names):
            raise Moved('%s: not a list of variable names' % name)
        table = {'name': name, 'decision': decision, 'reason': reason, 'offset': at, 'names': names}
        if exceptions is not None:
            table['exceptions'] = exceptions(names)
        tables.append(table)
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
        notes[name] = note.replace('\\u2014', '-').replace('\\u2013', '-')[:1000]
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
# The auth, endpoint and credential-redirect variables Codex reads, each by its literal neighbours (all
# `strip`: a login, a login endpoint, the model endpoint or a redirect of where the login or its state is
# read; each is also under the OPENAI_ or CODEX_ family, so the tables are what refuses them when an
# adapter configures one).
CODEX_TABLES += [
    ('agent_identity_endpoints', b'error', b'CODEX_AGENT_IDENTITY_AUTHAPI_BASE_URLCODEX_AGENT_IDENTITY_JWKS_BASE_URL',
     b'https://auth.openai.com/api/accounts', 'strip', 'the agent identity login endpoints'),
    ('auth_endpoint', b'agent identity registration attempt failed; retrying',
     b'CODEX_AGENT_IDENTITY_JWKS_BASE_URLCODEX_AUTHAPI_BASE_URL', b'https://auth.openai.com/api/accounts', 'strip',
     'the account login endpoint'),
    ('refresh_override', b'', b'CODEX_REFRESH_TOKEN_URL_OVERRIDE', b'login/src/auth/default_client.rs', 'strip',
     'the token refresh endpoint'),
    ('login_client', b'login/src/auth/default_client.rs', b'CODEX_APP_SERVER_LOGIN_CLIENT_ID',
     b'codex-mcp/src/binding_clients.rs', 'strip', 'the login client id'),
    ('login_issuer', b'ChatGPT login is disabled. Use API key login instead.', b'CODEX_APP_SERVER_LOGIN_ISSUER',
     b'Amazon Bedrock API key must not be empty.', 'strip', 'the login issuer'),
    ('revoke_override', b'token', b'CODEX_REVOKE_TOKEN_URL_OVERRIDE', b'https://auth.openai.com/oauth/revoke', 'strip',
     'the token revocation endpoint'),
    ('chatgpt_base', b'is_workspace_account', b'CODEX_APP_SERVER_CHATGPT_BASE_URL', b'/backend-api', 'strip',
     'the ChatGPT backend the subscription login talks to'),
    ('openai_base', b'GITHUB_ENTERPRISE_TOKEN', b'OPENAI_BASE_URL', b'sk-OPENAI_API_KEY', 'strip',
     'the model endpoint of the built-in OpenAI provider'),
    ('oss_provider', b'provider auth.command must not be empty', b'CODEX_OSS_PORTCODEX_OSS_BASE_URL', b'responses',
     'strip', 'the endpoint of the local model provider'),
    ('organization', b'OpenAI-Organization', b'OPENAI_ORGANIZATION', b'x-amzn-mantle-client-agent', 'strip',
     'the organization an API-key login bills'),
    ('sqlite_home', b'Environment value for `$', b'CODEX_SQLITE_HOME', b'` is overridden', 'strip',
     'where Codex keeps its thread state, a redirect of the profile beside CODEX_HOME'),
]

# Codex's error table: the text of every error its protocol Display prints (what `codex exec --json`
# puts in an `error` event and a failed turn), read from three places in the binary: the fixed messages,
# the format templates (length-prefixed pieces, 0xc0 marking an argument, 0x00 ending a template) and the
# workspace messages. Each message is classified: an exhaustion is a window the account's CLI reported
# exhausted (its id, and whether the message states its reset), anything else is not an allowance
# statement. A message this list does not classify fails the extraction by name.
CODEX_ERROR_FIXED = (b'LandlockRulesetLandlockPathFdTokioJoinEnvVar', b'request_id', (
    'turn aborted. Something went wrong? Hit `/feedback` to report the issue.',
    'shared rollout token budget exhausted',
    "Codex ran out of room in the model's context window. Start a new thread or clear earlier history before retrying.",
    'agent thread limit reached',
    'session configured event was not the first event in the stream',
    'timeout waiting for child process to exit',
    'request timed out',
    'spawn failed: child stdout/stderr not captured',
    'interrupted (Ctrl-C). Something went wrong? Hit `/feedback` to report the issue.',
    'Image poisoning',
    'Selected model is at capacity. Please try a different model.',
    'Quota exceeded. Check your plan and billing details.',
    'To use Codex with your ChatGPT plan, upgrade to Plus: https://chatgpt.com/explore/plus.',
    "We're currently experiencing high demand, which may cause temporary errors.",
    'internal error; agent loop died unexpectedly',
    'codex-linux-sandbox was required but not provided'))
CODEX_ERROR_TEMPLATES = (b'protocol/src/models.rs', b'\x00&sandbox denied exec error', b'\x00\x19invalid --profile value')
CODEX_ERROR_WORKSPACE = (b'<empty>', b"\x80\x96\x00You've hit your usage limit. Upgrade to Pro", (
    'Your workspace is out of credits. Add credits to continue.',
    'Your workspace is out of credits. Ask your workspace owner to refill in order to continue.',
    'You hit your spend cap set in your workspace. Increase your spend cap to continue.',
    'You hit your spend cap set by the owner of your workspace. Ask an owner to increase your spend cap to continue.'))
CODEX_ERROR_PRO = b"\x80\x96\x00You've hit your usage limit. Upgrade to Pro"
CODEX_EXHAUSTION = {
    'Your workspace is out of credits. Add credits to continue.': 'workspace_credits',
    'Your workspace is out of credits. Ask your workspace owner to refill in order to continue.': 'workspace_credits',
    'You hit your spend cap set in your workspace. Increase your spend cap to continue.': 'workspace_spend_cap',
    'You hit your spend cap set by the owner of your workspace. Ask an owner to increase your spend cap to continue.':
        'workspace_spend_cap',
    'Quota exceeded. Check your plan and billing details.': 'quota',
    'To use Codex with your ChatGPT plan, upgrade to Plus: https://chatgpt.com/explore/plus.': 'plan',
}
# The messages that name a limit, a credit, a quota or a plan and are still not an allowance statement.
CODEX_NOT_EXHAUSTION = {
    'shared rollout token budget exhausted': "Codex's own budget for one rollout, a local setting, not the account's",
    'agent thread limit reached': "Codex's own cap on concurrent agent threads",
    'exceeded retry limit, last status: {}{}': 'a request that failed its retries; it states no allowance',
    'Selected model is at capacity. Please try a different model.': 'the service is busy; transient',
}
ALLOWANCE_WORDS = re.compile(r'limit|credit|quota|spend|plan|billing|budget|capacity', re.I)


def _templates(block):
    """The format templates of a packed Display block: each a list of text pieces, None for an argument."""
    found, current, at = [], [], 0
    while at < len(block):
        byte = block[at]
        if byte == 0x00:
            found.append(current)
            current, at = [], at + 1
        elif byte == 0xc0:
            current.append(None)
            at += 1
        elif byte == 0x80:
            length = int.from_bytes(block[at + 1:at + 3], 'little')
            current.append(block[at + 3:at + 3 + length].decode())
            at += 3 + length
        elif byte < 0x80:
            current.append(block[at + 1:at + 1 + byte].decode())
            at += 1 + byte
        else:
            raise Moved('codex error templates: an unread byte %#x' % byte)
    if current:
        found.append(current)
    return [''.join('{}' if piece is None else piece for piece in template) for template in found if template]


def _classify(message):
    if message.startswith("You've hit your usage limit"):
        return {'window': 'usage_limit', 'reset': 'stated or none (its retry phrase)'}
    if message in CODEX_EXHAUSTION:
        return {'window': CODEX_EXHAUSTION[message], 'reset': 'none: blocked until observed otherwise'}
    if message in CODEX_NOT_EXHAUSTION:
        return {'window': None, 'reason': CODEX_NOT_EXHAUSTION[message]}
    if ALLOWANCE_WORDS.search(message):
        raise Moved('codex error table: an unclassified message names an allowance: %r' % message)
    return {'window': None, 'reason': 'a local, request or transient error; it states no allowance'}


def codex_errors(raw):
    entries = []
    before, after, messages = CODEX_ERROR_FIXED
    run = before + ''.join(messages).encode() + after
    if raw.count(run) != 1:
        raise Moved('codex error table: the fixed messages moved')
    entries += [('fixed', m, raw.index(run) + len(before)) for m in messages]
    anchor, start, end = CODEX_ERROR_TEMPLATES
    at = raw.find(anchor)
    first = raw.find(start, at)
    last = raw.find(end, first)
    if at < 0 or first < 0 or last < 0 or last - first > 4096:
        raise Moved('codex error table: the templates moved')
    entries += [('template', m, first) for m in _templates(raw[first + 1:last + 1])]
    before, after, messages = CODEX_ERROR_WORKSPACE
    run = before + ''.join(messages).encode() + after
    if raw.count(run) != 1:
        raise Moved('codex error table: the workspace messages moved')
    entries += [('workspace', m, raw.index(run) + len(before)) for m in messages]
    pro = raw.find(CODEX_ERROR_PRO)
    entries += [('template', m, pro) for m in _templates(raw[pro:raw.index(b'\xc0\x00', pro) + 2])]
    table = []
    for source, message, offset in entries:
        table.append(dict({'message': message, 'source': source, 'offset': offset}, **_classify(message)))
    if not any(e['window'] == 'usage_limit' for e in table) or len({e['message'] for e in table}) != len(table):
        raise Moved('codex error table: incomplete or repeated')
    return table


# What the binary says about where exec's turn usage comes from: the thread token usage it reports is a
# thread total and a last-turn figure; the strings do not say which one turn.completed copies.
CODEX_USAGE_SOURCE = (b'exec/src/event_processor_with_jsonl_output.rs', b'thread/tokenUsage/updated',
                      b'totalmodelContextWindowstruct ThreadTokenUsage with 3 elements',
                      b'struct TokenUsageInfo with 3 elements', b'last_token_usage')


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
    for piece in CODEX_USAGE_SOURCE:
        if piece not in raw:
            raise Moved('codex usage source moved: %r' % piece)
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
            'events': events, 'usage_limit': limit, 'errors': codex_errors(raw), 'credential_tables': tables,
            'notes': {'turn.completed.usage': (
                "exec's turn usage is read from the thread token usage its event processor receives "
                "(thread/tokenUsage/updated, a ThreadTokenUsage of total, last and modelContextWindow; the core's "
                "TokenUsageInfo of total_token_usage, last_token_usage and model_context_window): a thread total "
                "and a last-turn figure. The strings do not say which one turn.completed copies, so a resumed "
                "thread is never subtracted: the sum of the invocation's own completed turns never counts less "
                "than the CLI recorded under either reading")}}


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
