# Decisions

Routes `/decisions` and `/decisions/<request>`. Reads `reads.decisions`, reduced by
`features/decisions/inbox.ts` to pending requests with their current published presentation and ranked
by deadline urgency, then risk, then deadline. Answers through `decisions.answer` (see
[../ui/decision.md](../ui/decision.md)).

Wide (1024 px and up): the ranked inbox beside the open decision, exactly the viewport's height, each
scrolling on its own; the open decision shows its due time and risk badge, the question, the risk
statement in its own box, the choices, the rationale field and the answer action, in that order; with nothing picked, the most urgent decision opens (the route becomes its
address). Narrower: one at a time, with a back link.

States: loading, empty ("Nothing is waiting on you"), error (the read's refusal), a decision that is not
pending or not in scope (`missing_evidence:not_pending_or_out_of_scope`), and per answer: sending,
answer sent, "This question changed since you opened it" (a newer version in the store), or the refusal
beside the action: `stale_version:stale_presentation` (then "Load the current version"),
`stale_version:request_closed` (answered in Telegram first), `unauthorized:not_owner` (a member it was
not presented to), `unauthorized:out_of_scope` (a member whose scope no longer covers the request's
project), `invalid_input:missing_rationale`.

## A Keep answer to a space request (VELDO-0319 AC5)

A space request offers `accept save`, `accept keep` and `accept discard`, and for a review group the same with
a member's letter and index (`accept keep w2`). Save and Discard are finished by the settlement. Keep is not:
the ledger takes it only as the owner's own signed command. So when the owner picks a Keep answer and presses
Send answer, the screen (`features/decisions/DecisionDetail.vue`, with `features/space/keep.ts`):

1. reads `space.pending` and finds the worktree the answer names: the deferred item whose own request is this
   one, for a member pick the member with that index;
2. builds the ledger's Keep command for that item at the version the read shows and runs one passkey ceremony
   over its digest. A ceremony that does not finish sends nothing: "Keep was not signed, so no answer was sent.";
3. sends the answer through `decisions.answer`, unchanged;
4. once the answer has settled, sends the signed packet on `space.keep`.

One press, two commands. The result says "Your passkey signed the Keep and the ledger marked the worktree Keep."
only when the API said so. When the ledger refuses the packet (for example `stale_version:space_item`, because
the item's version moved while the answer was being given) the answer stands and the screen says the Keep is not
applied yet, with the refusal's name and a link to the Space screen, where the worktree is listed with Sign Keep
([space.md](space.md)). An answer that is not Keep, and a Keep to a request that is not a space request, are
sent as any other answer and no ceremony runs.
