# VELDO-0246 pilot design: the workflow canvas

Six static screens for the owner's OK before any build (a to d first, e and f added for Telegram 39079) (Telegram 39072: "UI Canvas for this needs to be
great! Extra effort to make UX super usable"). Content is the default social post definition of VELDO-0245
(draft copy, image, review, owner approval, schedule, publish).

| File | Screen |
|---|---|
| `a-canvas-social-post.png` | The canvas with the social post definition open, edited and not yet saved |
| `b-step-inspector.png` | The image step selected: the inspector, an inline field error, and the refused removal of the approval |
| `c-run-on-canvas.png` | One run of the definition on the same canvas, waiting on the owner |
| `d-run-phone.png` | The same run at 390 px, where the owner approves |
| `e-conditions-and-parallel.png` | Conditions and parallel work (Telegram 39079): Draft copy and Generate image at once, a Join, the Check "Mentions prices?" selected with its rule open, Yes to Legal review, otherwise straight on |
| `f-path-skips-approval.png` | The same canvas after one wrong edit: Legal review's Cleared wired to Schedule, around the approval; Save refused, the path shown in red and listed, with two fixes |

All are 1440x900 (the phone 390x844) at device scale 2. To rebuild: `python3 gen.py`, then
`NODE_PATH=<a Veldo engine/ui>/node_modules node render.mjs` (Playwright driving system Chrome at
`/opt/google/chrome`). Fonts are the UI's own Fontsource files (IBM Plex Sans Variable, IBM Plex Mono, OFL).

## Design plan

Subject: an owner who is not at a desk most of the day decides how each kind of work gets made, and must be
able to tell at a glance that nothing leaves the factory without passing them.

Color. The shell keeps VELDO-0229's neutral look (Telegram 38255): white panels `#FFFFFF`, ink `#171717`,
muted `#636363`, rules `#E5E5E5`, the main action solid inverted. The canvas adds one color of its own,
flow blue `#2E5BDA` (Telegram 37382: Veldo is built on blue), with its wash `#EDF2FD` and zone tint `#F5F8FE`.
Blue means "the flow": transitions, ports, the selection ring, drop targets and the path a run has taken. It
is never a button and never a state; state keeps green, amber and red, always with words.

Type. IBM Plex Sans for everything, IBM Plex Mono only for the live record. Step names 16/650, secondary 13
to 14, screen title 18/650 in the top bar. Sentence case, no all-caps labels.

Layout. The definition reads top to bottom, like a checklist, so the desktop canvas and the phone tell the
same story in the same order. Branches (changes asked, declined, failed) leave to the right with their
outcome named. The palette (or, in a run, the run list) is on the left; the inspector (or the run's
decision) on the right.

```
+==+===============================================================+
|  | Workflows / Social post v  Version 3  * Edited  [Design|Runs]  [undo][redo][Save as version 4]
|  +===========+====================================+==============+
|r | Add a step|  [check] Ready to save             | Inspector    |
|a | Work      |        [ Draft copy      ]<=+      | Who does it  |
|i |  Write    |              | Done         |      | What it needs|
|l |  Review   |        [ Generate image  ]  | Changes asked      |
|  | You       |              | Done         |      | Limits       |
|  |  Approval |        [ Review          ]==+      | Cost and     |
|  | Timing    |              | Passed              |  approval    |
|  | Going out |      [## Your approval ##]==> Dropped             |
|  |           |~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ barrier  |
|  |           |  Runs only after you approve                     |
|  |           |        [ Schedule ] => [ Publish ] => Published  |
+==+===========+====================================+==============+
```

The one bold element: the owner's approval is the only solid black card, wider than the rest, with a lock,
and it sits on a full-width barrier line. Everything below the line sits on a blue-tinted zone labeled
"Runs only after you approve". The rule that approval can never be skipped is visible as space, not as a
footnote. Everything else stays quiet: thin borders, no shadows, no motion except what answers an action.

Plan reviewed against the brief: the first idea was a left-to-right flow with the gate as a vertical bar.
It needed six cards across 1100 px (cards at 150 px, names wrapping) and turned into a different shape on the
phone. Replaced with the vertical flow, which fits the six steps at 100 percent and reads identically on a
phone. A numbered marker per step was dropped: branches make "step 3" ambiguous; the run says "step 4 of 6"
only along the path taken.

## Self-critique log (from the renders)

1. First render: the page was cut at about 810 px (Chrome's window size includes its own frame) and a class
   name collision boxed every step's secondary line. Rendering moved to Playwright with an exact viewport; the
   class was renamed.
2. Cards at 300 px wrapped "Generate image" onto two lines; widened to 340 (the approval to 384).
3. Screen b: the refusal callout covered Schedule and Publish. Moved beside the approval it explains, with a
   pointer, and the approval gets a red ring while the message shows.
4. Screen c: Approve, Ask for changes and Decline overflowed the 380 px panel; Approve is now full width with
   the other two below. The image card's line was cramped; it now says "2 images, $0.08 spent".
5. Phone: "1 failed, retried" lost its red to a more specific selector; fixed. The phone said "Changes"
   where desktop says "Ask for changes"; one action now has one name on both.
6. Removed a static hover highlight from the palette (a mockup should not show a hover nobody is doing).

## Conditions and parallel work (screens e and f, Telegram 39079)

The owner asked: "But what if steps are conditional, not just next next?" Three kinds of branching, all drawn
with the same cards, edges and labels as a to d:

1. A step's named outcomes (already in a to d): Passed or Changes asked, Approved or Declined, Live or Failed.
2. The Check step: a rule in plain words picked from fields (Look at, Test, Words), never code. Every branch is
   labeled on the canvas, and Otherwise is always there and cannot be removed. Its icon is the flowchart
   diamond, the one shape people already read as "a decision".
3. Parallel work: one step leads to several at once ("Both at once"), and a Join waits for all of them.

Loops stay capped (Review: up to 2 rounds). Whatever the branches, every path to Publish, Deliver or Deploy
passes the owner's approval; the canvas walks every path at save and refuses one that goes around it, naming
the path step by step (f) and offering the two fixes.

Layout choices: the flow is shown at 85 percent (Fit), the grid scaling with it, so the whole definition still
fits beside the inspector. Changes asked now returns on the left, because its target, Draft copy, is the left
card of the pair; the exits (Yes, Declined, Failed) still leave to the right. In f the one red element on the
canvas is the bypass: the edge, its labels, the cards it runs through, and a solid pill where it crosses the
approval line ("Skips your approval"), so the rule is again visible as space.

Palette: a full Flow group with descriptions measured 126 px too tall for a 900 px screen (Deliver files and
the shortcut line fell off). Check and Join are a compact Flow row of two tiles instead (descriptions as
tooltips), with group and item spacing tightened by 1 to 3 px; the palette fits exactly as before, on a, b, e
and f. Screens c and d have no palette and are unchanged.

Self-critique (e and f):

7. The first Check icon (a split line) read as a lambda; replaced with the diamond. Join kept its two-into-one.
8. f: the red Cleared label floated 100 px from its edge; moved beside it. Published got the path ring.
9. A full Flow group pushed the palette off screen; replaced with the compact row (measured, not guessed).

Open for the owner: the image prices ($0.04 an image) and engine names are illustrative, not quotes.
