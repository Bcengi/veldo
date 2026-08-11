# The Veldo Runbook

*The complete operational manual: every change type, every situation, every role, every keystroke. This is the document that takes a team from 0% to 100% of work done through Veldo.*

*Version 1.7, 2026-07-22*

## How to read this

Part I is five full runbooks, keystroke-exact: what you say, what comes back, what files appear with their contents. The first four operate one change; the fifth (Runbook E) operates a whole iteration through the planning layer. Read them with one rule in mind: steps marked as the agent's are shown for transparency, not for you to perform; in every runbook the human's actions are a handful of plain sentences (state intent, answer a question, approve, judge a delivered picture, say merge), and if you ever find yourself running git commands or assembling your own comparison, the setup is broken, not you. Transcript conventions: **YOU TYPE** blocks are entered verbatim; **AGENT** lines are what the agent prints; **FILE CREATED** shows the path and content of a file that now exists; **YOU CHECK** gives a command and the output you should see. Runbooks A and B narrate the same conventions inline. Parts II through V are the reference: change types, situations, roles, and administration. The cheat sheet at the end is the whole document in one table.

# Part I - The loop, operated

## Runbook A - Your first feature, end to end

The situation: the search endpoint has no rate limiting and a partner just hammered it. This runbook is every keystroke of your first real Veldo change.

**Step 1 - You state intent.** You type:

```
/veldo:spec Add rate limiting to the search endpoint
```

**Step 2 - The agent interviews you.** It asks; you answer in plain words:

```
Agent: What outcome matters: per-user limits, per-API-key, or global?
You:   Per API key. 60 requests a minute, burst of 10.
Agent: What should a limited caller receive?
You:   429 with a Retry-After header.
Agent: Should any callers be exempt?
You:   The internal service key bypasses it.
Agent: Rollback if this misbehaves in production?
You:   Put it behind a flag, rate_limit_search.
```

**Step 3 - The spec file appears.** `specs/VELDO-0207-search-rate-limit.md`:

```yaml
---
schema: veldo.spec/v1
id: VELDO-0207
title: Rate limit the search endpoint
status: draft
risk: standard
owner: dmitry
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A key exceeding 60 requests/minute (burst 10) receives 429 with a
          Retry-After header.
  - id: AC2
    text: Requests under the limit behave exactly as before; the existing
          search suite passes unchanged.
  - id: AC3
    text: The internal service key is exempt.
required_evidence: [unit, integration]
rollback: disable the rate_limit_search flag
reversible: true
---
```

The agent says: `Spec drafted as VELDO-0207 (draft). Say "ready" to approve it, or edit anything first.`

**Step 4 - You approve and run.** You type:

```
Ready. /veldo:run VELDO-0207
```

**Step 5 - You watch the run (or walk away).** The run prints its progress; the parts worth seeing:

```
implementer: rate limiter behind rate_limit_search; 9 tests added
== tests            passed (1,516)
== secret scan      passed
== veldo contracts   passed
GATE: GREEN (7d81c2e)
proof: proof/VELDO-0207/manifest.json written (3/3 criteria -> evidence)
review: dispatching veldo-reviewer (fresh context)
review: PASS, no blocking findings
         note: consider a metric on 429 rate (non-blocking)
```

The proof manifest it wrote, abbreviated:

```json
{
  "schema": "veldo.proof/v1",
  "spec_id": "VELDO-0207",
  "commit": "7d81c2e",
  "criteria": [
    {"id": "AC1", "status": "passed",
     "evidence": [{"type": "test", "ref": "tests/search/test_rate_limit.py::test_429_and_retry_after"}]},
    {"id": "AC2", "status": "passed",
     "evidence": [{"type": "test", "ref": "existing search suite, 62 tests, unchanged"}]},
    {"id": "AC3", "status": "passed",
     "evidence": [{"type": "test", "ref": "tests/search/test_rate_limit.py::test_internal_key_exempt"}]}
  ],
  "checks": [{"name": "verify", "command": "./scripts/verify.sh", "result": "pass"}],
  "rollback": "rate_limit_search flag off"
}
```

**Step 6 - See the guard refuse once, on purpose.** Make any edit (add a comment to a file) and ask the agent to push without re-running the gate:

```
You:   push it
Guard: Veldo guard: blocked. The canonical gate is not green for HEAD (91acb03).
       Run ./scripts/verify.sh on the current state first. Proof is valid only
       for the state it ran against.
```

That message is the method working. Revert the edit (or re-run the gate) and continue.

**Step 7 - Merge and keep the receipt.** You type `merge`. The evidence commit (proof + verdict + spec status flip, touching only `proof/`, `.veldo/`, `specs/`) inherits the implementation commit's proof, the push goes through, and the final receipt reads:

```
VELDO-0207 shipped.
  3/3 criteria proven. Gate green on 7d81c2e (1,516 tests).
  Review: pass. Rollback: flag off.
```

**What you actually did:** described a rate limit in four sentences, said "ready", watched, said "merge". Elapsed human attention: about three minutes.

## Runbook B - A UI change through the design lane

The situation: the orders screen shows nothing when a customer has no orders. Design has mocked an empty state in Figma. You want it built exactly to the mock.

**Step 1 - You start, handing the agent the design itself.** You type:

```
/veldo:spec Build the empty state for the orders screen from this mock:
https://www.figma.com/design/aB3xY9/Orders?node-id=214-1187
```

**Step 2 - The agent reads the mock and interviews you.** It pulls the node through the Figma API and comes back with what it found, then asks only what the mock cannot tell it:

```
Agent: I read node 214-1187 ("Orders / Empty state"). Extracted:
  component: IllustrationCard (library component, exists in code as <IllustrationCard>)
  illustration: "empty-box" asset, 160x160
  heading: "No orders yet" - text token heading-m
  body: "When you place your first order, it will show up here." - text token body-s, color token text-secondary
  spacing: 24 above heading (token space-6), 16 between heading and body (token space-4)
  button: "Browse products" - Button/primary, full width on mobile

Three questions the mock does not answer:
1. Where does "Browse products" navigate?
2. Does the empty state also apply to the filtered view (filters active, zero results), or only to truly-no-orders?
3. Desktop and mobile, or mobile only?
```

**Step 3 - You answer in plain words.** You type:

```
1. To /products.
2. Only truly-no-orders. Filtered-empty keeps the current "no results" text.
3. Both, same layout, the card centers in the content area on desktop.
```

**Step 4 - The spec file appears.** The agent writes `specs/VELDO-0214-orders-empty-state.md` and tells you so. Its contents:

```yaml
---
schema: veldo.spec/v1
id: VELDO-0214
title: Orders screen empty state
status: draft
risk: standard
owner: dmitry
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: "The journey, driven end to end: a customer with zero orders and no
          filters lands on the orders screen, sees the empty state, taps
          Browse products, and arrives at /products with products visible.
          Runs at desktop and mobile widths."
  - id: AC2
    text: "The failure journey: if navigation to /products fails, the button
          re-enables, an actionable error shows, and focus stays on the button."
  - id: AC3
    text: With active filters and zero results, the existing "no results" view is
          unchanged (journey: apply filter, clear results, observe).
  - id: AC4
    text: The empty state renders IllustrationCard with the empty-box asset,
          heading "No orders yet" (heading-m), body copy (body-s /
          text-secondary), spacing space-6 above the heading, space-4 between.
  - id: AC5
    text: No raw color, spacing, radius, or font values are introduced; the token
          lint stays clean.
  - id: AC6
    text: Desktop and mobile captures of every named state match the approved
          baselines within tolerance.
required_evidence: [unit, journeys, ui_states, baseline, figma_composite, design_review]
rollback: revert the commit; the empty state is a pure addition
reversible: true
---

## Intent

A customer with no orders should understand what this screen is for and have
one obvious next step, exactly as designed in Figma node 214-1187.
```

**Step 5 - You approve it to ready.** You type:

```
Looks right. Make it ready and run it.
```

The agent flips `status: draft` to `status: ready`, regenerates `specs/index.md`, and starts `/veldo:run VELDO-0214`.

**Step 6 - The gate catches a fidelity bug so you never see it.** The implementer builds the component and runs the gate. First pass, the token lint fails, and you can see exactly why in the run log:

```
== design-token-lint
src/screens/Orders/EmptyState.tsx:41
  margin-top: 24px        <- raw value; use space-6
   design-token-lint: FAIL
GATE: RED (a41f09c)
```

