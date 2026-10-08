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

## Recording closures (2026-10-08)

The proposer (scripts/propose_case_inputs.py) was run, traced, sequentially and in the foreground,
over one case of every control group (suite, module, fixture) of the 1602 confined cases the gate
ran fresh without a reviewed declaration: 200 groups covering every confined suite and module, in
batches under 10 minutes. Not every one of the 1602 cases was traced. Tracing all of them is about
24 hours of sequential work (the 0210d receipts hold 86451 worker seconds for their three modes),
and the first groups showed a blocker that holds for every case running Git, so the per-group
sample answers the admission question at a twelfth of the cost. Per-case results are in
closure-survey-0210d.json.

Before the run the proposer was corrected so its proposals match what the coordinator enforces:
it judges and proposes only what the case read after its Landlock (the coordinator's
after_confinement boundary; the authority's own bootstrap before it was being proposed, including a
listing of all of scripts/ that made every case look gate-starting); it grants runtime links by
their targets and the runtime directories a case lists or probes; it records a failed or
incomplete trace per case instead of stopping the batch; it merges batches; and it refuses, with
every reason, a case that cannot qualify.

Result: **0 of 200 groups qualify. scripts/mutation_case_inputs.json now holds no proposal**; its
30 earlier baseline-only proposals were each superseded by a traced refusal of the same group (11
of them belong to unconfined suites).

| Reason (any, a case can have several) | Groups |
| - | - |
| runtime_unkeyable: Git probes /usr/share/locale, whose tree has dangling links | 180 |
| starts_a_gate: the inputs include verify.sh, gate_candidate.py, gate_legs.py or agent_sandbox.py | 54 |
| worker_or_trace_failed: a worker timed out, or descendants were killed mid-syscall (incomplete trace) | 38 |
| host_input: probes outside repository, runtime and scratch (credential files in the home directory, /var/lib/dpkg/status) | 37 |
| unclean_baseline: a baseline or noop row failed when traced | 12 |
| reads_history: reads this repository's Git objects beyond the preamble | 8 |

99 groups fail on runtime_unkeyable alone: they are clean, file-only, read no history or host
path, and start no gate.

### Why every Git-running case is blocked today

1. The shared suite preamble (scripts/suites/shared.py) runs `git rev-list` twice at import, in
   every suite. In a declared snapshot there is no .git, Git probes for it, and
   case_inputs.safe_name forbids declaring .git even as absent, so the coordinator refuses the
   worker (`undeclared input read: .git`). COMMIT_DEPTH is computed and never used; ROOT_COMMITS
   is used only inside history_begins_with. Computing both lazily removes Git from every suite
   that does not ask about history, with no change to what any suite asserts.
2. Every Git process stats /usr/share/locale. To key that probe the directory must be a runtime
   grant, and gate_reuse.tree_identity refuses its tree because it holds dangling links
   (for example af/LC_MESSAGES/coreutils.mo). Identifying a dangling link by its link text
   (a target appearing later still changes the identity) would make it keyable.

Neither change is made here: the first needs a specification, the second changes a protected
identity rule. Both were applied only in a throwaway clone under /tmp to measure their effect
(below).
