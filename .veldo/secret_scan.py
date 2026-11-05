#!/usr/bin/env python3
"""The absolute secret scan (WARP-1302, W2 of PLAN-0013).

Pattern plus entropy over every diff, every generated file and every recorded artifact. It fails
closed and **there is no allowlist mechanism at all**.

WHY NO ALLOWLIST, WHICH IS THE ONLY INTERESTING DECISION HERE. Every secret scanner in the world
ships with an exemption list, and every one of those lists rots into a tunnel: the first entry is a
test fixture, the tenth is a real credential somebody was in a hurry about, and nobody re-reads it.
The exemption exists because in a normal codebase there are legitimate reasons to hold a literal
credential-shaped string.

**W1 removed those reasons.** A secret is a reference; a literal has no legitimate place in any
file. So the exemption has nothing to be for, and the correct number of exemption mechanisms is
zero. That is only defensible BECAUSE of W1, and the refusal text says so, because a future reader
hitting a false positive needs to know why the door they are looking for was deliberately not built.

**A FALSE POSITIVE IS RESHAPED, NEVER EXEMPTED.** A hash in a fixture or a sample token in
documentation is fixed by making the artifact not look like a credential - shorten it, obviously
fake it, move it behind a reference. That costs minutes at machine prices. The alternative costs a
credential in git history, where deleting it does not remove it.

TWO DETECTORS, because each catches what the other misses. PATTERNS catch known shapes - a provider
prefix, a private key header - including high-entropy-looking strings that are not random. ENTROPY
catches the unknown provider whose format nobody has written a pattern for yet. Neither alone is
enough and the combination is deliberately noisy in the safe direction.
"""
import ast
import math
import re

SCHEMA = "veldo.secret_scan/v1"

# KNOWN SHAPES. Each is a provider format or a structural marker, not a guess.
PATTERNS = (
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "an inline private key"),
    (re.compile(r"\b(sk|rk)_(live|test)_[A-Za-z0-9]{16,}"), "a Stripe-style secret key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "a GitHub token"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "a Slack token"),
    (re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b"), "an AWS access key id"),
    (re.compile(r"\bAIza[A-Za-z0-9_\-]{35}\b"), "a Google API key"),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\."), "a JWT"),
    (re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*"
                r"['\"][^'\"\s]{8,}['\"]"), "a credential assigned as a literal"),
)

# ENTROPY. A long, high-entropy, unbroken token is the shape of a key nobody has a pattern for.
ENTROPY_MIN_LEN = 32
ENTROPY_THRESHOLD = 4.0
_CANDIDATE = re.compile(r"[A-Za-z0-9+/=_\-]{%d,}" % ENTROPY_MIN_LEN)

# The ONE mechanism that is not an allowlist: a token that is structurally incapable of being a
# secret because it is a hex digest of a known width. Git object ids and sha256 digests are
# everywhere in this repository's own proofs, they are derived from public content, and they are
# not credentials. This is a SHAPE rule, not a list of blessed strings, which is the difference
# that stops it rotting.
_PURE_HEX = re.compile(r"\A[a-f0-9]+\Z", re.I)
DIGEST_WIDTHS = frozenset({7, 8, 10, 12, 32, 40, 64, 128})


def shannon(s):
    if not s:
        return 0.0
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _is_digest(tok):
    return bool(_PURE_HEX.match(tok)) and len(tok) in DIGEST_WIDTHS


def scan_text(text, where="<text>"):
    """Every finding in one blob, as (line, kind, why). Empty means clean.

    Line numbers are 1-based and real, because a finding an operator cannot locate is a finding
    they will disable."""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for rx, why in PATTERNS:
            if rx.search(line):
                out.append((i, "pattern", why))
                break
        else:
            for tok in _CANDIDATE.findall(line):
                if _is_digest(tok):
                    continue
                if shannon(tok) >= ENTROPY_THRESHOLD:
                    out.append((i, "entropy",
                                "a %d-character high-entropy token (%.2f bits/char), which is the "
                                "shape of a key no pattern covers yet" % (len(tok), shannon(tok))))
                    break
    return out


