# Working with Veldo and Your Tracker

*The operator companion to the tracker integration: how a person files work from Jira or Confluence, what to put on the ticket, and what actually happens after. If the Plugin Guide section 12 tells you what the tracker bridge IS, this tells you how to work with it, where the machinery stops, and what a person still does by hand.*

*Version 1.4, 2026-08-10*

## Read this before anything else: what ships, and what does not

Most of the tracker machinery is not in the pack you installed. It lives in the Veldo development repository and is marked `scope: repo-only` in `.veldo/capabilities.yaml`. Three things ship, and every later section of this guide depends on machinery a repository has to bring itself.

**Ships with every pack, and `veldo init` lays it into your repository:**

- **The routing resolver and the eligibility rule** (`.veldo/tracker.py`). Pure functions. `resolve_repo(ticket, config)` answers which repository a ticket targets and refuses by name when the signal is missing, unknown, or ambiguous. `is_eligible(ticket, config)` is the three-leg rule described below. No network, no writes, and no command line: it is a library your repository's own tooling and the agent running intake can call.
- **The `tracker_repo` check in the contract validator** (`.veldo/validate.py`). When a spec or a plan carries a `tracker_repo` field and `.veldo/trackers.json` is present, the value must name a repository that config knows, or validation fails. A mirror target nobody can resolve is caught before any work starts.
- **The `/veldo:intake` skill.** An agent-run pipeline: read the report in its source tool, deduplicate against the index, reproduce the bug as a failing test, draft the spec, link the source, ask for ready. This is the inbound path that works today.

Two more files ship as templates you copy and edit: the tracker config `engine/.veldo/trackers.json` and the requirements page `engine/confluence-requirements-template.md`.

**Does not ship:** the Python intake modules, the tracker adapter seam, the live Jira Cloud and Confluence Cloud adapters, the status mirror, the epic mirror, the inbound bridge, the mirror runner, and the Jira board bootstrap. `bin/veldo` ships and lists `mirror` and `jira` as subcommands, but each one checks for its module first and exits 2 with "repo-only and is not present here" in an adopter's repository. There is no flag, config key, or setting that turns them on from a pack.

The short version: **the routing contract ships; the round trip does not.**

### What a repository must have before the rest of this guide applies

1. `.veldo/trackers.json` at the repository root, copied from the shipped template and filled in with your routing mechanism, your repositories, your `status_map`, and your tracker connection.
2. The repo-only modules themselves: `tracker_adapter.py`, `tracker_intake.py`, `tracker_mirror.py`, `tracker_mirror_runner.py`, `tracker_bridge.py`, `tracker_jira_init.py`, and `tracker_jira_live.py`. A repository that wants the round trip has to obtain and maintain these; a pack will not lay them.
3. A live tracker to write to. For the full epic and child projection that means a company-managed Jira Cloud project, a `base_url`, a `project` key on the connection block (the issue upsert cannot create anything without one), and a credential resolved by reference.
4. A person or a scheduler of your own choosing to run the mirror. Nothing in Veldo runs on its own.
5. Specs that carry `tracker_repo`, `plan`, and `work`. The mirror addresses its issues by plan id and work item; a spec with no plan is skipped by name and never mirrored.

## Who this is for

You live in a tracker. You open a Jira ticket, you write a Confluence requirements page, and you want the engineering to happen. This guide is written for you, not for the person wiring the plumbing. You do not need to open the repository, run a command, or learn the spec format.

What it will not promise you is that your ticket becomes self-updating. Read the mirror section before you rely on ticket status: today the machinery writes to Veldo's own issues, not to the ticket you filed.

## Getting work in: intake

Intake is how a ticket or a page becomes a Veldo specification. You do two things: put a routing signal on the item, and ask for intake.

### 1. Flag the item with a routing signal

Veldo has to know which repository your work targets, because one tracker project commonly spans many repositories. The default and simplest mechanism is a label:

