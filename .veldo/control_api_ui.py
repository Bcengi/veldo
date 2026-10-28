#!/usr/bin/env python3
"""The factory UI's page and its built assets, served by the authenticated API from its own origin (VELDO-0145).

WHAT THIS MODULE IS. The owner's UI (engine/ui, Vue) is a single page built to static files. The API's
loopback listener (control_api.listen) hands every GET or HEAD whose path is outside /api/ to `serve`
here, so the page, its scripts, styles, fonts and workers come from the same origin as the API and fall
under the same content security policy (VELDO-0171), which allows nothing inline. Nothing here reads
the authority, a session or a store: the files carry no factory data, and every screen reads its data
through the API's own routes, which refuse a request without a passkey session.

WHAT IS SERVED. A file of the UI directory (`directory`) by its path, when the path is plain (no dot
segment, no backslash, no NUL, no percent escape of a separator) and the file resolves inside the
directory; its type comes from a fixed table of the extensions a Vite build emits (anything else is
refused). A path with no extension is a screen of the page, answered with index.html, so a reload on
/runs/... works. Built files under /assets/ carry a content hash in their name and are cached as
immutable; index.html is never cached. Every answer carries the API's Host check, HSTS and nosniff;
the listener adds the policy itself.

REFUSALS, named as the API names them: another Host (invalid_input:host), a path that is not plain
(invalid_input:path), no such file or a type outside the table (missing_evidence:asset) and no built UI
on this host (missing_evidence:ui_not_built).

THE DEPENDENCY POLICY (`dependency_problems`, VELDO-0131 AC4 as VELDO-0145 applies it). The UI's
package-lock.json is judged against its dependency-policy.json: every installed package carries a license
on the allowed list and matches no denied name (a Chinese-origin UI library, or a library with free and paid
tiers, from the major version the rule names) unless an owner decision names it; every direct dependency is
listed with its exact version, license, origin, tier and reason, and package.json pins it exactly.

WHAT IT IS NOT. Not a general file server, not a cache, not a writer. Standard library only.
"""
import fnmatch
import json
from pathlib import Path
import urllib.parse

HSTS = 'max-age=31536000'
INDEX = 'index.html'
# The extensions a Vite build of the UI emits, and their types. Anything else is refused.
TYPES = {
    '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
    '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
    '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon', '.woff2': 'font/woff2',
    '.woff': 'font/woff', '.ttf': 'font/ttf', '.json': 'application/json', '.webmanifest': 'application/manifest+json',
    '.txt': 'text/plain; charset=utf-8',
}
IMMUTABLE = 'public, max-age=31536000, immutable'


def directory(config=None, here=None):
    """The UI directory: the API configuration's `ui` when it names one, else the build beside this module
    (engine/ui/dist from engine/.veldo, or a `ui` directory laid beside the installed module)."""
    named = (config or {}).get('ui') if isinstance(config, dict) else None
    if isinstance(named, str) and named:
        return Path(named)
    base = Path(here or __file__).resolve().parent
    for candidate in (base / 'ui', base.parent / 'ui' / 'dist'):
        if (candidate / INDEX).is_file():
            return candidate
    return base.parent / 'ui' / 'dist'


def is_page_path(path):
    """Whether a request path is the UI's (everything outside the API's /api/ prefix)."""
    plain = str(path).split('?', 1)[0]
    return plain != '/api' and not plain.startswith('/api/')


def _refusal(status, code, host_ok=True):
    body = json.dumps({'refusal': code, 'error': code.split(':', 1)[0]}, sort_keys=True).encode()
    return status, [('Content-Type', 'application/json'), ('Cache-Control', 'no-store'),
                    ('Strict-Transport-Security', HSTS), ('X-Content-Type-Options', 'nosniff')], body


def _plain(path):
    """The path's segments when it is plain, else None."""
    raw = str(path).split('?', 1)[0].split('#', 1)[0]
    lowered = raw.lower()
    if '\\' in raw or '\x00' in raw or '%2f' in lowered or '%5c' in lowered or '%00' in lowered or '%2e' in lowered:
        return None
    text = urllib.parse.unquote(raw)
    if not text.startswith('/'):
        return None
    parts = [p for p in text.split('/') if p]
    if any(p in ('.', '..') or p.startswith('.') for p in parts):
        return None
    return parts


