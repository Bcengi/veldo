# VELDO-0253 amendment to VELDO-0241: the workflow revision store

VELDO-0241 is not edited by this note. When VELDO-0253 is approved and built, these changes apply to
the revision store VELDO-0241 builds on (VELDO-0132's control_workflow and VELDO-0241's
control_workflow_unit and control_project). Everything not named here stays as VELDO-0241 says.

## What changes

1. **The authoritative definition moves to the installation repository.** A workflow's definition and
   layout are two files under the workflow path the installation schema declares. The store no longer
   holds the editable head; it holds the record of what was accepted and what a run used.

2. **The save becomes a commit.** Workflows.save() stops committing save_workflow_revision. It builds a
   commit on the installation branch with the expected parent and publishes it by a compare and swap of
   the branch reference (stale_version when the parent is no longer the branch head), after the same
   whole-tree validation the loader runs. control_workflow.definition_problems and approval_problems are
   unchanged and run inside that validation, so VELDO-0241 AC2 holds for every commit, from the canvas
   or from anywhere else.

3. **The loader is the only writer of revisions.** The store command save_workflow_revision is replaced by
   record_workflow_revision, issued only by the installation loader when it accepts a commit whose tree
   changes a workflow's canonical definition. It writes:
   - a content entity workflow-definition:<definition_digest>, written once, holding the canonical
     definition bytes (the same digest VELDO-0132 computes, so existing pins resolve unchanged);
   - the revision entity workflow-revision:[domain, repository, workflow, version] as today, with the
     next version number, the definition digest, the layout digest, and a new source field {commit, path,
     blob} naming where it came from;
   - the head, which now moves only when a commit is accepted.
   A commit that changes only the layout writes a new layout record and no new version.

4. **The pin reads the content copy.** control_workflow_unit.pinned() resolves the unit's recorded
   {id, version, digest} through the revision entity to the workflow-definition content entity by digest.
   It never reads the repository, the branch or the head, so a changed, deleted or unreachable file does
   not change what a running unit or a finished run's canvas sees.

5. **Bindings move to the project file.** The binding from kind of work to workflow is declared in the
   project's file in the installation repository (workflow id, optionally a version). The loader resolves
   it to {workflow, version, digest} per accepted commit and records the resolution. A binding change is a
   widening change under VELDO-0253 AC2, so it is live only after the owner's signed decision on that
   commit, which replaces VELDO-0241's bind_workflow signed command. bind_workflow is refused
   (installation_managed) when an installation repository is configured.

6. **The shipped default stays product data.** The `code` definition stays in the product as version 0
   (SHIPPED) and is what a project with no binding runs. An installation that commits its own
   workflows/code.json overrides it for that installation from the commit that is accepted; the shipped
   bytes are never written into the installation repository by Veldo.

7. **Migration.** A setup re-run over a factory that already holds store revisions writes them, once, into
   the installation repository as one import commit (one file pair per workflow at its head revision) and
   records that commit as accepted without a new version, because every digest is already in the store.
   Earlier revisions stay in the store as content copies and remain readable by digest.

## What does not change

The definition schema (veldo.workflow/v1), the station step kinds, the approval rule and its refusal
names, the pin's fields and the rule that a unit runs only its pinned revision, the canvas document's
split of definition and layout, and the VELDO-0241 suite's default-equivalence and pinned-revision rows.
The save-refusal rows keep their names; their fixtures now drive a commit instead of a store write.
