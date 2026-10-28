# VELDO-0161 round 5: the review of round 4 (N1 and N2, both low)

Branch agent/claude/agent/claude/veldo-0161, from d65e573e. Review: proof/VELDO-0161/REVIEW-claude-r4-2026-10-23.md
(8294141b, added unchanged in e1a0abc9). Code at bde1bf57, rows and mutations at f5d84aa4. Nothing here is a
gate result, a review verdict or an approval. This sandbox refuses AF_UNIX sockets and has no user manager, so
the parts named below are the host's.

| Finding | Fix | Row | Falsifier(s), result here |
| --- | --- | --- | --- |
| N1, the scaffold push sends the annotated tags push.followTags asks for | control_repository_provisioner.push passes `-c push.followTags=false` and `--no-follow-tags`, as control_effect_executor's VELDO-0153 push does (checked_argv already accepts both). push.followtags stays in LOCAL_CONFIGURATION: the push overrides it on its own command line, no other local step reads it, and refusing it would refuse a common key for nothing | adoption/repository-commands, two new parts: a repository with push.followTags=true and an annotated tag `private-161` only it holds is adopted, and the remote holds exactly the scaffold commit with no tag | adoption161-push-follows-tags (the push as it was, neither the -c nor the flag): killed. Against d65e573e's modules (unfixed.json) the part fails with `refs/tags/private-161` on the remote |
| N2, the allowlist accepts a key in the URL-named remote section that the push then refuses after the branch moved | refuse_transport_config: the identity transport's own config_overrides over the same `config --includes --null --list` listing git_process makes before the push, for the proposal's remote, refused binding_mismatch:identity_transport_config. Run at prepare (before anything is laid) and in the effect's checks (before advance), each right after refuse_commands, which has already refused every include. One judge: the transport's function, not a second list | adoption/transport-config (new): `remote.<url>.push` set; the allowlist accepts it and the transport refuses it; prepare refuses it by the push's code, laying nothing; a repository that came to carry it after its scaffold was laid is refused by that code with its record failed, the working branch and the remote at the base and the ref removed | adoption161-transport-config-after-advance (the effect's call removed), adoption161-transport-config-prepare-unchecked (prepare's call removed): killed. Against d65e573e's modules (unfixed.json) prepare lays the scaffold (code None) and the settled adoption is refused by the push only after the branch moved: the reviewer's scenario |

`unfixed.json` (run_unfixed.py): suite 109 at f5d84aa4 in a `git archive` copy, once with the two adoption
modules (engine/.veldo and .veldo) as they were at d65e573e and once as they are at f5d84aa4. Unfixed: 73
passed, 6 failed, the four AC2 rows (AF_UNIX) plus repository-commands and transport-config, with the failing
parts above. Fixed: 75 passed, 4 failed, the four AC2 rows only.

`falsifiers.json` (proof/VELDO-0161/run_falsifiers.py): every finding-161 adoption case (52) through the driver's
worker mode, one run: each case's target rows red,
worker exit 0, 79 rows. adoption161-restart-take-on's row (same-process) is red at baseline here, so it is the
host's. The baseline before and after is the same four AC2 rows (AF_UNIX). No existing anchor moved.
Finding 161 now registers 55 cases: 52 adoption cases (49 before this round, 3 added) and the 3 setup161 cases.

Suite 73 here: 27 passed, 16 failed, every failure unavailable_service:profile:user_manager or its consequence,
as in the review's own run; nothing in this round touches setup.

## Host runs (required before review)

1. `python3 scripts/selftest.py --suite 73_veldo_0139_factory_setup`: every row green (43).
2. `python3 scripts/selftest.py --suite 109_veldo_0161_adoption`: every row green (81: the 79 of round 4 plus
   adoption/transport-config and its ran/ row), no HermeticViolation.
3. `python3 scripts/check_gate_mutations.py --finding 161`: 55 cases killed (52 adoption, the three setup161
   cases in the unconfined leg).
4. `python3 proof/VELDO-0161/round4/drive_setup.py proof/VELDO-0161/round5/drive-setup-host.json`: exit 0,
   "setup161: all killed".
5. `./scripts/verify.sh`: green.
