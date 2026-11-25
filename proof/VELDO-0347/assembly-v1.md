# Space V1 join 2, owner order 43607

Incoming 652d4e07f5cfb136d041e1f942364f8d02ffacbf joined after fb69b9aae.
Candidate 0347 (7808cb3da, d590d9252, bae8e633e) remains the implementation.
The clone-specific Keep-only request, target/form checks and signed completion are ported
onto its forms lifecycle. Table 1 stays immutable. A table without the clone form cannot
create that request. The Ledger reader from join 1 continues to read space_failure.
The shared signed-owner desk replaces suite 156's inline desk, preserving its signed Keep
and startup observations. Suite 155 records the shutdown stop callback. Incoming signed
Keep fixes in other suites remain. All modules remain mirrored.

Explicit implementation retirements:
- Old composite ends_on keys, SHEET_2, FORMS and duplicate no_space_ends reader are
  superseded by candidate forms/FORM_ROWS and join 1's current dispatch-format reader.
- Old probe ignored_work signature, old clean-clone allowlist walk, snapshot comparison
  and trunk callback implementation are superseded by candidate tracked-ignore directory
  checks, adopted/unreadable handling, repeated clone reads, descriptor safety, per-file
  comparisons and held/landing trunk resolution. Candidate suite 161 and suites 135-140
  retain their assertions. Distinct incoming assertion audit remains pending final validation.
- Old suite-135 all-events clone cells contradict the candidate run_finished-only clone row;
  retain candidate table/version assertions. No new form behavior is granted to table 1.
- Duplicate admission scaffold line (87fce757d) is already satisfied by 18f880dc8; exactly
  one line remains, along with the candidate's installation/timer/query/tracker closure.

Candidate proof bindings remain; conflicting incoming manifests/falsifiers are preserved
under historical-space-v1 with their original provenance. No historical receipt certifies
this tree. Registries will be reconciled after join 3. Suites/teeth not run while Gate 18
has no completion line. Protected paths changed: none. Assembly checkpoint only.
