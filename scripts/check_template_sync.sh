#!/usr/bin/env bash
# Template sync: engine/ is the canon; this repository's own instances must be byte-identical.
# Catches the classic drift where the template-owning repo quietly diverges from what it ships
# to everyone else.
#
# THE PAIRS ARE DERIVED, NOT LISTED, AND THAT IS THE POINT OF THIS FILE.
# It used to carry a hand-written list of seven pairs. Nine estimation modules shipped into
# engine/ and nobody added a single one, so the copy every adopter installs was covered by
# nothing: a review demonstrated it by inverting engine/.veldo/toe_corpus.py so the corpus always
# reported itself usable as ground truth, and this check printed pass while the whole suite
# printed 3942 passed. A curated list of what to verify is a promise that somebody will remember,
# and the thing it protects is exactly what people forget.
#
# So every tracked file under engine/ that has a counterpart at the path it ships to is compared,
# and drift is a failure. New engine files are covered the moment they are added, with nobody
# needing to know this file exists. 120 pairs today rather than 7.
#
# EXCEPTIONS ARE DECLARED HERE, EACH WITH ITS REASON, and an exception is the only way to opt out.
# A file that legitimately differs per repository says so in one place a reader can audit; a file
# that differs for no stated reason is drift and fails. Adding an entry here is a decision, which
# is the property the old list lost by being the only mechanism.
set -u
cd "$(dirname "$0")/.."
FAIL=0

is_excepted() {
  case "$1" in
    # The gate's own catalog: every repository declares which checks it runs and why the rest are
    # not applicable. Identical catalogs across repositories would mean the declaration is fiction.
    scripts/verify.sh) return 0 ;;
    # Per-repo policy: risk classes, protected paths and required independence are the local
    # decisions the method exists to let a team make.
    .veldo/policy.yaml) return 0 ;;
    # Per-repo architecture contract. The organ is adoption-safe precisely because this file is
    # local: docs state it is never shipped in the engine, and a repository with none is
    # byte-identically unaffected.
    .veldo/architecture.yaml) return 0 ;;
    # Per-repo tracker wiring: project keys and routing for one company's instance.
    .veldo/trackers.json) return 0 ;;
    # Per-repo agent instructions. The engine ships a starting point; a working repository's copy
    # accumulates its own standing decisions, which is the file doing its job.
    CLAUDE.md) return 0 ;;
    # The spec template and the derived index are local by construction: the index is generated
    # from this repository's own specs, and the template carries local conventions.
    specs/TEMPLATE.md) return 0 ;;
    specs/index.md) return 0 ;;
    *) return 1 ;;
  esac
}

CHECKED=0
EXCEPTED=0
UNPAIRED=0
while IFS= read -r eng; do
  inst="${eng#engine/}"
  # An engine file with no counterpart is not drift: much of engine/ is what init LAYS DOWN into a
  # fresh repository rather than something this repository runs a copy of.
  [ -f "$inst" ] || { UNPAIRED=$((UNPAIRED + 1)); continue; }
  if is_excepted "$inst"; then
    EXCEPTED=$((EXCEPTED + 1))
    continue
  fi
  CHECKED=$((CHECKED + 1))
  if ! cmp -s "$inst" "$eng"; then
    echo "   FAIL: $inst drifted from $eng"
    FAIL=1
  fi
done < <(git ls-files engine)

# A derived check that silently pairs nothing reports green, which is the failure mode this whole
# file exists to refuse. Fail closed on an implausible count rather than trust the enumeration.
if [ "$CHECKED" -lt 50 ]; then
  echo "   FAIL: only $CHECKED pair(s) compared, which cannot be right; the derivation is broken"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "template sync: pass ($CHECKED pair(s) compared, $EXCEPTED declared per-repo, $UNPAIRED engine-only)"
else
  echo "template sync: FAIL"
fi
exit $FAIL
