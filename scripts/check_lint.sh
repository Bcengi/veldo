#!/usr/bin/env bash
# Lint: syntax-check every tracked Python and shell file, including the
# plugin templates this repository ships to other repositories.
#
# ONE INTERPRETER FOR THE PYTHON HALF (WARP-0711). This stage used to run
# `python3 -m py_compile` once per tracked Python file. Measured at 7df08a1 that
# is one process spawn per file over the whole tracked Python corpus, and
# interpreter startup was the stage's cost rather than the compiling. The same
# file set compiled inside ONE process is the same check without the startups.
#
# WHAT IS PRESERVED, each of it asserted by the WARP-0711 block of
# scripts/selftest.py rather than claimed here:
#   - the file set comes from the SAME two `git ls-files` patterns the per-file
#     loop used, and is asserted EQUAL to the set that loop iterated;
#   - a file whose compilation RAISES is named by path on its own line as
#     `   FAIL: <path>`, verbatim because something may be parsing it, AND the
#     stage carries on to the next file. The handler is the same width as
#     py_compile's, so the set of raising files that get named is the same set;
#     the selftest drives it with two shapes from OUTSIDE the syntax families
#     (deep expression nesting, an overflowed parser stack) and asserts a broken
#     file sorting AFTER them is still named. A failure that kills the process
#     outright, a signal or the OOM killer, is named by nothing, and the stage's
#     non-zero exit is what the gate reads;
#   - the stage still exits non-zero if any file fails and zero otherwise;
#   - the summary line still begins `lint: pass` or `lint: FAIL`;
#   - the compilation is the same call py_compile performs on a source file
#     (SourceFileLoader.source_to_code, which is compile with dont_inherit).
# ONE THING CHANGES ON PURPOSE, measured as a differential in the selftest: this
# stage writes NO bytecode, where `python3 -m py_compile` wrote a .pyc per file
# into a __pycache__ beside it.
#
# The shell half still runs `bash -n` once per file. That is the check itself,
# not a startup cost: measured, the whole shell half is a fifth of a second.
#
# `check_lint.sh --list` prints the file set this stage would check, one
# `<language> <path>` line per file, and checks nothing. The selftest compares
# that against the set the per-file loop iterated, which is the one way a faster
# lint stage could silently cheat: by checking less.
#
# THAT LISTING IS A DIAGNOSTIC AND IT CANNOT BE MISTAKEN FOR A CHECK. It is
# reached only by an EXPLICIT ARGUMENT and it exits NON-ZERO, printing no
# `lint:` verdict line at all. Until round 3 it was reached by an ambient
# environment variable (VELDO_LINT_LIST) and exited 0, which the round-2 review
# measured turning a tree with six planted defects GREEN through the gate's own
# wiring: the ONE fail-open surface in this stage, and a surface the per-file
# loop it replaced did not have.
#
# NO ENVIRONMENT VARIABLE THIS STAGE READS CAN MAKE IT REPORT SUCCESS, AND IT
# READS NONE. That is a property of the text of BOTH HALVES and it is asserted
# over both: the shell half is pinned line for line, the python half imports a
# closed declared set of modules and names no environment accessor, and its two
# subprocess argument vectors are pinned by shape.
#
# THAT IS NOT ENOUGH ON ITS OWN, AND ROUND 4 CLAIMED IT WAS. `git ls-files` IS
# an environment-reading subprocess: measured on the round-4 text with no
# mutation at all, `GIT_DIR=<an empty repository>/.git` and `GIT_INDEX_FILE=`
# each gave `lint: pass (0 python, 0 shell, 0.00s)` and exit 0 over a tree
# carrying eight planted defects, and `GIT_LITERAL_PATHSPECS=1` did the same by
# turning the `*.py` pattern into a literal path that matches nothing. So the
# interpreter and every child it spawns now start from `env -i PATH="$PATH"`:
# ONE variable crosses the boundary, by name, and it is the one round 2 conceded
# is outside the threat model because PATH decides which `python3` and which
# `git` run at all. Not a list of hostile git variables to unset, which is the
# same losing enumeration this stage has already been corrected for twice.
# CDPATH is closed separately on the `cd` line above, because that `cd` runs
# BEFORE the boundary and `$(dirname "$0")/..` is a relative operand a hostile
# CDPATH would otherwise redirect.
#
# WHAT REMAINS, DECLARED RATHER THAN CLAIMED AWAY: variables that act on bash
# BEFORE or WHILE it reads this file, which no text inside the file can close.
# BASH_ENV names a file bash sources before line 1, measured as a false pass.
# PATH itself is conceded above. WHAT NO LONGER REMAINS, and is recorded because
# round 4 declared it: PYTHONPATH is CLOSED by the boundary, measured, and
# PYTHONHOME never belonged in that list at all - measured, it fails CLOSED with
# exit 1 and no summary line, so declaring it was claiming a weakness that does
# not exist. An unrecognised argument also exits non-zero.
set -u
CDPATH= cd "$(dirname "$0")/.."
exec env -i PATH="$PATH" python3 - "$@" <<'PY'
"""The lint stage, in one process: the tracked Python corpus compiled here, the
tracked shell corpus handed to `bash -n` one file at a time."""
import signal
import subprocess
import sys
import time
from importlib.machinery import SourceFileLoader

