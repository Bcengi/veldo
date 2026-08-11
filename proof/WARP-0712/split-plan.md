# WARP-0712 the decomposition plan, derived from the measurement

THIS PLAN IS GENERATED FROM THE MEASUREMENT, not drawn around topic names. `python3
scripts/suite_slice.py --emit-plan --from proof/WARP-0712/order-dependence.json` emits it whole
and the gate regenerates it and DIFFS. The boundaries below come from where data actually stops
crossing, which is the criterion AC1 sets, and the ORDER comes from each region's measured
dependency closure. Nothing in this document is executed by this round: WARP-0712 round 1 builds
the proofs and records the plan, and moves no file.

Measured from: `scripts/selftest.py`, content digest sha256 e8b70e982e750436c6e65e7874b5df7c8ed5cebd085ea68cfe9acbe109cdfa9d
Assertion budget per suite file: 250. This is a JUDGEMENT, published here next to what it decides.

PHASE 1 IS THE WHOLE COST AND IT IS NOT OPTIONAL. Every name in the hoist list is a module-level
binding one region creates and another reads, measured by running the reader without the writer
and watching it die. Until they live in one importable fixture module with a declared owner, every
suite that reads one is a suite that only passes in company. The owner column is DERIVED from the
binding, so no ownership is assigned by judgement.

PHASE 2 IS CHEAP ONCE PHASE 1 IS DONE, and it is where the throughput comes from. The partition
below walks the regions in file order and closes a suite when its assertion budget is reached, and
it NEVER closes at a marker a top-level statement straddles, because a split moves whole
statements and those markers are not boundaries at all.

PHASE 3 IS WHATEVER IS NOT SETTLED, LAST AND ON ITS OWN. A region belongs here if its prerequisite
search did not converge inside the round cap, so its closure is a LOWER bound, or if it DID
converge and then proved a different label set than the full run attributes to it. Either way its
independence is not established, and moving it behind the rest keeps the unknown in one place
instead of spread across the partition. The regions that put a suite in phase 3 are named under
the partition, so this paragraph is not the only place a reader learns of them.

## Phase 1: the shared fixtures to hoist, with their owners

