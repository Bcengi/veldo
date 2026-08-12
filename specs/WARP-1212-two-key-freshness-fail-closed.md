---
schema: veldo.spec/v1
id: WARP-1212
title: Two-key freshness must fail closed when no clock (hardening of PLAN-0012 W7 per the WARP-1207 review findings)
status: shipped
risk: high - this hardening edits the TWO-KEY ORGAN (.veldo/two_key.py), the enforcement core on the execution side, so per C2 ("specs touching the executor, the whitelist, the two-key rule, the kill switch, or the ladder configuration carry a HIGH risk floor with recorded human approval") the floor is HIGH and human_approval is required. It is HIGH, NOT critical - C2 reserves the CRITICAL tier for a spec that OPENS or WIDENS a data-mutating execution path (WARP-1207 met that trigger by building the reachable data-mutating run). This spec builds NO execution path and can NEVER cause a run that would not have happened before: it is a pure fail-CLOSED tightening that removes a latent fail-OPEN, so it only ever makes the two-key gate REFUSE MORE (in fact it PREVENTS the no-clock executions the buggy code allowed). Nothing lowers a class and nothing here raises it to critical. human_approval is required regardless
owner: dmitry
human_approval: required
lane: standalone
placement: [contracts]
footprint:
  - .veldo/two_key.py
  - .veldo/action_executor.py
  - engine/.veldo/two_key.py
  - engine/.veldo/action_executor.py
  - packs/*/.veldo/two_key.py
  - packs/*/.veldo/action_executor.py
  - scripts/selftest.py
  - specs/WARP-1212-two-key-freshness-fail-closed.md
