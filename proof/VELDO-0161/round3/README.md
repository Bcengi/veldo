# VELDO-0161 round 3: the two failures of the host run at 7b60b7c0

Branch agent/claude/agent/claude/veldo-0161, from 7b60b7c0. Code at cdb02138 (67649f2c suite 73 and the setup
mutations, 5b30385b suite 109, cdb02138 the specification). Nothing here is a gate result, a review verdict or
an approval. The sandbox refuses AF_UNIX sockets and has no qualified user manager, so the parts named below
are the host's.

| Failure | Fix | Row | Falsifier(s), result here |
| --- | --- | --- | --- |
| A. suite 73 setup/lays-down expected the owner as the only enrollment signer | The row is right to be exact and wrong in what it expected. VELDO-0161 AC1: "The adoption signer is a service key setup enrolls among the host's enrollment signers". Setup's output stays; the row now asserts exactly two lines, `owner namespaces="veldo-enrollment" <owner key>` and `adoption-signer namespaces="veldo-enrollment" <public key derived from keys/adoption-signer>`, nothing else, and the adoption key is among the 0600 keys | `VELDO-0139 setup/lays-down` | `setup161-adoption-signer-omitted`, `setup161-adoption-signer-wrong-key`, `setup161-extra-enrollment-signer`: the host's (here setup refuses `unavailable_service:profile:user_manager` before writing, so the row is red at baseline). `setup-signers.json`: the row's comparison over setup's own `host_files` is true as setup is, false for each mutant's text; the round-0 comparison is false as setup is (the host failure, reproduced) |
| B. `adoption161-signer-agent` ended in driver_error | The other rows' adoption signatures, not this row's, reached the fence's recording agent (the effect builds its own signer), so the fence raised at the suite's end. The row now owns an agent: a recording socket outside the fence's (a dead path where local sockets are refused) and a recording ssh-keygen first on PATH. Every `AdoptionSigner.sign` of the suite's and the effect's copies runs with them; the row is judged at the suite's end over every adoption signature: no agent variable passed on, nothing connected, every journaled signature made under the watch. Every other process stays under the fence; a signature the watch misses still reaches the fence | `VELDO-0161 adoption/signer-no-agent` | `adoption161-signer-agent` killed here (row red, exit 0, 69 rows, no other new failure) |

`falsifiers.json` (`run_falsifiers.py`, the driver's worker mode, every finding-161 case): the 37 adoption cases
all leave their target rows red with the worker exiting 0 and 69 rows; `adoption161-restart-take-on`'s row
is red at baseline here, as in round 2, so it is not judged here. The baseline is identical before and after (the
four AC2 rows red, by name). The three setup161 cases run suite 73 (43 rows), whose row is red at baseline here.

## Host runs (required before review)

1. `python3 scripts/selftest.py --suite 73_veldo_0139_factory_setup`: every row green, setup/lays-down included.
2. `python3 scripts/selftest.py --suite 109_veldo_0161_adoption`: every row green, signer-no-agent with its
   recording socket (AF_UNIX), and no HermeticViolation at the fence's end.
3. `python3 scripts/check_teeth_mutations.py --finding 161`: 40 cases killed; `adoption161-signer-agent` on
   `adoption/signer-no-agent` with no driver_error, and the three setup161 cases on `setup/lays-down`.
