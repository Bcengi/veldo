# AC3 approval record

The earlier request for an uncommitted draft was superseded by the owner's approval:
"approve 0153 push rule" (Telegram 33063, 2026-10-10).
Commit 49ed8bfd already added AC3 alone and quoted that approval in its message.
The authoritative criterion is specs/VELDO-0153-identity-push-profile-and-remote-owner.md:91.
This file records the requested draft shape, now approved; it does not amend the criterion.

Claim: Every identity push runs no hook from the clone and goes to exactly the one
GitHub URL accepted by the owner check.

Set and completeness: Disable clone hooks through the private hooks directory and
the push's no-verify option. Address publication and confirming listings to the checked
literal URL. Refuse clone url rewrites, pushInsteadOf and URL-named remote overrides,
including pushurl and AGit fan-out, by name before network writes. Ignore unrelated
remote sections and legacy routing files when using that literal URL. Keep the safety
checks for old tips, ref creation, destination state, output framing and clean exits.

The superseded VELDO-0028 rows are publication-pre-push-hook,
publication-url-rewrite, publication-records-resolved-destination,
publication-destination-despite-hook-text, publication-rejected-destination-recorded,
publication-completion-from-destination-state and publication-fan-out-agit-report.
The hook legs of publication-hook-text-without-newline and publication-non-utf8-output
are superseded too; their output parsing guarantees remain.

Falsifier: Enable clone hooks by removing both the private hooksPath and the push's
no-verify option. The planted pre-push hook row must fail.

falsified_by: identity153-pre-push-hook. The consumer registration
effects-push-skips-hooks now introduces that same approved defect, enabling hooks.
