---
schema: veldo.spec/v1
id: VELDO-0220
title: The gate holds the host it needs, and a red under someone else's load is reported invalid
status: draft
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0208, VELDO-0214, VELDO-0215]
placement: [enforcement]
protected_paths: ["scripts/verify.sh", "engine/scripts/verify.sh", "scripts/gate_legs.py", "engine/scripts/gate_legs.py", "scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py", ".veldo/policy.yaml", ".veldo/reuse_evidence.py", "engine/.veldo/reuse_evidence.py", "scripts/gate_host.py", "engine/scripts/gate_host.py", "scripts/gate_host.json"]
footprint:
  - scripts/verify.sh
  - engine/scripts/verify.sh
  - scripts/gate_host.py
  - engine/scripts/gate_host.py
  - scripts/gate_host.json
  - scripts/gate_legs.py
  - engine/scripts/gate_legs.py
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - .veldo/policy.yaml
  - .veldo/reuse_evidence.py
  - engine/.veldo/reuse_evidence.py
  - .veldo/init_scaffold.py
  - engine/.veldo/init_scaffold.py
  - .veldo/control_event_vocabulary.py
  - engine/.veldo/control_event_vocabulary.py
  - .veldo/metrics.py
  - engine/.veldo/metrics.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/*_veldo_0220_*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0220-the-gate-holds-the-host-and-never-blames-a-change-for-others-load.md
  - specs/index.md
  - proof/VELDO-0220/*
behavior_bearing: true
observability:
  logs: The gate prints the load it needs, the lock it took or found held (with the holder when recorded), and at the end the share of samples in which other work contended, with the worst sample.
  metrics: Five-second samples of host busy cores, the gate's own cores, CPU and memory pressure and available memory, summarized in the stamp and the gate event.
  traces: The stamp names the lock path, the gate's scope and the contention summary its classification was judged from.
  error_taxonomy: A held lock is NOT STARTED (exit 75, nothing written); a red result under measured contention is INVALID (exit 3, status invalid, event gate.invalid); a red on a quiet host is RED as before; a gate that cannot create its scope or read its counters says so and is RED.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: before any check runs, the gate takes the owner's host lock exclusively (the path in
      the authority's protected scripts/gate_host.json; on this host
      /home/dmitry/.local/state/core-gates/.gate.lock, which the core gates already hold with an
      exclusive flock) and keeps it until it exits on every path; when the lock is held it does not
      start, prints GATE: NOT STARTED with the holder when one is recorded, exits 75 and writes no
      stamp and no event, unless the caller asked to wait a stated number of seconds. Set: a lock
      held by another process, held by a core gate's flock, free, and released by a gate killed
      midway. Completeness: row host-lock/held-not-started and row host-lock/released-on-exit
      drive the real verify.sh against a fixture configuration.
    falsified_by: >
      Run the checks when the lock cannot be taken. Registered mutant host220-ignores-lock must
      fail host-lock/held-not-started.
  - id: AC2
    text: >
      Claim: the gate runs in a delegated user scope of its own (created through the user manager
      with the memory limit and out-of-memory score the configuration states, today 16 GiB and
      900), so its own CPU and memory are counted apart from the host's; every 5 seconds it
      records host busy cores, its own cores, CPU and memory pressure and available memory. Other
      work is contending in a sample when busy cores not the gate's exceed the configured tolerance
      (2 cores or 10 percent of the host, whichever is larger) or memory pressure exceeds 10
      percent. Set: a quiet fixture run, and one with a synthetic CPU load and one with a memory
      load started outside the scope. Completeness: row host-load/contention-measured requires
      the synthetic loads, and only they, to be counted as contending.
    falsified_by: >
      Count the gate's own CPU as external load. Registered mutant host220-own-load-external must
      fail host-load/contention-measured.
  - id: AC3
    text: >
      Claim: a red is never reported as the change's red when other work contended: a RED result
      with contention in more than 5 percent of the run's samples, or in more than 10 percent of a
      failing stage's samples, is INVALID (exit 3, stamp status invalid, event gate.invalid
      carrying the contention summary, terminal GATE: INVALID); a GREEN stays GREEN; a RED on a
      quiet host stays RED. An INVALID result never lands, because landing accepts only status
      green. Set: a failing fixture stage under synthetic load, the same quiet, and a passing stage
      under load. Completeness: row host-load/invalid-not-red drives the three through verify.sh and
      the landing check.
    falsified_by: >
      Report a contended RED as RED. Registered mutant host220-contended-red must fail
      host-load/invalid-not-red.
  - id: AC4
    text: >
      Claim: a contended run records no measurement: no unit leg time (VELDO-0214), no case time
      (VELDO-0215) and no case CPU or memory (VELDO-0219), so another job's load never stretches a
      later deadline or narrows a later admission. Set: a passing run under synthetic load followed
      by a quiet passing run. Completeness: row host-load/no-measurement-when-contended requires
      the stores unchanged by the first run and updated by the second.
    falsified_by: >
      Record leg and case times from a contended run. Registered mutant
      host220-records-contended must fail host-load/no-measurement-when-contended.
required_evidence: [unit, integration]
rollback: Remove scripts/gate_host.json; the gate then takes no lock, creates no scope and classifies nothing, as before.
---

## Intent

Two loaded gates on 2026-10-23 and 2026-10-24 were red while a quiet rerun passed (VELDO-0215's
intent records a worker that exceeded 120 seconds at host load 15 to 23). Suites also carry their
own timing assertions: the factory loop's scenario deadline is 45 seconds with 8-second waits, and
its ten mutants were invalid baselines in one run and valid rejections in another with the suite and
its targets byte-identical; scheduling sensitivity is the plausible cause, not a proven one. Each
such red cost a full rerun, three hours today, and was reported as the change's red. The canonical
run of 2026-10-25 was quiet (during its mutation stage the host was 60.6 percent busy while the gate
itself used 54 percent), and it passed.

The owner already serializes heavy gates with an exclusive flock on
/home/dmitry/.local/state/core-gates/.gate.lock (myday/scripts/gate_core_cand.sh). The Veldo gate
does not take it, so a core gate and a Veldo gate can overlap.

## Design

scripts/gate_host.json is the authority's host configuration, repository-owned like
scripts/gate_unconfined.json: read beside the authority, protected, not shipped to adopters. It
names the lock path, the scope's memory limit and out-of-memory score, the contention tolerance,
and the sampling period. With no file, the gate takes no lock, makes no scope and classifies
nothing, which keeps an adopter's gate exactly as today.

The load the gate needs is stated, not guessed: the configuration names the cores and memory the
gate's measured runs used (from VELDO-0216's per-node records and VELDO-0219's per-case records),
and the gate prints it on its first line. A new authority helper, scripts/gate_host.py, takes the
lock, creates the scope through the user manager (the authority runs outside every confinement, so
the user bus is reachable to it), moves the gate's own processes into a leaf of the scope so that
VELDO-0219 can make a cgroup per worker, runs the sampler, and classifies the result. The lock is an
exclusive flock on an open descriptor, released by the kernel when the gate exits on any path; the
gate also writes its process id, commit and start time to a holder file beside the lock so the next
caller can name it.

Classification looks only at results that are red. A green under load is still a pass: every
assertion held. A red under load cannot be told apart from a red the change caused without a quiet
rerun, so it is INVALID: not landable, not attributed. The quiet rerun decides. This keeps every
assertion, every case and every confinement rule as it is, and it removes only the false
attribution.

## Out of scope

How the gate uses the cores it holds (VELDO-0216, VELDO-0219); changing any suite's own timing
assertion; jobs that ignore the lock (they are measured and classified, not prevented).

## What the reviewer judges

Normal use: the owner's runners and the lander start verify.sh on this host. Threat model: as in
VELDO-0208. Candidate code cannot set the classification: it is computed by the authority from
counters outside the candidate's write grants, and an unconfined leg that forged load would only
turn its own red into INVALID, which never lands. Out of review scope: a job that holds the host
without contending in the sampled counters (for example heavy disk input and output without CPU or
memory pressure) and lock files on network file systems.

## Notes

Exit 75 is the conventional temporary-failure status, so a caller can retry later without parsing
text. Callers that wait use an environment variable naming the seconds to wait.
