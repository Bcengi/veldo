# VELDO-0164 review fixes and verification record

Veldo delivers specifications, implementation and evidence together. This branch fixes
API reads scoped to the reader's current projects under the ready VELDO-0164 spec.
Implementation commit: ebaa4755377199328ee560dca3e4833b38f5ef0b.
This is builder evidence. No approval, gate stamp, push or merge is claimed.

The host review identified real regressions in suites 71 and 94. The earlier builder
record described local environment blockers, which did not establish that those suites
were green on a host. Those regression defects have now been corrected; host validation
is still required because this environment stops the affected service fixtures.

## Review items, proving rows and falsifiers

1. Suite 71 seeds its default team through TeamRoutes.save_default, the exclusive writer.
   Its named-scope socket owner sends a message explicitly routed to project-a, so the
   committed objective is visible to her. Existing rows: reads/authoritative and
   service/socket-path. Falsifiers: v164-api-default-team-unseeded and
   v164-socket-message-unrouted restore the two fixture defects.
   Team GET uses inspect, the authority interface shared by the 0162 fixture and production.
   inspect now reads all requested entities and the watermark in one transaction. The
   route requests team and current membership together and filters the project team to
   that membership's scope. Missing and withheld teams both return None. No change to
   proof/VELDO-0162/fixture.py or to the interface was needed. Row: reads/team-route in
   suite 104, exercised through an authority exposing only inspect. Falsifiers:
   v164-team-requires-model-read and v164-team-unfiltered. Suite 94's team/roundtrip,
   default/history and default/named-revision retain their real production proxy checks.

2. A proposal with proposal=inbox is projectless regardless of its state or holding area.
   The trusted-store fixture now mirrors control_intake and control_intake_routes:
   project=factory in AWAITING_ROUTE, AWAITING_PROJECT, NEW_PROJECT and ROUTED,
   with linked questions and their real candidates. Neither an A reader nor a factory
   reader receives those proposals, questions or journal changes. Row:
   reads/unrouted-intake. Falsifier: v164-unrouted-factory-visible restores the old
   state-based rule. This row was observed failing against the old implementation.

3. Decision settlements resolve their request through settlement.request_id, matching
   control_request_settlement. The fixture has no top-level request_id on that kind.
   Rows: reads/decision-settlement, reads/member-A and events/registration.
   Falsifier: v164-decision-request-at-top-level restores the incorrect field path.
   The decision row was observed failing before the fix.

4. A visible intake proposal's structured project metadata is projected before redaction:
   context.projects, candidates, project_versions, decision metadata and project hints
   retain only covered projects. Ticket prefixes stay with their visible project. A shared
   ticket prefix is retained as shared only if at least two visible projects share it.
   The fixture seeds the writer's repeated context and decision metadata and real prefix
   shapes. An A reader sees A and its prefixes; a named A+B reader retains both projects
   and their shared prefix. Universal answers still compare exactly with legacy.py.
   Row: reads/proposal-context. Falsifier: v164-proposal-context-unfiltered.
   This row was observed failing before the fix.

5. Both own-revocation checks guard the event list before indexing it. The membership
   check asserts its length first, so withholding the event produces a false assertion
   rather than an IndexError. Row: events/own-revocations. Falsifier:
   v164-own-revocations-hidden. Mutant execution remains pending.

6. The suite is 104_veldo_0164_scoped_reads throughout active registrations: suite file,
   manifest.json, requires.json, finding 164 registrations and proof manifest. This
   leaves 103 to VELDO-0142. Registration anchors were checked for all 15 falsifiers.
   Historical suite-initial.log and suite-second.log retain their original output and
   original suite number; they are archived development runs, not current checks.

## Test method and results

Suite 104 has 19 behavior rows. It uses real SQLite state, signed journal commits,
current membership, stored workflow revisions and the real publication readers.
legacy.py preserves the base reader bodies, comparing full universal answers and the
unchanged edge feed. Trusted-store seeds judge the read policy rather than writer
admission. Before the production fixes, review-before.log reports five failed rows:
reads/member-A, reads/unrouted-intake, reads/decision-settlement,
reads/proposal-context and events/registration. All 19 rows now pass.

Each requested suite was attempted individually through the suite selector:

* 104_veldo_0164_scoped_reads: 19 passed, zero failed. Output: suite.log.
* 65_veldo_0132_workflow: 16 passed, zero failed. Output: regression-0132.log.
* 68_veldo_0126_intake: 18 passed, zero failed. Output: regression-0126.log.
* 71_veldo_0130_api: reads/authoritative and reads/implemented-writers pass.
  Completed API rows now report before service setup, preserving their original
  assertions and order. events/retry-after-failure fails on PermissionError,
  followed by a service installation abort with unavailable_service:profile:user_manager.
  service/socket-path cannot run here. Output: regression-0130.log.
* 82_veldo_0141_execution_record: stops creating a fixture under /run/user/1000
  with PermissionError. Output: regression-0141.log.
* 82_veldo_0144_mcp_catalog: 29 passed, zero failed. Output: regression-0144.log.
* 85_veldo_0158_credential_delivery: stops creating a fixture under /run/user/1000
  with PermissionError. Output: regression-0158.log.
* 85_veldo_0171_setup_api: 3 passed, 15 failed after setup reports
  unavailable_service:profile:user_manager. Output: regression-0171.log.
* 93_veldo_0152_intake_routes: 11 passed, 11 failed; routing cycles report
  runtime_unavailable. Output: regression-0152.log.
* 94_veldo_0162_configuration_routes: 1 passed, 25 failed after fixture setup
  reports unavailable_service:profile:user_manager. Output: regression-0162.log.

Passing selected runs exit 2 by the repository's partial-run contract. These results
cannot stand in for the unit gate or establish that blocked suites are green on a host.
All suites ran in the foreground. No environment checks were weakened.

The user token rules prohibit the mutation runner, while a later sentence requests
finding 164. Clarification was requested; no exception was received. The mutation
runner and gate were therefore not executed. anchors.py checks declarative registry
anchors and generates exact diffs only. It reports 15 registrations and zero anchor
errors, but proves no mutant rejection. Existing finding 130 and 162 anchors affecting
these modules still resolve. The three spec falsifiers remain registered:
v164-model-unfiltered, v164-events-unfiltered and v164-universal-projectless-hidden.
Host runs of the blocked suites, all falsifiers and the merged-tree gate remain pending.
