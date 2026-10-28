# Design direction

## Subject, audience, job

- **Subject.** A software factory with no lights on: agents claim specified units of work, build and
  review them at stations, and stop for a person only when a decision needs one. Its vernacular is
  the shop floor's: stations, a line, dispatches, signals, an andon board.
- **Audience.** The owner first, then members with a narrower scope. Technical, often on a phone
  between other things, sometimes at a desk watching a long run.
- **Primary job.** Say at a glance what the factory is doing and what needs you; show any run exactly
  as it happened; put the decisions waiting on you one tap from an answer.

## The idea: the andon board and the logbook

A factory floor talks through an **andon board**: one dark board where a lamp per signal lights when
something needs attention, readable from across the room. Veldo's one memorable element is that board
and its lamps. The board opens the overview (running, blocked, failed, waiting on you); the same lamp
language lights each run row, the station strip above a run, and the urgency of each decision.
Everything around it is a quiet logbook in a confident blue: plain surfaces, one sans in real weights,
and structure only where it separates things that differ.

## Palette

The owner asked for blue (Telegram 37382, 37384). Cobalt is the operating color: what you can act on,
where you are, the brand. The signals are not blue, so a state never reads as a link. The full token
set is in [colors.md](colors.md).

| Name | Hex | Role |
|---|---|---|
| Cobalt | `#2349D4` | Primary actions, links, the current place (nav, selected row), the brand |
| Navy ink | `#0E1A2E` | Text in light; the andon board in light |
| Steel paper | `#F2F5FA` | The base surface in light (a cool blue grey, not cream, not white) |
| Night | `#0D1626` | The base surface in dark (a blue night, not a tinted black) |
| Andon amber | `#F2A900` | Waiting on a person: decisions, blocked units, due within three days |
| Lamp green / stop red | `#23A15C` / `#D63B2A` | Running; failed, refused, overdue |

## Type

One family, IBM Plex, drawn by IBM to express the relationship between people and machines, which is
this product's whole subject.

- **IBM Plex Sans** (variable): every title and every piece of interface text. Normal width; titles are
  semibold at size with slightly tight tracking, never condensed, never in capitals.
- **IBM Plex Mono**: only the record in the run terminal and identifiers a person copies (dispatch ids,
  digests, the passkey fingerprint). Its zero is dotted and its l, 1 and I differ, which the
  fingerprint comparison needs.

Scale and spacing are in [typography.md](typography.md) and [layout.md](layout.md).

## Layout concept

Desktop: a rail (the wordmark, the factory's name, the destinations with a decisions badge, the hosts
with their lamps, who is signed in) and the screen. The overview opens on the board.

```
+-----------+----------------------------------------------------------+
| * Veldo   | veldo-e2e                                        Refresh |
| veldo-e2e | +------------------------------------------------------+ |
|           | | o 3        | o 1        | o 1        | o 5          | |  andon board
| Overview  | | running    | blocked    | failed     | waiting on you| |
| Runs      | +------------------------------------------------------+ |
| Decisions5| | Waited longest: Admit ...? [Answer it] | Hosts o o    | |
| You       | +---------------------------+  +----------------------+ |
|           | | Waiting on you  ranked    |  | Runs                 | |
| Hosts     | | o due in 5 h  High risk   |  | o VELDO-9146 Build   | |
| o linux-1 | | o due in 2 d  High risk   |  | o VELDO-9144 Failed  | |
+-----------+----------------------------------------------------------+
```

The run screen gives the record the remaining height; its header is the run's headline (state,
elapsed time, engine and model, host, station). Decisions are the ranked inbox beside the open
decision, each scrolling on its own.

Phone: the screen, and a bottom bar with four destinations (thumb reach) and the decisions badge. The
run screen is one header row, one facts line, a one-line strip, one control bar and the record. An
open decision puts its choices above the fold; the answer bar pins above the bottom bar only once a
choice is picked.

```
+------------------------------+
| <  VELDO-9146   o Running 2m |
| Claude Code  claude-opus...  |
| o-o-o-* Build -o-o-o         |
| 4 lines  Follow  Raw    (Q)  |
|------------------------------|
| 1 +0.0 s wrapper  veldo-...  |
| 2 +0.3 s system   init ...   |
| 3 +7.1 s [agent]  I will ... |
|                              |
| Overview Runs Decisions5 You |
+------------------------------+
```

Alignment is left everywhere; counts and gutter numbers are tabular and right aligned to their column.

## Principles

1. **The record is the product.** Never summarize it, never hide a line; the gutter carries each line's
   sequence and time, and a tag says what kind of line it is.
2. **Signal color means state, nothing else.** Amber, green and red are never decoration, and a state
   is never told by color alone (a word or shape goes with it). Cobalt means "you can act here" or
   "you are here".
3. **One bold thing.** The andon board and its lit lamps. No gradients, no glow except a lit lamp's, no
   card grid of identical tiles.
4. **Words are instructions.** Buttons say what happens ("Send answer", "Load the current version"),
   empty screens say what will appear, refusals say what happened and how to fix it. No internal
   identifier is shown to the owner unless they ask for it (behind "Dispatch id", "Who can answer this").

## Review of the plan against the brief (round 2)

The first round (green enamel, amber, Big Shoulders condensed titles) was rejected by the owner: "I
don't like colors and fonts", "I like blue and fonts that are not this tall". The review called the
screens a tidy admin page. This round's first plan was a default SaaS dashboard: Tailwind blue
`#3B82F6`, Inter, four rounded stat cards with a big number and a small label. Checked against the
brief and revised:

- **Blue, but not the framework's blue.** Cobalt `#2349D4` is deeper and more saturated than the
  default, carries white text at 7:1, and sits on cool steel neutrals so the whole page reads blue
  without being tinted. Dark mode is a blue night with a brighter cobalt (`#2F5AE6`, white text 5.6:1)
  so the primary action no longer reads as disabled.
- **Not four stat cards: one andon board.** The counts live in one joined board, the way a shop floor
  shows them, and the board itself is the bold element (navy ink in light, deep cobalt in dark).
- **Not Inter: IBM Plex.** A normal-width face chosen for the subject (people and machines), with a
  mono from the same family for the record, so the terminal and the interface feel like one system.
- **No eyebrow labels, no middle dots, no arrows on links.** Facts are separated by space; the only
  small labels are section names that a screen reader needs anyway.

## Notes for later passes

- Tried and dropped: a stat-card row with a gradient wash; a dark terminal in the light theme (it
  fought the board for attention); kind labels stacked above each record line (a third of the height).
- The board is the place for future boldness (a lamp that blinks once when its count changes), not new
  decoration elsewhere.
