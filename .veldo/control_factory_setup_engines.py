"""Factory setup's qualified host engines. Reads bytes, never executes an engine."""
import importlib.util
from pathlib import Path
import shutil


def organ(name, directory=None):
    path = Path(directory or Path(__file__).parent) / (name + '.py')
    spec = importlib.util.spec_from_file_location('setup_engines_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(Refused):
    """Locate the installed versioned Claude file and Codex package through PATH, before any write."""
    claude, codex = organ('control_engine_claude'), organ('control_engine_codex')
    paths = {}
    for engine, command in (('claude_code', 'claude'), ('codex', 'codex')):
        found = shutil.which(command)
        if found is None:
            raise Refused('missing_evidence:engine_source:' + engine)
        paths[engine] = Path(found).resolve()
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
        code = 'binding_mismatch:engine_digest' if error.code == 'stale_subject:engine_digest' else error.code
        raise Refused(code) from None
    return {bound['engine']: {key: bound[key] for key in ('version', 'path', 'sha256')}
            for bound in (pinned, vendor)}


def count_pins(state_root, engines):
    """Count distinct regular pinned copies made under this factory's engine directory."""
    directory = Path(state_root).resolve() / 'engines'
    paths = {Path(bound['path']) for bound in engines.values()}
    return sum(path.is_file() and not path.is_symlink() and directory in path.parents for path in paths)
