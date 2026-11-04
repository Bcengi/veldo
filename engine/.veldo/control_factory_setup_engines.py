"""Factory setup's qualified host engines. Reads bytes, never executes an engine."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile


def organ(name, directory=None):
    path = Path(directory or Path(__file__).parent) / (name + '.py')
    spec = importlib.util.spec_from_file_location('setup_engines_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def qualified_claude(Refused, directory=None):
    """VELDO-0230 AC4: the Claude Code copy the engines record beside the modules names (runtime/engines.json,
    written by qualify.py), never whatever `claude` on PATH resolves to."""
    record = Path(directory or Path(__file__).parent) / 'runtime' / 'engines.json'
    try:
        named = json.loads(record.read_text())['claude_code']['binary']
    except (OSError, ValueError, KeyError, TypeError):
        raise Refused('missing_evidence:engine_source:claude_code') from None
    named = str(named)
    if named == '~' or named.startswith('~/'):
        import pwd
        named = pwd.getpwuid(os.getuid()).pw_dir + named[1:]
    path = Path(named)
    if not path.is_absolute() or not path.is_file():
        raise Refused('missing_evidence:engine_source:claude_code')
    return path


def qualified_antigravity(Refused, directory=None):
    """VELDO-0232: {version, source} of the Antigravity binary the engines record names (its pinned copy, or the
    source the qualify command read when no state root was named) when it is the installed qualification's, else
    {skipped: <reason>}: Antigravity is an optional engine on a host, so setup pins it and gives the service its
    adapter only when the qualified binary is there, and says why not otherwise. None when the engines record
    names no Antigravity."""
    record = Path(directory or Path(__file__).parent) / 'runtime' / 'engines.json'
    try:
        named = json.loads(record.read_text()).get('antigravity')
    except (OSError, ValueError, AttributeError):
        raise Refused('missing_evidence:engine_source:antigravity') from None
    if named is None:
        return None
    source = str(named.get('binary') or '')
    if source == '~' or source.startswith('~/'):
        import pwd
        source = pwd.getpwuid(os.getuid()).pw_dir + source[1:]
    A = organ('control_engine_antigravity', directory)
    try:
        qualified = A.load_qualification()
    except A.Refused as error:
        return {'skipped': error.code}
    if not os.path.isabs(source) or not os.path.isfile(source):
        return {'skipped': 'missing_evidence:engine_source:antigravity'}
    if named.get('version') != qualified['version']:
        return {'skipped': 'stale_subject:engine_version'}
    if A._file_digest(source) != qualified['sha256']:
        return {'skipped': 'stale_subject:engine_digest'}
    return {'version': qualified['version'], 'source': source}


def check(Refused):
    """Locate the qualified versioned Claude file (the engines record's) and the Codex package through PATH,
    before any write."""
    claude, codex = organ('control_engine_claude'), organ('control_engine_codex')
    paths = {'claude_code': qualified_claude(Refused)}
    found = shutil.which('codex')
    if found is None:
        raise Refused('missing_evidence:engine_source:codex')
    paths['codex'] = Path(found).resolve()
    version = paths['claude_code'].name
    if not claude.VERSION_TEXT.fullmatch(version):
        raise Refused('missing_evidence:engine_version:claude_code')
    try:
        record = claude.qualification()
        if version not in record['versions']:
            raise Refused('missing_evidence:engine_baseline:' + version)
        entry = claude.qualified(version, record)
        claude.qualified_baseline({'version': version}, record)
        claude.qualified_tools(version, entry)
        if claude._file_digest(paths['claude_code']) != entry['sha256']:
            raise Refused('binding_mismatch:engine_digest')
        record = codex.load_qualification()
        package, manifest = codex._package(paths['codex'])
        if package is None:
            raise Refused('invalid_input:engine_package')
        if manifest.get('version') != record['package_version']:
            raise Refused('missing_evidence:engine_baseline:' + str(manifest.get('version')))
        vendor = str(package / record['executable'])
        bound = codex.bind({'executable': vendor})
    except (claude.Refused, codex.Refused) as error:
        code = 'binding_mismatch:engine_digest' if error.code == 'stale_subject:engine_digest' else error.code
        raise Refused(code) from None
    found = {'claude_code': {'version': version, 'versions': str(paths['claude_code'].parent)},
             'codex': {'executable': vendor, 'sha256': bound['sha256']}}
    antigravity = qualified_antigravity(Refused)
    if antigravity is not None:
        found['antigravity'] = antigravity
    return found


def pin_antigravity(state_root, directory, plan, Refused):
    """VELDO-0232: the Antigravity copy pinned under the state root, bound; None when the plan names none."""
    if not (plan.get('antigravity') or {}).get('version'):
        return None
    A = organ('control_engine_antigravity', directory)
    try:
        return A.pin(plan['antigravity']['version'], source=plan['antigravity']['source'], state_root=str(state_root))
    except A.Refused as error:
        raise Refused('binding_mismatch:engine_digest' if error.code == 'stale_subject:engine_digest'
                      else error.code) from None


def install(state_root, directory, plan, Refused):
    """Pin and bind against the records actually installed beside the receiver."""
    claude, codex = organ('control_engine_claude', directory), organ('control_engine_codex', directory)
    try:
        pinned = claude.pin(plan['claude_code']['version'], versions=plan['claude_code']['versions'],
                            state_root=state_root)
        vendor = codex.bind({'executable': plan['codex']['executable']})
    except (claude.Refused, codex.Refused) as error:
        code = 'binding_mismatch:engine_digest' if error.code == 'stale_subject:engine_digest' else error.code
        raise Refused(code) from None
    bound = [pinned, vendor, pin_antigravity(state_root, directory, plan, Refused)]
    return {b['engine']: {key: b[key] for key in ('version', 'path', 'sha256')} for b in bound if b}


def count_pins(state_root, engines):
    """Count distinct regular pinned copies made under this factory's engine directory."""
    directory = Path(state_root).resolve() / 'engines'
    paths = {Path(bound['path']) for bound in engines.values()}
    return sum(path.is_file() and not path.is_symlink() and directory in path.parents for path in paths)


def ensure(state_root, directory, plan, Refused, observe):
    """Complete the fresh pin layout, repairing unreadable records and refusing different ones."""
    claude, codex = organ('control_engine_claude', directory), organ('control_engine_codex', directory)
    version = plan['claude_code']['version']
    target = claude.pinned_path(state_root, version)
    record_path = Path(state_root) / 'host' / 'engines.json'
    try:
        vendor = codex.bind({'executable': plan['codex']['executable']})
        engines = {'claude_code': {'version': version, 'path': str(target),
                                  'sha256': claude.qualified(version)['sha256']},
                   'codex': {key: vendor[key] for key in ('version', 'path', 'sha256')}}
        bound = pin_antigravity(state_root, directory, plan, Refused)
        if bound is not None:
            engines['antigravity'] = {key: bound[key] for key in ('version', 'path', 'sha256')}
        try:
            recorded = json.loads(record_path.read_text())
        except (OSError, ValueError):
            recorded = None
        else:
            # VELDO-0232: a state root set up before Antigravity was qualified gains its entry; anything else differing
            # is refused by name.
            earlier = {k: v for k, v in engines.items() if k != 'antigravity'}
            if 'antigravity' in engines and isinstance(recorded, dict) and 'antigravity' not in recorded \
                    and recorded == earlier:
                recorded = None
            elif recorded != engines:
                raise Refused('invalid_input:state_root:differs:' + str(record_path))
        report = {'pins_made': 0, 'engines_record': None, 'engines': engines}
        if os.path.lexists(target) and recorded is not None:
            return report
        if not os.path.lexists(target):
            claude.pin(version, versions=plan['claude_code']['versions'], state_root=state_root)
            report['pins_made'] = 1
            observe({'point': 'engine_pin', 'path': str(target)})
        if recorded is None:
            claude.bind({'executable': {'version': version}}, state_root)
            fd, partial = tempfile.mkstemp(prefix='.engines.', suffix='.partial', dir=record_path.parent)
            try:
                with os.fdopen(fd, 'w') as handle:
                    handle.write(json.dumps(engines, sort_keys=True) + '\n')
                os.replace(partial, record_path)
            finally:
                if os.path.exists(partial):
                    os.unlink(partial)
            report['engines_record'] = str(record_path)
            observe({'point': 'engines_record', 'path': str(record_path)})
        return report
    except (claude.Refused, codex.Refused) as error:
        code = 'binding_mismatch:engine_digest' if error.code == 'stale_subject:engine_digest' else error.code
        raise Refused(code) from None
