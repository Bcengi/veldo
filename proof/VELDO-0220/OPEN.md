# VELDO-0220 round 3 status

The owner approved the single scripts/gate_unconfined.json entry in Telegram
37440 item 2 and 37442 ("all 3"). Round 3 directs that same entry to name the new
suite 114_veldo_0220_gate_scope whole. It replaces suite 113's userbus row entry;
no additional unconfined entry is added. The spec's footprint and amendment
record the split and approval.

Suite 113_veldo_0220_gate_host retains the three confined lock and not-started
rows. Suite 114 owns scope creation and teardown, including lock custody over a
worker in a separate session and child cgroup. Both suites are registered in the
manifest and requires. The three scope mutants target suite 114; the other four
still target suite 113.

The first round 3 drive reproduced the original seven-case refusal. Both split
suites passed, and the coordinator then admitted all seven cases. Four confined
mutants were rejected; the scope controls exposed a missing runtime directory in
the clean worker environment. Suite 114 now supplies the same runtime fallback
as other host suites. The first drive is retained in round3/red-runtime/.

Remaining for this round: rerun the two suites and all seven coordinator cases
with that fixture setup, then record the final evidence in [round3](round3/).

Remaining before landing: a fresh independent review of the final commit and
the owner's canonical gate. This round is explicitly limited to the ticket's
suites and mutation cases; targeted results do not claim a canonical gate pass.

Review note C remains unchanged: without a configured scope, teardown kills the
command's process group only, so a stage that creates a new session could outlive
the lock. This host configures a scope; adopters ship no host configuration.
