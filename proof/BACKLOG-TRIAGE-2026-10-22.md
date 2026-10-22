# Backlog triage, 2026-10-22

Read-only triage of the 79 branches `git branch --no-merged main` lists at main d49581b4.
Grouped by ticket. "Behind" and "merges" are measured against main d49581b4 with
`git merge-tree --write-tree`. "Spec moved" compares the ticket's spec on main between the
branch's merge base and main. Review verdicts are what the branches' proof files record; no
branch carries a reviewer's verdict file, so "last verdict" is the implementer's own status
line, quoted, and the owner's Telegram findings are not in the tree. WARP-1712 is being worked
on elsewhere and was skipped (three branches: agent/codex/warp-integration-evidence ce66a1f2,
agent/claude/fixcheck-warp-1712, agent/claude/review-warp-1712). gh-pages is the site, not a
ticket.

This sandbox denies AF_UNIX sockets (bind returns EPERM), which is the same blocker the batch 2
rounds recorded. Live captures were not run.

## Table, ordered by what can land soonest

| # | Ticket | Newest candidate | Last recorded status (branch proof) | Spec moved on main | Behind / merges | Next action |
|---|---|---|---|---|---|---|
| 1 | VELDO-0174 conversations | agent/codex/veldo-0174-b2 9d82fcf8 (= review-v0174c); older review-v0174b, review-v0174, review-r0174, seed/veldo-0174-b2, agent/codex/veldo-0174 | proof/VELDO-0174/scope-review-fix.json:5 "BLOCKED: both production restart rows require a host permitting AF_UNIX sockets"; README.md:9 "Suite 107 has 34 passing ticket rows; its two restart rows remain blocked". Last two commits 2cd6c93b, 9d82fcf8 have no evidence record. Suite 105 memory-backfill failure (batch-2.md:80-85) never rerun. No protected paths. | no | 13 / clean | CODE/TEST here: merge main, rerun 107_veldo_0174_conversations and 105_veldo_0182_memory on the merged tree, fix regressions, record. Then host: the two restart rows and suite 86 on a host with a user service manager; reviewer runs the full gate. |
| 2 | VELDO-0153 identity push | agent/codex/veldo-0153-b2 32c7ee2c (= review-v0153c); older review-v0153, review-r0153, seed/veldo-0153-b2, veldo-0153-host, agent/codex/veldo-0153 | review-corrections.md:7-8 "Verification remains BLOCKED on consumer and fenced integration execution; no full gate was run"; README.md:65 "Consumer verification remains red" (26 consumer suites, AF_UNIX); manifest.json AC1-AC3 not_run; host_check.py live GitHub qualification not run. Main c416bf44 and f9e9e17d dispositioned the fixture token lines by digest; the branch's lines changed since (identity_wire.py:59, suite 107:343), so the disposition may no longer cover them. No protected paths. | no | 13 / clean | CODE/TEST here: merge main, rerun 107_veldo_0153_identity_push and 108_veldo_0153_executor_profile, run scripts/secret_inventory.py on the merged tree (done 2026-10-22: 0 outstanding). Then host with AF_UNIX: suite 58 (57 rows) and the 26 consumers; live GitHub qualification. OWNER: approval of the four consumers that run prohibited mutation drivers (README.md:56-57); critical risk needs two reviews. |
| 3 | VELDO-0124 macOS worker profile | agent/codex/veldo-0124-b2 412b9c39 (= review-r0124); older seed/veldo-0124-b2, veldo-0124-host, agent/codex/veldo-0124b, agent/codex/veldo-0124 | ROUND-batch2.md:3 "BLOCKED on current native qualification, not shipped"; Linux suites 103 and 104 green (54 and 33 rows, 0 failed); SSH to the Mac timed out (host-access.exit 255). No protected paths. | no | 13 / clean | HOST: restore SSH to the Mac and run the native rows and falsifiers (ROUND-batch2.md:151-158) with both real engines. OWNER inputs listed in README.md:312-340 (Codex install and path, pinned binaries, logged-in profiles, consent for six model calls, account and project roots). Nothing to code here. |
| 4 | VELDO-0125 Mac relay routing | intcand-0125 e60d82e8 (= agent/codex/veldo-0125-b2 82074cf3 + main at f21e2a00); older review-fcv0125s/r/q (rounds 21, 20, 19), intcand-0125o/n, review-v0125..p, seed/veldo-0125-b2, veldo-0125-host, agent/codex/veldo-0125b, agent/codex/veldo-0125 | batch2/ROUND.md:3 "BLOCKED on current-tree host observations and the VELDO-0127 live recapture"; b2-round22/README.md:94-96 (round 22, 2026-10-17) "does not claim an audit code fix or canonical gate pass". Gate v0125q red only because the 0127 captures are digest-bound to .veldo/control_launch.py (b2-round18/README.md:49-62). Selected suites 103-106 and 15 pass. No protected paths. Carries an OLDER copy of the 0124 runner: 7 commits of veldo-0124-b2 are absent (a5fc50ba Claude bash-sandbox refusal and after), and merge-tree of veldo-0124-b2 with intcand-0125 conflicts in the six project_runner_macos* files plus both manifests. | no | 3 / clean against main; conflicts with veldo-0124-b2 | OWNER: approve the VELDO-0127 live re-capture (proof/VELDO-0127/live.py, pinned Claude 2.1.281 and Codex 0.154.0). CODE after 0124's shape is final: reconcile the macOS runner files with veldo-0124-b2. HOST: ipc_checks.py and native_roundtrip.py over the real socket, the two /run/user mutant controls, suite 86_veldo_0189. |
| 5 | VELDO-0061 + VELDO-0127 Codex 0.162.0 qualification | codex-0162-host b1dda912 (contains agent/codex/codex-0162-qualification 273313ff) | proof/VELDO-0061/README.md:5-7 "The production pin and the global install stay 0.154.0 ... It is not ready to pin yet: the live captures are not run. The reader decision is taken (Telegram 32962)". Nothing on main knows 0.162.0. | no (0127 amended on branch only) | 115 / clean | HOST: run the live captures (README "Moving the pin", line 112) on the real Codex 0.162.0, then the single pin-move change. |
| 6 | VELDO-0207 declared case reuse (case-closures) | case-closures bf1d849a | proof/VELDO-0207/gate-0210d-measurement.md:193-198 "The saving it buys on this gate today is nil ... needs the three fixes above, then narrower closures ... and an answer for the 892 unconfined cases". Design note in the spec marked "not built". Touches PROTECTED paths scripts/propose_case_inputs.py and scripts/mutation_case_inputs.json (floor high). | no | 122 / clean | OWNER: decide whether the three fixes are worth building given the nil saving; protected paths need a recorded approval. Then code here. |
| 7 | VELDO-0088 ingress grooming fix | fix-veldo-ingress-grooming 702ae771 (five of six commits also inside build-veldo-0205 and build-veldo-0185d) | Unlanded: main has no _serve in control_grooming.py or control_backlog.py, no v88 mutations. Prerequisite of the multirepo line. | no | 326 / conflict in scripts/suites/92_veldo_0088_pm_cycles.py | OWNER: decide whether the multirepo line (item 8) proceeds; if yes, rebase this first and rerun suites 92 and 93 (code work here). |
| 8 | Multirepo PM services (spec id collides with VELDO-0205) | build-veldo-0205 f53943bd; spec-veldo-multirepo 0f035c85 | proof/VELDO-0205/README.md on the branch: "Nothing of it is on main yet". Main's VELDO-0205 is mutation result reuse; no main spec carries the multirepo scope. | id collision | 326 / conflicts (PLAN-0019, proof README, suite 92, manifest) | OWNER: give the multirepo spec a new VELDO id and decide whether to revive; then rebase (large). |
| 9 | VELDO-0212 automatic engine upgrades (spec only) | veldo-0212-spec 401d802a | Spec status ready, risk high, PLAN-0019 W152; nothing on main mentions VELDO-0212. | n/a (absent on main) | 115 / conflict in specs/index.md only | OWNER: adopt or kill the spec. If adopted, regenerate the index (trivial). |
| 10 | Selective first-use reruns (spec id collides with VELDO-0211) | agent/codex/first-use-selective 23349e7d | proof/VELDO-0211/working-notes.md:3 "a partial validation record, not gate evidence"; ptrace refused in the sandbox; "No speedup is claimed". Main's VELDO-0211 is borrowed-login write-back. | id collision | 121 / conflicts (manifest, requires, index) | OWNER: new ticket id and suite number, or kill. Needs a ptrace-capable host afterwards. |
| 11 | Login sharing notes (VELDO-0210) | agent/codex/login-sharing c81e429f | Adds a 120-line "Login sharing investigation, 2026-10-08" section (Telegram 32715) to the 0210 spec; "Runtime changes are blocked on resolving that refresh coordination scope". | yes (+10/-7 on main) | 119 / clean | OWNER: decide the refresh-coordination design. The notes could move to proof/ and the branch close. |
| 12 | Gate-speed family VELDO-0190..0202 | build-veldo-0197 e29fe1c0 and build-veldo-0198 045c8a3b (stack 0191, 0192, 0194, 0195; also 0193, 0196, g0190, spec-gate-speed) | No spec of 0190-0202 ever reached main; main renumbered its own 0190 to 0203 (24f31ce6) and later wrote 0205-0208 fresh. 0197 and 0198 are superseded in intent by 0206 and 0205/0207; tracer (0191), hermetic snapshot (0192), preamble (0194), sharding (0195), scheduling (0196), concurrency (0200) and nightly (0202) have no counterpart on main. Suites 87-95 collide by number with main. | absent on main | 344 to 409 / all conflict | OWNER: kill, or pick the pieces to re-specify against today's 0205-0208 machinery. Not landable as is. |
| 13 | VELDO-0185 parallel implementation | build-veldo-0185d 09487438 (also build-veldo-0185, build-veldo-0185c) | VELDO-0185 landed via d12615eb (batch 1, green stamp 184e96db). 0185d is a separate implementation never landed; its extras: running-login clear, control_factory_setup_policy.py, two v185 falsifier fixes, the 0088 grooming edits. 0185 and 0185c record blockers main says do not hold. | yes (+29 on main) | 301 / conflicts (control_account_pool, control_factory_setup, control_launch) | OWNER: decide whether any 0185d extra is wanted on top of main; otherwise close all three. |
| 14 | VELDO-0213 + suite 106 flake | agent/codex/v106-flake c98b5f33 | Four of five commits are on main with identical patches (3eaf034a, c311c1dd, 42aace17, 28fc8f8f); only 0c5ecdfa's four diagnostic logs are missing (status "remaining", blocked on user manager). | yes (same text) | 21 / conflict in suite 106 (main newer) | CLOSE as superseded. |
| 15 | VELDO-0129 + VELDO-0141 | batch-0129-0141 d2b46e0d | Both source branches are in main's history; main has suites 82_veldo_0129 and 82_veldo_0141 and both proof READMEs. | yes | 831 / conflicts | CLOSE as superseded. |
| 16 | VELDO-0152 intake routing | build-veldo-0152 10364970 | Superseded by build-veldo-0152b (08d7edd3, in main via 47709632); main's control_intake.py:517 routes by ticket-key prefix. | yes (+347/-60) | 1082 / conflicts | CLOSE as superseded. |
| 17 | VELDO-0062 reviewer-scope template | build-veldo-0062 c0fff73a | Landed: merged commit 2bd13dc1 is on main; all five files carry the section. | yes | 1746 / clean | CLOSE as landed. |
| 18 | VELDO-0123 race check | land-claim ee02c07c | Landed: second parent 241b1f23 is on main; check_gate_mutations.py has inputs_unchanged (line 252). | yes | 2116 / clean | CLOSE as landed. |
| 19 | Stale gate stamps | build-veldo-0154 77ec9d34, land-0158 60c10082 | Each changes only .veldo/last_verify and .veldo/events.jsonl for commits already on main. | n/a | 718, 679 / conflict in the stamp files | CLOSE. |
| 20 | WARP-1712 | agent/codex/warp-integration-evidence ce66a1f2 (0 behind) | Skipped: being worked on elsewhere. "work in progress: VELDO-0045 enforcement, VELDO-0123 and VELDO-0208 still red". | - | 0 / clean | Skipped. |

