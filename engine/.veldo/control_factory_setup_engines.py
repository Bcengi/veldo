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


def approved_codex(codex, record, Refused, directory=None):
    """VELDO-0275 AC1: the approved Codex vendor binary, the one whose digest the qualification record holds: the
    one the `codex` on PATH runs when that is the approved one, else the installer's kept copy the engines record
    beside the modules names (runtime/engines.json, written by qualify.py). A newer version installed on PATH is
    never used because it is installed; with neither approved, setup is refused as engine_not_approved."""
    candidates = []
    found = shutil.which('codex')
    if found is not None:
        package, _ = codex._package(Path(found).resolve())
        if package is not None:
            candidates.append(package / record['executable'])
    try:
        named = str(json.loads((Path(directory or Path(__file__).parent) / 'runtime' / 'engines.json')
                               .read_text())['codex']['binary'])
    except (OSError, ValueError, KeyError, TypeError):
        named = None
    if named is not None:
        if named == '~' or named.startswith('~/'):
            import pwd
            named = pwd.getpwuid(os.getuid()).pw_dir + named[1:]
        candidates.append(Path(named))
    present = [path for path in candidates if path.is_absolute() and path.is_file()]
    if not present:
        raise Refused('missing_evidence:engine_source:codex')
    for path in present:
        if codex._file_digest(path) == record['sha256']:
            return path
    raise Refused('engine_not_approved')


def check(Refused):
    """Locate the approved versioned Claude file (the engines record's) and the approved Codex vendor binary
    (approved_codex), before any write. VELDO-0275 AC1: anything else is engine_not_approved."""
    claude, codex = organ('control_engine_claude'), organ('control_engine_codex')
    paths = {'claude_code': qualified_claude(Refused)}
    version = paths['claude_code'].name
    if not claude.VERSION_TEXT.fullmatch(version):
        raise Refused('missing_evidence:engine_version:claude_code')
    try:
        record = claude.qualification()
        if version not in record['versions']:
            raise Refused('engine_not_approved')
        entry = claude.qualified(version, record)
        claude.qualified_baseline({'version': version}, record)
        claude.qualified_tools(version, entry)
        if claude._file_digest(paths['claude_code']) != entry['sha256']:
            raise Refused('engine_not_approved')
        record = codex.load_qualification()
        vendor = str(approved_codex(codex, record, Refused))
        _, manifest = codex._package(vendor)
        if (manifest or {}).get('version') != record['package_version']:
            raise Refused('engine_not_approved')
        bound = codex.bind({'executable': vendor})
    except (claude.Refused, codex.Refused) as error:
        raise Refused(error.code) from None
    return {'claude_code': {'version': version, 'versions': str(paths['claude_code'].parent)},
            'codex': {'executable': vendor, 'sha256': bound['sha256']}}


def install(state_root, directory, plan, Refused):
    """Pin and bind against the records actually installed beside the receiver."""
    claude, codex = organ('control_engine_claude', directory), organ('control_engine_codex', directory)
    try:
        pinned = claude.pin(plan['claude_code']['version'], versions=plan['claude_code']['versions'],
                            state_root=state_root)
        vendor = codex.bind({'executable': plan['codex']['executable']})
    except (claude.Refused, codex.Refused) as error:
        raise Refused(error.code) from None
    return {bound['engine']: {key: bound[key] for key in ('version', 'path', 'sha256')}
            for bound in (pinned, vendor)}


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
        try:
            recorded = json.loads(record_path.read_text())
        except (OSError, ValueError):
            recorded = None
        else:
            if recorded != engines:
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
        raise Refused(error.code) from None
