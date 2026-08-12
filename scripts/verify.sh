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
cd "$(dirname "$0")/.."

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
CHECK_extra="required:bash scripts/check_template_sync.sh"
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
python3 .veldo/events.py reconcile-verdicts || \
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
mkdir -p .veldo
if [ "$FAIL" -eq 0 ]; then STATUS=green; EVENT=gate.passed; else STATUS=red; EVENT=gate.failed; fi
VELDO_VERSION=$(python3 .veldo/version.py 2>/dev/null | awk '{print $1}')
if [ -n "$VELDO_VERSION" ]; then VERSION_JSON="\"$VELDO_VERSION\""; else VERSION_JSON=null; fi
printf '{"commit":"%s","status":"%s","at":"%s","checks_run":%d,"checks_na":%d,"veldo_version":%s}\n' \
  "$COMMIT" "$STATUS" "$TS" "$RAN" "$NA" "$VERSION_JSON" > .veldo/last_verify
printf '{"schema":"veldo.event/v1","type":"%s","commit":"%s","at":"%s","producer":"verify.sh","checks_run":%d}\n' \
  "$EVENT" "$COMMIT" "$TS" "$RAN" >> .veldo/events.jsonl

echo ""
echo "catalog: ${RAN} run, ${NA} not-applicable (reasons on record), ${WAIVED} waived, ${UNDECLARED} undeclared"
if [ "$FAIL" -eq 0 ]; then
  echo "GATE: GREEN (${COMMIT})"
  exit 0
else
  echo "GATE: RED (${COMMIT})"
  exit 1
fi