def serve(ui_dir, method, path, headers, host):
    """(status, headers, body bytes) for one page request. `host` is the name the Host header must carry."""
    if (headers.get('Host') or '') != host:
        return _refusal(400, 'invalid_input:host')
    parts = _plain(path)
    if parts is None:
        return _refusal(400, 'invalid_input:path')
    root = Path(ui_dir)
    try:
        root = root.resolve(strict=True)
    except OSError:
        return _refusal(404, 'missing_evidence:ui_not_built')
    if not (root / INDEX).is_file():
        return _refusal(404, 'missing_evidence:ui_not_built')
    name = parts[-1] if parts else ''
    suffix = Path(name).suffix.lower() if name else ''
    if not suffix:
        target = root / INDEX
    else:
        target = root.joinpath(*parts)
    try:
        resolved = target.resolve(strict=True)
    except OSError:
        return _refusal(404, 'missing_evidence:asset')
    if root not in resolved.parents or not resolved.is_file():
        return _refusal(404, 'missing_evidence:asset')
    kind = TYPES.get(resolved.suffix.lower())
    if kind is None:
        return _refusal(404, 'missing_evidence:asset')
    body = resolved.read_bytes()
    length = len(body)
    cache = IMMUTABLE if parts[:1] == ['assets'] and suffix else 'no-store'
    out = [('Content-Type', kind), ('Cache-Control', cache), ('Strict-Transport-Security', HSTS),
           ('X-Content-Type-Options', 'nosniff'), ('Referrer-Policy', 'no-referrer'),
           ('Cross-Origin-Opener-Policy', 'same-origin'), ('Content-Length', str(length))]
    return 200, out, b'' if method == 'HEAD' else body


def _major(version):
    head = str(version or '').split('.', 1)[0]
    return int(head) if head.isdigit() else None


def dependency_problems(lock, policy, package):
    """Why the UI's installed packages (package-lock.json `lock`) and its manifest (package.json `package`) are
    not what the dependency policy admits, by name; [] when they are."""
    problems = []
    allowed = set((policy.get('licenses') or {}).get('allowed') or ())
    decided = {d.get('name') for d in policy.get('owner_decisions') or () if isinstance(d, dict)}
    deny = [d for d in policy.get('deny') or () if isinstance(d, dict) and isinstance(d.get('name'), str)]
    packages = (lock or {}).get('packages') if isinstance(lock, dict) else None
    if not isinstance(packages, dict) or not packages:
        return ['the lockfile lists no packages']
    for path, meta in sorted(packages.items()):
        if not path:
            continue
        name = path.rsplit('node_modules/', 1)[-1]
        meta = meta if isinstance(meta, dict) else {}
        version, license_ = meta.get('version'), meta.get('license')
        if license_ not in allowed:
            problems.append('%s@%s: license %s is not allowed' % (name, version, license_))
        for rule in deny:
            if not fnmatch.fnmatchcase(name, rule['name']):
                continue
            floor = rule.get('from_major')
            major = _major(version)
            if floor is not None and (major is None or major < floor):
                continue
            if name in decided and floor is None:
                continue
            problems.append('%s@%s: denied (%s)' % (name, version, rule.get('reason')))
    direct = policy.get('direct') or {}
    wanted = dict((package or {}).get('dependencies') or {}, **((package or {}).get('devDependencies') or {}))
    for name, spec in sorted(wanted.items()):
        entry = direct.get(name)
        if not isinstance(entry, dict):
            problems.append('%s: a direct dependency the policy does not list' % name)
            continue
        if not isinstance(spec, str) or not spec[:1].isdigit() or any(c in spec for c in '^~*<>| '):
            problems.append('%s: package.json does not pin an exact version (%s)' % (name, spec))
        installed = (packages.get('node_modules/' + name) or {}).get('version')
        if entry.get('version') != spec or installed != spec:
            problems.append('%s: policy %s, package.json %s, installed %s' % (name, entry.get('version'), spec, installed))
        for field in ('license', 'origin', 'tier', 'why'):
            if not entry.get(field):
                problems.append('%s: the policy records no %s' % (name, field))
        if entry.get('license') != (packages.get('node_modules/' + name) or {}).get('license'):
            problems.append('%s: the policy records license %s, the package declares %s' % (
                name, entry.get('license'), (packages.get('node_modules/' + name) or {}).get('license')))
    for name in sorted(set(direct) - set(wanted)):
        problems.append('%s: listed in the policy but not a direct dependency' % name)
    return problems
