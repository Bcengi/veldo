# VELDO-0302 proof

The creator seam declares before the first filesystem write and confirms after successful creation.
It stores item identities beside the existing creator records. Private repositories carry one of
worker_clone, batch_clone or candidate_workspace. Their main repository is the ledger's existing
owner-scope declaration, checked against the creator's source before creation. The sandbox's ordinary
agent repository has no form; its worktree and branch are children, with the exact start commit.
Artifacts, receipts, token usage held in artifacts, and gate observation folders are evidence.

The two worktree creators take the service's space_provisioned callback and call it before confirming
the new worktree. The real service callback is exercised with a supplied ledger. Owner Keep is
written with an enrolled owner's identity and survives both creators without another item write.
Receipt declaration precedes worker spawn. An artifact refusal is named in the report while usage
settlement continues. Failed creation marks an absent filesystem item gone; a partial item remains
recorded with its files. No cleanup primitive was added. Existing clone failure cleanup still goes
through the item-naming signal, keep step and removers.

Suite 153 has 41 ticket rows, plus the runner's 26 shared checks. Normal creation and refused-ledger
rows cover the clone, fleet, sandbox, run directory, batch clone, batch observation, both candidate
paths, receipts and artifacts. Seven crash rows use SIGKILL after the first mkdir or git creation;
the parent reads the committed declared item. Other rows cover repository forms, partial failure,
links and parent segments, owner Keep, receipt refusal before spawn, flat installation imports,
main-repository mismatch and the existing refusal to enter act mode. A failed clone plants untracked
and ignored work and verifies both remain recorded and byte-identical.

The VELDO-0303 removal fixture formerly declared the items itself before calling a creator. Its
manual fleet setup now uses an unwired creator, and its failed-clone setup reads the creator's own
items. Every original removal assertion remains, including keep-before-remove and planted-work rows.
Two existing mutation anchors changed indentation only; their defects and target rows are unchanged.

The final local falsifier pass applies each of the nine registered cases once to a disposable copy.
Every designated target row turns red. The baseline has 41 green rows. This is the small local runner
in run_falsifiers.py, not the gate's mutation stages. Development harness errors were corrected before
this pass: a missing item needed a false assertion instead of a dereference, and the empty-template
clone fixture needed its git info directory before writing an ignore rule. No exception is counted
as successful mutation detection.

Limits and stand-ins:

- Service startup is not wired here. All creator integration uses an explicitly supplied ledger,
  owner and, for ticket worktrees, callback. Flat-layout importability is proved; installed startup
  integration is not claimed. VELDO-0315 remains unbuilt.
- Suite 153 uses real SQLite journal transitions, git and filesystem operations. Journal signing is
  deterministic fixture signing. Owner enrollment uses a real SSH signature. The existing principal
  suite separately exercises the ledger's signature checks.
- Accepted clone inputs, worker results, identity acceptance and the gate executor are stand-ins.
  No worker, gate, Docker engine, real-data volume or protected data path is exercised by this ticket.
- All new provisioning-event rows stay in report mode. Existing removal and keeper suites exercise
  actual removers in their own isolated fixtures. No production act prerequisite was changed.
- Repository form validation is delivered here by the lead's decision. No VELDO-0347 lifecycle or
  disposal behavior is implemented. That ticket builds on the field.
- Suite 86_veldo_0127 and its captures were left alone. The full verify command and heavy or gate
  mutation stages were not run. The lead runs ./scripts/verify.sh through the gate lock.
