# VELDO-0128 proof

Release 1 stage 3: the owner hears on Telegram about ordinary progress, stops and completion, from the
committed journal only. Each enabled event committed after an explicit starting sequence gets one report,
sent through the activated VELDO-0073 edge to the configured owner's enrolled chat, recorded with what the
platform actually returned and correlated to its source record. Specification status, risk and
`.veldo/policy.yaml` are unchanged. This proof is for independent review; it is not a self-approval, and
the canonical gate is run by the lead, not recorded here.

## What was built

- **`.veldo/control_telegram_report.py` (new).** `Reporter(ingress, owner=, project=, since=)` on the
  activated ingress's one store connection. It refuses to be built unless the presenter's edge is the
  ingress's gated edge, so every send asks the activation gate.
  - `REGISTRY` is the declared event set, one handler each: `objective_accepted` (an objective record
    entering ACCEPTED), `decision_awaiting` (a VELDO-0064 decision request offered at a new request
    version, named by its settlement terms' touchpoint: grooming, admission), `work_progress` (a dispatch
    record entering accepted, running, exited, refused or unknown), `gate_result` (a unit leaving
    VERIFYING or REVIEWING along a declared R13 edge, passed or rejected, with its receipt), `stop` (a
    VELDO-0075 andon stop recorded) and `completion`.
  - Completion is only VELDO-0051's `spec.shipped`, taken from its public reader
    (`control_event_projection.Projection.derive`) over the same journal: a revision_landed receipt for
    the exact unit and a confirmed publication of its dispatch. The report names the confirmed revision,
    the proof digest, the implementation commit, the receipt and the event id. An exited dispatch, a
    build-only receipt or a unit state is never a completion.
  - A waiting decision and a stop are sent as a reply to the request's current presentation and name it
    (presentation id, message, request version, current state). A request with no presentation says so.
    The andon's own request is never reported as a waiting decision and a revised stop is not a new
    report: the andon's notice stays the one decision message. Unknown and missing values read
    `unknown` or `unavailable`.
  - One `telegram_report` record per (event, source record, owner), written only by its registered
    command `telegram_report_record` (declared owner of the kind): a `pending` intent before the send,
    then `sent` (platform chat, message, date, stored text), `anomaly`, `refused` (the gate's or the
    platform's refusal by name) or `unknown_outcome`. The source is kept by journal sequence, command,
    record digest, entity and entity digest. Nothing is sent again automatically; `unsent()` and
    `metrics()` show refused and unknown reports and the source events still pending.
  - It writes nothing but its own records: no admission, settlement, resumption or completion.
- **`.veldo/init_scaffold.py`.** Installs the module. Engine copies are byte-identical.

`request_doorbell.py`, `control_event_projection.py`, `control_channel_activation.py`,
`control_channel_projection.py` and `control_andon.py` are unchanged.

## Rows, falsifiers and red record

Suite `scripts/suites/72_veldo_0128_reports.py` (about 2 s). The authority is real: SQLite with OpenSSH
command and journal signatures, the production ingress from 0600 host files, qualified and activated by
the owner's signed commands, and the VELDO-0075 andon service. The grooming and admission waits are real
inbox requests (the grooming one presented); the stop is a real andon stop, noticed and revised. The
objective, the dispatch records, the unit transitions, the publication effects and the completion
receipts are fixtures written with the store's signed generic command, as the VELDO-0051 and VELDO-0075
suites lay them. The Bot API is the VELDO-0073 loopback stand-in with a switch that answers sendMessage
with the platform's own 403 error object; a socket guard refuses everything beyond 127.0.0.1. It passes
in the stage environment (`env -i`, empty HOME, `GIT_CONFIG_GLOBAL=/dev/null`). The real-Telegram send
is PENDING the lead's run with the owner and is never counted.

`red-at-e134922.json`: the current suite against the pre-change tree (`git archive e134922`): all 14
rows red by assertion, no region raised (there is no report module, so no reporter is built).

`python3 -B proof/VELDO-0128/drive.py` regenerates `mutations.json` and the diffs: 14 mutants, each reds
its named rows by assertion, the baseline and a no-op copy of each mutated module green. Registry:
`scripts/check_teeth_mutations.py --finding 128`.

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `registry/declared-set` | AC1 | none (the registry against the spec's six events) |
| `registry/delivery` | AC1 | `report-completion-handler-omitted` |
| `registry/committed-sources` | AC1 | `report-before-since`, `report-source-uncorrelated` |
| `content/completed` | AC2 | `report-complete-from-build-only` |
| `content/running` | AC2 | `report-running-from-current-state` |
| `content/awaiting-decision` | AC2 | `report-presentation-unlinked` |
| `content/gate-rejected` | AC2 | `report-gate-rejected-as-passed` |
| `content/unknown-explicit` | AC2 | `report-unknown-as-running` |
| `send/refusal-recorded` | AC3 | `report-refused-marked-delivered`, `report-refusal-drops-source` |
| `recipient/owner-chat-only` | AC3 | `report-gate-bypassed` |
| `recipient/substitution-refused` | AC3 | `report-gate-bypassed` |
| `stop/no-second-notice` | threat model | `report-andon-request-reported` |
| `install/assets` | all | `report-not-scaffolded` |
| `observability/named-refusals` | all | `report-refusal-unclassed` |

## What each criterion's rows drive

**AC1.** After the activation, the suite commits one or more records of every declared event: an
objective proposed then accepted, a presented grooming request and an unpresented admission request, a
dispatch through prepared, accepted, running and exited, one that ends unknown, a build-only dispatch
that exits, a gate rejection and a review pass, an andon stop (raised, noticed, revised), a confirmed
landing, a build-only attempt with its receipts and an unconfirmed publication. One run reports exactly
the enabled sources: the set of delivered events is compared with the spec's six, each report's text is
the platform's stored message in the owner's chat, and every record keeps project, unit, run and its
source (sequence, command, record digest, entity and digest), each checked against the committed journal
row. The prepared dispatch, build-only receipts, presentation records, the revision and the andon's own
request produce nothing; one message per report reached the chat; a second run sends nothing; the
reporter's journal records write only report records and every other entity is unchanged.

**AC2.** Delivered bytes are compared with the stored records: the running report states the dispatch,
unit, station, state and worker of its committed record (the dispatch has since exited); the grooming
wait replies to its current presentation message and names it, the admission wait says no presentation
is published and links nothing; the gate rejection names the edge and its failure receipt; the
completion names the confirmed revision, the proof and the receipt, and every completion report is one
VELDO-0051's own reader derives (computed independently by the suite), while the build-only unit and the
unconfirmed publication have none. An unknown dispatch reads unknown, an exit with no status reads
unavailable.

**AC3.** Every report went to the owner's enrolled chat, the activation's chat, with one gate admission
each, and no other chat received anything. A reporter configured for another person's enrolled chat is
refused by the gate as `chat_not_enrolled`: nothing reaches that chat, the record is visibly unsent and
names its source, and no other entity changes. With the stand-in answering 403, the record is `refused`
as `channel_refused` with no message identity, listed as unsent in the metrics and not pending, a later
run sends nothing again, its source record is still the committed one and no decision or state changed.

## Checks run

Finding 128 rejects in full (14). The scaffold mutations of findings 51, 73, 75, 77 and 138 still reject.
Every suite that loads `init_scaffold.py`, plus 06 and 24, passes (35 suites).

## Stated limits

One owner per reporter and the Telegram chat channel only. Reconnect, replay, lost-send lookup and
delivery recovery are Release 2: a refused or unknown report stays unsent until a later release says how
to retry it.
