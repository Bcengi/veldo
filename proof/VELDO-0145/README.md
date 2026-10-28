# VELDO-0145 proof: the UI shell, the live run terminal and the decisions screen

Built in Vue 3, TypeScript 6, Vite 8, Tailwind 4, Pinia 4, vue-router 5 and monaco-editor 0.57 (spec
amendments of 2026-10-28), with Veldo's own controls on native elements (no component library) and IBM
Plex Sans and Mono, under `engine/ui/`, served by the API from its own origin
(`engine/.veldo/control_api_ui.py`, hooked into `control_api.listen`). The UI guidelines came first and
move with the code: `engine/ui/CLAUDE.md` and `engine/ui/docs/`.

## Round 2 (after the review of 2026-10-28, NOT SOUND)

| Finding | What changed | Where it is proven |
|---|---|---|
| F1 host leg | `init_scaffold.py` (the repository's install path) lays the built UI as `<repository>/.veldo/ui`, beside the installed API module, replaced whole when the build changes; the API there serves it with no configuration. The tailnet phone leg and setup naming the UI for the systemd-installed API remain (OPEN.md items 1 and 2) | suite row `ui/installed`; `host-leg.json`: a scratch factory root laid by `init_scaffold.py`, files equal to the build, the sign-in browser file 5 of 5 green against it |
| F2 build | `npm run build` (vue-tsc, then vite) passes; the falsifier runner builds with it; ac3's mutant now also loosens the body type, since the typecheck alone refused the old one | `npm run build`; `falsifiers/*.json` (all at f5aa18e4) |
| F3 binding | The decision shows a snapshot of the presentation taken when it opened, and the answer binds to it; a newer version in the store says "This question changed", clears the choice and offers "Load the current version" instead of sending | unit `DecisionDetail.spec.ts` (two snapshot rows); e2e `snapshot binding`, `stale answer` |
| F4 out of scope | The API refuses an answer from a member whose scope does not cover the request's project as `unauthorized:out_of_scope`, before settlement | e2e `answer as a member outside the project's scope` (a steward narrows the member's scope mid-decision) |
| F5 next | `next` must match `^/(?![/\\])` (`safeNext`) | unit `router/next.spec.ts` |
| PrimeVue | Removed with its shim, preset, alias and owner decision; denied at every version; `VButton`, `VTextField`, `VTextArea`, `VRadio`, `VSwitch` are Veldo's own | suite row `ui/dependency-policy`; `docs/ui/` |
| Look | Cobalt and steel neutrals in both themes, IBM Plex Sans for titles and text, Plex Mono for the record and copied ids; tokens in `engine/ui/docs/design/colors.md` | `screens/` |
| Design review | The overview (andon board, hosts, oldest decision, inbox and runs panels); the run headline (state, elapsed, engine and model, host, station; dispatch id copyable); the inbox ranked by deadline and risk with "due in 3 d" and urgency lamps; the most urgent decision open on desktop with the list scrolling alone; a compact gutter with relative times and inline kind tags; the phone terminal (one-line strip, one control bar, the log over 55 percent of the height); unified diffs on phone; deliberate widths; no record controls over a refusal; Try again only when retryable; choices above the fold on phone; internal ids behind disclosures; shaped skeletons; one word (Done); a real badge; no duplicate theme toggle | unit `inbox.spec.ts` (ranking, due text), `overview.spec.ts` (counts), `record.spec.ts` (run facts, gutter times), `StatePanel.spec.ts` and `RunTerminal.spec.ts` (retryable); e2e `ranked inbox`, `run header`, `compact gutter`, `phone terminal`, `desktop decisions`, `phone decisions`, every screen and state at four widths |

Screens were taken from a fresh harness running `e2e/layout.spec.ts` alone with curated data (two
hosts, a blocked and a failed unit, five decisions with different deadlines and risks, paced record
times); a render that changes the factory cleans up after itself, so counts do not drift between shots. The one
exception is by necessity: `decision-refused` shows the decision it opened to be refused, so its badge
reads one more (6) until its cleanup answers it.

## How the checks run

| Layer | Command (from `engine/ui`) | What it runs against |
|---|---|---|
| Build | `npm run build` | vue-tsc over `src/` and the tests, then vite |
| Unit and component | `npx vitest run` | `src/**/*.spec.ts`, jsdom |
| Browser | `npx playwright test` | system Chrome against `e2e/harness.py`: a real SQLite authority with OpenSSH-signed membership, the real VELDO-0068 settlement and VELDO-0065 presenter (loopback Bot API), real execution records written by `control_execution_record.Recorder`, and the real `control_api.ControlApi` on the real `control_api.listen` serving the build under the real policy. Passkeys are real WebAuthn ceremonies from a Chrome virtual authenticator, verified by OpenSSL; the host's approval is the steward's signed `enroll_api_credential`. |
| Browser, installed | `VELDO_ORGANS=<root>/.veldo VELDO_UI_INSTALLED=1 npx playwright test e2e/signin.spec.ts` | the same, with the modules and the UI as `init_scaffold.py` laid them in a scratch factory root |
| API suite | `python3 scripts/selftest.py --suite 113_veldo_0145_ui` | the real ControlApi and listener with a recording authority stand-in; `ui/installed` lays a fixture build through `init_scaffold.lay_ui` |
| API mutations | `python3 scripts/check_teeth_mutations.py --finding 145` | 5 registered mutants of `control_api.py` and `control_api_ui.py` |
| UI falsifiers | `node scripts/falsify.mjs --all` | each AC's declared falsifier as an edit (`e2e/falsifiers.json`), built with `npm run build`, checked red, restored, checked green |

## Criteria and their checks

| AC | Built | Checks | Falsifier, red then green |
|---|---|---|---|
| AC1 | Passkey sign-in and the enrollment screen, the shell (rail with factory and hosts, bottom bar with a badge), session guard with a safe `next`, named refusals, page served by the API under VELDO-0171's policy, laid by the install path | e2e `signin.spec.ts` (also against the installed copy, `host-leg.json`); suite rows `ui/page-served`, `ui/unauthenticated-access`, `ui/route-trace`, `ui/installed`; unit `client.spec.ts`, `routes.spec.ts`, `session.spec.ts`, `next.spec.ts` | `falsifiers/ac1-sign-in-before-approval.json`; `falsifiers/ac1-data-before-session.json`; `mutations-api.json` `ui145-data-before-session` |
| AC2 | The run screen: the run's headline, the station strip, the terminal (every kept line in sequence, compact gutter, tool calls with inputs and results, output in mono, edits as Monaco diffs, errors marked, follow mode, search); live follow with resume from the cursor | e2e `run.spec.ts`: full detail line by line, live with a dropped connection, follow mode, station strip, run header, compact gutter; unit `record.spec.ts`, `RunTerminal.spec.ts` | `falsifiers/ac2-summary-in-place-of-record.json` |
| AC3 | The ranked inbox and the decision exactly as presented, answered inline bound to the snapshot shown, one settlement with Telegram, refusals beside the action | e2e `decisions.spec.ts`: exact presentation, ranked inbox, inline answer settles once, Telegram first (`stale_version:request_closed`), stale answer (`stale_version:stale_presentation`, then the current version answered), snapshot binding, out of scope (`unauthorized:out_of_scope`), not presented to (`unauthorized:not_owner`), choice and rationale required; unit `inbox.spec.ts`, `DecisionDetail.spec.ts` | `falsifiers/ac3-answer-without-presentation-version.json` |
| AC4 | Every screen (overview, runs, run, decisions, decision, sign-in, you) at 360, 390, 1280 and 1440 px, light and dark, in loading, empty, live, ended, error and populated states; keyboard and touch tasks; dependency policy | e2e `layout.spec.ts`: no page-wide overflow, no clipped or covered primary action, no overlapping controls, 44 px phone targets, axe (WCAG 2.2 AA), zero policy violations, phone decisions at 360, phone terminal, desktop decisions, keyboard-only desktop, touch phone, served assets; suite row `ui/dependency-policy` | `falsifiers/ac4-hide-answer-at-360.json`; `mutations-api.json` `ui145-tiers-admitted` |

## Files

- `review-2026-10-28.md`: the independent review this round answers.
- `host-leg.json`: the install path on a scratch factory root and the browser checks against it.
- `falsifiers/*.json`: the UI falsifiers, each with its edits, the red run and the green run.
- `unit-green.json`, `e2e-green.json`: the full green runs of this round.
- `mutations-api.json`, `red-at-59b119a1.txt`: round 1's API mutants and pre-change red run.
- `screens/`: every screen and state at 360, 390, 1280 and 1440 px, light and dark.
- `OPEN.md`: what needs the owner.

## Not proven here

- The phone leg over the tailnet with the owner, and setup naming the UI for the systemd-installed API:
  `OPEN.md` items 1 and 2.
- The canonical gate (`scripts/verify.sh`) was not run, by the owner's rule 37191; it runs on the batch.
