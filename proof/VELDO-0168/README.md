# VELDO-0168 proof

`scripts/suites/86_veldo_0168_text.py` reports nineteen rows through the real signed inbox, framing,
presentation, report and intake writers, a loopback Bot API stand-in and a signed SQLite authority. No
row reads a network host other than 127.0.0.1, and no real credential is used.

## The renderer 1 fixtures

`renderer-1-receipt.json` (one message) and `renderer-1-parts-receipt.json` (three parts cut by the
earlier chunker) are receipts recorded by the renderer before this change: the current suite file was
run against `git archive` of main at ad91698948dd1d894c0f6af4702b8a4b93c9694e, whose presentation
module is the one of the branch base, with `VELDO_0168_CAPTURE` and `VELDO_0168_CAPTURE_PARTS` naming
where to write the first presentation receipt and the soft-cut one. Neither names a renderer version,
and both are published receipts. The `receipts/earlier` row requires each to recheck cleanly under
renderer 1 while the current renderer shows its bound fields differently.

## Red and mutations

`drive.py --red ad916989` ran the current suite once against that archive: all nineteen rows failed,
each by assertion (`red-at-ad916989.json`). `drive.py` with no argument ran every finding 168 mutation
registered in `scripts/check_teeth_mutations.py` beside a baseline and a no-op copy of each of the six
modules: every mutation turned its named rows red by assertion and every control stayed green
(`mutations.json`, one `.diff` per mutation).

## A decision made while building

Telegram trims the spaces and line breaks at both ends of a message, and the receipt binds the exact
bytes shown, so a part ending in whitespace would come back from the platform as other bytes and be
recorded as a presentation mismatch. The branch as Codex left it kept the whitespace at a soft cut at
the end of the earlier part. A soft cut is now made at the start of the last whitespace run in reach, so
the run opens the next part after its part line, and the whitespace that begins or ends a whole
message (an inbox item whose brief ends in spaces, or a body part standing alone before the choices) is
shown escaped like any other invisible character. The `lines/edges` row holds this, including that no
message the stand-in received begins or ends with a space or a line break.
