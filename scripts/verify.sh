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
# The script and all security helpers come from the authority installation.
VELDO_AUTHORITY=$(cd "$(dirname "$0")/.." && pwd -P)
# How this gate was started, kept for the host holder (VELDO-0220), which runs it again inside
# its lock and scope from where it was started.
VELDO_SELF="$(cd "$(dirname "$0")" && pwd -P)/$(basename "$0")"; VELDO_START=$(pwd -P); VELDO_ARGV=("$@")
git() {
  python3 -I -S "$VELDO_AUTHORITY/.veldo/candidate_git.py" --root "$(pwd -P)" -- "$@"
}
# Every candidate command starts through the authority's gate_candidate.py (VELDO-0271): in the
# candidate root, standard input from /dev/null, every inherited descriptor closed, and an
# environment that carries no credential name. Each stage is one command and one stage line.
veldo_candidate() {
  python3 -I -S "$VELDO_AUTHORITY/scripts/gate_candidate.py" --root "$(pwd -P)" -- "$@"
}
# A LEFTOVER NAMESPACE HELPER (VELDO-0271). The gate once ran candidate commands through a
# root-installed helper and its AppArmor profile. Nothing calls either any more. Where one is still
# installed the gate says so once, with the owner's removal command, and the result does not change.
# VELDO_HOST_ROOT names another root to look under (a fixture host); it changes only this report.
veldo_leftover_report() {
  _veldo_left=""
  for _veldo_p in /usr/local/lib/veldo/veldo-userns /etc/apparmor.d/veldo-userns; do
    if [ -e "${VELDO_HOST_ROOT:-}$_veldo_p" ] || [ -L "${VELDO_HOST_ROOT:-}$_veldo_p" ]; then
      _veldo_left="${_veldo_left:+$_veldo_left, }$_veldo_p"
    fi
  done
  if [ -n "$_veldo_left" ]; then
    echo "leftover_namespace_helper: $_veldo_left is installed and no longer used; the owner removes it with: sudo rm /usr/local/lib/veldo/veldo-userns; sudo apparmor_parser -R /etc/apparmor.d/veldo-userns; sudo rm /etc/apparmor.d/veldo-userns"
  fi
}

# CANDIDATE MODE (VELDO-0058). `verify.sh --candidate <root> --sink <dir>` is how the trusted
# installation verifies a landing candidate: this script is the installed copy, every check runs in
# <root>, and the stamp, the gate event and the review-event reconciliation are written to <dir>, a
# directory outside the candidate, never into the candidate's tree. The sink is refused before any
# check runs when it is absent, not a directory, not writable, the candidate itself or inside it
# (symlinks are resolved first), or already holds a symlink where the event log goes (the stamp is
# renamed into place, which replaces a link rather than following it); the result is then
# RED and nothing falls back to the candidate's own files. A write to the sink that fails at the end
# is RED too. With no arguments this is the ordinary checkout gate, unchanged: it verifies the
# checkout it lives in and writes its stamp and its gate event under .veldo there, which is where
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
    if [ -z "$VELDO_REFUSE" ] && [ -L "$_veldo_sink/events.jsonl" ]; then
      VELDO_REFUSE="the sink's events.jsonl is a symlink"
    fi
    VELDO_OUT="$_veldo_sink"
  fi
else
  cd "$(dirname "$0")/.."
fi
if [ -n "$VELDO_REFUSE" ]; then
  echo "== gate output: REFUSED - $VELDO_REFUSE; no check ran and nothing was written"
  echo "GATE: RED (candidate refused)"
  exit 1
fi

