---
schema: veldo.spec/v1
id: VELDO-0296
title: "Declarations: the installation's space section"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: []
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_config.py"
  - ".veldo/control_space_config.py"
  - "engine/.veldo/installation.py"
  - ".veldo/installation.py"
  - "scripts/suites/*_veldo_0296_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0296-declarations-the-installations-space-section.md"
  - "specs/index.md"
  - "proof/VELDO-0296/**"
behavior_bearing: true
observability:
  logs: >
    A refused section is logged with the key and the reason: missing, malformed or unknown. Key names
    only; no value is logged.
  error_taxonomy: >
    A missing key is installation_missing with the key's name, as the installation reader already answers.
    A malformed key and an unknown key, mode included, are refused by the key's name. An installation with
    no space section is not an error: space management is off.
acceptance_criteria:
  - id: AC1
    text: >
      An installation with no space section has space management off and is not refused
    falsified_by: >
      Refuse an installation without the section; the row that reads the fixture installation with none is
      refused and fails
  - id: AC2
    text: >
      With the section present, a missing key is refused by name and a malformed one by name
    falsified_by: >
      Give a missing floor a built-in value; the row with the floor key left out is accepted and fails
  - id: AC3
    text: >
      The fixture installation's protect list, read back, holds each of its entries: an engine image
      folder, a repository folder, name patterns for a volume, a container, an image and a network, two
      compose project names and two image names, each returned for both of the fixture's engine contexts
    falsified_by: >
      Remove one entry from what the reader returns; that entry's row fails
  - id: AC4
    text: >
      The section has no mode key, and one written into it is refused as unknown, so an edit of the file
      cannot look like a mode switch
    falsified_by: >
      Accept a mode key and ignore it; the row with mode: act in the section is accepted and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. No installation is read for a space section, which is the same as space management
  off.
---

## Intent

The installation says whether space management is on and with what: pools and their floors, engines,
scratch and build roots, plain repositories, client accounts and the protect list. This ticket is the
reader for that section. It refuses a bad section by the key's name and treats a missing section as space
management off.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.8 (the installation's space
section), 7 (the protect list) and 11 (the protect list table). Section 12 of the design holds the ticket
itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Declarations reader. The project's space file is VELDO-0338.

Build order. It is one of the first five tickets, built in the order 0296, 0338, 0297, 0326, 0331. The
design states no dependency for this ticket, and it is the first in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: VELDO-0344 adds one key to the installation's space section, process_reader: the word
  none or the SHA-256 digest of the process reader the owner installed (design 6.8 and 7.1). It is
  built by that ticket, not here. No acceptance criterion changed.
