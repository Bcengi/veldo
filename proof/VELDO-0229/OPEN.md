# VELDO-0229: open items

Status: REMAINING (review and the canonical gate). The build, the restyle to the owner's template look (Telegram
38255) and the local verification are done as README.md records; what is left is below.

## REMAINING

1. **The canonical gate.** `bash scripts/verify.sh` was not run by the build (the brief for this round says not to
   run it; the shared host's gate lock is held by the batch gates for hours at a time). Green is the only done.
2. **Independent review** in a fresh context (CLAUDE.md rule 5), including the visual taste judgment the spec
   files out of review scope.
3. **Owner's look check.** The screenshots in screens/ are the evidence for AC2 and AC5; the owner judges whether
   the look matches the template's gallery.
4. **PDF rendering** is not affected (no docs/ change).

## Choices the reviewer should check

- Nuxt UI's dashboard layout components (UDashboardGroup, UDashboardSidebar, UDashboardPanel, UDashboardNavbar)
  were weighed and not used, as 38255 allows ("if they fit"): UDashboardGroup fixes the frame (`fixed inset-0
  overflow-hidden`) and UDashboardSidebar hides below 1024 px and replaces the phone's bottom bar with a slide-over,
  which would change the scrolling (the run record's and the decisions panes' heights, the phone's pinned answer
  bar) and the phone flow the specification keeps. The rail is Veldo's shell restyled; its toggle is a Nuxt UI
  UButton.
- The sidebar's expanded or collapsed state is kept for the page's lifetime and not stored: neither text asks for
  it to persist, and the theme stays the only stored preference.
- 38255 mentions a search field and pagination for tables and a period switch; none of the restyled screens has a
  table of that kind or a period, and adding them would be new behavior, which the brief excludes. The one pane
  switch the screens have (Gate and review: Changes, Old only, New only) is now a segmented strip.
- The joined summary panel of 38234 stays one panel (content), its cells styled as the template's KPI tiles; the
  runs summary of 38234 is three KPI tiles.
