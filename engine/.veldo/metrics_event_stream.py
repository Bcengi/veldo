#!/usr/bin/env python3
"""VELDO metrics: THE LOOP DERIVATION'S READ OF THE RECORDED EVENT STREAM (WARP-1210, round 10).

.veldo/events.jsonl is the ONE recorded artifact the LOOP measures are derived
from, and this module is the whole of how they read it: what a recorded LINE has
to be to become an event, and - the half that did not exist before round 10 -
WHAT IS SAID WHEN THE ARTIFACT ITSELF CANNOT BE READ.

THE DEFECT CLASS THIS MODULE EXISTS TO CLOSE, named from the HARM rather than
from the mechanism of the instance that was reported: AN EXCEPTION RAISED WHILE
READING A RECORDED ARTIFACT, WHICH NO HANDLER NAMES, EXITS ALL FOUR SURFACES
PRINTING NOTHING. Rounds 6, 8 and 9 each closed a member and each named the
class after its own mechanism (a byte no codec accepts, an unbounded directory
walk, 20000 nested JSON arrays), so each sweep missed the siblings that shared
the harm and not the mechanism. TWO WERE STILL LIVE AT ROUND 10, and both are
visible from this module - one is a defect AT the read below, the other is the
missing EXCEPTION CLASS this module declares for every read in the pass (its
other reachable instance is a sparse RECEIPT FILE, which enters through
.veldo/metrics_read_accounting.py's _record_shortfall and is closed there):

  * THE READ SAT INSIDE NO TRY AT ALL. A mode-000 .veldo/events.jsonl exited all
    four surfaces 1 with PermissionError and ZERO bytes of stdout, and a
    DIRECTORY at that path with IsADirectoryError - true at rounds 7, 8 and 9,
    while the SUPPORT pass's own reader of the same file already had the named
    stand-down for the identical shape ten lines away.
  * MEMORY ERROR WAS NAMED BY NO HANDLER ANYWHERE IN THE PASS. An event stream
    larger than the address space available took the same four surfaces down,
    and that is not an exotic input: this file is an APPEND-ONLY log the engine
    writes on EVERY gate run, with no rotation and no size bound anywhere, read
    WHOLE-FILE IN ONE ALLOCATION here and once more by the support pass. A
    sparse file (one truncate, ZERO bytes on disk) reproduces it in a second
    under the address-space ceiling a CI container is.

WHY IT IS ITS OWN MODULE, and this is the honest reason rather than a tidy one:
the read was four lines inside .veldo/metrics.py's load(), and that module stood
at 399 lines of its DECLARED 400. A guard needs a try, a try needs lines, and a
bound may not be relaxed - so the choice was to compress the declarations around
it (the wrong answer to a bound, which round 8 said in these words when it split
the DECLARED SKIP RULE out of the accounted read) or to split at a seam that is
real. The seam is the one the support pass has had since round 5: THE READ of a
recorded artifact is one job, THE MEASURES over it are another. metrics.py now
derives and renders; the read of its one artifact is declared here, where there
is room to say what it does when that artifact will not be read.

WHAT IT SAYS, and it is never an unexplained zero. An ABSENT stream is COMPLETE
AND EMPTY and carries NO shortfall, because a repository that has never run the
gate has no stream and that must stay adoption-safe. A stream that EXISTS and
cannot be read returns NO EVENT AND A NAMED SHORTFALL: one sentence carrying the
path, the exception class and its message, which .veldo/metrics.py prints ABOVE
the loop measures (and in --json) and .veldo/dashboard.py renders on both of its
surfaces. PRESENCE IS DECIDED BY os.lstat, the same primitive the accounted read
uses and for the same measured reason: exists() and is_dir() FOLLOW the link and
swallow the error, so a symlink LOOP and a DANGLING symlink answered ABSENT
while the directory entry was plainly there. Under lstat they are PRESENT and
unreadable, which is what the support pass has always reported them as - so the
two derivations now say the same thing about the same artifact in the same run,
each in its own words.

PRESENCE IS NOT ENOUGH, WHICH ROUND 10 GOT WRONG BY HALF: it adopted the support
reader's PRESENCE primitive and not its KIND TEST, so a FIFO here was PRESENT,
fell through to the read and BLOCKED FOREVER - every surface wrote nothing, exited
nothing and held the terminal until killed. A BLOCKING OPEN RAISES NOTHING, so no
handler and no gate rule keyed on exceptions can reach it, and a hang is worse than
a crash, so the surface tests run under a TIMEOUT. The predicate is RESTATED here
because the declared dependency direction is SUPPORT -> LOOP: this module loads
nothing, and a gate differential proves both implementations answer identically.

THE CODEC IS DECLARED HERE RATHER THAN INHERITED FROM THE ENVIRONMENT, which the
round-7 review measured as the cost of the byte guard below: read_text() with no
encoding decodes through the LOCALE's codec, so ONE valid-UTF-8 non-ASCII
character in a recorded line made this reader skip that line under LC_ALL=C and
keep it under C.UTF-8 - the SAME BYTES yielding events_total 2 with a gate pass
rate of 1.0 on one machine and 3 with 0.667 on the next, silently. A recorded
artifact has ONE encoding, which the writer beside this reader fixes (json.dumps
escapes every non-ASCII character, so the engine's own appends are ASCII, a
subset of UTF-8); naming it makes a LOOP MEASURE a property of the bytes rather
than of the operator's environment.

Reads one recorded file and writes nothing: no live system (NG1), no process,
thread or timer (NG3).
"""
import json
import os
import stat
from pathlib import Path

