---
schema: veldo.spec/v1
id: VELDO-0291
title: Suite 86 reports every failed service start with its log, and holds its API port bound for the whole run
status: draft
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [VELDO-0189]
placement: [enforcement]
protected_paths: []
footprint:
  - scripts/suites/86_veldo_0189_engine_upgrade.py
  - scripts/suites/support/v171_tailscale.py
  - scripts/check_teeth_mutations.py
  - specs/VELDO-0291-suite-86-reports-a-failed-start-and-holds-its-api-port.md
  - specs/index.md
  - proof/VELDO-0291/**
behavior_bearing: true
observability:
  logs: >
    A failed row restart/adoption-signer-kill prints, in its detail, every start the stand-in manager
    made during the row: the unit, the start code, the error text, the seconds it took, whether the
    process had exited and with what code, and for a failed start the last 800 bytes that start wrote
    to the unit log.
  metrics: >
    The row timings file (VELDO_ROW_TIMINGS) carries the same start records under adoption.starts, and
    the API port the suite holds.
  traces: >
    None. A start record sits in the order the starts were made, so a failed start is read beside the
    setup run that asked for it.
  error_taxonomy: >
    No product refusal changes. The suite adds no refusal of its own.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: suite 86 holds its API port bound from the moment the kernel chooses it until the suite's
      cleanup, so between a stop of the service and its next start no other process can bind that
      number and the kernel gives it to no bind to port 0 and no outgoing connection, while the API's
      own bind still succeeds. Set: the port the suite holds, the fresh host's service, and one child
      process started with the suite's child environment. Completeness: row port/held-for-the-run
      (printed with the prefix VELDO-0291) stops the fresh host's service and then requires four
      things. The child's bind of 127.0.0.1 at that port number, without SO_REUSEADDR, fails with
      EADDRINUSE. The port reserved_port() returns in the child, loaded from the same file the suite
      loaded, is a different one. 500 sockets bound to 127.0.0.1 port 0 and held open together are none
      of them given the port. The start that follows succeeds and a connection to the port is
      accepted. Red at 646ff7c8, where free_port() closes its socket and nothing holds the port, so the
      child's bind succeeds.
    falsified_by: >
      Close the held socket before reserved_port() returns. Registered mutant port291-not-held must
      turn port/held-for-the-run red. Leave SO_REUSEADDR off the held socket. Registered mutant
      port291-held-without-reuse must turn port/held-for-the-run red, because the API's bind then
      fails and the start that follows does not succeed.
  - id: AC2
    text: >
      Claim: the stand-in manager records every start it makes, a wanted unit's start included, and a
      failed start's record tells a refused bind from a late start. Set: the fresh host's service,
      stopped, and one fixture unit. Completeness: row start/failure-recorded (prefix VELDO-0291) has
      two legs. Refused bind: a socket that sets SO_REUSEADDR, binds the API port by number and listens
      holds it while the service is started, twice, the service stopped between the two. For the
      second start the row requires the record of the API unit's start to carry code 1, the error text
      "the unit did not start", an exit code that is not None, and a log tail in which "Address
      already in use" occurs exactly once, though the log file holds the first refusal too. With the
      socket closed and the service stopped, the next start succeeds and its records all carry code 0.
      Late start: a second Manager over a unit directory of its own under the suite's scratch
      directory starts one Type=notify fixture unit whose process writes the line "fixture waiting" to
      its output, never reports readiness and sleeps 30 s. The row requires code 1, the same error
      text, no exit code (the process was still running when the wait ended) and a log tail equal to
      "fixture waiting\n". The row then stops the fixture unit and requires its process gone. Red at
      646ff7c8, where the manager keeps no record, drops the result of a wanted unit's start (86:335)
      and never reads the unit log.
    falsified_by: >
      Record a failed start without its log tail. Registered mutant start291-log-tail-dropped must
      turn start/failure-recorded red. Leave wanted units out of the records. Registered mutant
      start291-wanted-unit-unrecorded must turn start/failure-recorded red. Take the tail from the
      start of the unit log. Registered mutant start291-tail-whole-log must turn
      start/failure-recorded red.
  - id: AC3
    text: >
      Claim: without_signer checks the start it makes, the row ends at a failed start, and the row's
      failure detail carries that start's code, error text and log tail. Set: the body of row
      restart/adoption-signer-kill, run a second time with a check function that records its calls
      and with the API port held by a listening socket that sets SO_REUSEADDR and binds it by number
      during the first without_signer start. Completeness: row
      restart/adoption-start-checked (prefix VELDO-0291) requires the last recorded check to be the
      start check and to be false; its label to name the API unit, code 1, "the unit did not start"
      and a log tail containing "Address already in use"; no setup run to have been made after it;
      the detail string the suite builds for a failed adoption row to contain the same record; and,
      once the port is released, the fresh host's service to be running again as it was before the
      row. Row restart/adoption-signer-kill itself still passes with every check it has today. Red
      at 646ff7c8, where without_signer makes no check (86:1552 to 1554) and the row goes on to the
      setup run.
    falsified_by: >
      Remove the start check from without_signer. Registered mutant start291-signer-start-unchecked
      must turn restart/adoption-start-checked red. Keep the check and let the row go on to the setup
      run. Registered mutant start291-row-continues must turn restart/adoption-start-checked red. Build
      the failed row's detail without the start records. Registered mutant
      start291-detail-without-starts must turn restart/adoption-start-checked red.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. Suite 86 again takes its port from free_port() and holds nothing and reports
  start codes only. No
  product file, stored record or other suite depends on anything this change adds.
---

## Intent

Row restart/adoption-signer-kill of suite 86 failed 2 of its 84 control runs across the six
landing-c gates that claimed workers by measured use. The
analysis (landing-c-flake-pattern-2026-11-11.md in the lead's research notes, section 4) lists four
timing assumptions behind the row. Two of them are defects in the suite, and this spec fixes those two.

The first is that a failed start says too little. The suite's stand-in for the systemd user manager,
Manager.start (86:305 to 336), answers "the unit did not start" for a process that exited and for one
that was only late (86:330 to 331). without_signer starts the service and doesn't look at the result
(86:1552), so the row carries on over a host that may not be running. The process's own output goes to
a unit log (unit-<name>.log under the suite's scratch directory, 86:319) that no check reads. One more
gap shows in the code: the API runs as a unit the authority unit wants, and Manager.start throws away
the result of a wanted unit's start (86:333 to 335). A refused bind of the API therefore never shows in
the start code of the service. It surfaces later, when setup finds the API unit not running, starts it
itself and refuses with unavailable_service:api (control_factory_setup.py:1500 to 1503).

The second is the port. The suite picks the API's port once, by binding port 0 and closing the socket
(free_port, scripts/suites/support/v171_tailscale.py:123 to 128, called at 86:600). Setup writes that
port into the API's process configuration, and the API binds it again at every start. The suite stops
and starts the service many times in its 75 s. Between a stop and the next start nothing holds the
port, and it lies inside the ephemeral range (32768 to 60999 on the qualification host), the range the
kernel hands out to outgoing connections and to every other bind to port 0. The mutation stage runs up
to 40 workers beside the suite. If one of them is handed the port, the API fails to bind and exits.

Today those two failures look the same in the row's detail, and round 9g could not tell them apart.

## What this spec leaves alone

Item 1 of the analysis, the 5 s readiness wait in setup_runtime.ready
(scripts/suites/support/setup_runtime.py:131), belongs to VELDO-0290. That spec declares suite 86 as a
wall-clock suite so the wait gets CPU headroom in the gate. The 5 s bound is not changed here.

Item 3, setup's 30 s answer wait after the restart (ANSWER_SECONDS,
.veldo/control_factory_setup_upgrade.py:437), is a product constant and stays.

## Design

### The port

The suite holds its API port bound for its whole run.

scripts/suites/support/v171_tailscale.py gains reserved_port() beside free_port(). It binds a TCP
socket to 127.0.0.1 port 0, so the kernel chooses a free port and claims it in one step, then sets
SO_REUSEADDR on that socket and returns the port and the socket. The socket never listens. Suite 86
calls it at 86:600 in place of free_port() and closes the socket in its cleanup, after its managers
have closed every service process. The other suites that call free_port() aren't changed.

This works because the API listens through http.server.ThreadingHTTPServer (control_api.py:1254),
which binds with SO_REUSEADDR. Linux lets a SO_REUSEADDR socket bind and listen beside a
SO_REUSEADDR socket that is bound and not listening. Every other bind of the number fails with
EADDRINUSE, and the kernel gives a bound port to no bind to port 0 and no outgoing connection. So the
API can bind the port at every start, and nothing else can take it between a stop and a start.

What it doesn't cover: a process that sets SO_REUSEADDR and binds that exact number while the API is
stopped. Only a process that already knows the number can do that, and the kernel never gives it
out. If the API ever stops setting SO_REUSEADDR, every start of it fails loudly with the address in
use, which the start record names.

Suite 86 loads the support file as ROOT / "scripts/suites/support" / "v171_tailscale.py", so a
registered mutant of reserved_port() (dir scripts/suites/support) replaces the copy the suite runs.
The child process in port/held-for-the-run loads the file the suite loaded, TS.__file__, so it runs
the same copy.

### Mechanisms weighed and not chosen

A socket that holds the port only between a stop and the next start. Nothing is gained over holding
it for the whole run, and the hand-off adds code in the stand-in's stop and start.

A fresh port for every start. The port isn't the stand-in's to choose: setup writes it into the
installed API configuration, and the rows compare installed files byte for byte and lay them down again
with restore. A new port per start would have the suite rewriting product state between a stop and a
start, including in the middle of setup's own restart. Each new port would also come from free_port()
and have the same gap between its close and the service's bind.

Passing the service an open listening socket, as systemd socket units do. The API has no such start
path, so this is a product change made for a test.

Listing the port in net.ipv4.ip_local_reserved_ports. That is host configuration and needs root, and
it only keeps the kernel from handing the port out, which a bound socket already does.

A network namespace of its own for the suite. It would isolate the port completely, but the suite's
stand-ins, its children and the user manager it talks to would all have to move into the namespace.
That's a rebuild of the fixture, not a fix for one port.

A port below the ephemeral range claimed through an abstract unix socket named after it. The name
only coordinates processes that look for it, and being outside the range adds nothing once the port
is bound.

### Start records

Manager keeps a list, starts. Every start it makes appends one record, whichever way the start was
reached: a direct call from the suite, setup's start or restart through the Bridge, the start inside a
failed restart, and each wanted unit. A record holds the unit, the code, the error text, the seconds
the start took and the process's exit code, None while it still runs. Before it starts the process the
manager notes the size of the unit log, which is opened for append and shared by every start of that
unit. For a failed start the record also holds the last 800 bytes written after that offset, so the
tail belongs to this start and no earlier one.

A wanted unit that fails still doesn't fail the unit that wants it. That matches systemd, where Wants
is the weak dependency. The failure is recorded where before it was dropped.

A late start and a refused bind then read differently. Late: no exit code, and a log tail with no
error. Refused bind: an exit code, and a tail that names the address in use.

A call that returns before starting a process (unit not found, a BindsTo unit inactive) appends a
record with its code and error text and launched false. A start of a unit that already runs appends
a record with code 0 and launched false, and then the records of its wanted units.

### The row

without_signer checks its start: the code is 0 and no start it caused, the wanted API unit included,
failed. A failed check carries the failed record in its label. The row ends there. Its later checks
would only repeat the same failure in other words, and a setup run over a host that isn't running
proves nothing about the adoption signer. The cleanup at the end of the row (stop, restore, start the
service again if it was serving) still runs.

When the row fails for any reason, its detail carries every start record made during the row, where
today it carries the two codes from without_signer. One function builds that detail, and the new row
reads it, so what the row checks is what a red gate prints.

To drive the failing case, the row's body takes the check function and a hook that runs before the
first without_signer start. Row restart/adoption-start-checked calls it with a recording check and a
hook that holds the port. The real row calls it as before.

### Cost

The late-start leg of start/failure-recorded waits out the 5 s readiness bound once, so the suite gets
about 6 s longer. The other legs each add one stop and start of the service. Touching
scripts/check_teeth_mutations.py is a trigger in scripts/mutation_selection.json, so the gate for this
change runs the full mutation sweep.

### Proof

Each summary under proof/VELDO-0291/ is veldo.proof-summary/v1 with its command, environment, host load
and discarded list. The red-before runs the built suite with each criterion's behavior put back as it
is at 646ff7c8: the port from free_port() with nothing held, Manager.start without records and without
reading the unit log, and without_signer without its check. Each new row must be red on the check its
criterion names. A row red only because its section raised does not count as red-before. The new rows
print with the prefix VELDO-0291 through a second expect helper in suite 86, so they aren't reported as
VELDO-0189 rows.

## Out of scope

The 5 s readiness bound and the wall-clock declaration (VELDO-0290). ANSWER_SECONDS and every other
product constant. Any file under .veldo/. The other suites that call free_port(). Making a failed
wanted unit fail the start of the unit that wants it.

## What the reviewer judges

- The port is bound from the kernel's choice to the suite's cleanup, the held socket never listens,
  and the API still binds it at every start.
- Every start the manager makes is recorded, and a failed record's log tail belongs to that start.
- The row ends at a failed start, its cleanup still runs, and the row's existing checks are unchanged.
- Nothing here waits longer or tries again to get a start through.

## History

2026-11-11: drafted from section 4 of the landing-c flake analysis
2026-11-11: revision 1 applies the findings of the review of 8b44659e
