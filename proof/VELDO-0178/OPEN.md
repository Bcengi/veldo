# VELDO-0178: open items

## 1. RESOLVED by the lead (footprint widened, header change applied): AC2 header binding, formerly outside the footprint: `engine/.veldo/control_launch.py` (and its synced copy `.veldo/control_launch.py`)

AC2 requires that "the record's header naming the conversation id and turn sequence". The record's header line is
written by `control_execution_record.Recorder` (inside the footprint) from the `header` mapping the launch receiver
builds in `control_launch.Receiver` (`header = {'dispatch_id': ..., 'unit': ..., 'station': ..., 'project': ...,
'account': ..., 'host': ...}`, about line 1195). That mapping carries the conversation id only as `unit` and does not
carry the turn sequence at all, and nothing the Recorder is handed (the header, the run's resolved values, the hint
sockets) holds the sequence. So the header cannot name the turn inside the footprint.

What is built inside the footprint: `control_execution_record.binding(header)` and the Recorder write `conversation`
and `turn` into the header whenever the mapping it is handed names a conversation turn (its `subject_kind` and
`source`, or `conversation` and `turn`). The fallback path that already hands the Recorder the whole contract
(`_record_commitment`, a receiver with no record) binds them today. The authority (`control_api_authority.record`)
refuses a record whose header names another conversation or turn than its contract (unknown_outcome:record_binding)
and serves the run's conversation and turn from the contract.

The exact change outside the footprint is `proof/VELDO-0178/control_launch-header.diff`, two lines after the header is
built:

    # VELDO-0178: a conversation turn's record header names its conversation id and turn sequence.
    header.update(ER.binding(dict(contract)))

A project run's header is unchanged by it (`binding` returns {} for any run that is not a conversation turn).

Until it is applied, suite 133's row AC2/header is red (15 of 16). With it applied to the checkout for the run and
restored after, suite 133 is 16 of 16 (suites.txt). The falsifier runs (falsifiers.txt) and the three mutation runs
(mutation-*.txt) were made with it applied the same way, because the gate's driver requires a wholly green baseline.
To land it: widen the footprint with `engine/.veldo/control_launch.py` and `.veldo/control_launch.py` and apply the
diff to both.

## 2. The mutation cases are registered; suite 133 needs no systemd user manager

`scripts/check_teeth_mutations.py` is in the footprint. The four finding 178 cases ran in the confined leg (each
receipt's legs are `confined`), so nothing is needed for `scripts/gate_unconfined.json`.

## 3. The API service's conversations root

`control_service_api.ServiceApi` now hands the judge a `control_conversation.Conversations` on the service's
connection. A conversation the API opens keeps its directory under the API configuration's optional `state_root`
(the factory state root), else beside the store. The service's own conversations resolve their root from the service
configuration's `state_root`, its conversation receiver's, else beside the store, which the API process cannot see.
On an installation whose state root is not the store's directory, the API service configuration should name
`state_root`; that file is written by `control_factory_setup_api.py`, outside this footprint. A conversation's turns
read its workspace and sessions from its own record, so a conversation opened under either root runs; only where its
directory lives differs.

## 4. Seen, not this change's

- Suite 113 (`113_veldo_0145_ui`) row ui/route-trace is red at the base b153dea1 as well: `messages.send` gained its
  optional `conversation` field in VELDO-0175 and the UI's `engine/ui/src/api/routes.json` does not list it. The UI
  is VELDO-0179's.
- Suite 86's live/claude and live/codex are the stale live captures the lead retakes.

## 5. Decisions to review

- The served refusal for another member reading a turn's record is `missing_authority:conversation_owner` (403, as
  `unauthorized:missing_authority:conversation_owner` at the API, the class prefix the API adds to every refusal whose
  head is not a class), the name AC1 gives the conversation reads; a run with neither a project nor a conversation is
  `unauthorized:out_of_scope`, as a project run outside the reader's scope is. An unknown run keeps its pre-change
  answer (out of scope to a member whose scope is not universal, else missing_evidence:unknown_run).
- Owner-only applies to a conversation's records wherever the reader scope decides: the event feed (also for a
  universal-scope reader, whose feed was unfiltered before), and the read models, where a conversation turn's
  dispatch (`dispatch`, `dispatch_active`) is now the owner's alone in the workers read. Fix round 1 extends this to
  every record of a turn's run and intake: the released index, the turn's reservations (also on the spend read, where
  a universal reader no longer sees a conversation's worker and invocation slots or its unit and project policies)
  and the turn's intake source or a reading proposed in it.
- `conversations.open` takes an optional `role`; the new conversation's id is derived from the API request id and its
  intake digest is the assertion's digest. Every conversation command's journal command id is the API request id,
  which the API's observation of the call carries, so a route call joins the command it sent.
- The four commands are actions of the UI contract (`control_api_models.ACTIONS`), as suite 71 requires of every write
  route; the routes form a new `conversations` family, which suite 71's family row now lists.
