# VELDO-0176 build proof

The factory keeps each conversation's engine session and history, so a turn resumes it on any account of its
engine, after an account limit and after a restart.

Test: `python3 scripts/selftest.py --suite 130_veldo_0176_conversation_history` (new suite, registered in
scripts/suites/manifest.json, requires.json regenerated). Seventeen rows, fake engines only: the fake Claude Code
keeps its transcript under `<profile>/projects/<workspace name>/<session>.jsonl` and resumes the session `--resume`
names only when that file is there; the fake Codex keeps `<profile>/sessions/.../rollout-...-<thread>.jsonl` and
resumes the thread `exec resume <thread> -` names only when that file is there. Limits are a fake rejected
rate-limit event, the credential is a fixture subscription token, the restart is the production service run twice
over one store. No real engine, login or user unit; the suite does not need the systemd user manager.

- Before the change: `before-change-suite130.txt` (suite 130 against the base 061f8deb production code: turn 2 on
  account B starts a new session, every row red).
- After the change: `after-change-suites.txt` (130 green; 123, 127, 128, 129 green; 86 green except its two live
  rows, which are red on the base too: stale captures the lead retakes).
- Falsifiers: `mutations/` holds, per spec falsifier, the exact diff and the receipt of
  `python3 scripts/check_teeth_mutations.py --case <name>` run alone: baseline green, no-op green, mutant red on the
  named row. The driver applies each edit to a copy, so the source is restored by construction.
- Engine options: `engine-resume-evidence.txt`, read from the pinned binaries' bytes (neither was run).

## AC1: the factory keeps the session; any account resumes it

Built:
- `control_launch.Receiver`: after the engine ends (`_capture`), the session file the engine reported is taken
  out of the account profile (Claude Code's `session_file`: `projects/<cwd, [^a-zA-Z0-9] as ->/<id>.jsonl`; Codex's:
  the rollout file of the thread under `sessions/`), kept at `<conversation directory>/sessions/<engine>/<hash>.jsonl`
  mode 0600 (`control_conversation.capture`) and reported on the launch pipe (`conversation_session`).
- `control_service.ConversationLine`: the capture is bound to the turn record by `end_conversation_turn`
  (`session`: engine, session id, relative place, capture path, digest, account, dispatch). The next offer names the
  newest held session of the role's engine in the payload (`resume`, `held`).
- Receiver before acceptance (`_held`): the turn record and the capture are read back and the digest compared;
  just before the spawn (`_place`) the bytes are placed at the same relative place in the chosen account's profile,
  and the engine's resume option is appended (`resume_argv`: Claude Code `--resume <id>`, Codex
  `resume <thread> -` after `exec`'s options). Both options and the input bounds are recorded in the pinned versions'
  qualification records (engine/runtime and .veldo/runtime); a version without them is refused
  `missing_evidence:engine_resume:<version>`. The meter's `resumes` is the payload's session, so it charges the
  difference.
- An engine reporting another session id than the placed one is stopped by name (`take` in `_reap`, cause
  `conversation_resume`); its turn ends `binding_mismatch:conversation_resume`, and its session is not bound.

Rows: `AC1/any-account` (turn 1 on account-claude_code-1, turn 2 on account-claude_code-2, same session id, the
engine on B remembers turn 1, argv carries `--resume <id>`), `AC1/capture-kept` (0600 under the conversation,
digest bound, relative place, nothing left in any profile), `AC1/resume-qualified` (meter charged `difference`,
qualification records, unqualified version refused), `AC1/resume-mismatch`, `AC1/observability`.

Falsifier: skip placing the held session (`resume176-not-placed`): `AC1/any-account` fails on the new session id
turn 2 reports (killed; AC1 rows red).

## AC2: a limit, every account limited, a restart

