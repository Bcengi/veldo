---
schema: veldo.plan/v1
id: PLAN-0009
title: VELDO Fleet distribution - ship the fleet as an installable per-repo capability with a real CLI, in-session workers, persistent per-account pacing, and opt-in resume
kind: mvp
status: released
revision: 2
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-19T14:10:00Z
risk: standard

outcomes:
  - id: O1
    becomes_true: The fleet is INSTALLABLE. A repo that adopts VELDO gets the fleet - the seven fleet
      modules ship in the canonical engine, /veldo:init lays them down, and every pack carries them -
      and a real veldo CLI exposes the fleet, worker, status, and account commands. Nothing has to be
      copied out of the veldo repo by hand.
    measure: a fresh repo set up only from the shipped plugin (or a pack) runs veldo work and veldo
      fleet N end to end, with no file copied from the veldo repo, and the drift and conformance checks
      cover the fleet modules as engine
  - id: O2
    becomes_true: A claimed unit is actually built and reviewed by real agents. The work-loop
      dispatch seam is filled so veldo work claims a ready spec, builds it through the VELDO loop, gets
      an independent fresh-context review, and lands it, with no human hand-driving the steps.
    measure: veldo work in a repo with ready work produces a landed, independently reviewed change
      through the full loop, and a claimed review unit gets a verdict
  - id: O3
    becomes_true: Workers run in-session and never detached, and you choose which account each runs
      under. Each account is logged in once into its own persisted profile, and veldo work --account
      NAME (or veldo fleet N) launches as many concurrent sessions as accounts, one account per
      session, reusing saved auth with no relogin.
    measure: two accounts each registered once run concurrently, one session per account, with no
      login prompt, and self-divide the frontier through the claim ledger
  - id: O4
    becomes_true: The pool paces per account and resumes per account. The governor tracks each
      account's own session and weekly budget, backs off an account at its limit while other accounts
      keep going, and an in-session resume-waiter resumes a backed-off account at its reset without
      any detached process.
    measure: with one account at its limit, its workers wait for its reset while another account's
      workers keep building, and the limited account resumes automatically at its reset inside the
      living session
  - id: O5
    becomes_true: The docs and the honesty manifest tell the truth about the fleet. The README, the
      plugin guide, the setup scaling stages, the runbook, and capabilities.yaml describe the fleet
      exactly as shipped, with no capability claimed that the adopter's tree does not carry.
    measure: every fleet command named in the docs exists and runs, and capabilities.yaml marks a
      fleet capability mechanical only where shipping code backs it in an adopter's tree

non_goals:
  - id: NG1
    text: Detached or headless background workers. A worker is a vanilla in-session Claude Code
      session (PLAN-0007 NG1, restated). The optional external supervisor (open decision D1) only
      LAUNCHES a session at a budget-reset time; it never runs autonomous headless work itself, and
      it is off by default.
  - id: NG2
    text: A hosted scheduler, queue service, database, or message bus (PLAN-0007 NG2, restated).
      Coordination stays git plus the shared run registry plus the claim ledger.
  - id: NG3
    text: Rewriting the fleet control logic. PLAN-0007 Y1 through Y7 are shipped and stay; this plan
      FILLS their seams (dispatcher, spawner, resume-waiter), ships them in the engine, and wraps them
      in a CLI. Only the seam implementations, the CLI, the account model, distribution, and docs are
      new.
  - id: NG4
    text: Per-tool native marketplace publishing (inherited deferral). The fleet ships inside the
      packs assembled in this repo, not as a separately published per-tool extension.
  - id: NG5
    text: The fleet worker role on the IDE cluster. The IDE packs (Cursor, Copilot) carry the engine
      modules for byte-identical no-drift, but the autonomous worker role is a CLI-agent capability
      (PLAN-0008 NG5), documented not enforced on the IDE packs.

