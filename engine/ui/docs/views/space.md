# Space

Route `/space` (VELDO-0319). In the factory group of the rail. Reads `space.pools`, `space.usage`,
`space.pending` and `space.removed`, live ([factory.md](factory.md)), `reads.decisions` when a request is open,
and `reads.contract` once. Acts through `space.reconcile`, `space.abandon` and `space.keep`
(`src/api/actions.ts`).

Where the space is and what Veldo is about to do with it. Every figure is a record of the space ledger, summed
and worded by the API (`control_api_models`: `space_usage`, `space_pending`, `space_removed`, `space_pools`);
the screen adds nothing up and measures nothing. The four reads are taken one after another and the journal is
followed from the first one's watermark, so any later record re-reads all four. No timer reads anything.

## Sections

| Section | Shows |
|---|---|
| Pools | One card per pool: its floor, what is held on it (the admitted and the advised holds, each need less what the run's own items already use), its type and host. Under it the runs waiting for space and, in report mode, the runs that would have waited (started on advice), each with need, free, held and floor as the ledger recorded them when the run was judged. A run a dispatch carries links to it; a waiting run has no dispatch yet |
| Usage | Bytes and item counts by project, plain repository or "No project", then ticket, then kind, with the event each kind was measured at and a totals row. Every item that is still there counts, a deferred one too. A table on a desktop, the same rows as a list on a phone. A row whose items were never measured says "not measured", never 0 |
| Pending removal | Every due and deferred item: its reason in words ("In use by process 4412", "Uncommitted changes in 3 files"), the events that retry it, its owner and size. The worktrees of one decision request are listed under it, a review group's by index with the answers the request offers for each alone (`accept discard w2`) |
| Worktrees | Each worktree the owner can give up, with Abandon |
| Removed | The removal history, newest first: what, whose, which event and when, how much, the pool's free space before and after; for an engine pool the host figure apart; for a worktree and a private repository how many refs were kept and whether a snapshot was saved |
| Reconcile | Run a reconcile now, for one project or every project |

A pool's capacity and its free space now are on no ledger record (a pool record holds its floor), so the Pools
section shows free space only where the ledger recorded it: on a judged hold and on a removal.

## Actions

All are the owner's signed commands. The screen removes nothing itself, and a row changes only when the
ledger's record does (the journal re-reads it).

- **Reconcile now** sends `space.reconcile` with the project chosen, or null for every project. The result is
  the API's, beside the control.
- **Abandon** asks for an inline confirmation and sends `space.abandon` with the item and the version shown.
  The answer says what was removed, what was deferred and which worktrees stay until the owner's Discard, which
  saves first: Abandon removes no unique work.
- **A decision request** is answered on the Decisions screen ([decisions.md](decisions.md)), through the
  settlement the request already uses: "Answer in Decisions" opens it when it is among the decisions waiting on
  the member and has been presented; otherwise the screen says why it cannot be answered here.

- **Sign Keep** (AC7). Keep is the one answer the settlement cannot finish alone: the ledger takes it only as
  the owner's own signed command. A Keep that settled and was not applied (the item's version moved, the packet
  did not arrive, or the answer came over a channel that cannot sign, such as the phone's message channel) is
  listed under Pending removal with the tag "Answered Keep, not signed" and the button Sign Keep; its request
  card says "You answered Keep. It is not applied until your passkey signs it." Sign Keep builds the ledger's
  Keep command for the item at the version shown, naming the item's own request (`request_id`; for a member of
  a review group the alias the member kept when the group moved on), runs one passkey ceremony whose challenge
  is SHA-256 of the command's canonical bytes (`features/space/keep.ts`), and sends the packet on `space.keep`.
  The ledger verifies the passkey itself. The ceremony is limited to the session's credential and uses the
  relying-party id the pending read names (`signing`); where the read names none, the button is replaced by
  "This installation takes no passkey-signed Keep; sign it at the host." A ceremony the owner closes sends
  nothing and says so.

Confirm (VELDO-0320), Wrong and the mode switch (VELDO-0332) and Adopt (VELDO-0315's ledger command, with the
Reports section) are not on this screen: each of those tickets adds its own control with its command.

## States and refusals

Loading (row skeletons), empty ("The space ledger holds nothing yet", with Reconcile), error (the named refusal,
Try again when retryable), ready. Each section has its own empty line.

A refusal is named beside the control it concerns, with its name in `data-refusal`:
`unauthorized:not_owner` for a member who is not the owner of the space ledger (a project owner whose scope
covers the space scope), `stale_version:space_item` when the worktree's record moved after the screen read it,
`unavailable_service:space_ledger` when the authority has no space ledger. For Sign Keep also:
`unauthorized:not_authorized` (the ledger did not find the owner's passkey behind this command),
`missing_evidence:space_disposition_unsettled` (the request has no settled answer),
`invalid_input:space_disposition_choice` (the request settled as Save or Discard),
`stale_version:space_disposition_state` (already applied), and `not_signed` when the ceremony did not finish.

A member whose scope is not the whole factory is served the items, holds and requests of their projects only:
no plain repository and no "No project" row. Pools are the installation's and are shown to every member.

The API redacts what its secret scanner finds in a view. An item's identity is kept, and its path is judged
part by part, so a long path is served and only a part that looks like a credential is replaced.

Usage figures and their column headers share a right edge on desktop. The browser row
`ac1/numeric-alignment-1440` checks text bounds in light and dark, including the totals row.

Removal order comes from the sequence stamped by the Ledger at removal, with its time read by
publication key. A legacy record without that stamp stays visible with unknown order and time.
The dispatch link uses the hold index; neither read scans history.
