# VELDO-0145 proof: the UI shell, the live run terminal and the decisions screen

Built in Vue 3, TypeScript 6, Vite 8, PrimeVue 4.5.5 (unstyled), Tailwind 4, Pinia 4, vue-router 5 and
monaco-editor 0.57 (spec amendment of 2026-10-28, owner Telegram 37226 and 37228), under
`engine/ui/`, served by the API from its own origin (`engine/.veldo/control_api_ui.py`, hooked into
`control_api.listen`). The UI guidelines came first: `engine/ui/CLAUDE.md` and `engine/ui/docs/`.

## How the checks run

| Layer | Command (from `engine/ui`) | What it runs against |
|---|---|---|
| Unit and component | `npx vitest run` | `src/**/*.spec.ts`, jsdom |
| Browser | `npx playwright test` | system Chrome against `e2e/harness.py`: a real SQLite authority with OpenSSH-signed membership, the real VELDO-0068 settlement and VELDO-0065 presenter (loopback Bot API), real execution records written by `control_execution_record.Recorder`, and the real `control_api.ControlApi` on the real `control_api.listen` serving `dist/` under the real policy. Passkeys are real WebAuthn ceremonies from a Chrome virtual authenticator, verified by OpenSSL; the host's approval is the steward's signed `enroll_api_credential`. |
| API suite | `python3 scripts/selftest.py --suite 113_veldo_0145_ui` | the real ControlApi and listener with a recording authority stand-in |
| API mutations | `python3 scripts/check_teeth_mutations.py --finding 145` | 5 registered mutants of `control_api.py` and `control_api_ui.py` |
| UI falsifiers | `node scripts/falsify.mjs --all` | each AC's declared falsifier as an edit (`e2e/falsifiers.json`), built, checked red, restored, checked green |

## Criteria and their checks

| AC | Built | Checks | Falsifier, red then green |
|---|---|---|---|
| AC1 | Passkey sign-in and the enrollment screen (registration and possession ceremonies, the pending label and fingerprint compared with the host's, sign-in only after host approval), the shell, session guard, named refusals, page served by the API under VELDO-0171's policy | e2e `signin.spec.ts`: enroll-then-sign-in, unauthenticated access, session ends, member outside a project, route trace; suite rows `ui/page-served`, `ui/unauthenticated-access`, `ui/route-trace`; unit `client.spec.ts`, `routes.spec.ts`, `session.spec.ts` | `falsifiers/ac1-sign-in-before-approval.json` (the enroll row fails: the shell appears before approval); `falsifiers/ac1-data-before-session.json` (unauthenticated access fails: `reads.decisions` answers 200); `mutations-api.json` `ui145-data-before-session` |
| AC2 | The run terminal: every kept line in sequence, tool calls with inputs and results, output in mono, edits as Monaco diffs, errors marked, follow mode, search, the station strip; live follow with resume from the cursor | e2e `run.spec.ts`: full detail (line by line against the record, raw payloads exact), live with a dropped connection mid-run, follow mode, station strip; unit `record.spec.ts`, `RunTerminal.spec.ts` | `falsifiers/ac2-summary-in-place-of-record.json` (full detail and the component test fail) |
| AC3 | Inbox and the decision exactly as presented, inline answer bound to the shown presentation version, one settlement with Telegram, refusals beside the action | e2e `decisions.spec.ts`: exact presentation, inline answer settles once and Telegram after it settles nothing, Telegram first then UI (`stale_version:request_closed`), presentation changed (`stale_version:stale_presentation`), a member it was not presented to (`unauthorized:not_owner`); unit `inbox.spec.ts`, `DecisionDetail.spec.ts` | `falsifiers/ac3-answer-without-presentation-version.json` (the stale-answer row fails: `invalid_input:fields` instead of `stale_version:stale_presentation`) |
| AC4 | Every screen at 360, 390, 1280 and 1440 px, light and dark, in loading, empty, live, ended, error and populated states; keyboard and touch tasks; dependency policy | e2e `layout.spec.ts`: no page-wide overflow, no clipped or covered primary action, no overlapping controls, 44 px phone targets, axe (WCAG 2.2 AA) with zero violations, zero policy violations, phone decisions at 360, keyboard-only desktop, touch phone, served assets; suite row `ui/dependency-policy` | `falsifiers/ac4-hide-answer-at-360.json` (phone decisions fails); `mutations-api.json` `ui145-tiers-admitted` |

## Files

- `red-at-59b119a1.txt`: the suite on the pre-change tree: three rows red by their own assertions;
  `ui/unauthenticated-access` already held there (the API refused data without a session before this
  change), so its teeth are the mutant.
- `mutations-api.json`: the API mutants, each turning exactly its named row red with a green baseline.
- `falsifiers/*.json`: the UI falsifiers, each with its edit, the red run and the green run.
- `unit-green.json`, `e2e-green.json`: the full green runs.
- `screens/`: every screen and state at each width, light at every width and dark at 390 and 1280.
- `OPEN.md`: what needs an owner decision.

## Not proven here

- The phone leg over the tailnet with the owner (AC1 asks the lead to run it once): see `OPEN.md` item 4.
- The canonical gate (`scripts/verify.sh`) was not run, by the owner's rule 37191; it runs on the batch.
