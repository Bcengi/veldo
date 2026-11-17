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
  - "engine/.veldo/control_clone.py"
  - ".veldo/control_clone.py"
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
- 2026-11-14: fix round 3, the item-naming signal adopted, by the lead's decision recorded in the entry
  above. No acceptance criterion changed and the footprint is as it was. It closes what N1 left open (the
  second fix round's "what is not closed" and the third round's DEPENDENCY): the run's own items are no
  longer held back by a clone a retirement handed to the ledger.
  - What changed, in control_launch.py. The receiver's send and the sweep's (space_signal with `alone`)
    no longer signal the owner. They name exactly the run's own items, each with the version read at that
    moment (space_named, space_versions), and the ledger acts on those and on nothing else of the owner.
    The run's own items are what the owner's event reached before: present, kept or deferred, ending on
    run finished, not marked Keep by the owner; the run directory, the scratch folder and a worktree or
    an agent repository of the run elsewhere among them. The versions are read before the records, so a
    record that changes between the two reads is named at the version it had and refused.
  - A clone is never named, in any state. One handed over (due, deferred, removing or kept) is the
    ledger's: it does not hold the event back any more, and the event leaves it at the state and the
    version it had. One still live (declared or present) holds the event back as before (not_alone): its
    teardown is to come, and that teardown sends run finished for the owner, behind its clone_in_use
    test, which ends the run's folders with the clone. The teardown's own send is control_clone.py's,
    outside this footprint, and still names the owner. FOR THE LEAD.
  - A version that changed between the read and the send. The ledger refuses the whole command, with
    nothing written (space_item_version:<item>). The receiver sends nothing in its place: its end says
    not sent, reason remove_refused, with the ledger's reason, and the hold is released as for any run
    that has ended. No event reached the run directory, so it is a leftover the sweep may send its one
    event for, with the versions read then. Nothing is lost by the refusal and nothing is stuck by it.
  - A leftover with nothing to name. An item no event reaches (declared, never confirmed) used to be sent
    an owner's event that matched nothing. Now no command is sent at all. The sweep still records it
    once, under the same name (run_finished_sent), and drops it: it is the ledger's and reconcile's, as
    before.
  - Who signs. No allowance was added to the ledger. Its rule for who may sign (permit) limits the two
    host principals, space-observer and space-runner, and the runner stays refused for a signal that
    names items, as VELDO-0312 decided. The receiver signs as its own principal, launch-receiver, which
    is no host principal of the ledger and is limited, as before, to what the installation wires in. The
    row shows both: the runner refused for the same named items, the receiver's command accepted under
    its own principal.
  - What is not changed, FOR THE LEAD. The retry of AC3 (space_retry) still signals the owner of the
    dispatch's deferred items: it is the ledger's retry of everything deferred for the run, the clone's
    items among them, which is its purpose. A run item that is declared after the receiver's send and
    after the sweep dropped the leftover is still reconcile's (VELDO-0315).
  - Suite 146 is 33 rows, 59 passed. n1/handed-over-clone-untouched is rewritten to the old N1 probe,
    closed: beside a deferred, handed-over clone the receiver sends run finished once, naming exactly the
    run directory and the agent repository at the versions read; both are removed, the repository after
    its commit was kept; the clone's three items keep their state and version, the clone whole, its
    commit readable and its pin held; the sweep does the same for a leftover; and no event of the suite
    sent by the receiver or the sweep named an item of a clone. Its falsifier, registered and applied
    once to the copy the suite loads, seen red: space308-run-finished-names-the-owner (the owner is
    signalled, as it was). New row n1/changed-between-judge-and-send: an item of the run is measured
    after the receiver's read and before the ledger's command; the whole send is refused, the three
    items stay present and on disk, and the sweep's later send ends all three. Its falsifier, applied
    once and red: space308-refused-send-falls-back-to-the-owner. f1/sent-once-and-alone and
    n2/observations-bounded now expect no command for a leftover with nothing to name. One falsifier was
    re-anchored, unchanged in meaning (space308-any-repository-of-the-owner-holds-the-event-back), and
    it and the seven others whose lines or rows were touched were applied again by hand, one at a time:
    all red on their rows. The registered set was not run as a whole in this round. Suite 142 is
    unchanged, 57 passed.
