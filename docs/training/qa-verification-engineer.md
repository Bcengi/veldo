# QA in Veldo: the Verification Engineer

*Training series. The most transformed role in the building, and the one Veldo cannot run without.*

*Version 1.0, 2026-07-16*

## 1. Your job, redefined - and the honest part first

Manual test execution is gone. Clicking through regression checklists, writing test plans nobody reads, being the last gate before release and the first person blamed after it: all of that is over, and it is right to say so plainly rather than pretend the role is unchanged.

Here is what is equally true: Veldo's entire premise is that verification is the bottleneck, which makes verification the discipline the whole method runs on. The judgment you built finding what breaks - the instinct for the edge case, the user path nobody designed for, the "what if I do this twice" reflex - is the scarcest skill in the new system. It just stops being spent one manual click at a time and starts being spent three ways: criteria quality (bugs prevented at spec time), verification engineering (the gate as a product), and exploratory judgment (the human review lane machines cannot fill).

| What stops | What starts |
|---|---|
| Executing manual test passes | Owning the gate: the checks, their depth, their speed, their zero-flake standard |
| Writing test plans as documents | Writing acceptance criteria with the PM: every plan is now criteria the machine runs forever |
| Being the release bottleneck | Being the reason the gate can be trusted enough to merge on green |
| Finding bugs after implementation | Preventing them at spec time: your "what breaks" instinct applied to intent |
| Regression checklists | Exploratory testing as a review lane on risky changes: recorded findings, same verdict contract |

## 2. Your day

The gate is your product and you read its health like a dashboard: first-pass rate, flake count (target: zero, always), escaped defects. A PM spec is missing its failure cases; you add three criteria in five minutes that would have been three bug reports in the old world. A high-risk change requests the exploratory lane, so you spend an hour trying to break it the way only you can, and your findings land as a verdict file. An escaped defect from last week becomes a permanent check by end of day.

## 3. Your moments in the loop (exact)

**Criteria partnership (before implementation, where you now live):**

```
VELDO-0231 is missing the ugly paths. Add: AC5, a second rapid submit does not
double-pause; AC6, a payment succeeding DURING the pause flow un-pauses
cleanly; AC7, the paused state survives a webhook retry storm.
```

**The exploratory lane (on request or by policy for risky surfaces):**

```
Record my exploratory review for VELDO-0240: FAIL. Reproduced: switching
accounts mid-checkout keeps the old account's coupon. Steps attached.
Also two non-blocking oddities in the error copy.
```

Your findings are a verdict file bound to the commit; the failure returns the change to implementation with your reproduction as a new criterion.

**Gate stewardship:**

```
/veldo:spec Quarantine and rewrite the flaky payment-webhook test: it failed
3 times this week on timing, not behavior. Flakes are production defects
of the proof system.
```

**The escaped-defect ritual:** every bug that reaches production proves a missing check. You own the ritual: reproduce, criterion, check, done - the same bug is now impossible, permanently.

## 4. The curriculum

**Module 1 - From plans to criteria.** Take your best old test plan. Convert every case into an acceptance criterion a machine can decide. What cannot be converted (true exploratory judgment) is your review lane; notice how little of the plan that is, and how much sharper it makes the remainder.

**Module 2 - Gate literacy, then gate ownership.** Learn verify.sh end to end: what each check proves and what it cannot. Exercise: find the gap (a bug class no current check catches), demonstrate it with a planted bug, close it with a new check.

**Module 3 - The zero-flake standard.** A flaky check teaches the team to bypass; it is worse than no check. Exercise: take one intermittent test and make it deterministic or kill it, and write one paragraph on which was right and why.

**Module 4 - Exploratory testing as evidence.** Your instinct, recorded. Exercise: one hour against a sandbox change, findings written as a verdict with reproductions; then the harder half: turn your two best findings into standing criteria so the machine holds them forever.

**Module 5 - Proof skepticism.** Exercise: five proof manifests, one satisfied in letter but not intent. Find it faster than the backend developer does. (You will. This is your muscle.)

## 5. How you break Veldo without meaning to

- **Rebuilding the manual gate.** Inserting yourself as a sign-off on ordinary green changes recreates the queue Veldo deleted, and it will be routed around, and then your judgment is absent where it mattered.
- **Letting flakes live.** Every tolerated flake is a lesson to the team that red is negotiable.
- **Keeping findings verbal.** A bug mentioned in chat evaporates; a criterion holds forever. If it is not in the spec, the gate, or a verdict, it did not happen.
- **Testing the implementation instead of the intent.** Your lane judges whether the INTENT survives contact with reality, not whether the code matches the spec (the machine already proved that).

## 6. You have arrived when

- The gate's first-pass rate is trusted enough that nobody asks for a manual pass anymore, and that fact is because of you.
- A PM asks for your criteria before writing a spec, not your testing after.
- Your exploratory lane caught something both the implementer and the fresh-context reviewer missed, and its reproduction is now a permanent criterion.
- Zero flaky checks for a full quarter.
- Your title stopped mattering to you: the proof system is yours, and everyone knows it.

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-16 | Initial training document |