# Refuse marker redirection before any candidate code or repository Git command. A checkout with
# no Git marker at all has nothing to redirect: the guard refuses every Git query there, so the
# stamp records no-git. A marker is checked against the authority's own shared gitdir.
if [ -e .git ] || [ -L .git ]; then
  if [ -z "${VELDO_EXPECTED_GIT_COMMON:-}" ]; then
    if ! VELDO_EXPECTED_GIT_COMMON=$(python3 -I -S "$VELDO_AUTHORITY/.veldo/candidate_git.py" --authority-common); then
      echo "GATE: RED (authority Git directory unavailable)"
      exit 1
    fi
  fi
  export VELDO_EXPECTED_GIT_COMMON
  if ! python3 -I -S "$VELDO_AUTHORITY/.veldo/candidate_git.py" --root "$(pwd -P)" --validate-only; then
    echo "GATE: RED (candidate Git boundary refused)"
    exit 1
  fi
fi

# THE HOST LOCK AND THE GATE'S OWN SCOPE (VELDO-0220). The authority's scripts/gate_host.json, when it
# exists, names the lock every heavy run on this host serializes on and the scope the gate runs in.
# Before the first check, a gate not yet running under its holder execs scripts/gate_host.py, which
# takes the lock (or finds it held for this gate by its caller), runs in a delegated user scope of its
# own and starts this script again inside them. A lock held by anyone else is GATE: NOT STARTED with
# exit 75: no check runs, and no stamp and no event are written. With no file there is no lock and no
# scope, as before; the host field below is then absent from the stamp and the event.
VELDO_HOST_FIELD=""
if [ -e "$VELDO_AUTHORITY/scripts/gate_host.json" ]; then
  if _veldo_host=$(python3 -I -S "$VELDO_AUTHORITY/scripts/gate_host.py" --inside); then
    # The stamp and the event are records the gate commits beside the candidate, so the host lock's
    # path names the home directory as ~ (VELDO-0259): the personal-setup stage judges every added
    # line, and the gate's own writer must not hand it the host owner's home.
    _veldo_host=$(printf '%s' "$_veldo_host" | python3 -I -S -c '
import json, os, re, sys
homes = {os.path.expanduser("~")}
try:
    import pwd
    homes.add(pwd.getpwuid(os.getuid()).pw_dir)
except (ImportError, KeyError):
    pass
homes = sorted({h.rstrip("/") for h in homes if h and h.rstrip("/")}, key=len, reverse=True)
def tilde(value):
    if isinstance(value, str):
        for home in homes:
            value = re.sub(re.escape(home) + r"(?![A-Za-z0-9_.\-])", lambda _: "~", value)
        return value
    if isinstance(value, dict):
        return {k: tilde(v) for k, v in value.items()}
    if isinstance(value, list):
        return [tilde(v) for v in value]
    return value
print(json.dumps(tilde(json.load(sys.stdin)), sort_keys=True, separators=(",", ":")))
') || _veldo_host=null
    VELDO_HOST_FIELD=",\"host\":$_veldo_host"
  else
    _veldo_root=$(pwd -P)
    cd "$VELDO_START" && exec python3 -I -S "$VELDO_AUTHORITY/scripts/gate_host.py" --enter --root "$_veldo_root" \
      -- "$VELDO_SELF" "${VELDO_ARGV[@]}"
    echo "GATE: RED (the host holder could not be started)"
    exit 1
  fi
fi

# THE MUTATION SELECTION (VELDO-0267). The mutation stage runs the cases this candidate's changes
# select plus a fixed canary set (scripts/mutation_selection.py), or the full sweep when a trigger
# says so. Its base is the trunk commit the gate is told to compare against: VELDO_GATE_BASE_COMMIT
# from the caller (a landing's synced trunk commit), else the trunk branch's commit read HERE, before
# any candidate command runs and could move it. The stage writes its selection record beside the
# stamp before the first case runs; the stamp's mutation block names its digest.
if [ -z "${VELDO_GATE_BASE_COMMIT:-}" ]; then
  VELDO_GATE_BASE_COMMIT=$(git rev-parse --verify --quiet 'refs/heads/main^{commit}' 2>/dev/null || true)
fi
export VELDO_GATE_BASE_COMMIT
VELDO_MUTATION_SELECTION=""
if _veldo_o=$(cd "$VELDO_OUT" 2>/dev/null && pwd -P); then
  VELDO_MUTATION_SELECTION="$_veldo_o/mutation-selection.json"
  rm -f "$VELDO_MUTATION_SELECTION"
fi
export VELDO_MUTATION_SELECTION

# ---- the validation catalog: declare EVERY item (see header) ---------------
CHECK_format="na:no formatter adopted yet"
CHECK_lint="required:bash scripts/check_lint.sh"
CHECK_types="na:untyped codebase or no checker adopted"
CHECK_unit="required:python3 scripts/selftest.py"
CHECK_integration="na:estimation layer parked until a spend source exists, VELDO-0278"
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
# VELDO-0259 AC2: refuse a candidate that adds personal setup. The patterns come from the installation
# (.veldo/installation.py), the check itself knows only shapes that name nobody; with no installation it
# runs those alone and says so. scripts/publish.py runs the same code over the produced tree.
CHECK_personal_setup="required:python3 scripts/check_personal_setup.py"
CHECK_deploy_dry_run="na:no automated deployment path yet"
# VELDO-0205: the mutation receipt says which results were fresh and which reused. Every case runs
# fresh since VELDO-0271, so the reused count is 0; the fields stay on the stamp and the event, and
# VELDO_GATE_FORCE_FRESH=1 still marks the run force_fresh.
VELDO_REUSE_RECEIPT=$(mktemp)
export VELDO_REUSE_RECEIPT
trap 'rm -f "$VELDO_REUSE_RECEIPT"' EXIT
CHECK_extra="required:bash scripts/check_template_sync.sh"
CHECK_mutation="required:authority mutation stage"
# Configured for the VELDO home repository (docs + plugin templates + plans):
# lint syntax-checks every shipped script, unit is the contract-system
# negative self-test, docs enforces the standing hygiene rules, generated
# keeps the index derived, extra keeps instances synced to the template canon.
#
# INTEGRATION is na (VELDO-0278). It drove a throwaway copy through the estimation layer's
# spend recorder and ran the whole suite again; with nothing recording spend it
# guarded a first use that cannot happen. Its script is parked with the estimation suites in
# scripts/parked/estimation/ (`python3 scripts/selftest.py --parked estimation` runs them).
# -----------------------------------------------------------------------------

ORDER="format lint types unit integration contract journeys ui_states accessibility \
token_lint visual_baselines build dependency_audit licenses security migration \
generated docs performance coverage packaging personal_setup deploy_dry_run extra mutation"

FAIL=0; RAN=0; NA=0; WAIVED=0; UNDECLARED=0; MUTATION_RAN=0
TODAY=$(date -u +%Y-%m-%d)
# VELDO-0216: the authority graph replaces only required catalog execution.
# No graph retains the original serial path. An invalid present graph never falls back.
VELDO_GRAPH_FIELD=""; VELDO_SCHEDULE=""; VELDO_GRAPH_REFUSED=0
if [ -e "$VELDO_AUTHORITY/scripts/gate_graph.json" ] || [ -L "$VELDO_AUTHORITY/scripts/gate_graph.json" ]; then
  VELDO_SCHEDULE=$(mktemp -d)
  trap 'rm -f "$VELDO_REUSE_RECEIPT"; rm -rf "$VELDO_SCHEDULE"' EXIT
  _veldo_stages=()
  for _veldo_name in $ORDER; do
    _veldo_var="CHECK_${_veldo_name}"; _veldo_decl="${!_veldo_var}"
    case "$_veldo_decl" in
      required:*) _veldo_cmd="${_veldo_decl#required:}" ;;
      ""|na:*|waived:*) continue ;;
      *) _veldo_cmd="$_veldo_decl" ;;
    esac
    _veldo_stages+=(--stage "$_veldo_name" "$_veldo_cmd")
  done
  if ! python3 -I -S "$VELDO_AUTHORITY/scripts/gate_schedule.py" --root "$(pwd -P)" \
      --directory "$VELDO_SCHEDULE" --receipt "$VELDO_REUSE_RECEIPT" \
      --output "$VELDO_OUT/gate-schedule.json" "${_veldo_stages[@]}"; then FAIL=1; fi
  if [ -f "$VELDO_SCHEDULE/graph-field" ]; then
    VELDO_GRAPH_FIELD=$(cat "$VELDO_SCHEDULE/graph-field")
  else
    echo 'GATE: RED (graph refused; no catalog stage completed)'
    FAIL=1; VELDO_GRAPH_REFUSED=1
    VELDO_GRAPH_FIELD=',"graph":null,"graph_refused":true'
  fi