def refusal(where, findings):
    """The refusal text. It states that there is no allowlist AND why, because a reader hitting a
    false positive will go looking for the exemption mechanism and needs to find the reason it
    does not exist rather than concluding the tool is broken."""
    head = "%s: %d possible secret(s) found" % (where, len(findings))
    body = ["  line %d: %s (%s)" % (ln, why, kind) for ln, kind, why in findings[:8]]
    tail = [
        "  THERE IS NO ALLOWLIST, DELIBERATELY. Secrets are references (see .veldo/secretref.py),",
        "  so a literal credential has no legitimate reason to exist in any file, so an exemption",
        "  mechanism would have nothing to be for except the case this check exists to catch.",
        "  FIX A FALSE POSITIVE BY RESHAPING THE ARTIFACT, never by exempting it: shorten the",
        "  sample, make it obviously fake, or move it behind a reference. Minutes of work, against",
        "  a credential in git history that deleting does not remove.",
    ]
    return [head] + body + tail


def scan_files(files, read=None):
    """Scan an iterable of paths. `read` is injectable so the gate can scan a diff, a generated
    artifact or a proof body without this module knowing where any of it came from."""
    reader = read or (lambda p: open(p, "r", encoding="utf-8", errors="replace").read())
    out = {}
    for p in files:
        try:
            found = scan_text(reader(p), str(p))
        except (OSError, UnicodeError):
            # UNREADABLE IS NOT CLEAN. A file the scanner cannot read is a file it cannot vouch
            # for, and passing it silently is how a binary blob becomes the hiding place.
            found = [(0, "unreadable", "could not be read, so it cannot be vouched for")]
        if found:
            out[str(p)] = found
    return out


# THE WORKSPACE AND PROJECT-TREE SCAN (VELDO-0254 AC2). An outside-service credential lives only behind the
# outside gate; this scan finds one left in a run's workspace, a landing candidate's changed files or a project
# tree, and REPORTS it, masked, so the owner moves it behind the gate. It never edits a file, stops a run or
# refuses a landing. One entry, `scan`, serves every trigger, and nothing else reports a found credential.
# Detection: the product's generic credential formats (FORMATS, kept in this module so every installed copy of it
# carries them) and an exact match against the credentials held for the gate, compared by digest inside this process
# and never written out. A finding is
# written as its MASKED form only: the kind, the length and a short digest of the value, never a character of
# it. The engine's own model login in its usual place (LOGIN_PLACES) is where it belongs and is not a finding.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

