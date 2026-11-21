# VELDO-0176 open items

## 1. RESOLVED by the lead (footprint widened, qualify.py writes resume and history_bound): .veldo/qualify.py (and its synced copy engine/.veldo/qualify.py)

AC1 records the resume option, and AC3 the input bound, in each engine's qualification record for the pinned
version. Both records are in the footprint and now carry them. The Codex record is written by
`control_engine_codex.qualification()`, which now includes `resume` and `history_bound`, so `qualify.py` reproduces
it unchanged. The Claude Code version entry is assembled inside `qualify.py` (`claude_record`), which is not in the
footprint, so a fresh `python3 .veldo/qualify.py` would write the entry without the two keys and suite
126_veldo_0230_qualify_reproduces would find the shipped record different. The one change needed, in
`claude_record` of `.veldo/qualify.py` and `engine/.veldo/qualify.py`, is to add to the `entry = dict(...)` call:

    resume=C.RESUME, history_bound=C.HISTORY_BOUND,

(`C` is the loaded control_engine_claude; the shipped JSON was written from exactly these constants.) Suites 125
and 126 run the real binaries, so this build did not run them.

## 2. Presentation of the conversation's questions (not a missing path; for the reviewer)

The wait-or-move question, VELDO-0160's re-run-or-stop question for a conversation turn, and the restart
acknowledgement are opened in the existing decision inbox (control_assignment, VELDO-0064) under the conversation's
coordinate (`conversation:<id>` in place of a repository), owner and scope the conversation owner's, and settled by
his signed answer there. Presenting a conversation's decisions on the chat he wrote from and in the decisions
screen is VELDO-0181 AC1, which lists this decision and is not built yet; suite 130 answers through the inbox.

## 3. Unconfined list

Suite 130 does not need the systemd user manager: nothing to add to gate_unconfined.json.

## 4. Mutation stage note

Each of the five cases ran alone with status passed: baseline and no-op green, and `rejected=1`, the stage's count
of mutants the suite rejected (killed), with the mutant red on its named row.
