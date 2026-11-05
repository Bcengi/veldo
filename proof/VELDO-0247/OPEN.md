# VELDO-0247 open items

1. Built in round 2 (lead's ruling 1): the Line runs check and join nodes and fan-outs in a unit's process
   (control_workflow_unit.walk, control_service.Line.step_check, step_join, fork; suite 129). Limits that remain,
   each a named refusal or a recorded assumption for the lead:
   - unsupported_configuration:parallel_station:<node>, at binding (control_workflow_unit.parallel_problems): two
     stations of one kind in different branches of one fan-out (two reviews in parallel), because control_launch
     (outside this footprint) holds one active dispatch per unit and station, so they could not run at the same
     time; and a gate in a branch, because the Line's gate runs inside the land and the branch could never arrive.
     The spec's error taxonomy names neither.
   - A unit's check reads only subject fields (the unit's record): a {node, result} source must name an assignment
     node (AC1's save rule), which is not a station, so a unit's check cannot read a station's result.
   - The Line evaluates a check on every pass; a branch a station already recorded at that check that differs from
     the evaluation now is refused unsupported_workflow:branch_mismatch (the cycle's name), so a unit whose subject
     changed under a taken branch stops and is named in the pass rather than re-routed.
2. The canvas run view that reads the recorded decisions and branch positions is VELDO-0246's.
3. The rollback's refusal of a later installation commit holding check or join is VELDO-0253 AC1's.
4. Metrics are in-process counters (Cycles.metrics; saves refused by problem in Workflows.refusals, VELDO-0241);
   no exporter is built here.
5. Named refusal for the lead to add to the spec's error taxonomy (lead's ruling 3, refusal kept): a fan-out inside
   a branch is refused at save as unsupported_configuration:branch_escapes_join:<node>, naming the nested fan-out
   node; nesting is out of this spec's scope and no AC requires it.
6. Lead's ruling 2 applied: the VELDO-0043 graph adapter (control_graph.py) is left unchanged. No AC of this spec
   requires an observed text field value containing '/' to pass: AC1 allows '/' in a check's literal value, which
   is checked at save and passes; AC2's rows run on number and choice fields. A cycle check over a text field whose
   observed value holds a path separator is refused path_in_request by that adapter before the runner sees it. The
   Line's check (item 1) is evaluated in process and does not go through that adapter.
7. Assumption: a number field holds integers (a definition is VELDO-0132 plain data, which carries no floats).
8. Suite 101 (landing reuse) fails its two sandbox rows and ends on 'incomplete file-read trace' in this
   environment, identically at 56d8860e before any round-2 change (suite-101_veldo_0208_landing_reuse-at-56d8860e.txt):
   its strace rows are the gate's unconfined leg (scripts/gate_unconfined.json) and need nested ptrace here.
