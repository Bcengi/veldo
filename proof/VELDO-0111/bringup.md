# VELDO-0111 brought onto the line, 2026-11-20

Source branch: `agent/codex/veldo-0111` at 2a7bfcec6aff. New base: the line (space-0329b) at 0b767d26baf6.
The ticket's own commits, oldest first, were brought over as one change (the branch is stale against
the line, so its diff was ported, not replayed commit by commit):

- 83ec3ad2 VELDO-0111 add supervised ptrace census and scoped acceptance checks
- 66c31675 VELDO-0111 record socket addresses and add isolated falsifier drive
- bd59a819 VELDO-0111 reject malformed receipts and document qualification limits
- 99dcf5ea VELDO-0111 make descendant drain probe independent of host timing
- db1da0a6 VELDO-0111 retain baseline receipts with incomplete host qualification
- a494c9a0 VELDO-0111 retain four red and green falsifiers and open qualification gaps
- 4800972e VELDO-0111 independent review: NOT SOUND
- ab7ea982 fix(census): require matching lifecycle faults and record AC4 cycle
- 0c5ab2b7 fix(census): track accepted sockets and implicit UDP bindings
- ca76b979 fix(census): derive named qualification limits from generated host probes
- 2b66a9d1 test(census): retain final-source swallowed-fault falsifiers
- 5eeb6664 VELDO-0111 fix-check round 2: NOT SOUND
- 4f323123 docs(census): apply approved AC2 and AC4 amendments
- c72afd41 fix(census): enforce family boundary and verify implicit Unix bindings
- 2a7bfcec test(census): retain round 3 falsifiers and remaining qualification evidence

## Receipts not carried

