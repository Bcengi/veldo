#!/usr/bin/env python3
"""VELDO pack engine: assemble a self-contained pack from one canonical engine, and prove no
pack has drifted.

A pack is a complete drop-in for one AI coding tool: the tool-agnostic VELDO engine (the gate,
policy_check, validate, the .veldo substrate, the runners, the CI workflow, capabilities.yaml,
the templates) PLUS that tool's driver wrapper (its agents, skills or commands, guard trigger,
and instruction file). "Each pack has everything in it" and "one source of truth, no drift"
hold at once because every pack's engine is ASSEMBLED from a single canonical source, and a
drift-check proves the assembled copy byte-identical - the same discipline that keeps the two
capability files in lockstep, generalized to the whole engine.

Pure stdlib file operations, parametrized by path so they are deterministic and gate-tested
offline over temporary trees. This is the mechanism (W1 of PLAN-0008); wiring it to the real
plugin engine and creating the seven packs is W2 (Claude as a peer) onward."""
import filecmp
import glob
import json
import os
import shutil

# The canonical ENGINE: the tool-agnostic files that must be byte-identical in every pack. Globs
# are relative to the engine source root. The driver wrapper (per tool) is everything a pack adds
# on top of these. W2 finalized this against the real substrate (engine): the guard script
# and the whole runners tree are engine, alongside the gate, the .veldo modules and config, the CI
# workflow, and the spec/plan templates. W5 of PLAN-0009 added the veldo CLI front door (bin/veldo): it
# is engine, so every pack carries it and the drift-check covers its content and its executable bit.
ENGINE_GLOBS = (
    "scripts/verify.sh",
    "scripts/veldo-guard.sh",
    "scripts/*.py",
    "scripts/runners/**/*",
    "bin/veldo",
    ".veldo/*.py",
    ".veldo/*.yaml",
    ".github/workflows/veldo-gate.yml",
    "specs/TEMPLATE.md",
    "plans/TEMPLATE.md",
)

# Build artifacts are never part of the byte-identical engine set: a __pycache__ directory holds
# compiled .pyc files that are not source and would spuriously "drift" between packs.
def _is_artifact(rel):
    parts = rel.replace("\\", "/").split("/")
    return "__pycache__" in parts or rel.endswith(".pyc")


def engine_files(engine_src, globs=ENGINE_GLOBS):
    """The sorted set of engine files (paths relative to engine_src) matching the manifest, with
    build artifacts (__pycache__, .pyc) excluded so the set is exactly the shipped source."""
    out = set()
    for g in globs:
        for p in glob.glob(os.path.join(engine_src, g), recursive=True):
            if os.path.isfile(p):
                rel = os.path.relpath(p, engine_src)
                if not _is_artifact(rel):
                    out.add(rel)
    return sorted(out)


def assemble_pack(engine_src, wrapper_src, agents_md, dest, globs=ENGINE_GLOBS):
    """Assemble a self-contained pack at dest: every engine file copied byte-for-byte from
    engine_src, the tool wrapper tree copied from wrapper_src, and the canonical AGENTS.md
    placed at dest/AGENTS.md. Returns dest. The result is a complete drop-in - engine plus
    wrapper together, nothing external needed."""
    for rel in engine_files(engine_src, globs):
        src = os.path.join(engine_src, rel)
        dst = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)  # copy CONTENT AND MODE: an engine script's exec bit is load-bearing
    if wrapper_src and os.path.isdir(wrapper_src):
        for root, _dirs, files in os.walk(wrapper_src):
            for fn in files:
                src = os.path.join(root, fn)
                rel = os.path.relpath(src, wrapper_src)
                dst = os.path.join(dest, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy(src, dst)
    if agents_md and os.path.isfile(agents_md):
        shutil.copy(agents_md, os.path.join(dest, "AGENTS.md"))
    return dest


def engine_drift(engine_src, pack_dir, globs=ENGINE_GLOBS):
    """Report every engine file that is MISSING from a pack or DIFFERS from the canonical
    source, as a list of (relative_path, reason). An empty list means the pack's engine is
    byte-identical to the source - the assertion the gate makes so no pack silently forks."""
    drift = []
    for rel in engine_files(engine_src, globs):
        src = os.path.join(engine_src, rel)
        dst = os.path.join(pack_dir, rel)
        if not os.path.isfile(dst):
            drift.append((rel, "missing"))
        elif not filecmp.cmp(src, dst, shallow=False):
            drift.append((rel, "differs"))
        elif (os.stat(src).st_mode & 0o111) != (os.stat(dst).st_mode & 0o111):
            # content matches but the executable bit does not: a non-executable copy of an engine
            # script (e.g. a git hook or veldo-guard.sh) is silently skipped by git and fails open,
            # so mode drift is real drift, not cosmetic.
            drift.append((rel, "mode"))
    return drift


PACKS_SCHEMA = "veldo.packs/v1"


class PackManifestError(ValueError):
    """The pack manifest is malformed - raised by name so a bad manifest never silently no-ops
    (parallels TrackerConfigError in the tracker resolver)."""


def default_packs_path(repo_root=None):
    return os.path.join(repo_root or ".", ".veldo", "packs.json")


def load_packs(repo_root=None, path=None):
    """Load and validate the pack manifest (.veldo/packs.json, veldo.packs/v1), or return {} if none
    is present. Pure: reads one file, no network. A malformed manifest is rejected by name."""
    p = path or default_packs_path(repo_root)
    if not os.path.exists(p):
        return {}
    with open(p) as f:
        data = json.load(f)
    _validate_packs(data)
    return data


def _validate_packs(cfg):
    if not isinstance(cfg, dict) or cfg.get("schema") != PACKS_SCHEMA:
        raise PackManifestError("pack manifest schema must be %r" % PACKS_SCHEMA)
    packs = cfg.get("packs")
    if not isinstance(packs, list) or not packs:
        raise PackManifestError("pack manifest needs a non-empty 'packs' list")
    seen = set()
    for pk in packs:
        pid = (pk or {}).get("id")
        if not pid:
            raise PackManifestError("a pack entry is missing its 'id'")
        for field in ("tool", "engine_src", "pack_dir"):
            if not pk.get(field):
                raise PackManifestError("pack %r must declare a %r" % (pid, field))
        if pid in seen:
            raise PackManifestError("duplicate pack id %r" % pid)
        seen.add(pid)


def pack_drift_report(repo_root=None, path=None):
    """For every declared pack, the engine drift of its pack_dir against its engine_src. Returns a
    list of (pack_id, drift_list); a pack with an empty drift_list is conformant. Paths in the
    manifest are relative to repo_root. The canonical source for a pack is its declared engine_src."""
    cfg = load_packs(repo_root=repo_root, path=path)
    root = repo_root or "."
    report = []
    for pk in cfg.get("packs", []):
        engine_src = os.path.join(root, pk["engine_src"])
        pack_dir = os.path.join(root, pk["pack_dir"])
        report.append((pk["id"], engine_drift(engine_src, pack_dir)))
    return report
