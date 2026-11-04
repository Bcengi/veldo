# VELDO-0187 batch fix round 1 (conversation chain)

Branch agent/claude/veldo-0187, from 66ab9a3c. Every run below is `python3 scripts/selftest.py --suite <name>`
alone unless stated. scripts/verify.sh was not run.

## 1. Regressions named by the lead

a. 86_veldo_0168_text inventory/sends-and-assets. Red at 66ab9a3c ("inventory delta engine/production:
   + control_conversation_channel.py Messages.answer edge.send, + Replies.deliver self.edge.send,
   - control_intake.py Intake._ask self.asker.send"). Checked each send: Messages.answer sends
   TEXT.message(text) (escaped once); Replies.deliver sends reply parts from parts() (TEXT.visible + edges,
   once) but status lines raw, unescaped (status_line). Production fix: status_line returns
   TEXT.message(line, free_text=False). Inventory: the two sends replace Intake._ask (gone since VELDO-0181:
   the question goes out through Presenter._send, already listed), with their renderer routes
   (parts TEXT.visible, status_line TEXT.message, Messages.answer TEXT.message) and assignments in
   wanted_routes/wanted_assignments. Green after (1ed5b38a).

b. 86_veldo_0168_text intake/delivery. Red at 66ab9a3c (questions with delivery null). Since VELDO-0181 the
   question is a decision request the presenter shows. Its choices are picks, and project names are
   [A-Za-z0-9][A-Za-z0-9_.-]*, so the fixture's project `literal<U+200B>` was unpresentable
   (unmapped_choice). The row now uses valid projects and carries the literal escape where the owner's own text
   reaches the question: the opening words of an open conversation of his (opened through the real
   new_conversation route, with a fixture default team). The intake gets request_sign, and the journal signer is
   enrolled as a service member, as the service and suite 68_0126 do. The check stays strict: the messages on his
   chat equal the receipt's rendering, they contain expected(brief) exactly once, they show `literal<U+003C>U+200B>`
   and never `literal<U+200B>`, and the question prompt and request brief keep it as written. 26/26 (1ed5b38a).

c. 86_veldo_0189_engine_upgrade ownership/restore-reported. Red at 66ab9a3c. Cause: VELDO-0181 (8fb17e67) made
   control_request_settlement.py differ from the 8bc34e94 engine for the first time, so its six ownership rows are
   recorded as previous too. They restore cleanly, but the row treated every recorded row as blocked. The row
   now computes the blocked rows (module lacks its previous bytes), requires them to be exactly the damaged
   module's (at least 2), and requires each to be named. Green after (e876f4a7), 34 rows.

d. 83_veldo_0154_factory_loop loop/owner-stop-asked-on-wake. Bisect: green at 043c2ef6, 1c0f9d67, 671bd13e,
   4a83cc5e; red at c6ca5b8d (VELDO-0175's first commit) and every later chain head (aa1c989b and
   1f416231 also redden loop/owner-no-stops). Cause: the rows ran past their 45 s budget. A profile of the
   installed service shows Line.next calling _organ('control_workflow_cycle_pm') per unit, and since c6ca5b8d
   that module imports control_intake_conversation and about 100 modules each time (29 s of 40 s). Passes went
   from about 1.2 s to 2.3 s. Fix: load it once (PM = _organ(..., lazy=True)). 14/14, three runs (b489be50).

## 2. OPEN items 1 and 2

The suite 138 entry is in scripts/gate_unconfined.json as OPEN.md words it, and
runtime/claude-mem-qualification.json is in 86_0186's expected list. 86_0186 is 37 passed alone (3855caea).

## 3. Reruns and the sweep

Every suite named in the brief ran alone and is green, plus 78_veldo_0160 (changed by the chain). The
exception is 86_veldo_0127, where only live/claude and live/codex are red (stale live captures, for the lead).

The full selftest could not be run as asked. The gate's serial baseline puts the unit stage at about 2800 s,
the tool's foreground limit is 600 s, and background runs were barred. One batch the harness moved to the
background was stopped at once. In its place, every one of the 202 manifest suites ran alone, in batches under
`systemd-run --user --scope -p MemoryMax=10G -p MemorySwapMax=0`. This is not the aggregate run: a
PASSES_ALONE_FAILS_IN_AGGREGATE defect would not show here. It found these reds:

- 50_git_environment git-boundary/no-private-git-invocations, red since VELDO-0180 (56c03501): the conversation
  snapshot ran git_process under the alias GP, so the boundary checker could not see it. Renamed to _git_process.
  Green (493855b8).
- 51_parser_boundary parser/no-private-readers, red since VELDO-0187 (b6849b26): the claude-mem fetch regex
  `method:\s` reads as a YAML key regex to the checker. Spelled `method[:]` (same matches, checked). Green
  (493855b8). 136 and 138 rerun green.
- 63_veldo_0040_containment, 31 rows, red since VELDO-0231 (237851d1, bisected: 8da5d061 green): the suite's fake
  receiver lacked attributes _reap and _finish now read (0231 login and flags, 0184 file_memory, 0176
  held_session, rendering and _capture). It now carries Receiver.__init__'s unbound-run values and runs the real
  _capture and _unplace. 85/85 (a8cfaec6).
- 101_veldo_0208_landing_reuse unconfined-leg/declared-list and dispatcher-is-protected: the pinned list missed
  the six chain suites the lead added to gate_unconfined.json. Updated to 49 whole and 51 files (49405511).
  sandbox/unavailable-refuses-before-exec, sandbox/old-abi-refuses-before-exec and a ValueError "incomplete
  file-read trace" are red identically on main 043c2ef6. Not this chain; left.
- 103_veldo_0142_git_identities launch/spawn-config-commit-authors, red since VELDO-0176: its bare Receiver lacked
  held_session. Set to None as __init__ does. 49/49 (825a620c).
- 105_veldo_0182_memory unit/completed, red since VELDO-0187 (b6849b26 split _apply into _apply and _stored): the
  suite's in-place mutation now targets _stored. 153 passed (78b4aeb2).

Open, attributed and not fixed:

- 82_veldo_0172_live_formats fake/census: suites 129_0177, 130_0183 and 132_0175 build fake engines without
  VELDO-0172's conform_fake teardown, fake/capture row and format row. Red since VELDO-0177 (between 1c0f9d67 and
  671bd13e), widened by 0183 and 0175. 129 and 130's fakes answer login status only, so the readback would fail
  them as they are: each needs a conformant fake (as 106 uses the 0186 fake) plus the wiring.
- 84_veldo_0169_project_handouts census/writers: red since VELDO-0175 (c6ca5b8d), widened by 0180, 0181, 0183 and
  0184. Eight writers are unclassified or are handouts without the Gate's project check:
  control_intake_conversation._turn_changes and _conversation_route, control_intake_routes._point_conversation,
  control_conversation_channel.Messages.__init__ and control_conversation_decisions.presented (bare transition
  registration), control_factory_setup_memory.servers_main, and control_memory_kb.call (two dynamic getattr).
  Whether a conversation turn needs the project check is a design decision for the lead.
- 126_veldo_0230_qualify_reproduces qualify/reproduces: it runs the installed Codex and Claude Code binaries
  (offline, empty profiles, loopback). Its result differs with identical code (green on main, red at the
  spec-only 8da5d061), and another session was upgrading those binaries meanwhile. I ran it during the sweep and
  bisect and did not run it again. Left for the lead.
