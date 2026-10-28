# Decisions

Routes `/decisions` and `/decisions/<request>`. Reads `reads.decisions`, reduced by
`features/decisions/inbox.ts` to pending requests with their current published presentation. Answers
through `decisions.answer` (see [../ui/decision.md](../ui/decision.md)).

Wide (1024 px and up): the inbox beside the open decision. Narrower: one at a time, with a back link.

States: loading, empty ("Nothing is waiting on you"), error (the read's refusal), a decision that is not
pending or not in scope (`missing_evidence:not_pending_or_out_of_scope`), and per answer: sending,
answer sent, or the refusal beside the action: `stale_version:stale_presentation`,
`stale_version:request_closed` (answered in Telegram first), `unauthorized:not_owner`,
`invalid_input:missing_rationale`.
