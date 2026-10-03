# VELDO-0151: specialist roles and capability configurations

This implementation extends the existing signed team service. Every role retains
VELDO-0089's fields and adds `kind` and `capability_configuration`. The four required
names have kind `required`; all other valid names have kind `specialist`. The
capability reference is an explicit `{role, revision}` selector resolved by the
VELDO-0127 reader in this store's domain and repository. No tools or MCP definitions
are copied into the team schema.

Proposal, owner amendment and assignment check accepted capability revisions.
Missing references, unresolved revisions and incorrect kinds open an owner staffing
request and accept no team revision. The owner amendment brief shows every role,
its kind and its exact reference. Accepted revisions remain in the team history.
The roster does not write authority or invent workers.

An assignment command's `role` names the staffed role; existing callers default to
`implementation`. The explicitly selected builder must belong to that role. A
missing role opens one pending staffing request to the current project owner and
writes no assignment. Assignments retain the team revision, digest and version,
selected role, capability reference, independent-review capability reference,
unit subject and applicable engineering-review policy. Configurations do not float
to a newer capability head. Review count, independence and subject checks still run.
Specialist selection and worker dispatch remain outside this specification.

## Behavior rows

Suite `91_veldo_0151_specialists` reports exactly 25 behavior rows.

| Criterion | Rows | What they observe |
| --- | --- | --- |
| AC1 | `roles/required-only`, `roles/specialists` | Signed owner acceptance of four required roles and an amended roster with designer, ios_builder and builder_jira; exact fields, history, unchanged authority and specialist count. |
| AC1 | `roles/missing-reference/*`, `roles/unresolved-reference/*`, `roles/unversioned-reference` | Required and specialist roles need an explicit accepted revision; one pending owner request, no new revision or worker. |
| AC1 | `roles/kind/*` | Unknown, absent-value and reversed required/specialist kinds refuse with an owner request. |
| AC1 | `roles/required-still-required/*` | Removing each of the four required roles still opens a staffing request, including when independence declarations name the missing role. |
| AC1 | `roles/brief-and-authority` | The owner sees specialist kinds and references; admission permissions and a second tool filter are refused. |
| AC1 | `roles/specialist-outside-project` | A designer naming outsider, enrolled only in proj-b, refuses in proj-a with one owner request naming the problem; no team revision, assignment or authority change. |
| AC2 | `assignment/policy` | A specialist assignment succeeds with the real review policy; absent policy, insufficient count, shared builder/reviewer and wrong subject refuse. |
| AC2 | `assignment/bindings` | Assignment binds the selected role, worker, exact capability revision, current team and policy; a capability-head update does not change the old team reference; stale team revisions refuse; a separate reader sees stored bindings. |
| AC2 | `assignment/reviewer-capability-binding` | The returned specialist assignment and its exact stored record carry the independent-review capability reference, distinct from the builder's reference. |
| AC2 | `assignment/unlisted-worker`, `assignment/staffing-request` | A worker outside the selected specialist role refuses; an absent specialist creates one owner request and no assignment. |
| AC1, AC2 | `roles/observability` | Accepted/refused revision counts, staffing requests by reason and the capability revision's pinned store version. |

The suite uses generated OpenSSH keys, signed membership and configuration writers,
real SQLite stores, loopback owner presentation and the real settlement path. Its
execution unit comes from the intake, objective and backlog writers. The existing
backlog writer has no risk input, so the fixture adds the team's policy risk to
that production-created unit while retaining its provenance. This does not qualify
an end-to-end dispatch or introduce a risk writer. No fake model engine is used.

## Red record and mutations

`drive.py` runs the current suite against an unchanged archive of the requested
commit. `red-at-f1e1abb9.json` records the original 23 behavior rows failing by assertion on
f1e1abb9, with no raised-region substitutes. The production module digest is retained.

Finding 151 registers 17 unique mutations. `mutations.json` names each exact diff,
source digest and target rows, including both declared criterion falsifiers:
accept a missing capability reference and assign a missing specialist by falling
back to an implementation worker. The original 15 mutations remain pending the
reviewer. The two review follow-up mutations were hand-applied separately after
committing the rows and registrations at `54e88be6`; only suite 91 was run.
`review-followup.json` retains the command, source and mutant digests, log excerpts
and exit codes. Both honest runs (before and after mutation) report 25 behavior
rows passed and zero failed assertions. Each mutant reports exactly one failed
assertion in its named row, with no crash, timeout or raised-region substitute:

- `v151-specialist-roster-unchecked` restricts staffing validation to REQUIRED_ROLES.
  `roles/specialist-outside-project` fails refusal, owner request and unchanged-team checks.
- `v151-reviewer-capability-binding-dropped` removes the reviewer configuration field.
  `assignment/reviewer-capability-binding` fails both returned and stored binding checks.

Production was restored after each run and remains byte-identical to the engine copy.
The mutation runner and gate were not run; these are scoped observations only.
The existing finding-89 required-role anchor follows the extended role iteration.

## Verification scope

`checks.json` records the actual scoped commands and results, including the requested
clean environment. Scoped selftest returns exit 2 by design even with zero failed
assertions; the record retains that exit code. These are partial selftest observations, not a gate stamp,
landing authorization, independent review or completed proof manifest. The full
selftest, gate and mutation executables were not run under the token rules.

The footprint adds the four existing team-consumer suites so their fixtures create
accepted capability revisions through the real writer. VELDO-0089's superseded
closed-role assertion now checks invalid names and still rejects tool fields.
Its specification criteria and all specification statuses remain unchanged.
Production changes stay in `control_team.py`, whose engine and installed copies
are byte-identical. The existing scaffold already installs both the team service
and capability service. The production reader census found the objective service
reading the accepted PM workers and the API model registry exposing the team record;
both consume the added fields without a production change.

The supplied `scratchpadanchor_check.py` path does not exist. The supplied
`scratchpad/anchor_check.py` checker is used and its result is retained instead.
