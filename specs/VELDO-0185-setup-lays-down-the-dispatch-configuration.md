---
schema: veldo.spec/v1
id: VELDO-0185
title: Factory setup saves the default team, gives the installed service its engine adapters and work configuration, enrolls the authority and launch receiver as reservation services and writes the receivers' state root, so after the owner logs in each account work runs on both engines on every account, and a second run changes nothing
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W145
plan_revision: 4
depends_on: [VELDO-0139, VELDO-0154, VELDO-0155, VELDO-0156, VELDO-0160, VELDO-0162, VELDO-0167, VELDO-0170, VELDO-0171, VELDO-0172, VELDO-0186]
placement: [engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/control_accounts.py"
  - ".veldo/control_accounts.py"
  - "engine/.veldo/control_account_pool*.py"
  - ".veldo/control_account_pool*.py"
  - "engine/.veldo/control_engine_claude*.py"
  - ".veldo/control_engine_claude*.py"
  - "engine/.veldo/control_engine_codex*.py"
  - ".veldo/control_engine_codex*.py"
  - "engine/.veldo/control_team*.py"
  - ".veldo/control_team*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "bin/veldo"
  - "engine/bin/veldo"
  - "scripts/suites/*_veldo_0185_*.py"
  - "scripts/suites/73_veldo_0139_factory_setup.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0185-setup-lays-down-the-dispatch-configuration.md"
  - "specs/index.md"
  - "proof/VELDO-0185/*"
behavior_bearing: true
observability:
  logs: >
    Record each dispatch step setup runs (the default team, the adapters, the work configuration, each
    principal's reservation_service enrollment, the receivers' state root, each account's login status) as
    done, already done or refused, with the paths it wrote, the revisions it saved and the principals it
    enrolled, and each account's first dispatch after setup with its engine and station; never a key or a
    credential.
  metrics: >
    Count setup runs by outcome, dispatch steps by outcome, accounts found not logged in, and dispatches per
    engine and account after setup.
  traces: >
    Join each dispatch step to its setup run, the installed service's loop status to the work configuration
    it loaded, and each launch after setup to the adapter and account it bound.
  error_taxonomy: >
    Distinguish an existing file the run would write differently (invalid_input:state_root:differs:<path>),
    a store write setup cannot send through the running service
    (invalid_input:state_root:service_running:<step>) and an account whose engine's own login status is not
    a subscription login (missing_authority:account_login:<account>, a name this specification adds).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Factory setup saves the default team, writes the launch receiver's engine adapters and a work
      configuration whose builder and reviewer come from that team, and installs the service with both, so
      the installed factory loop is configured on a fresh host. Set and completeness: Where the store holds
      no default team, setup saves one by the owner's signed commands: one capability configuration revision
      per role (VELDO-0162 AC1) and one `save_default_team` revision (VELDO-0162 AC4) with control_team's
      four REQUIRED_ROLES, `project_manager`, `elaboration`, `implementation` on Claude Code and
      `independent_review` on Codex, as the operating-model design's walkthrough runs them (all four on one
      engine when the account registry names only one). It writes one adapter per engine the account
      registry names, `claude_code` naming its pinned version and `codex` its vendor binary (both laid down
      by VELDO-0186), and passes them through the installer's `adapters` option; it writes the work
      configuration (`veldo.factory_work/v1`) naming the enrolled workspace's repository, its builder from
      the team's `implementation` role and its reviewer from `independent_review`, each with control_service's
      ROLE_FIELDS, and passes it through the installer's `work` option (VELDO-0154). After setup the running
      service's loop status reads `available` and `configured` true with no refusal, and the receiver
      configuration names both adapters. The suite sets up a fresh fixture host with fake accounts of both
      engines and reads the saved team back. Falsifier: Install the service without the `work` option, and
      the loop-configured row must fail on `configured` false.
    falsified_by: >
      Install the service without the `work` option, and the loop-configured row must fail on `configured`
      false.
  - id: AC2
    text: >
      Claim: Setup enrolls the `authority` and `launch-receiver` principals with the `reservation_service`
      role by the owner's signed command, and every receiver configuration the installer writes carries the
      state root. Set and completeness: Each enrollment is the owner's signed `enroll_principal` command with
      the role, sent under VELDO-0171 AC1's lock rule, as setup enrolls its other principals, and the account
      pool and reservation service (VELDO-0160, VELDO-0036) accept both principals' usage observations and
      reservations. Setup passes its state root to the installer, which writes it as `state_root` into every
      receiver configuration it writes: each repository's, and VELDO-0174 AC4's conversation receiver
      configuration, written the same way once that lands; so the execution records, runs and pinned
      engines resolve under it (control_execution_record `directory`, control_launch `bind`). The suite
      reserves an account slot as each principal and launches through the installed receiver. Falsifier:
      Enroll both principals without the role, and the reservation row must fail on the reservation
      service's refusal.
    falsified_by: >
      Enroll both principals without the role, and the reservation row must fail on the reservation
      service's refusal.
  - id: AC3
    text: >
      Claim: Running setup again with the same arguments changes nothing, and on a host laid down before this
      change it adds only these steps. Set and completeness: Each step follows VELDO-0171 AC4's re-run rule: a
      file equal to what it would write is left alone, an absent one is written, a receiver configuration
      gains its `state_root` key only where it lacks it or holds it as null, any other differing file is
      refused by name (invalid_input:state_root:differs:<path>), a default team already saved is not saved
      again, and an enrollment already in the journal is not sent again. After a second run over a complete
      host, every file under the state root, install root and unit directory, VELDO-0186's installed runtime
      files and pinned engines among them, is byte for byte the same, nothing is pinned or installed again,
      and the journal head is unchanged. Over a host set up by VELDO-0139 and VELDO-0171 alone, only these
      steps write. Falsifier: Send both enrollments on every run, and the second-run row must fail on the
      changed journal head.
    falsified_by: >
      Send both enrollments on every run, and the second-run row must fail on the changed journal head.
  - id: AC4
    text: >
      Claim: After setup and the owner's one-time login of each account, the installed factory dispatches
      build and review work to both engines on every registered account, and an account not yet logged in
      takes no work while the others carry on. Set and completeness: Setup's account step runs each
      registered account's engine's own login status in that account's profile environment (control_accounts
      `login_environment`): Claude Code's `auth status`, whose JSON must report `loggedIn` true, and Codex's
      `login status`, which control_engine_codex `login_status` must read as `chatgpt`, as VELDO-0156 AC3's
      `login_problem` reads it. Each account that fails is named in setup's answer with its login step
      (VELDO-0160 AC1) and refused by name (missing_authority:account_login:<account>); the launch receiver
      runs the same check before acceptance, so a dispatch on that account is refused before spawn and the
      Line offers the unit on another account at its next pass. With the owner's accounts registered (three
      Claude Code and one Codex in his case) and logged in, a unit submitted after setup is built and
      reviewed through the installed service and receiver alone, and over successive units every account
      runs at least one build or review, the Codex account among them. The suite uses fake engines that print
      the installed CLIs' output shape and login status (VELDO-0172), with one Claude Code account logged
      out. Falsifier: Write the receiver's adapters without `codex`, and the every-account row must fail on
      the Codex account with no run.
    falsified_by: >
      Write the receiver's adapters without `codex`, and the every-account row must fail on the Codex
      account with no run.
