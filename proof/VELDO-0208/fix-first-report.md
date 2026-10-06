# VELDO-0208 FIX FIRST follow-up

Work begins at 80b02ff2 on build-gate-reuse. No push, merge, full gate or mutation
stage is run here. The reviewer owns the fresh merged-tree gate and stamp.

## Candidate execution boundary

The gate executes candidate commands through the authority launcher. Registry
imports are confined; mutation worker entry/driver code comes from authority.
The coordinator alone reads/publishes reusable records, validates its launched
worker observations, and writes the receipt outside candidate write grants.
Worker output files are outside worker scratch and observed through inherited
stdout/stderr, with exit status checked. Candidate stage receipts are not ingested.

Targeted suite: `python3 scripts/selftest.py --suite 100_veldo_0208_landing_reuse`.
First pass: 107 passed, 0 failed; selector exit 2 denotes partial, not a gate pass.
Includes a planted suite whose Store.put attempt fails and reddens the command
with an explicit store-denied-domain message. Full gate remains unrun.