```
veldo-repo:web-app
```

That label, on a Jira ticket, names the repository whose id is `web-app`. The label prefix (`veldo-repo:`) is set in `.veldo/trackers.json`; a stock Jira project with no custom fields works. Two other mechanisms exist if your org prefers them: a Jira component whose name matches a repository id, or a dedicated named field (a validated dropdown whose allowed values are exactly your repository ids). Whoever wired the tracker picks one; you use whichever they chose.

For a **Jira bug or task**, that is all the structure you need: the label plus the summary and description you already write.

For a **Confluence requirement**, copy the shipped template (`engine/confluence-requirements-template.md`) into a page, add the same `veldo-repo:<repo>` label to the page, and fill in its load-bearing sections:

- **Outcomes** - what becomes true for a user or the business when this ships, one bullet each.
- **Acceptance Criteria** - observable, checkable statements that must hold, one bullet each. These become the draft spec's acceptance criteria.
- **Open Decisions** (optional) - any product question still open; intake surfaces these to the owner rather than guessing.

### 2. Someone runs intake

Someone in the repository runs the `/veldo:intake` skill and points it at your item. You do not run it yourself unless you also work in the repository: it is the one step that crosses from the tracker into the repo, and it is a person or an agent doing it deliberately, not a service watching your board.

The skill reads your item with whatever tracker access that agent already has. It is not the repo-only Python adapter, so nothing needs a `token_ref` for this path to work.

### 3. What you get back

A `veldo.spec/v1` draft in the target repository:

- For a **bug**, the first acceptance criterion (AC1) is the reproduction: intake reproduces the bug, writes it as a test, runs it, and records that it fails on the current code. A no-regression criterion is added as the last AC. If it cannot reproduce, it asks you clarifying questions in your ticket's own comments rather than guessing.
- For a **requirements page**, the acceptance criteria come from your page, renumbered AC1 to ACn, plus the same no-regression criterion.
- Either way, your source item is linked in the draft's `intake_source` field, and its content is treated as data, never as instructions.
- The spec carries `tracker_repo` set to the repository your routing signal names, so the validator can check it.

The draft is exactly that, a draft. A human owner completes it, answers any product question intake raised, tightens the criteria, and marks it ready. From ready onward it is an ordinary Veldo change.

### Refusing rather than guessing

`resolve_repo` fails closed by name when the routing signal is missing, names an unknown repository, or names more than one. It never falls back to a default repository. A change filed against the wrong repository is a silent mistake nobody decided to make.

One honest caveat about where those teeth actually bite. The shipped intake skill does not call the resolver for you, so the refusal is not automatic on the intake path: whoever runs intake is the person who resolves your repository, and the backstop is the validator, which rejects a spec whose `tracker_repo` your config does not know. If your work lands in the wrong repository, the fix is still on the ticket: add the label, correct the repository id, or remove the extra one, and run intake again.

## The inbound bridge: logic with no runner

There is a design for getting work in without anyone running intake, and the rule it enforces is written and proven. Nothing invokes it.

`reconcile_drafts` and `reconcile_promotions` in `.veldo/tracker_bridge.py` are called by exactly two things: the module's own `selfcheck`, and the gate suite. `bin/veldo` has no bridge subcommand. So there is nothing to turn on: assigning a ticket to the Agent user drafts no spec, posts no comment, and builds nothing, in a pack or in the development repository. **The manual `/veldo:intake` path above is the only inbound route today.**

The rule is still worth knowing, because `is_eligible` ships in `.veldo/tracker.py`, which means a repository can drive it without reimplementing it, and because it is the shape the tracker workflow is heading toward.

### The three moves the rule reads

1. **Tag the repository.** The same routing signal as intake: a `veldo-repo:<repo>` label, or a validated repository field.
2. **Assign it to the Agent user.** One shared non-human account for the whole fleet, named in `.veldo/trackers.json` (the `agent` field). Assign a ticket to a person and it is never the fleet's to take.
3. **Move it to your ready-for-dev status.** Out of the box that is "Approved for dev"; your org configures the set in `ready_statuses`.