The implementer replaces the raw value with the token and reruns:

```
== tests            passed (9 new unit: rendering, tokens, filtered-empty untouched)
== journeys         passed (3 driven end to end at 2 widths:
                     empty->browse->products arrives with products visible;
                     failed navigation re-enables button, error shown, focus kept;
                     filtered-empty view unchanged)
== ui-states        captured and asserted (empty, navigating, nav-failed)
== design-token-lint passed
== build            passed
== secret scan      passed
== veldo contracts   passed
GATE: GREEN (b52e11d)
```

The journeys line is the heart of UI proof: the agent DROVE the flows a user
would take, both the happy one and the failing one, and asserted behavior at
every step - navigation, state transitions, focus. Screenshots come next, but
they are the fidelity layer, not the proof of function.

You did nothing during this step; it is shown so you know what the lint buys you.

**Step 7 - The agent builds the visual comparison and DELIVERS it to you.** You never assemble anything. The agent: exports the exact Figma frame as a PNG through the Figma API, captures the rendered screen with Playwright at both viewports, and composites them side by side with a pixel-diff heat strip between them:

```
figma export:  proof/VELDO-0214/visual/figma-214-1187-desktop.png
render:        proof/VELDO-0214/visual/rendered-desktop.png (1280x800)
render:        proof/VELDO-0214/visual/rendered-mobile.png  (390x844)
composites:    proof/VELDO-0214/visual/composite-desktop.png
               proof/VELDO-0214/visual/composite-mobile.png
               (mock | rendered | diff strip, mismatched pixels highlighted)
```

Then it sends you the two composite IMAGES, in chat, where you live. You look at two pictures and reply in one line:

```
Desktop approved. Mobile: the button sits 8px from the bottom edge, the mock
shows 24. Fix and resend.
```

The implementer fixes it (token space-6), recaptures, sends the new composite, and this time you reply `Approved`. Your approved captures become the locked baselines: from this moment the gate fails on drift beyond tolerance, forever, without you. The composites stay in `proof/VELDO-0214/visual/` as evidence: the validation is a picture on the record, not a sentence.

**Step 8 - The design owner records their verdict.** This is a human review lane, so the change cannot merge without it. The design owner (say, Maya) receives the same two composites plus the interaction recording (the Playwright video of the flow being driven), compares, and tells the agent in her own session:

```
Maya: Record my design review for VELDO-0214: approved. The empty state matches
      the mock on both breakpoints.
```

The agent writes `proof/VELDO-0214/design-verdict.json`:

```json
{
  "schema": "veldo.verdict/v1",
  "spec_id": "VELDO-0214",
  "commit": "b52e11d",
  "reviewer": {"human": "maya", "role": "design-owner", "context": "fresh"},
  "verdict": "pass",
  "criteria": [{"id": "AC5", "assessment": "satisfied"}],
  "findings": {"blocking": [], "non_blocking": []}
}
```

Her name is in the file; the file is bound to the exact commit; if the commit changes, her verdict is stale and the merge blocks again.

**Step 9 - Proof, review, receipt.** The run finishes the standard way: the proof manifest lands at `proof/VELDO-0214/manifest.json` mapping AC1-AC5 to the tests, the lint, and the visual artifacts (the composites ARE evidence, referenced by the manifest); the fresh-context reviewer files its verdict; and you get the receipt, with the final composites attached one more time:

```
VELDO-0214 ready to merge.
  6/6 criteria proven. Gate green on b52e11d.
  Flows: 3 journeys driven at 2 widths (happy, failure, filtered) - all pass.
  States: empty / navigating / nav-failed captured and asserted.
  Fidelity: composites match the mock; baselines locked.
  Agent review: pass. Design review: pass (maya, from composites + the
  interaction recording).
Merge?
```

You type `Merge`, and it lands with all of its evidence.

**What you actually did in this entire runbook:** pasted a Figma link, answered three questions, corrected one spacing bug by eye, said "approved" twice, and said "merge". Everything else is on the record without you.

## Runbook C - A bug from a support ticket

The situation: support forwards ticket 184: "CSV exports show the previous calendar day for customers west of UTC. Account 4821 selected March 10, the export says March 9."

Count your actions in this runbook: you type three sentences. Everything else is shown so you can see what the machine does on your behalf, not because you do it.

**Step 1 - YOU (sentence one):**

```
Turn ticket 184 into work. Don't implement until the timezone expectation is explicit.
```

**Step 2 - AGENT (automatic).** It reads the ticket, reproduces in a scratch workspace, and comes back with the reproduction and the one question that is genuinely a product decision:

```
Agent: Reproduced. A date-only value parsed as UTC midnight and formatted in
       America/Los_Angeles renders as the previous day. The existing export
       tests all pass; none applies a timezone west of UTC.
       One decision: should date-only report fields preserve the customer's
       selected calendar date regardless of timezone?
```

**Step 3 - YOU (sentence two):**

```
Yes. Date-only fields are calendar dates, not timestamps. Timestamp fields
keep their current conversion.
```

**Step 4 - AGENT (automatic).** It writes the reproduction as a failing test, runs it to prove it fails on the current code, and drafts the spec with that test as the first criterion:

```
Agent: tests/export/test_date_only_timezone.py written and run against the
       current code: FAILED as expected (expected 2026-03-10, got 2026-03-09).
       Spec drafted: VELDO-0307, three criteria (reproduction passes after the
       change; UTC and Asia/Tokyo render the same date; timestamp fields and
       CSV shape unchanged). Risk standard, no protected paths. Ready?
```

**Step 5 - YOU (sentence three):**

```
Ready.
```

**Step 6 - AGENT (the whole run, one transcript).** `/veldo:run VELDO-0307` executes without you:

```
implementer: date-only values routed through a calendar-date serializer;
             timestamp path untouched; 4 tests added
== tests            passed (previously-failing reproduction now passes)
== secret scan      passed
== veldo contracts   passed
GATE: GREEN (71bc81e)
proof: proof/VELDO-0307/manifest.json (reproduction evidence records BOTH runs:
       failed-before at the parent commit, passed-after at 71bc81e)
review: fresh-context reviewer PASS - confirmed the test genuinely fails on
        the parent commit and the timestamp path is untouched
evidence commit + push: guard satisfied (gate green, proof for HEAD)
merged.
ticket 184: closing comment posted -
  "Fixed and merged. Root cause: address updates rebuilt pricing input...
   date-only fields now serialize as calendar dates. Evidence: spec VELDO-0307,
   gate green on 71bc81e, reproduction test attached, independent review pass."
```

**Step 7 - The receipt you see:**

```
VELDO-0307 shipped. 3/3 criteria proven (reproduction fail->pass recorded).
Review: pass. Ticket 184 closed with evidence links. Rollback: revert.
```

**What this teaches:** a bug's first acceptance criterion is its reproduction, recorded failing BEFORE the fix and passing after, and the reporter never leaves their tool. And the human count was three sentences: hand it over, decide the one product question, approve.

## Runbook D - A protected-path change

1. **YOU TYPE**

```text
/veldo:spec Increase the production billing provider request timeout from 2 seconds to 3 seconds in billing/config/production.yaml. This is needed because provider requests are timing out during peak settlement.
```

2. **AGENT ASKS/REPLIES**

```text
The requested file matches protected path billing/**.

Policy result:
- Requested risk: standard
- Protected-path floor: high
- Effective risk: high
- Human approval: required
- Minimum review independence: L2

Risk cannot be lowered below high.

I need:
1. The observable success criterion.
2. The rollback condition.
3. The production owner authorized to approve this change.
4. The expiry period for that approval.
```

3. **YOU ANSWER**

```text
Success means the production billing provider timeout is exactly 3 seconds and staging remains 2 seconds. Roll back if provider error rate or p95 billing latency increases after deployment. Elena Garcia is the billing owner. Approval should expire after one hour.
```

4. **AGENT ASKS/REPLIES**

```text
What must not change, and how will configuration parsing be tested?
```

5. **YOU ANSWER**

```text
Do not change retry counts, provider URLs, credentials, staging config, or request code. Add a configuration test that loads production and staging and asserts their timeout values. Owner is Sam Patel.
```

6. **FILE CREATED**

`/workspace/payments/billing/specs/VELDO-0401-production-provider-timeout.md`

