---
schema: veldo.spec/v1
id: VELDO-0212
title: When Claude Code or Codex releases a new version, the factory installs it into its own engine store beside the qualified one, runs the full engine qualification against it, and switches to it by itself only when the qualification passes, while running jobs finish on the version they started and a failure keeps the last qualified version and is reported
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W152
plan_revision: 4
depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0127, VELDO-0128, VELDO-0141, VELDO-0154, VELDO-0155, VELDO-0156, VELDO-0172, VELDO-0173, VELDO-0186]
placement: [engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_engine_store*.py"
  - ".veldo/control_engine_store*.py"
  - "engine/.veldo/control_engine_claude*.py"
  - ".veldo/control_engine_claude*.py"
  - "engine/.veldo/control_engine_codex*.py"
  - ".veldo/control_engine_codex*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "engine/runtime/claude-qualification*.json"
  - ".veldo/runtime/claude-qualification*.json"
  - "engine/runtime/codex-qualification*.json"
  - ".veldo/runtime/codex-qualification*.json"
  - "engine/runtime/engine-qualification-set.json"
  - ".veldo/runtime/engine-qualification-set.json"
  - "bin/veldo"
  - "engine/bin/veldo"
  - "proof/VELDO-0061/qualification.py"
  - "proof/VELDO-0127/wire_fixture.py"
  - "scripts/suites/*_veldo_0212_*.py"
  - "scripts/suites/78_veldo_0060_claude_adapter.py"
  - "scripts/suites/79_veldo_0061_codex_adapter.py"
  - "scripts/suites/82_veldo_0173_tool_registry.py"
  - "scripts/suites/86_veldo_0127_agent_configuration.py"
  - "scripts/suites/87_veldo_0127_codex_delivery.py"
  - "scripts/suites/88_veldo_0127_feature_defaults.py"
  - "scripts/suites/89_veldo_0127_feature_listing.py"
  - "scripts/suites/90_veldo_0127_feature_profile.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0212-automatic-engine-upgrades.md"
  - "specs/index.md"
  - "proof/VELDO-0212/*"
behavior_bearing: true
observability:
  logs: >
    Record each release check (engine, channel, version found, outcome), each install (version, the
    vendor's checksum, the computed digest, the store path), each qualification run (version, digest, the
    qualification set's digest, every row and its result, the proof directory), each pointer switch
    (engine, from version and digest, to version and digest) and each copy removed from the store with
    the reason it was no longer referenced; never a credential or a login token.
  metrics: >
    Count release checks by outcome, installs by outcome, qualification runs by outcome, pointer
    switches, launches per engine version, and copies kept and removed by the store.
  traces: >
    Join each launch to the engine version and digest it bound and the pointer state it read, and each
    pointer switch to the install and the qualification run that allowed it.
  error_taxonomy: >
    Distinguish a release channel that cannot be read (unavailable_service:engine_release:<engine>), a
    download whose bytes do not match the vendor's published checksum
    (binding_mismatch:engine_checksum:<engine>:<version>), a qualification that did not pass
    (missing_evidence:engine_qualification:<engine>:<version>:<row>), a switch refused because the
    pointer moved while the qualification ran (stale_subject:engine_pointer:<engine>), and a store copy
    whose digest changed or that is gone (binding_mismatch:engine_store:<engine>:<digest>), names this
    specification adds; never label an unknown outcome as a pass.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A new release of Claude Code or Codex is found on the vendor's own release channel and
      installed into the factory's engine store beside the current version, checked against the
      vendor's published checksum, and nothing the running version uses is touched. Set and
      completeness: The release check runs in the installed service at the interval the factory
      configuration names (six hours by default) and on the owner's `veldo engines check`. For Codex it
      reads the `latest` dist-tag of `@openai/codex` from the npm registry and downloads the Linux x64
      platform package tarball, checked against the registry's `dist.integrity`; the tarball is
      unpacked, and no package script ever runs. For Claude Code it reads the `latest` pointer of the
      release bucket the vendor's native installer reads, then that version's `manifest.json`, and
      downloads the Linux x64 binary, checked against the manifest's SHA-256 for that platform. The copy
      is written beside, made read only (mode 0555, owned by the factory's account) and renamed into
      `<state root>/engines/<engine>/sha256-<digest>/`; a download that fails the checksum is removed and
      refused by name (binding_mismatch:engine_checksum:<engine>:<version>). The active copy, its
      directory and the active pointer are byte for byte the same before and after. The suite serves a
      fixture registry and a fixture bucket on loopback with a new version of each engine, one of them
      with a wrong checksum. Falsifier: Skip the checksum comparison, and the wrong-checksum row must
      fail on a copy in the store.
    falsified_by: >
      Skip the checksum comparison, and the wrong-checksum row must fail on a copy in the store.
  - id: AC2
    text: >
      Claim: A newly installed version runs the factory's full engine qualification in isolation, and
      only when it passes does the active pointer move to it, in one atomic step, while every job already
      running finishes on the version it started with. Set and completeness: The qualification set is
      one declared list, `runtime/engine-qualification-set.json`, of the checks that gate a hand-made
      qualification change today: the stream and terminal formats (VELDO-0062, VELDO-0172), the adapter
      lifecycle and pinned launch (VELDO-0060, VELDO-0061), the everything-off baseline, the paid-API
      guard and credential handling (VELDO-0155, VELDO-0156), the sandbox and feature flags and the
      capability inventory, every registered tool and feature classified (VELDO-0127, VELDO-0173). The
      hand-made path and the automatic one both read that file, so neither can run fewer checks. The
      run uses the version's store copy through the one engine selector the suites read (the
      VELDO_CODEX_BINARY selector of the codex-0162-host work, generalized to both engines), a scratch
      state root and a scratch home with no owner login or credential in reach, and no live model call.
      The record extractors write the version's qualification record into the scratch root, and on a
      pass the record is installed beside the earlier versions' records (Claude Code's `versions` map,
      Codex's per-version records). The pointer `<state root>/engines/<engine>/current` is then replaced
      by one rename; a pointer that moved since the run began is not overwritten
      (stale_subject:engine_pointer:<engine>). A launch reads the pointer once at bind, records the
      version and digest in its execution record (VELDO-0141) and runs the store copy by its full path,
      so a job never reads the pointer again. The suite starts a long fake job on the old version,
      completes a passing qualification of a new one, and requires the job to finish on the old copy and
      the next launch to bind the new one. Falsifier: Leave one check out of the set the automatic path
      reads, and the set-equality row must fail on the missing check.
    falsified_by: >
      Leave one check out of the set the automatic path reads, and the set-equality row must fail on the
      missing check.
  - id: AC3
    text: >
      Claim: A failed qualification keeps the last qualified version active, records what failed, reports
      it to the owner once, and is never retried in a loop. Set and completeness: The pointer, the active
      copy and the installed records are unchanged after a failure. The failure record names the engine,
      the version, the digest, the qualification set's digest, every failing row with its first lines of
      output, and the proof directory that holds the rest, under
      missing_evidence:engine_qualification:<engine>:<version>:<row>. It is written to the factory
      journal as one `engine_qualification_failed` event, which VELDO-0128 reports to the owner on
      Telegram, the channel his assistant reads. A version and digest that failed are run again only when
      the qualification set's digest changes (a factory release that carries a fix), when a newer version
      appears, or on the owner's `veldo engines requalify <engine> <version>`; a release check that finds
      the same failed version does nothing and sends nothing. The suite qualifies a fixture version with
      an unclassified tool (the Codex 0.162 case), then runs ten more release checks. Falsifier: Requalify
      the failed version at every release check, and the no-loop row must fail on a second qualification
      run and a second report.
    falsified_by: >
      Requalify the failed version at every release check, and the no-loop row must fail on a second
      qualification run and a second report.
  - id: AC4
    text: >
      Claim: Every engine the factory runs, in its jobs, gates and suites, is a factory-owned store copy
      referenced by digest, so a vendor auto-updater, a global package upgrade or a pruned vendor cache
      cannot change or remove it, and an old copy stays until nothing references it. Set and
      completeness: control_engine_claude `bind`, control_engine_codex `bind` and the engine selector the
      suites read resolve only store copies whose digest is the one the qualification record names; no
      production module or suite reads `~/.local/share/claude/versions`, the npm global package or a
      `claude` or `codex` link on PATH at run time (suite 82's fixed vendor path among them), and
      setup's first pin (VELDO-0186) copies into the same store. A copy is referenced while it is the
      active pointer's target, the previous qualified version kept for rollback, or bound by any job
      whose execution record is not finished; the service removes an unreferenced copy at its release
      check and logs it. A store copy whose digest changed, or that is gone, refuses the launch by name
      (binding_mismatch:engine_store:<engine>:<digest>) and is reported once. The suite qualifies and
      binds both engines, then deletes the vendor's versions directory, upgrades the fixture's global
      Codex package to another version and runs the vendor updater fixture, and requires every bind and
      every qualification row to stay green. Falsifier: Bind Claude Code from the vendor's versions
      directory instead of the store, and the pruned-cache row must fail on the missing source.
    falsified_by: >
      Bind Claude Code from the vendor's versions directory instead of the store, and the pruned-cache
      row must fail on the missing source.
required_evidence: [unit, integration]
rollback: >
  The owner sets `auto_upgrade: false` in the factory configuration, which stops installs and switches,
  and runs `veldo engines use <engine> <version>` to point back to the previous version, which the store
  keeps (AC4) and which AC2's pointer writer accepts only for a version whose qualification passed.
  Running jobs finish on the version they bound. Store copies, qualification records and the journal
  are unchanged.
---

## Intent

Claude Code and Codex release about once a week, and pinning each version by hand does not keep up. The
factory picks up each new release by itself, checks it with the same qualification a hand-made change
must pass, and moves to it only when it passes. A running job is never broken by an upgrade, a failed
upgrade leaves the factory on the last good version and tells the owner what broke, and nothing the
vendor's own updater does can change or remove the engine the factory runs.

## Context

W152 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5, built after the
current batch. The owner approved automatic upgrades on 2026-10-10 (Telegram 33029-33031), which brings
into Release 1 the replacement of pins after an update that VELDO-0186 and VELDO-0139's Notes had left to
Release 2. The qualification records and pinned launch are VELDO-0060 and VELDO-0061's; the baselines and
guards VELDO-0155 and VELDO-0156's; the capability inventory VELDO-0127 and VELDO-0173's; setup's first
pin VELDO-0186's. This specification builds on the per-version Codex records and the VELDO_CODEX_BINARY
selector of the codex-0162-host work, which lands first under VELDO-0061 and VELDO-0127.

## Out of scope

The Mac's engines, which follow VELDO-0147's legs once this lands on Linux; any live model call on the
owner's logins during qualification, which runs only with his consent and is not part of the automatic
run; carrying an automatically qualified record back into the repository, which stays an ordinary
reviewed change; fixing an adapter so a version that failed can pass, which is a hand-made change as
today; engines other than Claude Code and Codex, and host kinds other than Linux x64.

## What the reviewer judges

- Normal use: Codex publishes a new version; within the check interval the factory installs it beside
  the current one, qualifies it, and switches; jobs running at the switch finish on the old version, the
  next launch binds the new one, and the old copy is removed once nothing references it. When a version
  fails, the owner gets one Telegram report naming the failed checks, and the factory keeps running on
  the last good version.
- Threat model: an unqualified binary reaching a job or a gate, as the global Codex 0.162 upgrade did; a
  vendor updater or cache pruning removing the binary a gate reads, as with Claude Code 2.1.281; a
  download that is not the vendor's published build; a switch that changes the binary under a running
  job; a failed version retried and reported in a loop; an automatic run that checks less than a
  hand-made qualification does.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as two
  releases published within one qualification run (the newer is qualified at the next check); a vendor
  whose release channel itself is compromised and publishes a matching checksum.

## Notes

Owner decision, Telegram 33029-33031 (2026-10-10): hand-pinning versions does not scale; Veldo installs
a new version beside the current qualified one, runs its engine qualification against it, switches by
itself through one stable path when it passes, and stays on the last qualified version and reports what
broke when it fails. Engines must never break a running job, and the vendor's auto-updater must never
change or delete the binary Veldo runs.

Two incidents this week drive AC4. A global Codex 0.162 upgrade turned every gate red, because the gates
ran whatever binary the package manager had installed, which was not qualified. Claude Code's native
installer pruned 2.1.281 from `~/.local/share/claude/versions`, and gates went red, because Veldo read
the vendor's cache instead of its own copy. The 0.162 audit on codex-0162-host also shows why AC2 runs
the whole set: that version changed a usage-limit message, the bundled models, eleven feature defaults
and a credential table, and offered resource readers that needed an owner decision (Telegram 32962).
Under this specification such a version fails, is reported once, and waits for a hand-made fix.

The vendors publish no push notice of a release, so the check is a scheduled read of their release
channel, the way Renovate and Dependabot work. The active pointer is the one stable path the owner asked
for: every consumer resolves the engine through it, and a launch then holds the digest it resolved.

## History

2026-10-10: new specification on the owner's decision (Telegram 33029-33031), written ready on that
approval, after the Codex 0.162 and Claude Code 2.1.281 gate incidents of the same week.
