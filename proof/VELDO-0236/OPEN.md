# VELDO-0236: what is open after the build

Items 1 and 2 were built after the footprint was widened; the rest are outside this spec's footprint or need a
decision.

1. Done (commit deb9762c, after the lead widened the footprint in 0e0b7c4f): suite 71_veldo_0130_api's `bodies`
   table carries entries for accounts.pause, accounts.resume and accounts.ceiling; suite 71 passes (71 passed).
2. Done (commit 61ae3359, same widening): the pacing component is mounted on src/views/UsageView.vue beside the
   spend read, its page under engine/ui/docs/views/usage.md, and the narrow and wide screen suites (121, 122) run.
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
6. Open, for the lead (review 2026-11-05 finding 2, outside this spec's criteria): all_limited (VELDO-0176,
   engine/.veldo/control_service.py near line 2912) counts only `blocking`, not pacing, so when every account of a
   conversation's engine is paused or capped the owner is not offered the move to the other engine; the turn waits
   until the pause ends. Worth a follow-up ticket.