```markdown
---
schema: veldo.spec/v1
id: VELDO-0401
title: Increase production billing provider timeout
status: draft
risk: high
owner: Sam Patel
human_approval: required
protected_paths:
  - billing/config/production.yaml
acceptance_criteria:
  - id: AC1
    text: Loading billing/config/production.yaml returns a billing provider request timeout of exactly 3 seconds.
  - id: AC2
    text: Loading billing/config/staging.yaml continues to return a billing provider request timeout of exactly 2 seconds.
  - id: AC3
    text: Retry counts, provider URLs, credentials, and billing request code are unchanged.
required_evidence: [unit]
rollback: Revert the configuration commit if provider error rate or p95 billing latency increases after deployment.
---

## Intent

Reduce peak-settlement billing provider timeouts by increasing only the production provider request timeout from 2 seconds to 3 seconds.

## Context

The target file billing/config/production.yaml matches protected path billing/**. Policy floors the effective risk to high and requires approval from the billing owner.

Elena Garcia is the billing owner. Approval must be bound to the final commit and expires one hour after recording.

## Out of scope

Retry counts, provider URLs, credentials, staging configuration, and billing request code are not changed.

## Notes

The production timeout must be exactly 3 seconds. Staging must remain exactly 2 seconds. Add a configuration-loading test for both environments.
```

7. **AGENT ASKS/REPLIES**

```text
The draft validates at effective risk high. The protected path and required human approval are recorded.

Reply with approval to mark the specification ready. This approves the intent only. It does not replace the commit-bound billing-owner approval required after implementation and proof.
```

8. **YOU ANSWER**

```text
I approve VELDO-0401 as ready.
```

9. **FILE UPDATED**

`specs/VELDO-0401-production-provider-timeout.md`: same file, `status: ready`. The agent reminds you: this approves the intent only; the commit-bound billing-owner approval still comes after implementation and proof.

10. **YOU TYPE**

```text
/veldo:run VELDO-0401
```

11. **FILE CREATED**

`/workspace/payments/billing/billing/config/production.yaml`

```yaml
schema: billing.config/v1
provider:
  url_env: BILLING_PROVIDER_URL
  request_timeout_seconds: 3
  retry_count: 2
```

12. **FILE CREATED**

`/workspace/payments/billing/tests/test_billing_config.py`

```python
from billing.config import load_config


def test_production_provider_timeout_is_three_seconds():
    config = load_config("production")

    assert config.provider.request_timeout_seconds == 3
    assert config.provider.retry_count == 2


def test_staging_provider_timeout_remains_two_seconds():
    config = load_config("staging")

    assert config.provider.request_timeout_seconds == 2
```

13. **AGENT ASKS/REPLIES**

```text
Implementation commit:
d1fb1b70db9f06cf055ff3eec78a925ed9935f92

Running the expanded high-risk gate.
```

14. **AGENT ASKS/REPLIES**

```text
== format
61 files already formatted
   format: pass
== lint
All checks passed
   lint: pass
== types
Success: no issues found in 29 source files
   types: pass
== tests
....................................................                     [100%]
52 passed in 2.47s
   tests: pass
== build
Billing configuration build passed
   build: pass
== extra
Production configuration policy checks passed
   extra: pass
== secret scan
   secret scan: pass
== veldo contracts
OK: 1 specification, 0 proofs, 0 verdicts
   contracts: pass

GATE: GREEN (d1fb1b70db9f06cf055ff3eec78a925ed9935f92)
```

15. **FILE CREATED**

`/workspace/payments/billing/proof/VELDO-0401/manifest.json`

```json
{
  "schema": "veldo.proof/v1",
  "spec_id": "VELDO-0401",
  "commit": "d1fb1b70db9f06cf055ff3eec78a925ed9935f92",
  "produced_at": "2026-08-07T16:05:12Z",
  "producer": {
    "role": "implementation",
    "model": "claude-sonnet-4-5-20250929",
    "runtime": "claude-code"
  },
  "criteria": [
    {
      "id": "AC1",
      "status": "passed",
      "evidence": [
        {
          "type": "test",
          "ref": "tests/test_billing_config.py::test_production_provider_timeout_is_three_seconds"
        }
      ]
    },
    {
      "id": "AC2",
      "status": "passed",
      "evidence": [
        {
          "type": "test",
          "ref": "tests/test_billing_config.py::test_staging_provider_timeout_remains_two_seconds"
        }
      ]
    },
    {
      "id": "AC3",
      "status": "passed",
      "evidence": [
        {
          "type": "diff",
          "ref": "billing/config/production.yaml"
        }
      ]
    }
  ],
  "checks": [
    {
      "name": "verify",
      "command": "./scripts/verify.sh",
      "result": "pass"
    }
  ],
  "rollback": "Revert commit d1fb1b70db9f06cf055ff3eec78a925ed9935f92 if provider error rate or p95 billing latency increases."
}
```

16. **FILE CREATED**

`/workspace/payments/billing/proof/VELDO-0401/verdict.json`

```json
{
  "schema": "veldo.verdict/v1",
  "spec_id": "VELDO-0401",
  "commit": "d1fb1b70db9f06cf055ff3eec78a925ed9935f92",
  "reviewer": {
    "model": "claude-opus-4-1-20250805",
    "context": "fresh"
  },
  "verdict": "pass",
  "criteria": [
    {
      "id": "AC1",
      "assessment": "satisfied"
    },
    {
      "id": "AC2",
      "assessment": "satisfied"
    },
    {
      "id": "AC3",
      "assessment": "satisfied"
    }
  ],
  "findings": {
    "blocking": [],
    "non_blocking": []
  },
  "test_assessment": "Configuration tests load both production and staging. The final diff changes only the production timeout and adds tests and Veldo artifacts."
}
```

17. **AGENT ASKS/REPLIES**

```text
The implementation, proof, and independent review pass.

Merge is blocked by one required human action:

Required approver:
- Elena Garcia
- Role: billing-owner

Approval scope:
- Spec: VELDO-0401
- Commit: d1fb1b70db9f06cf055ff3eec78a925ed9935f92
- Proof: proof/VELDO-0401/manifest.json
- Expiry: one hour after recording

Elena must state her identity, decision, and reason. Approval of a different commit will not satisfy policy.
```

18. **YOU ANSWER**

```text
I am Elena Garcia, billing owner. I approve VELDO-0401 for commit d1fb1b70db9f06cf055ff3eec78a925ed9935f92. I reviewed the production-only timeout change, the staging assertion, the unchanged retry count, the green expanded gate, and proof/VELDO-0401/manifest.json. The change is reversible and approved for deployment. Record this approval with a one hour expiry.
```

19. **AGENT ASKS/REPLIES**

```text
Recording approval apr-0401.

Recorded at: 2026-08-07T16:12:00Z
Expires at: 2026-08-07T17:12:00Z
Bound commit: d1fb1b70db9f06cf055ff3eec78a925ed9935f92
```

20. **FILE CREATED**

`/workspace/payments/billing/proof/VELDO-0401/approval-apr-0401.json`

```json
{
  "schema": "veldo.approval/v1",
  "id": "apr-0401",
  "decision": "approved",
  "approver": {
    "id": "elena-garcia",
    "role": "billing-owner"
  },
  "scope": {
    "spec_id": "VELDO-0401",
    "commit": "d1fb1b70db9f06cf055ff3eec78a925ed9935f92",
    "proof": "proof/VELDO-0401/manifest.json"
  },
  "reason": "Reviewed the production-only timeout change, staging assertion, unchanged retry count, green expanded gate, and proof. The change is reversible and approved for deployment.",
  "recorded_at": "2026-08-07T16:12:00Z",
  "expires_at": "2026-08-07T17:12:00Z"
}
```

21. **AGENT ASKS/REPLIES**

```text
Veldo receipt for VELDO-0401

Gate:
- Green for d1fb1b70db9f06cf055ff3eec78a925ed9935f92

Proof:
- Valid for d1fb1b70db9f06cf055ff3eec78a925ed9935f92

Review:
- Pass
- Blocking findings 0

Protected-path approval:
- Approved by Elena Garcia
- Bound to d1fb1b70db9f06cf055ff3eec78a925ed9935f92
- Expires at 2026-08-07T17:12:00Z

The change is ready to merge until the approval expires or the implementation commit changes.
```

22. **YOU ASK FOR ONE MORE THING** (this is the interesting part: watch what it does to the approval)

```
Also tag the change with ticket SETTLE-882 in the config comment.
```

23. **AGENT** (automatic): amends the implementation commit with the tag.

