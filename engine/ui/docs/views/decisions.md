# Decisions

Routes `/decisions` and `/decisions/<request>`. Reads `reads.decisions`, reduced by
`features/decisions/inbox.ts` to pending requests with their current published presentation and ranked
by deadline urgency, then risk, then deadline. Answers through `decisions.answer` (see
[../ui/decision.md](../ui/decision.md)).

Wide (1024 px and up): the ranked inbox beside the open decision, exactly the viewport's height, each
scrolling on its own; with nothing picked, the most urgent decision opens (the route becomes its
address). Narrower: one at a time, with a back link.

States: loading, empty ("Nothing is waiting on you"), error (the read's refusal), a decision that is not
pending or not in scope (`missing_evidence:not_pending_or_out_of_scope`), and per answer: sending,
answer sent, "This question changed since you opened it" (a newer version in the store), or the refusal
beside the action: `stale_version:stale_presentation` (then "Load the current version"),
`stale_version:request_closed` (answered in Telegram first), `unauthorized:not_owner` (a member it was
not presented to), `unauthorized:out_of_scope` (a member whose scope no longer covers the request's
project), `invalid_input:missing_rationale`.
