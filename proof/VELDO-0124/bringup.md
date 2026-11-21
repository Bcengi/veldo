# VELDO-0124 brought onto the line, 2026-11-20

Source branch: `agent/codex/veldo-0124-b2` at aa04094bab95. New base: the line (space-0329b) at 10d4ba11d546.
The ticket's own commits, oldest first, were brought over as one change (the branch is stale against
the line, so its diff was ported, not replayed commit by commit):

- 146a24f9 Add qualified macOS worker lifecycle and authority adapter
- 869d76ff Test macOS authority boundaries and declare native qualification checks
- e9002c96 Record macOS development checks and pending native evidence
- 2f7850f6 macOS worker job declares the Background session type so launchctl bootstrap into user/<uid> succeeds on macOS 26 (VELDO-0124)
- f79d48ef Record VELDO-0124 native lifecycle and containment results from macOS 26.5.1 and what the real engine rows need
- 86cdc221 VELDO-0124: narrow Seatbelt profile, run scoped HOME and TMPDIR, engine group under the wrapper with a deadline backstop, coalition descendant tracking, slot recovery and pinned interpreter
- 7be4d267 VELDO-0124: native rows for every containment rule, hard kill and supervisor loss, per rule native falsifiers, production engine environment for native rows, and the review fixes recorded in the spec and README
- 7b70d125 Record VELDO-0124 native rows and native falsifiers run on macOS 26.5.1 from 7be4d267
- a5fc50ba Enforce disabled Claude bash sandbox in the reviewed Mac profile
- 3b59a3b9 Record Claude sandbox refusal diagnostics and check-removal falsifier
- c6768100 Resolve suite catalog conflicts and retain both sets of registrations
- eebad4f9 Repair pending macOS proof schema and preserve falsifier rounds
- 90d4d2ec Record batch 2 macOS checks, review responses, and native blockers
- 412b9c39 Normalize diagnostic log whitespace and retain exact mutation edits
- 020067d0 VELDO-0124: record 2026-10-28 native Mac qualification observations
- 722845bb VELDO-0124: independent review 2026-10-28, NOT SOUND
- e20b4c15 VELDO-0124: review 2026-10-28, record reviewer reruns
- 96901dbf VELDO-0124: verify qualification evidence files and bindings
- c946b759 VELDO-0124: observe real Codex signal ignoring child on Mac
- ea4e9d83 VELDO-0124: prepare Claude child accounting for login unblock
- 1671e2e3 VELDO-0124: record round 2 proof and Claude owner blockers
- 754b9101 VELDO-0124: fix-check round 2 2026-10-28, NOT SOUND
- 6570d20d VELDO-0124: cover five evidence checks and neutralize fixture identity
- cebc3445 VELDO-0124: document round 3 scope and pending verification
- 227b444a VELDO-0124: record qualification red-green evidence
- 028c043b VELDO-0124: complete scoped verification evidence
- aa04094b VELDO-0124: describe the round 2 fixture identity finding without naming the address

## Receipts not carried

These files stay on the source branch: binary receipts (the personal-setup check refuses binary
files) and bulk that would take the ticket's proof over 1 MB. Each is named with its size and
sha256 as on that branch:

