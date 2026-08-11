# WARP-0620 live-sandbox proof - run record

Run 2026-07-24 evening EDT, throwaway project TE1 (board 69), created by Dmitry for this purpose.
Executed from the worktree `/path/to/repo/WARP-0623` at commit f5d36ee, i.e. with
the WARP-0623 collision fix in place and independently reviewed (pass_with_notes, must_fix empty). Dmitry
chose to run from the reviewed branch rather than wait for a merge.

Nothing on the production board (VEL) was read or written. No real decision settled. No listener, webhook,
timer or service was created.

---

## Step 1 - the codified provisioner ran live for the first time

`python3 .veldo/tracker_jira_init.py init --tracker sandbox`, admin identity (provisioning needs the
group and workflow-admin scopes the agent deliberately lacks, which is the two-identity model working):

```
veldo jira init (live)
{ "project": "TE1", "project_type": "company-managed", "provisioned": true,
  "issue_types_created": 1, "issue_types_reused": 2,
  "statuses_created": 0, "statuses_reused": 14,
  "workflow_wired": 13, "workflow_already": 29,
  "epics_mirrored": 0, "specs_mirrored": 0, "children": 0, "transitions": 0 }
```

Notes: the Decision issue type was CREATED, two existing types REUSED, and all 14 statuses REUSED rather
than duplicated, which is the attach-not-fake behaviour the operator guide documents. Nothing from the
private corpus was mirrored (0 specs, 0 epics), so the sandbox carries no internal artifact.

Before the WARP-0623 fix this same command could not run at all: it raised
`TypeError: 'str' object is not callable` with a project configured and
`TypeError: 'NoneType' object is not callable` without one.

## Step 2 - the fence was applied BY THE CODE, not by a script

Read back from the live board, all 16 transitions of the provisioned workflow. Exactly three carry a
condition:

```
  FENCED  To Decided    -> Decided
  FENCED  To Approved   -> Approved
  FENCED  To Rejected   -> Rejected
```
Every other transition (To Backlog, To Ready, To Under Independent Review, To Needs Decision,
To In Discussion, To Awaiting Approval, To Changes Requested, To Blocked, To Shipped, To Superseded, and
the three default statuses) is unconditional. This matches the shape the ad-hoc script produced on the
production board, this time from the codified path.

Fence groups verified on the live site beforehand: `veldo-agents` contains exactly one member, the
Veldo Agent app account; `veldo-approvers` contains exactly one member, Dmitry Grinberg. The agent is
absent from the approver group.

## Step 3 - THE LOAD-BEARING TEST: the agent tried to approve and could not

Acting through the shipped OAuth token manager on the agent's client credentials. Identity confirmed from
the API before the attempts: `('Veldo Agent', 'app')`.

CONTROL FIRST, so that a refusal cannot be mistaken for broken authentication:

```
  Needs Decision : PERFORMED
```

Then each terminal transition:

```
  Approved  : NOT OFFERED to this credential (target Approved absent from its transition list)
  Decided   : NOT OFFERED to this credential (target Decided absent from its transition list)
  Rejected  : NOT OFFERED to this credential (target Rejected absent from its transition list)
```

This is stronger than an HTTP 403: the transitions do not exist for that identity. And the control proves
the credential was working in the same seconds. THE CLAIM THE WHOLE SURFACE RESTS ON - that the machine
cannot authorize its own work - is therefore proven against a real board rather than designed on paper.

## Step 4 - one real human transition, then the real changelog

Dmitry fired Approved on TE1-1 (he can; he is in the approver group). The authenticated pull returned the
ordered attributed changelog, captured verbatim in `te1-changelog-raw.json`:

```
{"id": "31204", "at": "2026-07-24T20:28:12.074-0400", "actor": "Veldo Agent",
 "actor_type": "app", "account_id": "712020:591c1515-...", "from": "To Do", "to": "Needs Decision"}
{"id": "31205", "at": "2026-07-24T20:30:34.329-0400", "actor": "Dmitry Grinberg",
 "actor_type": "atlassian", "account_id": "712020:fbf897f7-...", "from": "Needs Decision", "to": "Approved"}
```

## Step 5 - the SHIPPED derivation, run on that real data

```
  _opening_actor        -> Veldo Agent
  _terminal_decision    -> outcome: accept | decisive to: Approved
  _entry_actors         -> ['Dmitry Grinberg']
  proposer != approver  -> True
```

Every property the design claims, checked on real data, all PASS:
- the opening actor derives as the AGENT (the verified proposer, from the changelog lineage)
- the terminal actor derives as the HUMAN (never a self-declared field)
- the outcome resolves to accept FROM THE ORDER, not from current status
- the decisive entry is the LAST accepting transition
- no conflict (accept and reject both present would BLOCK)

## Field-by-field: the real shape against what the offline fake assumed

| field the shipped accessors read | reader | present in every real entry |
|---|---|---|
| `from` | `_from_state` | yes |
| `to` | `_to_state` | yes |
| `actor` | `_opening_actor`, `_entry_actors` | yes |

Real entries additionally carry `id`, `at`, `account_id` and `actor_type`, which the accessors ignore.
`actor_type` is the field GAP 1 below is about.

IMPORTANT CAVEAT, stated because it limits what this step proves: the shipped accessors read a FLAT
`{actor, from, to}` shape, and Jira's raw changelog is NESTED (`values[].author.displayName`,
`values[].items[].fromString`, `values[].items[].toString`). The normalization between them was written BY
HAND for this run. See GAP 2.

---

## GAP 1 - the repository-side machine-actor guard does not recognize the real agent

`authorization.MACHINE_ACTORS` is an EXACT set-membership test over generic words: agent, automation, ava,
bot, executor, machine, responder, service, service-account, service_account, veldo-executor,
veldo-responder.

```
real agent display name        : 'Veldo Agent'
normalized                     : 'veldo agent'
in MACHINE_ACTORS (exact set)  : False
```
Also not caught: `veldo-agent`, `Veldo Bot`, `Automation for Jira`. Caught: the bare words `agent`, `bot`,
`automation` - names no real account uses.

Meanwhile the tracker reported `accountType` in the same response - `app` for the agent, `atlassian` for the
human - and `authorization.py` never references it (grep count 0).

Why it matters: the plan states the repository is authoritative and the tracker fence is defence in depth.
Today the fence saves us, proven in step 3. On a surface with NO per-transition fence - which the launch
plan now carries a work item for - this guard is the ONLY control, and it would not fire. Fix specified as
WARP-0624, which WARP-1710 must not ship before.

## GAP 2 - there is no live changelog reader

`read_changelog` is declared on the `TrackerAdapter` base, and its docstring says a live adapter reads the
real board through the same seam, "reference-wired". It is not: `_read_changelog` is implemented only on
the FakeTracker. For this run the REST fetch and the nested-to-flat normalization were hand-written.

So the authenticated pull the entire inbound edge depends on does not exist for a real board, and a shipped
docstring implies it does. This is the missing piece the live proof existed to find.

---

## What this run did NOT establish

- That the reconcile writes a settlement receipt from live data end to end. The derivation functions were
  exercised on the real changelog; `reconcile_requests` was not driven against a live board, because there
  is no live changelog reader (GAP 2) and no seeded request record was projected to TE1.
- That the outbound projection and the Telegram doorbell fire live. Neither was executed in this run.
- That the fence holds against an actor who is in the approver group but should not be. That is access
  control, not a property of this edge.
- Anything about the production board. VEL was read for its group membership and transition conditions
  only, and never written.
