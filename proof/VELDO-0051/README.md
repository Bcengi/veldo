# VELDO-0051 proof

Canonical event vocabulary and journal-derived publication, PLAN-0019 revision 3 W36 (Release 1
stage 1). Branch `build-veldo-0051`, built on the merge of origin/main at 8231708 (origin/main is
still da9127b, so the second merge was a no-op). The specification stays **ready**. This is
implementation evidence, not independent review, owner approval or a full-gate result; the lead runs
`bash scripts/verify.sh`.

## What landed

**`.veldo/control_event_vocabulary.py`** (standard library, no I/O) is the one registry of event
types. It holds 32 types, each with the producer that owns it and the file that producer's code lives
in (9 producers), plus the schema spellings: `veldo.event/v1` is written, and the historical spelling
is accepted and kept split in the source. `line_problems()` names why one line is not a valid
envelope. Before this change the emitter held 31 types and the validator its own 21, so the validator
refused the `run.*` milestones the emitter wrote.

**`.veldo/events.py`** takes its types and schema from the registry. Two types are now
projection-owned: `verdict.recorded` (the review projection) and `spec.shipped` (the journal
projection). A hand emission of either is refused whatever `--producer` says, and a hand line may not
declare either projection's producer. A line written on a projection's own append path must carry
that projection's producer. `refuse_substitution()` refuses a line whose type is not the type `emit()`
was asked for (an `extra` or `--field type=` naming another type). `append_journal_projection()` is
the journal projection's append path and admits only its own types.

**`.veldo/validate.py`** loads the same registry, so `check_events` recognizes exactly the
producers' types and both schema spellings.

**`.veldo/control_event_projection.py`** reads one store's journal read-only, walks every committed
record in order, and publishes `spec.shipped` into one repository's `.veldo/events.jsonl` only for a
`revision_landed` completion receipt that passes all of these:

- `completion_contract.fact_problems` and `landing_receipt_problems`, the predicates the Gate's
  completion reader applies;
- it names a unit of the projected repository;
- its dispatch is a publication already committed in the journal, for the same unit, domain and
  repository;
- that publication completed with every destination at the tip;
- its commit and old tip are the receipt's candidate commit and old remote tip.

Any other receipt is refused by name and observed. The event id is keyed to (domain, repository, unit,
dispatch), and the event carries the journal sequence, command and record digest. After appending,
the projector stores the watermark (last sequence and its record digest) in
`.veldo/events.watermark.json`. Store, domain, repository and destination are explicit arguments.

**`.veldo/init_scaffold.py`** lays both new modules. The vocabulary is `REQUIRED_SUBSTRATE`, because
the validator loads it. All five modules have byte-identical `engine/.veldo` copies.

**Suite 11** (`11_inbound_command_receipt_reconcile`): its WARP-1208 row pinned the validator's set
as an exact list. It now requires the previously recognized set to be kept, as an inclusion.

**The spend recorder, a landed producer this change broke (review fix).** `.veldo/spend.py`
(WARP-0733) wrote each spend record as a hand-emitted `spec.shipped`. Once `spec.shipped` became
projection-owned, every record was refused: `spend.py record` exited 1 where it exited 0 at 8231708,
and spend actuals stopped being recorded. Spend is not completion, so spend has its own type. The
vocabulary registers `spend.recorded`, owned by `spend.py` (producer string and file). `spend.py`
writes it with that producer and declares `spec.shipped` as the historical type of its earlier
records, which stay valid under that spelling. No hand path to `spec.shipped` is reopened.

**The readers of spend actuals.** Each one was checked for the event type it reads. Only
`.veldo/judgment_load.py` keys on it: its kind map now puts both `spend.recorded` and the historical
`spec.shipped` in `ship_bulk`. Without that, a new record's minutes would land in `other`. The rest
sum `tokens`, `cost_usd` and `human_minutes` whatever the type, so they read both types unchanged:
`toe_corpus.spend_for` and everything built on the corpus (`toe_normalize`, `toe_analogy`,
`toe_reconcile`, `toe_budget`, `cost_to_change`), `metrics.compute` and the budget and governor
readers, `sizing_pass.ledger_state` and `scripts/check_first_use.py`. `sizing_pass.record_self_cost`
records through `spend.record`, so it now writes `spend.recorded` too.

