#!/usr/bin/env python3
"""Pack drift gate check (PLAN-0008): every declared pack's engine is byte-identical to the source.

One canonical engine is assembled into a self-contained pack per AI coding tool. This is the
assertion that keeps "one source of truth, no drift" true: it reads the pack manifest
(.veldo/packs.json) and, for every pack, reports any engine file that is MISSING from or DIFFERS from
the canonical source. An empty report across all packs is conformance; any drift fails the gate by
name, so a pack can never silently fork the engine. The same discipline that keeps the two
capabilities.yaml copies in lockstep, generalized to the whole engine.

If no manifest is present the check is a no-op (a repo that ships one pack does not need it). Pure
stdlib, no network; reuses .veldo/pack.py (WARP-0801) - no second drift implementation.

  python3 scripts/check_pack_drift.py     # exit 0 if every pack conforms, 1 with named drift
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    PK = _load("veldo_pack", ".veldo/pack.py")
    try:
        cfg = PK.load_packs(repo_root=str(ROOT))
    except PK.PackManifestError as e:
        print("pack drift: FAIL (malformed manifest: %s)" % e)
        return 1
    if not cfg:
        print("pack drift: no manifest (no-op)")
        return 0
    report = PK.pack_drift_report(repo_root=str(ROOT))
    failed = False
    for pack_id, drift in report:
        if drift:
            failed = True
            print("   pack %s: %d engine file(s) drifted from the canonical source:" % (pack_id, len(drift)))
            for rel, reason in drift:
                print("     %s: %s" % (rel, reason))
        else:
            print("   pack %s: engine byte-identical to source" % pack_id)
    if failed:
        print("pack drift: FAIL")
        return 1
    print("pack drift: pass (%d pack(s))" % len(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