# The workspace triggers of AC2, and `launch`, the launcher's scan of a run's final environment and command line
# before the run starts (AC1): a credential found there refuses that launch, by the launcher, never by this scan.
TRIGGERS = ('run_end', 'landing_candidate', 'setup', 'command', 'launch')
# THE PRODUCT'S GENERIC LIST OF CREDENTIAL FORMATS: a kind and the regular expression of its format; the first entry
# that matches a span names it. Formats only: no value, account or service of any installation belongs here. They
# live in this module, not in a data file beside it, because the installed service copies modules only
# (control_service.closure) and a scan without its formats would find nothing on every installed receiver.
FORMATS = (
    ('private_key', r'-{5}BEGIN (?:[A-Z]+ )*PRIVATE KEY-{5}'),
    ('aws_access_key', r'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b'),
    ('github_token', r'\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{22,255})\b'),
    ('gitlab_token', r'\bglpat-[A-Za-z0-9_\-]{20,}'),
    ('slack_token', r'\bxox[abposr]-[A-Za-z0-9\-]{10,}'),
    ('stripe_key', r'\b[rs]k_live_[A-Za-z0-9]{20,}'),
    ('google_api_key', r'\bAIza[0-9A-Za-z_\-]{35}\b'),
    ('anthropic_key', r'\bsk-ant-[A-Za-z0-9_\-]{20,}'),
    ('openai_key', r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{32,}'),
    ('npm_token', r'\bnpm_[A-Za-z0-9]{36}\b'),
    ('telegram_bot_token', r'\b[0-9]{8,10}:AA[A-Za-z0-9_\-]{33}\b'),
    ('jwt', r'\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}'),
    ('url_password', r'\b[a-z][a-z0-9+.\-]*://[^\s:/@]+:[^\s:/@]{8,}@'),
)
LOG_NAME = 'secret-scan.jsonl'
HELD_KIND = 'gate_credential'
LOGIN_PLACES = ('.claude/.credentials.json', '.codex/auth.json')
SKIPPED_DIRECTORIES = ('.git',)
LARGEST = 16 * 1024 * 1024
DIGEST_CHARS = 12
_DELIMITED = re.compile(r'[^\s"\'`,;()\[\]{}<>|\\]+')


def formats():
    """[(kind, compiled pattern)] in the order FORMATS gives them."""
    return [(kind, re.compile(pattern)) for kind, pattern in FORMATS]


def store_logs(store):
    """The scan logs of one installation, as the running service's channel reads them: beside its store (a receiver
    configuration that names no state root) and in the state root that holds the store's directory."""
    directory = os.path.dirname(os.path.abspath(str(store)))
    return [os.path.join(directory, LOG_NAME), os.path.join(os.path.dirname(directory), LOG_NAME)]


def _digest(value):
    return hashlib.sha256(value.encode('utf-8', 'surrogatepass')).hexdigest()


def mask(kind, value):
    """The only form a found value ever leaves this process in: kind, length, short digest."""
    return {'kind': kind, 'length': len(value), 'digest': _digest(value)[:DIGEST_CHARS]}


def login_place(relative, login=()):
    """Whether `relative` is the engine's own model login in its usual place (or a login path the caller names)."""
    return any(relative == place or relative.endswith('/' + place) for place in tuple(LOGIN_PLACES) + tuple(login))


def tree_files(root):
    """(relative path, bytes) of every regular file under `root`, links and Git metadata not followed; a file
    larger than LARGEST is yielded as None (counted, not read)."""
    root = str(root)
    for directory, names, files in os.walk(root, followlinks=False):
        names[:] = sorted(n for n in names if n not in SKIPPED_DIRECTORIES)
        for name in sorted(files):
            path = os.path.join(directory, name)
            relative = os.path.relpath(path, root).split(os.sep)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            try:
                if os.path.getsize(path) > LARGEST:
                    yield '/'.join(relative), None
                    continue
                with open(path, 'rb') as handle:
                    yield '/'.join(relative), handle.read()
            except OSError:
                yield '/'.join(relative), None


def tree_state(root):
    """{relative path: (size, mtime_ns, inode)} of every regular file under `root`, as tree_files walks it; nothing
    is read. What a run's workspace holds as it starts, so its end reads only what it changed."""
    state, root = {}, str(root)
    for directory, names, files in os.walk(root, followlinks=False):
        names[:] = sorted(n for n in names if n not in SKIPPED_DIRECTORIES)
        for name in files:
            path = os.path.join(directory, name)
            try:
                info = os.lstat(path)
            except OSError:
                continue
            if os.path.isfile(path) and not os.path.islink(path):
                state['/'.join(os.path.relpath(path, root).split(os.sep))] = (info.st_size, info.st_mtime_ns,
                                                                              info.st_ino)
    return state


def changed_files(root, before):
    """(relative path, bytes) of each file under `root` that is new or changed against `before` (tree_state), so
    a credential that was already there is not read, nor reported, again."""
    now = tree_state(root)
    for relative in sorted(name for name, seen in now.items() if (before or {}).get(name) != seen):
        path = os.path.join(str(root), *relative.split('/'))
        try:
            if os.path.getsize(path) > LARGEST:
                yield relative, None
                continue
            with open(path, 'rb') as handle:
                yield relative, handle.read()
        except OSError:
            yield relative, None


def candidate_files(repository, base, head):
    """(relative path, bytes) of each file a landing candidate `head` adds or changes against `base`, read from
    the candidate's own objects, never its work tree."""
    git = ['git', '-c', 'core.quotepath=off', '-C', str(repository)]
    environment = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'GIT_CONFIG_NOSYSTEM': '1',
                   'GIT_CONFIG_GLOBAL': os.devnull, 'LANG': 'C'}
    listed = subprocess.run(git + ['diff', '--name-only', '-z', '--no-renames', '--diff-filter=AM', base, head,
                                   '--'], capture_output=True, timeout=120, check=True, env=environment,
                            stdin=subprocess.DEVNULL).stdout
    for name in [n for n in listed.decode('utf-8', 'surrogateescape').split('\0') if n]:
        blob = subprocess.run(git + ['cat-file', 'blob', '%s:%s' % (head, name)], capture_output=True, timeout=120,
                              env=environment, stdin=subprocess.DEVNULL)
        yield name, (blob.stdout if blob.returncode == 0 and len(blob.stdout) <= LARGEST else None)


def _covered(line, digests):
    """(start, end) of each delimited value on `line` whose digest is one of `digests`."""
    spans = []
    for match in _DELIMITED.finditer(line):
        token, start = match.group(0), match.start()
        candidates = [(token, start)]
        for separator in ('=', ':'):
            if separator in token:
                at = token.index(separator) + 1
                candidates.append((token[at:], start + at))
        for value, at in candidates:
            if value and _digest(value) in digests:
                spans.append((at, at + len(value)))
                break
    return spans