fi
veldo_scheduled_result() {
  if [ -f "$VELDO_SCHEDULE/$1.status" ]; then
    RAN=$((RAN+1))
    if [ "$(cat "$VELDO_SCHEDULE/$1.status")" = pass ]; then echo "   $1: pass"
    else echo "   $1: FAIL"; FAIL=1; fi
  else echo "   $1: FAIL (graph refused before completion)"; FAIL=1; fi
}
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
      if [ -n "$VELDO_SCHEDULE" ]; then
        veldo_scheduled_result "$name"
        if [ "$name" = mutation ] && [ -f "$VELDO_SCHEDULE/mutation.status" ]; then MUTATION_RAN=1; fi
        continue
      fi
      echo "== ${name}"
      if [ "$name" = mutation ]; then MUTATION_RAN=1; fi
      if { if [ "$name" = mutation ]; then
        python3 -I -S "$VELDO_AUTHORITY/scripts/check_gate_mutations.py" --root "$(pwd -P)" --receipt "$VELDO_REUSE_RECEIPT"
      else veldo_candidate bash -c "$cmd"; fi; }; then
        echo "   ${name}: pass"; RAN=$((RAN+1))
      else
        echo "   ${name}: FAIL"; FAIL=1; RAN=$((RAN+1))
      fi
      ;;
    na:*)
      echo "== ${name}: na (${decl#na:})"
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
      if [ -n "$VELDO_SCHEDULE" ]; then
        veldo_scheduled_result "$name"
        if [ "$name" = mutation ] && [ -f "$VELDO_SCHEDULE/mutation.status" ]; then MUTATION_RAN=1; fi
        continue
      fi
      echo "== ${name}"
      if veldo_candidate bash -c "$decl"; then
        echo "   ${name}: pass"; RAN=$((RAN+1))
      else
        echo "   ${name}: FAIL"; FAIL=1; RAN=$((RAN+1))
      fi
      ;;
  esac
