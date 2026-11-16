# VELDO-0304 fix round

Implementation: 6e9738497df777f86dad54f56ecf37a0b12e06dc. This fix round is incomplete: the lead decision
about failed-adoption scaffold preservation is pending. No aggregate gate or landing result is claimed.

The requested suites ran with nice -n 10. Suites 155, 142, 66_0042, 67_0056,
146_0308, 129_0239, 138, 139 and 140 have zero failed rows. Suite 109_0161 has
five failed-adoption cleanup rows; integration-conflict.json names each one and
records the conflict. All accepted suites are unchanged. Selected selftest runs
return exit 1 even with zero failed rows; these logs are diagnostics, not a
passed unit-evidence record.

The final check was check_teeth_mutations.py --finding 304, also at nice 10.
Its valid baseline and all 37 rejected cases are recorded in teeth.log and
teeth-receipt.json. No edits occurred while it ran. Only proof files were
written after it. Exact applied diffs are in fix-round-mutations/.

Standalone cleanup now looks and keeps before removal through the removers.
Retirement supplies the item id and records only successful pin releases.
Batch staging refs wait for clone discard. Successful scaffold cleanup proves
branch reachability; creation cannot overwrite an existing ref. Failed-adoption
scaffold refs with unheld work remain until the lead decides their preservation
format. Ref cleanup runs no repository hooks. Delivery acknowledgement removes
spool inputs, and shutdown removes only the socket this service instance bound.
The boundary catches recursive walk deletion, stdin ref deletion, indirect
rmtree, forced ref overwrite and unchecked kept-ref updates. Suite 155 loads
all script dependencies beside its installed .veldo for every mutation copy.

The protected scripts/verify.sh line is unchanged. policy_check.py and the
aggregate verification command were not run; they remain the lead's.

manifest.json, sources.json, registered-falsifiers.json, integration-conflict.json,
boundary.log, teeth files, fix-round-mutations/ and the ten requested suite logs
are this round's evidence. Other files here are historical artifacts from the
prior build and do not describe this round's result.
