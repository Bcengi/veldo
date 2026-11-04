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


def install(root, base, mods):
    formats = load('v186_formats', root / 'proof/VELDO-0172/fake_formats.py')
    # Carry the shared constructor even though this fixture emits no engine protocol.
    fake = formats.embed('#!/usr/bin/env python3\nimport json\nraise SystemExit("installation fixture must not execute")\n')
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
    engines = json.loads((mods / 'runtime/engines.json').read_text())
    manifest.write_text(json.dumps({'name': codex.PACKAGE, 'version': engines['codex']['version']}))
    qualification = codex.qualification(str(vendor))
    # VELDO-0230: the qualified binary's bundled catalog, as the shipped record holds it, with its digest and the
    # model tool modes the writer derives from it (codex.catalog_modes), never copied apart from their catalog.
    catalog = json.loads((root / '.veldo/runtime/codex-qualification.json').read_text())['model_catalog']
    qualification.update(model_catalog=catalog, model_catalog_digest=codex.catalog_digest(catalog),
                         model_tool_modes=codex.catalog_modes(catalog))
    (mods / 'runtime/codex-qualification.json').write_text(json.dumps(qualification))
    shim = package / 'bin/codex.js'
    shim.parent.mkdir()
    shim.write_text('installation fixture shim; must not execute\n')
    shim.chmod(0o755)
    path = base / 'path'
    path.mkdir()
    (path / 'claude').symlink_to(source)
    # VELDO-0230 AC4: setup takes the Claude Code copy the engines record beside the modules names.
    engines['claude_code'].update(binary=str(source), sha256=claude._file_digest(source), version=version)
    (mods / 'runtime/engines.json').write_text(json.dumps(engines, indent=1, sort_keys=True) + '\n')
    (path / 'codex').symlink_to(shim)
    return dict(fake=fake, path=path, version=version, source=source, vendor=vendor, manifest=manifest)
