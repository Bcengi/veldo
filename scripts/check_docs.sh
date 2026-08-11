#!/usr/bin/env bash
# Docs hygiene: the standing rules of this repository, mechanically enforced.
#   1. No em-dash or en-dash in any tracked text file (ASCII hyphen only).
#   2. No non-ASCII in any tracked text file (box-drawing U+2500-257F and the
#      U+2713 checkmark are the only intentional exceptions, for diagrams).
#   3. Generic documents (docs/, packs/claude/) carry zero company or product
#      references. plans/, specs/, proof/, docs/design/, docs/research/ are
#      internal working artifacts: exempt from rule 3, never from 1 and 2.
# DOCS_CHECK_PATHS overrides the file lists (both sweeps) for hermetic tests.
set -u
cd "$(dirname "$0")/.."
FAIL=0

if [ -n "${DOCS_CHECK_PATHS:-}" ]; then
  TEXT_FILES="$DOCS_CHECK_PATHS"
  GENERIC_FILES="$DOCS_CHECK_PATHS"
else
  TEXT_FILES=$(git ls-files | grep -vE '^pdf/|\.(png|pdf|pyc|jpg|jpeg|webp|ico)$')
  GENERIC_FILES=$(git ls-files 'docs/*.md' 'docs/training/*.md' 'packs/claude/**' | grep -v '^docs/design/\|^docs/research/' | grep -v '\.png$')
fi

echo "-- dash sweep (em/en dashes forbidden)"
if echo "$TEXT_FILES" | xargs grep -lP '[\x{2013}\x{2014}]' 2>/dev/null; then
  echo "   FAIL: em/en dash found in files above"; FAIL=1
fi

echo "-- non-ASCII sweep"
if echo "$TEXT_FILES" | xargs grep -lP '[^\x00-\x7F\x{2500}-\x{257F}\x{2713}]' 2>/dev/null; then
  echo "   FAIL: non-ASCII characters in files above"; FAIL=1
fi

echo "-- genericity sweep (docs/ and packs/claude/; design/ and research/ are internal provenance)"
# ONE LIST, shared with the publication leak scan (scripts/publish.py). It used to be a regex
# literal here and a different judgement there, and two lists disagree the first time one is
# updated - silently, and in the direction that matters: this gate green, the published tree
# carrying the name. Per-repo like policy.yaml, so it stands down honestly where there is none.
NAMES_FILE=".veldo/private_names.txt"
# THIS REPOSITORY'S OWN DISTRIBUTION COORDINATE, read from a file rather than written here, because
# this script SHIPS. Hardcoding it put our organisation's name into a file handed to every adopter,
# and the publication leak scan refused the release over it, correctly. Absent means strip nothing,
# which is right for an adopter: their own coordinate is not in our name list.
OWN_COORD=""
[ -f .veldo/own_coordinate ] && OWN_COORD=$(head -1 .veldo/own_coordinate)
: "${OWN_COORD:=__no_own_coordinate__}"
if [ ! -f "$NAMES_FILE" ]; then
  echo "   (no $NAMES_FILE in this repository: genericity sweep stands down)"
else
  # FIXED STRINGS, not a regex. The list documents itself as substrings, and joining it into an
  # alternation made an entry containing a dot match an innocent phrase in a training document,
  # because a dot is a metacharacter. grep -F gives the same semantics the publication scan uses, so
  # the two cannot disagree about what a name is either.
  #
  # The example is described rather than quoted ON PURPOSE. This file SHIPS, and naming one of the
  # private terms in a comment put that term into the published tree, where the leak scan found it
  # and refused the release. A comment explaining a leak check must not itself be the leak.
  NAMES_TMP=$(mktemp)
  grep -vE '^[[:space:]]*(#|$)' "$NAMES_FILE" > "$NAMES_TMP"
  if [ ! -s "$NAMES_TMP" ]; then
    rm -f "$NAMES_TMP"
    echo "   (no names declared in $NAMES_FILE: genericity sweep stands down)"
  else
    # The repository's own distribution coordinates are not a company reference.
    HITS=""
    for f in $GENERIC_FILES; do
      if sed "s|$OWN_COORD||g" "$f" | grep -qiF -f "$NAMES_TMP"; then HITS="$HITS $f"; fi
    done
    rm -f "$NAMES_TMP"
    if [ -n "$HITS" ]; then
      echo "   FAIL: private name in generic docs:"
      for f in $HITS; do echo "      $f"; done
      FAIL=1
    fi
  fi
fi

if [ "$FAIL" -eq 0 ]; then echo "docs hygiene: pass"; else echo "docs hygiene: FAIL"; fi
exit $FAIL