**Suites 01 and 1407.** Suite 01's WARP-0733 row drives `spend.record` through an injected emitter.
That emitter admits any type, which is how the refusal stayed hidden, so the row now also requires
the type to be one the real writer admits (in the vocabulary, owned by no projection). Suite 1407's
drift guard follows the recorder to `spend.recorded` and requires the historical type to stay in
`ship_bulk`.

## Rows (suite `66_veldo_0051_events`, 11 rows: 8 criterion rows and 3 `ran/` rows, 37 assertions with the preamble)

The suite uses a real SQLite store with OpenSSH journal signatures. It works in a destination
repository laid by the installed scaffolder, which runs its own gate and push guard. Four real pushes
go to bare remotes through the VELDO-0028 effect executor. The installed emitter CLI, executor hook,
review projection and validator each run as separate processes.

| AC | Row | What it observes |
|---|---|---|
| AC1 | `events/vocabulary-roundtrip` | The registry, the vocabulary's and the emitter's sets are equal. Every producer registration (events.py, runlog.py, incident.py, request.py, verify.sh, veldo-guard.sh, spend.py) lies inside the registry, the spend recorder's type is registered to the spend recorder itself, and every owner's file exists. The journey is the 26 types whose owner file the scaffolder lays, and it includes `spend.recorded`. Each of them is written by its registered owner: hand types through the installed CLI, the executor's three through its hook, `spend.recorded` by the installed `spend.py record`, `emergency.push` by the push guard in the emergency lane, the gate's two by the laid gate, `verdict.recorded` by the review projection over a committed verdict, and `spec.shipped` by the journal projection. The combined JSONL carries both schema spellings, and the installed validator passes it in another process (exit 0). |
| AC1 | `events/unknown-refused` | The CLI refuses an unknown type, an unknown schema and `--field type=gate.passed` (exit 2, log unchanged). In process, a type substituted through `emit(extra=)` or the executor hook is refused `type substitution`. A control line lands. The validator refuses an unknown type and a bad schema by name (exit 1). |
| AC1 | `events/spend-recorded` | The installed `spend.py record` runs in another process through the real emitter and exits 0. Exactly one line is appended: `spend.recorded`, producer `spend.py`, carrying the spec, the three figures, the basis and the note, and the id the CLI printed. A record with no figure is still refused (exit 1) and appends nothing. The installed validator passes the new line beside two historical `spec.shipped` spend lines, one in each schema spelling, in another process (exit 0). The corpus (`toe_corpus.spend_for`), the judgment axis (`judgment_load` tokens and minutes by kind) and the budget reader (`metrics.compute`) each read the new line, the historical lines and both together, with the exact figures, and the judgment axis puts every minute in `ship_bulk`. |
| AC2 | `events/projection-prefix` | The CLI publishes up to the explicit head (31). It appends exactly the two confirmed landings (sequences 16 and 31) in journal order, joined by type, unit, dispatch, sequence, command, record digest and receipt, and stores watermark 31 with that record's digest and coordinates. A second publish from the stored watermark to 38 appends exactly the next landing. The historical-spelling line and every earlier byte stay a prefix. The log holds 3 distinct ids. |
| AC3 | `events/confirmed-landing-only` | Three publications complete at the origin's tip. The one the hooked remote rejects is `unknown` and leaves that remote unchanged. `spec.shipped` exists exactly for U1, U2 and U4, each bound to its dispatch, candidate commit, spec, domain and repository. The other receipts are refused by name: a receipt naming another unit's dispatch (`stale_subject:dispatch/unit`), a dispatch not in the journal (`missing_authority:dispatch`), the rejected push (exactly `unknown_outcome:publication`), and no remote confirmation (`missing_evidence:receipt/remote_confirmation` and `missing_evidence:landing/remote_confirmation`). A second receipt for U2's landing is counted as 1 duplicate and not republished. The same journal under another repository's coordinates publishes nothing, with every receipt refused `missing_authority:repository`. |
| AC3 | `events/completion-owner` | U0's build-only attempt has an exited dispatch, `attempt_finished` and `artifact_accepted`, and the executor records `proof.recorded`. The CLI refuses a plain `spec.shipped`, one through `--field type=`, and a hand line that declares the projection's producer (exit 2). In process, `emit`, `emit(extra=)` and the executor hook are refused. The log bytes are unchanged, and nothing for U0 is judged or projected. |
| (Notes) | `events/installed-assets` | The scaffold lays the eight modules the journey loads, each byte-identical to its engine template. The vocabulary is required substrate and the projector is created. The laid gate goes green, then red on a failing check. The laid validator passes a historical-spelling line. The laid projector answers `unavailable_service:store` for an absent store. |
| (obs.) | `events/observations` | There is one `project_receipt` observation per receipt (8), each with operation, domain, repository, unit, request, receipt, dispatch, accepted versions, outcome and sequence. The 4 refusals each carry a code and its taxonomy class, and together they cover four classes. The `publish` observations are at watermarks [31, 38]. Before the second publish, `status()` shows watermark 31, head 38, 7 pending records and exactly the one pending event, and 0 and none after it. An unnamed code classifies as `unknown_outcome`. No key path or key text appears. |

