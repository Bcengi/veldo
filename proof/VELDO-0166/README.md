# VELDO-0166 proof

Branch `build-veldo-0166`, based on `582cc961`, with main merged at `f2526112` (VELDO-0154, 0158, 0165,
0169 and 0172 among it). Implementation `f6e0654f` by Codex, finished after its usage limit in `0ada81fa`
and the commits after it.

**The meter.** A Claude Code `rate_limit_event` becomes one window observation for the window
`rateLimitType` names, carrying the event's own status (normalized to allowed or rejected as before),
reset and utilization, and one for every other readable entry of `unifiedWindows`, carrying that entry's
reset and utilization and no status, because the event rated only the window it names. In the live line
the named window's own fields equal its `unifiedWindows` entry; the meter takes them from the event's
top level. Each observation keeps the raw line as its receipt, with its digest. A missing reset stays
null; an unreadable entry gives no observation.

**Why the named window reads the top level.** After the merge, VELDO-0172's shared fake constructors fill
a `unifiedWindows` map with zero values into every fake rate-limit line that lacks one. Codex's first
version read the named window from that map, so a fake five-hour rejection was recorded with reset 0 and
utilization 0, and suites 0062 (`usage/rate-limit-reset`) and 0160 (five rows) went red. Reading the
event's own fields for the window it names is faithful to the live line and to every older line.

**A rejection in force is kept.** The account writer accepts an observation with no status. Such an
observation never replaces a recorded rejection whose reset has not passed (VELDO-0160's `blocking`
decides): only a rating of that window, or its reset, lifts it. Without this, an event rating seven_day
beside a five-hour window at its limit would erase the five-hour rejection and hand the account work
before its reset (suite 0160 `pool/until-earliest` went red on exactly that). A rejection whose reset
has passed is replaced by the report as it came.

**The profile helper** chmods only a directory it creates, 0700. A directory that already exists keeps
its mode and contents. The persisted record names the directory and whether it was `created` or
`existing`. The three changed modules are byte-identical to their `engine/.veldo` copies.

The spec footprint adds `control_accounts.py` and its engine copy, since the writer must accept an
absent status and keep a rejection in force. The proof driver is `proof/VELDO-0166/drive.py`.

## Rows

Suite `83_veldo_0166_usage_windows`, seven rows, each reported once. It drives the real `Metering`
receiver seam, the `Accounts` writer and production membership authorization over a signed SQLite store
with a generated journal key, profiles and receipt directories. No engine, login or credential.

| Criterion | Row | Evidence |
| --- | --- | --- |
| AC1 | `windows/five-hour` | The verbatim 2.1.281 line records five_hour (0.3, 1790487000) and seven_day (0.7, 1790960400) on the account, one raw receipt and digest per observation, bound to the dispatch and account. |
| AC1 | `windows/qualified-set` | Every window the 2.1.281 qualification lists is stored exactly once with its own values. |
| AC1 | `windows/status-only-named` | Rejected, allowed_warning and allowed apply only to seven_day, the named window; companions hold no status and `blocking` names only seven_day on a rejection. |
| AC1 | `windows/missing-reset-receipts` | A companion without a reset stays null, an unreadable entry is skipped, a named window absent from the map is still recorded, receipts and attribution intact. |
| AC1 | `windows/rejection-kept` | A five-hour rejection in force survives a later seven_day event beside it and still blocks; a rejection whose reset has passed is replaced by the companion's values. |
| AC2 | `profiles/existing` | For both providers a generated 0755 directory keeps its mode, file bytes, mtime and entries, recorded `existing`. |
| AC2 | `profiles/created` | For both providers a missing directory is created exactly 0700 under umask 022, recorded `created` and resolvable. |

Suite 75 (`75_veldo_0062_accounts`) prints the spec's live line verbatim through a shared VELDO-0172
constructor (`c_live_rate`, `live_step`), every field of it, both windows included, and its
`attribution/stored-account` row checks the five-hour window reached acct-c1 through the real Runner and
receiver with its reset, utilization, dispatch and no status. Its teardown `conform_fake` compares the
line against the live capture (`fake/capture:0062_accounts`).

## Red record and mutations

`proof/VELDO-0166/drive.py` with its red option and `582cc961` archives the unchanged pre-change
tree and runs the current suite against it: `red-at-582cc961.json` records all seven rows red by assertion.

`proof/VELDO-0166/drive.py` writes `mutations.json`: a green baseline, green unmodified copies of each
module, and twelve finding-166 mutations each red on its named rows by assertion, with its exact diff.

| Mutation | Named rows |
| --- | --- |
| `windows166-named-only` (AC1 declared falsifier) | `windows/five-hour`, `windows/qualified-set` |
| `windows166-named-only-journey` (same edit, suite 75) | `attribution/stored-account` |
| `windows166-existing-chmod` (AC2 declared falsifier) | `profiles/existing` |
| `windows166-status-spills` | `windows/status-only-named` |
| `windows166-allowed-invented` | `windows/status-only-named` |
| `windows166-named-twice` | `windows/qualified-set`, `windows/status-only-named` |
| `windows166-reset-borrowed` | `windows/five-hour`, `windows/qualified-set`, `windows/missing-reset-receipts` |
| `windows166-utilization-borrowed` | `windows/five-hour`, `windows/qualified-set` |
| `windows166-absent-status-refused` | `windows/five-hour`, `windows/status-only-named` |
| `windows166-rejection-lifted` | `windows/rejection-kept` |
| `windows166-rejection-kept-forever` | `windows/rejection-kept` |
| `windows166-new-profile-public` | `profiles/created` |

The suite-75 case runs through the registry's own worker, as the gate's mutation check runs it.

## Verification

On `099b8511`: suites 83_veldo_0166_usage_windows (33 assertions), 75_veldo_0062_accounts (49),
78_veldo_0160_account_pool (60) and 82_veldo_0172_live_formats (30) each pass with no failure.
The mutation registry, two jobs, one finding after another: finding 166 rejects all 12, finding 62
all 50, finding 160 all 134, each from a green baseline. Anchors report 0 bad, the Git boundary check
and `.veldo/validate.py all` pass, and every `.veldo` module is byte-identical to its `engine/.veldo`
copy. The whole selftest passed: 7076 assertions, zero failed, exit status 0, with the worktree left
untouched while it ran. The canonical gate was not run, as instructed.
