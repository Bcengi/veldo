# VELDO-0302 proof

The creator seam declares before the first filesystem write and confirms after successful creation.
It stores item identities beside the existing creator records. Private repositories carry one of
worker_clone, batch_clone or candidate_workspace. The ledger accepts exactly the four forms of design
4.1: agent, worker_clone, batch_clone and candidate_workspace. Their main repository is the ledger's
existing owner-scope declaration, checked against the creator's source before creation. A source that
is a linked worktree is read through git's common directory, so it gives its main repository; a
source outside the main repository, or a folder beneath it that is no work tree, is refused. The
sandbox's ordinary agent repository states no form, which the design reads as agent; its worktree and
branch are children, with the exact start commit. The sandbox writes no item map file.
Artifacts, receipts, token usage held in artifacts, and gate observation folders are evidence.

The two worktree creators take the service's space_provisioned callback and call it before confirming
the new worktree. The real service callback is exercised with a supplied ledger. Owner Keep is
written with an enrolled owner's identity and survives both creators without another item write.
Receipt declaration precedes worker spawn. An artifact refusal is named in the report while usage
settlement continues. Failed creation marks an absent filesystem item gone; a partial item remains
recorded with its files. No cleanup primitive was added. Existing clone failure cleanup still goes
through the item-naming signal, keep step and removers.

Suite 153 has 42 ticket rows, plus the runner's 26 shared checks. Normal creation and refused-ledger
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

The final local falsifier pass applies each of the twelve registered cases once to a disposable copy.
Every designated target row turns red. The baseline has 42 green rows. This is the small local runner
in run_falsifiers.py, not the gate's mutation stages. Development harness errors were corrected before
this pass: a missing item needed a false assertion instead of a dereference, and the empty-template
clone fixture needed its git info directory before writing an ignore rule. No exception is counted
as successful mutation detection.

Fix round after the review (verdict FIX), at commit 259f54f7:

- Finding 1: the row ac2/three-items is checked before any item is read through, and the failure
  path records it too, so it fails and never disappears. The gate's stage for this ticket,
  python3 scripts/check_teeth_mutations.py --finding 302, now passes: registered 12, rejected 12.
  That one stage was run here; no other mutation stage was.
- Finding 2: the form agent is accepted. Row ledger/forms declares it; case
  space302-agent-form-refused removes it and turns that row red.
- Finding 3: row safety/main-repository-worktree runs the real batch creator from a linked worktree
  of the main repository and reads the clone's item, and declares once more through the seam. Row
  safety/main-repository gains three refusals: a linked worktree of another repository, another
  repository, and a folder beneath the main repository. Cases space302-worktree-source-not-resolved
  and space302-any-source-accepted turn those rows red.
- Note N1: the write of veldo-space.json is removed from the protected sandbox pair. The pair's change
  against the base is now the signature, the load of the creator module and the three nested
  declarations. The creator module is still loaded on every prepare, also with no installation;
  that part of the note was not changed.
- Notes N2 and N3 are unchanged: the batch observation folder is declared as evidence, and service
  startup is not wired.

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
