# VELDO-0253 build notes

The approved specification and `amend-0241.md` govern this change. No acceptance
criterion is waived. This is a work record, not an approval or a passing proof.

## Code boundaries examined before implementation

- `engine/.veldo/installation.py:110`: resolution and the single installation reader;
  settings at 246, overrides at 314, patterns at 326 and decisions at 359.
- `engine/.veldo/control_workflow.py:777`: whole-definition validation, including
  approval reachability at 673; layout validation at 841; store writer at 914;
  verified revision reads at 955 and canvas save at 1008.
- `engine/.veldo/control_workflow_unit.py:147`: binding resolution and immutable
  pins at 189. `control_service.py:3294` is the production station caller.
- `engine/.veldo/control_project.py:402`: signed project commands and binding
  updates at 776. Configuration bindings must not bypass commit approval.
- `engine/.veldo/control_service.py:4429`: startup and the descriptor wait loop;
  installation status at 2279 and installed asset closure at 722.
- `engine/.veldo/control_service_api.py:182` constructs Workflows;
  `control_api_authority.py:671` saves for the authenticated API principal;
  `control_client_api.py:132` routes workflow reads to the authority.
- `engine/.veldo/control_factory_setup.py:485`: setup, its store lock and owner
  bootstrap; re-run at 1316, command-line installation resolution at 1843.
  Setup memory, engines, records, trust, dispatch, API and upgrade helpers own
  their existing configuration and installation steps.
- `engine/.veldo/init_scaffold.py:185`: installation reader distribution;
  `engine/ui/src/api/workflows.ts` and the workflow document helpers carry
  definition/layout documents and numeric base versions.
- `engine/.veldo/control_store.py:585`: registered transactions require declared
  expected versions for every write and verify each writer's owning module.
- `engine/.veldo/control_request_settlement.py:416`: signed immutable terms;
  settlement records at 659 bind target, proposal, owner, presentation and answer.
- `engine/.veldo/control_credential_keystore.py:16`: current keystore boundary
  offers value lookup, but no metadata-only existence check.

## Required proof

AC1: an invalid connector and a valid new project refuse together; neither becomes
live. AC2: adding an allowed tool waits for the owner's exact commit decision.
AC3: a canvas save produces a compare-and-swap commit before its recorded head.
AC4: pinned bytes remain readable after the source commit is unreachable.

Each requires a registered mutation that fails its named row for that defect.
Suite runs use a committed snapshot on the named compute node. Host-specific
checks use the external host-heavy wrapper. The lead runs the canonical gate.
