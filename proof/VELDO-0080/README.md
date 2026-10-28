# VELDO-0080

Base: `59b119a1c565c805b1c883fa56c2ce6685548d67`, main at worktree creation.
Owner authorization: Telegram 37209 and 37212, as supplied with this task.

Ordinary defects use the existing backlog, grooming, claim, proof, review and
landing services. The new defect report retains the intake source and reported
severity. Grooming shows and binds that report with the specification digest.
Reports with scope changes require a presented owner decision. Reproduction
claims supply no authority and the deferred standing/emergency handlers stay off.

| Criterion | Automated check | Declared falsifier |
| --- | --- | --- |
| AC1 | `defects/ordinary-admission` | A POLICY_DEFECT label makes a unit executable without admission |
| AC2 | `defects/ordinary-completion` | The floor fabricates a passing reviewer when no review exists |
| AC3 | `defects/no-automatic-admission` | A model reproduction claim selects admission by message |

`run.py` runs exactly these three checks, without the selftest prelude or any
dependency suite. Suite 113 registers the same checks for the later batch gate.
`falsify.py` runs each mutant in a private source copy, requires the corresponding
named check to fail by assertion, then reruns the unmodified checks. It also
mutates severity preservation, report binding and the scope-change routing guard.
The diffs, individual red logs, `mutations.json`, `green.log` and
`observations.json` record the driven results. Source hashes bind each mutation
to the bytes exercised.

Run the ticket checks with `python3 proof/VELDO-0080/run.py`. Run the falsifier
driver with the blocking host lock:

```
flock /home/dmitry/.local/state/core-gates/.gate.lock python3 proof/VELDO-0080/falsify.py
```

The driver never opens or releases the host lock itself. It never edits product
files, starts detached processes or touches another worktree. The full repository
gate is excluded by owner rule 37191 and runs later on the batch.

AC1 uses real channel acquisition, intake, SQLite journals, OpenSSH signatures,
objective acceptance, shaping, presentations and decision settlement. Telegram
uses a loopback Bot API; the API leg uses its authenticated intake interface.
Plain Telegram prose first takes the ordinary PM route from the factory inbox.
Each source retains its exact text and canonical attribution. The tests withhold
admission, then priority, and inspect the exact owner decision binding.

AC2 consumes AC1's admitted unit in the same store. An actual failing arithmetic
check turns green after a builder process fixes it. The proof service accepts the
committed proof against the accepted spec and observed check. The floor rejects
a missing gate, missing review and self-review. A separate reviewer process reads
the assigned commit and proof and signs its verdict. Candidate observation and
acceptance check the exact tree, the effect executor publishes to a disposable
bare remote, and the landing service records the confirmed completion receipt.
The ordinary backlog then reaches DONE. Missing admission and priority each also
refuse at the real claim entry before the positive journey.

The builder and reviewer are deterministic Python workers, not live models.
Their dispatch records contain observed process exits and output digests; this
does not qualify the Runner. Staffing risk metadata is a fixture input. The
ticket verifier runs only the arithmetic check through the production candidate
observation service, using a fixture verifier path. No `scripts/verify.sh` is
executed, including in scratch repositories. Fixture publication uses the
existing hermetic Git identity transport with local remotes. These checks do not
claim live Telegram, worker-engine, host, full-gate or independent code-review
qualification.

AC3 checks an agent reproduction claim, standing maintenance and a security
emergency without authority. A fresh authenticated owner message still admits
ordinary work at default rank 3 without reproduction. Each declared scope-change
dimension is presented, returned by the owner and re-entered into grooming with
identical severity and source. Installation registration and canonical/installed
byte equality are checked in AC1. There are no tracked pack copies of these files.

Protected paths touched: none. See [OPEN.md](OPEN.md) for the inherited release
wording and architecture mapping. Specification status remains ready; this branch
does not claim a trunk landing.
