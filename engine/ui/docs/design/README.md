# Design direction

## Subject, audience, job

- **Subject.** A software factory with no lights on: agents claim specified units of work, build and
  review them at stations, and stop for a person only when a decision needs one. Its vernacular is
  the shop floor's: stations, a line, dispatches, signals, receipts.
- **Audience.** The owner first, then members with a narrower scope. Technical, often on a phone
  between other things, sometimes at a desk watching a long run.
- **Primary job.** Show what the factory is doing right now, exactly as it happened, and put the
  decisions waiting on you one tap from an answer.

## The idea: andon and logbook

A factory floor talks through an **andon**: a lamp per station, lit in a signal color when that
station needs attention. Veldo's one memorable element is that lamp. It appears in exactly three
places: the station strip above a run (which station the unit is at, lit), the navigation entry for
decisions (an amber lamp when something waits on you), and the run state of each row in the runs
list. Everything around it is a quiet logbook: plain surfaces, real type, hairline structure only
where it separates things that differ.

## Palette

Six named colors carry the identity. The full token set is in [colors.md](colors.md).

| Name | Hex | Role |
|---|---|---|
| Machine ink | `#16242C` | Text in light, the base surface in dark |
| Drafting paper | `#EDF0EA` | The base surface in light |
| Enamel green | `#2E5E4E` | Brand and primary action, the paint of an old machine tool |
| Andon amber | `#F2A900` | Waiting on a person: pending decisions, attention |
| Lamp green | `#3FAE6A` | Live: a run that is running, a stream that is open |
| Stop red | `#D2412C` | Stopped with an error, a refusal |

## Type

- **Big Shoulders** (variable): screen titles and the station names in the strip. It was drawn from
  industrial signage, condensed, and set in sentence case at size, never tracked out in capitals.
- **Atkinson Hyperlegible Next** (variable): everything a person reads or operates. Designed for
  legibility, which matters on a phone in daylight.
- **Atkinson Hyperlegible Mono** (variable): the record itself (commands, output, payloads) and
  fingerprints. Its glyphs keep 0 and O, 1, l and I apart, which is the point when the owner compares
  a passkey fingerprint against the host's screen character by character.

Scale and spacing are in [typography.md](typography.md) and [layout.md](layout.md).

## Layout concept

Desktop: a narrow left rail (navigation and the account), the screen to its right. The run screen
gives the record the whole remaining height. Decisions are a list beside the open decision.

```
+--------+---------------------------------------------------------+
| Veldo  | VELDO-9130 build                                         |
|        | ( ready )( claimed )( dispatching )(*RUNNING*)( verify ) |
| Runs   +---------------------------------------------------------+
| Deci. *| [follow on] [search.........] [3 of 12]  engine stderr   |
|        |  12  10:02:11  Bash  ls -la                              |
|        |  13  10:02:12  result  total 24 ...                      |
|        |  14  10:02:13  Edit  src/a.ts   [ monaco diff ]          |
| you    |                                                         |
+--------+---------------------------------------------------------+
```

Phone: a top bar with the screen title and a back action, the screen, and a bottom bar with the
three destinations (thumb reach). The answer action of a decision is pinned above the bottom bar.

```
+------------------------------+
| < Decisions     Decide de1   |
|------------------------------|
| question text                |
| ( ) accept                   |
| ( ) return for elaboration   |
| ( ) reject                   |
| [ rationale ............ ]   |
|------------------------------|
| [      Send answer       ]   |
|  Runs   Decisions*   You     |
+------------------------------+
```

Alignment is left everywhere; numbers in the record gutter are right aligned to their column.

## Principles

1. **The record is the product.** Never summarize it, never hide a line; structure helps reading but
   the line is always there with its sequence, time and stream.
2. **Signal color means state, nothing else.** Amber, green and red are never decoration, and a
   state is never told by color alone (a word or shape goes with it).
3. **One bold thing.** The lit lamp. No gradients, no glow except the lit lamp's, no card grid.
4. **Words are instructions.** Buttons say what happens ("Send answer", "Sign in with passkey"),
   empty screens say what to do next, refusals say what happened and how to fix it.

## Review of the first plan against the brief

The first pass picked a near-black canvas with a single bright green accent for "live", JetBrains
Mono throughout and small capital labels over each panel. That is the generic dark-dashboard default
(a near-black ground with one acid accent, a monospace face for every label, tracked capitals), not
something this subject asked for. Revised:

- The canvas became machine ink, a blue-green slate taken from machine paint, with a light theme on
  drafting paper that is a first-class equal rather than an inverted afterthought.
- The accent split by meaning: enamel green is the brand; amber, lamp green and stop red are signals
  only, borrowed from the andon the shop floor already uses.
- Monospace is kept for machine text only (the record and fingerprints), and the mono face was chosen
  for character disambiguation, which the passkey comparison needs.
- Panel labels were dropped; headings are sentence case in Big Shoulders where a heading is needed.

## Notes for later passes

- Tried and dropped: a glow on every live element. It competed with the lit lamp; only the lamp
  glows now.
- The strip is the place to spend future boldness (for example a lamp that blinks once when a
  station changes), not new decoration elsewhere.
