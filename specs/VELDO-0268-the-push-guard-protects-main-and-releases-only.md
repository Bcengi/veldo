---
schema: veldo.spec/v1
id: VELDO-0268
title: The push guard checks only pushes to protected refs, main, master, release branches and tags as the policy declares them, and never blocks a working branch, while landing keeps the green gate and every approval
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0058]
placement: [enforcement]
protected_paths: ["scripts/veldo-guard.sh", "engine/scripts/veldo-guard.sh", ".veldo/policy_check.py", "engine/.veldo/policy_check.py", ".veldo/policy.yaml"]
footprint:
  - "scripts/veldo-guard.sh"
  - "engine/scripts/veldo-guard.sh"
  - "packs/claude/scripts/veldo-guard.sh"
  - ".veldo/policy_check.py"
  - "engine/.veldo/policy_check.py"
  - ".veldo/policy.yaml"
  - "engine/.veldo/policy.yaml"
  - "engine/AGENTS.md"
  - "scripts/suites/141_veldo_0268_protected_refs.py"
  - "scripts/suites/manifest.json"
  - "specs/VELDO-0268-the-push-guard-protects-main-and-releases-only.md"
  - "specs/index.md"
  - "proof/VELDO-0268/**"
behavior_bearing: true
observability:
  logs: >
    For every push or merge it inspects, the guard prints one line per destination ref to standard
    error: the ref, whether it is protected, the pattern that made it protected and the policy file that
    pattern came from, and either "not protected: the gate check applies when this lands" or the checks
    it then runs. A destination it could not resolve is printed as such, with the reason, and is treated
    as protected.
  metrics: >
    None added.
  traces: >
    None added. The guard's existing emergency.push event is unchanged.
  error_taxonomy: >
    No new refusal. Every block message the guard and policy_check print today is unchanged, and is now
    printed only for a protected destination. A policy whose protected_refs key is malformed refuses
    the push with "VELDO guard: blocked. protected_refs in <file> cannot be read", which is the fail
    closed direction.
