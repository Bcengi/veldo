# Where the 0210d gate spends its time

Source: the green gate log for 90df3823 (gate-0210d, 2026-10-08), read after the fact. Nothing was
rerun to produce these figures. The log prints no timestamp per stage, so stage times come from the
figures each stage prints about itself, and a stage that prints none is marked as such.

## Wall time per stage

| Stage | Wall time | Source in the log |
| - | - | - |
| lint | 1.85 s | lint line |
| unit, confined leg (7413 rows) | about 1164 s | not printed; the first-use rerun of the same leg took 1164 s |
| unit, unconfined leg (850 rows) | about 753 s | not printed; the first-use rerun of the same leg took 753 s |
| integration, confined leg (first use) | 1165 s | elapsed line |
| integration, unconfined leg (first use) | 754 s | elapsed line |
| security, generated, docs, packaging, extra | not printed | short |
| mutation | 4359.9 s | mutations line |
| secret scan, contracts, shape gate, review events | not printed | short |

The gate therefore runs the whole selftest four times (two legs, twice: unit and the first-use
integration rerun), about 3836 s, and the mutation stage once, about 4360 s: roughly 8200 s, or
2 h 17 min, of which the unit and integration stages are 47% and mutation 53%. Nothing in the unit
or integration stages is reused.

## Mutation stage

2494 cases, 3190 workers, 16 in parallel, 4359.9 s wall, 69282 worker seconds. Reused: 0.

| Receipt reason | Cases | Worker seconds |
| - | - | - |
| unknown_closure (no declaration recorded) | 1583 | about 35000 |
| unconfined_leg | 892 | 33635 |
| unreviewed_declaration | 19 | (in the row above, confined) |

### The 20 slowest suites in the stage (worker seconds, all modes)

| Worker s | Workers | Leg | Suite |
| - | - | - | - |
| 5707 | 150 | confined | 78_veldo_0160_account_pool |
| 4993 | 124 | unconfined | 71_veldo_0130_api |
| 3742 | 52 | confined | 82_veldo_0144_mcp_catalog |
| 3589 | 65 | confined | 75_veldo_0062_accounts |
| 3528 | 86 | confined | 58_veldo_0028_effects |
| 3066 | 67 | unconfined | 86_veldo_0127_agent_configuration |
| 2853 | 60 | unconfined | 86_veldo_0189_engine_upgrade |
| 2798 | 44 | unconfined | 86_veldo_0148_re_land |
| 2443 | 27 | unconfined | 92_veldo_0088_pm_cycles |
| 1680 | 26 | unconfined | 93_veldo_0152_intake_routes |
| 1643 | 47 | unconfined | 78_veldo_0060_claude_adapter |
| 1623 | 74 | confined | 59_veldo_0037_aliases |
| 1418 | 64 | unconfined | 82_veldo_0141_execution_record |
| 1410 | 24 | unconfined | 82_veldo_0129_worker_wiring |
| 1306 | 91 | confined | 62_veldo_0065_presentations |
| 1017 | 27 | unconfined | 73_veldo_0139_factory_setup |
| 964 | 69 | confined | 62_veldo_0054_decisions |
| 957 | 24 | confined | 67_veldo_0056_candidates |
| 912 | 41 | unconfined | 79_veldo_0061_codex_adapter |
| 911 | 29 | confined | 69_veldo_0058_gate_output |

### The 20 slowest suites by one run (the baseline worker runs the whole suite once)

The selftest prints no per-suite time in a full run, so the mutation stage's baseline workers are
the best per-suite runtime the log holds. The sum of the median baselines of all 95 mutated suites
is 1666 s, close to the selftest's own 1917 s.

| One run | Leg | Suite |
| - | - | - |
| 95.2 s | unconfined | 92_veldo_0088_pm_cycles |
| 72.0 s | confined | 82_veldo_0144_mcp_catalog |
| 70.2 s | unconfined | 93_veldo_0152_intake_routes |
| 67.9 s | confined | 87_veldo_0127_codex_delivery |
| 64.8 s | unconfined | 86_veldo_0148_re_land |
| 60.9 s | unconfined | 82_veldo_0129_worker_wiring |
| 54.1 s | confined | 75_veldo_0062_accounts |
| 52.3 s | unconfined | 86_veldo_0127_agent_configuration |
| 51.8 s | unconfined | 86_veldo_0189_engine_upgrade |
| 47.4 s | unconfined | 83_veldo_0154_factory_loop |
| 41.6 s | confined | 67_veldo_0056_candidates |
| 39.9 s | unconfined | 71_veldo_0130_api |
| 38.5 s | confined | 78_veldo_0160_account_pool |
| 38.3 s | confined | 58_veldo_0028_effects |
| 35.3 s | unconfined | 78_veldo_0060_claude_adapter |
| 34.7 s | unconfined | 73_veldo_0139_factory_setup |
| 31.6 s | confined | 69_veldo_0058_gate_output |
| 30.8 s | unconfined | 71_veldo_0138_channel_service |
| 23.7 s | confined | 58_veldo_0036_reservations |
| 23.5 s | confined | 59_veldo_0037_aliases |

### The 892 unconfined_leg cases

They are every case of the 32 suites that scripts/gate_unconfined.json names whole (owner decision,
VELDO-0208, Unconfined leg). The listed reason for each is the systemd user manager: the suite
launches workers or services as transient user units (systemd-run and systemctl against the user manager) and
reads their state under /run/user/uid, which Landlock confinement and the seccomp ban on Unix
service sockets forbid. Largest: 71_veldo_0130_api 100, 86_veldo_0127_agent_configuration 53,
82_veldo_0141_execution_record 50, 86_veldo_0189_engine_upgrade 48, 63_veldo_0040_containment 41,
66_veldo_0047_authority 40, 63_veldo_0049_floor 36; 25 more suites hold 10 to 35 each. The two
row-scoped entries (suites 100 and 101, strace rows) hold no mutation case.

An unconfined case is neither confined nor traced, so nothing bounds what it read, and the
coordinator never keys it (check_gate_mutations.run_stage sets its key to None). These cases are
outside VELDO-0207 by construction: host services are the case VELDO-0207 leaves fresh until a
separate closure can enforce them. They are 36% of the cases and 49% of the worker seconds.

### The 19 unreviewed_declaration cases

These are the 19 confined cases of the original 30-case VELDO-0207 measurement whose proposals are
in scripts/mutation_case_inputs.json with reviewed false (the other 11 belong to unconfined suites).
28 of the 30 were imported baseline-only from that measurement, so they are incomplete proposals
by the spec's own terms; none was ever reviewed. A proposal grants no reuse.
