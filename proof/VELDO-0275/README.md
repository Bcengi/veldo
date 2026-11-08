# VELDO-0275 proof: build stopped on a footprint blocker

Status: not implemented. No AC is built, no falsifier is written, no suite was run, and there is
no pending_runs.sh because there is nothing to run. The build stopped before changing code, as the
brief requires when something outside the footprint must change.

## Blockers (checked on this branch, base main 918e7c0e plus spec 871cacf9)

1. AC1 replaces codex-qualification.json and claude-qualification.json with AC2's small summaries.
   These records are read by modules outside the footprint (each also has its engine/.veldo canon copy):
   - .veldo/init_scaffold.py lines 496 to 501 install both records into adopting repositories.
   - .veldo/control_factory_setup_dispatch.py line 155 reads the Codex model catalog from the record.
   - .veldo/control_agent_config.py line 97 reads model_catalog through load_qualification().
   - .veldo/control_agent_config_handoff.py lines 234 to 431 read accepted_plugins, engine_plugins,
     engine_skills, feature_listing and the model catalog from the record.
   - scripts/fixtures/policy_agreement.py and scripts/fixtures/reader_agreement.py,
     scripts/mutation_case_inputs.json reference the records or the qualification code.
   Removing or reshaping the records without changing these breaks role binding, agent configuration
   and scaffold installation.
2. AC2 reports approvals "in the owner's daily summary" and sends the owner a one-line notice on
   failure, and runs "when the installer or the service loop finds a version". No daily summary
   exists on main, and the service loop and channel modules are outside the footprint.
3. AC4 withholds variables matching "the credential name patterns of VELDO-0254 (on its branch, not
   yet on main)". Those patterns are not on main or on this branch; implementing AC4 needs either
   VELDO-0254 merged first or the patterns added here, which duplicates that ticket.

## What would unblock

Either widen the footprint to the files in blocker 1 (and name where the owner notice and daily
summary of blocker 2 live), and land VELDO-0254 first (blocker 3), or split the ticket so a first
increment carries only what fits: AC3 (the launch-time stream probe) and the digest pin of AC1
without deleting the records.

## Inherited reds

None observed; no suite was run.
