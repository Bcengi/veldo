---
schema: veldo.spec/v1
id: VELDO-0308
title: "Run finished, from the receiver"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_retirement.py"
  - ".veldo/control_retirement.py"
  - "scripts/suites/*_veldo_0308_*.py"
  - "scripts/suites/142_veldo_0303_space_paths.py"
  - "scripts/suites/129_veldo_0254_canary_launch.py"
  - "specs/VELDO-0303-the-existing-removal-paths-go-through-the-safety-rules.md"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0308-run-finished-from-the-receiver.md"
  - "specs/index.md"
  - "proof/VELDO-0308/**"
behavior_bearing: true
observability:
  logs: >
    The receiver's end records the census, each removal outcome and the released hold, in that order.
  error_taxonomy: >
    A removal refused at run finished is a deferral. Run finished is not sent while the dispatch's
    containment group still has a process.
acceptance_criteria:
  - id: AC1
    text: >
      Run finished is sent only after the dispatch is conclusive and its group is empty, and the removal
      is complete before the receiver exits
    falsified_by: >
      Send it when the worker's own process exits; the row has a surviving child that keeps a file open
      under the scratch root (not its working directory), the scratch is judged while the child lives, and
      the row fails
  - id: AC2
    text: >
      At the run's end the receiver runs the census, then Signal, then releases the hold, in that order,
      and all three are written before it exits
    falsified_by: >
      Exit after Signal without releasing the hold; the row's waiting unit, which needs the released hold
      as well as the freed bytes, is still waiting after the receiver has gone, and the row fails
  - id: AC3
    text: >
      When a pending retirement's obligation completes and the retirement is carried out, the dispatch's
      deferred items are retried in that call; a sweep that finds the obligation unchanged retries nothing
    falsified_by: >
      Retry on every sweep call; the row counts retries over three sweeps with an unchanged obligation,
      finds three and fails
  - id: AC4
    text: >
      The clone obligation of a retirement closes when the clone's teardown has been handed to the
      ledger: when the teardown answers retired, and when it is refused as space_deferred, for the
      ledger then tracks the clone's items and retries them itself. The worker slot is released then. A
      teardown refused as clone_in_use keeps the obligation open and the slot held, unchanged. A sweep
      does not attempt a deferred teardown again. The clone's pins are released when the work tree's
      item is removed, whoever removes it and whenever, and not before
    falsified_by: >
      Each of these turns a row of its own red. Keep the obligation open on space_deferred: the row's
      dispatch, whose clone is left due in report mode, still holds its worker slot after the sweep,
      and the row fails. Attempt the teardown on every sweep: the row counts the run finished events
      sent for the same clone over three sweeps, finds three and fails. Release the pins at the
      teardown call only: the row has the owner's Confirm remove the work tree after the slot was
      released, finds the pin still held in the cache, and fails. Release them at hand-over: the row
      collects the cache while the work tree is deferred, finds its commit unreadable, and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The receiver sends no run finished, and the run's items stay present until another
  event ends them.
---

## Intent

A dispatch's scratch, run directory and Docker objects go when the run has finished: the dispatch is
conclusive and its containment group is empty. The receiver then runs the census, Signal and the release
of the hold, in that order, and all three are written before it exits. A pending retirement that completes
retries the dispatch's deferred items in the same call.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 5 (run finished), 6.7 (release) and
8.1 (steps 6 to 10). Section 12 of the design holds the ticket itself; its acceptance criteria and
falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Receiver, Retirement. A review's verdict recorded is VELDO-0337.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-14: AC4 added, from the review of VELDO-0303 (finding 4) and the lead's decision on it. Not
  built yet, here or in VELDO-0303. What the review found in control_retirement.py: the clone
  obligation is open while the clone is on disk or a pin is held (_observe), lifecycle refuses the
  release of the worker slot while clone is the first open obligation, _complete_clone turns every
  refused teardown into teardown refused, and _due answers true for it at every sweep. So once a
  ledger is wired into the clone provisioner, a clone that a rule defers, and in report mode every
  clone, would keep its dispatch's worker slot until the owner's Confirm, and every sweep would
  send run finished again for the same items, which is the falsifier of AC3. The decision: the slot
  is compute, and the clone's files are a deferred item the ledger tracks. So the obligation closes
  on hand-over to the ledger (retired, or a refusal whose code is space_deferred), the slot is
  released then, and a deferred teardown is recorded as deferred with the ledger's item and is not
  attempted again by a sweep. clone_in_use is live compute and keeps the obligation open. Two things
  follow and are part of AC4 and of this ticket's build. The pins: today the provisioner releases
  them only inside the teardown call (control_clone.Clones._through_space), and after the slot is
  released nothing calls the teardown again, so the release has to follow the work tree item's
  removal outcome wherever it is written (the next event, admission, reconcile, the owner's
  Confirm). AC3: its "a pending retirement's obligation completes" now includes the clone
  obligation closing at hand-over, and the design's Retry paragraph of section 7 and the Retirement
  row of the component table need the same wording when the design is next revised. This ticket
  must land before `space` is wired into the clone provisioner: VELDO-0303 threads `space` through
  to the three places that build one (control_launch.py twice, control_launch_work.py once), and
  nothing gives them a ledger yet.
