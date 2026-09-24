#!/usr/bin/env bash
# VELDO canonical gate. One command, one clear result. Green is the only done.
#
# The slots below are the method's full validation catalog (method section 3,
# stage 6). Every item MUST be declared with one of three states:
#   required:<command>          the check runs; failure is red
#   na:<reason>                 not applicable here, with the reason on record
#   waived:<YYYY-MM-DD>:<reason>  consciously waived, with an expiry
# A blank item is UNDECLARED and makes the gate RED: a skipped validation is
# a decision someone made, never an omission nobody noticed. Secret detection
# runs always; VELDO contract validation runs always and is red if unavailable.
set -u
# CANDIDATE MODE (VELDO-0058). `verify.sh --candidate <root> --sink <dir>` is how the trusted
# installation verifies a landing candidate: this script is the installed copy, every check runs in
# <root>, and the stamp, the gate event and the review-event reconciliation are written to <dir>, a
# directory outside the candidate, never into the candidate's tree. The sink is refused before any
# check runs when it is absent, not a directory, not writable, the candidate itself or inside it
# (symlinks are resolved first), or already holds a symlink where an output goes; the result is then
# RED and nothing falls back to the candidate's own files. A write to the sink that fails at the end
# is RED too. With no arguments this is the ordinary checkout gate, unchanged: it verifies the
# checkout it lives in and writes .veldo/last_verify and .veldo/events.jsonl there, which is where
# the landing step commits them from. The line below is the interface the installed caller
# (control_verification.py) requires before it runs a verifier in candidate mode.
# veldo-gate-interface: candidate-sink/v1
VELDO_CANDIDATE=""; VELDO_SINK=""; VELDO_REFUSE=""; VELDO_OUT=".veldo"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --candidate|--sink)
      if [ "$#" -lt 2 ] || [ -z "$2" ]; then VELDO_REFUSE="$1 needs a value"; break; fi
      if [ "$1" = --candidate ]; then VELDO_CANDIDATE="$2"; else VELDO_SINK="$2"; fi
      shift 2 ;;
    *) VELDO_REFUSE="unknown argument (only --candidate <root> --sink <dir>)"; break ;;
  esac
done
if [ -z "$VELDO_REFUSE" ] && { [ -n "$VELDO_CANDIDATE" ] || [ -n "$VELDO_SINK" ]; } \
   && { [ -z "$VELDO_CANDIDATE" ] || [ -z "$VELDO_SINK" ]; }; then
  VELDO_REFUSE="candidate mode needs both --candidate and --sink"
fi
if [ -n "$VELDO_REFUSE" ]; then
  :
