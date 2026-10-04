# Intake fixture clock diagnosis, 2026-10-03

The shared `scripts/suites/support/v73_authority.py` Bot API stand-in generated dates as
`1791000000 + tick`, starting at 2026-10-03 04:00:00 UTC, while its authority enrolled the owner
using `time.time()`. Once enrollment passed that fixed epoch, production
`Intake._member_when_sent` correctly found no key effective at the message date and refused intake;
the assignment deadline never participated in this refusal.

The measured baseline message date was `1791000018`, before the owner's key took effect at
`1791009210.3877325`. Actual `taken` contained three refusals with
`reason=unauthorized:not_member_when_sent`; `questions=[]` and `delivered_messages=[]`.
This explains a pass at 02:40 UTC and failure at 04:30 UTC without a code change, cache or shared
machine state. Temporary authorities and Bot API state are freshly created by every run.

The fix is in the shared fixture, not production: `int(time.time()) + tick` supplies dates relative
to the run. The positive tick preserves message ordering and puts the first integer platform date
after a fractional-second enrollment. Two frozen-clock probes (the old boundary plus 0.75 seconds
and 2100-01-01 plus 0.75 seconds) reject both the old epoch and a replacement future constant.
The original escaping and prompt-retention assertion is unchanged. Failures now print actual
intake results, stored questions, delivered messages and the two relevant times; setting
`VELDO_0168_INTAKE_TRACE=1` also prints these on success.

## Executed checks

All runs used the owner's clean environment, a fresh HOME under /dev/shm, and only
`python3 scripts/selftest.py --suite 86_veldo_0168_text`. No gate, whole selftest, mutation checker,
or unrelated suite was run. The dispatcher adds 26 shared setup assertions to its totals and
deliberately exits 2 for a passing partial run; failures exit 1.

| Case | VELDO-0168 rows | Dispatcher total | Exit |
| --- | --- | --- | --- |
| Original fixture, with diagnostics | 25 pass, intake/delivery fails | 51 pass, 1 fail | 1 |
| Fixed fixture, intake row alone | 1 pass | 27 pass, 0 fail | 2 |
| Fixed fixture, full named suite after restoring mutants | 26 pass | 52 pass, 0 fail | 2 |
| Send no longer escapes | 25 pass, intake/delivery fails | 51 pass, 1 fail | 1 |
| Fixed epoch restored | 25 pass, intake/delivery fails both clock and delivery checks | 51 pass, 1 fail | 1 |

In the final green suite, all three intake results are `inbox`. The stored questions say
`Which project is this for? Reply to this message with one of: project-a, literal<U+200B>.`;
the delivered question text says
`Which project is this for? Reply to this message with one of: project-a, literal<U+003C>U+200B>.`.
The first delivery also carries the real waiting-request hint. The isolated row has one incoming
message, one stored question and one delivered question.

The send mutant changes only `.veldo/control_intake.py` inside `Intake._ask`:
`prompt = render_prompt(question['prompt'])` becomes `prompt = question['prompt']`.
Intake still creates questions, but direct sends contain the unescaped literal and the original
named behavior assertion fails. The clock mutant restores only the old fixed date expression in
the shared fixture. Both mutations were removed before the final green suite run.

[intake-clock-observations.json](intake-clock-observations.json) retains the actual outcomes,
stored prompts and deliveries from all five runs, with repeated command metadata omitted.
[intake_clock_recheck.py](intake_clock_recheck.py) reproduces `row`, `suite`, `send-mutant` or
`clock-mutant` from the repository root, one case per invocation; redirect its output to a file.
For `row`, it temporarily removes the unrelated row bodies and names, retaining the real authority,
HTTP setup, clock probes, intake body and cleanup. It restores all temporary edits in `finally`
and returns the dispatcher's exit code. It must run without another process editing those files.

## Audit of every suite

Searched all of `scripts/suites`, including support files, with `rg` for fixed numeric platform
dates, calendar deadlines/expirations, and the exact `1791000000` epoch. Follow-up searches checked
`CM.admit`, `effective_at`, `Intake` and `time.time` at the matching sites. The table lists every
other fixed-date message generator found; these are static findings, not claimed suite failures.

| Suite file (under scripts/suites) | Message date locations | Clock context |
| --- | --- | --- |
| 60_veldo_0064_inbox.py | 76 | Keys seeded effective at zero |
| 62_veldo_0065_presentations.py | 74, 255 | Keys seeded effective at zero |
| 63_veldo_0066_attribution.py | 43 | Keys seeded effective at zero |
| 65_veldo_0067_edges.py | 49 | Real enrollment clock; epoch 1791000000 |
| 68_veldo_0126_intake.py | 255 | Keys seeded effective at zero; explicit historical-membership test |
| 68_veldo_0136_hints.py | 83 | Keys seeded effective at zero |
| 69_veldo_0068_settlement.py | 53 | Real enrollment clock; epoch 1791000000 |
| 69_veldo_0133_dispositions.py | 122, 395 | Keys seeded effective at zero |
| 70_veldo_0069_bindings.py | 262 | Real enrollment clock; epoch 1791100000 |
| 71_veldo_0130_api.py | 193 | Real enrollment clock; epoch 1791000000 |
| 72_veldo_0077_objectives.py | 82 | Real enrollment plus intake; epoch 1791200000 |
| 73_veldo_0078_backlog.py | 104 | Real enrollment plus intake; epoch 1791300000 |
| 73_veldo_0089_team.py | 81 | Real enrollment clock; epoch 1791300000 |
| 76_veldo_0079_grooming.py | 114 | Real enrollment plus intake; epoch 1791400000 |
| 77_veldo_0149_adopted_activation.py | 89 | Real enrollment clock; epoch 1791000000 |
| 82_veldo_0085_decomposition.py | 90 | Real enrollment plus intake; epoch 1791300000 |

The later epochs cross the wall clock on October 4 at 07:46:40, October 5 at 11:33:20,
October 6 at 15:20:00 and October 7 at 19:06:40 UTC respectively, plus each fixture's tick.
Real enrollment plus fixed message dates warrants follow-up wherever a reader compares the two;
the zero-effective-time fixtures do not reproduce this particular inversion. Isolated historical
message literals also occur at 62:1090, 63:529-530, 69/dispositions:929,955 and 70/activation:498.
Fixed assignment deadlines and other calendar-expiration literals were found as well; they are
not evidence of the measured intake failure. No unrelated suite was modified or run.

The repaired shared helper is referenced by suites 70/0073, 71/0130, 71/0138, 72/0075, 72/0128,
73/0139, 74/0140, 82/0144, 84/0169, 85/0171, 86/0168 and 86/0189, so those consumers inherit the
fixture fix. Their independent results remain for the reviewer to establish.

These are partial diagnostic checks, not a gate stamp, independent review, or landing approval.