- 2026-11-14: built. No acceptance criterion changed. What the build decided, recorded here because
  the criteria do not say it:
  - Where it is. In control_launch.py: Receiver._space_end and _group_empty, the functions
    space_release, space_retry and space_run_items, Runner.retry_deferred, and report_end. In
    control_retirement.py: the hand-over (_tracked, _hand_over), follow_pins and the retry seam
    (`deferred`). Nothing in either deletes anything: every removal is Signal's, after the safety rules
    and the keep step. Nothing in the engine builds `space` yet, so an installation runs as before.
  - The order at the receiver's end. With a ledger the receiver judges nothing where only the worker's
    own process is known to have ended. The end is recorded first (exit or refusal), then the run-end
    scan reads the run's workspace, then the space end runs (census, Signal, release), and only then is
    the end reported; the runner stops the receiver once it reads that report. So the space end sits
    in report_end, between the scan and the emit. The refusal paths of launch call it after their
    refuse record. With no ledger the run directory goes where it went before.
  - Conclusive is exited or refused, read from the store at that moment. An unknown outcome is not a
    recorded end: such a run is sent nothing by its receiver, its items stay and its hold stays held.
    Its run directory is still the sweep's (Runner.clear_runs, VELDO-0303), which sends run finished
    for a leftover once the kernel shows the run gone, whatever the record says. That is unchanged
    here, because suite 142 holds it to that and is outside this footprint. FOR THE LEAD: that sweep
    still sends run finished at every sweep for a leftover whose run directory stays deferred, and the
    event reaches every item of the same run, a clone handed over among them. It judges again and
    loses nothing, but it is a run finished per sweep for an unknown or orphaned dispatch.
  - A group nobody could read (empty is None) is not held back by the receiver: the event is sent and
    rule 3 is left to the answer the installation wired in, as VELDO-0303 built it. Only a group known
    to hold a process stops the send.
  - The hold. The receiver releases the hold the contract's space field names (design 6.7), else the
    one placed under the dispatch's own identity; nothing writes either yet (VELDO-0316). It is
    released whenever the run has ended (conclusive, group not known to hold a process), also when a
    consumer of the run's clone kept the event from being sent. Nothing but the receiver releases a
    hold in this ticket: a hold of a run whose receiver died, or whose outcome is unknown, stays
    until VELDO-0315 or 0316 gives the sweep or reconcile that release. FOR THE LEAD.
  - Handed to the ledger means the ledger answers for it. The clone obligation closes on retired, and
    on a refusal that starts space_deferred only while the ledger records the clone's root as a live
    item in state due, deferred, removing or kept. A clone no item records
    (space_deferred:not_in_ledger), a root still present because Signal raised and the event never
    reached it, a ledger that cannot be read, and an installation with no ledger keep the obligation
    open and the slot held, and are attempted again as before. This is narrower than "any refusal
    whose code is space_deferred": releasing the slot there would leave a clone on disk that nothing
    tracks. FOR THE LEAD, should the slot be wanted back in those cases too.
  - The pins. follow_pins runs at every sweep and every retire call. It releases a handed-over
    clone's pins when every item the ledger records at the work tree's path is removed or gone and
    the kernel says nothing is at that path. What it follows is in memory, like every entry of the
    retirement service: after a restart of the runner a clone handed over before it keeps its pins
    until something else releases them (a held pin keeps objects; it loses nothing).
  - The retry of AC3 is run finished for the run, sent once for each owner among the run's deferred
    items. Rule 3 is answered for that run alone, and only when the runner reads at that moment that
    the record has a known end and the kernel shows the worker gone and its group empty; otherwise it
    is left to the answer the installation wired in. It is made only when a retirement that was pending is carried out; one carried
    out at its first attempt retries nothing. When that same attempt's teardown already sent run
    finished for the clone, the owners of the clone's items are not signalled twice. It is not sent
    while a consumer of the run's clone has not ended.
  - Two registered falsifiers of earlier tickets were re-anchored, unchanged in meaning, because
    _remove_run now reads the group in one place: space303-receiver-answers-for-an-unread-group and
    space305-no-census-at-the-receivers-end. Each was applied again and turns its row red.
