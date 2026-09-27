---
schema: veldo.spec/v1
id: VELDO-0168
title: Telegram presentations keep their line breaks, show invisible and direction characters escaped, and mark a cut inside a long token
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W128
plan_revision: 4
depends_on: [VELDO-0064, VELDO-0065, VELDO-0128]
placement: [contracts, tracker, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_channel_presentation*.py"
  - ".veldo/control_channel_presentation*.py"
  - "engine/.veldo/control_channel_projection*.py"
  - ".veldo/control_channel_projection*.py"
  - "engine/.veldo/control_intake.py"
  - ".veldo/control_intake.py"
  - "engine/.veldo/control_telegram_report*.py"
  - ".veldo/control_telegram_report*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0168_*.py"
  - "scripts/suites/60_veldo_0064_inbox.py"
  - "scripts/suites/62_veldo_0065_presentations.py"
  - "scripts/suites/72_veldo_0128_reports.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0168-telegram-text-shown-as-written.md"
  - "specs/index.md"
  - "proof/VELDO-0168/*"
behavior_bearing: true
observability:
  logs: >
    Record, per presentation or report, the renderer version, the count of characters shown escaped by
    class and the count of hard cuts; never the escaped text itself beyond what the receipt already holds.
  metrics: >
    Count presentations and reports sent, escaped characters by class, and hard cuts.
  traces: >
    Join each sent message to its receipt, renderer version and part number.
  error_taxonomy: >
    Distinguish a receipt that fails its recheck under its own renderer version from one naming a
    renderer version this engine does not know; neither is reported as delivered.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Text the owner reads on Telegram keeps the line breaks it was written with. Set and
      completeness: The set is every renderer whose text is sent to Telegram, found by listing every call
      of the Bot API send in the engine and tracing its text back: the decision presentation
      (control_channel_presentation.render), the inbox presentation (control_channel_projection.render),
      the reports (control_telegram_report), and the intake question prompt
      (control_intake.py, _ask's asker.send of question['prompt']); the suite holds that list and fails
      on a send it does not name. In each, a brief, risk statement, report body or question prompt keeps its line breaks, with a carriage return
      and line feed pair shown as one break, and nothing inside a line is collapsed: runs of spaces are
      kept as written, and a tab is shown escaped by AC2's rule, never collapsed or turned into a space.
      A three-line brief renders as three lines in each renderer, and a line holding two spaces and a tab
      keeps both spaces and shows the tab as `<U+0009>`. Falsifier: Restore the whole-text
      whitespace collapse in the decision presentation's brief, and its three-line row must fail.
    falsified_by: >
      Restore the whole-text whitespace collapse in the decision presentation's brief, and its three-line
      row must fail.
  - id: AC2
    text: >
      Claim: Two values that differ only in characters the owner cannot see never look the same to him.
      Set and completeness: In every renderer of AC1, each character of Unicode general category Cf
      (format, which includes the zero-width characters, the byte-order mark and the bidirectional
      embedding, override and isolate controls), of category Cc other than the line break (the tab and a
      carriage return outside a carriage return and line feed pair included), of categories Zl and Zp,
      and of category Zs other than U+0020 (the non-breaking space U+00A0 and every other space
      character) is shown as its code point in the visible form `<U+XXXX>`; the set comes from the
      category table of the running Python's unicodedata, so no list is kept by hand. The escape is one to
      one: a literal `<` that begins `<U+` in the text is itself shown as `<U+003C>`, so every shown text
      maps back to exactly one original. A choice name, a scope and a subject reference that differ from
      another only by U+200B, U+202E, U+2066, a tab in place of a space, U+00A0 in place of a space, or
      the written characters `<U+200B>` in place of U+200B each render differently from it. Falsifier:
      Pass U+200B through unescaped, and the zero-width row must fail.
    falsified_by: >
      Pass U+200B through unescaped, and the zero-width row must fail.
  - id: AC3
    text: >
      Claim: When a presentation must cut a token that has no whitespace in reach, the cut is marked. Set
      and completeness: The decision presentation's split into parts (control_channel_presentation._chunks)
      cuts at whitespace when there is any in reach; when it cuts inside a token instead, the part ends
      with the marker `[cut inside a word, continues in the next part]` and the next part begins with
      `[continued]`, both inside the platform limit, and a cut at whitespace carries no marker. Render a
      brief holding one 9,000-character token and one of ordinary words. Falsifier: Drop the marker at a
      hard cut, and the long-token row must fail.
    falsified_by: >
      Drop the marker at a hard cut, and the long-token row must fail.
  - id: AC4
    text: >
      Claim: A receipt recorded before this change still verifies. Set and completeness: The receipt names
      the renderer version it was rendered with; a receipt that names none was rendered by the version
      before this change, and its recheck (receipt_problems) recomputes its text with that version's
      renderer, while new receipts name and use the new one. Recheck a receipt recorded before this change
      (a stored fixture made by today's renderer) and one recorded after it. Falsifier: Recheck
      every receipt with the new renderer, and the earlier-receipt row must fail.
    falsified_by: >
      Recheck every receipt with the new renderer, and the earlier-receipt row must fail.
required_evidence: [unit, integration]
rollback: >
  New presentations go back to the earlier renderer version, which receipts of both versions keep naming;
  nothing already sent or recorded changes. No automatic rollback is authorized.
---

## Intent

The owner reads a brief on his phone laid out as it was written, and cannot be shown two values that look
identical but bind to different things.

## Context

W128 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3. The review of
VELDO-0149 (rv149b) filed that the Telegram presenter collapses every run of whitespace, line breaks
included (`' '.join(text.split())`), so a multi-line brief reaches the owner as one run of text, and
asked, before first use, for line breaks to be kept, invisible and direction characters shown escaped,
and a hard cut inside a long token marked. The presentation's receipt binds the exact bytes shown, so
escaping keeps the binding honest: what he sees distinguishes what he answers. This new specification is
draft; authoring it supplies neither implementation proof nor operational activation.

## Out of scope

Splitting long reports into parts (filed for VELDO-0128); markup or rich text; how the owner's typed
answer is matched against a choice (VELDO-0065's folding, unchanged); other channels.

## What the reviewer judges

- Normal use: the factory sends the owner a decision presentation, an inbox item or a report on Telegram,
  and he reads it on his phone.
- Threat model: a brief shown without its line breaks; two values that differ only by an invisible or
  direction character, a tab, a non-breaking or other space, or a doubled space shown alike; text that
  spells an escape shown like the character it names; a cut inside a token that looks like the token's
  end; an earlier receipt that no longer verifies. The owner's account, the store and Telegram are
  trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as
  confusable letters from different scripts, which are visible characters; fonts on his phone; a platform
  limit change.

## Notes

Escape at render time only: the stored brief, the digests over the request and the choice matching read
the original text. The escaped form is plain text, since the presentations carry no markup.

## History

2026-09-27: new draft from the follow-up ticket filed on the review of VELDO-0149 (rv149b). A draft: only
the owner marks a specification ready.

2026-09-27: amended on the independent check of this batch. AC2's escape is one to one: the literal
`<U+` prefix is itself escaped, so the written characters `<U+200B>` and the real U+200B never look the
same. One rule for the tab in both criteria: it is escaped as `<U+0009>`, never collapsed, and AC1 no
longer collapses runs of spaces, which would make two values differing by a doubled space look alike.
The non-breaking space and every other Zs space but U+0020 are escaped. Still a draft.