- 2026-11-14: fix round 4, by the lead's decision on the point fix round 3 left FOR THE LEAD. The clone's
  teardown names exactly the clone's own items at their versions, and a clone that is still live holds
  nothing back. No acceptance criterion changed. FOOTPRINT AMENDED: control_clone.py and its engine copy
  (engine/.veldo/control_clone.py, .veldo/control_clone.py) are added, by that decision.
  - What changed, in control_clone.py. The send of the space path (space_signal, called by the teardown
    and by a provision that failed part way) no longer signals the owner. It sends one event that names
    exactly the items the ledger records at or beneath the clone's root that the event reaches (present,
    kept or deferred, ending on run finished, not marked Keep by the owner), each at the version read
    then (space_named). The versions are read before the records. The ledger acts on those items and on
    nothing else of the owner, so a run directory, a scratch folder, a worktree or an agent repository
    of the same owner outside the clone is never reached by a teardown. With nothing to name, no command
    is sent. The `alone` argument of this module's space_signal, which nothing called, is gone.
  - A version that changed between the read and the send. The ledger refuses the whole command, with
    nothing written (space_item_version:<item>). The teardown is refused as space_deferred:remove_refused
    with the ledger's reason on its retire event, no pin is released, and nothing is sent in its place.
    The clone is whole and its obligation open: the next teardown reads the versions again.
  - What changed, in control_launch.py. The look that held the run's send back while a clone of the same
    owner was declared or present is removed (space_apart, _space_apart, SPACE_CLONE_LIVE, the refusal
    not_alone of the receiver and of the sweep). The receiver's send and the sweep's name the run's own
    items and never a clone's, as since fix round 3, so nothing of the clone can be reached by them and
    nothing of the run waits for the clone's teardown. The clone_in_use test before both sends is
    unchanged: a run directory still stays while another dispatch uses the run's clone.
  - Nothing here removes anything. Every removal is Signal's, after the safety rules and the keep step.
    No allowance was added to the ledger; the teardown signs as before.
  - What is not changed, FOR THE LEAD. The retry of AC3 (space_retry) still signals the owner of the
    dispatch's deferred items, as recorded in fix round 3. The sends of fleet.py, lander.py and
    control_launch_work.py are other tickets' and still signal the owner.
  - Suite 146 is 36 rows, 62 passed. New rows, each with a registered falsifier applied once to the
    copy the suite loads and seen red. n1/live-clone-holds-nothing-back: beside a live clone of the same
    owner the receiver, and for a leftover the sweep, sends run finished once naming the run's own items;
    they are removed, and the clone's three items stay present at the version they had; each clone is
    then removed by its own teardown. Falsifier space308-live-clone-holds-the-send-back (the look put
    back). n1/teardown-names-its-clone-only: the teardown names exactly the clone's three items at the
    versions read, the run directory and an agent repository of the same owner keep their state and
    version, and no teardown of the suite named an item outside its own clone. Falsifier
    space308-teardown-names-the-owner (every item of the owner named, as the owner's event did).
    n1/teardown-changed-between-judge-and-send: an item of the clone is measured after the read and
    before the ledger's command; the whole send is refused, nothing of the clone is ended, no pin is
    released, and the next teardown removes the clone. Falsifier
    space308-teardown-refused-send-falls-back-to-the-owner.
  - Older rows that changed with the behavior. f1/sweep-never-resends: the run directory is deferred by
    the receiver's own event, since the teardown no longer reaches it. f1/sent-once-and-alone: its
    not_alone part is gone. n2/observations-bounded: once the consumer has ended the next sweep sends
    the one event and the run directory goes while the clone is present. Suite 142,
    f3/consumer-holds-clone: once the consumer has ended the sweep removes the run directory alone, the
    live clone stays whole and present, and the teardown then removes the clone. Suite 146 loads
    control_clone.py by its production anchor, so the registered runner substitutes it and the canon
    row compares it.
  - Falsifiers re-anchored, unchanged in meaning, each applied again and red on its rows:
    space308-sweep-event-reaches-the-clone and space308-receiver-event-reaches-the-clone (the send for
    the owner; target n1/live-clone-holds-nothing-back), space308-any-repository-of-the-owner-holds-the-
    event-back (the look put back for every worktree and agent repository of the owner),
    space308-sent-leftover-stays-in-memory and space308-sweep-resends-for-a-handed-over-run (their
    anchors lost the look). 36 cases are registered under finding 308. The registered set is run whole
    in this round through scripts/check_teeth_mutations.py; the counts are in the proof bundle.
- 2026-11-14: fix round 5, after the review of the item naming (verdict FIX, finding 1). No acceptance
  criterion changed and no production code changed: rows and falsifiers only.
  - The finding. The names of the run's send (space_named in control_launch.py) and of the teardown's
    (space_named in control_clone.py) leave out an item the owner marked Keep, as fix rounds 3 and 4
    say, and no row had such an item: with the exclusion deleted suite 146 stayed green. The ledger
    refuses a named Keep item, so nothing would be lost, but every send for a run or a clone with one
    Keep item would be refused whole and nothing else of it ended.
  - Suite 146 is 38 rows, 64 passed. New row keep/run-kept-item-not-named: a run with its run directory,
    its scratch folder and an agent repository of the same owner that the owner marked Keep (the
    outcome kept with the owner's mark, as the owner). The receiver sends run finished once, naming
    exactly the run directory and the scratch folder at the versions read; the ledger accepts it and
    both are removed; the repository is on disk at its commit and its item is kept, the owner's mark on
    it, at the version it had. The sweep does the same for a leftover of such a run. Falsifier
    space308-run-names-a-kept-item (the exclusion deleted from the launch module's names). New row
    keep/teardown-kept-item-not-named: a clone whose scratch folder the owner marked Keep. The teardown
    sends run finished once, naming exactly the clone's root and its work tree at the versions read;
    the ledger accepts it; the work tree is removed after its commit was kept and its pin released; the
    folder the owner kept is on disk with its file, its item kept at the version it had; the root,
    which holds it, is deferred and on disk, and the teardown hands the clone over as deferred by a
    rule, not as a refused send. Falsifier space308-teardown-names-a-kept-item (the exclusion deleted
    from the clone provisioner's names). Each falsifier was applied once to the copy the suite loads
    and seen red on its row, its no-op copy green. 38 cases are registered under finding 308.
- 2026-11-17: VELDO-0329b gate fix 4 (lead ruling 1 on gate 99zzF). space308-pins-released-at-hand-over
  and space308-pins-released-while-the-item-is-not-removed survived the first full mutation stage.
  Stale teeth, not a product defect: since VELDO-0304 a pin is released only by the remover's
  remove_ref, which refuses an item that is not removed, so a release the retirement asks too early
  no longer takes the pin. No acceptance criterion and no production file changed.
  - ac4/pins-held-while-deferred reads what the retirement still decides: through the hand-over, the
    sweeps and the work tree under its marked name the remover was asked for no release. Both
    falsifiers are rejected again, unchanged.
  - The same row asks the remover itself for the deferred work tree's own item: refused as
    not_in_ledger, the pin where it was. Falsifier added at the code that now decides,
    space308-remover-releases-for-an-item-not-removed (the state test of remove_ref deleted), red on
    that row by the refusal's name; the pin is still held under it by the keep verification that
    follows. Suite 146 loads the modules under test from the folder of the copy under test, so the
    remover a release reaches is that copy.
  - Suite 146 is 38 rows, 64 passed. 39 cases are registered under finding 308, each applied once
    through the driver's materialize() and worker(): 39 rejected, the no-op copies green (36 of 38
    before). Dispositions in proof/0329b-gate-fix/teeth.md, the runs in gate4-cases.txt there.
