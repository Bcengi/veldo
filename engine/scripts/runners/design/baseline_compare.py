#!/usr/bin/env python3
"""VELDO visual baseline comparator (reference).

The design contract's last layer is visual fidelity: a human approves a
rendered state against its design ONCE, that render is stored as a baseline,
and the machine guards drift forever after. This compares a current render to
its baseline and passes only if the fraction of differing pixels is within a
declared tolerance - never a machine-diff of a browser render against a design
export (that is unclosable), always render-vs-approved-baseline.

  baseline_compare.py <baseline.png> <current.png> [--config c.json] [--name n]

config.json (optional):
  {"default_tolerance": 0.01, "baselines": {"home": 0.02}}

Tolerance is the maximum fraction of pixels allowed to differ (0.01 = 1%).
--name selects a per-baseline tolerance from config; otherwise default is used.
Dimension mismatch is an automatic failure (the layout moved). Exit 0 =
within tolerance, 1 = drift beyond tolerance or size mismatch.
"""
import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops
except Exception:
    print("baseline compare: Pillow (PIL) is required")
    sys.exit(2)


def fraction_differ(a_path, b_path):
    a = Image.open(a_path).convert("RGB")
    b = Image.open(b_path).convert("RGB")
    if a.size != b.size:
        return None, a.size, b.size
    diff = ImageChops.difference(a, b)
    # a pixel "differs" if any channel differs at all
    bbox = diff.getbbox()
    if bbox is None:
        return 0.0, a.size, b.size
    differing = 0
    total = a.size[0] * a.size[1]
    for px in diff.getdata():
        if px != (0, 0, 0):
            differing += 1
    return differing / total, a.size, b.size


def tolerance_for(config_path, name):
    if not config_path:
        return 0.01
    cfg = json.loads(Path(config_path).read_text())
    if name and name in (cfg.get("baselines") or {}):
        return float(cfg["baselines"][name])
    return float(cfg.get("default_tolerance", 0.01))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline")
    ap.add_argument("current")
    ap.add_argument("--config")
    ap.add_argument("--name")
    args = ap.parse_args()

    tol = tolerance_for(args.config, args.name)
    frac, size_a, size_b = fraction_differ(args.baseline, args.current)
    if frac is None:
        print(f"baseline compare: SIZE MISMATCH baseline {size_a} vs current {size_b} - the layout moved")
        return 1
    pct = frac * 100
    if frac <= tol:
        print(f"baseline compare: pass ({pct:.3f}% differ, tolerance {tol * 100:.3f}%)")
        return 0
    print(f"baseline compare: FAIL ({pct:.3f}% differ exceeds tolerance {tol * 100:.3f}%)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