```
Amended: 0a98ce4 "VELDO-0401 increase provider timeout for SETTLE-882"
```

24. **AGENT** (automatic): attempts the push.

26. **AGENT ASKS/REPLIES**

```text
Veldo guard: blocked. git push was not executed.

HEAD:
0a98ce4e283eea07118bb4a5f967743fb385a336

Gate:
STALE
The green gate is bound to d1fb1b70db9f06cf055ff3eec78a925ed9935f92.

Proof:
STALE
proof/VELDO-0401/manifest.json is bound to d1fb1b70db9f06cf055ff3eec78a925ed9935f92.

Run ./scripts/verify.sh (or /veldo:run VELDO-0401) on the current state first.

Agent: The recorded approval apr-0401 is also stale for the same reason: it names
the previous commit. After re-proving, Elena must approve the new commit.
```

27. **YOU TYPE**

```text
/veldo:run VELDO-0401
```

28. **AGENT ASKS/REPLIES**

```text
The implementation already satisfies the ready specification. The commit changed after the previous gate, proof, review, and approval.

I will rerun the expanded gate and regenerate proof and review for commit 0a98ce4e283eea07118bb4a5f967743fb385a336.
```

29. **AGENT ASKS/REPLIES**

```text
== format
61 files already formatted
   format: pass
== lint
All checks passed
   lint: pass
== types
Success: no issues found in 29 source files
   types: pass
== tests
....................................................                     [100%]
52 passed in 2.43s
   tests: pass
== build
Billing configuration build passed
   build: pass
== extra
Production configuration policy checks passed
   extra: pass
== secret scan
   secret scan: pass
== veldo contracts
OK: 1 specification, 1 proof, 1 verdict
   contracts: pass

GATE: GREEN (0a98ce4e283eea07118bb4a5f967743fb385a336)
```

30. **FILE CREATED**

`/workspace/payments/billing/proof/VELDO-0401/manifest.json`

```json
{
  "schema": "veldo.proof/v1",
  "spec_id": "VELDO-0401",
  "commit": "0a98ce4e283eea07118bb4a5f967743fb385a336",
  "produced_at": "2026-08-07T16:19:31Z",
  "producer": {
    "role": "implementation",
    "model": "claude-sonnet-4-5-20250929",
    "runtime": "claude-code"
  },
  "criteria": [
    {
      "id": "AC1",
      "status": "passed",
      "evidence": [
        {
          "type": "test",
          "ref": "tests/test_billing_config.py::test_production_provider_timeout_is_three_seconds"
        }
      ]
    },
    {
      "id": "AC2",
      "status": "passed",
      "evidence": [
        {
          "type": "test",
          "ref": "tests/test_billing_config.py::test_staging_provider_timeout_remains_two_seconds"
        }
      ]
    },
    {
      "id": "AC3",
      "status": "passed",
      "evidence": [
        {
          "type": "diff",
          "ref": "billing/config/production.yaml"
        }
      ]
    }
  ],
  "checks": [
    {
      "name": "verify",
      "command": "./scripts/verify.sh",
      "result": "pass"
    }
  ],
  "rollback": "Revert commit 0a98ce4e283eea07118bb4a5f967743fb385a336 if provider error rate or p95 billing latency increases."
}
```

31. **FILE CREATED**

`/workspace/payments/billing/proof/VELDO-0401/verdict.json`

```json
{
  "schema": "veldo.verdict/v1",
  "spec_id": "VELDO-0401",
  "commit": "0a98ce4e283eea07118bb4a5f967743fb385a336",
  "reviewer": {
    "model": "claude-opus-4-1-20250805",
    "context": "fresh"
  },
  "verdict": "pass",
  "criteria": [
    {
      "id": "AC1",
      "assessment": "satisfied"
    },
    {
      "id": "AC2",
      "assessment": "satisfied"
    },
    {
      "id": "AC3",
      "assessment": "satisfied"
    }
  ],
  "findings": {
    "blocking": [],
    "non_blocking": []
  },
  "test_assessment": "The expanded gate and configuration tests pass for the amended commit. The added change ticket metadata does not alter runtime timeout or retry behavior."
}
```

32. **AGENT ASKS/REPLIES**

```text
The amended commit now has a green gate, valid proof, and a passing independent review.

The previous approval remains STALE because it names the previous commit.

Elena Garcia must approve:
0a98ce4e283eea07118bb4a5f967743fb385a336
```

33. **YOU ANSWER**

```text
I am Elena Garcia, billing owner. I reapprove VELDO-0401 for commit 0a98ce4e283eea07118bb4a5f967743fb385a336. I reviewed the added SETTLE-882 change-ticket metadata, the unchanged 3 second production timeout, the unchanged 2 second staging timeout, the green expanded gate, and the regenerated proof. Record a new one hour approval.
```

34. **FILE CREATED**

`/workspace/payments/billing/proof/VELDO-0401/approval-apr-0402.json`

```json
{
  "schema": "veldo.approval/v1",
  "id": "apr-0402",
  "decision": "approved",
  "approver": {
    "id": "elena-garcia",
    "role": "billing-owner"
  },
  "scope": {
    "spec_id": "VELDO-0401",
    "commit": "0a98ce4e283eea07118bb4a5f967743fb385a336",
    "proof": "proof/VELDO-0401/manifest.json"
  },
  "reason": "Reviewed the SETTLE-882 metadata, unchanged production and staging timeout values, green expanded gate, and regenerated proof.",
  "recorded_at": "2026-08-07T16:23:00Z",
  "expires_at": "2026-08-07T17:23:00Z"
}
```

35. **YOU CHECK**

```text
Command:
python3 .veldo/validate.py approval proof/VELDO-0401/approval-apr-0402.json

Expected output:
OK: valid veldo.approval/v1 apr-0402
```

36. **AGENT** (automatic): commits the evidence and pushes.

37. **AGENT ASKS/REPLIES**

```text
[feature/veldo-0401 c6ef2a1] VELDO-0401 record final evidence and approval
 8 files changed, 137 insertions(+), 3 deletions(-)
 create mode 100644 proof/VELDO-0401/approval-apr-0401.json
 create mode 100644 proof/VELDO-0401/approval-apr-0402.json
 create mode 100644 proof/VELDO-0401/manifest.json
 create mode 100644 proof/VELDO-0401/verdict.json

Pre-push check: evidence-only commit; inherits proof from the parent.

HEAD c6ef2a18269faf14cf01e86ba6be3e4246ada911 inherits proof from parent 0a98ce4e283eea07118bb4a5f967743fb385a336.

Gate: green
Proof: valid
Verdict: pass
Approval apr-0401: stale
Approval apr-0402: approved and unexpired

To github.com:acme/payments.git
 * [new branch]      HEAD -> feature/veldo-0401
```

38. **YOU SAY:** `merge`

39. **AGENT** (automatic) - merges and shows the policy receipt:

```text
Merge policy evaluated: satisfied.

Spec: VELDO-0401 ready
Protected path: billing/config/production.yaml
Effective risk: high
Gate: green
Proof: valid
Independent verdict: pass
Blocking findings: 0
Required approval: approved by Elena Garcia
Approval commit: 0a98ce4e283eea07118bb4a5f967743fb385a336
Approval expiry: 2026-08-07T17:23:00Z
Rollback: present

✓ Merged pull request acme/payments#503 (VELDO-0401 Increase production billing provider timeout)
```

## Runbook E - An iteration through the planning layer

The situation: the orders area needs a real redesign - reorder, saved carts, and an empty state - not one change but several, with a regression surface they share. This is the planned lane. A single bug never comes here; this runbook is for a product increment.

**Step 1 - You state the increment at the product level.** You type:

```
/veldo:plan create the orders redesign: reorder, saved carts, and the empty state
```

**Step 2 - The agent interviews you about the WHOLE, not a change.** Answer in outcomes and features:

```
Agent: What user outcomes must become true?
You:   Returning customers reorder in two taps; a cart survives a session; a
       customer with no orders knows what the screen is for.
Agent: What is explicitly out?
You:   Payment changes. Wishlists. Not this iteration.
Agent: What must stay green across the whole thing?
You:   Checkout must keep working end to end after every piece.
Agent: What does done mean?
You:   All three shipped, checkout journey green, then a week of watching reorder rate.
```

**Step 3 - The plan file appears.** `plans/PLAN-0007-orders-redesign.md` (abbreviated):