| name | owning region(s) | regions that needed it |
|---|---|---|
| AC | 82 | 3 |
| ACT | 104 | 6 |
| AE | 105 | 26 |
| AR | 6 | 9 |
| ARCH | 87 | 41 |
| AUTHZ | 119 | 20 |
| BR | 65 | 1 |
| C10 | 126 | 1 |
| CL10 | 126 | 1 |
| CLI | 9, 85 | 1 |
| DEC | 88 | 32 |
| DSP | 80 | 2 |
| EN | 96 | 1 |
| EV | 7, 41, 100 | 2 |
| EV22 | 151 | 2 |
| EX | 39 | 2 |
| FL | 54 | 5 |
| FR | 49 | 5 |
| GOOD_ARCH | 87 | 3 |
| GOOD_DECISION | 88 | 3 |
| GOOD_INCIDENT | 98 | 19 |
| GOOD_REMEDY | 98 | 2 |
| GOV | 53 | 3 |
| IC | 101 | 1 |
| IK | 62 | 3 |
| INC | 98 | 7 |
| IOS | 23 | 11 |
| IR | 124 | 17 |
| ISC | 40 | 37 |
| JI | 108 | 9 |
| K10 | 126 | 3 |
| ME | 7 | 21 |
| MI | 60 | 3 |
| PK | 57, 72 | 41 |
| PL | 5, 27 | 2 |
| RL | 42 | 4 |
| RN | 68 | 2 |
| RP | 115 | 1 |
| RQ_RR | 122 | 1 |
| RS | 44, 97 | 66 |
| SG | 95 | 1 |
| TA | 58 | 79 |
| TK | 106 | 22 |
| TR | 55 | 3 |
| WK | 50 | 4 |
| _ACT_TRIO | 104 | 21 |
| _CH_ENGINE | 71 | 1 |
| _D724V | 178 | 2 |
| _FakeDriver | 6 | 1 |
| _FakeIosDriver | 23 | 1 |
| _FakeLoop | 39 | 3 |
| _L07_FM | 149 | 26 |
| _L07_LOOP_MARKER | 144 | 1 |
| _L07_SPEC_TEXT | 144 | 27 |
| _L07_SRC | 144 | 2 |
| _M10_DECLARED_SOURCES | 129 | 4 |
| _M10_FILES | 126 | 3 |
| _M10_MEASURE_KEYS | 129 | 5 |
| _M10_R10_PRIMS | 137 | 4 |
| _M10_R10_TREES | 137 | 1 |
| _M10_R11_TREES | 139 | 1 |
| _M10_R11_UNIT_OF | 139 | 1 |
| _M10_R11_UNIT_PATHS | 139 | 1 |
| _M10_R7_TREES | 132 | 3 |
| _M10_R8_READERS | 133 | 2 |
| _M10_R9_SELFREC | 135 | 1 |
| _M10_R9_TREES | 131 | 2 |
| _M10_R9_TRIES | 135 | 6 |
| _MW_MADE | 6 | 1 |
| _MW_SEC | 6 | 1 |
| _P13_CONTRACT | 89 | 2 |
| _SG_PACKS | 95 | 38 |
| _TRIP_DETACH_TOKENS | 92 | 33 |
| _V13Recorder | 195 | 3 |
| _V13_FAKE | 195 | 2 |
| _V13_FROZEN | 194 | 3 |
| _V13_MOBILE | 189 | 5 |
| _V23_NAMES_PRESENT | 176 | 1 |
| _ag_cfg | 111 | 1 |
| _az_hashlib | 119 | 1 |
| _connected_pair | 90 | 1 |
| _good_request | 113 | 1 |
| _ir_src | 124 | 1 |
| _ji_mut | 108 | 2 |
| _js_cfg | 109 | 1 |
| _l07_fixture_repo | 145 | 1 |
| _l07_git | 144 | 2 |
| _l07_run | 145 | 1 |
| _lp_src | 143 | 33 |
| _m10_f3_a | 127 | 13 |
| _m10_futures | 138 | 3 |
| _m10_nest | 130 | 3 |
| _m10_no_measure | 129 | 4 |
| _m10_pre_change | 131 | 8 |
| _m10_r11_engine | 140 | 2 |
| _m10_r9_engine | 134 | 1 |
| _m10_record_text | 126 | 2 |
| _m10_seed_record_unencodable | 130 | 9 |
| _m10_sh | 128 | 14 |
| _m10_tree_seed | 126 | 6 |
| _mw_instrument | 6 | 1 |
| _pkos | 77 | 1 |
| _rd_hashlib | 117 | 1 |
| _rl_os | 42 | 34 |
| _rr_hashlib | 122 | 20 |
| _s16_re | 179 | 1 |
| _threading | 17 | 2 |
| _tk_human | 106 | 2 |
| _tk_run | 106 | 1 |
| _v13_ast_settle_map | 193 | 3 |
| _v13_canon | 203 | 1 |
| _v13_class_src | 191 | 2 |
| _v13_load_copy | 196 | 3 |
| _v13_rec | 197 | 1 |
| _v13_resolves_real | 190 | 4 |
| _v13_src | 189 | 1 |
| _v13_time | 189 | 3 |
| _v13_time_calls_outside_driver | 192 | 1 |
| _v13_tracked_copies | 189 | 1 |
| _v22_derivable | 152 | 2 |
| _v22_engine_copies | 151 | 1 |
| _v22_events_src | 152 | 1 |
| _v22_fx_route | 168 | 1 |
| _v22_git | 151 | 8 |
| _v22_keys | 152 | 1 |
| _v22_lines | 151 | 1 |
| _v22_module_in | 151 | 1 |
| _v22_module_rels | 152 | 7 |
| _v22_rep | 154 | 1 |
| _v22_seed | 151 | 9 |
| _v22_skill_rels | 175 | 2 |
| _v22_spec_text | 151 | 1 |
| _v22_tracked | 152 | 3 |
| _v22_verify_rels | 155 | 4 |
| _v22_wrapper_copies | 151 | 1 |
| _v25_artifact_rel | 156 | 2 |
| _v25_entitlement | 156 | 2 |
| _v25_enum_blobs | 157 | 1 |
| _v25_enum_keys | 157 | 1 |
| _v25_module_texts | 156 | 1 |
| _v25_shutil | 156 | 1 |
| hashlib | 151 | 1 |
| re | 71, 108 | 103 |

Names read and bound nowhere at module level: none

## The measured coupling, before the hoist

