---
schema: veldo.spec/v1
id: VELDO-0177
title: A conversation acts in its own workspace with exactly its role's tools and servers, inside the same containment and credential rules as project runs, and can work on a fresh clone of a project it is attached to
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W137
plan_revision: 4
depends_on: [VELDO-0040, VELDO-0042, VELDO-0127, VELDO-0158, VELDO-0162, VELDO-0165, VELDO-0171, VELDO-0173, VELDO-0174, VELDO-0185]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_conversation*.py"
  - ".veldo/control_conversation*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/control_clone*.py"
  - ".veldo/control_clone*.py"
  - "engine/.veldo/control_agent_config*.py"
  - ".veldo/control_agent_config*.py"
  - "engine/.veldo/control_team*.py"
  - ".veldo/control_team*.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "bin/veldo"
  - "engine/bin/veldo"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0177_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0177-conversation-workspace-and-tools.md"
  - "specs/index.md"
  - "proof/VELDO-0177/*"
behavior_bearing: true
observability:
  logs: >
    Record each turn's workspace, worker group, role revision, tool and server names and credential
    references, and each project attach with its project, trunk commit and clone path; never a credential
    value.
  metrics: >
    Count turns by role revision, turns refused for a workspace mismatch, and project attaches.
  traces: >
    Join each turn's launch to its conversation, its role revision and the clone of each attached project.
  error_taxonomy: >
    Distinguish a turn launched outside its own workspace (binding_mismatch:conversation_workspace), an
    attach of a project outside the owner's scope (missing_authority:project), and every launch refusal the
    project runs already name (VELDO-0155, VELDO-0156, VELDO-0158, VELDO-0165, VELDO-0173).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Each conversation's turns run in its own workspace, through the same Runner, containment and
      launch guards as project runs, and no conversation's workspace, session or credentials reach another
      conversation's run. Set and completeness: VELDO-0174 AC1's open command creates the workspace
      directory under the conversation's directory, and it is the engine's working directory for every turn.
      Each turn launches through the Runner in a VELDO-0040 worker group with the declared caps, with
      VELDO-0155's or VELDO-0156's baseline, VELDO-0165's environment strip, VELDO-0173's tool switch-off and
      VELDO-0158's credential delivery of exactly its role's servers' credentials, each added to that run's
      redaction set. The receiver refuses by name a turn whose working directory is not its own
      conversation's workspace (binding_mismatch:conversation_workspace), before anything is spawned. The
      suite runs turns of two conversations at once; each fake engine lists its working directory, worker
      group and credential file; each differs, and neither names the other's. Falsifier: Give every
      conversation one shared workspace, and the isolation row must fail on the same working directory in
      both runs.
    falsified_by: >
      Give every conversation one shared workspace, and the isolation row must fail on the same working
      directory in both runs.
  - id: AC2
    text: >
      Claim: A turn is offered exactly its role revision's tools and servers, so it can read and change
      files, run commands and look things up, and setup gives the default team an assistant role on each
      engine. Set and completeness: The launch hands in the bound revision's native tools, MCP selections,
      skills and instruction files exactly as VELDO-0127 AC2 hands them for a project run; nothing is added or
      taken away for a conversation. Setup saves `assistant` on Claude Code, granting the pinned version's
      in-run tools with WebSearch and WebFetch, and `assistant_codex` on Codex, granting its workspace-write
      sandbox with network access and web search, all `always`, into the default team by the owner's signed
      commands: one capability configuration revision each (VELDO-0162 AC1) and one `save_default_team`
      revision (VELDO-0162 AC4) adding both roles to the team VELDO-0185 AC1 saves, and a second setup run
      saves nothing again (VELDO-0171 AC4's re-run rule). VELDO-0183 and VELDO-0184 add the memory items to
      both, and the owner changes either in the role form (VELDO-0163). The suite reads the init event's tools and servers against the revision, and the record of a turn that
      edits a file, runs a command and fetches a loopback page. Falsifier: Launch conversation turns with no
      role revision bound, and the offered-tools row must fail on WebFetch missing from the init event.
    falsified_by: >
      Launch conversation turns with no role revision bound, and the offered-tools row must fail on
      WebFetch missing from the init event.
  - id: AC3
    text: >
      Claim: The owner attaches one of his projects to a conversation, and its turns then read and change a
      fresh isolated clone of that project's repository with its history, and never publish to it. Set and
      completeness: The `attach_project` command (from the API, VELDO-0178, or Telegram's `/attach`,
      VELDO-0175 AC4), on the conversation's current version (VELDO-0174 AC1), names a project in the
      owner's scope, and anyone else's is refused by name (missing_authority:project). It makes a VELDO-0042
      isolated clone of the project's repository at its current trunk commit under the workspace's
      `projects/<project>` directory, with the full history, recorded with that commit; attaching again
      takes a new clone beside the old one. The clone has no push remote, no Git identity profile
      (VELDO-0142, VELDO-0153) and no publication credential, so a change reaches the project only as
      VELDO-0180 carries it. The suite attaches a fixture project, runs a turn that reads `git log` and
      commits in the clone, then tries to push. Falsifier: Give the clone the project's push remote, and the
      no-publication row must fail on the fixture remote's changed ref.
    falsified_by: >
      Give the clone the project's push remote, and the no-publication row must fail on the fixture
      remote's changed ref.
required_evidence: [unit, integration]
rollback: >
  Stop launching conversation turns while keeping every workspace and record; project runs are unchanged.
  No automatic rollback is authorized.
---

## Intent

A conversation does not only answer: it reads and changes files, runs commands and looks things up, as
the owner's assistant does today, with exactly the tools its role grants and under the same rules as
every other run, and it can work on a project's code and history without touching the project.

## Context

W137 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Project runs
already get their role's tools (VELDO-0127, VELDO-0173), credentials (VELDO-0158), baseline and
environment strip (VELDO-0155, VELDO-0156, VELDO-0165) and containment (VELDO-0040) in an isolated clone
(VELDO-0042). A conversation has no project clone, so this gives it a workspace and reuses every rule.
AC3 carries the smaller "answer a question from a project's code and history" draft the owner agreed to
on 2026-09-27, which this requirement contains. A draft: only the owner marks it ready.

## Out of scope

Operating-system separation between two runs of the same account beyond their worker groups, and
exhaustive containment qualification (Release 2, O4); keeping an attached clone up to date with trunk
(attach again); the Mac leg (VELDO-0147).

## What the reviewer judges

- Normal use: the owner asks a conversation to draft a script, run it and fix it; to look something up on
  the web; and, attached to veldo, to explain why a gate row failed from the code and its history.
- Threat model: a turn offered a tool or server its role does not grant, or missing one it does; a turn
  running outside its workspace or seeing another conversation's credentials; a conversation publishing
  to a project's repository; a project attached by someone outside its scope.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a run reading
  another workspace through a tool the owner granted, which the Release 2 containment qualification
  covers; forged rows in our own store.

## Notes

The assistant roles setup saves are a starting grant, never a ceiling: only the owner changes them, and the
factory never narrows them for a conversation (C15).

## History

2026-09-27: new draft for the owner's conversation requirement (Telegram, 2026-09-27). Only the owner
marks a specification ready.

2026-09-27, review of the drafts: AC2 no longer says VELDO-0162 seeds the default team, which it does not;
setup saves `assistant` and `assistant_codex` into the default team VELDO-0185 saves, by the owner's
signed commands. AC3's attach comes from the API or Telegram's `/attach`. depends_on adds VELDO-0171 and
VELDO-0185. Still a draft.
