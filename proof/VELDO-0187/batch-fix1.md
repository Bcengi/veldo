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

# Round 2 (the two items left open above, by the lead's rulings)

Every suite run below is `python3 scripts/selftest.py --suite <name>` alone; every mutation case is
`python3 scripts/check_gate_mutations.py --case <name>` alone (the gate's driver, so suites on
gate_unconfined.json run in its unconfined leg), each under `systemd-run --user --scope -p MemoryMax=10G
-p MemorySwapMax=0`. scripts/verify.sh and suite 126 were not run. No requirement was added.

## 1. 82_veldo_0172_live_formats fake/census

Suites 129_0177 and 130_0183 build their fakes through VELDO-0171's installed-host fixture, as 106 does. Each
fake is now built with fake_formats.embed and prints each CLI's stream (initialize answer, init, assistant,
result; thread, turn, agent message, turn completed) only when called with the read-back's fixture argument
(`--veldo-0172-format-readback`, passed by the suite's own `readback_args`). Every other call behaves as
before: login status as before, 130's extraction as before, anything else still exits 2, so "setup launches
no run" is as strict as it was. Each teardown calls compare_formats.conform_fake(locals(), '<short name>')
in a `finally` over the installed fake (h['engines186']['fake']), keeps a `format/fake-lines` row and reports
`VELDO-0172 fake/capture:<short name>` (4173f6b0, e71321cb).

Suite 132_0175 drives its PM run on a Claude Code fake of its own, as suite 93 does. The fake now requires the
initialize request (as 93's does), and the suite's outer `finally` reads it back with conform_fake before the
fake's directory is removed (Claude Code only: the suite builds no Codex executable, so `fake_engine('codex')`
gives none), with the same two rows (660e34e5).

82_0172: 4 passed, census 23 suites, no problem. 129: 6 passed; 130_0183: 19 passed; 132: 21 passed.

## 2. 84_veldo_0169_project_handouts census/writers

The lead's ruling, as built (9c91ef66):

- The census reads a `transition` reached through a binding of control_conversation (`CV = _organ(...)`,
  resolved from the syntax tree) as that organ's. The organ now declares PROJECT_OPERATIONS = (ATTACH, POINT).
- Project handouts. Attach (clones a project) and VELDO-0180's pointing (moves work into a project) now ask the
  Gate's one project check: control_eligibility.Gate.project_named_problems, the same _project_problems for
  a project named directly, through control_conversation.project_problems, inside the organ's write
  transaction after the owner's authority. A new project's conversion must find exactly that the project is
  not in the store yet (else stale_subject:project_exists). Intake's conversion plan
  (Conversing._point_plan, moved from Routes._point_conversation so the census can resolve its CV) asks the
  check first and refuses an existing project that fails it. The census requires the check before every
  organ return a project operation reaches and before every project-operation call or parameters build
  outside the organ.
- Conversation-scoped. A call or registration whose operations are all other organ operations is classified
  conversation-scoped, citing VELDO-0174 and VELDO-0181. It is not an unchecked exemption: the census verifies
  that `_member` (VELDO-0174's owner and service gate) runs before every organ return an owner operation
  reaches, and an unresolved operation is refused. A registration counts only under the organ's own OPERATION
  and is classified by the builds of the class or function that registers it.
- Memory and host. control_memory_kb.call looks up only FUNCTIONS (a fixed table of the kb functions, refusing
  any other name), and servers_main reads only KB_INPUTS (refusing a TOOLS field outside it). Their getattr
  calls now resolve and are recorded memory-scoped and host-scoped with the reason. The census's
  NON_PROJECT_SCOPES table only labels resolved accesses, and an entry with no resolved access is refused as
  stale.
- Rows: census/writers now finds each class (the two handouts at the organ, intake's pointing handout, four
  conversation-scoped writers, the memory and host records) and checks that every conversation writer is
  classified. census/planted adds eight falsifiers: the pointing without the check (intake and organ), an
  attach without it, the owner gate dropped, an unresolved operation, a POINT build beside a registration, a
  registration under another key, and kb's free getattr. Each is refused at its own site.

84_0169: 27 passed (census: 7 handouts, 4 conversation-scoped, 1 memory, 1 host, no failure).

## 3. Reruns

Suites, each alone, all green: 82_0172 4, 84_0169 27, 106 20, 123 38, 128 15, 129 6, 130_0176 17,
130_0183 19, 131_0175 16, 131_0184 16, 132 21, 133 16, 136 21, 137 19, 138 13, 68_0126 18, 68_0134 27,
68_0136 7, 68_0137 2. Also, for the modules changed: 86_0189 34, 93_0152 24, 71_0076 32, 60_0052 54,
83_0154 14, 50 4, 51 25, 52 12, 86_0168 26, 125 7, 53_0123 14.

Mutation cases, each alone through the gate's driver, all `passed` (baseline and no-op green, mutant
rejected): 0175 9/9, 0177 7/7, 0180 4/4, 0181 6/6, 0183 7/7, 0187 3/3. Also, because their suites or modules
changed: 0169 22/22, 0172 9/9, 0174 8/8. Note: check_teeth_mutations.py run directly gives
`invalid_baseline` for the 0187 cases, because it confines suite 138, which is on gate_unconfined.json. Through
check_gate_mutations.py they pass. One batch was moved to the background by the harness at its 600 s limit
and stopped at once. The case it was running (setup183-no-servers-step) was rerun alone and passed.

Open: nothing from these two items. 126 remains with the lead.