| component size | regions |
|---|---|
| 151 | 6, 7, 23, 36, 39, 40, 41, 42, 43, 44, 45, 46, 49, 50, 53, 54, 55, 56, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 161, 162, 163, 164, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 189, 190, 191, 192, 193, 194, 195, 196, 197, 200, 201, 202, 203, 204, 205 |
| 3 | 5, 11, 12 |
| 3 | 17, 18, 22 |
| 1 | 1 |
| 1 | 2 |
| 1 | 3 |
| 1 | 4 |
| 1 | 8 |
| 1 | 9 |
| 1 | 10 |
| 1 | 13 |
| 1 | 14 |
| 1 | 15 |
| 1 | 16 |
| 1 | 19 |
| 1 | 20 |
| 1 | 21 |
| 1 | 24 |
| 1 | 25 |
| 1 | 26 |
| 1 | 27 |
| 1 | 28 |
| 1 | 29 |
| 1 | 30 |
| 1 | 31 |
| 1 | 32 |
| 1 | 33 |
| 1 | 34 |
| 1 | 35 |
| 1 | 37 |
| 1 | 38 |
| 1 | 47 |
| 1 | 48 |
| 1 | 51 |
| 1 | 52 |
| 1 | 57 |
| 1 | 59 |
| 1 | 70 |
| 1 | 79 |

## Phase 2: regions to files

| suite file | regions | regions held | assertions | move in phase | unsettled regions |
|---|---|---|---|---|---|
| scripts/suites/01_warp_0101_reviewer_notes.py | 1-22 | 22 | 252 | 2 | - |
| scripts/suites/02_mobile_ios_runner_b8.py | 23-32 | 10 | 261 | 2 | - |
| scripts/suites/03_plugin_extension_loading_runner.py | 33-43 | 11 | 261 | 2 | - |
| scripts/suites/04_run_status_reader_warp.py | 44-54 | 11 | 254 | 2 | - |
| scripts/suites/05_tracker_routing_resolver_warp.py | 55-70 | 16 | 251 | 2 | - |
| scripts/suites/06_capabilities_manifest_honesty_warp.py | 71-89 | 19 | 255 | 2 | - |
| scripts/suites/07_warp_1103_completion_mandatory.py | 90-96 | 7 | 255 | 2 | - |
| scripts/suites/08_restoration_spec_generation_warp.py | 97-103 | 7 | 288 | 2 | - |
| scripts/suites/09_action_whitelist_warp_1205.py | 104-109 | 6 | 259 | 2 | - |
| scripts/suites/10_warp_0613_anti_vacuity.py | 110-121 | 12 | 250 | 2 | - |
| scripts/suites/11_inbound_command_receipt_reconcile.py | 122-126 | 5 | 263 | 2 | - |
| scripts/suites/12_warp_1210_hardening_four.py | 127-142 | 16 | 266 | 3 | 142 (CLOSED_PROVES_DIFFERENTLY) |
| scripts/suites/13_warp_0623_codified_live.py | 143-205 | 51 | 187 | 2 | - |

Observation point for every suite above: its own `selftest: N passed, M failed` line and its own assertion-LABEL multiset, compared against the projection of the full run onto it by scripts/suite_equiv.py. The dispatcher's aggregate line keeps its exact current format, which is what AC2 holds it to.

## The order

1. `scripts/suites/_fixtures.py` and `scripts/suites/manifest.json` first, carrying the assertion primitive, the counters and every hoisted name above. Nothing else can move before this exists.
2. The phase 2 suites, in the order listed, one commit each, with `scripts/suite_equiv.py` run after each one and the label identity re-checked against the recorded baseline after each one.
3. The phase 3 suites last: scripts/suites/12_warp_1210_hardening_four.py
4. `scripts/selftest.py` reduced to the dispatcher only, which is the point at which AC2's assertion that it holds no assertion of its own can pass.

## What this plan does NOT establish

1. That the phase 3 regions are independent: 142 (CLOSED_PROVES_DIFFERENTLY). Each either did not
   converge inside the round cap, so its closure is a lower bound, or converged and then proved a
   different label set.

2. That hoisting a name is behaviour-preserving. A name bound by a statement with side effects
   moves those side effects with it, and only the label identity proof and the per-suite
   equivalence run can say whether that mattered.

3. That the assertion budget is the right one. It is a judgement, and a different budget changes
   only how many files the same regions land in.