acceptance_criteria:
  - id: AC1
    text: >
      The protected set is declared, never hard-coded in the guard. .veldo/policy.yaml gains a
      protected_refs list of full ref name patterns (fnmatch, matched against refs/heads/... and
      refs/tags/...); the engine's policy.yaml ships refs/heads/main, refs/heads/master,
      refs/heads/release, refs/heads/release/*, refs/heads/release-* and refs/tags/*, and this
      repository's policy carries the same list. The guard and policy_check read one function,
      protected_ref(name), in policy_check.py, whose set is the union of the patterns in the working
      tree's policy, the policy committed at the local trunk ref (refs/heads/main, so a candidate cannot
      shrink the set by editing its own policy before it pushes main), and the installation's policy
      when the installed-policy runner sets POLICY (VELDO-0058). Anything may add a ref; nothing removes
      one. When no source declares protected_refs, every ref is protected, which is today's behavior.
    falsified_by: >
      The new suite builds fixture repositories and calls protected_ref for refs/heads/main,
      refs/heads/release/1.2, refs/tags/v1, refs/heads/agent/claude/x and refs/heads/mainline: protected,
      protected, protected, not, not. A working tree policy that drops main still yields main protected
      when the trunk's committed policy lists it; a policy with no key protects agent/claude/x. Registered
      mutations: (1) the union reads only the working tree: the shrink row goes red; (2) the missing key
      means nothing protected: the fail-closed row goes red.
  - id: AC2
    text: >
      A push whose destinations are all unprotected is never blocked by the gate stamp, the proof
      manifest, the reuse evidence or policy_check, on either path. On the git pre-push path the guard
      takes the destination ref from VELDO_GUARD_REF, set per ref by the hook beside VELDO_GUARD_COMMIT
      (the interface core's hook already uses for the commit). On the PreToolUse path the guard resolves
      destinations with git itself, by a porcelain dry run of the same push with hooks disabled, never by
      parsing the command text; a command it cannot reproduce, or a dry run that fails, counts as a push
      to a protected ref. gh pr create moves no protected ref and is not blocked. A push with several
      destinations is judged per destination: the unprotected ones pass, and the push is blocked only if
      a protected destination fails its checks.
    falsified_by: >
      The suite drives the guard over a fixture repository whose gate stamp is red and that has no proof
      manifest: git push of agent/claude/x to a local bare remote, through a pre-push hook and through a
      PreToolUse payload, exits 0 and the remote has the branch; the same push of main exits 2 on both
      paths; a push of both refs at once exits 2 and names main only; a payload of "cd x && git push" whose
      dry run fails exits 2. Registered mutations: (1) the guard reads the destination from the command
      text: a payload "git push origin HEAD:main" is let through and the row goes red; (2) an unresolved
      destination counts as unprotected: the fail-closed row goes red.
  - id: AC3
    text: >
      A push to a protected ref keeps every check exactly as today: the gate stamp for the commit, the
      reuse evidence, the proof manifest, and policy_check's protected path approval block, emergency debt
      and unresolved objections. A merge into a protected branch (git merge while it is checked out, gh pr
      merge whose base is protected, its base read from gh, unresolvable counted as protected) is judged
      the same way. Landing, the lander moving the trunk through its installed-policy run, is unchanged
      and still requires the green gate and every approval; the emergency lane is unchanged.
    falsified_by: >
      The suite repeats, for a push of main, the existing refusal rows of the guard and policy_check (red
      stamp, missing manifest, protected path without approval, open emergency debt, unresolved
      objection) and requires the same exit code and message as before the change, byte for byte; the
      lander's refusal of a protected path without approval is unchanged. Registered mutation: the
      approval block is skipped for refs/tags/*: the tag row goes red.
  - id: AC4
    text: >
      The three copies of the guard (scripts/, engine/scripts/, packs/claude/scripts/) and the two of
      policy_check.py stay byte-identical, so the template-sync check stays green, and engine/AGENTS.md
      states the rule in one paragraph: the push guard protects the refs the policy names; landing is
      where the gate and approvals bind; working branches push freely.
    falsified_by: >
      The gate's existing template-sync check reds on any drift between the copies; the suite's
      documentation row reads the paragraph from engine/AGENTS.md and reds when it is missing.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. The guard again judges every push and merge whatever the destination, as today.
  The protected_refs key left in a policy file is read by nothing after the revert. No record, stamp or
  event changes shape, so nothing needs migrating.
---

## Intent

Work must be able to leave the machine while it is in progress. The owner, Telegram 39642: "I hate that
we can't push for this long. This is a serious problem." In Telegram 39647 the owner agreed that the
gate check guards only main and releases, never a working branch. A working branch is a backup and a
review surface, not a release; the gate and the approvals bind where the trunk moves.

## Context

- scripts/veldo-guard.sh is a PreToolUse hook (wired in .claude/settings.json) that matches any
  "git push", "git merge", "gh pr merge" or "gh pr create" in a command and then blocks unless the gate
  is green for HEAD, the reuse evidence holds, a proof manifest names HEAD, and .veldo/policy_check.py
  passes. It does not look at the destination at all, so a backup push of a working branch is blocked
  whenever its gate is not green, which for a branch in progress is most of the time. This repository
  has no git pre-push hook of its own; core has one (.githooks/pre-push, core.hooksPath), which calls the
  guard once per ref with VELDO_GUARD_COMMIT and does not pass the destination either.
- core-integration had 3,678 commits on this disk only for that reason (the audit's decision A). A
  nightly push of every working branch already runs from myday/scripts/push_work_branches.sh with
  the pre-push hook skipped; it keeps its own protected list (main, master, release*, production) and is not changed
  here. This spec removes the reason it has to bypass the hook.
- policy_check.py already separates its policy source (POLICY) and range base (BASE) from the subject
  tree so a candidate cannot weaken the rules it is judged by (VELDO-0058 AC3). The union rule of AC1
  follows the same reasoning for the protected set.

How core gets the same change. Core does not take engine files by re-laying them: its
.veldo/installed.json says 3.10.1 laid from this engine on 2026-09-03, but its scripts/veldo-guard.sh
(477 lines) and .veldo/policy_check.py are core's own versions, changed since by core's specifications
(VELDO-0162, VELDO-0182 and VELDO-0342 in core's numbering), and its .githooks/pre-push exists only in
core. Re-laying the engine would overwrite those changes. So after this spec lands, a core specification
ports the same rule through core's normal path: protected_refs added to core's .veldo/policy.yaml
(including refs/heads/production, which push_work_branches.sh already treats as protected), the
protected_ref function and union rule added to core's policy_check.py, core's guard made to stand down
for an unprotected destination, and core's pre-push hook made to pass the remote ref it already reads
as VELDO_GUARD_REF. It lands through core's own gate and the owner's approval for those protected
files. The owner is told when it is drafted.

## Out of scope

Shipping a git pre-push hook in the engine or in this repository; server-side branch protection; the
nightly push script; what the gate checks; any change to the lander; core's own copies, which change
through the core specification described above.

## What the reviewer judges

- No path lets a push or merge that moves a protected ref skip a check it ran before.
- The destination is always git's own answer, and every case where it is not known is protected.
- An agent cannot unprotect a ref by editing the policy in the tree it is about to push.
- Working branches are truly never blocked by the gate stamp, on both paths.

## History

2026-11-07: drafted on the owner's messages, Telegram 39642 ("I hate that we can't push for this long.
This is a serious problem") and 39647 (agreement that the gate check guards only main and releases,
never a working branch, with a nightly push of all working branches, which now runs from
myday/scripts/push_work_branches.sh). A draft: only the owner marks it ready.

2026-11-07: ready on the owner's approval, Telegram 39694 ("Ok") to the summary in 39693.