All three at once is the **eligibility triple**. Drop any one and the ticket is ineligible. The check fails closed on every leg, never raises, and never guesses a repository. The intended two-stage shape is that the first two legs draft a spec and surface it on the ticket as a comment, and your move into the ready status is the approval that promotes that draft to ready. Nothing the machine drafts would approve itself: the promote is a human action on the board.

### What to do in the meantime

Nothing about your ticket makes work happen on its own. Ask someone in the repository to run `/veldo:intake` on it, then review the draft they show you and say when it is ready.

## What happens after: the mirror, and what it does not touch

This is the part people get wrong, so it is stated flatly.

**The mirror does not touch the ticket you filed.** It maintains Veldo's own issues: one epic per plan, one child issue per work item. Each is found by a stable marker label derived from the key it belongs to (`veldo-key-epic-PLAN-0010` for a plan, `veldo-key-child-PLAN-0010-W5` for a work item), so a re-run finds the same issue and updates it in place rather than forking a second one. Every status transition, comment, artifact link, and reassignment the mirror performs lands on those Veldo issues.

**Your ticket is never transitioned, commented on, or reassigned by the mirror.** There is no path from a spec back to the ticket it came from. Intake records your item in the spec's `intake_source` field, but the index the mirror reads carries only the spec id, plan, work item, `tracker_repo`, title, status, and reporter. Wiring your filed ticket into the round trip would mean building an `intake_source` to issue linkage, and that linkage does not exist.

So what does reach your ticket? Whatever the person or agent running intake writes there. That is why the intake skill's last step tells them to post the closing comment with the evidence links (spec id, gate commit, reproduction test path, review verdict) by hand when the fix ships.

### What the mirror writes, and where

When the repo-only mirror is present and someone runs it:

| The spec reaches | Veldo status | The Veldo child issue moves to |
|-|-|-|
| marked ready | `ready` | your mapped "ready" status |
| blocked on a question | `blocked` | your mapped "blocked" status |
| a review verdict recorded | `in_review` | your mapped "in review" status, plus artifact links and a reassignment to the reviewer |
| shipped | `shipped` | your mapped "done" status, plus a closing comment |
| merged | `merged` | your mapped "done" status |

It is driven by the events the Veldo loop already emits, so it needs no bookkeeping from anyone, and it never reads or polls your tracker.

### Your own status names, via the status_map

Veldo does not impose its vocabulary on your board. Each Veldo status is translated to your project's own status name through the `status_map` in `.veldo/trackers.json`. A small one looks like this:

```json
"status_map": {
  "ready": "Ready",
  "blocked": "Blocked",
  "in_review": "In Review",
  "shipped": "Shipped",
  "merged": "Shipped"
}
```

If your board has no status for a given Veldo status, that status is recorded as a keyed comment instead of an invented transition, so the mirror never forces an issue into a state your workflow does not have. Omit the `status_map` entirely and the mirror is comment-only. The shipped template maps onto the same status set the board bootstrap provisions, so the two agree by default.

### At ready-to-test, the child issue hands off to your reviewer

When the build is done and a review verdict is recorded, two things happen on the Veldo child issue at once. The mirror posts a comment with the artifact links that actually exist (the commit always, the pull request and the proof when the events carry them, never fabricated), and it reassigns that child issue away from the Agent user to your reviewer, so it lands in a human's queue for testing rather than sitting on a robot account.

Who the reviewer is comes from `.veldo/trackers.json`: a per-repo `reviewer` overrides a global `reviewer`, and if neither is set it falls back to the reporter recorded on the spec. If none of those is known, the mirror leaves the assignee alone rather than invent one. This happens only at ready-to-test; while the work is being built the child issue stays on the Agent user.

