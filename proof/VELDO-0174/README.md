# VELDO-0174 implementation and review record

Latest round: [scope-review-fix.json](scope-review-fix.json). Project attachment
now requires both ownership and current membership scope covering the project,
checked inside the store transition. The signed-command `AC1/project-scope` row
refuses attachment after a steward removes scope and preserves the durable row,
including its version and digest. Restoring named or wildcard scope permits the
attachment. Removing only the scope guard makes that row fail. Both source copies
are byte-identical. Suite 107 has 34 passing ticket rows; its two restart rows
remain blocked by this host's AF_UNIX socket denial. The full gate remains for
the reviewer; no gate or mutation driver was run here.

Previous round: [review-fixes.json](review-fixes.json). The project attachment owner
check and its falsifier are verified. The restart fixture now supplies its unit and
sends signed messages through the running service to wake scheduling. Suite 107
has 33 passing ticket rows; its two restart rows remain blocked by this host's
AF_UNIX socket denial. The full gate remains for the reviewer.

Previous round: [batch-2.md](batch-2.md), with direct results in
[batch-2-results.json](batch-2-results.json). Status: BLOCKED on host verification.
The narrative below is the inherited round, retained as history; batch 2 resolves
the versioned-command, skill-delivery and production project-priority gaps.

This record is focused review evidence, not a proof manifest or a landing decision. The specification
remains ready. The reviewer must run the canonical gate in the checkout that will land the change.
No gate, live capture, real login, push, or user service installation was run in this worktree.

Turns now use the shared account pool, reservation ledger, invocation guard, engine capability handoff,
meter, usage charging, reported windows, and account release. Configured domain caps cover both kinds
of work. Account, allowance and unit ceilings remain mandatory. The conversation role budget supplies
its allowance policies, and the next turn reserves only the remaining wall-time allowance.

The Line retries temporary login, host trust and engine binding refusals on another account. Durable
in-flight records are reconciled on startup to a recorded unknown outcome or a conclusive refusal.
An unknown turn releases its account slot only after kernel observation of termination. Its retained
usage stays in the ledger. The next dispatch requires that release, so recording an outcome alone
cannot permit concurrent writers in the conversation directory.

Conversation commands use stable parameters and replay their committed results. Each conversation
has its own durable directory. Project commands reject conversation ids; turn stations require
conversation contracts. Turn observations retain the account, receiver and role revision at end, and
the loop and receiver count conversation offers and kind refusals. An active-turn refusal is emitted
once per waiting turn during a Line's lifetime.

Suite 107 replaces source-text assertions with behavioural rows. It drives real conversation Lines
and receiver subprocesses using pinned fake Claude and Codex engines, validates their selected native
tools and empty MCP selection, queues three turns, checks charged usage and saved windows, kills a
receiver, reconstructs a Line, and exercises temporary account retry. The priority fixture supplies a
pending project unit and a build station at the shared account admission boundary. Installer and kind
checks use a no-work configuration and a real receiver. It also checks all project command names,
unknown conversations, close-before-dispatch, station kind, redelivery and domain capacity.

The real service restart row starts the production service and asks it to bind its authority socket.
This sandbox denies that socket with EPERM. The row remains failed, not skipped or passed. Host
execution is required. The evidence JSON records other suite results and the host-required set.

Open verification work: a nonempty MCP selection and skill delivery in both fake engines; a full
project Line priority journey; recovery followed by another completed turn across a real service
restart; and the complete transitive suite closure. Unknown usage can still correctly refuse later
invocations under the shared caps until accounting is resolved. These are not claimed as proved.

Role-change and project-attach versioning, message text delivery and session continuity remain open
with VELDO-0175 and VELDO-0176. No review approval or shipped status is asserted here.