def _held_spans(line, held):
    """(start, end) of each delimited value on `line` whose digest is a held credential's."""
    return _covered(line, held)


def _occurrences(text, known, held, own=frozenset()):
    """[(line, kind, value)]: one per occurrence. A held credential is named as such; a span a held credential
    covers is not reported again by format, and overlapping formats report the first. A span that is one of `own`
    (the digests of the engine's own model login where the launcher hands it over) is where it belongs, not a
    finding."""
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        taken = list(_covered(line, own)) if own else []
        for start, end in _held_spans(line, held) if held else ():
            taken.append((start, end))
            found.append((number, HELD_KIND, line[start:end]))
        for kind, pattern in known:
            for match in pattern.finditer(line):
                start, end = match.span()
                if end > start and not any(start < e and s < end for s, e in taken):
                    taken.append((start, end))
                    found.append((number, kind, match.group(0)))
    return found


def notice_text(trigger, project, findings):
    """The owner's notice: each finding masked, and what to do with it."""
    lines = ['Veldo secret scan (%s, project %s): %d credential(s) found. Move each one behind the outside gate '
             'and take it out of the file.' % (trigger, project, len(findings))]
    if trigger == 'launch':
        lines[0] += ' The launch was refused.'
    lines += ['%s %s:%d (%s, %d characters, sha256 %s)' % (f['code'], f['file'], f['line'], f['masked']['kind'],
                                                          f['masked']['length'], f['masked']['digest'])
              for f in findings]
    return '\n'.join(lines)


def failure_text(trigger, project, error):
    """The owner's notice of a scan that failed: what was not checked and how to check it."""
    return ('Veldo secret scan (%s, project %s) failed: %s. Its files were not checked; check the project tree with '
            'secret_scan.py scan --project <name> --root <tree>.' % (trigger, project, error))


def error_name(error):
    """A failure's name for the log and the notice: its class, and the errno name of an OSError. Never its message,
    which could quote what it was reading."""
    name = type(error).__name__
    number = getattr(error, 'errno', None)
    return name + (':' + __import__('errno').errorcode.get(number, str(number)) if isinstance(error, OSError)
                   and number else '')


def failed(trigger, project, error, log, dispatch=None):
    """A scan that could not run, logged by name to the owner's scan log (and noted on stderr when even that log
    cannot be written), so a failure is never silent. It changes nothing about the run or the landing."""
    entry = {'event': 'secret_scan_failed', 'scan': uuid.uuid4().hex[:16], 'trigger': trigger, 'project': project,
             'dispatch': dispatch, 'error': error_name(error), 'at': time.time()}
    sys.stderr.write('secret scan (%s) failed: %s\n' % (trigger, entry['error']))
    try:
        _log(log, entry)
    except Exception as again:
        sys.stderr.write('secret scan failure could not be logged: %s\n' % type(again).__name__)
    return entry


def notices(log):
    """[(scan id, notice text)] of each scan in a scan log that found a credential or failed, in log order: what
    the owner is told through Veldo's own channel. Built from the logged masked findings only."""
    try:
        with open(str(log), encoding='utf-8') as handle:
            entries = [json.loads(line) for line in handle if line.strip()]
    except (OSError, ValueError):
        return []
    found, out = {}, []
    for entry in entries:
        if entry.get('event') == 'secret_found':
            found.setdefault(entry.get('scan'), []).append(entry)
        elif entry.get('event') == 'secret_scan' and entry.get('findings'):
            out.append((entry['scan'], 'secret_scan',
                        notice_text(entry.get('trigger'), entry.get('project'), found.get(entry['scan'], []))))
        elif entry.get('event') == 'secret_scan_failed':
            out.append((entry['scan'], 'secret_scan_failed',
                        failure_text(entry.get('trigger'), entry.get('project'), entry.get('error'))))
    return out


def _log(log, entry):
    if log is None:
        return
    if callable(log):
        log(entry)
        return
    os.makedirs(os.path.dirname(os.path.abspath(str(log))), exist_ok=True)
    with open(str(log), 'a', encoding='utf-8') as handle:
        handle.write(json.dumps(entry, sort_keys=True) + '\n')