constraints:
  - id: C1
    text: Every item stays proportionate and is built through VELDO itself, with the same gate, proof,
      and independent review.
  - id: C2
    text: Workers are vanilla and in-session, never rogue or detached processes. The real
      WorkerSpawner spawns an in-session worker (the same in-session parallel mechanism a human
      session uses); the multi-account path is explicit account selection, not an auto-spawner of
      detached sessions.
  - id: C3
    text: Coordination state (claims, run progress, shared-dep ref counts) lives under the git common
      dir, shared across worktrees, outside git history; durable results land on the trunk. A fully
      drained worker stops cleanly; a backed-off worker waits, it does not spin.
  - id: C4
    text: The fleet ships in the CANONICAL ENGINE so every pack's copy is byte-identical and the
      drift-check plus cross-pack conformance cover the new modules; adding the modules to the engine
      forces re-assembling every pack.
  - id: C5
    text: Account selection is explicit and auth PERSISTS per account. An account is logged in once
      into its own profile (its own config dir holding its credentials); thereafter selecting it by
      name reuses the saved auth with no relogin. The governor paces each account against its own
      budget.
  - id: C6
    text: capabilities.yaml stays honest. A fleet capability is marked mechanical only when shipping
      code backs it in the adopter's tree; while this plan is in flight the manifest states the true
      current status, not the target.

feature_tree:
  - id: F1
    title: Real seams - the dispatcher, the in-session worker spawner, and the resume-waiter filled so
      the fleet runs end to end with live agents in-session
    outcome_refs: [O2, O3, O4]
  - id: F2
    title: The veldo CLI and the account model - one executable exposing work, fleet, status, and
      account commands, with persistent per-account auth and by-name selection
    outcome_refs: [O1, O3]
  - id: F3
    title: Distribution - the fleet modules ship in the engine, /veldo:init and every pack carry them,
      drift and conformance cover them, and capabilities.yaml is honest
    outcome_refs: [O1, O5]
  - id: F4
    title: Per-account pacing and opt-in resume - the governor tracks each account's budget, the
      in-session resume-waiter resumes a backed-off account at its reset, and an opt-in external
      supervisor is the only way to survive a fully killed session
    outcome_refs: [O4]
  - id: F5
    title: Docs made true - the README, plugin guide, setup scaling, runbook, and the honesty
      manifest describe the fleet exactly as shipped
    outcome_refs: [O5]
  - id: F6
    title: Release - a version bump distributing the installable fleet
    outcome_refs: [O1]

work:
  - item: W1
    spec: WARP-0901
    title: Real dispatcher - fill the work-loop dispatch seam so a claimed BUILD unit is built through
      the VELDO loop (veldo run) and a claimed REVIEW unit gets a fresh-context independent reviewer,
      the durable outcome (a landed build flips the spec to shipped) driving the frontier; the fake
      dispatcher is kept for control tests and the real path is gate-tested over a throwaway repo
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: W2
    spec: WARP-0902
    title: In-session worker spawner and account model - fill the fleet spawn seam with a real
      in-session spawner (never detached), plus veldo account add that logs an account in once into its
      own persisted profile and by-name selection (veldo work --account NAME) that reuses saved auth
      with no relogin; multi-account is many one-account sessions self-dividing the frontier
    feature_refs: [F1, F2]
    depends_on: [WARP-0901]
    order: 20
  - item: W3
    spec: WARP-0903
    title: Per-account pacing and in-session resume-waiter - the governor tracks each account's own
      session and weekly budget so an account at its limit backs off while others keep going, and the
      launcher wait seam is filled with an opt-in in-session waiter that sleeps to that account's
      reset and re-checks before resuming, spawning nothing
    feature_refs: [F4]
    depends_on: [WARP-0902]
    order: 30
  - item: W4
    spec: WARP-0904
    title: The veldo CLI - a real executable (console entrypoint) dispatching work, fleet, status, and
      account subcommands to the existing modules, so the commands the README promises actually exist;
      no new control logic, just the front door, gate-tested for argument routing and honest errors
    feature_refs: [F2]
    depends_on: [WARP-0901, WARP-0902, WARP-0903]
    order: 40
  - item: W5
    spec: WARP-0905
    title: Ship the fleet in the engine - move the fleet modules and the CLI into the canonical engine
      (engine) and ENGINE_GLOBS so /veldo:init lays them down and every pack carries them,
      re-sync the packs byte-identical, extend the drift-check and cross-pack conformance to the fleet
      modules, and make capabilities.yaml honest about what now ships
    feature_refs: [F3]
    depends_on: [WARP-0904]
    order: 50
  - item: W6
    spec: WARP-0906
    title: Docs made true - correct the README fleet claim to what actually ships, add an accurate
      fleet section to the plugin guide and to the setup scaling stages, cover veldo fleet and veldo
      work and account selection in the runbook, so a team adopting through the docs finds the real,
      installable fleet
    feature_refs: [F5]
    depends_on: [WARP-0905]
    order: 60
  - item: W7
    spec: WARP-0907
    title: Opt-in external resume supervisor - a user-level systemd timer (off by default, opt-in,
      visible) that at an account's budget-reset time launches a fresh in-session fleet session so the
      pool survives a fully killed session; it launches a session and does no autonomous work itself.
      GATED on open decision D1
    feature_refs: [F4]
    depends_on: [WARP-0903]
    order: 70
  - item: W8
    spec: WARP-0908
    title: Release VELDO Fleet distribution v1 - bump the plugin version, record the shipped fleet in
      the capability manifest, update the docs, and mark the plan released once the release check is
      green
    feature_refs: [F6]
    depends_on: [WARP-0905, WARP-0906]
    order: 80

