# VELDO-0089 proof

Release 1 stage 4: a project's team is plain versioned data naming one project manager and the required
elaboration, implementation and independent review roles; missing or conflicting staffing opens an owner
request and never invents a worker; the current owner amends the team only through his settled VELDO-0068
answer, bound to the exact proposal and team version, and the roster grants no authority; builder and
reviewer assignments bind the current team revision and the VELDO-0049 engineering-review policy.
Specification status, risk and `.veldo/policy.yaml` are unchanged. This proof is for independent review;
it is not a self-approval, and the canonical gate is run by the lead, not recorded here.

## What was built

- **`.veldo/control_team.py` (new).** The team service: the only writer of `team:<project>` records and
  `team-assignment:` records (it declares both kinds and both prefixes through
  `control_store.declare_owners`). Every operation is a signed command `{'command', 'signature'}` verified
  against the principal's active key, from an active member whose scope covers the project, on an ACTIVE
  VELDO-0076 project, bound to the team record's current version.
  - The schema is closed: `REQUIRED_ROLES` (project manager, elaboration, implementation, independent
    review), each with exactly `ROLE_FIELDS` (workers, responsibilities, expertise, proposal permissions,
    engines, budget, independence). Any other field, including a tool or MCP server list, is refused by
    name (`invalid_input:field:<role>/<field>`). There is no tool list and no second capability filter: a
    role's tools and MCP servers come only from VELDO-0127's capability configuration.
  - `propose` judges the project's requirements (`staffing_problems`): every required role staffed, one
    project manager, every worker an enrolled active member in the project's scope, the role's required
    responsibility, engines among the registered subscription adapters (VELDO-0036
    `control_reservation_runtime.ADAPTERS`), budgets finite and inside the project's coordination budget,
    independent review declared and kept separate from implementation by principal and independence
    group. Any problem writes no team and opens a VELDO-0064 inbox request to the project's owner naming
    every problem (subject kind `team_staffing`), refused `incomplete_roster:<first problem>`. A complete
    team becomes the pending proposal with its revision, base revision and content digest.
  - `amend` applies the owner's settled answer (decision_disposition touchpoint): the effect's target must
    be exactly `amendment_target` of the pending proposal, the request must have shown exactly
    `amendment_brief`, be addressed to the project's recorded owner, who is current, and he must be the
    settlement's only principal. Accepted revisions are appended to `revisions` and never rewritten.
  - A proposal permission is a kind of proposal (`PROPOSAL_KINDS`); naming an R37 role or a settlement
    touchpoint refuses `roster_not_authority:<role>/<name>`. Nothing writes a membership, role, delegation
    or key.
  - `assign` (the team's project manager or the owner) binds one builder and the reviewers of a unit of
    the project to the current team revision and the policy record `review-policy:<repository>`. A missing
    policy or a risk without a count refuses `missing_authority:review_policy` (no default). Fewer distinct
    reviewers than the count refuses `insufficient_reviews:<n>/<need>`; the builder, his independence
    group or a repeated reviewer refuses `reviewer_not_independent:<who>`; each position must name the
    exact subject (unit, revision, scope digest), else `wrong_subject:<position>`.
- **`.veldo/init_scaffold.py`.** Installs `control_team.py` (not validator substrate). Engine copies are
  byte-identical.

`authorization.py`, `request.py` and `decision_review.py` are unchanged: nothing in this concern needed
them, and the deferred VELDO-0070 decision review is not invoked.

## Rows, falsifiers and red records

Suite `scripts/suites/73_veldo_0089_team.py` (about 2 s): the real SQLite store with OpenSSH command,
envelope, journal and API answer signatures, VELDO-0025 enrollment by the steward's signed commands, the
VELDO-0076 project activated by its owner, the VELDO-0064 inbox, the VELDO-0065 presenter over a loopback
Bot API, the VELDO-0068 settlement service answered through the authenticated API edge, the VELDO-0049
review policy record built by `dispatch.review_policy_record` from the repository's `.veldo/policy.yaml`,
and a reader in another process. It also passes in the stage environment (`env -i`, empty HOME,
`GIT_CONFIG_GLOBAL=/dev/null`).

`red-at-d0cf6a5.json`: the suite against the pre-change tree (`git archive d0cf6a5`): all 18 criterion
rows red by assertion (the tree has no team service, so every team command is answered
`no_team_service`), and every region ran to its end.

`python3 -B proof/VELDO-0089/drive.py` regenerates `mutations.json` and the diffs: 23 mutants, each reds
its named row by assertion, the baseline and a no-op copy of each mutated module green. Registry:
`scripts/check_teeth_mutations.py --finding 89`.

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `install/assets` | all | `team-not-scaffolded` |
| `team/incomplete-roster` | AC1 | `review-role-not-required`, `no-owner-request` |
| `team/schema-closed` | AC1 | `tool-field-accepted` |
| `team/conflicting-staffing` | AC1 | `two-managers-accepted`, `separation-unchecked`, `invented-worker-accepted` |
| `team/project-requirements` | AC1 | `budget-over-project`, `engine-unregistered` |
| `team/complete-proposal` | AC1 | none (the accepted case the refusals are compared with) |
| `team/roster-not-authority` | AC2 | `roster-grants-admission`, `authority-permission-accepted` |
| `team/owner-amendment` | AC2 | none (the accepted case, and the stored revision history) |
| `team/stale-amendment` | AC2 | `amendment-version-unbound`, `amendment-target-unchecked` |
| `team/altered-amendment` | AC2 | `amendment-target-unchecked`, `amendment-brief-unchecked`, `amendment-signature-unverified` |
| `team/self-promotion` | AC2 | `any-settler-amends`, `scope-unchecked` |
| `team/policy-required` | AC3 | `policy-defaults-to-no-reviews` |
| `team/valid-assignment` | AC3 | none (the valid independent assignment) |
| `team/review-count` | AC3 | `review-count-unchecked` |
| `team/independence` | AC3 | `reviewer-independence-unchecked` |
| `team/exact-subject` | AC3 | `subject-unbound` |
| `team/stale-team` | AC3 | `team-revision-unbound`, `non-manager-assigns` |
| `team/observability` | all | none |

Each declared falsifier is the first mutation of its row: AC1 `review-role-not-required` (a team missing
independent review is accepted), AC2 `roster-grants-admission` (the configured project manager is granted
`admission_authority` when an amendment applies), AC3 `policy-defaults-to-no-reviews` (a missing policy
means no reviews). Several mutants also red later rows of the same region (an accepted bad proposal leaves
a team record the later rows find); `mutations.json` lists every row each one turned red, with the suite's
own failure detail.

## Stated limits

Concurrent amendment races, mid-cycle reassignment and recovery are Release 2; additional owners and
delegation are Release 3. The manager's own answer is refused by the VELDO-0068 settlement itself (a
service cannot settle a decision); this service refuses the resulting unsettled request as
`missing_evidence:settlement`, and that path has no mutation of its own here.