# A gate stage is a unix filter and dies like one when its reader goes away: the
# per-file loop this replaced was `echo`, which takes SIGPIPE's default. Python
# installs a handler that turns the same event into a BrokenPipeError traceback,
# so the default is restored here and `check_lint.sh | head` stays quiet.
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

T0 = time.monotonic()

# The stage's DEFINITION of what it checks, unchanged from the per-file loop this
# replaced. One entry per language: (label, git ls-files pattern, checker name).
PATTERNS = (("python", "*.py"), ("shell", "*.sh"))


def tracked(pattern):
    """The tracked files matching one pattern, in git's order."""
    out = subprocess.run(["git", "ls-files", pattern], check=True,
                         capture_output=True, text=True).stdout
    return out.split()


def check_python(path):
    """Compile path IN THIS PROCESS. True on success; on failure the diagnostic
    goes to stderr, where py_compile's traceback went, and the caller names the
    path on stdout.

    source_to_code is the call py_compile performs on the source bytes it reads,
    so this is the same compilation with the .pyc write removed rather than a
    different check.

    THE HANDLER IS `Exception` BECAUSE THAT IS WHAT py_compile CATCHES
    (py_compile.compile wraps source_to_code in `except Exception as err` and
    turns it into a PyCompileError, which py_compile.main maps to a non-zero
    exit), so this mirrors the loop's width instead of enumerating the
    exceptions someone thought of. AN EARLIER VERSION OF THIS STAGE NAMED THREE
    FAMILIES - SyntaxError, ValueError, OSError - and the round-1 reviewer
    measured two classes escaping them: a RecursionError from deep expression
    nesting (`x = 1` and 9,996 `+1` terms, and an ordinary 20,000 term string
    concatenation) and a MemoryError from an overflowed parser stack. Each
    aborted the process with a traceback naming no path and left every later
    file unchecked, where the loop named the file and carried on. A narrower
    handler here is a coverage regression, which is why the width is the
    contract and not a judgement. BaseException is deliberately NOT caught:
    KeyboardInterrupt and SystemExit are not a file's fault, and py_compile
    does not catch them either."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
        SourceFileLoader("<lint>", path).source_to_code(data, path)
    except Exception as e:
        # The path is repeated here because a SyntaxError renders only the BASENAME
        # in its own message, and py_compile's traceback carried the full path.
        print("%s: %s: %s" % (path, type(e).__name__, e), file=sys.stderr, flush=True)
        return False
    return True


def check_shell(path):
    """`bash -n path`, exactly as the per-file loop ran it. bash writes its own
    diagnostic to this process's stderr; the caller names the path."""
    return subprocess.run(["bash", "-n", path]).returncode == 0


CHECKERS = {"python": check_python, "shell": check_shell}
FILES = {label: tracked(pattern) for label, pattern in PATTERNS}

# The list mode reads the SAME dict the checking loop below iterates, so what it
# prints is the file set this stage checks and not a second derivation of it. It
# is gated on an EXPLICIT ARGUMENT, which the gate never passes (verify.sh runs
# `bash scripts/check_lint.sh` with none), and it exits NON-ZERO with no `lint:`
# verdict line, because a listing has checked nothing and must not be readable as
# a pass by an exit-status consumer or by a human. LISTED is 2 to keep it
# distinguishable from 1, which means the corpus was checked and something failed.
LISTED = 2
if sys.argv[1:] == ["--list"]:
    for label, _pattern in PATTERNS:
        for path in FILES[label]:
            print("%s %s" % (label, path))
    print("lint: LISTED %s and checked NOTHING (diagnostic mode)"
          % ", ".join("%d %s" % (len(FILES[label]), label) for label, _p in PATTERNS),
          file=sys.stderr, flush=True)
    sys.exit(LISTED)
if sys.argv[1:]:
    print("usage: check_lint.sh [--list]", file=sys.stderr, flush=True)
    sys.exit(LISTED)

FAIL = 0
for label, _pattern in PATTERNS:
    check = CHECKERS[label]
    for path in FILES[label]:
        if not check(path):
            print("   FAIL: %s" % path, flush=True)
            FAIL = 1

# The counts make a silently shrinking file set visible in the output rather than
# only in the timing, and the elapsed time makes a later cost regression
# attributable. It is this process's own elapsed time, from before the file set
# is derived to after the last file is checked.
print("lint: %s (%s, %.2fs)"
      % ("pass" if FAIL == 0 else "FAIL",
         ", ".join("%d %s" % (len(FILES[label]), label) for label, _p in PATTERNS),
         time.monotonic() - T0), flush=True)
sys.exit(FAIL)
PY