regression:
  journeys:
    - id: RJ1
      title: Two accounts, each registered once, run concurrently one session per account with no
        relogin, and self-divide the frontier through the claim ledger
      activation: {when: after:WARP-0902}
      owner_spec: WARP-0902
      profiles: [per_spec, release]
      suite: fleet account and claim selftest
    - id: RJ2
      title: A claimed build unit is built through the VELDO loop and independently reviewed and landed,
        and a claimed review unit gets a verdict, via the real dispatcher
      activation: {when: after:WARP-0901}
      owner_spec: WARP-0901
      profiles: [per_spec, release]
      suite: dispatcher selftest
    - id: RJ3
      title: An account at its limit backs off and resumes at its own reset inside the living session
        while another account's workers keep building
      activation: {when: after:WARP-0903}
      owner_spec: WARP-0903
      profiles: [per_spec, release]
      suite: per-account governor and resume-waiter selftest
    - id: RJ4
      title: The shipped fleet runs in a FRESH repo set up only from the plugin, with no file copied
        from the veldo repo, proving distribution
      activation: {when: after:WARP-0905}
      owner_spec: WARP-0905
      profiles: [per_spec, release]
      suite: fresh-repo fleet distribution journey
    - id: RJ5
      title: The existing VELDO gate stays green across every item (selftest passes, contracts pass, no
        drift) so shipping the fleet never regresses the home repo
      activation: {when: start}
      profiles: [per_spec, release]
      suite: scripts/verify.sh (selftest slot)

release:
  milestone: VELDO Fleet distribution v1 - the fleet is installable per-repo through the plugin and
    every pack, driven by a real veldo CLI, with in-session workers, explicit persistent-auth account
    selection, per-account pacing and in-session resume, and honest docs
  version: plugin 3.5.0
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: each item is additive (a filled seam, a new CLI, engine modules, docs). Reverting the
    release commit withdraws the version bump; the fleet modules can be removed from the engine to
    return to the pre-distribution state, leaving PLAN-0007's control logic intact in the repo.
  observation:
    duration: run veldo fleet across two accounts on a real ready frontier and confirm self-division,
      per-account backoff and in-session resume, and a clean drain before the version is defaulted on

open_decisions: []