# THE EXCEPTION CLASSES A READ OF A RECORDED ARTIFACT MUST NAME, declared ONCE and named identically at
# every read of an artifact in this pass, so the rule is mechanical rather than a judgment per site:
#   OSError         the read itself failing - permission, a directory at the path, a link that does not
#                   resolve, an I/O error. FileNotFoundError is an OSError, which is why ABSENCE is decided
#                   BEFORE the read rather than inside this tuple.
#   ValueError      the DECODE failing: read_text() raises UnicodeDecodeError - a ValueError, never an
#                   OSError - on a byte the declared codec cannot decode (R5-B2), and a path the platform
#                   refuses outright (an embedded NUL) raises it too.
#   RecursionError  a RuntimeError, so NEITHER of the two above catches it: json.loads recurses once per
#                   nesting level, and 20000 nested arrays in a recorded artifact raised it past every
#                   handler in the pass at round 8 (R8-B1's class, second member).
#   MemoryError     the artifact being larger than the memory the process may have. It appeared ZERO times
#                   in this repository before round 10, so it was not even a declared residual, and it is
#                   the exception an UNROTATED APPEND-ONLY LOG read whole-file in one allocation actually
#                   produces (R9-B1).
# KEYBOARDINTERRUPT AND SYSTEMEXIT ARE DELIBERATELY NOT IN THIS SET, and saying so is the point rather than
# leaving it to be inferred: KeyboardInterrupt and SystemExit are BaseExceptions rather than Exceptions, an
# operator's Ctrl-C and a caller's exit are not properties of the artifact, and a read that swallowed either
# would turn a deliberate stop into a stood-down section. They MUST propagate, so no handler anywhere in this
# pass names KeyboardInterrupt, SystemExit or BaseException.
ARTIFACT_READ_ERRORS = (OSError, ValueError, RecursionError, MemoryError)

# THE ONE SENTENCE a surface prints when the artifact exists and will not be read. It carries the PATH (so
# an operator knows which file), the exception CLASS (so they know which kind of failure) and its message,
# and it says what the measures below it are - because a zero nobody explained is the defect this pass
# exists to prevent, and the same zero with the artifact named beside it is a diagnosis.
STREAM_UNREADABLE = ("THE RECORDED EVENT STREAM AT %s EXISTS AND COULD NOT BE READ (%s: %s), so every "
                     "measure below is derived from NO recorded line at all rather than from a shorter "
                     "history: this is an unread artifact and never an empty one")
# THE SECOND SENTENCE, for the kind that RAISES NOTHING: the same fact, plus what a wedge cannot say.
STREAM_UNOPENABLE = ("THE RECORDED EVENT STREAM AT %s EXISTS AND COULD NOT BE READ: the entry is NEITHER A "
                     "REGULAR FILE NOR A DIRECTORY (st_mode %s), so nothing here OPENED it - such a read "
                     "BLOCKS until a writer appears rather than raising, which no exception name can catch "
                     "and which exits every surface with nothing printed at all. Every measure below is "
                     "derived from NO recorded line at all rather than from a shorter history: this is an "
                     "unread artifact and never an empty one")


