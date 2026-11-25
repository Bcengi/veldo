VELDO-0360 implements scheduler fail-fast. Only exact `VELDO_GATE_COLLECT_ALL=1` opts into the prior diagnostic inventory behavior. Every required stage remains mandatory for green.

Native controls run tiny sleeping processes in a private delegated service capped at 256 MiB. They use the production meter and scheduler CLI, with fixture commands, graph, capacity and input guard. They exercise real cgroup killing/removal, orphan adoption/reaping, ledger release and receipt publication. They are not a full gate. `native-controls.json` summarizes four controls; the four `native-*.json` files preserve complete receipts and partial results. No load generator or host gate lock was used.

`check_mutants.py` uses the registry materializer and assertion observer. Each of 15 new mutants has a green no-op control and a red named row; exact applied diffs and source hashes are retained. `check_load_graph.py` runs only suite 160's graph assertion, with green baseline/no-op and red legacy load-guard mutant; it excludes the generator and shell gate sections.

The scheduler suite (27 rows), shard suite (50 rows), and new fail-fast suite (38 rows) pass alone. The adjacent measured-admission suite has seven existing failures, identical with the original scheduler. See `scheduler-suites.txt` and `admission-baseline.txt`; these partial selectors are diagnostics, not canonical proof of a green gate.

Protected paths touched: `scripts/gate_schedule.py`, `engine/scripts/gate_schedule.py`. Their contents match. Neither verification shell nor the unconfined declaration changed. No live-capture-bound module changed.

Review status: prepared, not independently reviewed. The owner prohibited sub-agents and a full gate for this task. No approval or verdict is authored here. A fresh-context reviewer should receive the ready spec, final diff and this bundle; a full gate and commit-bound owner approval of both protected paths remain required at landing.
