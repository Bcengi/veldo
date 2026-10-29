# VELDO-0145: open items for the owner (round 3)

Round 2 closed the review's findings F2 to F5, dropped PrimeVue, rebuilt the look around blue and IBM
Plex, and delivered the in-footprint half of F1. Round 3 closed the fix-check's N1 to N4 (records under
`round3/`): the out-of-scope refusal has a gate row and a mutant, laying the UI is opt-in (`--ui`) and
ignored by the target repository, the phone run headline wraps, and the fixture records name their own
units. What is left needs the owner's phone and the owner's approval of the draft spec VELDO-0227.

## 1. The phone leg over the tailnet (AC1): owner and lead, once

AC1 asks the lead to run the phone enrollment and sign-in once with the owner over the tailnet and
record it. Everything before it is proven: in Chrome with a virtual authenticator against a real
factory harness, and (round 2) against the UI exactly as the repository's install path lays it on a
scratch factory root (`host-leg.json`).

Steps, in order. Run the host commands as the factory's owner account on the factory host.

1. Build the UI and lay it in the factory workspace (laying it is opt-in, so `--ui` is required):
   ```
   cd <veldo checkout>/engine/ui && npm ci && npm run build
   python3 <veldo checkout>/.veldo/init_scaffold.py --ui <factory workspace>
   ```
   The second command prints `factory UI laid at <factory workspace>/.veldo/ui (N files)`. The directory
   carries its own `.gitignore`, so the workspace repository never lists or commits it.
2. Point the installed API at that directory (item 2: a manual step until VELDO-0227 lands): in the
   API process configuration under the installation's `config/` directory (the file `veldo factory
   setup` wrote for the `veldo-api-*` unit), add `"ui": "<factory workspace>/.veldo/ui"` inside the
   `api` object. Then restart the API unit:
   `systemctl --user restart veldo-api-<service id>.service`.
3. On the host, check the page is served: `curl -sI https://<host tailnet name>/sign-in` answers
   `200` with a `Content-Security-Policy` header. (`missing_evidence:ui_not_built` means step 1 or 2
   did not land.)
4. On the owner's phone (on the tailnet), open `https://<host tailnet name>/sign-in`. Tap "Add a passkey
   on this device", name it (for example "Owner phone"), and create it with the phone's screen lock.
5. The phone shows the pending passkey's name and fingerprint. On the host run `veldo factory passkey`;
   read the fingerprint aloud group by group against the phone and approve only that registration.
6. On the phone tap "Sign in with this passkey". The overview opens with the andon board.
7. Open a run from Runs (watch its record), open a decision from Decisions (do not answer unless it is a
   real one), then You, "Sign out".
8. The lead records the date, the host name, the phone model and browser, the passkey name and
   fingerprint prefix, and the outcome of each step in `proof/VELDO-0145/phone-leg.md`, with a phone
   screenshot of the overview and of the pending fingerprint.

## 2. Setup naming the UI for the installed API (F1, outside this footprint): drafted as VELDO-0227

In this spec: `init_scaffold.py --ui` lays the built UI as `<repository>/.veldo/ui` (replaced whole when
the build changes, ignored by that repository, and only when asked: a plain scaffold lays none), and the
API module installed beside it serves it with no configuration (`control_api_ui.directory`). Proven by
the suite rows `ui/installed` and `ui/scaffold-opt-in` and by the sign-in browser checks run against a
scratch factory root laid by `init_scaffold.py` (`host-leg.json`: the laid files equal the build, 5 of 5
green). Without a build the report names the step: build in this checkout's `engine/ui`, or, from a
composed pack (which carries no UI source), build and lay from a Veldo source checkout.

Not done, because the files are outside this spec's footprint: `veldo factory setup` installs the API
from a copy of the modules in the installation's `bin/` (`control_service.install`), which does not
carry `ui/`, and writes the API process configuration (`control_factory_setup_api.process_config`)
without a `ui` key. Until a follow-up spec teaches setup to write `"ui": "<workspace>/.veldo/ui"` (or to
copy the laid UI beside the installed module), step 2 of item 1 is a manual edit. Filed in round 3 as
the draft spec `specs/VELDO-0227-factory-setup-tells-the-api-where-the-ui-is.md` (status draft, not
implemented): setup writes `"ui": "<workspace>/.veldo/ui"`, upgrades a configuration that lacks only that
key, and reports whether a built UI is there. Decide: approve VELDO-0227 (or amend it). AC1 of this spec
waits on it for "the owner opens it on his host" without a hand edit.

## 3. Out-of-scope answers (F4, decided)

Decided by the owner: the AC3 row is now exercised as written, and (round 3) the gate runs it: suite 113
row `ui/out-of-scope` answers over the API as a narrowed member of a real factory, and the registered
mutant `ui145-out-of-scope-answered` (the branch removed) turns it red. A project owner (`mover`) opens a
decision presented to them; a steward narrows their scope to another project; their answer is refused
`unauthorized:out_of_scope` beside the action and nothing settles. The API names this refusal before
settlement (`control_api_authority.py`, the `answer_decision` branch); before this round such an answer
was refused as a stale presentation. A member it was never presented to is still `unauthorized:not_owner`
(its own row).

## 4. The stack named by PLAN-0019 C16, VELDO-0131 and VELDO-0179

Unchanged from round 1: those documents still name React (and 0131's AC4 allowed list names shadcn/ui,
TanStack Table, React Flow, Chart.js). This screen set is Vue with no component library. Decide the Vue
equivalents for 0131's remaining screens (tables, the workflow canvas, charts) when that plan is
revised; each must pass the same dependency policy (no free and paid tiers, no Chinese-origin library).

## 5. Monaco's style shim

Kept (round 1 item 2, the reviewer agreed): the API's policy stays exactly VELDO-0171's, and Veldo's
module writes Monaco's styles through the CSS object model. With PrimeVue gone it is the only shim, and
the browser checks assert zero policy violations on every screen and state.

## 6. Package origins

Vue, Vite, Vitest, vue-router and Pinia are maintained by the Vue and Vite teams; the owner chose Vue
explicitly. IBM Plex is IBM's (United States, OFL-1.1), packaged by Fontsource. The policy records each
direct package's origin, license and tier; no package from the deny list is installed.

## 7. A file outside this footprint (round 3)

`specs/VELDO-0227-factory-setup-tells-the-api-where-the-ui-is.md` (and its line in `specs/index.md`): the
draft spec the fix-check asked to be filed for item 2, written at the lead's request. It changes no
behaviour and is not implemented.