elif [ -n "$VELDO_CANDIDATE" ]; then
  if ! cd "$VELDO_CANDIDATE" 2>/dev/null; then
    VELDO_REFUSE="the candidate is not a directory"
  elif [ ! -d "$VELDO_SINK" ]; then
    VELDO_REFUSE="the sink is absent or not a directory"
  elif ! _veldo_sink=$(cd "$VELDO_SINK" 2>/dev/null && pwd -P); then
    VELDO_REFUSE="the sink cannot be entered"
  else
    _veldo_root=$(pwd -P)
    case "$_veldo_sink/" in "$_veldo_root"/*) VELDO_REFUSE="the sink resolves inside the candidate" ;; esac
    if [ -z "$VELDO_REFUSE" ] && [ ! -w "$_veldo_sink" ]; then VELDO_REFUSE="the sink is not writable"; fi
    for _veldo_f in last_verify events.jsonl; do
      if [ -z "$VELDO_REFUSE" ] && [ -L "$_veldo_sink/$_veldo_f" ]; then
        VELDO_REFUSE="the sink's $_veldo_f is a symlink"
      fi
    done
    VELDO_OUT="$_veldo_sink"
  fi
else
  cd "$(dirname "$0")/.."
fi
if [ -n "$VELDO_REFUSE" ]; then
  echo "== gate output: REFUSED - $VELDO_REFUSE; no check ran and nothing was written"
  echo "GATE: RED ($(git rev-parse --verify HEAD 2>/dev/null || echo "no-git"))"
  exit 1
fi

# ---- the validation catalog: declare EVERY item (see header) ---------------
CHECK_format="na:no formatter adopted yet"
CHECK_lint="required:bash scripts/check_lint.sh"
CHECK_types="na:untyped codebase or no checker adopted"
CHECK_unit="required:python3 scripts/selftest.py"
CHECK_integration="required:python3 scripts/check_first_use.py"
CHECK_contract="na:no external API contracts"
CHECK_journeys="na:no user interface in this repository"
CHECK_ui_states="na:no user interface in this repository"
CHECK_accessibility="na:no user interface in this repository"
CHECK_token_lint="na:no design system in this repository"
CHECK_visual_baselines="na:no user interface in this repository"
CHECK_build="na:nothing to build; committed pdf/ artifacts are a manual release act (render_pdfs.py + Chrome CDP)"
CHECK_dependency_audit="na:enforcement scripts are stdlib-only (verified); render_pdfs.py imports markdown, websockets, yaml from system python as a manual release act"
CHECK_licenses="na:dependencies not redistributed"
CHECK_security="required:python3 scripts/secret_inventory.py"
CHECK_migration="na:no database in this repository"
CHECK_generated="required:bash scripts/check_generated.sh"
CHECK_docs="required:bash scripts/check_docs.sh"
CHECK_performance="na:no performance thresholds declared"
CHECK_coverage="na:no coverage floor declared"
CHECK_packaging="required:python3 scripts/check_install_and_run.py"
CHECK_deploy_dry_run="na:no automated deployment path yet"
CHECK_extra="required:bash scripts/check_template_sync.sh && python3 -B scripts/check_gate_mutations.py"
# Configured for the VELDO home repository (docs + plugin templates + plans):
# lint syntax-checks every shipped script, unit is the contract-system
# negative self-test, docs enforces the standing hygiene rules, generated
# keeps the index derived, extra keeps instances synced to the template canon.
#
# INTEGRATION is the one stage that drives this repository's own writers end to
# end instead of reading artifacts: in a THROWAWAY COPY it uses a sanctioned
# writer the way the layer it belongs to exists to be used, runs the whole unit
# suite over the result, and requires that nothing which passed before now
# fails. It exists because five assertions independently wrote today's EMPTINESS
# down as a required invariant, so the suite was green only while nobody used
# the feature and reddened for the first person who did. It does NOT make
# recording anything a condition of the gate; it makes a suite that BREAKS on
# first real use a condition. Its limits are declared in the script's docstring,
# it fails LOUD rather than by default when it cannot answer, and it costs one
# nested suite run on the green path (the second run is paid only when there is
# a failure to attribute).
# -----------------------------------------------------------------------------

ORDER="format lint types unit integration contract journeys ui_states accessibility \
token_lint visual_baselines build dependency_audit licenses security migration \
generated docs performance coverage packaging deploy_dry_run extra"

FAIL=0; RAN=0; NA=0; WAIVED=0; UNDECLARED=0
TODAY=$(date -u +%Y-%m-%d)
for name in $ORDER; do
  var="CHECK_${name}"
  decl="${!var}"
  case "$decl" in
    "")
      echo "== ${name}: UNDECLARED (blank) - declare required:, na:, or waived:"
      UNDECLARED=$((UNDECLARED+1)); FAIL=1
      ;;
    required:*)
      cmd="${decl#required:}"
      echo "== ${name}"
      if bash -c "$cmd"; then
        echo "   ${name}: pass"; RAN=$((RAN+1))
      else
        echo "   ${name}: FAIL"; FAIL=1; RAN=$((RAN+1))
      fi
      ;;
    na:*)
      NA=$((NA+1))
      ;;
    waived:*)
      exp="${decl#waived:}"; exp="${exp%%:*}"
      if [[ "$exp" < "$TODAY" ]]; then
        echo "== ${name}: WAIVER EXPIRED (${exp}) - renew or implement"
        FAIL=1
      fi
      WAIVED=$((WAIVED+1))
      ;;
    *)
      # legacy plain command = treat as required
      echo "== ${name}"
      if bash -c "$decl"; then
        echo "   ${name}: pass"; RAN=$((RAN+1))
      else
        echo "   ${name}: FAIL"; FAIL=1; RAN=$((RAN+1))
      fi
      ;;
  esac
done

echo "== secret scan (built-in)"
if grep -rInE '(api[_-]?key|secret|password|token)[[:space:]]*[:=][[:space:]]*["'"'"'][A-Za-z0-9+/_-]{16,}' \
     --include='*' --exclude-dir={.git,node_modules,venv,.venv,dist,build,proof} \
     --exclude={verify.sh,veldo-guard.sh} . 2>/dev/null | grep -v '\.veldo/examples/'; then
  echo "   secret scan: FAIL (possible secret above)"; FAIL=1
else
  echo "   secret scan: pass"
fi

echo "== veldo contracts (built-in: fails closed if unavailable)"
if command -v python3 >/dev/null && [ -f .veldo/validate.py ]; then
  if python3 .veldo/validate.py all; then
    echo "   contracts: pass"
  else
    echo "   contracts: FAIL"; FAIL=1
  fi
else
  echo "   contracts: FAIL (python3 or .veldo/validate.py unavailable - the contract system is mandatory)"
  FAIL=1
fi

echo "== shape gate (built-in: mechanizable architecture-contract rules; adoption safe, fails closed)"
if ! python3 .veldo/shape_gate.py; then FAIL=1; fi

# Review observability (built-in): DERIVE the verdict.recorded event of every committed
# verdict artifact. It lives here, in the stage that always runs, because the thing it
# replaces was an instruction asking whoever ran a review to append the event by hand -
# and across every verdict in the corpus nobody ever did. It APPENDS AND REPORTS, and
# does NOT touch FAIL: a stage that reddened the build over its own bookkeeping would
# make the first run after it lands unlandable. Idempotent, so every run after the
# backfill appends nothing.
echo "== review events (built-in: derived from the verdict artifacts; appends and reports, never judges)"
# THE STAND-DOWN NAMES ITS OWN CONDITION, inside the `||` fallback WARP-0722 requires. A bare
# fallback could not tell a missing interpreter from a missing file from a crash inside the module,
# and a reviewer proved it swallowed a real traceback and still printed green. The guard stays a
# disjunction, so reconciliation still cannot redden the build (WARP-0722 AC1, deliberate: this is
# bookkeeping and must never make a landing impossible). What changes is that the line a human
# reads now distinguishes an ABSENCE from a DEFECT, which is the whole difference between standing
# down honestly and hiding.
# In candidate mode the reconciliation reads and appends the SINK's log, seeded once from the
# candidate's committed log so that what it already covers is still known; the candidate's own
# .veldo/events.jsonl is read and never written.
set --
if [ "$VELDO_OUT" != ".veldo" ]; then
  if [ ! -e "$VELDO_OUT/events.jsonl" ]; then
    if [ -f .veldo/events.jsonl ]; then cp .veldo/events.jsonl "$VELDO_OUT/events.jsonl"; else : > "$VELDO_OUT/events.jsonl"; fi
  fi
  set -- --repo-root "$(pwd -P)" --log "$VELDO_OUT/events.jsonl"
fi
python3 .veldo/events.py reconcile-verdicts "$@" || \
  { if ! command -v python3 >/dev/null 2>&1; then \
      echo "   review events: reconciliation unavailable (no python3 on PATH) - by design not a gate failure"; \
    elif [ ! -f .veldo/events.py ]; then \
      echo "   review events: reconciliation unavailable (.veldo/events.py not present) - by design not a gate failure"; \
    else \
      echo "   review events: PRESENT AND ERRORED - .veldo/events.py exists and reconcile-verdicts did not"; \
      echo "   review events: complete. A defect in this repository rather than an absence. It does not"; \
      echo "   review events: redden the build because WARP-0722 keeps this bookkeeping unable to make a"; \
      echo "   review events: landing impossible; the traceback above is the finding."; \
    fi; }

COMMIT=$(git rev-parse --verify HEAD 2>/dev/null || echo "no-git")
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
if [ "$VELDO_OUT" = ".veldo" ]; then mkdir -p .veldo; fi
if [ "$FAIL" -eq 0 ]; then STATUS=green; EVENT=gate.passed; else STATUS=red; EVENT=gate.failed; fi
# THE EXIT CODE AND THE SHAPE, both, and neither alone. version.py prints its REFUSAL on stdout
# when it cannot read a version, so taking the first word gave "veldo" - an invented version, in the
# one record where it would be believed, and it shipped to adopters. Found by independent review of
# VELDO-0010. The exit status is checked first, and the value must still LOOK like a version, because
# a shape test survives any future change to what that script prints.
VELDO_VERSION=""
if _veldo_v=$(python3 .veldo/version.py 2>/dev/null); then
  _veldo_v=$(printf '%s' "$_veldo_v" | awk '{print $1}')
  case "$_veldo_v" in [0-9]*.[0-9]*) VELDO_VERSION="$_veldo_v" ;; esac
fi
if [ -n "$VELDO_VERSION" ]; then VERSION_JSON="\"$VELDO_VERSION\""; else VERSION_JSON=null; fi
# WHAT WAS VERIFIED IS THE WORKING TREE, AND THE RECORD USED TO NAME ONLY THE COMMIT. Ledger finding 69:
# this stamp carried `commit` from `git rev-parse HEAD` and nothing about whether the tree was clean, so
# a reader of {"commit":"c771092","status":"green"} concluded that commit passed when what passed was
# that commit plus whatever was uncommitted - which through 2026-08-12 was routinely twenty-odd modified
# files. Gate-then-commit is the correct order and it makes the record lag by one commit every time, so
# the stamp systematically named a state it had not verified. Same family as findings 46, 56 and 68: a
# record whose SUBJECT is not what it appears to name.
# `tree` is "clean" or the COUNT of dirty paths, never the paths themselves: a filename can carry
# anything and this record is machine-read. A count is enough to tell a reader that `commit` alone does
# not identify what ran. If git cannot answer, the value is null rather than a guess at "clean", because
# an unanswered question and a clean tree invite opposite conclusions.
# Dmitry approved this protected-path edit on 2026-08-13 (Telegram 23680, "Change verify, it's fine, I
# was wrong about it") after first challenging whether verify.sh needed touching at all. It does: this
# printf is the only thing that writes the stamp, and run_scope.verify_stamp_payload has no production
# caller by design. Recorded at proof/WARP-0727/approval-dmitry-finding-69.json.
if _veldo_dirty=$(git status --porcelain 2>/dev/null); then
  if [ -z "$_veldo_dirty" ]; then TREE_JSON='"clean"'; else
    _veldo_n=$(printf '%s\n' "$_veldo_dirty" | wc -l | tr -d ' ')
    TREE_JSON="\"$_veldo_n dirty path(s)\""
  fi
else
  TREE_JSON=null
fi
STAMP_LINE=$(printf '{"commit":"%s","status":"%s","at":"%s","checks_run":%d,"checks_na":%d,"veldo_version":%s,"tree":%s}' \
  "$COMMIT" "$STATUS" "$TS" "$RAN" "$NA" "$VERSION_JSON" "$TREE_JSON")
EVENT_LINE=$(printf '{"schema":"veldo.event/v1","type":"%s","commit":"%s","at":"%s","producer":"verify.sh","checks_run":%d}' \
  "$EVENT" "$COMMIT" "$TS" "$RAN")
if [ "$VELDO_OUT" = ".veldo" ]; then
  printf '%s\n' "$STAMP_LINE" > .veldo/last_verify
  printf '%s\n' "$EVENT_LINE" >> .veldo/events.jsonl
else
  # The sink, written only through names that are not symlinks: the stamp is renamed into place (a
  # rename replaces a link rather than following it) and the event is appended only to a regular
  # file. Any failure is RED, and nothing is written to the candidate instead.
  _veldo_written=no
  if [ ! -L "$VELDO_OUT/events.jsonl" ] && [ -f "$VELDO_OUT/events.jsonl" ] \
     && printf '%s\n' "$STAMP_LINE" > "$VELDO_OUT/.last_verify.$$" 2>/dev/null \
     && mv -f "$VELDO_OUT/.last_verify.$$" "$VELDO_OUT/last_verify" 2>/dev/null \
     && printf '%s\n' "$EVENT_LINE" >> "$VELDO_OUT/events.jsonl" 2>/dev/null; then
    _veldo_written=yes
  fi
  if [ "$_veldo_written" != yes ]; then
    echo "== gate output: NOT WRITTEN - the sink refused the stamp or the gate event; this run is not trusted success"
    FAIL=1
  fi
fi

echo ""
echo "catalog: ${RAN} run, ${NA} not-applicable (reasons on record), ${WAIVED} waived, ${UNDECLARED} undeclared"
if [ "$FAIL" -eq 0 ]; then
  echo "GATE: GREEN (${COMMIT})"
  exit 0
else
  echo "GATE: RED (${COMMIT})"
  exit 1
fi