Both writes are idempotent, the links by comment key and the reassignment by target assignee, so a replay adds no duplicate.

### A plan builds an epic and children

A spec that belongs to a plan gets one child issue under that plan's epic. A spec with no plan gets nothing, because there is no epic to place a child under, which is why the mirror wants `plan` and `work` on every spec it should project. A larger effort planned as a Veldo product plan mirrors its whole work graph: the epic is keyed to the plan id and never forks, and every work item becomes a child, so the whole structure is visible even for items not yet started. Each child's status follows its work item's spec status through the same `status_map`; the epic rolls up to the mapped shipped status once every work item has shipped, and stays open until then.

### It is one-way, and the repository wins

- **The mirror only ever writes status, comments, and the ready-to-test assignment.** It never writes a spec or a plan definition back from the tracker. If a tracker issue and the repository disagree, the repository is right. Nothing typed in a ticket comment becomes engineering truth; a decision that changes a requirement is committed to the spec.
- **It is idempotent and never polls.** The mirror is a reconciler: each run it recomputes the desired issue state from the repository and applies it. Replaying the whole event stream, or a doubled event, records no duplicate transition and no duplicate comment. It reads the repository's event stream, never your tracker.

A spec that is not wired for mirroring is skipped by name, not errored, and never partially applied. Four things cause a skip: no `tracker_repo`, no tracker config, a `tracker_repo` that does not resolve, and no `plan` on the spec.

### How the mirror would reach a live tracker

`veldo mirror` is the runner: one reconcile pass that reads the repository's event stream and applies the desired issue state through the live adapter. It is repo-only. In a pack it prints "the tracker mirror runner is repo-only and is not present here" and exits 2.

Where the runner is present, its posture is worth stating: it is opt-in and off by default. Installing Veldo starts no background service, lays no timer, and spawns nothing. Each invocation is one pass, and a cadence is whatever interval the operator chooses to run it again. Live epic and child creation needs the `project` key wired on the connection block, because creating an issue requires a project.

So when someone says the round trip runs on "two services", the accurate count is one command a person runs (`veldo mirror`) and one library nothing calls (`tracker_bridge.py`).

## Starting a whole plan from a requirements page

A structured requirements page can produce a whole Veldo plan rather than a single spec. Two things about how that is triggered:

**It is triggered by page id, not by a ticket.** Someone in the repository calls `intake_plan_from_requirements(adapter, page_id, config, plan_id=...)` with the page's id and a plan id they allocate. There is no watcher and no ticket trigger. A kickoff ticket that points at a page triggers nothing at all today, and if that ticket were assigned to the Agent user, the bridge's draft path drafts a single spec from the ticket, never a plan from the page it mentions. The Deliverables section of the shipped page template still describes the ticket trigger; treat the page id as the input and read that paragraph as intent, not behavior.

**It needs a Deliverables section.** With one, the plan's outcomes come from the page's Outcomes and it gets one work item per named Deliverable, all bound to the repository the page's `veldo-repo:<repo>` label resolves to, with the page linked as the source. Without one, the page drafts a single spec as before. Page content is sanitized so nothing in it can inject plan front matter.

Like every other draft, the plan is a draft: a human refines it, allocates a real spec id per work item, and approves it. The generator never approves its own plan. Once approved, the epic and children appear on the board the next time someone runs the mirror.

## The repo-only board bootstrap

Everything from here to the end of this section describes `veldo jira init`, which is repo-only. In a pack it prints "the Jira bootstrap is repo-only and is not present here" and exits 2. Read it as the reference for what a wired repository sets up, not as something you can run after installing a pack.

### The two-identity model: why the automation cannot approve its own work

The autonomous loop rests on one structural guarantee: the automation must not be able to approve its own work. Veldo achieves that with two distinct identities.

