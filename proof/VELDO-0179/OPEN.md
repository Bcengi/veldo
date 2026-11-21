# VELDO-0179: open items for the lead

1. RESOLVED by the lead (footprint widened, entries added): scripts/gate_unconfined.json: add `134_veldo_0179_conversation_screens` and `135_veldo_0179_conversation_layout`.
   Both are browser suites (system Chrome through Playwright, the checkout's engine/ui/node_modules) like suites 118
   to 124. In the confined leg the worker's copy has no node_modules and npm ci cannot complete, so the gate's driver
   refuses the baseline as invalid_baseline (mutation-confined-leg.txt). Until they are on the list the four finding
   179 mutation cases cannot be judged by scripts/check_gate_mutations.py; run alone unconfined through the driver's
   own worker entry, each is killed with baseline and no-op green (mutation-*.txt).
2. Neither suite needs the systemd user manager.
3. No dependency was added; package.json and package-lock.json are unchanged. One icon (`i-lucide-messages-square`,
   from the already locked @iconify-json/lucide) is added to src/ui/icons.ts for the rail entry.
4. The specification says "the React shell of VELDO-0145"; the shell is Vue 3 (the house stack in engine/ui,
   VELDO-0229), so the screens are Vue views in that shell. No requirement was added or changed.
5. On a phone the conversations list is reached from the You screen (Factory card, first link), because the
   bottom bar holds at most four destinations (src/app/navigation.ts); on a desktop the rail lists it in the
   operate group.
6. engine/ui/index.html now declares `interactive-widget=resizes-content` in its viewport, so the layout viewport
   shrinks above a phone keyboard and the pinned message box stays above it; this applies to every screen.
7. The browser harness (engine/ui/e2e/conversation_harness.py) runs turns with a fake engine of its own through the
   production conversation authority's dispatch and end commands and the real Recorder, not through VELDO-0174's
   receiver subprocess (suite 133 covers that path); the Telegram turn is the real Acquirer and intake with the
   factory PM's route document applied as suite 131 applies it (the PM run is suite 132's).