```yaml
---
schema: veldo.plan/v1
id: PLAN-0007
title: Orders redesign - reorder, saved carts, empty state
kind: iteration
status: draft
revision: 1
owner: dmitry
outcomes:
  - {id: O1, becomes_true: Returning customers reorder in two taps, measure: reorder rate}
  - {id: O2, becomes_true: A cart survives a session, measure: cart-restore success}
  - {id: O3, becomes_true: A customer with no orders understands the screen, measure: empty-state click-through}
work:
  - {item: W1, spec: VELDO-0501, title: Reorder API, feature_refs: [F1], depends_on: [], order: 10}
  - {item: W2, spec: VELDO-0502, title: Reorder UI, feature_refs: [F1], depends_on: [VELDO-0501], order: 20}
  - {item: W3, spec: VELDO-0503, title: Saved carts, feature_refs: [F2], depends_on: [], order: 30}
  - {item: W4, spec: VELDO-0504, title: Empty state, feature_refs: [F3], depends_on: [], order: 40}
regression:
  journeys:
    - {id: RJ1, title: Checkout works end to end, activation: {when: start}, profiles: [per_spec, release], suite: e2e/checkout}
release:
  milestone: Orders redesign live
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
open_decisions: []
---
```

The agent says: `Plan drafted as PLAN-0007 (draft). It validates. Say "approve" to make the ordering real, or refine anything first.`

**Step 4 - You approve it.** You type:

```
Approve the plan.
```

The agent sets `status: ready`, records you as `approved_by` with `approved_at`, re-validates, and regenerates the index. The Product Plans section now tracks it.

**Step 5 - You read the frontier and pull in order.** You type:

```
/veldo:plan status PLAN-0007
```

```
PLAN-0007 - Orders redesign - reorder, saved carts, empty state
status ready, revision 1, 0/4 shipped
  W1   VELDO-0501    unstarted (frontier)
  W2   VELDO-0502    waiting: VELDO-0501
  W3   VELDO-0503    unstarted (frontier)
  W4   VELDO-0504    unstarted (frontier)
frontier: VELDO-0501 (W1), VELDO-0503 (W3), VELDO-0504 (W4)
```

Three items are buildable in parallel; W2 waits on W1. You pull one:

```
Pull VELDO-0501.
```

The agent creates its spec with `/veldo:spec`, setting `lane: planned`, `plan: PLAN-0007`, `work: W1`, `plan_revision: 1`, interviews you on that one piece, and you approve and run it exactly as in Runbook A. Repeat for the other frontier items; run parallel work in separate worktrees only up to what you can actually judge.

**Step 6 - The machine refuses broken order, so you never have to police it.** Suppose you try to jump ahead to the Reorder UI before its API has shipped:

```
You:   Pull and run VELDO-0502.
Agent: run-check VELDO-0502: REFUSED
         - dependency VELDO-0501 is ready, not shipped
       Not building out of order. Ship VELDO-0501 first, or change the plan.
```

That refusal is the DAG enforcing itself. Ship W1, and W2 moves onto the frontier on its own.

**Step 7 - You change your mind, honestly.** Saved carts turns out to need the reorder API too:

```
Make W3 depend on W1.
```

The agent revises the plan (not edits it): bumps `revision` to 2, adds a `## Revisions` note, and shows the impact:

```
impact of VELDO-0501 in PLAN-0007:
  VELDO-0502 (shipped)
  VELDO-0503 (ready)
  WARNING: 1 already-shipped dependent(s) may need re-proof: VELDO-0502
```

Any spec pulled against revision 1 is now stale; `run-check` will refuse it until it is re-pulled against revision 2. Intent changed, and nothing ships against a plan that moved underneath it.

**Step 8 - You ask for the release, and the check answers.** When the work is done you type:

```
/veldo:plan release PLAN-0007
```

If anything is unfinished, the check says exactly what:

```
PLAN-0007: NOT releasable
  - work not shipped: VELDO-0504
```

You ship the last piece, ask again, and get:

```
PLAN-0007: releasable (Orders redesign live)
```

The agent sets `status: released` and records the milestone. In continuous mode the pieces already merged as they went green, so release is the marker plus the week of watching reorder rate you named in Step 2.

**What you actually did across the whole iteration:** described three outcomes, approved the plan, pulled frontier items in order (the machine refused the one out-of-order attempt), answered one dependency change, and asked to release. No standup, no board, no status report. The plan reported itself the entire time.

## Part II - Every change type

The loop never changes; what changes per type is the evidence the spec demands and who must judge. This part gives the exact recipe per type: the criteria pattern, the evidence list, the human moments.

### II.1 Infrastructure as code (the chapter that takes you from 0%)

Infrastructure is where teams quietly bypass their own process, because "it's just a config value." Under Veldo it is the opposite: infrastructure is the most protected class in the repository.

**One-time setup for an infra-bearing repository (exact steps):**

1. Put every infrastructure definition in the repository if it is not already there: terraform under `infra/`, compose files, deploy configs, CI definitions. If it cannot be read and diffed, it cannot be governed; this is non-negotiable and is usually the real migration work.
2. Floor the paths in `.veldo/policy.yaml`:

```yaml
protected_paths:
  - {path: "infra/**",            floor: high}
  - {path: "infra/production/**", floor: critical}
  - {path: "docker-compose*.yml", floor: high}
  - {path: ".github/workflows/**", floor: high}
```

3. Add the plan step to the gate. In `scripts/verify.sh`, the EXTRA_CMD slot runs the normalized plan when infra paths changed, and the plan text becomes evidence:

```bash
EXTRA_CMD="./scripts/infra-plan.sh"   # terraform plan -no-color > proof/<spec>/plan.txt when infra/ changed"
```

**The recipe per infra change:**

| Element | Pattern |
|---|---|
| Criteria | The exact intended delta ("autoscaling max 20 to 40"), "the normalized plan contains only the expected change", the observation criterion ("queue depth and error rate observed post-apply") |
| Evidence | plan text as an artifact, staging validation where one exists, a tested rollback command |
| Human moment | approval bound to the exact commit AND the plan digest; expires; any new plan invalidates it |
| Irreversible ops | destructive migrations, deletions, key rotations: prepare-and-execute (setup 7.2): approve the exact plan artifact, execute before expiry, stop on any mismatch |

**What you type** (the whole flow is Runbook D in Part I; the short form):

```
/veldo:spec Raise production worker autoscaling max from 20 to 40. Minimum unchanged.
ready
/veldo:run VELDO-0311
approve          (when shown the plan: 1 update, 0 create, 0 destroy, cost within ceiling)
merge
```

The plan-digest binding is the whole trick: you approved that exact plan, not "the idea of scaling up." If the plan regenerates differently, your approval is stale and the merge blocks.

### II.2 Database changes

Never one change. The agent proposes the expand-and-contract decomposition and refuses to bundle (the refusal is in the method, not your memory):

1. Additive migration, dual-write, nullable. Rollback = stop writing.
2. Backfill (resumable, batched) + switch reads behind a fallback. Data-owner approval. Rollback = read old path.
3. After observation: enforce constraints, remove fallback.

Each is its own spec with its own gate, proof, review, merge. The criteria pattern for any migration: "the migration applies and reverts cleanly on a copy of production data" is evidence, not hope: the gate runs it.

### II.3 Dependencies

One standing spec per class (`specs/VELDO-STANDING-*.md`) defines criteria, risk, and evidence once. Each bump: `Apply the next safe update under VELDO-S001` and the ordinary loop runs; the proof manifest references the standing id. Majors, license changes, auth/payment/infra libraries: excluded by the standing spec's constraints, each needs its own spec.

### II.4 Pure documentation and copy

Proportionate proof at its floor: one criterion (the corrected text, asserted or built), the gate, a fast review pass. Minutes. Never skipped, because "small" is where regressions hide from memory.

### II.5 Configuration and feature flags

Config that changes behavior is code: same loop. The one addition: the spec's rollback field must name the flag or the previous value explicitly, so the receipt contains its own undo.

### II.6 Testing itself: agents test, humans judge pictures

The rule that governs all testing under Veldo: **if a test can be executed by an agent, a human executing it is a defect in the setup.** Agents write the tests, run them, and interpret the failures. Humans see evidence delivered to them; humans never assemble their own validation.

