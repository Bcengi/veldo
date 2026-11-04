---
schema: veldo.spec/v1
id: VELDO-0238
title: Files travel both ways in a conversation, on Telegram and the UI - a turn sends files from its workspace to the owner, and files the owner sends land in the turn's workspace and its record, redacted and size-capped
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0141, VELDO-0158, VELDO-0168, VELDO-0174, VELDO-0175, VELDO-0177, VELDO-0178, VELDO-0179]
placement: [contracts, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_conversation*.py"
  - ".veldo/control_conversation*.py"
  - "engine/.veldo/control_intake*.py"
  - ".veldo/control_intake*.py"
  - "engine/.veldo/control_service_channel*.py"
  - ".veldo/control_service_channel*.py"
  - "engine/.veldo/control_telegram_report*.py"
  - ".veldo/control_telegram_report*.py"
  - "engine/.veldo/control_channel_presentation*.py"
  - ".veldo/control_channel_presentation*.py"
  - "engine/.veldo/control_execution_record*.py"
  - ".veldo/control_execution_record*.py"
  - "engine/.veldo/control_api*.py"
  - ".veldo/control_api*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "engine/ui/src/**"
  - "scripts/suites/*_veldo_0238_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0238-conversation-files-in-and-out.md"
  - "specs/index.md"
  - "proof/VELDO-0238/*"
behavior_bearing: true
observability:
  logs: >
    Record each file in and out with its conversation, turn, direction, channel, name, size, digest and
    outcome (delivered, landed, over_cap, withheld), and each channel receipt (Telegram message id or the UI
    download); never file contents, a credential or a channel token.
  metrics: >
    Count files and bytes by direction, channel and outcome.
  traces: >
    Join each file to its turn, its channel message and, for an outgoing file, the turn's reply it went with.
  error_taxonomy: >
    A file over its cap is invalid_input:file_size; a name or path that leaves the workspace, or a link, is
    binding_mismatch:conversation_workspace; an outgoing file holding a value of the run's redaction set is
    refused as withheld:credential; a channel that fails to deliver or fetch is unavailable:<channel>; an
    unknown delivery outcome is unknown, never retried by itself.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a file the owner sends in a conversation lands in the turn's workspace and in the turn's record.
      Set: on Telegram a document or photo in a message that continues a conversation (a reply to one of its
      messages, VELDO-0175), and in the UI a file attached in the conversation screen's composer, are fetched
      by the factory and written to inbox/<turn>/<name> in the conversation's workspace, the name reduced to a
      safe base name (no separator, no leading dot, a numeric suffix on a clash); the turn's input names each
      path, size and type. The turn record (VELDO-0141, VELDO-0178) keeps each file's name, size and digest,
      and for a text file its content after the record's redaction (VELDO-0141 AC4); a file that is not text
      is kept in the record by name, size and digest only. Rows: in/telegram and in/ui send a CSV and a PNG
      and require both in the workspace byte for byte, the CSV's content in the record and the PNG by digest.
    falsified_by: >
      Keep the inbound text file in the record without the record's redaction, and the in/telegram row that
      sends a CSV holding a planted credential value must fail on that value in the record.
  - id: AC2
    text: >
      Claim: inbound files are size-capped before anything is fetched. Set: an inbound cap, configured in the
      factory's channel configuration with a default of 20 MB per file (Telegram's bot download limit), is
      checked against the size the channel reports before the fetch, and again on the bytes received; a
      message with any file over the cap is answered with the refusal naming the file and the cap, no file of
      it is written and no turn runs for it. Rows: cap/in sends a file one byte over a lowered cap and
      requires the refusal, nothing in the workspace and no turn.
    falsified_by: >
      Check the cap only after writing the file, and the cap/in row must fail on the file present in the
      workspace.
  - id: AC3
    text: >
      Claim: a turn sends files from its workspace to the owner with its reply. Set: at a turn's end each
      regular file in the workspace's outbox directory is sent with the turn's reply, on Telegram as a document
      (bytes unchanged) and in the UI as a download in the turn's view served only to the conversation's owner
      (VELDO-0178), then moved to sent/<turn>/ so it is sent once. Only regular files whose resolved path is
      inside the outbox are sent; a link or a path outside is refused by name and not sent. An outbound cap,
      default 50 MB per file (Telegram's bot upload limit), refuses a larger file by name in the reply. The
      record keeps each sent file's name, size, digest and channel receipt. Rows: out/telegram and out/ui
      produce a PDF and a PNG and require both delivered byte for byte and listed in the record; out/escape
      places a link to a file outside the workspace and requires it refused and nothing sent.
    falsified_by: >
      Follow links in the outbox, and the out/escape row must fail on the outside file delivered.
  - id: AC4
    text: >
      Claim: no outgoing file carries a credential the run was given. Set: before sending, each outgoing file
      is checked for every value in the run's redaction set (VELDO-0158); a file holding one is withheld,
      never altered and sent, and the reply names it as withheld:credential. Rows: out/credential writes the
      run's delivered server credential into an outbox file and requires it withheld and the channel fake to
      receive nothing for it.
    falsified_by: >
      Skip the redaction-set check on outgoing files, and the out/credential row must fail on the file
      delivered.
required_evidence: [unit, integration, ui_states]
rollback: >
  Stop fetching inbound files and sending outbound ones, then revert; text conversation is unchanged. Files
  already in workspaces and records stay. No automatic rollback is authorized.
---

## Intent

Half of the owner's work with his assistant moves files: decks, rendered pages, images, CSVs and HTML
previews out to him, and his own files in. A Veldo conversation carries text only; VELDO-0175 put
attachments out of scope until Release 4 channels. This pulls that item forward for Telegram and the UI:
files from a turn's workspace go to the owner, and files he sends land in the turn's workspace and its
record, redacted and size-capped.

## Context

- A conversation's turns run in its own workspace (VELDO-0177 AC1); each turn's run is kept in its
  execution record, redacted, and served only to the conversation's owner (VELDO-0141, VELDO-0178).
- Telegram messages are acquired by the service's channel pass and decided by intake (VELDO-0175); replies
  are sent as written (VELDO-0168).
- VELDO-0242 (a separate draft) delivers approved rendered files to the owner through an installed file
  delivery; this spec is that delivery for conversations.
- The owner's parity report (kept in the owner's installation), kinds 16 to 19, 24 and 31, ticket T5.

## Out of scope

Channels other than Telegram and the UI; files in project units; a file store beyond the workspace and the
record; sending files to anyone but the conversation's owner; editing sent messages. The /attach command
stays the project attach of VELDO-0177 AC3.

## What the reviewer judges

- Normal use: the owner sends a CSV and gets back a chart PNG and a PDF in the same chat.
- Threat model: a turn exfiltrating a credential or a file outside its workspace to the chat; an oversized
  upload filling the disk; a secret the owner pasted into a file kept unredacted in the record.

## History

- 2026-11-04: drafted from the Veldo parity report, ticket T5, under the owner's decisions to move the work
  to Veldo (Telegram 39047, 39049) and that Veldo runs non-software projects (Telegram 39067, lifting
  PLAN-0019 NG3). Not implemented; the owner approves it before it is claimed.

2026-11-04: approved by the owner, Telegram 39096 ("Yes covers both", to 39089-39092 asking approval of VELDO-0236 to VELDO-0249, the PLAN-0019 amendment and the connectors plan). Status ready.