resolved_decisions:
  - id: D1
    text: Auto-relaunch after FULL account exhaustion. In-session pacing and the resume-waiter (W3)
      handle backoff and resume while the session process is alive; but a session that is fully killed
      cannot restart itself. Option A (default, no supervisor - W7 is dropped) - stay fully in-session
      and accept that a truly killed session needs a one-word human restart. Option B (opt-in, off by
      default - W7 is built) - a user-level systemd timer launches a fresh in-session fleet session at
      the reset time. Recommended: build W7 as an opt-in, off by default, so the escape hatch exists
      but nothing persistent runs unless the founder turns it on.
    resolved: true
    resolved_at: 2026-07-19
    resolution: Option B, founder-authorized 2026-07-19. Build W7 as an OPT-IN, OFF-BY-DEFAULT external
      supervisor. The in-session resume-waiter (W3) stays the DEFAULT; the external systemd-timer
      supervisor only launches a fresh session at a budget-reset time and never runs headless work, and
      nothing persistent exists unless the founder explicitly installs it. WARP-0907 is unblocked and
      built.
    blocks: []

---

## Intent

The VELDO Fleet already exists as real, gate-tested control logic (PLAN-0007 Y1 through Y7: the claim
ledger, the global frontier, the worker loop, the serialized lander, environment provisioning, the
token governor, and the fleet launcher). But three seams are unfilled (the work-loop dispatcher, the
worker spawner, and the resume-waiter), there is no veldo CLI, and none of it is distributed: the
modules live only in this repo's own .veldo/, so /veldo:init does not lay them down and no pack carries
them, while the README and capabilities.yaml present the fleet as an installed capability. This plan
makes the fleet REAL and SHIPPED: it fills the seams with in-session implementations, adds a real veldo
CLI with explicit persistent-auth account selection, ships the modules in the canonical engine so
every adopter and every pack gets them, paces and resumes per account, and makes the docs and the
honesty manifest tell the truth.

## Context

This is the delta on top of PLAN-0007, not a rebuild. PLAN-0007's control logic is shipped and stays;
its own capability notes state that the dispatcher and the spawner and the waiter are seams driven by
fakes in the gate, and that the multi-account path is a documented procedure rather than an
auto-spawner. Filling those seams in-session, wrapping them in a CLI, and shipping them in the engine
is what turns "the fleet was built" into "an adopter can run the fleet." The founder's requirements
(2026-07-19): select which account runs each session; run as many concurrent sessions as accounts,
one per account, without relogin (persistent per-account auth); and keep everything inside the
no-rogue-processes rule (workers in-session; any relaunch-after-exhaustion mechanism opt-in and
visible).

## Ordered delivery rationale

W1 (the dispatcher) is the root of real work: without it a claimed unit is not actually built. W2 (the
in-session spawner and the account model) depends on it so a spawned worker does real work. W3
(per-account pacing and the in-session resume-waiter) depends on the account model. W4 (the CLI) wires
the front door once the pieces behind it are real. W5 ships the whole thing in the engine and proves
no drift. W6 makes the docs true against what W5 shipped. W7 (the opt-in external supervisor) is gated
on D1 and hangs off W3. W8 releases once the work is shipped and regression is green.

## Out of scope

Detached or headless workers (NG1); a hosted scheduler, queue, database, or bus (NG2); rewriting the
fleet control logic (NG3); per-tool native marketplace publishing (NG4); the autonomous worker role on
the IDE packs (NG5). The external supervisor is the only path to surviving a fully killed session and
it is opt-in and off by default, gated on D1.

## Revisions

Revision 1 (2026-07-19): created from the fleet-distribution design and approved by the founder (his
decision to ship the fleet, plus the account-selection and persistent-auth requirements and the
no-rogue-processes constraint on any relaunch mechanism). The auto-relaunch-after-full-exhaustion form
is recorded as open decision D1, blocking only the opt-in external supervisor (W7), so all other work
proceeds while that decision is settled.

Revision 2 (2026-07-19): open decision D1 resolved by the founder as Option B - build W7 as an OPT-IN,
OFF-BY-DEFAULT external supervisor, with the in-session resume-waiter (W3) as the default and the
external systemd-timer supervisor only launching a fresh session at a budget-reset time, never running
headless work and never present unless the founder explicitly installs it. D1 is moved to
resolved_decisions with its resolution and its blocks list cleared, so it no longer blocks WARP-0907;
WARP-0907 is built and shipped in this revision (W7 of 8). Only WARP-0908 (the release) remains.