**UI proof is four layers, in this order of importance** (the method's design edge already says it: flows are specifiable; feel is human):

1. **Flows.** The primary proof. Every journey the spec names is DRIVEN end to end by the agent - the happy path, the failure path, the recovery path - with behavior asserted at each step: navigation happened, state transitioned, data persisted, focus went where it should. A UI whose screenshots are perfect and whose flows are unproven is unproven.
2. **States.** Every named state (empty, loading, error, offline, permission-denied) is REACHED by driving, captured, and asserted on content and accessibility, not just photographed.
3. **Interaction detail.** Keyboard order, gestures, animation timing where specified: asserted where assertable, recorded for the human lane where not.
4. **Visual fidelity.** The token lint, the Figma composites, the locked baselines. This is the layer humans judge as pictures, and it is the LAST layer, not the proof.

Plus the fifth thing that is not a layer: **feel**, which stays human, as the design review lane, judging the interaction recordings and composites.

**Web.** The agent drives Playwright end to end across the spec's widths: journeys first, then state captures, traces and videos recorded for the lanes. The gate runs it all; the human sees composites and recordings, not test logs.

**Mobile, treated as first-class because it is historically the weakest AI-tested surface.** The agent drives the emulator end to end:

1. Boots the device profile the spec declares (OS version, form factor); the matrix is spec-declared, not assumed.
2. Installs the build and drives the spec's JOURNEYS itself - taps, text entry, the full flow to its asserted outcome - then re-drives them through the lifecycle events where mobile actually breaks: backgrounding mid-flow, process death mid-sync, rotation, network loss.
3. Captures every state the spec names as a screenshot, and records the whole interaction as video.
4. Compares user-facing screens against the Figma exports and builds the composites.
5. Writes it all to `proof/<spec-id>/visual/` and delivers the composites and the video link to the judging human.

**The visual pipeline (any design-lane change, web or mobile).** Figma frame exported via the API (the exact node, not a screenshot of a screenshot) -> rendered captures from Playwright or the emulator -> side-by-side composite with a pixel-diff strip -> delivered to the human in chat -> the one-line reply becomes the baseline approval or the design verdict. The composite is evidence: it lives next to the manifest and the reviewer checks it too.

**The evidence contract for UI and mobile specs.** `required_evidence` for user-facing work names what must exist, and the proof fails without it:

```yaml
required_evidence: [unit, journeys, ui_states, interaction_recording, figma_composite]
# mobile adds: device_matrix (the spec declares which OS versions and form factors)
# journeys is the load-bearing entry: named flows, driven end to end, behavior asserted
```

**Honesty clause.** An emulator is not a device fleet; where risk demands physical devices (payments flows, camera, biometrics), the spec says so and a human lane covers exactly that residue - the point is that the residue is small, named, and shrinking, never the default.

### II.7 Emergencies

The full transcript is in Part III.7. The short form: a human declares it, `VELDO_EMERGENCY=1` on the push, service restored by the fastest safe means, and the debt (spec + proof + review of what actually shipped) closes within 24 hours or the next ordinary merge blocks.

## Part III - Every situation

What you will actually see, and exactly what to do. Each entry: the signal, the cause, the action.

### III.1 The gate is red

Signal: `GATE: RED (<commit>)` and the failing check named above it.
Action: nothing, usually; the implementer fixes defects and reruns. You only get pulled in if the same spec fails repeatedly, which is a spec problem, not a code problem.

**The inner loop while you are fixing it, and what it is not.** Paying the whole unit suite for a one-line fix is where red-gate debugging time actually goes, so the suite can be run in part: `python3 scripts/selftest.py --suite <name>` runs one named suite plus the prerequisites it was measured to need, and `--upto <name>` runs everything through one suite. Use them to iterate. That is the entire purpose, and it is worth being blunt about the limit: **a partial run is not evidence that anything works.** No proof manifest, no evidence claim and no landing decision may cite one. This is not a matter of discipline, because a partial run cannot write the gate stamp, cannot satisfy the required-evidence check and cannot emit the summary line the gate reads: each of those raises `PARTIAL_RUN_CANNOT_VERIFY`, its exit status is never zero, and it prints a banner saying so. **Which of those is doing the work today, so you know what you are relying on:** the mechanism is the NON-ZERO EXIT STATUS, because the gate decides green from the exit status of its unit slot and a partial run never returns zero. The summary line has one production caller. Refusing the stamp and refusing the evidence record are forward guards with no caller yet, since the stamp is written by the gate script in shell and proof artifacts are written by hand; they are what the first generated one will hit. A green canonical gate remains the only thing that means done. Three practical notes: selecting a name that does not exist is a refusal listing the real ones, never a silent pass over nothing; a flag takes its value as the next WORD, so `--suite=<name>` is refused as an unrecognised flag rather than quietly ignored, which used to run the whole suite while you waited for a subset; and the saving is uneven, because a suite's cost is not evenly spread. Check what a selection actually costs before assuming it is fast.

### III.2 The guard blocked a push

Signal:
```
Veldo guard: blocked. The canonical gate is not green for HEAD (91acb03).
```
Cause: something changed after the last gate run; proof is valid only for the state it ran against.
Action: `/veldo:gate`, let it go green, push again. If you see this often, changes are being pushed mid-thought; finish the loop first.

### III.3 A review failed

Signal: `review: FAIL` with blocking findings listed.
Action: none the first time; the implementer addresses findings and a fresh review runs. The SECOND failure on the same spec stops the machine and pulls you in, and the defect is almost always in the specification: ambiguous intent or untestable criteria. Fix the spec, not the code.

### III.4 A spec is blocked

Signal: status `blocked` in the index, with the blocker recorded in the spec.
Cause: the agent hit a material product decision it refuses to guess.
Action: answer the question in the spec (or in chat and let the agent record it), flip back to `ready`.

### III.5 You need to change a ready spec

Action: just say what changed. The agent revises the spec; the revision invalidates any proof or approval bound to the old version, mechanically. Never edit acceptance criteria to match an implementation; that direction is prohibited.

### III.6 An approval went stale

Signal:
```
Veldo guard: blocked. No proof manifest found for HEAD (...)
```
after an amend, or a re-request for approval you already gave.
Cause: approval binds to the exact commit and proof; anything changed = stale, by design.
Action: look once more (it is a new thing now), approve again. If this annoys you, it is working: you were about to approve something you had not seen.

### III.7 Production is down (the emergency, verbatim)

```
You:    Production checkout is failing after the 14:10 deploy. Emergency. Revert it.
Agent:  Reverting deploy 42da901; smoke test on checkout passing locally.
        Pushing with the emergency lane.
System: Veldo guard: emergency lane used; backfill the specification, proof,
        and review within the policy window.
Agent:  Reverted. Checkout error rate back to baseline. Backfill debt is open,
        due 2026-07-17 17:55 UTC.
```

Within 24 hours (you or the agent, one line): `Backfill the emergency from last night.` The spec describing intent, proof against what actually shipped, and an independent review land as normal artifacts; the debt closes. An unclosed backfill blocks the next ordinary merge.

### III.8 The trunk moved under a proven change

Signal: the run reports re-proving on the merged result before completing the merge.
Action: none; this is automatic. Two changes that each pass alone can fail together; the trunk only ever contains states a gate has seen.

### III.9 A bug will not reproduce

Action: the spec says so explicitly and names the closest observable proxy as the criterion: a log signature stops appearing, a metric returns to baseline. Never a pretend failing test; never a criterion nobody can check.

## Part IV - Every role

### IV.1 The founder, from chat

You never open a terminal. Your whole interface, in five sentences you already know how to say:

| You want | You say (to your assistant) |
|---|---|
| New work | "Add X to <repo>." (the interview follows; answer in plain words) |
| Approve a spec | "Ready." |
| Status | "Where are we on <repo>?" or "/veldo:status" |
| Judgment | You get pinged: an approval with the exact delta, a design baseline to eyeball, a blocked question. Answer in one line. |
| Receipts | Arrive on ship: criteria proven, gate, verdict, rollback. |

Protected-path approvals: for now these are confirmed on the pull request page (identity), one tap deeper; the ping still reaches you in chat with the link.

### IV.2 The engineer, in terminal or IDE

`/veldo:spec` when starting something, `/veldo:run` to execute it, `/veldo:status` when returning from lunch. The six step-skills for debugging. The only rules that bite: no implementation without a ready spec, green is the only done, and the reviewer is never you.

### IV.3 The design owner

You are a reviewer lane, not a meeting. When a change touches look, feel, or flow you get: the mock link, the rendered baselines, the exact commit. You compare, then say one of two sentences to the agent: "Record my design review for VELDO-NNNN: approved." or ": rejected, <what is off>." Your verdict is a file with your name in it, bound to that commit; nothing user-facing merges without it.

### IV.4 The reviewer's obligations (agent or human)

Fresh context, always. Inputs: spec, final diff, proof, instructions; never the implementer's narrative. Rerun what you doubt. Judge against Intent, not just criteria. Two verdicts only matter: blocking findings, or pass; style opinions are non-blocking notes.

## Part V - Running it

### V.1 Bringing the next repository in (the 0-to-100 path)

Per repository, in order, about an hour of human attention:

1. `/plugin install veldo@veldo` if not already; `/veldo:init` in the repo.
2. Answer the three init questions honestly: authoritative commands, unrecoverable paths, whether the design lane applies.
3. Let init run the gate once; fix what is genuinely broken (init will surface real rot: flaky tests, undocumented build steps; this is the migration's actual work).
4. Approve the adoption spec; it merges as the repo's first Veldo change.
5. From then on: all new work through the loop. Do NOT stop to retrofit old work; Veldo governs changes, not history.

Repository order for the migration: most-active first (highest change volume = highest protection value), infrastructure repositories second (the 0% that matters), quiet repositories last or never.

### V.2 Adding or changing a protected path

Policy is code: say "protect <path> at <tier> in <repo>"; the agent edits `.veldo/policy.yaml` through the ordinary loop (a spec, a review); it is itself a protected-class change. Effective immediately for every subsequent change.

### V.3 Creating a standing specification

"Make a standing spec for <recurring class>: criteria are <...>, excluded are <...>." One file in `specs/`, reviewed once, then instances flow without ceremony.

### V.4 The weekly pass (the one ritual)

Fifteen to twenty minutes, in chat or terminal: `/veldo:index`, then walk the list: close what shipped, kill what went stale, re-answer what is blocked, confirm what is ready next. If it takes longer than twenty minutes regularly, specs are too big.

If the repository carries an architecture contract (`.veldo/architecture.yaml`), the weekly pass is also where its living tripwires and entropy get their in-session read - both are ordinary functions, nothing detached, nothing running between passes. Update the small recorded-readings file (`.veldo/readings/*.yaml`) with this week's assumption signals, then run the tripwire pass; a breached assumption is a named finding (and it already surfaces in the gate and in `veldo status`), and it drafts exactly one re-decision unit for you to promote - a wrong foundation caught by assumption breach, not by outage. Then glance at the per-area cost-to-change (the entropy CLI or the metrics dashboard): a trusted threshold crossing drafts one restoration spec you promote through the normal loop, and once a restoration ships the pass reports the cost delta so you can see whether it paid off. Nothing here auto-gates and nothing auto-promotes; the human decides, the same way the human decides everything foundational. A repository with no contract sees none of this (the checks stand down).

### V.5 Upgrading the plugin

`/plugin update veldo@veldo` (or reinstall). Upgrades never rewrite your repository substrate; when a template you already have changes, apply it as an ordinary reviewed change. Announce upgrades to the team; version drift degrades politely.

### V.6 Reading the numbers

Everything is derivable from `.veldo/events.jsonl`: spec-to-ship time (spec.ready to spec.shipped), gate latency (gate events), first-pass rate (gate.failed density), emergency debt (unclosed emergency.push), human minutes (the human_minutes fields). One question to ask monthly: is human-minutes-per-shipped-change trending toward stating-intent-plus-judging and nothing else? That number is the whole promise.

### V.7 The planning layer, day to day

For a product increment (never for a single bug), a Product Plan runs above the spec loop. Runbook E is the full walkthrough; the recurring rhythm is short:

- **Start one:** `/veldo:plan create <the increment>`, answer the product-level interview, `approve` once you have read the draft. Tens of minutes, not a planning phase.
- **Work it:** `/veldo:plan status <plan>` shows the burn-down and the frontier; pull a frontier item, run it, repeat. You choose which frontier item matters next; the machine decides which are allowed (`run-check` refuses unshipped deps and stale context, so you never police order).
- **Change it:** say what changed; the agent revises (bumps the revision, shows impact), never silently edits. Anything pulled against the old revision goes stale until re-pulled.
- **Release it:** `/veldo:plan release <plan>` runs the release check and only then marks it released; continuous mode already merged the pieces, so this is the milestone plus the observation window.

It folds into the one ritual: the weekly pass (V.4) walks open plans the same way it walks specs - confirm each plan's frontier is moving, surface any decision that has blocked an item too long, and kill a plan that reality has overtaken. The plan is the board; do not build a second one on top of it (that failure mode is III-style status theater, in V.4 and the anti-patterns). Everything the plan reports is derived from the spec files, so it is always current without anyone maintaining it.

### V.8 Running the fleet

When a repository has several independent ready specs, run them in parallel with the fleet instead of one at a time. Everything runs in-session; the fleet spawns nothing detached.

**One-time, per account.** Register each account once:

```
veldo account add alpha
```

This is a login into that account's own persisted profile (its own `CLAUDE_CONFIG_DIR`). You log in once; a worker driven under that account reuses the saved login from then on, with no re-login. `veldo account list` shows the registered accounts.

**Run workers.** One worker in the current terminal:

```
veldo work --account alpha
```

Or up to N workers paced by the governor:

```
veldo fleet 4 --account alpha
```

Each worker claims the next ready unit from anywhere in the repository, builds it, and lands it through the serialized lander, then claims the next, until the frontier is drained. Two workers never take the same unit, and a build routes only to a worker whose machine can run it.

**How a worker is started (the coordinator drive).** A worker is a vanilla in-session worker, git-worktree-isolated: the coordinator provisions a fresh git worktree for it (an in-line `git worktree` call that isolates its source tree, never a detached process) and starts it through the SAME in-session parallel mechanism a human session uses to run parallel work, so the worker dies with the session. The multi-account pool stays one account per worker: each worker carries its own account's `CLAUDE_CONFIG_DIR`, and one account is never run as two workers. The whole pool is opt-in and in-session, it spawns nothing detached, and it grows and shrinks only while the coordinating session is alive. On Claude Code the actual worker launch is agent-mediated: the coordinator dispatches the in-session worker itself (a reference the coordinator provides at runtime), because a program cannot start an in-session worker without detaching, which is forbidden. Where no in-session mechanism is available the start fails loud by name rather than fabricate a worker or fall back to a detached process, so a bare `veldo fleet` with no in-session start wired stops at the first spawn instead of going rogue.

**Monitor.** Watch the live run state without touching it:

```
veldo status          # a one-shot read: the runs, their phase, and any blocked question
veldo watch           # the same, refreshing, interruptible
```

`veldo answer`, `veldo steer`, and `veldo abort` speak to a specific run through its inbox when you need to unblock, redirect, or stop it.

**When an account hits its budget (the default: in-session resume).** The governor measures burn from the event stream and paces the pool. When an account spends its window's budget, its workers back off, and the pool resumes IN-SESSION when that account's window rolls off, re-checking the budget before spawning again so it never resumes straight back into the limit. This is the wired default of `veldo fleet`: you do nothing, the wait is a bounded in-session wait, not a detached timer. Add accounts for more parallelism, and the governor sums each account's own budget into the pool, so one spent-out account never stalls the others.

**The one gap: a fully killed session.** The in-session resume carries a LIVING session through a reset. The single case it cannot cover is a session the OS fully KILLED at a hard token cap, because a dead process cannot resume itself. For that, and only if you want it, there is an opt-in external supervisor. It is OFF by default: unless you run the install command below, nothing is scheduled and no artifact exists on your system, and the fleet behaves exactly as the in-session default above.

**The opt-in external supervisor.** It is a standard systemd user timer that you own and can inspect and remove. Turn it on with:

```
veldo supervisor install --on-calendar '2026-07-19 16:30:00 UTC'
```

That generates a user timer plus a oneshot service unit under your own `~/.config/systemd/user`, prints exactly what it created, and enables the timer. Give it the resume time as an `--on-calendar` expression (or `--resume-at <epoch>`, typically the governor's resume time). Inspect it the way you inspect any user unit, and remove it cleanly when you no longer want it:

```
veldo supervisor status              # the timer state (enabled, active)
systemctl --user list-timers        # the same, in systemd's own view
veldo supervisor uninstall           # disable and remove it, cleanly and idempotently
```

The unit's launch command is a documented, fail-loud reference until you wire your own fresh-session launcher (pass it with `--launch-command`); Veldo generates the timer and the command but never spawns the session itself. Install is idempotent, so re-running it is safe.

**The boundary.** A worker is a real in-session worker, never a headless or detached background process, and the in-session resume is a bounded in-session wait, not a background timer. The only persistent mechanism Veldo will ever create is the external supervisor above, and only when you explicitly install it: a visible, inspectable, removable user systemd timer, never a hidden daemon, a system crontab, a lock-refresher, or a headless polling loop. If you ever find a fleet process running outside a session or a scheduler you did not install, that is a defect, not the design. The build, the fresh-context review, the worker-start primitive, and the supervisor's session launch are delegated seams that fail loud rather than fake a result.

## The cheat sheet

| Situation | What you type | What you get back |
|---|---|---|
| Plan a product increment (several features, many specs) | `/veldo:plan create <the increment>` | A product-level interview (outcomes, feature tree, ordering, regression, release), then a draft `plans/PLAN-NNNN-*.md` |
| Approve a plan | `Approve the plan.` | Status `ready`, `approved_by` and `approved_at` recorded, index regenerated with the Product Plans section |
| See the plan burn-down and frontier | `/veldo:plan status PLAN-NNNN` | Each item shipped / waiting on named deps / blocked / frontier, and the ready frontier - derived from spec files |
| Pull the next work item into a spec | `Pull VELDO-NNNN.` | A `lane: planned` spec bound to the plan and work item; then the ordinary spec loop |
| Revise an approved plan | `Make W3 depend on W1.` (or any scope change) | A revision (bumped, noted) plus impact analysis; specs pulled against the old revision go stale |
| Release the increment | `/veldo:plan release PLAN-NNNN` | The release check; on pass, status `released` and the milestone recorded; on fail, exactly what is missing |
| Start a backend feature | `/veldo:spec Rate limit POST /api/exports` | An interview covering outcome, constraints, edge cases, failure, risk, and ownership |
| Approve a drafted specification | `I approve VELDO-0101 as ready.` | Spec status changes to `ready`, validation runs, the index updates, and a `spec.ready` event is appended |
| Run the complete implementation pipeline | `/veldo:run VELDO-0101` | Implementation, tests, canonical gate, proof manifest, independent verdict, and merge-policy receipt |
| Inspect the canonical gate yourself | `./scripts/verify.sh` | Configured checks followed by `GATE: GREEN (<commit>)` or `GATE: RED (<commit>)` |
| Inspect proof (optional) | `python3 -m json.tool proof/VELDO-0101/manifest.json` | Criteria mapped to evidence, exact commit, checks, producer, and rollback |
| Start a Figma-backed UI change | `/veldo:spec Add the Orders empty state. Figma: <link with node-id>` | Figma node, component names, tokens, text, spacing, dimensions, and design-owner questions |
| UI validation | nothing - the agent exports the Figma frame, captures the render, composites them with a diff strip, and sends you the image | Two pictures in chat; you reply in one line |
| Approve a baseline | `Approved.` (or name what is off, e.g. "button 8px from bottom, mock shows 24") | Locked baselines the gate defends forever; composites stored as evidence |
| Record a design-owner verdict | `I am <name>, design owner. I compared <Figma node> with <baseline>. My verdict is approved.` | `proof/<spec-id>/design-verdict.json` bound to the implementation commit |
| Hand a support ticket to Veldo | `Turn ticket 184 into work.` | Reproduction, failing test, one product question, a spec to approve - then everything else automatically |
| Close the support ticket | nothing - the agent posts the closing comment with evidence links when the fix ships | Ticket updated, reporter notified |
| Change a protected path | `/veldo:spec Change billing/config/production.yaml ...` | Risk is floored by policy, required approver is identified, and human approval becomes mandatory |
| Record protected-path approval | `I am <name>, <owner role>. I approve <spec> for commit <hash> because <reason>.` | A commit-bound `veldo.approval/v1` JSON file with recorded and expiry times |
| Change anything after an approval | just ask for the change | The agent amends; the guard blocks its own push; re-proof runs; you re-approve the new exact thing |
| Reprove an amended commit | nothing - /veldo:run does it as part of the flow | Gate, manifest, and verdict regenerated for the new commit |
| Merge | `merge` | The agent merges; policy is checked mechanically (gate, proof, verdict, evidence, unexpired commit-bound approvals) |
| Run several ready specs in parallel | `veldo fleet N --account <name>` (once: `veldo account add <name>`) | N in-session workers claim, build, and land ready work; `veldo status` / `veldo watch` show progress |
| Opt in to external resume after a killed session (off by default) | `veldo supervisor install --on-calendar '<time>'` (remove: `veldo supervisor uninstall`) | An inspectable user systemd timer that launches a fresh fleet at the reset time; nothing runs until you install it |
| Declare the repository's intended shape | author `.veldo/architecture.yaml` (areas, dependencies, patterns, invariants, budgets), then approve it | The shape gate enforces the mechanizable rules (module-size budget, engine invariants) and specs must declare their placement; a repository with no contract is unaffected |
| Check foundation assumptions and area entropy (weekly, in-session) | update `.veldo/readings/*.yaml`, run the tripwire pass, glance at the entropy CLI | A breached assumption named in the gate and `veldo status` plus one re-decision draft; a trusted entropy crossing drafts one restoration spec you promote - nothing auto-gates or auto-promotes |

## Document History

Minor versions add, clarify, or extend; major versions restructure or break compatibility with existing practice.

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-16 | Initial runbook: four keystroke-exact runbooks (feature, UI design lane, bug intake, protected path), every change type with infrastructure first-class, every situation, every role, administration, cheat sheet |
| 1.1 | 2026-07-16 | Human steps re-attributed honestly (a handful of sentences; agents run all commands); Runbook C rewritten chat-first; UI validation now ends with a delivered Figma-vs-render composite stored as evidence; new II.6: agents test, humans judge pictures - first-class AI-driven testing including agent-driven mobile emulators, the visual pipeline, and the UI/mobile evidence contract |
| 1.2 | 2026-07-16 | UI proof restructured as four layers led by FLOWS (journeys driven end to end with behavior asserted), then states, interaction detail, and visual fidelity; Runbook B criteria, gate transcript, and receipt now flow-led; journeys added to the evidence contract |
| 1.3 | 2026-07-16 | Protected-path runbook independence aligned to the optional-escalation ladder (L2 default) |
| 1.4 | 2026-07-16 | The planning layer: Runbook E (an iteration end to end through /veldo:plan - create, approve, pull the frontier, out-of-order refusal, revise with impact, release check), Part V.7 (the planning layer day to day, folded into the weekly pass), and cheat-sheet rows for the plan verbs |
| 1.5 | 2026-07-19 | Running the fleet (W6 of PLAN-0009): Part V.8 covers the one-time `veldo account add` per account (a persisted `CLAUDE_CONFIG_DIR` login, no relogin), `veldo fleet N` / `veldo work --account`, monitoring with `veldo status` / `veldo watch`, the in-session resume when an account hits its budget, and the no-detached-process boundary; a cheat-sheet row for running specs in parallel |
| 1.6 | 2026-07-19 | The fleet supervisor (W7 of PLAN-0009): Part V.8 now states the in-session resume is the wired default of `veldo fleet`, and documents the opt-in, off-by-default external supervisor (`veldo supervisor install` / `status` / `uninstall`) as a visible, inspectable, removable user systemd timer for the one gap the in-session resume cannot cover (a fully killed session), with the no-detached-process boundary restated (no hidden daemon, no system crontab, no lock-refresher, no polling loop; the session launch is a fail-loud reference seam); a cheat-sheet row for the opt-in external resume |
| 1.7 | 2026-07-22 | The architecture organ in the weekly pass (VELDO-1110 of PLAN-0011, plugin 3.7.0): Part V.4 now covers the in-session tripwire and entropy read for a repository that carries an architecture contract - updating the recorded-readings file and running the tripwire pass (a breached assumption named in the gate and `veldo status`, drafting one re-decision unit), and glancing at per-area cost-to-change (a trusted crossing drafts one restoration spec, and the delta is reported once it ships), with nothing auto-gating, nothing auto-promoting, and nothing running between passes; two cheat-sheet rows for declaring the contract and running the weekly foundation-and-entropy check |
