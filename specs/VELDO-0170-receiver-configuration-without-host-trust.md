---
schema: veldo.spec/v1
id: VELDO-0170
title: A launch receiver configuration that names no host trust stops by name, and factory setup's re-run adds the host trust
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W130
plan_revision: 4
depends_on: [VELDO-0039, VELDO-0047, VELDO-0069, VELDO-0139, VELDO-0171]
placement: [engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0170_*.py"
  - "scripts/suites/73_veldo_0139_factory_setup.py"
  - "scripts/suites/62_veldo_0039_dispatch.py"
  - "scripts/suites/63_veldo_0040_containment.py"
  - "scripts/suites/63_veldo_0049_floor.py"
  - "scripts/suites/64_veldo_0050_proof.py"
  - "scripts/suites/67_veldo_0041_heartbeat.py"
  - "scripts/suites/67_veldo_0135_offers.py"
  - "scripts/suites/71_veldo_0076_projects.py"
  - "scripts/suites/75_veldo_0062_accounts.py"
  - "scripts/suites/78_veldo_0060_claude_adapter.py"
  - "scripts/suites/78_veldo_0160_account_pool.py"
  - "scripts/suites/79_veldo_0061_codex_adapter.py"
  - "scripts/suites/80_veldo_0155_claude_baseline.py"
  - "scripts/suites/81_veldo_0156_codex_baseline.py"
  - "scripts/suites/82_veldo_0141_execution_record.py"
  - "scripts/suites/82_veldo_0165_launch_hygiene.py"
  - "scripts/suites/82_veldo_0173_tool_registry.py"
  - "scripts/suites/85_veldo_0158_credential_delivery.py"
  - "scripts/suites/70_veldo_0069_bindings.py"
  - "scripts/suites/*_veldo_0171_*.py"
  - "scripts/suites/92_veldo_0088_pm_cycles.py"
  - "scripts/suites/93_veldo_0152_intake_routes.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0170-receiver-configuration-without-host-trust.md"
  - "specs/index.md"
  - "proof/VELDO-0170/*"
  - "proof/VELDO-0127/factory.py"
behavior_bearing: true
observability:
  logs: >
    Record each launch refused for a configuration with no host trust, with the configuration's path and
    repository, and each re-run's host trust step with the configurations it added the key to and left as
    they were; never a key.
  metrics: >
    Count launches refused for a missing host trust, and receiver configurations the re-run gave a host
    trust and found already current.
  traces: >
    Join each refusal to its dispatch and receiver configuration, and each host trust step to the setup
    run, the installation and the host trust file it read.
  error_taxonomy: >
    Distinguish a configuration that names no host trust (host_trust_required:receiver_configuration)
    from a named trust that is absent or unreadable (host_trust_required, unchanged) and from an unsigned
    decision; a re-run whose host trust step finds no installed trust is refused by name with nothing
    written.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A launch under a receiver configuration that names no host trust is refused by one name
      before anything is spawned, never as an unsigned decision. Set and completeness: The receiver
      (control_launch.Receiver) checks for the `host_trust` key when it accepts a dispatch, for every unit,
      governed or not; a configuration without it refuses host_trust_required:receiver_configuration, and
      the service's status names each installed receiver configuration without it and the one repair:
      run `veldo factory setup` again with the arguments the host was laid down with (VELDO-0171's
      re-run). Take a receiver configuration as the installer wrote it before the host trust fix
      (no `host_trust` key) and launch a governed unit and an ungoverned one: both are refused by that
      name. Falsifier: Treat a configuration with no host trust as trusting no settlement, as today, and
      the governed-unit row must fail on unsigned_decision.
    falsified_by: >
      Treat a configuration with no host trust as trusting no settlement, as today, and the governed-unit
      row must fail on unsigned_decision.
  - id: AC2
    text: >
      Claim: Running factory setup again with the same arguments (VELDO-0171's re-run, the one upgrade
      path) gives each receiver configuration that names no host trust its `host_trust`, changing nothing
      else. Set and completeness: The re-run gains one host trust step: for each receiver configuration
      the installed service configuration lists, it adds `host_trust` naming the host's installed trust
      file, the one the installation's channel ingress configuration names, else the default location
      (control_eligibility.host_trust_path), which must load and whose host identity must equal the
      installed service's. It replaces the file whole at 0600 with only that key added; a configuration
      that already names a trust is left byte for byte, and one that differs in anything else is refused
      by name as VELDO-0171 AC4 refuses. The step is refused by name, writing nothing, when no installed
      trust loads. There is no separate upgrade command. Re-run setup over an installation with one old
      and one current receiver configuration, then launch a governed unit under each: both are decided by
      the settlement signers. Falsifier: Rewrite the configuration without the `host_trust` key, and the
      launch-after-re-run row must fail.
    falsified_by: >
      Rewrite the configuration without the `host_trust` key, and the launch-after-re-run row must fail.
required_evidence: [unit, integration]
rollback: >
  Restore the receiver configurations from before the re-run by hand; launches under them are refused by
  name until setup is run again. No automatic rollback is authorized.
---

## Intent

A factory installed before the host trust fix tells the owner exactly what is wrong and how to fix it,
instead of quietly refusing every decision-governed unit.

## Context

W130 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The Codex
whole-project review of 2026-09-26 found that the launch receiver built its eligibility Gate without the
settlement signers, so work the front door had cleared was refused unsigned_decision at launch; the fix
landed on main at a4769f68 and the installer now writes `host_trust` into each receiver configuration. Its
review (rvfix0926) filed that a configuration written before the fix has no `host_trust`, and the receiver
reads that as trusting no settlement: every governed unit is refused as unsigned, with no stop that names
the cause and no path to fix it but reinstalling. The lead decided on one upgrade path, the re-run of
factory setup that VELDO-0171 defines, so this specification names the stop and adds its repair as one
step of that re-run, with no command of its own; it depends on VELDO-0171 and is built in stage 5 with it.
VELDO-0139 is a standalone built item, so its edge is kept here and not in the plan graph. This new
specification is draft; authoring it supplies neither implementation proof nor operational activation.

## Out of scope

Checking that the host trust path lies outside places a worker can write (filed for Release 2); any
other configuration key; the re-run's own argument and differing-file rules (VELDO-0171 AC4); migrating
the store.

## What the reviewer judges

- Normal use: the owner's factory was installed before the fix; after updating Veldo he starts it, sees
  the named stop in the service status, runs factory setup again with the same arguments, and governed
  work launches again.
- Threat model: an old configuration silently refusing governed units; a re-run that changes anything but
  the missing key, or that points a receiver at a trust file the service was not installed with. The
  owner's account, the installed service and its trust file are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as an
  re-run interrupted between two configurations (running it again finishes it); configuration files
  planted in the installed directory; hosts with several installations.

## Notes

Filed, out of review scope: a host installed without factory setup has no repair path.

The host trust step reads the trust path from the installation, never from a flag, and checks its host
identity against the installed service's, so it cannot point a receiver at another host's trust. It needs no
restart: the receiver reads its configuration at each launch.

## History

2026-09-27: new draft from the review rvfix0926 of the Codex-review fixes landed at a4769f68 (item f of
its filed list). A draft: only the owner marks a specification ready.

2026-09-27: amended on the lead's decision of one upgrade path, VELDO-0171's re-run. The separate `veldo
factory upgrade` command is dropped: AC1 names the stop and the re-run as its one repair, and AC2's repair
is one step of that re-run. depends_on adds VELDO-0171, so the work item moves from stage 3 to stage 5;
bin/veldo leaves the footprint. Still a draft.

2026-09-27: marked ready by the owner (Telegram 29229, "all ready").

2026-10-02: implementation on build-veldo-0170. The receiver names missing configuration
trust before accepting work; lifecycle status and service inspection list affected configurations.
Factory setup gains an installation-derived host trust step even on a current engine.
The footprint adds suites 62 and 70 because their old receiver fixtures or assertions
explicitly rely on the absent-trust behavior this criterion replaces. Suite 87 and proof/VELDO-0170 record eight behavior rows, all red by assertion at
f1e1abb9. The comparison retains owner-configured adapters and the historical default
runs path, as the existing engine upgrade requires. Finding 170 registers ten mutants;
the owner reserves mutation execution and the full gate to the reviewer. Status remains
ready and independent review is pending.

2026-10-02: the footprint also names the sixteen existing launch suites whose ordinary
receiver fixtures lacked host trust. AC1 requires every receiver to name it, so those
fixtures now write a generated host trust with no settlement signers. Their behavior
assertions and explicit missing-trust tests are unchanged. Broader suite execution is
reserved to the reviewer under the owner's test scope restriction.

2026-10-02: review follow-up adds proof/VELDO-0127/factory.py to the footprint.
Its ordinary receiver now names generated host trust without settlement signers.
Suite 86 clears the launch failures; its two live-capture assertions remain stale
for control_launch.py from commit 600f9ec9 and require the owner's real-login recapture.
No production launch code or live captures change in this follow-up.
The comparison proof now perturbs principal, workspace, store and journal_key
separately, each with a named no-write refusal assertion and its own registered
finding-170 mutation. Suite 87 passes all eleven specification rows alone;
mutation execution remains reserved to the reviewer.

2026-10-04: merged main at 298d0fd2. Both suite 62 fixture additions and all
suite registrations are retained, with requires regenerated. The footprint adds the
0088 coordination and 0152 intake suites because their new receiver constructors
also need explicit generated host trust. Their behavioral assertions are unchanged.
The 0170 installation fake still uses the shared 0172 constructor and now passes
its local fixture context directly to conformance at teardown. Live 0127 captures
are left for the owner to refresh with real logins.
