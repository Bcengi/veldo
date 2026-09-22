# Review repairs on fixes-20260922

The repository describes Veldo as Verification-Enforced Lifecycle Delivery Orchestration.
These repairs retain its YAML policy format and the reader's exact-read-or-refuse contract.
All changes were made in this worktree. Nothing was pushed. Every changed `.veldo/` file
has an identical `engine/.veldo/` copy.

The twenty entries below split finding 4 into its three reported exposures. Finding 2
covers both accessors. The identifiers otherwise follow the review prompt.

| Finding | Repair | Evidence |
| --- | --- | --- |
| 1a | Refuse unrecognized top-level policy syntax instead of interpreting it as an absent setting. | Suite 45 drives both quoted root keys and a flow-style root through the real proof-check call site; each fails closed. |
| 1b | Decode YAML double-quoted escapes, including control and hexadecimal escapes; reject invalid escapes. | Suite 45 checks that `\b35081...` contains a backspace and cannot become a commit id; existing escaped-quote and YAML-oracle checks pass. |
| 2 | Both accessors retain the decoded value's literal apostrophes; the start-line accessor also retains whitespace. | Suites 44 and 45 check already decoded values; literal apostrophes cannot become a valid commit boundary or a true flag. |
| 3 | Accept a positive ancestry path, but report unknown on negative ancestry in a shallow repository or failed history traversal. | Suite 44 has both endpoints present and verifies Git returns 1 with empty stderr; scope remains included and says it cannot determine ancestry. |
| 4, record | Route every validation-record Git operation through the shared environment boundary. | Suite 50 contaminates Git selectors and checks commit lookup, root lookup, history, revision output, and ancestry against the intended repository. |
| 4, archive | Route validation-runner and capsule archives through the same boundary. | Suite 50 calls the real validation checkout under contamination and checks the extracted file belongs to repository A. Suites 40 and 42 cover capsule and fix-runner behavior. |
| 4, enrollment | Remove inherited `GIT_*` variables and disable global/system Git configuration, including HOME/XDG discovery. Migrate all runtime Git users and package the helper. | Suite 50 demonstrates a hostile HOME config breaks raw Git but cannot change enrollment roots through the wrapper. Suite 46 retains the competing-repository test. The boundary scanner rejects direct, aliased, assigned, absolute-path, and shell Git calls. |
| 5 | Generate clone UUID before signing; require it in the signed binding and always compare it. | Suite 47 deletes and changes the field: deletion is malformed and alteration invalidates the signature. |
| 6 | Pass domain UUID, store UUID, and the authority's minimum generation into enrollment resolution. | Suite 47 tests conflicting domain/store coordinates and a generation below the authority's floor, with no applied command. |
| 7 | Sign repository UUID/root commits, clone UUID, binding digest, and generation with the command; compare them to current enrollment. | Suite 47 signs a request, replaces its workspace with an unrelated repository, reenrolls at a later generation, and verifies the old request is refused while a fresh one succeeds. |
| 8 | Validate request field types before invoking the verifier or resolver. | Suite 47 gives every request field a wrong type, including a list signature and nested root list; all produce malformed_request. |
| 9 | Give accepted sockets a timeout and a total read deadline, retaining the byte limit. | Suite 47 leaves one client holding a single byte open, then verifies a second request is served after the first deadline. |
| 10 | Handle connect, send, shutdown, receive, timeout, and empty response within the authority-unavailable path. | Suite 47 uses real peers that close, reset, or time out after consuming the request; inspection returns the recorded state explicitly stale. |
| 11 | Propagate a refused inspection as RoutingRefused with the original reason and message. | Suite 47 sends a signature refusal over a real socket and checks both fields survive. |
| 12 | Write last-seen records using a unique temporary file per writer and atomic replacement, with cleanup. | Suite 47 synchronizes two writers immediately before replacement; both complete and one intact record remains without temporary files. |
| 13 | Use the shallow clone's actual tip, require both objects and successful fixture setup, and remove the vacuous success alternative. | The mutation driver writes a copy that treats return code 1 as settled non-ancestry; this exact row turns red. |
| 14 | Check the applied-command list as well as refusal responses. | A broken copy applies the invalid-signature command and then returns the correct refusal; the transport/signature row turns red. |
| 15 | Drive the executable relay with raw stdin and compare stdout byte for byte, including binary, empty, large, and whitespace-sensitive payloads. | A broken executable reserializes JSON and rejects binary input; the carrying row turns red. |
| 16 | The original repair distinguished empty output from `{}` but still conflated it with JSON `null`. | The teeth-20260922 follow-up compares raw stdout to `b""` in suite 48 row `relay/an-unreachable-authority-is-reported-not-answered`; `null`, one newline, one space, and `{}` each turn it red. `relay/usage-has-zero-stdout`, `relay/oversized-request-has-zero-stdout`, and `relay/oversized-response-has-zero-stdout` extend the zero-byte assertions to the other refusal paths. |
| 17 | Snapshot recursive file contents and metadata in both state directories after authority shutdown, including existing files. | A broken client overwrites an existing last-seen file while still refusing; the no-local-authority row turns red. |

## Verification record

All five requested groups were committed separately. The follow-up fixture changes keep
policy tests independent of this branch's protected-path changes, add the new Git dependency
to copied fixtures, and ensure the installer launcher check observes the shared wrapper too.
The policy fixture explicitly proves an objection override does not authorize a protected path.

`python3 scripts/check_review_mutations.py` passed: all five honest rows were green and all
five broken copies made their named row red without editing runtime code in this checkout.
The detailed results are in `mutation-results.json`.

Targeted runs passed for suites 01, 19, 24, 37, 44, 45, 46, 47, 48, 49, and 50.
A selector run is a partial check, not a gate pass. Generated-file and template-sync checks passed.
The first canonical gate attempt's unit stage reported 5500 passed and 4 failed; it was stopped
after that stage to repair the fixture failures. Its failures are not represented as passes.

Final canonical gate result: **GREEN** on code commit
`093e06689aec9fdc589e7585ae7b7744dbeabbf3`, using `bash scripts/verify.sh`.
The full unit suite reported **5508 passed, 0 failed**. The first-use integration check passed,
including its nested full suite after real spend writes. All eight applicable catalog checks
passed; fifteen were not applicable with recorded reasons, zero were waived, and zero were
undeclared. This includes the complete suites covering every modified runtime module and test.

All twenty reported defects are repaired and verified; none was left unfinished.
The final evidence commit only completes this report and restores the checkout's gate byproducts.
Existing enrollment bindings and requests signed under the old field set must be reenrolled or
signed again with the new identity fields; accepting their old signatures would retain the defect.

No independent review or merge approval is claimed. The relay suite explicitly leaves real
sshd authentication untested, as before; the executable relay and local authority are exercised.
The checkout's gate stamp and event log are byproducts and are excluded from these commits.