def read_stream(path):
    """(the RECORDED LINES of the stream, the SHORTFALL naming the artifact when there are none because it
    could not be read).

    ABSENT is COMPLETE AND EMPTY: no lines, NO shortfall, which is the adoption-safe answer a repository
    that has never run the gate has to get. Everything else falls through to the KIND TEST and then to the
    read, which NAMES whatever it raises rather than letting it out - the whole of R9-B1(b). A DIRECTORY and
    an entry that cannot be RESOLVED are deliberately NOT refused by the kind test: each RAISES on the read
    and is NAMED with its message. Presence is decided by os.lstat and
    absence by FileNotFoundError alone, so an entry that is plainly there and cannot be stat'ed (an
    unreadable parent directory, a path the platform refuses) is PRESENT and is named by the read below,
    never reported as an absent stream."""
    try:
        os.lstat(str(path))
    except FileNotFoundError:
        return [], None
    except ARTIFACT_READ_ERRORS:
        # PRESENT and not even inspectable. Not named here: the read below raises the same class and names
        # it with its message, so there is ONE sentence for one artifact rather than two that can disagree.
        pass
    try:
        mode = os.stat(str(path)).st_mode
    except ARTIFACT_READ_ERRORS:
        mode = None   # not RESOLVABLE at all: the read below raises the same class and NAMES it
    if mode is not None and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
        return [], STREAM_UNOPENABLE % (path, oct(stat.S_IFMT(mode)))
    try:
        return Path(path).read_text(encoding="utf-8", errors="surrogateescape").splitlines(), None
    except ARTIFACT_READ_ERRORS as exc:
        return [], STREAM_UNREADABLE % (path, type(exc).__name__, exc)


def load_stream(path):
    """(every RECORDED event of the stream, the SHORTFALL) - one line at a time, SKIPPING any line this
    reader cannot use, and NAMING the artifact when the stream itself could not be read.

    FOUR SKIPS, PER LINE, counted from this function's own AST rather than claimed: a blank line, a byte no
    UTF-8 decoder accepts, a line that does not parse, and a line that PARSES TO SOMETHING THAT IS NOT A
    RECORD. Each costs its own `continue`, so no number a stream already yielded can move. This reader has
    always skipped a line it cannot parse (a torn write, a half-flushed append); the SUPPORT pass reads the
    same file under the OPPOSITE rule and stands its own section down instead, because a stream read in PART
    is not a shorter history. Two derivations, two rules, and both are declared rather than left to be
    discovered - and at the ARTIFACT level, where PART of the stream is none of it, they now agree: the
    shortfall this returns is the loop derivation's own version of that stand-down.

    A LINE WHOSE BYTES ARE NOT VALID UTF-8 IS SKIPPED EXACTLY AS AN UNPARSEABLE LINE IS (WARP-0108's read
    decoded the whole file STRICTLY, so one such byte raised UnicodeDecodeError out of every surface):
    surrogateescape carries the byte through LOSSLESSLY and the strict re-encode below is what detects it,
    so the split and the parse of every line that does decode are exactly what they were. A LINE THAT PARSES
    AND IS NOT A RECORD is skipped for the reason the support pass already gave (_record_shortfall): `[1, 2]`
    on its own line reached compute() as a list and exited all four surfaces 1 with AttributeError, so
    is-this-a-record now has ONE answer on both sides of the stream."""
    lines, shortfall = read_stream(path)
    events = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            line.encode("utf-8")
        except ValueError:
            # THE BYTE NO UTF-8 DECODER ACCEPTED, skipped as its own line rather than raised:
            # surrogateescape maps it to a lone surrogate, which is exactly what a strict encode refuses.
            continue
        try:
            record = json.loads(line)
        except Exception:
            # Exception rather than the two obvious names, and it is load-bearing: json.loads RECURSES once
            # per nesting level, so a deeply nested recorded line raises RecursionError here - a
            # RuntimeError that (OSError, ValueError) would let past, which is R8-B1's class at this site.
            continue
        if not isinstance(record, dict):
            continue
        events.append(record)
    return events, shortfall