Branches with no row of their own because they are strictly older points on a line above:
review-v0125 through review-v0125p, review-fcv0125q/r/s, intcand-0125n/o, seed/*, *-host,
agent/codex/veldo-0124, 0124b, 0125, 0125b, 0153, 0174, review-r0124, review-r0153,
review-r0174, review-v0153, review-v0174, review-v0174b, agent/codex/codex-0162-qualification,
build-veldo-0191..0196, build-veldo-g0190, spec-gate-speed, build-veldo-0185, build-veldo-0185c.

Landing order among the live candidates: 0174 and 0153 both add a suite numbered 107 at the
same manifest position (main already tolerates duplicate numbers, 103 and 104 twice), so the
second to land resolves a manifest.json and requires.json text conflict. 0124 and 0125 conflict
in the macOS runner files; 0124-b2 is the newer runner, so land 0124 first and reconcile 0125.

## Decisions only the owner can make

1. VELDO-0125: approve the VELDO-0127 live re-capture on the pinned engines (the only way the
   v0125q gate goes green), and confirm 0124-b2's runner wins the reconciliation.
2. VELDO-0124: the inputs in proof/VELDO-0124/README.md:312-340 (Codex install, pinned
   binaries and digests, logged-in profiles per engine, consent for six model calls, account and
   project roots, Keychain under VELDO-0147), plus restoring SSH to the Mac.
3. VELDO-0153: approval for the four consumer suites that run prohibited mutation drivers;
   two independent reviews (critical). The token-line dispositions still cover the merged tree
   (secret inventory 0 outstanding on 2026-10-22), so no fresh disposition is needed.
4. VELDO-0207 case-closures: build the three fixes despite the measured nil saving, or kill;
   protected paths need a recorded approval either way.
5. Multirepo line (build-veldo-0205, spec-veldo-multirepo, fix-veldo-ingress-grooming): new
   spec id in place of the colliding VELDO-0205, and whether to revive at 326 commits behind.
6. VELDO-0212 spec: adopt or kill.
7. Selective first-use (first-use-selective): new id in place of the colliding VELDO-0211, or
   kill.
8. Login sharing (VELDO-0210 notes): the refresh-coordination design.
9. Gate-speed family VELDO-0190..0202: kill, or name the pieces to re-specify.
10. VELDO-0185d extras: wanted on top of the landed 0185 or not.
11. Branch deletion for the superseded and landed rows (14-19) and the older points listed
    above; nobody but the owner deletes branches.

## Part 2 outcome, 2026-10-22

- agent/claude/fix-VELDO-0174 (main merged, commit 5034b175): run_falsifier.py repaired (broken
  by the ticket's own 2cd6c93b), all ten falsifiers red with the source restored, suite 107 at
  36 passing rows with only the two AF_UNIX restart rows red, suites 105 and 103 green, six
  other affected suites failing identically on main's own commit in this sandbox. Record in
  proof/VELDO-0174/merged-main-2026-10-22.
- agent/claude/fix-VELDO-0153 (main merged, commit b44736c0): static checks and secret
  inventory green, 22 anchors intact, suite 108 green; suites 107, 58, 103 and 67 die at the
  fixture SSH agent's AF_UNIX socket, so consumer repair stays host work. Record in
  proof/VELDO-0153/merged-main-2026-10-22.
- The mutation driver (check_teeth_mutations.py) cannot start inside this sandbox
  (candidate_execution_denied, nested agent sandbox without its launcher marker).