Built:
- A run whose invocation ended `account_limit`: its capture is taken as for any turn; `ConversationLine.limited`
  makes VELDO-0160 AC3's decision over its execution record and returns the turn to waiting with its capture
  (`wait_conversation_turn` now also from an exited limited dispatch; `limited`, `limits` on the record). The next
  pass dispatches the same turn under a new dispatch identity; the pool passes over the limited account; the
  payload resumes the capture and carries `notice` ("The previous run of this turn stopped at an account limit;
  continue from where it stopped."). An `ask` decision opens VELDO-0160's re-run-or-stop question first.
- Every account of the engine at its limit (`no_account*` and every active account blocking): `engine_limit` opens
  one decision request per turn in the decision inbox (VELDO-0064; choices `wait`, `move`; the reset named) to the
  conversation's owner, noted on the turn. Nothing moves before his answer. `wait` leaves the turn waiting for the
  reset; `move` sends `set_conversation_role` as his command to `assistant_codex` (from Claude Code) or `assistant`
  (from Codex), and the turn is offered at once under AC3.
- Restart: `recover` already ends a running turn `outcome_unknown`; `told` now opens an acknowledgement request to
  the owner saying so and that his next message resumes from the last capture, and notes it on the turn.

Rows: `AC2/continues-after-a-limit` (two attempts, new dispatch id, other account, same session id resumed with
the partial work, notice, decision rerun), `AC2/ask` (question in the inbox, no Codex turn, role unchanged, for
both conversations), `AC2/wait`, `AC2/move`, `AC2/running-at-restart` (a new factory loop over the store while the
turn runs: outcome_unknown, acknowledgement opened, the next message resumes the last capture), `AC2/restart` (the
production service restarted between two turns; turn 2 resumes turn 1's session).

Falsifiers: discard the capture of a limited turn (`limit176-capture-discarded`): the continues row fails on a
fresh session (killed); move without asking (`ask176-moved-unasked`): the ask row fails on a Codex turn with no
settled answer (killed).

## AC3: an engine change starts from the factory's history

Built:
- The engine changes only by the role: a role on the same engine resumes its held session; a role on the other
  engine with no held session there gets `history` in the payload, and the receiver renders it once the engine is
  bound (`_conversation_start`): `control_conversation.history` reads each earlier turn's execution records as their
  exits committed them, `turn_from_record` takes the owner's message (the receiver's new `turn_input` wrapper line),
  each tool call with input and result, and the reply, all from the redacted payloads, never the held session;
  `render` keeps the newest whole turns that fit the engine's qualified bound (`history_bound`) after one line
  naming how many were left out. A history beyond the bound is shortened, never refused.
- The earlier engine's held session stays, so a change back resumes it. A held session whose digest differs is
  refused `binding_mismatch:conversation_session` before acceptance, never replaced by a rendering.

Rows: `AC3/same-engine`, `AC3/redaction` (the held Claude Code session holds the token; the Codex first input is
the rendering with `[REDACTED` in its place and no token), `AC3/long-history` (history three times the fixture
bound of 2000 characters; the Codex turn completed from the newest two whole turns with "left out: 6"),
`AC3/change-back`, `AC3/digest-refused` (a tampered capture: the turn is refused by name, nothing ran, no
rendering), `AC3/observability`.

Falsifiers: build the rendering from the held session (`render176-from-held-session`): the redaction row fails on
the credential value (killed); refuse a history beyond the bound (`render176-long-refused`): the long-history row
fails on the turn that never ran (killed).

## Observability

Logs: `session_capture` and `turn_start` observations (conversation, turn, engine, session id, account, digest),
receiver events `conversation_session_placed`, `conversation_session` (the session id the engine reported),
`conversation_history` (turn count, left out, digest), `conversation_session_refused`, and `turn_question`
(question and answer). Metrics: `Conversations.status()['sessions']` (resumed, rendered, rendered_shortened,
captures, questions by answer, session_mismatch, resume_mismatch). Traces: each turn's `starts` names the held
session it resumed and `captures` the capture it produced, with dispatch and account.

Open items: `OPEN.md`.