`observations.json` (from `drive.py`) holds one unmutated run.

## Red at the pre-change code

`red.py <commit>` runs the current suite with every production anchor (events.py, validate.py,
init_scaffold.py, spend.py, judgment_load.py and the two new modules) pointed at the commit's own
bytes, and every other installed module and engine template written from `git show <commit>`. A
module the commit lacks is replaced by a marked stand-in in `prefix/`. Both records below were
written over the final suite text.

**At 8dba446 (`red-8dba446.json`, the build before the spend fix), exactly two rows fail by
assertion: `events/vocabulary-roundtrip` and `events/spend-recorded`. The other six criterion rows
and all 3 `ran/` rows pass, and nothing raised.** 171 installed modules and 328 engine template
files come from the commit, and nothing is substituted. What it observed:

- `spend.py record` exited 1 with the writer's refusal (`'spec.shipped' is DERIVED, never
  emitted`) and appended nothing, so every reader read no spend from the new record.
- The spend recorder registers `spec.shipped`, which the registry gives to
  `control_event_projection.py`, and `spend.recorded` is not in the registry or the journey.
- The validator passed the historical `spec.shipped` spend lines, which stayed valid.

**At 8231708 (`red-8231708.json`, before VELDO-0051), all 8 criterion rows fail by assertion, all 3
`ran/` rows pass, and nothing raised.** 169 installed modules and 326 engine template files come from
the commit. The two modules the commit lacks are stand-ins: the registry the suite enumerates, taken
from the current module and loaded by nothing at the commit, and a projection that derives nothing.
What it observed:

- The validator refused `run.aborted`, `run.blocked`, `run.done`, `run.resumed` and `run.started`,
  all written by the emitter.
- `--field type=gate.passed` landed a `gate.passed` line, and both in-process substitutions landed.
- A direct `spec.shipped` after the build-only run landed through the CLI and through
  `--field type=`, and a hand line declaring the projection's producer landed too.
- Nothing projected the journal, and no watermark was stored.
- `spend.py record` exited 0 and wrote its record as `spec.shipped` with producer `events.py`, so no
  `spend.recorded` line existed for the readers.

## Mutations (finding 51, 22 registered in `scripts/check_teeth_mutations.py`)

`mutations.py` drives them and writes `mutations.json`, with each exact edit in `mutations/`. Every
mutation reds its named row by assertion, **no `ran/` row goes red**, and the unmutated control is
green with 37 assertions. The declared falsifiers:

- **AC1:** `events-validator-forgets-run-done`. The validator drops `run.done` while the emitter
  still writes it.
- **AC2:** `projection-skips-committed-event`. The first fresh event is dropped while the watermark
  still advances.
- **AC3:** `events-direct-spec-shipped`. `spec.shipped` is removed from the projection-owned set, so
  it can be emitted by hand after a build-only run.

The spend fix adds four:

- `spend-records-as-spec-shipped` puts the reported defect back: `spend.py` writes its record as
  `spec.shipped`. It reds `spend-recorded` and `vocabulary-roundtrip`.
- `vocabulary-forgets-spend-recorded` drops the spend type from the registry, so a producer is
  missing from the vocabulary. It reds `vocabulary-roundtrip` and `spend-recorded`.
- `judgment-spend-recorded-unkinded` and `judgment-historical-spend-unkinded` each drop one of the
  two spend types from `judgment_load`'s kind map, so those minutes land in `other`. Each reds
  `spend-recorded`.

| Row | Mutations |
|---|---|
| vocabulary-roundtrip | validator-forgets-run-done, emitter-forgets-run-done, historical-spelling-dropped |
| unknown-refused | substitution-admitted, unknown-schema-validates |
| projection-prefix | skips-committed-event, rewrites-history, watermark-unbound |
| completion-owner | direct-spec-shipped, vocabulary-spec-shipped-hand-owned |
| confirmed-landing-only | dispatch-unit-unjoined, confirmation-unrequired, duplicate-republished |
| installed-assets | scaffold-vocabulary-not-laid, scaffold-projection-not-laid |
| observations | refusal-unobserved, unknown-taxonomy-classified, pending-unlisted |
| spend-recorded | spend-records-as-spec-shipped, vocabulary-forgets-spend-recorded, judgment-spend-recorded-unkinded, judgment-historical-spend-unkinded |

## Costs

- **Suite 66:** 3.7 s inside selftest (3.66 s in the normal shell, 3.73 s under the stage
  environment), against the 60 s limit. The spend row added about 0.5 s.
- **Mutation driver:** finding 51 with `--jobs 4` takes 22.6 s in the normal shell and 23.1 s under
  the stage environment, for 22 mutations.
- **Gate:** the mutation stage will run these 22 at about 3.7 s each, roughly 80 worker seconds. That
  stage was not run here.

The suite passes, and all 22 mutations are rejected, under the gate's mutation-stage environment as
well: `env -i`, PATH set to a directory holding only a python3 link followed by `/usr/bin` and
`/bin`, a temporary HOME and TMPDIR, and no global Git configuration.

## Not done here, stated

- **Owners the scaffold does not lay.** `incident.closed` (incident_reconcile.py) and the request
  lifecycle with `decision.decided` (request_reconcile.py) are registered and recognized. The
  scaffold lays neither file, so they fall outside the enabled journey and the round trip does not
  drive them.
- **Emitted types.** For a type that is not projected, the `producer` field only describes the
  source. The writer does not judge that string (Notes).
- **Spend is no longer completion.** At 8231708 a spend record was a `spec.shipped` line, so it also
  counted as a ship: cycle time, the tracker mirror's shipped status, an emergency debt's closure
  and the entropy map's cost samples (which count a change once `spec.shipped` exists). A
  `spend.recorded` line counts for none of those; its figures still join the change's totals, and
  the change counts as shipped when its projected `spec.shipped` exists. Historical spend lines keep
  their old reading, because they are `spec.shipped` lines in an append-only log.
- **Trigger.** Nothing runs the projector after a landing or on a schedule. It runs when called
  (`publish` or `status`). With a hand `spec.shipped` refused, an emergency debt closes through
  `emergency.closed` or a projected `spec.shipped`.
- **Refusals no row drives.** The code refuses a stored watermark that names another journal record
  (`stale_subject:watermark`), an out-of-range `--upto` and a held lock, but no row exercises them.
- **Fixture records.** The suite writes units, the build-only attempt's records, completion receipts,
  effect contracts and permissions with the store's generic command. Their services (VELDO-0050,
  VELDO-0057, permission issuance) are not re-proved.
- **Later releases.** Several projectors, two clones, replay after a crash between the append and the
  watermark (only an id already in the log is skipped) and replica-failure recovery are Release 2.
  The multi-repository matrix is Release 4.
- **Not run:** `verify.sh` and the Mac.
