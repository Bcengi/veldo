---
schema: veldo.spec/v1
id: WARP-0315
title: Security-guard runner (reference) - B15 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B15
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A security-guard runner ships at
      engine/scripts/runners/security/security_guard_runner.py. It
      reads a fixture (a JSON list of cases, each a guard name, an input, a
      required verdict label of block or allow, and an optional per-guard config)
      and applies the named guard predicate to each input, comparing the guard's
      verdict to the label. It ships three reference guard predicates as pure
      functions (input, config) -> (blocked, reason) with no I/O: is_ssrf_target
      (blocks internal, loopback, link-local including 169.254.169.254, private,
      and non-global addresses, and non-http(s) schemes such as file://),
      is_path_traversal (blocks a dot-dot escape such as ../../etc/passwd and an
      absolute path outside an allowed root such as /etc/passwd), and
      is_secret_leak (matches recognizable credential formats: an AWS-style
      access key, a Google API key, a GitHub or Slack token, a JWT, a bearer
      token, and a PEM private-key header).
  - id: AC2
    text: The passing fixture
      (engine/scripts/runners/security/fixtures/pass.security.json)
      exits 0. It is a correctly-labeled corpus that exercises all three guards
      in both directions (SSRF targets and a public host, a traversal and an
      in-root file, secrets and ordinary prose); every guard verdict matches its
      label, so security_guard_runner.py on that fixture exits 0. Every fixture
      value is an obviously-fake example (the canonical AWS example key, a bare
      key header, a documentation IP), never a real credential.
  - id: AC3
    text: The deliberately-failing fixture
      (engine/scripts/runners/security/fixtures/fail.security.json)
      exits 1 with the failure named. It allowlists the 169.254.169.254 cloud
      metadata endpoint through the guard config (a config hole) while the corpus
      still labels that host block, so the hostile input slips through and the
      runner exits 1, printing a SECURITY BYPASS line naming the input. A hostile
      input the guard allows is graded a bypass and a benign input it blocks a
      false positive, so a runner that could only ever say PASS is impossible: the
      labeled corpus is the source of truth and a slip-through fails the run.
  - id: AC4
    text: The assertions reflect real observed behavior and the control logic is
      unit-tested in scripts/selftest.py with no external dependency (no network,
      no filesystem, no live service). Each guard is exercised in both directions,
      the runner's grading is shown to name a bypass, a false positive, and config
      errors (an unknown guard or a bad label), and a config hole (an SSRF host
      allowlist and an emptied secret pattern set) is proven to let a hostile
      input through. Both shipped fixtures are driven end to end (pass -> exit 0,
      fail -> exit 1 with the SECURITY BYPASS named). All prior selftest cases keep
      passing and the gate stays green.
  - id: AC5
    text: The runner is generic - zero company or product names in the runner,
      fixtures, wrapper, or README - and .veldo/capabilities.yaml (template and
      repository instance, kept byte-identical) declares it status reference (a
      shipped reference wired per repo to its own guards, corpus, and patterns;
      the veldo home repo has no request-taking surface of its own to guard),
      never mechanical. The docs-hygiene, secret, lint, and template-sync gates
      stay green.
required_evidence: [unit, operational]
rollback: git revert; B15 adds a new runner file, a fixture pair, a wrapper and a
  README under engine, a selftest block, and an honest capabilities
  entry (template and instance) - no protected gate script or enforcer is touched,
  so reverting removes the reference artifact and its unit block with no effect on
  any running gate; the prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B15 is the security surface. The outcome that should become true is that
a repository can drive its security guards with the attacks themselves and get
proof that each attack is stopped: an SSRF request at an internal or cloud
metadata address is blocked, a path-traversal escape is blocked, and a leaked
credential is detected. A guard is only as good as the attacks it actually stops,
so a happy-path unit test that never sends it a real attack string is no proof.
This runner sends a labeled corpus of hostile and benign inputs at the guard and
fails the run naming any hostile input that slips through, because a hostile input
the guard allows is a security bypass, the worst kind of silent green.

## Context

B15 of PLAN-0003, feature F6 (security and safety surfaces), pulled against plan
revision 2, with no dependency. It follows the shipped runners' pattern: a
generic reference under engine/scripts/runners/, a fixture PAIR (a
correctly-labeled passing corpus and a deliberately-failing corpus with a config
hole), a wrapper, a README, and a unit block that gate-tests the control logic
with pure guard predicates and no live surface. The guards are the common web
attack classes: SSRF (a request the server makes to an attacker-chosen internal
address), path traversal (a file path that escapes its sandbox), and secret
leakage (a credential exposed in text). The config is a seam (an SSRF host
allowlist, a path root, a replacement pattern set) so an adopting repo adapts and
extends each guard for its own threats.

## Out of scope

DNS resolution and therefore DNS rebinding and resolve-then-connect races: the
reference guards classify literal hosts deterministically and document that a
production SSRF guard must resolve every host and re-check each resolved address.
Arbitrary high-entropy secret detection (the reference matches known credential
formats, which have far fewer false positives). A live request-taking surface in
the home gate, because the veldo repo takes no requests of its own; the honest
evidence is the pure-predicate control-logic test. This spec adds no enforcer and
touches no protected path.

## Notes

Why reference (not mechanical): the veldo home repo has no request-taking surface
of its own to guard, so the honest evidence is the fake-corpus unit tests, not a
live run against a real endpoint. required_evidence is [unit, operational]: unit
is the selftest control-logic block, operational is the two shipped fixtures
driven end to end through the runner (pass -> exit 0, fail -> exit 1 with the
bypass named) via test_security_guard_runner.sh. capabilities.yaml states status:
reference, never mechanical.

The adversarial properties a reviewer should confirm by rerunning the selftest
and driving the fixtures: (1) each guard blocks its hostile inputs and allows its
benign controls (SSRF metadata, loopback, private, and non-http scheme blocked, a
public host allowed; a dot-dot and an absolute escape blocked, an in-root file
allowed, and the /data vs /database prefix trap not fooled; an AWS key, a PEM
header, and a JWT blocked, ordinary prose allowed); (2) a hostile input the guard
allows is named a SECURITY BYPASS and a benign input it blocks a false positive;
(3) a config hole (an SSRF allowlist entry, an emptied secret pattern set) is
proven to let a hostile input through, which is exactly what the failing fixture
demonstrates; (4) an unknown guard or a bad label is a config error, never a
vacuous pass.