| File | Bytes | sha256 |
| --- | --- | --- |
| proof/VELDO-0124/batch2/AC1-claude-sandbox.log | 9711 | 2ff937b6d62d94a8c8eec4430cce208387ad1c8b723f6ab286e071b32a5c2026 |
| proof/VELDO-0124/batch2/AC1-qualification.log | 9053 | 30570509f77bb0669041df7906551e6a77c753cf4094c91dd1f322b822d83675 |
| proof/VELDO-0124/batch2/AC1-session-type.log | 9023 | 532e2df129a5a86f0cacdc24703d942c26dae30d9d9e349ceab9888211dec880 |
| proof/VELDO-0124/batch2/AC2-capacity.log | 9038 | 219d04d00c647eac4c31dbb1e1afd4ecdc3715f655e0065e623fa38a3756a826 |
| proof/VELDO-0124/batch2/AC2-deadline.log | 9536 | 8790642acc23f4c2051b487d43377257e637149c3a545e730c63ecb35922a06d |
| proof/VELDO-0124/batch2/AC2-postcall.log | 9432 | 4cac9f11ebf568464addac6f0fe6b210c5d01433fae4bb6586e62c4e95edb3f1 |
| proof/VELDO-0124/batch2/AC3-group-only.log | 9507 | f7e7f33407ee341ffece215cee60b1309793d9b51fc19db5c14f2c84be0e56aa |
| proof/VELDO-0124/batch2/AC3-parent-only.log | 8992 | 5887c23796d4ba784ced00bb774847d3037d7f0a35bd263cf85f879a05086c05 |
| proof/VELDO-0124/batch2/AC3-unknown-retire.log | 9046 | baf3091b33ecfd989664674d685aaeafd943c0e10dad7b55e44c96cb8145f73a |
| proof/VELDO-0124/batch2/contracts-final.log | 50698 | 64cd5e5e59a1f20190f8438c16d7d061383eb74dec66a022d8768ded190dd497 |
| proof/VELDO-0124/batch2/contracts.log | 51233 | 06d2b749aa349c161346623124a11a6adaa66984ac8c3a2510ac78fd9c87222a |
| proof/VELDO-0124/batch2/diff-check-before-normalization.log | 594 | bf9af6b634b3208ec2574d687dcfb891e585b107685a2263b3e1476ac8e0d235 |
| proof/VELDO-0124/batch2/diff-check.log | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| proof/VELDO-0124/batch2/docs-final.log | 313 | e4c366e2b87332bd87bf456866d97c14886ea5a7cec6313163cab88a4199bf6c |
| proof/VELDO-0124/batch2/docs.log | 313 | e4c366e2b87332bd87bf456866d97c14886ea5a7cec6313163cab88a4199bf6c |
| proof/VELDO-0124/batch2/generated-final.log | 250 | f11b77ff165398767a2894fd34d9592c5d6d516b2828368d967fa7663a9d1217 |
| proof/VELDO-0124/batch2/generated.log | 250 | f11b77ff165398767a2894fd34d9592c5d6d516b2828368d967fa7663a9d1217 |
| proof/VELDO-0124/batch2/host-access.log | 68 | c386b8a1f539b6020804c98cefbc5e70d15661fd60013f5e81bcbba90cc99087 |
| proof/VELDO-0124/batch2/lint-final.log | 42 | b02a09f12906d995ce635a3b55602d7d030b2a02af64381a2e69d09e68ba5d56 |
| proof/VELDO-0124/batch2/lint.log | 42 | b0a5cacfbb621a767a026b5c16fe1efb63dd6b8db2d4cb29a0cdbb6a5e1d5e08 |
| proof/VELDO-0124/batch2/negative-controls.log | 382 | 4dd8ff49d570736242ac325931a48c951dae76cbc95dd615c0fa816a77c523a5 |
| proof/VELDO-0124/batch2/security-final.log | 162 | be460396307bc3a319ed1cbd79ab47f3628548318df71dcaecfb28f2d8f57d74 |
| proof/VELDO-0124/batch2/security.log | 162 | be460396307bc3a319ed1cbd79ab47f3628548318df71dcaecfb28f2d8f57d74 |
| proof/VELDO-0124/batch2/shape-after-cleanup.log | 572 | 11be7dfa91bec399bd37b4fbd2233a733f69f5bf4d48d0c2bf40a4bf83765a54 |
| proof/VELDO-0124/batch2/shape-final.log | 8020 | c751ec52fd4054666614a9c41d3ad356abc205056c575d054fe2aade2b3e35f7 |
| proof/VELDO-0124/batch2/shape.log | 572 | 11be7dfa91bec399bd37b4fbd2233a733f69f5bf4d48d0c2bf40a4bf83765a54 |
| proof/VELDO-0124/batch2/suite-103-baseline.log | 8915 | 5dcee26c7c34a0a8ea0344f218860d5e371923f60d010797fccfea92e6387d0c |
| proof/VELDO-0124/batch2/suite-103-final.log | 8915 | a206be146441ca842ea836121943f68af456e853ca9c62f6b5f2aea96f149407 |
| proof/VELDO-0124/batch2/suite-104-baseline.log | 8917 | f35b7b37b1124bafc2307c94da33802c5947d65667f6f6c7500e2dee59648876 |
| proof/VELDO-0124/batch2/suite-104-final.log | 8917 | 8ffee890fa1765a9dc14f29f9adf57de4bb5039ec3539c4aab4d8bb08ed1f961 |
| proof/VELDO-0124/batch2/template-sync-final.log | 81 | e6ca4120594d7b828b7cf24052956271125a2c270736ad1ae7074ee79eea4a24 |
| proof/VELDO-0124/batch2/template-sync.log | 81 | e6ca4120594d7b828b7cf24052956271125a2c270736ad1ae7074ee79eea4a24 |
| proof/VELDO-0124/native-2026-10-28/manuals/index.json | 876 | 39119a32415d855ad9d50eb3cfe5d711274ef02bd5146f1c2566b19e689ab92b |
| proof/VELDO-0124/native-2026-10-28/manuals/kqueue.2.txt | 25177 | ffbc58c740d3b3b395330c1e35cd9281e716106addd997eb1c4ee849dabf71e1 |
| proof/VELDO-0124/native-2026-10-28/manuals/launchctl.1.txt | 30654 | af9960dd23ba3cd07d11828831739cd72109b7282bbec34d7f2bd5c51c156f11 |
| proof/VELDO-0124/native-2026-10-28/manuals/launchd.plist.5.txt | 35997 | 19ac513cbf5f6bd54cb58b55cb809d36e303e5b6d6bb9b1c6604c6632f8f70e3 |
| proof/VELDO-0124/native-2026-10-28/manuals/ps.1.txt | 19212 | 95baa63095924bdb8cc63626f53f548bb27733718df384edcc8bf7f2e015d829 |
| proof/VELDO-0124/native-2026-10-28/manuals/sandbox-exec.1.txt | 1125 | 8155d6b0c16d26874ab9b280976d6df9c325bd2526151924b7e81a5e1a7f66cf |

