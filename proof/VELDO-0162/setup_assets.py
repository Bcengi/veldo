"""Inert engine bytes for installation tests, never launched or logged in."""
import importlib.util
import json
from pathlib import Path
import shutil


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def install(root, base, mods, fake):
    shutil.copytree(root / '.veldo/runtime', mods / 'runtime', dirs_exist_ok=True)
    claude = load('v186_claude_fixture', mods / 'control_engine_claude.py')
    codex = load('v186_codex_fixture', mods / 'control_engine_codex.py')
    record = claude.qualification()
    version = sorted(record['versions'])[-1]
    versions = base / 'versions'
    versions.mkdir()
    source = versions / version
    source.write_text(fake)
    source.chmod(0o755)
    record['versions'][version]['sha256'] = claude._file_digest(source)
    (mods / 'runtime/claude-qualification.json').write_text(json.dumps(record))
    package = base / 'package'
    vendor = package / 'vendor/fixture/codex'
    vendor.parent.mkdir(parents=True)
    vendor.write_text(fake)
    vendor.chmod(0o755)
    manifest = package / 'package.json'
    manifest.write_text(json.dumps({'name': codex.PACKAGE, 'version': '0.154.0'}))
    qualification = codex.qualification(str(vendor))
    (mods / 'runtime/codex-qualification.json').write_text(json.dumps(qualification))
    shim = package / 'bin/codex.js'
    shim.parent.mkdir()
    shim.write_text('installation fixture shim; must not execute\n')
    shim.chmod(0o755)
    path = base / 'path'
    path.mkdir()
    (path / 'claude').symlink_to(source)
    (path / 'codex').symlink_to(shim)
    return dict(fake=fake, path=path, version=version, source=source, vendor=vendor, manifest=manifest)