- **An admin identity** performs the one-time board bootstrap (provisioning statuses and the workflow) and the fencing below. It is used only for setup, by a person with tracker-admin rights.
- **A separate, non-human service-account identity** does the runtime writes (status transitions, comments, the ready-to-test reassignment). It is a distinct principal, so its actions are attributable to the automation and it can be restricted. It is fenced out of the terminal approval and decision states: it can advance an issue through the working states but cannot move one into "approved", "decided", or "rejected". Only the approver group can.

A principal can never fence or unfence itself. The fencing is an admin act, and the service account has no group-admin or workflow-admin permission, so it cannot reach the endpoints that would change the fence. This is configuration, not convention.

### Standing up the service-account identity and its OAuth credential

The runtime writer authenticates as a service account using an OAuth 2.0 client-credentials grant, a machine-to-machine credential with no interactive login and no human user behind it:

1. Create a service account in your identity provider or tracker admin, dedicated to the automation.
2. Create an OAuth client-credentials app bound to that account and record its client id and client secret. Put each in your secrets store; the config references them, it never holds the raw values.
3. Grant the credential the minimal scopes it needs and no more:
   - `read:jira-work`
   - `write:jira-work`
   - `read:jira-user`
   Do not grant it group-admin or workflow-admin scopes. Withholding those is what makes the fence structural: even if asked, the service account cannot alter groups or the workflow restriction.

A client-credentials token is short-lived and carries no refresh token; the runner fetches a fresh one and re-fetches when it lapses. It drives the tracker's API gateway, not the site URL, because a site-URL call with basic auth does not accept a service-account token.

### The auth-mode config

The jira-cloud tracker block in `.veldo/trackers.json` selects the auth mode by reference. The default is unchanged, so an existing basic-auth setup keeps working:

```json
"trackers": {
  "primary": {
    "kind": "jira-cloud",
    "base_url": "https://YOUR-SITE.example",
    "auth": "basic",
    "email": "YOU@example.com",
    "token_ref": "env:YOUR_TOKEN_VAR"
  }
}
```

To run the writes as the fenced service account, switch that block to the OAuth mode with secret references, never the raw client id or secret:

```json
"trackers": {
  "primary": {
    "kind": "jira-cloud",
    "base_url": "https://YOUR-SITE.example",
    "auth": "oauth-client-credentials",
    "client_id_ref": "env:YOUR_CLIENT_ID_VAR",
    "client_secret_ref": "env:YOUR_CLIENT_SECRET_VAR",
    "project": "YOUR_PROJECT_KEY"
  }
}
```

Either way, a raw credential never appears in a config file, a prompt, a proof, or a log, and the connection fails closed if no token resolves. If your `cloud_id` is known you can set it on the block to skip the one-time lookup; otherwise it is resolved once from the credential's accessible resources.

### The fence config

The board bootstrap fences the board in the same pass, driven by a `fence` block under `bootstrap`:

```json
"bootstrap": {
  "project_key": "YOUR_PROJECT_KEY",
  "fence": {
    "agent_group": "YOUR_AGENT_GROUP",
    "approver_group": "YOUR_APPROVER_GROUP",
    "agent_account_id": "YOUR_SERVICE_ACCOUNT_ACCOUNT_ID",
    "terminal_states": ["Approved", "Decided", "Rejected"]
  }
}
```

The bootstrap ensures both groups exist, places the service account's account id in the agent group and not in the approver group, and restricts each named terminal transition so only the approver group may fire it. It is idempotent, and it fails loud by name if you name a terminal transition your workflow does not have rather than silently skipping it. Omit the `fence` block and the board is provisioned but not fenced.

### What the live provisioner actually does

The live company-managed provisioner needs a real Jira and a scoped admin token, so it never runs in the gate; the gate proves the bootstrap logic over a fake tracker. Its Jira Cloud REST v3 calls are the ones proven against a real board, so you can audit them:

- **Statuses are global.** A company-managed lifecycle status is created with `POST /rest/api/3/statuses`, scope `GLOBAL`, its category mapped onto Jira's `TODO | IN_PROGRESS | DONE`. Existing statuses are read from the paginated `GET /rest/api/3/statuses/search` and reused by name.
- **The workflow is edited through the bulk API.** The provisioner reads the workflow via `POST /rest/api/3/workflows`, validates a change via `POST /rest/api/3/workflows/update/validation`, and applies it via `POST /rest/api/3/workflows/update`. Existing statuses are kept, so an active workflow needs no status migration.
- **The fence is a workflow transition condition.** Each transition landing on a terminal status is restricted with the `system:restrict-issue-transition` condition scoped to the approver group. Groups are addressed by id: created with `POST /rest/api/3/group`, resolved by name with `GET /rest/api/3/groups/picker`, and membership read and written through `GET /rest/api/3/group/member` and `POST` or `DELETE /rest/api/3/group/user`.
- **Issue types are attached, never faked.** The bootstrap attaches an existing instance issue type to the project's issue-type scheme (`PUT /rest/api/3/issuetypescheme/{schemeId}/issuetype`); a type your instance does not have fails loud rather than mapping to a wrong type.

One caution worth carrying: this module shipped once with a method that could not be called in any configuration, because an instance attribute shadowed it, and the offline suite could not see it by construction. Codified from a proven script is not the same as the codified path ran. A composition check now refuses that class of name collision, but only executing the module against a real Jira proves a wrong endpoint, payload, or scope.

### Adding a new decision issue type

The bootstrap only attaches issue types that already exist in your Jira instance (Epic for plans, Task for specs by default). If you want a dedicated issue type for human decisions and your instance does not have one, that is a one-time admin action, separate from the bootstrap: create a standard issue type with `POST /rest/api/3/issuetype` (`type: standard`, `hierarchyLevel: 0`), then add it to your project's issue-type scheme with `PUT /rest/api/3/issuetypescheme/{schemeId}/issuetype`. A hierarchy-level-1 type such as Epic cannot be created this way and must already exist. Once the type is in your instance, name it in `bootstrap.issue_types` and the bootstrap attaches it like any other.

## A full round-trip, walked through once

Start to finish, with a bug, in a repository that has the repo-only modules wired and someone running the mirror:

1. **You file it.** You open a Jira bug: "Checkout total is wrong when a coupon is applied." You add the label `veldo-repo:web-app`. That is the whole of your job.
2. **Someone runs intake.** They run `/veldo:intake` on your ticket. The agent reads it, reproduces the wrong total as a failing test (that becomes AC1), and drafts a spec in the `web-app` repository with your ticket linked in `intake_source` and `tracker_repo` set to `web-app`.
3. **The owner finishes the draft and marks it ready.** Your ticket does not move. On the next mirror run, a Veldo child issue appears under the plan's epic and moves to your mapped ready status.
4. **The change is built and reviewed.** At the review verdict the mirror posts the artifact links on that child issue and reassigns it to your reviewer. Your ticket still has not moved.
5. **It ships.** The mirror moves the child issue to your mapped done status and posts the closing comment there. Your own ticket is closed by whoever ran intake, following the skill's last step: a comment with the spec id, the gate commit, the reproduction test path, and the review verdict.

Where does that leave you as the filer? Watch the Veldo child issue, or ask for its key in a comment on your ticket at intake time. The one thing you cannot do today is watch only your own ticket and assume it is telling you the truth.

A Confluence requirements page runs the same way, except intake takes AC1 to ACn from your page's Acceptance Criteria instead of reproducing a bug. A wiki page has no status workflow, so nothing is ever transitioned on the page itself.

## Who does what