def scan(trigger, project, files, *, held=(), login=(), log=None, notify=None, dispatch=None, known=None, own=()):
    """THE ONE SCAN ENTRY. `files` is an iterable of (relative path, bytes or None); `held` the credentials held
    for the gate (values, digested here and dropped); `log` a JSONL path or a callable taking each line; `notify`
    the owner channel's sink, called once with the notice text and returning its id. Returns the report: the
    scan id, trigger, project, dispatch, files read, files not read and the masked findings. Reports only."""
    if trigger not in TRIGGERS:
        raise ValueError('unknown trigger: %r' % (trigger,))
    held = {_digest(value) for value in held if isinstance(value, str) and value}
    own = frozenset(_digest(value) for value in own if isinstance(value, str) and value)
    known = formats() if known is None else known
    scan_id = uuid.uuid4().hex[:16]
    findings, read, unread = [], 0, 0
    for relative, data in files:
        if login_place(relative, login):
            continue
        if data is None:
            unread += 1
            continue
        read += 1
        text = data.decode('utf-8', 'replace') if isinstance(data, bytes) else str(data)
        for number, kind, value in _occurrences(text, known, held, own):
            findings.append({'code': 'secret_found:' + kind, 'kind': kind, 'file': relative, 'line': number,
                             'masked': mask(kind, value)})
    notice = None
    if findings and notify is not None:
        try:
            notice = notify(notice_text(trigger, project, findings))
        except Exception as error:  # a notice that fails is logged, never raised into the trigger
            notice = None
            _log(log, {'event': 'secret_notice_failed', 'scan': scan_id, 'error': type(error).__name__})
    now = time.time()
    for finding in findings:
        _log(log, dict(finding, event='secret_found', scan=scan_id, trigger=trigger, project=project,
                       dispatch=dispatch, notice=notice, at=now))
    _log(log, {'event': 'secret_scan', 'scan': scan_id, 'trigger': trigger, 'project': project, 'dispatch': dispatch,
               'files': read, 'unread': unread, 'findings': len(findings), 'notice': notice, 'at': now})
    return {'scan': scan_id, 'trigger': trigger, 'project': project, 'dispatch': dispatch, 'files': read,
            'unread': unread, 'findings': findings, 'notice': notice}


def metrics(log):
    """Scans by trigger, findings by kind and trigger, and the findings still open (those of the latest scan of
    each project and trigger), read from a scan log."""
    scans, kinds, latest = {}, {}, {}
    with open(str(log), encoding='utf-8') as handle:
        entries = [json.loads(line) for line in handle if line.strip()]
    for entry in entries:
        if entry.get('event') == 'secret_scan':
            scans[entry['trigger']] = scans.get(entry['trigger'], 0) + 1
            latest[(entry['project'], entry['trigger'])] = entry['findings']
        elif entry.get('event') == 'secret_found':
            key = '%s/%s' % (entry['kind'], entry['trigger'])
            kinds[key] = kinds.get(key, 0) + 1
    return {'scans_by_trigger': scans, 'findings_by_kind_and_trigger': kinds, 'open': sum(latest.values())}


# THE STATIC DELIVERY ROW (VELDO-0254 AC1). No outside-service credential is ever delivered into a run. Every
# place in the launch modules that builds a run's configuration, environment or command (a function that starts a
# process, or whose name says it builds one) is a SITE; a site whose calls reach a keystore resolution or a
# credential read (followed through the module's own functions and the engine modules it loads, stopping at
# another site, which is judged itself) is named credential_delivery_site:<module>:<function>. The engine's model
# login is not read through the keystore and stays where it is.
RUN_MODULES = ('control_launch*.py', 'control_engine_*.py', 'control_clone.py', 'control_conversation*.py',
               'control_workflow*.py', 'control_service_projects.py', 'control_agent_config*.py')
SITE_NAMES = re.compile(r'environment|argv|command|baseline|configur|spawn|launch|wrap|exec|contained')
SPAWNS = ('Popen', 'execve', 'execv', 'execvp', 'execvpe', 'posix_spawn', 'posix_spawnp', 'spawnve')
CREDENTIAL_MODULES = ('control_credential_keystore', 'secretref')
CREDENTIAL_CALLS = (('control_credential_delivery', 'resolve'),)
CREDENTIAL_NAMES = ('resolve_for_runtime', 'SecretService')


def _organ_name(node):
    """The module an organ-loading call names (`_organ('x')`, `organ('x')`), else None."""
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ('_organ', 'organ')
            and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
        return node.args[0].value
    return None