protected_paths: []
behavior_bearing: true
observability:
  logs: The two-key freshness refusal is a NAMED result from the existing closed taxonomy at the same
    decision point (authorization_expired for KEY 1, confirmation_expired for KEY 2), now also fired
    when a declared expiry cannot be verified for want of a clock; the detail string names the no-clock
    cause explicitly ("its declared expiry cannot be verified because no clock was supplied on the
    two-key path"), so a freshness refusal is diagnosable from the result alone (the stranger question).
  error_taxonomy: The refusal reasons stay the closed, named set the two-key gate already ships
    (authorization_expired, confirmation_expired); this hardening widens WHEN they fire (an unverifiable
    declared expiry now counts as expired) without adding, removing, or renaming any reason code, so the
    failure mode is legible from the message and no silent no-op is introduced.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Revert the no-clock branch of _expired at .veldo/two_key.py:173 from `return True` to `return False`,
      and the assertion that an expired-but-declared key with no clock REFUSES must go red by authorizing
      again, which is the exact latent fail-open both WARP-1207 reviews flagged; the positive controls with a
      clock must stay green, so the tightening is not a redesign.
    text: >
      The two-key freshness helper (_expired in .veldo/two_key.py, the single freshness check
      authorize() applies to both keys) FAILS CLOSED when there is no clock. Before, with no clock
      injected (now absent or empty) _expired returned False for a key that DECLARES an expiry - even a
      PAST one - so an expired-but-declared key PASSED the freshness check; the reviews of WARP-1207
      (proof/WARP-1207/verdict.json and verdict-2.json) both flagged this as a latent fail-OPEN in the
      CRITICAL two-key path. After this hardening the key is fresh ONLY when a real clock proves a
      declared expiry lies in the future; every other case (no expiry declared, or a declared expiry
      that cannot be verified because no clock was supplied) is treated as expired and the two-key gate
      REFUSES it by name, so a clock is REQUIRED on the two-key path. The change is minimal and surgical:
      only _expired's no-clock branch changes (from a fail-open return False to a fail-closed return
      True); no other guard, the two-distinct-keys guarantee, the digest binding, the self-separation, or
      the L2 single-confirmation path is touched or weakened. POSITIVE CONTROLS (the tightening is not a
      redesign): a valid unexpired pair WITH a clock still authorizes and runs both keys end to end
      against the fake system, and the with-a-clock expired and no-expiry refusals are unchanged.
  - id: AC2
    falsified_by: >
      Make ActionExecutor.execute substitute a wall-clock value when now is None, and the assertion that a
      VALID unexpired key with NO clock still REFUSES authorization_expired must go red, because the freshness
      control would then be silently disabled by omitting the clock; that leg is load-bearing, since an
      expired key refuses either way and only this one proves the control cannot be switched off from the call
      site.
    text: >
      An expired-or-unverifiable-freshness key can NEVER authorize, regardless of whether a clock was
      passed, proven at BOTH the gate and the executor surface (fail closed, degrade DOWN never up, C3).
      Through two_key.authorize and through ActionExecutor.execute(..., now=None): an EXPIRED-but-declared
      human authorization with no clock REFUSES authorization_expired (before, it authorized), and an
      EXPIRED-but-declared independent confirmation with no clock REFUSES confirmation_expired; a VALID
      unexpired key with no clock also REFUSES (authorization_expired) because its declared expiry is
      unverifiable, so the freshness control can never be silently disabled by omitting the clock; and
      execute(expired human, now=None) returns executed False with the reason named and no run (the
      reviewers' exact probe, which previously returned executed True). The neither-key fence is
      UNCHANGED (the fix returns before _expired on the both-absent path, so a call with neither key and
      no clock still refuses with the canonical requires_two_key value, drift-bound to
      action_executor.REFUSE_REQUIRES_TWO_KEY).
  - id: AC3
    falsified_by: >
      Point the in-memory mutation at a copy the probe does not import, so the reverted fix line never takes
      effect, and the assertion that the mutated copy AUTHORIZES again with reason None must go red; that
      assertion is what proves the one fix line is load-bearing rather than decorative, and the on-disk module
      must still be asserted byte-unchanged either side of it.
    text: >
      The fix is LOAD-BEARING (anti-vacuity, C1) and the engine stays byte-identical. A selftest reverts
      the one fix line to the pre-WARP-1212 return False in an IN-MEMORY copy of two_key.py and a
      formerly-refused input AUTHORIZES again (reason None) - both an expired-but-declared key with no
      clock AND a valid unexpired pair with no clock - while the real on-disk module REFUSES
      (authorization_expired), with the real .veldo/two_key.py byte-unchanged before and after the
      mutation. .veldo/two_key.py and .veldo/action_executor.py are re-synced BYTE-IDENTICAL across root,
      engine, and all 6 packs (aider, antigravity, codex, copilot, cursor, opencode) by cmp.
      The SECONDARY cosmetic fix both reviews flagged is included and clearly secondary: the ActionExecutor
      class docstring (previously "Anything irreversible or data-mutating REFUSES pending the two-key
      rule ... so this organ builds NO data-mutating execution path", false since W7) is corrected to say
      the organ ROUTES to the two-key rule and the data-mutating path exists only behind both keys. No
      protected path is touched (verify.sh, veldo-guard.sh, policy.yaml, policy_check.py and their
      engine twins unchanged; validate.py unedited). The full gate is GREEN with ZERO
      regressions across the corpus (validate.py all exit 0), RULE #1 is clean (ASCII hyphen only, no em
      or en dash, no prose double-hyphen), and the spec dogfoods HIGH risk with human_approval required.
required_evidence: [unit]
rollback: >
  Revert the commit. The behavioral change is a single line in .veldo/two_key.py's _expired helper (its
  no-clock branch flips from return False to return True) plus its docstring and two refusal-detail
  strings, re-synced byte-identical across engine and the 6 packs, and a secondary cosmetic
  ActionExecutor class-docstring correction in .veldo/action_executor.py (also re-synced), plus a
  selftest block and this spec. The change is strictly TIGHTENING (fail closed): reverting restores the
  latent fail-open the WARP-1207 reviews flagged and changes nothing else - no reason code, no other
  guard, no execution path, and no gate wiring (validate.py is unedited; the two-key gate is still not
  wired into run_all, that is WARP-1211 / W11). A repository that never configures the responder is
  unaffected either way; no live target is wired (NG1).
---

## Intent

Both independent fresh-context reviews of WARP-1207 (the two-key rule, W7 of PLAN-0012) returned the
same non-blocking finding: the two-key FRESHNESS (expiry) check FAILS OPEN when no clock is injected.
Concretely, `two_key.authorize(...)` and `action_executor.execute(...)` default `now=None`, and when
`now` is None the `_expired` helper returned False for a key that DECLARES an expiry (even a PAST one),
so an expired-but-declared key PASSED the freshness check with no clock supplied. A key with NO declared
expiry always refused (that part was already fail-closed), and the primary two-key guarantee (two
distinct, digest-bound, self-separated keys) held unconditionally, so this was latent and not reachable
in the shipped surface (all current callers inject a clock and no live driver exists). But it is a real
fail-OPEN in the CRITICAL two-key path, and both reviewers recommended closing it at the enforcement
point: require a clock on the two-key path and fail closed if it is absent (equivalently, have `_expired`
refuse a declared-but-unverifiable expiry when no clock is supplied) so a future caller cannot silently
disable the freshness control. This spec is that hardening, in the shape of WARP-0113 and WARP-0114 (a
small standalone spec that closes a defect a prior independent review found), the discipline C1 demands
in this plan: the refusals are the product, so a fail-open in a refusal is a defect worth its own gated
unit of work.

