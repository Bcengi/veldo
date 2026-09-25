# VELDO-0128 proof

Release 1 stage 3: the owner hears on Telegram about ordinary progress, stops and completion, from the
committed journal only. The running service's channel runs the reporter on every pass of an active edge:
each enabled event committed after the stored since gets one report, sent through the activated VELDO-0073
edge to the owner's enrolled chat, recorded with what the platform actually returned and correlated to its
source record. Specification status, risk and `.veldo/policy.yaml` are unchanged. This proof is for
independent review; it is not a self-approval, and the canonical gate is run by the lead, not recorded here.

## What was built

- **`.veldo/control_telegram_report.py` (new).** `Reporter(ingress, owner=)` on the activated ingress's one
  store connection. It refuses to be built unless the presenter's edge is the ingress's gated edge, so
  every send asks the activation gate.
  - `REGISTRY` is the declared event set, one handler each, and each reads only what its real writer
    commits: `objective_accepted` (an objective entering ACCEPTED), `decision_awaiting` (a VELDO-0064
    decision request offered at a new request version, named by its settlement terms' touchpoint),
    `work_progress` (a VELDO-0039 `dispatch` record entering accepted, running, exited, refused or
    unknown), `gate_result` (a `gate_observation` control_proof records for LiveLoop.gate, and a
    `floor_unit` step dispatch.py's floor_transition commits: accept_build, record_review passing or
    returning the unit, handoff), `stop` (a VELDO-0075 andon stop) and `completion`.
  - The fields read, with their writer: the dispatch record's `receiver.principal` (accept),
    `process.pid` and `process.host` (run), `termination.returncode`, `signal` and `deadline_stop` (exit,
    `control_dispatch.TERMINATION_FIELDS`), `refusal` (refuse), `reason` (unknown), and the contract's
    `unit`, `station`, `attempt` and `reservation.project` (`control_launch.Runner.prepare`). No report
    names a worker: `CONTRACT_FIELDS` has none. The gate observation's `commit`, `exit`, `green`,
    `terminal`, `stdout_digest` and `refusals` (`control_verification.observe_gate`); it names no unit and
    the report says so. The floor record's `history[-1].action`, `source`, `proof`, `builder`, `build`
    (`dispatch._accept_build`), `reviews[-1]` and `returned_to` (`dispatch._record_review`) and `handoff`
    (`dispatch._handoff`). The project is the source record's own, or its unit's accepted project, or
    `unavailable`.
  - Completion is only VELDO-0051's `spec.shipped`, from its public reader
    (`control_event_projection.Projection.derive`) over the same journal. A green gate, a passed review, a
    handoff, an exited dispatch or a build-only receipt is never a completion.
  - A waiting decision and a stop are sent as a reply to the request's current presentation and name it.
    The andon's own request is never reported as a waiting decision and a revised stop is not a new report.
  - One `telegram_report` record per (event, source record, owner), written only by its registered command
    `telegram_report_record`: a `pending` intent before the send, then `sent`, `anomaly`, `refused` (by
    name) or `unknown_outcome`. Nothing is sent again automatically.
  - **The stored since.** A `telegram_report_cursor` record per domain, repository and owner, written by
    the same command and only moving forward. With none stored, reporting starts after the owner's first
    activation of the edge. After a run it stands at the last sequence read, or just before the first event
    whose report could not be recorded. A pass with nothing new but the reporter's own records reads
    nothing more.
- **`.veldo/control_service_channel.py`.** `Channel.tick` runs `Channel.report` after acquisition,
  presentation and the VELDO-0140 tells, only when the gate woke the pass and the record is `active`, for
  the activation record's owner. The pass summary names every report made. The reporter sends through its
  own record-before-send path on the presenter's gated edge; it adds no reach into the presenter's private
  methods.
- **`.veldo/init_scaffold.py`.** Installs the module. Engine copies are byte-identical.

## Rows, falsifiers and red record

Suite `scripts/suites/72_veldo_0128_reports.py` (about 3 s). The authority is real (SQLite, OpenSSH command,
journal and review signatures, the protected signer). The reports are made by
`control_service_channel.Channel`, built from the 0600 ingress host file and activated by the owner's signed
commands, driven with `Channel.tick`. The sources are written by their real writers: `control_dispatch`
(prepare with a complete contract binding a VELDO-0036 worker slot and, for a build, the VELDO-0031 claim;
the receiver's accept, run, exit; unknown; refuse), `LiveLoop.gate` running a verifier in candidate mode over
the real Git repository with the VELDO-0050 proof service (two green observations, one red), and
`FloorAuthority` (accept_build over the committed proof and the exited build dispatch, assign_review,
record_review with the reviewer's signed receipt printed by its own exited review dispatch, one pass and one
return, and handoff under the review policy). The waits are real inbox requests and the stop a real andon
stop. The objective and the completion receipts remain store fixtures, as the VELDO-0051 and VELDO-0075
suites lay them. The Bot API is the VELDO-0073 loopback stand-in with a 403 switch; a socket guard refuses
everything beyond 127.0.0.1. The real-Telegram send is PENDING the lead's run with the owner.

`red-at-f623b78.json`: the current suite against the pre-rework tree (`git archive f623b78`): 16 of 18 rows
red by assertion, no region raised. There the channel never runs the reporter, and its registry listens to
execution_unit edges for the gate result (`sources/real-writers`). `install/assets` and
`registry/declared-set` are green there, as they should be.

`python3 -B proof/VELDO-0128/drive.py` regenerates `mutations.json` and the diffs: 23 mutants, each reds its
named rows by assertion, the baseline and a no-op copy of each mutated module green. Registry:
`scripts/check_teeth_mutations.py --finding 128`.

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `registry/declared-set` | AC1 | none (the registry against the spec's six events) |
| `registry/delivery` | AC1 | `report-completion-handler-omitted`, `report-not-wired` |
| `registry/committed-sources` | AC1 | `report-before-since`, `report-source-uncorrelated` |
| `content/completed` | AC2 | `report-complete-from-build-only` |
| `content/running` | AC2 | `report-running-from-current-state`, `report-worker-invented` |
| `content/awaiting-decision` | AC2 | `report-presentation-unlinked` |
| `content/gate-rejected` | AC2 | `report-review-returned-as-passed`, `report-gate-from-unit-edges`, `report-gate-observation-ignored`, `report-review-step-unreported` |
| `content/unknown-explicit` | AC2 | `report-unknown-as-running` |
| `send/refusal-recorded` | AC3 | `report-refused-marked-delivered`, `report-refusal-drops-source` |
| `recipient/owner-chat-only` | AC3 | `report-gate-bypassed` |
| `recipient/substitution-refused` | AC3 | `report-gate-bypassed` |
| `stop/no-second-notice` | threat model | `report-andon-request-reported` |
| `sources/real-writers` | findings 1 and 2 | `report-gate-from-unit-edges`, `report-review-step-unreported`, `report-exit-status-invented`, `report-worker-invented` |
| `wiring/tick-reports` | finding 3 | `report-not-wired`, `report-since-unstored` |
| `wiring/restart` | finding 3 | `report-since-unstored`, `report-since-reset-at-restart` |
| `wiring/stopped-edge` | finding 3, VELDO-0073 | `report-while-stopped` |
| `install/assets` | all | `report-not-scaffolded` |
| `observability/named-refusals` | all | `report-refusal-unclassed` |

## What each row group drives

**AC1.** After the activation the suite commits every declared event through its writer, then runs one
channel pass. That pass reports exactly the enabled sources: every dispatch record's accepted, running,
exited, unknown and refused states (never prepared), the three gate observations, the floor's accept_build,
record_review and handoff steps (never assign_review), the waits, the stop and the confirmed landing. The
delivered events are compared with the spec's six; each record keeps project, unit, run and its source
(sequence, command, record digest, entity and digest), checked against the committed journal row; one
message per report; a second pass reports and sends nothing; the reporter writes only its own report and
since records.

**AC2.** Delivered bytes against stored records: the running report names the process of its committed
record (the dispatch has since exited); the red gate names its commit, exit 1 and its RED line; the
returned review names the reviewer, verdict `fail`, the review dispatch, its output digest and the finding
ids the floor recorded; the passing review, the handoff and the build acceptance never claim completion;
an unknown dispatch reads unknown with its recorded reason; a worker ended by signal 9 at its deadline has
no return code and says so; a refused launch names its refusal.

**Findings 1 and 2 (`sources/real-writers`).** The registry's kinds are the writers' own constants
(`control_dispatch.RECORD_KIND`, `control_proof.OBSERVATION_KIND`, `dispatch.FLOOR_KIND`, and the objective,
inbox and andon kinds); every progress and gate report's source command is the dispatch, proof or floor
writer's; the accepted and exited facts equal the receiver and return code the stored record holds; no fact
names a worker.

**Finding 3 (`wiring/*`).** Nothing is reported before the channel's pass; the pass makes every report for
the activation record's owner and stores the since at the last sequence it read. After the channel closes,
events committed while it was down are reported by the first pass of a new channel, and only those: its
reporter read nothing already reported. While the owner has the edge stopped, a pass is refused
`edge_stopped` and sends and records nothing and leaves the since; once he activates it again, the event
committed meanwhile is reported once.

**AC3.** Every report went to the owner's enrolled chat with one gate admission each. A reporter configured
for another person's chat is refused by the gate as `chat_not_enrolled` for every event, nothing reaches
that chat, each record is visibly unsent and names its source. With the stand-in answering 403 the record
is `refused` as `channel_refused`, listed as unsent and not pending, and a later pass sends nothing again.

## Checks run

Finding 128 rejects in full (23), `--jobs 2`. Suites 72_veldo_0128_reports, 71_veldo_0138_channel_service,
74_veldo_0140_standing_delegation and 73_veldo_0139_factory_setup pass.

## Stated limits

One owner per reporter and the Telegram chat channel only. The objective and completion sources are
fixtures here; their writers are proved by their own suites. A gate observation names no unit, so its
report says so rather than guessing. Reconnect, replay, lost-send lookup and delivery recovery are Release
2: a refused or unknown report stays unsent until a later release says how to retry it.