def _module_table(path):
    """({qualified name: node}, {alias: module}) of one module."""
    tree = ast.parse(Path(path).read_text())
    functions, aliases = {}, {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions[node.name + '.' + item.name] = item
        elif isinstance(node, ast.Assign) and _organ_name(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    aliases[target.id] = _organ_name(node.value)
    return functions, aliases


def delivery_sites(directory):
    """{'sites': [module:function], 'findings': [credential_delivery_site:module:function]} over `directory`."""
    import fnmatch
    directory = Path(directory)
    tables = {}
    for path in sorted(directory.glob('*.py')):
        try:
            tables[path.stem] = _module_table(path)
        except (SyntaxError, OSError, UnicodeError):
            continue
    run_modules = sorted(stem for stem in tables if any(fnmatch.fnmatch(stem + '.py', g) for g in RUN_MODULES))

    def edges(module, name):
        """(reads a credential directly, [(module, function) it calls])."""
        functions, aliases = tables[module]
        node, owner = functions[name], name.split('.')[0] if '.' in name else None
        reads, called = False, []
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Call):
                continue
            func = sub.func
            if isinstance(func, ast.Name):
                reads = reads or func.id in CREDENTIAL_NAMES
                if func.id in functions:
                    called.append((module, func.id))
            elif isinstance(func, ast.Attribute):
                reads = reads or func.attr in CREDENTIAL_NAMES
                target = (_organ_name(func.value) if isinstance(func.value, ast.Call)
                          else aliases.get(func.value.id) if isinstance(func.value, ast.Name) else None)
                if isinstance(func.value, ast.Name) and func.value.id == 'self' and owner:
                    if owner + '.' + func.attr in functions:
                        called.append((module, owner + '.' + func.attr))
                elif target is not None:
                    if target in CREDENTIAL_MODULES or (target, func.attr) in CREDENTIAL_CALLS:
                        reads = True
                    elif target in tables and func.attr in tables[target][0]:
                        called.append((target, func.attr))
        return reads, called

    def is_site(module, name):
        if module not in run_modules:
            return False
        node = tables[module][0][name]
        spawns = any(isinstance(s, ast.Call) and (
            (isinstance(s.func, ast.Attribute) and (s.func.attr in SPAWNS or (
                s.func.attr == 'run' and isinstance(s.func.value, ast.Name) and s.func.value.id == 'subprocess')))
            or (isinstance(s.func, ast.Name) and s.func.id in SPAWNS)) for s in ast.walk(node))
        return spawns or bool(SITE_NAMES.search(name.rsplit('.', 1)[-1].lower()))

    sites = [(m, n) for m in run_modules for n in sorted(tables[m][0]) if is_site(m, n)]
    findings = []
    for site in sites:
        seen, stack, reached = {site}, [site], False
        while stack and not reached:
            reads, called = edges(*stack.pop())
            reached = reads
            for nxt in called:
                if nxt not in seen and not (nxt != site and is_site(*nxt)):
                    seen.add(nxt)
                    stack.append(nxt)
        if reached:
            findings.append('credential_delivery_site:%s.py:%s' % site)
    return {'sites': ['%s.py:%s' % s for s in sites], 'findings': findings}


def main(argv=None):
    """The owner's command: `secret_scan.py scan --project <name> --root <tree> [--log <file>]` scans a project
    tree and prints each finding masked; `secret_scan.py metrics --log <file>`; `secret_scan.py sites <dir>`
    prints the static delivery row. Exit 0 whatever is found: the scan reports, it refuses nothing."""
    import argparse
    parser = argparse.ArgumentParser(prog='secret_scan.py')
    sub = parser.add_subparsers(dest='action', required=True)
    one = sub.add_parser('scan')
    one.add_argument('--project', required=True)
    one.add_argument('--root', required=True)
    one.add_argument('--log')
    sub.add_parser('metrics').add_argument('--log', required=True)
    sub.add_parser('sites').add_argument('directory', nargs='?', default=str(Path(__file__).parent))
    args = parser.parse_args(argv)
    if args.action == 'metrics':
        print(json.dumps(metrics(args.log), sort_keys=True))
        return 0
    if args.action == 'sites':
        found = delivery_sites(args.directory)
        print('\n'.join(found['findings'] or ['no credential_delivery_site']))
        return 0
    report = scan('command', args.project, tree_files(args.root), log=args.log)
    for f in report['findings']:
        print('%s %s %s:%d %s/%d/%s' % (f['code'], args.project, f['file'], f['line'], f['masked']['kind'],
                                        f['masked']['length'], f['masked']['digest']))
    print('secret scan %s: %d files read, %d not read, %d findings' % (report['scan'], report['files'],
                                                                      report['unread'], len(report['findings'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
