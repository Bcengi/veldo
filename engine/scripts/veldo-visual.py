#!/usr/bin/env python3
"""VELDO visual composite builder: the reference implementation of the visual
pipeline's last step. Takes the design frame (exported from the design tool's
API) and the rendered capture (Playwright or emulator), and produces the
side-by-side composite with a pixel-diff strip that gets DELIVERED to the
judging human and stored as evidence.

Usage:
  python3 scripts/veldo-visual.py <figma.png> <rendered.png> <out-composite.png>

Requires: Pillow (pip install pillow). Stack-agnostic by design: anything
that can produce two PNGs can use it.
"""
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFont


def build(figma_path, rendered_path, out_path):
    a = Image.open(figma_path).convert("RGB")
    b = Image.open(rendered_path).convert("RGB")

    # normalize heights for a fair side-by-side
    h = max(a.height, b.height)
    if a.height != h:
        a = a.resize((int(a.width * h / a.height), h))
    if b.height != h:
        b = b.resize((int(b.width * h / b.height), h))

    # diff strip: compare at common size, highlight mismatched pixels
    common_w = min(a.width, b.width)
    a_c = a.resize((common_w, h))
    b_c = b.resize((common_w, h))
    diff = ImageChops.difference(a_c, b_c).convert("L")
    # threshold: anything visibly different glows red on dark
    strip = Image.new("RGB", (common_w, h), (24, 24, 24))
    mask = diff.point(lambda v: 255 if v > 24 else 0)
    red = Image.new("RGB", (common_w, h), (255, 64, 64))
    strip.paste(red, mask=mask)
    changed_pct = 100.0 * sum(mask.point(bool).getdata()) / (common_w * h)

    gap, label_h = 16, 28
    W = a.width + gap + b.width + gap + strip.width
    out = Image.new("RGB", (W, h + label_h), (255, 255, 255))
    out.paste(a, (0, label_h))
    out.paste(b, (a.width + gap, label_h))
    out.paste(strip, (a.width + gap + b.width + gap, label_h))

    d = ImageDraw.Draw(out)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
    d.text((4, 6), "DESIGN (figma export)", fill=(0, 0, 0), font=font)
    d.text((a.width + gap + 4, 6), "RENDERED", fill=(0, 0, 0), font=font)
    d.text((a.width + gap + b.width + gap + 4, 6),
           f"DIFF ({changed_pct:.1f}% of pixels differ)", fill=(180, 0, 0), font=font)

    out.save(out_path)
    print(f"composite: {out_path} ({changed_pct:.1f}% pixel difference)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    sys.exit(build(sys.argv[1], sys.argv[2], sys.argv[3]))