- 2026-11-14: fix round, after the review of this ticket (verdict FIX, five findings) and the lead's
  decisions on them. No acceptance criterion changed. The footprint gained three files by the lead's
  decision: suite 142 (its rows stated the sweep as a retry), suite 129_veldo_0254 (the race in its
  own read, finding 2) and the VELDO-0303 spec (a History line). What changed, and what it replaces
  in the entry above:
  - Finding 1, a sweep is no retry. The entry above left Runner.clear_runs sending run finished at
    every sweep for a leftover whose run directory stays deferred, FOR THE LEAD. The decision: a
    sweep never sends run finished again for a run already handed over. Now clear_runs reads the
    ledger first. A run directory whose item is due, deferred, removing or kept is the ledger's (an
    ending event reached it): the leftover is dropped with the observation remove_run, outcome
    handed_over, and nothing is sent; its retries are the ledger's (design section 7, Retry). Run
    finished is sent only while the item is declared or present, and at most once for a leftover:
    after its own event a held item is dropped the same way, and one the event did not move is not
    sent another (refusal run_finished_sent). sweep_runs applies the same rule at start, so a
    restart does not make a deferred run directory a leftover again. A ledger that cannot be read
    sends nothing and forgets nothing.
  - Finding 1, the event is for the run's own folders alone. The sweep and the receiver both send
    with `alone`, and both look first (space_apart): while the run's owner also has a live work
    tree or agent repository that is not at or beneath the run's folders (its clone), nothing is
    sent, the reason is not_alone, and the clone's own teardown sends the one run finished for that
    owner, behind its clone_in_use test; that event removes the run directory with the clone. So
    the receiver's send can no longer judge a clone, handed over or not. The cost, for the lead: a
    run that owns a worktree or an agent repository elsewhere which no teardown ends (none is
    declared that way today; VELDO-0302 decides the owners) is sent nothing by its receiver, and its
    run directory and scratch stay until that worktree's own event or reconcile. That costs space
    and loses nothing. The ledger's signal takes an owner and no single item, and the ledger module
    is outside this footprint, so `alone` is the limit used.
  - The consequence the review asked to be recorded: until VELDO-0315 or 0316 lands, a deferred run
    directory of a run whose outcome is unknown (no retirement completes) stays on disk until
    reconcile. That costs space and loses nothing.
  - Suite 142 changed with it: ac3/deferred-then-swept now expects the leftover dropped as handed
    over, no second event with the journal unchanged, and the removal by a retry of the ledger's;
    f3/consumer-holds-clone now expects not_alone once the consumer has ended and the removal of
    the run directory by the clone's teardown. Runner.wait keeps an exited run as a leftover when a
    ledger is wired, so a run directory its receiver sent nothing for is the sweep's in the same
    runner and not only after a restart.
  - Finding 2, the test. Suite 129_veldo_0254 read /proc/<pid>/environ right after Popen and an
    asynchronous SIGSTOP, before the kernel had laid out the new image. It now waits, with a
    deadline, until /proc/<pid>/stat shows state T, reads only then, and is red when the process
    never stops. Measured on this host: the old row red in 4 of 60 runs of the suite, the fixed row
    in 0 of 200. No product code changed for it.
  - Finding 3, fail closed. The entry above said a group nobody could read is not held back by the
    receiver. It is now: an unread group is not known to be empty, so _space_end sends nothing,
    judges nothing and keeps the hold, with the reason group_unread (design 0.6). The sweep's kernel
    test, which reads the group itself, takes over the run directory. The hold of such a run stays
    held until VELDO-0315 or 0316 gives the sweep or reconcile that release, as the entry above
    already says of an unknown outcome.
  - Finding 4, the pins survive a restart. The entry above said what follow_pins follows is in
    memory. It now reads the pin refs in the caches at each call (refs/veldo/pins/<clone id>/...),
    takes the work tree's path from the clone id, and releases a clone's pins only when the ledger
    records an item at that path, every item it records there is removed or gone, and nothing is at
    the path. Never on "no item and nothing at the path": a clone being made holds its pins before
    its work tree exists. It runs when the service is made (the start), at every sweep and at every
    retire call.
  - Finding 5, coverage. Two rows drive Receiver.launch itself, one refusal before any spawn and
    one failed spawn, and show the order: the refusal recorded, the space end, the report.
  - Rows added to suite 146, each with a registered falsifier applied once and seen red:
    f1/sweep-never-resends (the reviewer's probe row with the expectation reversed),
    f1/start-sweep-applies-the-rule, f1/sent-once-and-alone, f3/unread-group-sends-nothing,
    f4/pins-followed-after-a-restart, f4/clone-being-made-keeps-its-pin, f5/refused-before-spawn,
    f5/spawn-failed. Two registered falsifiers were re-anchored, unchanged in meaning, and applied
    again: space303-receiver-answers-for-an-unread-group and
    space308-pins-released-at-the-teardown-only.
- 2026-11-14: second fix round, after the re-review of the fix round (verdict FIX, findings N1 and
  N2) and the lead's decisions on them. No acceptance criterion changed and the footprint is as it
  was. What changed, and what it replaces in the entry above:
  - N1, alone no longer refuses the whole send. The entry above held run finished back while the
    run's owner had any work tree or agent repository outside the run's folders, and named the cost
    FOR THE LEAD. The decision: run finished is sent for the run's own items, and only what a
    retirement handed to the ledger (the clone) is kept out of it. Now the look (space_apart, and
    the same test made again at the send, space_signal's `alone`) counts only items of a clone:
    beneath the installation's clones folder (clones_root), of the same owner, not at or beneath the
    run's folders, and in a state an event takes (declared, present, deferred, kept). A run that
    owns a worktree or an agent repository that is no clone's is sent run finished by its receiver,
    and a leftover of such a run by the sweep, and the one event ends every item of the run, as
    design 6.10 has it. A clone the teardown's event left due or removing is not matched by any
    event, so it does not hold the run's event back and is not touched by it. An installation with
    no clones has no clone to count. Clones that are wired and whose folder cannot be read send
    nothing (the send refuses by itself).
  - N1, what is not closed, FOR THE LEAD. The ledger's signal names an owner and no item
    (control_space.py, outside this footprint), so an event cannot be sent for some items of an
    owner and not for others. While a clone of the run's own owner is live and present, or handed
    over and deferred or kept, an event for that owner would judge the clone, so nothing is sent
    from the receiver or the sweep (not_alone, as before) and the run's other items wait with it.
    While the clone is live its teardown sends run finished for that owner, and that event ends
    the run's own items with the clone, each after the rules and the keep step. For a clone handed
    over and deferred, the run's items wait for the ledger's next retry (the retirement retry,
    admission, reconcile), and nothing in production calls that retry for them today: see the
    correction in the entry of the third round below. The lead's row (every item of the run that
    is no clone's ended, the handed-over clone untouched) is therefore shown with the clone left
    due, and the deferred clone has its own row: nothing sent, the clone not judged again, and the
    run's items deferred and unharmed. Sending for the run's items alone beside a deferred clone
    needs the signal that names items, the same follow-up VELDO-0310 names. This costs space and
    loses nothing.
  - N2, bounded observations. A leftover that was sent its one event and is still there is recorded
    once (run_finished_sent) and dropped from the runner's memory: no sweep sends it another, so it
    is the ledger's and reconcile's. What a sweep finds of a leftover is recorded once for each
    outcome and refusal (Runner._once), never once at every sweep: clone_in_use, not_alone, a
    refusal of the send, a ledger that could not be read. A leftover held back by its clone stays
    in memory, with its one observation, so the sweep still reports its removal after the teardown.
    With no ledger the sweep records as it did.
  - Suite 146: f1/sent-once-and-alone now expects the leftover dropped after run_finished_sent, and
    the not_alone observation to name the clone's three items. Rows added, each with a registered
    falsifier applied once to the copy the suite loads and seen red: n1/own-items-ended (the
    re-review's probe row with the expectation reversed; falsifier
    space308-any-repository-of-the-owner-holds-the-event-back, the look as it was),
    n1/handed-over-clone-untouched (space308-event-reaches-a-handed-over-clone) and
    n2/observations-bounded (space308-observation-at-every-sweep and
    space308-sent-leftover-stays-in-memory). The four falsifiers of the first fix round whose
    lines were touched keep their anchors and were applied again: all red.
- 2026-11-14: third round, a correction after the re-review of the second fix round (verdict FIX,
  finding 1). No acceptance criterion changed, no engine code changed, and the footprint is as it
  was. What the entry above said of N1 and was not true, and what is true:
  - What the entry said. That the run's items held back behind a handed-over, deferred clone "are
    not held for ever", because the ledger's own retry (space_retry, when the clone's retirement is
    carried out) sends run finished for that owner. Its row showed that by calling
    Runner.retry_deferred by hand.
  - What production does. space_retry has one production caller: Retirements._attempt, and only for
    a retirement that was pending and is released (control_retirement.py, `if released and
    pending`). A retirement that hands the clone over and releases the slot in the same attempt
    was never pending, so that call is not made for it, then or later. Nothing else in production
    calls retry_deferred for those items today. Every later sweep finds the clone still counted
    and refuses not_alone, once on the record (N2). A runner that restarts forgets the leftover,
    and then no sweep looks at all.
  - So the run's items deferred behind a handed-over clone wait for the ledger's next retry: the
    retirement retry (only where a retirement is still pending), admission (VELDO-0316, not built
    on this branch) and reconcile (VELDO-0315, not built). Until one of the two lands, such items
    stay as they are without bound. Nothing is ended wrongly and nothing is lost: the clone is
    whole with its pin held, the run directory and the agent repository are on disk and present
    in the ledger, and when an event does come it is run finished for an owner whose run is over,
    after the rules and the keep step. It costs space, never work.
  - How reachable it is. In the usual order the clone's teardown event (the same owner, ended)
    already reaches the run directory, the scratch folder and any item that is no clone's, because
    they are present then. The held-back case needs a run item that becomes reachable after the
    hand-over (declared then and confirmed later, or declared later by a creator of VELDO-0302),
    or a clone item in state kept.
  - DEPENDENCY, FOR THE LEAD. Closing it needs one of: the signal that names items (the follow-up
    VELDO-0310 also names), so run finished can be sent for the run's items beside a deferred
    clone; or VELDO-0315 reconcile, which picks up what no event reached; or admission's retry
    (VELDO-0316). The creators of VELDO-0302 that declare run items beside a clone depend on it.
    A retry made by the sweep when a handed-over clone's work tree leaves deferred was not built:
    finding 1 of the first review ruled that a sweep is no retry, so that is the lead's decision.
  - Suite 146, row n1/handed-over-clone-untouched: the hand call of retry_deferred is gone. After
    the holder has gone the row drives production, five Runner.sweep calls, and asserts that no
    retirement is pending, nothing is sent, no retry is made, nothing is written, the leftover
    keeps its one not_alone observation, the clone is deferred at the version it had, whole, its
    commit readable and its pin held, and the run directory and the agent repository are present
    on disk and in the ledger, the repository at its commit. 146 is 58 passed. Its falsifier
    (space308-event-reaches-a-handed-over-clone) was applied again and is red on the row.
- 2026-11-14: recorded from the fix round of VELDO-0312, by the lead's decision. The ledger's signal can
  now name items: a subject that is a list of items, each with the version its sender read, on which the
  ledger acts exactly and which it refuses whole when one of them changed (control_space.py, A SIGNAL
  THAT NAMES ITEMS). This ticket adopts it next: it closes what N1 left open above, the signal that
  named an owner and no item, so run finished can be sent for exactly the items the receiver judged. No
  behaviour of this ticket changed in that round.