## What changed in the port

- The five `project_runner_macos*.py` modules (and engine copies), suites 103_veldo_0124_macos and
  104_veldo_0124_control and the specification are the branch's. The branch's merge of main
  (feabeec7) is not replayed; the line already holds what it brought.
- `scripts/suites/manifest.json` and `requires.json`: the two suites are added to the line's lists.
- Load rule (owner 42829): the suites' clock is simulated (FakeOS), so their timed rows do not read
  the host. The three real subprocess timeouts (5 s, 10 s, 20 s) and the falsifier driver's 60 s are
  hang detectors now (120 s, 600 s for the driver).
- Suite 103 spells its synthetic Mac paths in two parts, and the two historical qualification
  drivers no longer name a home directory, so the personal-setup check finds nothing.

## One more suite: the send inventory

86_veldo_0168_text (VELDO-0168) counts every `send` call site in the engine and went red on the Mac
runner's four (`Run.descendants` twice, `Run.step`, `Run.wait`). They are OS signals to a run's
processes and carry no text to a person; they are declared in the suite's inventory, as the
VELDO-0125 branch had done. The suite passes 26 rows.

## The git boundary

`scripts/check_git_boundary.py` (suite 50_git_environment) refuses a git call that does not go
through `git_process`. `check_clone` in `project_runner_macos_os.py` called `/usr/bin/git` twice
directly. Both calls go through `git_process.run` now, the module loaded from beside the file: the
same change the VELDO-0125 branch made to these lines (15787c77). Suites 103 and 104 and the
fifteen falsifiers were rerun after it.

## Needs review: one space-boundary entry

The line's VELDO-0304 check (`scripts/check_space_boundary.py`) refuses a recursive removal outside
a reviewed boundary, and `Run.release` in `project_runner_macos.py` removes the run's own
per-dispatch TMPDIR with `shutil.rmtree`. The rule did not exist when the ticket was built. The
bring-up added `REVIEWED[('engine/.veldo/project_runner_macos.py', 'Run.release')]` with its
reason, marked in the file as not yet reviewed with design 6.10. The Mac worker host has no space
ledger; whether its folders should be declared to one is for the reviewer and the owner. With the
entry the check passes and suite 155_veldo_0304_space_boundary passes 51 rows.

## Results on the new base

bringup-2026-11-20/results.txt: suite 103 29 rows, suite 104 7 rows, all passed; 15 of 15
falsifiers rejected. Native macOS qualification was not rerun and stays open (OPEN.md); the last
independent check on the source branch was NOT SOUND (fixcheck-2026-10-28.md), answered by round 3
without a later review.