| You | Veldo, where the machinery is wired | A person, by hand |
|-|-|-|
| Put a `veldo-repo:<repo>` label on the ticket or page | Resolves the target repository, or refuses by name | Runs `/veldo:intake` on your item |
| Fill Outcomes and Acceptance Criteria on a requirements page | Turns them into the draft spec's acceptance criteria | Completes the draft and marks it ready |
| Answer the one product question intake raises | Reproduces a bug as AC1 and links the source | Allocates the plan id and per-item spec ids for a plan draft |
| Read the Veldo child issue to see where the work is | Transitions that child issue through your own statuses, one-way | Runs `veldo mirror` on a cadence they choose |
| (nothing) | Posts the closing comment and artifact links on the child issue | Posts the closing comment on the ticket you filed |
| (nothing) | Builds the epic and child issues for a planned effort | Everything the inbound bridge would do, until it has a runner |

## Where the pieces live

This guide is the workflow companion to the capability reference. For what each piece is and the mechanical-versus-reference split, see [`plugin.md` section 12, Tracker integration](plugin.md#12-tracker-integration-jira-and-confluence).

The authority on what ships is `.veldo/capabilities.yaml`. Every tracker entry there carries a `home` and, where it applies, `scope: repo-only`. If an entry you are relying on says `repo-only`, it is not in your pack, and no sentence in this guide about it applies to your repository yet. The docs defer to that file, including this one.

## Document History

| Version | Date | Changes |
|-|-|-|
| 1.0 | 2026-07-20 | Initial operator guide (VELDO-0611): the human workflow for tracker intake and the mirror round-trip, companion to the Plugin Guide section 12 capability reference. Covers flagging a ticket or requirements page with a routing signal, running intake and what it drafts, the fail-closed refusal, the one-way status mirror through the per-org status_map, epic and child structure for a plan, the one-way repository-wins and never-poll rules, and a full round-trip walked through once. |
| 1.1 | 2026-07-21 | The autonomous loop section (VELDO-1008 of PLAN-0010, plugin 3.6.0): the three moves in Jira, the eligibility triple, the draft-then-promote two-stage gate, the ready-to-test handoff, starting a plan from a requirements page, and the opt-in `veldo mirror` runner. |
| 1.2 | 2026-07-23 | The fenced agent identity (VELDO-0614): the two-identity model, standing up the service account and its OAuth client-credentials, the minimal scopes, the auth-mode config, and the fence config. Placeholders throughout; no secret and no organization-specific value. |
| 1.3 | 2026-07-23 | Codified the proven live Jira REST shapes (VELDO-0614 F3): GLOBAL-scope statuses, the bulk workflow validate-then-apply edit, the transition-condition fence, attach-not-fake issue types, and the optional admin one-off for creating a decision issue type. |
| 1.4 | 2026-08-10 | Corrected four claims an audit found false, all of which were in front of readers of the public distribution. (1) The mirror does not project onto the ticket you filed: it maintains Veldo's own issues, one epic per plan and one child per work item found by a marker label, and the filed ticket is never transitioned, commented on, or reassigned, because no `intake_source` to issue linkage exists. Every "your ticket moves" sentence, the status table, the ready-to-test section, and the walkthrough are rewritten accordingly. (2) A new opening section states what ships and what does not: only the routing resolver and eligibility rule, the `tracker_repo` validator check, and the `/veldo:intake` skill ship, while the intake modules, adapters, mirror, bridge, runner, and board bootstrap are `scope: repo-only`, and `veldo mirror` and `veldo jira init` exit 2 in an adopter's repository. It also lists what a repository must supply first. (3) The inbound bridge is logic with no runner: nothing invokes `reconcile_drafts` or `reconcile_promotions` outside the module's selfcheck and the gate, so nothing can be turned on and the manual intake path is the only inbound route; the "two services" count is corrected to one command and one uncalled library. (4) A plan draft is produced by running the plan intake against a page BY PAGE ID; a kickoff ticket pointing at a page triggers nothing, and the same ticket assigned to the Agent user would draft a single spec. The repo-only bootstrap sections are kept and relabelled as reference for a wired repository. |
