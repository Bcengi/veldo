#!/usr/bin/env bash
# Docs hygiene: the standing rules of this repository, mechanically enforced.
#   1. No em-dash or en-dash in any tracked text file (ASCII hyphen only).
#   2. No non-ASCII in any tracked text file (box-drawing U+2500-257F and the
#      U+2713 checkmark are the only intentional exceptions, for diagrams).
#   3. Generic documents (docs/, packs/claude/) carry zero company or product
#      references. plans/, specs/, proof/, docs/design/, docs/research/ are
#      internal working artifacts: exempt from rule 3, never from 1 and 2.
# DOCS_CHECK_PATHS overrides the file lists (both sweeps) for hermetic tests.
#
# EVERY FILE IS CHECKED, WHATEVER THE SIZE OF THE LIST. Sweeps 1 and 2 used to be
# "xargs grep -l" tested by its exit status. xargs splits a long list into several grep
# calls and answers 123 when any one of them found nothing, so with more files than one
# call holds the sweep printed its findings and passed: red or green depended on where the
# batch boundaries fell. The verdict is now the list of files found, never an exit status,
# and a grep that could not run (an unreadable file, a locale without UTF-8) fails the
# sweep instead of counting as "nothing found".
#
# What is not a text file is declared, not guessed: pdf/ and the binary extensions in
# BINARY below. A text file that has to keep a non-ASCII character it did not write
# (a generated lockfile, a raw tool log kept as evidence) is named, with its reason, in
# .veldo/docs_nonascii_allowed.txt: one "path<space>reason" line each. A named file is
# exempt from rule 2 only, and an entry whose file is gone or has become clean fails the
# check, so the list cannot outlive its reasons. Absent file: nothing is exempt.
set -u
cd "$(dirname "$0")/.."
FAIL=0
export LC_ALL=C.UTF-8
BINARY='\.(png|pdf|pyc|jpg|jpeg|webp|ico|gz)$'
ALLOWED_FILE=".veldo/docs_nonascii_allowed.txt"
DASH='[\x{2013}\x{2014}]'
NON_ASCII='[^\x00-\x7F\x{2500}-\x{257F}\x{2713}]'

# The text files to sweep, NUL-separated. Only regular files: a tracked path that is a
# symlink, a submodule or deleted from the working tree has no text of its own here.
text_files() {
  if [ -n "${DOCS_CHECK_PATHS:-}" ]; then
    # shellcheck disable=SC2086
    printf '%s\0' $DOCS_CHECK_PATHS
  else
    git ls-files -z | grep -zvE "^pdf/|$BINARY"
  fi | while IFS= read -r -d '' f; do
    if [ -f "$f" ] && [ ! -L "$f" ]; then printf '%s\0' "$f"; fi
  done
}

# sweep <pattern> <file for the hits>: every listed file is read; the hits are the names
# written. Returns 1 only when a grep could not do its work (its status above 1).
sweep() {
  text_files | xargs -0 -r sh -c 'grep -lP -e "$0" -- "$@"; [ $? -le 1 ]' "$1" > "$2"
}

HITS=$(mktemp)
trap 'rm -f "$HITS" "$HITS.kept"' EXIT

if [ -n "${DOCS_CHECK_PATHS:-}" ]; then
  GENERIC_FILES="$DOCS_CHECK_PATHS"
else
  GENERIC_FILES=$(git ls-files 'docs/*.md' 'docs/training/*.md' 'packs/claude/**' | grep -v '^docs/design/\|^docs/research/' | grep -v '\.png$')
fi

echo "-- dash sweep (em/en dashes forbidden)"
if ! sweep "$DASH" "$HITS"; then
  echo "   FAIL: the dash sweep could not read every file"; FAIL=1
fi
if [ -s "$HITS" ]; then
  cat "$HITS"
  echo "   FAIL: em/en dash found in files above"; FAIL=1
fi

echo "-- non-ASCII sweep"
if ! sweep "$NON_ASCII" "$HITS"; then
  echo "   FAIL: the non-ASCII sweep could not read every file"; FAIL=1
fi
if [ -z "${DOCS_CHECK_PATHS:-}" ] && [ -f "$ALLOWED_FILE" ]; then
  # Declared exceptions: drop each named file from the hits; a name that is not a hit is stale.
  : > "$HITS.kept"
  while IFS= read -r line; do
    case $line in ''|'#'*) continue ;; esac
    path=${line%% *}
    if [ "$path" = "$line" ]; then
      echo "   FAIL: $ALLOWED_FILE names $path without a reason"; FAIL=1
    fi
    if grep -qxF -- "$path" "$HITS"; then
      printf '%s\n' "$path" >> "$HITS.kept"
    else
      echo "   FAIL: $ALLOWED_FILE names $path, which has no non-ASCII character now (or is not a swept file): remove the entry"; FAIL=1
    fi
  done < "$ALLOWED_FILE"
  if [ -s "$HITS.kept" ]; then
    echo "   ($(wc -l < "$HITS.kept") file(s) declared in $ALLOWED_FILE, each with its reason)"
    grep -vxF -f "$HITS.kept" "$HITS" > "$HITS.left"; mv "$HITS.left" "$HITS"
  fi
fi
if [ -s "$HITS" ]; then
  cat "$HITS"
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