done

if [ "$VELDO_GRAPH_REFUSED" = 0 ]; then
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
  if veldo_candidate python3 .veldo/validate.py all; then
    echo "   contracts: pass"
  else
    echo "   contracts: FAIL"; FAIL=1
  fi
else
  echo "   contracts: FAIL (python3 or .veldo/validate.py unavailable - the contract system is mandatory)"
  FAIL=1
fi

echo "== shape gate (built-in: mechanizable architecture-contract rules; adoption safe, fails closed)"
if ! veldo_candidate python3 .veldo/shape_gate.py; then FAIL=1; fi

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
python3 -I -S "$VELDO_AUTHORITY/.veldo/events.py" reconcile-verdicts "$@" || \
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

fi # A refused graph reaches the normal red stamp without running more checks.

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
if [ "$VELDO_GRAPH_REFUSED" = 0 ] && _veldo_v=$(veldo_candidate python3 .veldo/version.py 2>/dev/null); then
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
# The receipt exists only when the mutation stage ran. Declared na: or waived:, it ran no case,
# so nothing was reused and there is no receipt to read; a stage that ran still needs a valid one.
if [ "$MUTATION_RAN" = 1 ]; then REUSE_SOURCE="$VELDO_REUSE_RECEIPT"; else REUSE_SOURCE=--not-run; fi
REUSE_JSON=$(python3 -I -S "$VELDO_AUTHORITY/scripts/reuse_stamp.py" "$REUSE_SOURCE" "${VELDO_GATE_FORCE_FRESH:-0}" "$COMMIT") || {
  FAIL=1; STATUS=red; EVENT=gate.failed
  # The refusal prints a RED stamp's fields in the requested mode; only a reducer that printed
  # nothing (an unreadable mode) leaves this fallback.
  if [ -z "$REUSE_JSON" ]; then
    REUSE_JSON='"force_fresh":false,"reused":{"mutation":null,"unit":0}'
  fi
}
# The mutation block (VELDO-0267): the stage's mode, cases selected and run, wall seconds, the
# selection record's digest and the nightly sweep the landing relies on. Null when the stage left
# no selection to report; a failed stage is already red through the reuse fields above.
MUTATION_FIELD=""
if [ "$MUTATION_RAN" = 1 ]; then
  MUTATION_FIELD=$(python3 -I -S "$VELDO_AUTHORITY/scripts/mutation_selection.py" --stamp-field \
    "$VELDO_REUSE_RECEIPT" "$VELDO_MUTATION_SELECTION" 2>/dev/null) || MUTATION_FIELD='"mutation":null'
  MUTATION_FIELD=",$MUTATION_FIELD"