Binary receipts stay on the source branch (the personal-setup check refuses binary files and a
ticket's proof stays under 1 MB). Each is named here with its size and sha256 as on that branch:

| File | Bytes | sha256 |
| --- | --- | --- |
| proof/VELDO-0111/AC1-green.json.gz | 61860 | da8ddc1536bed62399ed17e63d5bf1ac3a826ec7e5c07777fa4cb218a15c11bf |
| proof/VELDO-0111/AC1-red.json.gz | 61120 | 76a115e81d93a200902ae1dc43699ba2809f89549c8adad8a7c1643e172c3884 |
| proof/VELDO-0111/AC2-green.json.gz | 61856 | 3b0a5c1a4adaf7fb9cf8a0779583a24ab857059cedbf902d364a3669a3fbbc6d |
| proof/VELDO-0111/AC2-red.json.gz | 61797 | dc8bebf24cadf7b022acb689474b4d89ec77a8033f0b1b7fbe928960d07fc8e8 |
| proof/VELDO-0111/AC3-green.json.gz | 61867 | d295927e6c29e956e047ea215ae65781503d4f1b04604e0ec5960b279acacff4 |
| proof/VELDO-0111/AC3-red.json.gz | 60980 | 655b3fdbcdade5bfe9596fd120893c6c566e60ab0718e0b5047767af1d76eb9d |
| proof/VELDO-0111/AC4-green.json.gz | 61880 | 04221a0a304d0faafa651d4ba0268d06400dfd8cd5a24e1b5c32b2ec34783455 |
| proof/VELDO-0111/AC4-red.json.gz | 61726 | 2d21e12e329484b7bc87e97124fc84deb1501c0a85673780f94589e82a0a7a73 |
| proof/VELDO-0111/baseline.json.gz | 37432 | 8daf46e9c35b47bea4376ec859b03868953d34ccd2eec238ead4540643c81275 |
| proof/VELDO-0111/round2/fault-green-control.json.gz | 560520 | 9de3f9029f4b53ee71c6f4133b83f1e0290f9847eb8b40383b503b65db8d8aeb |
| proof/VELDO-0111/round2/green-control.json.gz | 45137 | 0332920909c02c7bf47452c02a456deb70bd946aca054cf06b23af4124a10d20 |
| proof/VELDO-0111/round2/green-escape-mutant.json.gz | 45314 | 37660cec03aeeba4d723b4567c7b570b870b76d64d501b6bb116df93b10e34c9 |
| proof/VELDO-0111/round2/green-swallow-abi.json.gz | 560484 | 05bd229a43db7af82403709468e1279d97a1aba889e30d7166e4c57e1216e2f6 |
| proof/VELDO-0111/round2/green-swallow-corrupt.json.gz | 560557 | 090be9303ab1787e6845618234855f9a0cab8b5fc3874c4d59fffd7c7f019878 |
| proof/VELDO-0111/round2/green-swallow-loss.json.gz | 560563 | c0adf86ec29bfb200667aa029fe9ef62d559e48ae8fb4b619d3db6eb55fbb941 |
| proof/VELDO-0111/round2/qualification-green.json.gz | 560560 | bf3b7583e7f310fcdef24c6afd4490ab90ed0255334bb70713b7ef81788ef41e |
| proof/VELDO-0111/round2/qualification-red.json.gz | 45143 | 8e26e39b46e5a91cad77ac279e13c715674a924106df43ff5c1f925ef3ea637a |
| proof/VELDO-0111/round2/red-control.json.gz | 44696 | 2e1a871ceab44172a1336110a12e015ee2a43f9764a49e73906ab9c7c48e5589 |
| proof/VELDO-0111/round2/red-escape-mutant.json.gz | 44896 | d71b9051755c4113880724b65c33aa4c8bbd69c356e0dc8ca07d203bd2b82b79 |
| proof/VELDO-0111/round2/red-swallow-abi.json.gz | 37385 | 158fc12812d2c02447a0fcbc9b3d60a90e9760c7b670bae3050655eb58e1b797 |
| proof/VELDO-0111/round2/red-swallow-corrupt.json.gz | 37419 | 599ec7c4bc60755485a98d352b093fb18307fbaba96ade583f56735a2ad8e80e |
| proof/VELDO-0111/round2/red-swallow-loss.json.gz | 37475 | 57e0d1f8e8881956290219b24e1275dc52cbbe749f9414d8455a3c2b79e00d85 |
| proof/VELDO-0111/round3/drop-autobind-green.json.gz | 54469 | f4f3bd86de468152031e3aafabc8df956bc589b759f0f14103df88e7838f6aeb |
| proof/VELDO-0111/round3/drop-autobind-red.json.gz | 54383 | 14c1895df32ca7c9513d0d8324bdbb8e6066b358c8bbb9f1a07a7a0543233165 |
| proof/VELDO-0111/round3/other-family-service-green.json.gz | 54465 | 0bc7b199acda0b64011f1d7c70245546fd797b12ec9dbc1a47aeb3356cf64eba |
| proof/VELDO-0111/round3/other-family-service-red.json.gz | 54529 | 4c70f3e9a734267ab6ce666bebea3aa107fc333f2eb0eb2f6217579045446bfa |
| proof/VELDO-0111/round3/phantom-unix-green.json.gz | 54460 | bd4ae12d46f4ed8e1848ce1185b897707cb9373b0a9c829118d608509e8d847c |
| proof/VELDO-0111/round3/phantom-unix-red.json.gz | 54525 | f96e127073133fe02f6a2b056a98515d3b877795f1fce44d58369544796b3684 |
| proof/VELDO-0111/round3/regressions-red.json.gz | 107935 | e7bbbd0c30b63922d7583563ebc331fcc1ef9fae35eb843ef9234d8aa8ffbc47 |
| proof/VELDO-0111/round3/silence-family-green.json.gz | 55950 | bb07d8a042fca84e6a441ff934742375cd3ada77f6f2bdbd1fde71555369d293 |
| proof/VELDO-0111/round3/silence-family-red.json.gz | 55483 | 13384c40961dbaf6d41d67a42f5ae51dd57b4688d4ae36e8ccba6054b96f898a |
| proof/VELDO-0111/round3/suite-green.json.gz | 700247 | 78711b73905e5b3b319143c33cea3fd10ffc0dff3138a2629eba415acaa84ca2 |
| proof/VELDO-0111/round3/uncovered-state-green.json.gz | 291 | e0b9b6638d6c4562300b56ddc5b451f5e653cb85d66d428b006f757dcb7a6e70 |
| proof/VELDO-0111/round3/uncovered-state-red.json.gz | 295 | adedd2f70972bdca5dd87270778701f5c794fb6165abbde0a7e7f2f320a3e811 |

## What changed in the port

- `scripts/suites/manifest.json` and `scripts/suites/requires.json`: the line's entries are kept and
  the row for `113_veldo_0111_census` is added.
- Load rule (owner 42829): the census deadline is a hang detector. `census()` defaults to 120 s
  (was 10 s), accepts up to 1200 s (was 60 s), and the supervisor waits 120 s past it for the
  collector (was 2 s). The inventory probe's deadline is 600 s (was 60 s). The drain-expiry probe's
  root now blocks in `signal.pause()` forever instead of sleeping 10 s, so expiry does not depend
  on host speed; its 0.05 s deadline is the behaviour under test, not a wait for the host.
- Home-directory paths in the retained diffs and in round3/README.md are rewritten.

## Deadlines touched, and what each one guards (load rule)

The ticket has no `manifest.json` (its record is `results.json` and the round records), so this section
is the manifest's statement. The suite passed 13 rows before and after these changes: none of them
was made to turn a failing row green. No row of suite 113_veldo_0111_census compares an elapsed time
with a number.

| Bound | Was | Is | The wait it guards | Why it is not a timing assertion |
| --- | --- | --- | --- | --- |
| `census(deadline=...)` default, used by every probe that ends on its own | 10 s | 120 s (`HANG_SECONDS`) | The collector's drain loop: `waitpid` on the traced root and every traced descendant, until the last of them has exited | The loop ends on the last exit event. When the bound is reached the census is reported INCOMPLETE (`drain_deadline`); the rows over these probes assert a COMPLETE capture, so a bound sized to a quiet host would turn a correct run red on a busy one. It detects a probe that never ends. |
| `census()` largest accepted deadline | 60 s | 1200 s | Nothing waits on it: it is the argument check | It only admits the inventory probe's bound below. |
| The supervisor's wait for the collector | deadline + 2 s | deadline + 120 s | `waitpid` on the collector process | The collector reports its own drain expiry in its receipt and then exits; this bound is reached only by a collector that hangs after its own deadline, and it is then killed and reported as `collector_death`. |
| The inventory probe's `deadline` | 60 s | 600 s | The same drain loop, for the longest probe (every socket family, type and operation) | As the first row. |
| The drain-expiry probe (`deadline=.05`) | root sleeps 10 s | root blocks in `signal.pause()` for ever | Nothing: 0.05 s is the behaviour under test, a drain that expires | The row asserts the outcome (INCOMPLETE on expiry), not a duration. The root never exits, so expiry is reached on any host; with `sleep(10)` a host slow enough to take 10 s to reach the drain loop would have seen the root exit first. |

## Status carried over unchanged

The ticket is not accepted in full: AC2 qualification remains open (OPEN.md), the last independent
check on the source branch was NOT SOUND (fixcheck-2026-10-28.md) and round 3 answers it without a
later review. The bring-over changes none of that.

## Results on the new base

Ported at 88eb37a9. bringup-2026-11-20/results.txt:

- Suite 113_veldo_0111_census alone: 13 rows passed, twice (before and after the deadline change).
- Two falsifiers run singly on scratch copies, each red on its named row and green on the original:
  round 1 AC4 (a COMPLETE receipt with an empty trace after collector death) and round 3
  uncovered-state (bringup-2026-11-20/sample-falsifiers.json). AC4 is the row whose expiry probe
  the load-rule change touched.
- The full falsifier drives, run through the host lock on 2026-11-21 in a scratch clone of 6b322350 at
  load 22 (`bringup-2026-11-21/drives.txt`): `python3 -B proof/VELDO-0111/drive.py`, four falsifiers each
  red on its named row and green on the original (AC1 census/process-lifetimes, AC2
  census/listener-lifetimes, AC3 census/observer-is-outside, AC4 census/incomplete-is-not-empty), and
  `python3 -B proof/VELDO-0111/round3/falsifiers.py`, five falsifiers each red on its row and green on
  the original. Both exit 0. Every run was under the deadlines of the table above, on a loaded host.
  The `.json.gz` receipts both write are not committed (6.8 MB together).

`results.json`, the four `AC*.diff` files and the `round3/*-red.json` and `*-green.json` files are now
this run's and carry the line's source digests. `round3/acceptance.json` and the round 2 records are
still the source branch's.
