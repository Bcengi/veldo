#!/usr/bin/env python3
"""Refuse a candidate that adds personal setup to the product (VELDO-0259 AC2).

    python3 scripts/check_personal_setup.py [--root DIR] [--base REF]   # gate: the lines a candidate adds
    python3 scripts/check_personal_setup.py --sweep [--root DIR]        # a whole tree

THE CHECK NAMES NOTHING PERSONAL. What is personal for one deployment lives in that deployment's
installation folder, patterns/ (literal strings and expressions, each with a category), read through
.veldo/installation.py, the folder's only reader. This file carries only shapes that are personal for
anybody and name nobody:
  home_path      an absolute path under a user's home directory;
  login_uid      a login uid in a systemd or runtime path;
  fixture_email  an email outside the reserved example domains, in a fixture;
  secret         the secret shapes the existing secret scanner knows (.veldo/secret_scan.py), less the
                 lines the repository's secret inventory has dispositioned by digest.
With no installation the built-in shapes run alone and the check says so on its own line, so a
contributor is not blocked by patterns they do not have.

GATE MODE judges the lines the candidate adds against its base: the commits ahead of the trunk the
candidate declares (refs/remotes/origin/HEAD, the ref a clone sets and the lander points at the trunk it
gates against, unless --base names one), the uncommitted changes and every line of an untracked file.
The base is never guessed: a repository with commits and no declared trunk is refused as
personal_setup:no_base, never passed on its uncommitted lines alone. File names are read NUL-separated,
so a name Git would quote (non-ASCII, a double quote, a backslash) is judged like any other. SWEEP MODE judges every line of every file given (scripts/publish.py calls it over
the produced tree, so the gate and publication share one definition).

A finding prints as `personal_setup:<category> <file>:<line> <masked>`, the mask being the first two
characters then ***; the matched value is never printed. A closing line counts findings per category.
Exit 0 clean, 1 refused, 2 the installation or the arguments could not be read.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

# The product's .veldo, where the installation reader and the secret scanner live.
LIB = Path(__file__).resolve().parent.parent / '.veldo'

_NOT_NESTED = r'(?<![A-Za-z0-9_.\-/])'
HOME_PATH = re.compile(_NOT_NESTED + r'(?:/home/|/Users/)[A-Za-z0-9_][A-Za-z0-9_.\-]*'
                       r'|[A-Za-z]:\\Users\\[A-Za-z0-9_][A-Za-z0-9_.\-]*')
LOGIN_UID = re.compile(r'/run/user/[0-9]+|\buser-[0-9]+\.slice|\buser@[0-9]+\.service')
EMAIL = re.compile(r'(?<![A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]+@([A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,})\b')
# RFC 2606 and RFC 6761: the names reserved for examples and tests.
RESERVED_DOMAINS = ('example.com', 'example.org', 'example.net')
RESERVED_SUFFIXES = ('.example', '.test', '.invalid', '.localhost')
FIXTURE_DIRS = {'fixture', 'fixtures', 'testdata', 'test', 'tests', 'suites'}
BUILTIN = ('home_path', 'login_uid', 'fixture_email', 'secret')


def _load(name):
    spec = importlib.util.spec_from_file_location('veldo_cps_' + name, str(LIB / name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mask(value):
    return value[:2] + '***'


def is_fixture(rel):
    parts = rel.replace('\\', '/').split('/')
    return any(p in FIXTURE_DIRS for p in parts[:-1]) or parts[-1].startswith('test_') \
        or 'fixture' in parts[-1]


def _reserved(domain):
    domain = domain.lower()
    return domain in RESERVED_DOMAINS or domain == 'localhost' or domain.endswith(RESERVED_SUFFIXES) \
        or any(domain.endswith('.' + d) for d in RESERVED_DOMAINS)


def rules(installation):
    """[(category, matcher)], matcher(line) -> the matched text or None. Installation patterns first."""
    out = []
    for category, kind, text in installation.patterns() if installation is not None else ():
        if kind == 'literal':
            needle = text.lower()

            def literal(line, needle=needle, size=len(text)):
                at = line.lower().find(needle)
                return line[at:at + size] if at >= 0 else None
            out.append((category, literal))
        else:
            rx = re.compile(text)
            out.append((category, lambda line, rx=rx: (rx.search(line) or [None])[0]))
    return out


def _builtin(category, rel, line, scan):
    if category == 'home_path':
        hit = HOME_PATH.search(line)
        return hit.group(0) if hit else None
    if category == 'login_uid':
        hit = LOGIN_UID.search(line)
        return hit.group(0) if hit else None
    if category == 'fixture_email':
        if not is_fixture(rel):
            return None
        for hit in EMAIL.finditer(line):
            if not _reserved(hit.group(1)):
                return hit.group(0)
        return None
    for rx, _why in scan.PATTERNS:
        hit = rx.search(line)
        if hit:
            return hit.group(0)
    return None


def _dispositions(root):
    """The line digests the repository's secret inventory has dispositioned for the pattern detector."""
    try:
        data = json.loads((Path(root) / '.veldo' / 'secret_inventory.json').read_text())
        return {d['digest'] for d in data.get('dispositions', []) if d.get('detector') == 'pattern'}
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return set()


def _digest(line):
    return 'sha256:' + hashlib.sha256(line.encode('utf-8', 'replace')).hexdigest()[:12]


