# VELDO-0342 fix round

Implementation: edeaac5af72f75d0937720a38278a9225fc65e54. Review: bf962cfc, findings F1 and F2.
Builder diagnostics, not an independent verdict or a full gate run. The original proof files
remain historical; this round supersedes their description of members waiting for Keep application.
Machine-readable counts, source digests and all twenty falsifiers are in fix-round.json.

F1: the publication triggered by settlement advances a member Keep immediately. The group records
that member's answer with pending_application; the item stays deferred under its original alias,
with its work on disk. The owner's signed packet can apply that answer after the remaining group
closes. The original service worker carries this work; no polling or filesystem work was added to
the service loop. No signer was built; that gap is routed to VELDO-0319.

Rows: next/settled-keep (members 1 and 3 get request 2 after Keep w2; the late packet still applies
after group closure), next/keep-join (later same-day member 4 joins request 2), next/keep-text
(the brief states the actual timing), and the extended worker/member-pick row. Each is green.
Three added F1 falsifiers were each applied once and rejected with green baseline and no-op runs:

- space342-keep-waits-for-application: next/settled-keep, next/keep-join, next/keep-text and
  worker/member-pick turn red.
- space342-pending-keep-loses-its-original-request: next/settled-keep turns red.
- space342-keep-text-omits-settlement: next/keep-text turns red.

F2: next/left-member starts judging member 3 again between settlement and application of Discard w2.
The pick write marks member 3 gone. Its judgment defers it again while member 1 survives, and it
joins the same request under index 4 with its edit intact. This also exposed and fixed replay of
the old requested disposition after the gone mark. Both added F2 falsifiers were each applied once
and rejected with green baseline and no-op runs:

- space342-departed-member-not-marked-gone: next/left-member turns red.
- space342-departed-member-replays-old-request: next/left-member turns red.

Requested suites, all with zero failed rows: 0342 22, 0340 16, 0336 21, 0318 45, 0327 27,
0345 31, 0300 39. These selected-suite diagnostics exit 2 by design. Fast checks: validation,
docs, template sync, lint, space boundary and Git boundary all exit 0. All runs used nice -n 10.
The supervisor process check after each run found none owned by that run.

Teeth 342 ran last on the clean implementation commit, with no edits during the run: 20 registered,
20 executed, 20 rejected, 0 reused, 0 invalid results, 28 workers, 0 surviving workers or supervisors.
Elapsed 573.940 seconds. All fifteen existing falsifiers also remain rejected. No further checks
were run after teeth. Proof was written only after its completion. No full gate or forbidden suite
was run. The protect list was untouched; removals exercised the keep step and existing removers.