## Context

- STANDALONE HARDENING LANE, not plan work. Exactly as WARP-0113 ("Harden enforcement per the WARP-0100
  independent review findings") and WARP-0114 closed review- and dogfood-found defects without being
  added to PLAN-0001's work list, this spec closes a WARP-1207 review finding without being added to
  PLAN-0012's work list. It declares no `plan`/`work`/`lane`, PLAN-0012's plan file is untouched, and the
  plan's completed W7 stays as shipped; this spec references W7, it does not reopen it. The number
  WARP-1212 follows the plan's W1..W11 block (WARP-1201..WARP-1211), the same way WARP-0113/0114 followed
  the PLAN-0001 range.
- THE FIX IS AT THE ENFORCEMENT POINT, and it is one line of behavior. `_expired` is the single freshness
  check `authorize` applies to KEY 1 and KEY 2. Its no-clock branch changes from `return False` (fresh:
  the fail-open) to `return True` (expired: fail closed). Because the "no declared expiry" branch already
  returned True, the post-fix helper returns False (fresh) ONLY when a real clock proves a declared
  expiry is in the future - every other case fails closed. This simultaneously satisfies both forms the
  reviewers named: "require a clock on the two-key path and refuse if it is absent" and "refuse a
  declared-but-unverifiable expiry when no clock is supplied" are the same behavior once the no-expiry
  case is already closed. No reason code is added or renamed; the existing authorization_expired /
  confirmation_expired reasons now also fire for the unverifiable-no-clock case, with the detail string
  naming the cause.
- RISK: HIGH, one review. The change edits the two-key organ, so C2 floors it at HIGH with recorded human
  approval. It is NOT critical: C2 puts the CRITICAL tier on a spec that OPENS or WIDENS a data-mutating
  execution path, which WARP-1207 did (a reachable data-mutating run now exists) and which this spec does
  not - it builds no path and only ever REFUSES more, so it cannot cause any run that would not have
  happened before (it prevents the no-clock runs the fail-open allowed). HIGH means one independent
  fresh-context review and a recorded founder approval to land; the builder stops at review.
- ANTI-VACUITY (C1). The fix ships as a negative test that proves the refusal: an expired-but-declared
  key with no clock now REFUSES by name where it previously passed, and the mutation that REVERTS the fix
  (the one line back to `return False`) turns that assertion RED (the formerly-refused input authorizes),
  with the real module byte-unchanged. Positive controls keep it honest: a valid unexpired pair WITH a
  clock still executes both keys, and the neither-key and with-a-clock refusals are unchanged.

## Out of scope

- No redesign of the two-key rule. The two-distinct-keys guarantee, the digest binding, the
  self-separation (NG4), the named taxonomy, and the L2 single-confirmation path are untouched; this is a
  surgical tightening of one freshness branch.
- No gate wiring and no live target. Landing a two-key check into validate.py run_all and the init
  lay-down is still WARP-1211 (W11); validate.py is unedited. No live target is wired (a separate
  per-system human-approved enablement act, NG1). It starts no process, thread, or timer (NG3).
- No change to the L2 single-confirmation freshness posture. The reversible-action L2 path
  (_check_confirmation) never carried an expiry check and this spec does not add one; the freshness
  control this hardens is the two-key path's, which is the CRITICAL one the reviews flagged.

## Notes

- What a human approving this vouches for: that the two-key freshness (expiry) control now fails CLOSED
  when no clock is available to verify a declared expiry - an expired-or-unverifiable-freshness key can
  never authorize regardless of whether a clock was passed - so a future caller (the WARP-1208 driver or
  a live enablement) cannot silently disable freshness by omitting the clock; that a clock is now
  required on the two-key path; that the change is a pure fail-closed tightening that weakens no existing
  refusal and opens no execution path; that the neither-key fence and the with-a-clock behavior are
  unchanged and a valid unexpired pair with a clock still executes; and that the engine copies are
  byte-identical with no protected path touched.
- What the reviewer should scrutinize: that the one-line change is truly fail-closed and cannot be
  reached in a way that authorizes without a clock (probe execute/authorize with now=None across
  expired, no-expiry, and valid-unexpired keys and confirm every one refuses); that the neither-key path
  still returns requires_two_key before any freshness check (the fix must not disturb it); that no other
  guard, reason code, or the L2 path changed; that the revert-the-fix mutation genuinely turns the
  anti-vacuity assertion red (the fix is load-bearing, not cosmetic); and that the HIGH-not-CRITICAL
  determination holds (no data-mutating execution path is opened or widened).
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
</content>
</invoke>