def scan_lines(items, installation_rules, dispositions=frozenset()):
    """items: [(file, line number, text)]. Returns [{file, line, category, masked}], one per finding."""
    scan = _load('secret_scan.py')
    findings = []
    for rel, number, text in items:
        for category, matcher in installation_rules:
            hit = matcher(text)
            if hit:
                findings.append({'file': rel, 'line': number, 'category': category, 'masked': mask(hit)})
        for category in BUILTIN:
            hit = _builtin(category, rel, text, scan)
            if hit and not (category == 'secret' and _digest(text) in dispositions):
                findings.append({'file': rel, 'line': number, 'category': category, 'masked': mask(hit)})
    return findings


def _git(root, *args):
    done = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, timeout=120)
    return done.stdout if done.returncode == 0 else None


def _read(path):
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    if b'\0' in data[:8192]:
        return None
    return data.decode('utf-8', 'replace')


def _diff_added(text):
    """Added lines of a -U0 unified diff of ONE file as [(line number, text)]."""
    out, number, body = [], 0, False
    for line in (text or '').splitlines():
        if line.startswith('@@'):
            hit = re.match(r'@@ -\S+ \+(\d+)', line)
            number, body = (int(hit.group(1)) if hit else 0), True
        elif body and line.startswith('+'):
            out.append((number, line[1:]))
            number += 1
    return out


class NoBase(Exception):
    code = 'personal_setup:no_base'


# The trunk a candidate declares: a clone sets it to the remote's default branch, and the lander points
# it at the trunk it syncs and gates against (lander.POLICY_HEAD_REF), whatever that trunk is named.
DECLARED_TRUNK = 'refs/remotes/origin/HEAD'


def base_ref(root, base=None):
    """The commit the candidate's lines are judged against: `base` when named, else the declared trunk.
    Raises NoBase when it does not resolve; a local main or master is never taken as a guess."""
    ref = base or DECLARED_TRUNK
    found = (_git(root, 'rev-parse', '--verify', '-q', ref + '^{commit}') or '').strip()
    if not found:
        raise NoBase('%s does not resolve to a commit' % ref)
    return found


def _changed(root, *revs):
    """The files changed between revs (or revs and the working tree), NUL-separated, so no name is quoted."""
    names = _git(root, 'diff', '--name-only', '-z', '--no-renames', '--diff-filter=d', *revs)
    if names is None:
        raise NoBase('git diff %s cannot be read' % ' '.join(revs))
    return [n for n in names.split('\0') if n]


def added_lines(root, base=None):
    """Every line the candidate adds: commits ahead of the base, uncommitted changes, untracked files."""
    root = Path(root)
    added = {}
    flags = ('-U0', '--no-color', '--no-ext-diff', '--no-renames', '--text')
    ranges = []
    if (_git(root, 'rev-parse', '--verify', '-q', 'HEAD') or '').strip():
        merge = (_git(root, 'merge-base', base_ref(root, base), 'HEAD') or '').strip()
        if not merge:
            raise NoBase('no merge base with %s' % (base or DECLARED_TRUNK))
        ranges = [(merge, 'HEAD'), ('HEAD',)]
    for revs in ranges:
        for rel in _changed(root, *revs):
            for number, text in _diff_added(_git(root, 'diff', *flags, *revs, '--', ':(literal)' + rel)):
                added[(rel, number, text)] = None
    for rel in (_git(root, 'ls-files', '-z', '--others', '--exclude-standard') or '').split('\0'):
        text = _read(root / rel) if rel else None
        for number, line in enumerate((text or '').splitlines(), 1):
            added[(rel, number, line)] = None
    # A line of the committed diff that the working tree has since changed is judged as it stands now.
    return list(added)


def sweep_items(root, files):
    root = Path(root)
    for rel in files:
        text = _read(root / rel)
        for number, line in enumerate((text or '').splitlines(), 1):
            yield rel, number, line


def installation(stream=None):
    return _load('installation.py').load(stream=stream)


def report(findings, out, installed):
    for f in findings:
        out.write('personal_setup:%s %s:%d %s\n' % (f['category'], f['file'], f['line'], f['masked']))
    counts = {}
    for f in findings:
        counts[f['category']] = counts.get(f['category'], 0) + 1
    if not installed:
        out.write('personal setup: no installation found; ran the built-in shapes only\n')
    out.write('personal setup: %d finding(s)%s\n' % (
        len(findings), ''.join(' %s=%d' % item for item in sorted(counts.items()))))


def _rules(out):
    inst = installation(stream=out)
    return inst, rules(inst if inst.found else None)


def sweep(root, files=None, out=None, dispositions_root=None):
    """Every line of `files` (default: every file under root) against the installation's patterns and the
    built-in shapes. Prints the findings and returns them."""
    out = sys.stdout if out is None else out
    root = Path(root)
    inst, active = _rules(out)
    if files is None:
        files = sorted(str(p.relative_to(root)) for p in root.rglob('*')
                       if p.is_file() and '.git' not in p.relative_to(root).parts)
    findings = scan_lines(sweep_items(root, files), active, _dispositions(dispositions_root or root))
    report(findings, out, inst.found)
    return findings


def gate(root, base=None, out=None):
    out = sys.stdout if out is None else out
    inst, active = _rules(out)
    findings = scan_lines(added_lines(root, base), active, _dispositions(root))
    report(findings, out, inst.found)
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(prog='check_personal_setup.py')
    parser.add_argument('--root', default='.')
    parser.add_argument('--base')
    parser.add_argument('--sweep', action='store_true')
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    out = sys.stdout
    try:
        if args.sweep:
            findings = sweep(args.root, out=out)
        else:
            findings = gate(args.root, args.base, out=out)
    except Exception as error:  # an unreadable installation is red, never a silent pass
        out.write('personal setup: REFUSED %s%s\n' % (getattr(error, 'code', type(error).__name__),
                  ': %s; name the base with --base' % error if isinstance(error, NoBase) else ''))
        return 2
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