fi
VELDO_HOST_FIELD="$VELDO_HOST_FIELD$VELDO_GRAPH_FIELD"
EVENT_LINE=$(printf '{"schema":"veldo.event/v1","type":"%s","commit":"%s","at":"%s","producer":"verify.sh","checks_run":%d,%s%s}' \
  "$EVENT" "$COMMIT" "$TS" "$RAN" "$REUSE_JSON" "$VELDO_HOST_FIELD")
veldo_write_stamp() {
  printf '{"commit":"%s","status":"%s","at":"%s","checks_run":%d,"checks_na":%d,"veldo_version":%s,"tree":%s,%s%s%s}\n' \
    "$COMMIT" "$STATUS" "$TS" "$RAN" "$NA" "$VERSION_JSON" "$TREE_JSON" "$REUSE_JSON" "$MUTATION_FIELD" \
    "$VELDO_HOST_FIELD" > "$1"
}
if [ "$VELDO_OUT" = ".veldo" ]; then
  veldo_write_stamp .veldo/last_verify
  printf '%s\n' "$EVENT_LINE" >> .veldo/events.jsonl
else
  # The sink, written only through names that are not symlinks: the stamp is renamed into place (a
  # rename replaces a link rather than following it) and the event is appended only to a regular
  # file. Any failure is RED, and nothing is written to the candidate instead.
  _veldo_written=no
  if [ ! -L "$VELDO_OUT/events.jsonl" ] && [ -f "$VELDO_OUT/events.jsonl" ] \
     && veldo_write_stamp "$VELDO_OUT/.stamp.$$" 2>/dev/null \
     && mv -f "$VELDO_OUT/.stamp.$$" "$VELDO_OUT/last_verify" 2>/dev/null \
     && printf '%s\n' "$EVENT_LINE" >> "$VELDO_OUT/events.jsonl" 2>/dev/null; then
    _veldo_written=yes
  fi
  if [ "$_veldo_written" != yes ]; then
    echo "== gate output: NOT WRITTEN - the sink refused the stamp or the gate event; this run is not trusted success"
    FAIL=1
  fi
fi

veldo_leftover_report
echo ""
echo "catalog: ${RAN} run, ${NA} not-applicable (reasons on record), ${WAIVED} waived, ${UNDECLARED} undeclared"
if [ "$FAIL" -eq 0 ]; then
  echo "GATE: GREEN (${COMMIT})"
  exit 0
else
  echo "GATE: RED (${COMMIT})"
  exit 1
fi
