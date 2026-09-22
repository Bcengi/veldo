---
schema: veldo.spec/v1
id: VELDO-0111
title: Observe process creation and every supported listener during a call
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: []
placement: [contracts, runners]
protected_paths: []
footprint:
  - "scripts/fixtures/lifecycle_census.py"
  - "scripts/suites/*_veldo_0111_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0111-process-and-listener-census.md"
  - "specs/index.md"
  - "proof/VELDO-0111/*"
behavior_bearing: true
observability:
  logs: >
    Record observation barriers, process birth identities and ancestry, socket family/type/address, listener lifetime, and the measured scope separately from the observer.
  metrics: >
    Report event totals, lost events, measured process count and supported/unsupported socket families.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish observer_unavailable, observation_incomplete, event_loss and lifecycle_violation; none is a successful absence observation.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A reusable census captures process births, execs and exits throughout the measured call, including short-lived, double-forked and reparented descendants.
      Set: Every task in a fresh measured PID/cgroup scope from a start barrier before the call until return and descendant quiescence; qualification helpers cover fork, clone, exec, immediate exit and daemonization.
      Completeness: Kernel lifecycle events, not periodic process listings, account for each birth identity (PID plus birth sequence), with descendant inheritance and an end barrier. The helper's independently acknowledged births must equal the trace inventory, including children that exit between barriers.
      Refutation: census/process-lifetimes is false on any missing birth or prematurely closed interval.
    falsified_by: >
      Drop exit-before-return descendants from the census event stream; census/process-lifetimes must turn red.
  - id: AC2
    text: >
      Claim: The same census records every successful transition to listening and every new service receive binding during the interval, even if closed immediately.
      Set: All address families and socket types exposed by the qualification kernel, including pathname and abstract Unix, IPv4 and IPv6; addresses are unrestricted. Datagram/raw receive bindings are included as service exposure even where listen is inapplicable.
      Completeness: A kernel-level socket hook has no family or path filter; qualify the hook with a runtime family/type capability inventory and generated bind/listen/close probes for every available combination. Record unsupported combinations with the kernel error and do not claim unqualified families; any available but unobserved combination prevents a complete result.
      Refutation: census/listener-lifetimes is false if the expected service event is missing, including a transient abstract Unix listener or a listener outside the fixture directory.
    falsified_by: >
      Discard AF_INET6 listener events in the collector; census/listener-lifetimes must turn red on the required IPv6 qualification host.
  - id: AC3
    text: >
      Claim: The observer and fixture orchestration cannot count themselves or hide a measured child by its name.
      Set: Observer, event sink and setup helpers created outside the measured scope before arming, plus measured processes with names identical to the observer and to a process-search command.
      Completeness: Membership is established by kernel scope and birth identity; no name matching is allowed. A paired empty interval and a same-name child interval require respectively zero measured births and exactly the acknowledged child's birth. Out-of-scope observer activity is separately recorded.
      Refutation: census/observer-is-outside is false if observer events leak into the result or the same-name child disappears.
    falsified_by: >
      Exclude measured processes whose command name equals the observer's name; census/observer-is-outside must turn red.
  - id: AC4
    text: >
      Claim: An absence result is valid only after successful arming, loss-free collection and complete drain; unavailable observation is explicitly incomplete.
      Set: Normal runs, denied kernel access, absent hooks, lost-event counters, collector death and drain deadline expiry.
      Completeness: Generate fault cases from the collector's lifecycle states and terminal statuses; require every status to have a result and prohibit incomplete statuses from satisfying consumer rows.
      Refutation: census/incomplete-is-not-empty is false if any injected observation failure yields a complete empty trace.
    falsified_by: >
      Return a complete empty trace after collector death; census/incomplete-is-not-empty must turn red.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Provide one reusable lifecycle measurement capability for the no-auto-start and no-listener obligations.

## Context

The gaps are recorded in proof/VELDO-0108/README.md:35-40 and proof/VELDO-0109/README.md:71-77 at 2d19756. VELDO-0108 AC3 and VELDO-0109 AC1/AC3 currently observe only socket snapshots. Consumer rules belong to separate dependent drafts.

## Out of scope

Client refusal semantics, deciding which launches consumers allow, filesystem-write observation, and implementing a host monitoring service.

## Notes

The qualification lane requires a Linux host with the kernel observation privileges and IPv4/IPv6/Unix support needed by the probes. Other hosts report unavailable coverage by name. This is an in-session fixture with bounded teardown, never a detached monitor. Fixture processes and pre-existing authority/SSH endpoints are established outside the measured scope before the barrier; the call and all its descendants stay inside. A consumer may exclude only explicit launch identities declared before observation, never matching names or paths.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.
