# VELDO-0236: what is open after the build

Each item is outside this spec's footprint or needs a decision; none was built here.

1. Suite 71_veldo_0130_api keeps a fixed request body for every published write route
   (scripts/suites/71_veldo_0130_api.py, the `bodies` table near line 1233). The three new write routes
   (accounts.pause, accounts.resume, accounts.ceiling) have no entry, so its rows session/forgery-refused and
   routes/body-actor-refused fail with KeyError: 'accounts.pause' (proof/VELDO-0236/suites/71_veldo_0130_api.txt).
   The fix is three body entries, for example {'account': 'none', 'window': 'five_hour'}, {'account': 'none'} and
   {'account': 'none', 'window': 'five_hour', 'value': 50}. The file is not in the footprint; the full gate stays
   red until the footprint is widened to it or another ticket adds them.
2. The usage screen itself is src/views/UsageView.vue, outside the footprint (only src/features/usage/** and
   src/api/** are in it). The pacing component (src/features/usage/AccountPacing.vue), its logic (pacing.ts), the
   read (src/api/reads.ts readPacing, route accounts.pacing) and the actions (src/api/actions.ts) are built and
   tested, but mounting the component on the screen (one import, a readPacing beside readSpend, one tag) and the
   screen's browser states at 360, 390, 1280 and 1440 pixels are not done. The UI rules also ask for the screen's
   page under engine/ui/docs/views/ in the same commit; that is outside the footprint too.
3. The owner's time zone: no store record of it exists. The answers use the service configuration key
   `time_zone` (an IANA name, default UTC), read where the service builds intake (control_service) and the API
   judge (control_service_api). Where an installation declares it is the installation configuration's
   (VELDO-0253) decision.
4. Reading of "sends the operation through the API as the owner" (AC3): intake runs in the authority service, so
   the Telegram route calls the same signed control_accounts operation (pause, ceiling, resume) the API judge
   calls, as the sender, in process, rather than over the HTTP API. Both routes produce the same journal record
   type and fields (suite 139 route/ui). If the lead reads AC3 as a literal HTTP call, that is a follow-up.
5. A change beyond the literal criteria, needed for them to hold: several control_accounts.Accounts instances on
   one connection each overwrote the connection's command registry, so the last one built judged every later
   account command with its own last command. Each Accounts write now claims the registry first (`_own`).