required_evidence: [unit, integration]
rollback: >
  Reinstall the service without the work configuration, so the loop stops offering work, and revoke the two
  role grants with the owner's signed commands; accepted records, the default team among them, are
  unchanged. No automatic rollback is authorized.
---

## Intent

After setup, the factory the owner installed on a fresh host starts work on its own: it has a team, the
service knows its engines and its work, the services that reserve account slots are allowed to, and once
he has logged in each of his accounts, work runs on all of them.

## Context

W145 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The VELDO-0154
review on 2026-09-27 found that a factory set up on a fresh host dispatches nothing, which blocks the
owner's first use on October 1: setup passes no `adapters` and no `work` configuration to the service
(VELDO-0154 added the installer's `work` option), never enrolls the `authority` and `launch-receiver`
principals with the `reservation_service` role, and writes a receiver configuration with no `state_root`;
nor does anything save the default team the work configuration's builder and reviewer come from. The
installed runtime assets and pinned engines are VELDO-0186, built first because AC1's adapters name its
pin; the end-to-end dispatch on every account, first drafted there, is AC4 here. The re-run is
VELDO-0171's one upgrade path. VELDO-0139 is a standalone built item, so its edge is kept here and not in
the plan graph. A draft: only the owner marks it ready.

## Out of scope

The runtime assets, qualification records and pinned engines (VELDO-0186); replacing installed engine
files after an update (Release 2, VELDO-0139's Notes); the Mac relay's receiver (VELDO-0125); a team other
than the default one.

## What the reviewer judges

- Normal use: the owner runs setup on a fresh host with his accounts registered, logs in each of his four
  accounts once, starts the service as setup tells him, and the loop reports itself configured; a unit he
  sends is built and reviewed, and over the day every account runs work, the Codex account among them;
  later he runs setup again and nothing changes.
- Threat model: a service installed with no work configuration, so nothing runs and nothing says why; a
  principal reserving slots without the role, or given the role without the owner's signed command; a
  receiver whose records and pins resolve outside the state root; an account that is not logged in taking
  work; a default team saved again, or saved without his signed command; a re-run that enrolls twice or
  rewrites a file.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as setup
  interrupted between two dispatch steps (running it again finishes it); forged rows in our own store.

## Notes

The work configuration names roles, not accounts: the account pool (VELDO-0160) picks the account per run,
so an account registered later takes work with nothing reinstalled. The default team's engines are a
starting grant the owner changes in the role form (VELDO-0163). Conversation turns launch through
VELDO-0174 AC4's conversation receiver configuration, which the installer writes with the same state root,
so setup lays it down with nothing more once VELDO-0174 lands.

## History

2026-09-27: new draft for the VELDO-0154 review finding of 2026-09-27 that a factory set up on a fresh host
dispatches nothing. Only the owner marks a specification ready.

2026-09-27, review of the drafts: the order with VELDO-0186 is reversed, since AC1's adapters need its pin:
this specification now depends on VELDO-0186 and takes its former AC3 as AC4, naming the check that finds
an account not logged in (each engine's own login status); AC1 also saves the default team its builder and
reviewer come from; AC2 writes the state root into every receiver configuration, the conversation
receiver's included. depends_on adds VELDO-0155, VELDO-0156, VELDO-0162, VELDO-0172 and VELDO-0186. Still
a draft.
