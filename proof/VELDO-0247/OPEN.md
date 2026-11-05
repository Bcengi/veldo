# VELDO-0247 open items

1. The Line (control_service.py) does not run check or join nodes in a unit's process. The check, join and
   fan-out are built for the VELDO-0132 cycle (control_workflow_cycle.py and the LangGraph runner), where two
   assignment branches are dispatched together and run in one superstep. `check` and `join` are not registered as
   station kinds, so a unit workflow holding them is refused at binding as not_a_station
   (control_workflow_unit.unit_problems) and the Line never meets one. The AC3 sentence "the Line dispatches the
   branches' workers without waiting for one another" is therefore not built for the Line: the Line keys a unit's
   stations by (unit, station), one build and one review per unit, and parallel stations need that keying changed.
   This is inside this spec's footprint, so it is this spec's gap, recorded for the owner and the lead; the save
   check (AC4) already holds for unit definitions that use check, fan-out and join.
2. The canvas run view that reads the recorded decisions and branch positions is VELDO-0246's.
3. The rollback's refusal of a later installation commit holding check or join is VELDO-0253 AC1's.
4. Metrics are in-process counters (Cycles.metrics; saves refused by problem in Workflows.refusals, VELDO-0241);
   no exporter is built here.
5. A fan-out inside a branch is refused as unsupported_configuration:branch_escapes_join:<node>; the spec's save
   taxonomy names no separate problem for it.
6. A text field whose observed value contains a path separator is refused by the VELDO-0043 adapter
   (path_in_request, control_graph.py, outside this footprint) before the runner sees it, although '/' is allowed in
   a check's literal value.
7. Assumption: a number field holds integers (a definition is VELDO-0132 plain data, which carries no floats).
