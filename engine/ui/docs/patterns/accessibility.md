# Accessibility

The bar is WCAG 2.2 AA, checked on the real page by axe in the e2e tests and by hand with a
keyboard. The rules below are the ones that matter most for these screens.

1. **Landmarks.** The shell has `nav` (labeled "Main"), `main`, and on phone the bottom bar is the
   same `nav`. Each screen has one `h1`.
2. **Names.** Every control has an accessible name from its visible label. Icon-only buttons get
   `aria-label`. Lamps have a text alternative ("running", "waiting on you").
3. **Targets.** Primary actions and navigation entries are at least 44 by 44 CSS px on phone. Dense
   toolbar controls on desktop may be 32 px tall but never smaller than 24 px.
4. **Contrast.** See [../design/colors.md](../design/colors.md). Measured, not assumed.
5. **Live regions.** The terminal's new lines are not announced one by one (that would be noise);
   the toolbar's line count and state ("Live", "Ended", "Reconnecting") are a polite status region.
   Answer outcomes are `status`, refusals `alert`.
6. **The record as a list.** The terminal body is a `role="log"` region containing an ordered list;
   each line is a list item whose name starts with its sequence number.
7. **Forms.** Choices are a `radiogroup` with a legend (the question); the rationale is a labeled
   textarea with its requirement stated in the label, not only in an error.
8. **Reduced motion.** `prefers-reduced-motion: reduce` disables every transition and the lamp ease.
9. **Zoom and reflow.** At 400 percent zoom on desktop (320 px equivalent) nothing is lost; this is
   the same layout as the 360 px phone.
10. **Language.** `<html lang="en">`. User-facing text is English and sentence case.
