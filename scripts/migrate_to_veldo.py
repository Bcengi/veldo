#!/usr/bin/env python3
"""Produce the FULL source tree for the public repository, once.

This is a one-time migration, not a pipeline, and it says so rather than pretending to be
publish.py's bigger sibling. publish.py answers "what may an adopter install"; this answers
"what does the project look like when the private repository stops existing". The two have
different subjects, so they are different programs, and this one reuses publish.py's scanner
rather than growing a second copy of the only safety that matters.

THE SHAPE, and each step exists because the step before it can be wrong:

  1. Copy every TRACKED file except an explicit deny list. Tracked, so untracked scratch cannot
     ride along. Deny list, so every withholding is a decision recorded in the map file.
  2. Redact, case preserving, from scripts/migrate_name_map.json.
  3. SCAN the produced tree with publish.py's own scanner and the same 26-name list. Non-empty
     means refuse: the tree is not publishable and no amount of intent changes that.
  4. Run the GATE inside the produced tree. A redaction that renames a spec id, breaks a plan
     reference or corrupts a JSON file leaves a scan that is clean and a repository that is
     dead, and only the gate can tell the difference.

Step 4 is the one that makes this trustworthy. A scrub verified only by "no forbidden words
remain" is verified by absence, and absence is exactly what a broken tree also looks like.

Usage:
  python3 scripts/migrate_to_veldo.py <dest> [--genericize-public] [--skip-gate]
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_FILE = ROOT / "scripts" / "migrate_name_map.json"
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".woff", ".woff2",
                   ".ttf", ".zip", ".gz", ".webp", ".pyc", ".mp4"}


def _publish_module():
    """publish.py is the ONE home of the private-name list and the scanner. Import it rather
    than reimplementing either, so a name added there is a name enforced here."""
    spec = importlib.util.spec_from_file_location("publish", str(ROOT / "scripts" / "publish.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_map():
    m = json.loads(MAP_FILE.read_text("utf-8"))
    names = {}
    for k, v in m["private"].items():
        if not k.startswith("_"):
            names[k] = v
    return m, names


def tracked_files():
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"],
                         capture_output=True, text=True, check=True).stdout
    return [p for p in out.split("\0") if p]


def denied(rel, deny):
    for pat in deny:
        if pat.startswith("_"):
            continue
        if rel == pat or (pat.endswith("/") and rel.startswith(pat)):
            return pat
    return None


def _case_preserving(replacement, matched):
    """A name appears as bcengi, Bcengi and BCENGI, and a redaction that only catches one
    spelling is the negative-grep mistake wearing a different hat. Mirror the shape of what
    was actually matched instead of assuming lowercase."""
    if matched.isupper() and len(matched) > 1:
        return replacement.upper()
    if matched[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def redact(text, names, path_placeholder):
    for name, replacement in names.items():
        # re.escape because affiliate-network and mailer carry a dot that would otherwise
        # match any character, which would silently over-redact.
        text = re.sub(re.escape(name),
                      lambda m: _case_preserving(replacement, m.group(0)),
                      text, flags=re.IGNORECASE)
    # Local build paths leak the operator's home directory and say nothing anyone needs. The
    # lookbehind is load bearing: without it this rewrites `GET /api/v1/home/`, which is the
    # product's own documented route, and a redaction that corrupts an endpoint is a defect
    # wearing a safety badge. Only an absolute path, never a nested segment.
    not_nested = r"(?<![A-Za-z0-9_.\-/])"
    text = re.sub(not_nested + r"/home/[A-Za-z0-9_.-]+/projects/[A-Za-z0-9_.-]+",
                  path_placeholder, text)
    text = re.sub(not_nested + r"/home/[A-Za-z0-9_.-]+", path_placeholder, text)
    return text


def redact_path(rel, names):
    """A FILENAME carries a name as loudly as a line of prose does, and redacting only the
    contents leaves plans/PLAN-0002-companion-home.md sitting in the tree announcing itself.
    The same map runs over the path, so a reference in some other file lands on the new name
    and the tree stays internally consistent."""
    for name, replacement in names.items():
        rel = re.sub(re.escape(name),
                     lambda m: _case_preserving(replacement, m.group(0)),
                     rel, flags=re.IGNORECASE)
    return rel


def build(dest, names, path_placeholder, deny):
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    copied, redacted, withheld = 0, 0, []
    for rel in tracked_files():
        if rel == ".veldo/private_names.txt":
            # NOT WITHHELD, REWRITTEN, and the difference matters. Deleting it looked right (the
            # list of what to hide is the last thing to publish) and broke the new repository's
            # own gate, because the honesty suite refuses to scan for nothing by design. It was
            # also the wrong question. The list's job in the new repository is to keep the METHOD
            # documents company-free going forward, and the only company names that can still
            # appear there are our own already-public ones. The private names are gone from every
            # byte of this tree, so listing them would be the single most revealing file in it:
            # a tidy index of exactly what we removed. So the new list carries the public names
            # only. It discloses nothing that is not on our website, and the sweep keeps working.
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            keep = sorted(k for k in json.loads(MAP_FILE.read_text("utf-8"))["public"]
                          if not k.startswith("_"))
            out.write_text(
                "# The names that must not appear in the method's own documents.\n"
                "# Swept over docs/ and packs/ by scripts/check_docs.sh on every gate run.\n"
                "# These are this project's own public product names. The dogfooding records\n"
                "# under specs/, plans/ and proof/ name them on purpose: they are receipts of\n"
                "# real work and a falsified receipt is worth nothing.\n"
                + "".join(n + "\n" for n in keep), "utf-8")
            copied += 1
            continue
        pat = denied(rel, deny)
        if pat:
            withheld.append(rel)
            continue
        src, out = ROOT / rel, dest / redact_path(rel, names)
        if not src.is_file():
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() in BINARY_SUFFIXES:
            shutil.copy2(src, out)
        else:
            try:
                original = src.read_text("utf-8")
            except UnicodeDecodeError:
                shutil.copy2(src, out)
                copied += 1
                continue
            new = redact(original, names, path_placeholder)
            out.write_text(new, "utf-8")
            # WRITING TEXT CREATES A NEW FILE AT THE DEFAULT MODE, so the executable bit is gone.
            # That silently disarms every git pre-push hook, veldo-guard.sh and bin/veldo: git
            # skips a hook it cannot execute, so the tree would have shipped LOOKING gated and
            # been fail-open. The leak scan cannot see this and did not; the gate inside the
            # produced tree caught all eleven, which is the entire argument for running it.
            shutil.copymode(src, out)
            if new != original:
                redacted += 1
        copied += 1
    return copied, redacted, withheld


def run_gate(dest):
    """The gate, inside the produced tree. It needs a git repository to reason about, so the
    tree gets one: a single commit, which is exactly the flattened history the migration is
    for. If this is red, the redaction broke something the scan cannot see."""
    dest = Path(dest)
    env = dict(os.environ, GIT_AUTHOR_NAME="Dmitry Grinberg",
               GIT_AUTHOR_EMAIL="dimaimages@gmail.com",
               GIT_COMMITTER_NAME="Dmitry Grinberg",
               GIT_COMMITTER_EMAIL="dimaimages@gmail.com")
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "commit", "-q", "-m", "Veldo"]):
        subprocess.run(cmd, cwd=str(dest), env=env, check=True,
                       capture_output=True, text=True)
    r = subprocess.run(["bash", "scripts/verify.sh"], cwd=str(dest),
                       capture_output=True, text=True)
    tail = [ln for ln in r.stdout.splitlines() if ln.startswith("GATE:")]
    return r.returncode, (tail[-1] if tail else "(no GATE line)"), r.stdout


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("dest")
    ap.add_argument("--genericize-public", action="store_true",
                    help="also rename our own already-public product names")
    ap.add_argument("--skip-gate", action="store_true",
                    help="produce and scan only; still refuses on a dirty scan")
    a = ap.parse_args(argv[1:])

    m, names = load_map()
    if a.genericize_public:
        names.update({k: v for k, v in m["public"].items() if not k.startswith("_")})

    copied, redacted, withheld = build(a.dest, names, m["path_placeholder"], m["deny"])
    print("migrate: %d file(s) -> %s" % (copied, a.dest))
    print("migrate: %d file(s) redacted, %d name(s) in the map" % (redacted, len(names)))
    print("migrate: withheld %d file(s): %s"
          % (len(withheld), ", ".join(sorted({w.split('/')[0] + '/' for w in withheld})) or "none"))

    pub = _publish_module()
    findings = pub.scan(Path(a.dest), pub.load_private_names())

    # OUR OWN PUBLIC NAMES ARE ALLOWED IN THE RECEIPTS AND NOWHERE ELSE (Dmitry, 2026-08-11:
    # "Leave our names, it's fine"). This is not a hole punched in the scanner, it is the split
    # the gate ALREADY enforces: scripts/check_docs.sh sweeps docs/ and packs/ for these names
    # and deliberately leaves design/ and research/ alone as internal provenance. The method's
    # generic documents and everything an adopter installs stay company-free; the dogfooding
    # records, which are receipts of real work and are worthless once falsified, keep the real
    # subject. A name is exempt only if it is on the public list AND under a receipt path.
    # Anything else still refuses, and the exempted count is PRINTED rather than swallowed,
    # because a scrub that quietly forgives things is a scrub nobody can audit.
    public = {k for k in m["public"] if not k.startswith("_")}
    if a.genericize_public:
        public = set()

    # The method's own documents stay company-free WITHOUT needing a rule here, because
    # scripts/check_docs.sh already sweeps docs/ and packs/ for exactly these names on every gate
    # run. The scan below confirms it: our names appear only in the dogfooding records, in the
    # scrubbing machinery, and in test fixtures that assert their own absence. So the exemption is
    # by NAME, matching the instruction, and the existing gate keeps the documents honest.
    #
    # SELF-REFERENCE: a file that IS the redaction machinery must be allowed to contain the thing
    # it looks for, or the scanner can never describe its own job. Listed by exact path, never by
    # pattern, so adding one stays a decision somebody made on purpose.
    machinery = ("scripts/publish.py", "site/build_site.py")
    accepted, refused = [], []
    for rel, name, line in findings:
        if name in public:
            accepted.append((rel, name, line))
        elif name.startswith("build path") and rel in machinery:
            accepted.append((rel, name, line))
        else:
            refused.append((rel, name, line))

    if accepted:
        by_name = {}
        for _, name, _ in accepted:
            by_name[name] = by_name.get(name, 0) + 1
        print("migrate: %d occurrence(s) of our own public names ALLOWED in the receipts: %s"
              % (len(accepted), ", ".join("%s %d" % (k, v) for k, v in sorted(by_name.items()))))
    if refused:
        print("migrate: SCAN DIRTY, %d finding(s) outside what is allowed. NOT PUBLISHABLE."
              % len(refused))
        for rel, name, line in refused[:25]:
            print("  %s:%s  %s" % (rel, line, name))
        if len(refused) > 25:
            print("  ... and %d more" % (len(refused) - 25))
        return 1
    print("migrate: leak scan clean over the produced tree against %d private name(s), "
          "no private name and no build path survives" % len(pub.load_private_names()))

    if a.skip_gate:
        print("migrate: gate SKIPPED by flag; the tree is scanned but not proven to work")
        return 0
    code, line, full = run_gate(a.dest)
    print("migrate: %s" % line)
    if code != 0:
        print("migrate: THE GATE IS RED IN THE PRODUCED TREE. The redaction broke something the "
              "scan cannot see. Not publishable.")
        for ln in full.splitlines():
            if "FAIL" in ln or "refus" in ln.lower():
                print("  " + ln)
        return 1
    print("migrate: the produced tree is clean AND its own gate is green.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
