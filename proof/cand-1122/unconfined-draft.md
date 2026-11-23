# Unconfined declaration draft for the owner's landing decision

Prepared on `cand-1122-unconfined-draft`, starting at `2e4c3a8fb`.
This is a proposal on the separate draft branch, not an approval or an edit to
`cand-1122`. It implements the four groups in [combine.md section 7a](combine.md#7a-scriptsgate_unconfinedjson-the-entries-for-the-owners-landing-decision)
as six additional entries in `scripts/gate_unconfined.json`. Existing entries,
including the six bring-up entries for 0177, 0179, 0183 and 0187, and the
declaration's authority and stages are unchanged.

## Scope the existing schema can enforce

`scripts/gate_legs.py:load` validates `veldo.gate-unconfined/v1`: each suite has
one entry containing `suite`, `reason` and optionally one lowercase `rows` tag.
It does not accept literal row paths, row lists, case names or per-entry stages.
A tag works only where the suite calls `leg_runs(tag)` and keeps its ordinary
rows behind `leg_runs()`. An invented tag would not filter a suite's assertions.
Of these six suites, only `48_veldo_0108_relay` implements that division.

Mutation selection is coarser still: `gate_legs.mutation_leg` lists suites, and
`check_gate_mutations.in_leg` requires a whole-suite entry. A mutation case for
a row-scoped suite is refused as `rows_scoped_unconfined_case`, not run outside
confinement. Consequently this draft cannot limit 0113's exemption to five
cases, or move only 0358's two rows while also enabling its mutation baselines.
The suite execution and routing schema are unchanged by this draft. Two
supporting declaration-check updates are included: suite 101's exact expected
list now includes the five additional whole suites and suite 48's `census` tag;
suite 48's documentation names suite 0114 without a file path. The latter avoids
the fixture-sharing check mistaking a documentation cross-reference for a
loaded whole-suite fixture. Neither change adds a permission or weakens an
assertion: suite 101 still requires exact membership and no missing sharers.

## The four groups

1. **VELDO-0358 wave 1:** `157_veldo_0358_suite_runtime`, whole suite.
   `waits/no-idle-wake` and `waits/cgroup-gone-is-empty` create child cgroups.
   The confined leg denies those writes. There is no leg-aware tag for these
   rows, and its mutation workers require the whole suite. This is broader
   than the two failing assertions; a narrower unit entry would require suite
   changes, and would still leave its mutation cases refused under this schema.
   [Integration section 7, item 3](../VELDO-0358/integration-wave1.md#7-open-for-the-lead-and-the-owner)
   records both permission failures and all thirteen mutation controls red.

2. **VELDO-0113:** `114_veldo_0113_no_autostart`, whole suite.
   The VELDO-0111 observer arms each measured client with `PTRACE_TRACEME`;
   confinement denies ptrace. The [mutation evidence](../VELDO-0113/ptrace-mutation-cases.txt)
   records all 22 external cases ending before the pre-exec stop, with
   `Operation not permitted`, and all five mutation cases `invalid_baseline`.
   The schema has no case-scoped entry, and the fixture measures the matrix
   before emitting its rows. The five requested cases are:

   | Case | Target row |
   | --- | --- |
   | `autostart113-reaped-fallback` | `unavailable/no-client-starts-the-authority` |
   | `autostart113-transient-abstract-listener` | `unavailable/no-client-hosts-a-listener` |
   | `autostart113-incomplete-counts-as-success` | `unavailable/no-auto-start-needs-census` |
   | `autostart113-construction-outside-authority` | `unavailable/in-process-construction-boundary` |
   | `autostart113-cli-direct-construction` | `unavailable/in-process-construction-boundary` |

3. **VELDO-0359 B2:** `158_veldo_0359_store_guard`, whole suite.
   The fixture receiver needs the systemd user manager, pidfds, Landlock and
   the namespace helper. The confined leg refuses its initial private fixture
   under `/var/lib/veldo`, before it can exercise that boundary. This follows
   the [B2 proposal](../VELDO-0359/b2-gate-unconfined-proposal.txt) and the
   confined mutation baseline failures recorded in combine.md section 3.
   `VELDO_0359_ROWS` is a fixture selector, not a gate `rows` tag; the fixture
   placement happens before the selected checks. The existing real-mount
   deferrals are unaffected.

4. **VELDO-0111 / VELDO-0114 relay census:** three entries.
   - `113_veldo_0114_relay_census`, whole suite: the relay's census starts
     before exec and continues through descendant drain. Denied ptrace makes
     receipts incomplete and withholds the no-listener/no-second-process
     claims. The suite has no leg-aware row tag.
   - `48_veldo_0108_relay`, **`rows: "census"`**: only
     `relay/one-endpoint-one-judgement` moves. Its VELDO-0114 no-listener claim
     consumes the VELDO-0111 census; without complete receipts it stands down
     with `census_incomplete`. The other ten ordinary assertions stay confined.
     The suite implements both sides of this tag, and suite 0114 contains the
     corresponding row-partition check. Any mutation case assigned to suite 48
     remains subject to the row-scoped-case refusal described above.
   - `113_veldo_0111_census`, whole suite: the process/listener lifetime,
     observer, qualification and descriptor probes need the ptrace collector.
     The suite has no leg-aware row tag. A denied observer cannot establish
     its live census claims.

## Selected confined runs without the draft entries

The original declaration was loaded before editing, with SHA-256
`4fb4d48ce0c9c412c54a13de45c3aae25971d604322b44085f010f47c5253afb`.
Its `entries` and digest
were passed using `gate_legs._env('confined', entries, digest)`. Each named suite
was invoked once, sequentially, through the actual gate launcher:

```sh
python3 -B scripts/gate_candidate.py --root "$PWD" -- \
  python3 -B scripts/selftest.py --suite SUITE_NAME
```

These are selected-suite confined runs, not an aggregate leg or mutation stage.
Their counts include the dispatcher's shared preamble. A successful selected
run exits 2; an assertion failure exits 1. A stand-down is not proof of the
live claim even when the protocol assertions pass.

| Suite | Exit | Confined observation without the proposed entries |
| --- | --- | --- |
| `157_veldo_0358_suite_runtime` | 1 | 36 passed / 2 failed. Both named cgroup rows failed with `Errno 13: Permission denied` creating a child under the current cgroup. The other event-source probes in `waits/no-idle-wake` returned `done`. |
| `114_veldo_0113_no_autostart` | 1 | 34 passed / 2 failed. `each-external-client-reaches-refusal` and `full-fault-matrix-is-exercised` failed. All 22 external clients reported `PTRACE_TRACEME`, `root did not reach pre-exec stop` and `Errno 1: Operation not permitted`. The three absence rows stood down with `census_incomplete`; construction passed and store-write remained the explicitly reported GAP. |
| `158_veldo_0359_store_guard` | 1 | Uncaught `PermissionError`, errno 13, in `TemporaryDirectory(..., dir='/var/lib/veldo')`, before B2 assertions or a final count summary. |
| `113_veldo_0114_relay_census` | 1 | 28 passed / 1 failed. `relay/no-listener-during-call`, `relay/no-second-process` and `relay/listener-proof-needs-census` stood down with `census_incomplete`. `relay/rows-scoped-entry-moves-only-the-census-row` failed: its nested logical legs selected exactly one census row and ten ordinary rows, but did not satisfy the requirement that every asserted row be true. Both nested runs still inherited actual confinement. |
| `48_veldo_0108_relay` | 1 | 37 passed / 1 failed. `relay/one-endpoint-one-judgement` failed; the ordinary relay rows did not fail. The composite deliberately stays red when its endpoint/judgement comparison fails even if census evidence is incomplete. This run must not be described as a passing composite or merely a stand-down. |
| `113_veldo_0111_census` | 1 | Fourteen `census/*` assertions failed, including process/listener lifetimes, observer separation, incomplete/qualification checks, protocol operations, accepted/implicit effects, compatibility, async/io_uring and clone-untraced checks. Then `receiver.bind` on the abstract Unix socket for the escaped-reference probe raised `PermissionError: [Errno 1] Operation not permitted`. Execution ended before the later rows and before a final count summary. |

All six selected invocations completed once; none was retried. Suite 48's
documentation correction was in place before its invocation and does not change
its execution. These failures and stand-downs show what confinement prevented;
no unconfined rerun or mutation verdict is claimed for this draft.

Raw stdout/stderr and exit records remain locally under
`/tmp/cand-1122-unconfined-proof-exnirjcc`, with one `SUITE_NAME.log` per run.
The following SHA-256 values bind those raw logs; the observations above omit
personal home prefixes and runtime account identifiers.

| Suite | Raw log SHA-256 |
| --- | --- |
| `157_veldo_0358_suite_runtime` | `d0aa798b1bd8ee6c24dbc718d6a07b162a635276b2cc28a37d945820b71f096a` |
| `114_veldo_0113_no_autostart` | `f0c0a7b006c1f81e81e1078a2c156e97316b8a0ca938617c4f5c9c8898496000` |
| `158_veldo_0359_store_guard` | `205d435d0121e92222828d7842b8424e4484ab8260ce5bb1c9a3de7e49a3cf60` |
| `113_veldo_0114_relay_census` | `6e05aa9377bb4516561cd1e863e9bc65ea6fa2ad0c95b8d964ea15394ea8da07` |
| `48_veldo_0108_relay` | `a24e02b3621bce1140ebffb092239b02cfc1f6140a2d0d6db7019e6fb0d285b6` |
| `113_veldo_0111_census` | `626d2c3cc58870f1e0ec288b6f3ebd28cdd807264b46be94d020504f1c1ab2ca` |

## Validation

The existing validator accepted the edited declaration for each exact stage
command (exit 0 each):

```sh
python3 -B scripts/gate_legs.py --declared --stage unit -- 'python3 scripts/selftest.py'
python3 -B scripts/gate_legs.py --declared --stage integration -- 'python3 scripts/check_first_use.py'
python3 -B scripts/gate_legs.py --declared --stage mutation -- 'authority mutation stage'
```

These commands only validate the declaration; they do not execute those stages.
The existing suite 101 blocks `unconfined-leg/declared-list` and
`unconfined-leg/fixture-sharers-are-listed` were extracted verbatim and executed
with the real loader, manifest and source tree: both passed (`[]` and `{}`
respectively). Suite 101 was not run in full. Exact expected membership remains
checked: 59 whole suites, the two prior `strace` entries and suite 48's `census`
entry. All six new names occur in the manifest; the prior entries and metadata
compare equal to the starting declaration. Both edited Python files parse.

The proposed declaration has SHA-256
`80b2fcbce692cf0d70e74bba071cd8a6ece1503a92ccfb004d91ea0fb04057ac`.

`python3 -B scripts/check_personal_setup.py`: **0 findings** (built-in shapes;
no installation found). `git diff --check`: pass. No full leg or `verify.sh`
was run. No hook or Git/shell tooling refused a typed command; the confined
suite failures above are test observations, not such guards.
