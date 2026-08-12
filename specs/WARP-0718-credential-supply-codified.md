---
schema: veldo.spec/v1
id: WARP-0718
title: The human-decision surface is real in the code and INERT in practice - there is no documented way to
  supply the agent credentials, so the agent cannot reach the board and every approval degrades to a chat
  message, which is the exact thing the plan forbids
status: ready
risk: high - this item is about how a CREDENTIAL reaches a process, so a careless version of it is how secrets
  end up in a repository, a log, or a shell history. It must therefore add a documented SUPPLY MECHANISM and a
  diagnosable REFUSAL without ever widening where a secret may live: no secret in a tracked file, no secret in
  an error message, no secret in a repr, no secret in a captured command line. It is high for that reason and
  not critical because it grants no new capability - the agent could already authenticate if the environment
  carried the values, and this item only makes that supply codified, adopter-safe and diagnosable instead of
  folklore
owner: dmitry
human_approval: required
approved_by: dmitry
approved_at: 2026-07-25
approval_record: >
  RECORDED ON THE BOARD: VEL-8 (https://bcengi.atlassian.net/browse/VEL-8), transitioned to Approved BY DMITRY
  HIMSELF at 2026-07-25 21:16 EDT, on a ticket carrying the full RISK section (no new capability, refusal of a
  world-readable or git-tracked secrets file, sentinel-proven absence of any secret from every captured output,
  gitignore coverage asserted in every pack). The agent created the ticket and moved it to Awaiting Approval but
  did NOT fire the Approve transition. Note the circularity this item exists to remove: the ticket had to be
  created through Dmitry's own Atlassian identity, because the missing agent credentials ARE the subject of the
  item.
lane: standalone
depends_on: [WARP-0620]
placement: [engine]
footprint:
  - .veldo/tracker_intake.py
  - engine/.veldo/tracker_intake.py
  - packs/*/.veldo/tracker_intake.py
  - docs/
  - scripts/selftest.py
  - specs/WARP-0718-credential-supply-codified.md
  - specs/index.md
protected_paths: []
behavior_bearing: true
observability:
  logs: A failure to resolve a credential names WHICH reference failed and WHICH supply mechanisms were tried,
    in order, and says what to do about it, so an operator can fix it without reading the source. It never
    prints, echoes or reprs the value, and a resolved credential is reported only as resolved-or-not.
  error_taxonomy: The names are closed and diagnosable: CREDENTIAL_UNRESOLVED (no mechanism produced a value,
    with the reference name and the mechanisms tried), CREDENTIAL_SOURCE_UNSAFE (a candidate source exists but
    is rejected, for example a world-readable file or a tracked path), and the pre-existing
    MirrorRunnerError kept for the case where the token exchange itself fails.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Make _default_secret_resolver return an empty string rather than nothing when the environment carries no
      value, so the mirror's live path treats it as a resolved credential and proceeds, and the assertion that
      with the environment variables absent the resolver yields nothing and the live path refuses BY NAME must
      go red.
    text: >
      THE DEFECT IS REPRODUCED FIRST, AS AN OPERATIONAL FACT. A selftest asserts that with the environment
      variables absent, the credential resolver returns nothing and the mirror's live path refuses BY NAME
      rather than proceeding, which is correct today and must stay correct. The accompanying record states the
      measured situation this item exists for: `_default_secret_resolver` reads ONLY os.environ, there is no
      dotenv support, no entry in .gitignore anticipating a secrets file, and nothing in the operator guide
      describing how to supply the values - so on a machine where they are not exported, the entire human
      decision surface built by PLAN-0016 cannot be exercised by the agent, and every approval degrades to a
      chat message, which constraint C-approvals explicitly forbids. That is the gap: not a bug in the code, a
      hole where the instructions should be.
  - id: AC2
    falsified_by: >
      Drop the owner-only permission test on the operator secrets file so a group or world readable file is
      accepted, and the assertion that such a file is REFUSED must go red; that is the load-bearing leg, since
      it is the one deciding whether a credential may sit readable by every account on the box, while the git-
      tracked refusal and the .gitignore coverage in the repository and in every pack falsify the same
      criterion from the other two sides.
    text: >
      THERE IS ONE CODIFIED, IDEMPOTENT, ADOPTER-SAFE SUPPLY MECHANISM, part of the init flow rather than a
      thing a person is told in chat. The resolver accepts a documented ordered set of sources, tries them in a
      declared order, and names the order in its failure message: the process environment first (unchanged, so
      nothing that works today stops working), then a local operator secrets file at a documented path that is
      REFUSED unless its permissions are owner-only and REFUSED if it is tracked by git, asserted for both
      rejections. No secret is ever written to a tracked file, and a selftest asserts the secrets path is
      covered by .gitignore in the repository AND in every pack, because an adopter who follows our
      instructions must not be able to commit their own credentials by accident. `veldo init` reports whether a
      credential resolves, without printing it.
  - id: AC3
    falsified_by: >
      Interpolate the resolved value into the resolver's failure message or its __repr__, and the sentinel
      assertions, which resolve a known sentinel and require it absent from every captured log line, error
      message, exception string and repr including the failure paths, must go red on that output.
    text: >
      NO SECRET LEAKS AND THE REFUSAL IS DIAGNOSABLE, both proven rather than promised. Selftests assert that a
      resolved credential appears in NO log line, NO error message, NO exception string and NO object repr,
      including the failure paths, by resolving a sentinel value and asserting the sentinel is absent from every
      captured output. The failure message names the reference and the mechanisms tried and says what to do, so
      the operator experience is a sentence rather than a traceback. The operator guide gains one short section
      describing the supply mechanism generically, adopter-safe, passing the genericity sweep. Engine canon
      holds across engine and all six packs, the frozen safety core is byte-UNCHANGED, no protected
      path is touched, the full gate is GREEN, and RULE #1 is clean.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds an ordered credential-supply mechanism with two safety refusals, a
  gitignore entry in every copy, leak assertions, and one operator-guide section, all re-synced byte-identical
  across engine and the packs. Reverting returns the resolver to environment-only, which means the
  approval surface stays inert on any machine that does not export the values - a loss of operability rather
  than a return to a good state. No secret, record, contract or write path changes, so there is no migration.
---

## Intent

Dmitry, 2026-07-26, on being told his approval had been given in a chat message: **"Is there a ticket for my
approval?"** There was not, and there could not be, and that is the finding.

PLAN-0016 built a human-decision surface whose whole premise is that approvals are recorded on the tracker,
asynchronously, with a readable brief and a risk section, precisely so that a transient yes in a chat window
can never stand in for a considered decision. The code for that surface exists and is gate-proven. The live
fence was proven against a real board: the agent structurally cannot approve its own work.

And yet tonight an approval happened in a chat message, because the agent cannot reach the board at all. The
credential resolver reads only `os.environ`; shell state does not persist between an assistant's commands; there
is no dotenv support, no anticipated secrets path, and no line in the operator guide that says how a person is
supposed to supply the values. So the mechanism is real in the code and INERT IN PRACTICE.

That is worse than a missing feature, because it is invisible: everything passes, the design is sound, the live
proof succeeded, and the surface still does not function where it matters. The gap is not in the code, it is
where the instructions should be - which is exactly the failure mode the house rule about codified setup exists
to prevent: setup, init and provisioning are CODE, idempotent and adopter-safe and part of the init flow, never
a thing an assistant tells someone in a chat window.

## Context

- What is measured, not assumed: `_default_secret_resolver` in .veldo/tracker_intake.py maps `env:NAME` to
  `os.environ.get(NAME)` and returns None otherwise. The OAuth token manager then raises by name, never
  printing the value, which is the correct half of the design and must be preserved.
- What the dry-run already proves, and its limit: `bin/veldo mirror --dry-run` runs with both variables unset,
  over an in-memory fake tracker, no network, exit 0. So the projection logic is exercisable offline; only the
  LIVE pass is unreachable.
- Why an owner-only permission check and a tracked-path refusal are load-bearing rather than decoration: the
  moment a documented secrets path exists, an adopter will create it, and the two ways that goes wrong are a
  world-readable file and a committed one. Both must be refusals, not warnings.
- Why the sentinel-based leak assertions rather than a code read: proving a value is absent from every captured
  output is a property over behaviour; grepping the source for a print statement proves something about today's
  source only.

## Out of scope

- No change to the fence, the authorization core, or the approver set. This item is about REACHING the board,
  never about who may decide.
- No new capability for the agent. It may already authenticate when the environment carries the values; this
  makes that supply documented and safe.
- No secret manager integration, no keyring, no cloud provider. One local mechanism, documented, plus the
  environment. Anything further is its own item with its own argument.
- No change to what a decision means or how it is recorded once the board is reachable.

## Notes

- Do not widen where a secret may live in order to make this convenient. The refusals are the point as much as
  the mechanism is.
- Assert the gitignore coverage in EVERY pack, not just the repository. An adopter committing their own
  credentials because they followed our instructions would be our defect, not theirs.
- Write the failure message for a tired operator at midnight: which reference, which mechanisms were tried, what
  to do next.
- NO UNBACKED UNIVERSAL: "no secret appears in any log, error or repr" is the central claim and needs the
  sentinel sweep over every captured output, including the failure paths.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
