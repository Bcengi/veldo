# VELDO-0229: the web UI is built on Nuxt UI

Status: built and verified locally; the canonical gate and independent review remain ([OPEN.md](OPEN.md)).

## What this round changed (restyle to Telegram 38255)

The owner's newer style direction (Telegram 38255: look like the nuxt-dashboard template's gallery) replaces the
look of 38234 and 38235; everything else in 38234 and 38235 stands. Commits 62be8fa3 to b0d979b7 (integration,
wrappers, theme preference, CSP adapters, the screens' layouts, browser checks) are kept and restyled:

| Commit | Piece |
|---|---|
| 1a5ef544 | Spec: AC2's visual criterion states the template look of 38255 in place of 38234's blue primary and 14px corners |
| e7f0e2ff | Tokens and Nuxt UI theme: neutral surfaces (light #FFFFFF; dark page #171717, panels #1C1C1C), 1px neutral borders, no shadows, 8px panels, 6px controls, the main action solid inverted; `--cobalt*` renamed `--accent*`; VButton's variants neutral; the previous run's sound edits kept (Tailwind color hints, icons registered in both name forms) |
| f1c92a15 | Shell: a 52px icon rail grouped by separators, the avatar at the bottom; the panel toggle in each screen's slim 50px top bar expands it to the 240px labeled sidebar (identity, hosts, appearance, account); cards bordered again (the card's shadow token had voided Nuxt UI's ring) |
| 70e82de2 | Screens: summary cells as KPI tiles, runs summary as three KPI tiles, units in mono, neutral risk and answer boxes, a segmented pane strip, bordered panel links |
| f4ed10f4 | Browser findings fixed: secondary text #636363, toggle hidden on phones, phone run header tightened, scroll padding above the bottom bar; two tests updated to the new markup |

## Acceptance criteria

| AC | Result |
|---|---|
| AC1 Nuxt UI, wrappers, one theme preference, pinned deps | Met: unchanged from 62be8fa3; unit tests and suites 113 and 120 green |
| AC2 look (38255) and screen content (38234) | Met locally: screenshots in [screens/](screens/index.md); layout spec green; owner judges the look |
| AC3 security and behavior, CSP, contrast, focus | Met: no policy violation or foreign request; primary action contrast 17.9:1 light and 16.4:1 dark at rest, 10.4:1 and 12.1:1 on hover; focus outline checked |
| AC4 verification | Met except the canonical gate (not run, by instruction) |
| AC5 screenshots | Met: 8 PNGs and the index, labeled seeded demonstration data |

## Checks run (2026-11-01, under the gate lock, MemoryMax=10G)

- `npm run typecheck`: clean. `npm run build`: built.
- `npx vitest run`: 30 files, 132 tests passed.
- `npx playwright test` (all browser tests, including the VELDO-0145 layout spec at 360, 390, 1280 and 1440 in
  both themes, theme persistence, contrast and focus, CSP and external requests): 71 passed, 0 failed, 1 skipped
  (the screenshot spec, run on request) ([e2e-run.txt](e2e-run.txt)). The first run had 10 failures, all fixed in
  f4ed10f4 (axe contrast of secondary text on the refusal wash, the toggle overlapping on phones, the phone record
  at 54.7 percent of the height, a primary action under the bottom bar, two tests bound to old markup).
- Suites (`python3 scripts/selftest.py --suite <name>`, a partial run that exits 2 by design): 113_veldo_0145_ui
  33 passed, 117_veldo_0227_ui_location 33 passed, 118_veldo_0159_mcp_credential_form 33 passed,
  119_veldo_0163_role_team_form 36 passed, 120_veldo_0131_factory_ui 52 passed; 0 failed in each (logs
  `suite-*.log`).
- `scripts/verify.sh`: not run (this round's brief).
- Polish round (2026-11-02, the review's four low findings): You selected by link name in servers.spec.ts, every top bar Refresh the bordered neutral button, overview KPI labels in secondary text and sentence case, no lamp glow (89ded518); typecheck clean, 132 unit tests and 71 browser tests passed (1 skipped), suites 113 (33), 117 (33), 118 (33), 119 (36), 120 (52) passed with 0 failed; the eight screenshots regenerated (263d1063).
