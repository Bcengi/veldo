# VELDO-0231: open items

1. Outside the footprint: scripts/suites/78_veldo_0160_account_pool.py, row decision/outward-tool-asks (line about
   1960). The row holds the lead's VELDO-0160 allowlist as a literal set; AC2 moves SendUserMessage onto that list,
   so the reader's allowlist now holds it and the row is red. The fix is one name: add 'SendUserMessage' to the set
   `{'Agent', 'Bash', ..., 'Write'}` in that check. Not made: the path is not in the spec's footprint.

2. Outside the footprint: AC4's strict form, "process start made to raise in the service, a flag is still
   delivered". Every record the authority store commits is journal-signed by a local process,
   `ssh-keygen -Y sign` (.veldo/control_signer.py sign_bytes, called through the store's `sign`). A flag record is a
   store record, so its commit starts that process. Suite 127 makes socket creation and every other process start
   raise, lets only that signer through and names it in the row. The strict form needs an in-process journal
   signature: .veldo/control_signer.py and .veldo/control_store.py (and their engine/ canon copies). Nothing of a
   flag leaves the host either way.

3. For the lead (not a footprint question): run `python3 .veldo/qualify.py` on the qualified binaries. The shipped
   Codex record carries `flag_means` as not probed (the marked line), so request_user_input_async is refused at save
   until the real binary's loopback probe records its stream form and an immediate answer with no answers. The same
   run regenerates the VELDO-0127 fixtures, which bind the digests of the edited handoff and engine modules; suite
   126 (qualify reproduces) is expected red until then. Not run here: the build was to launch no real engine.

4. For the lead: suite 86 live/claude and live/codex are stale live captures (module digests, and the Codex mapping
   in `wire_tools`); retaken on real accounts by the lead.

5. Not verified against a real binary: whether SendUserMessage is enabled in a 2.1.281 print-mode run (its
   definition is enabled only under a condition), and the form in which Codex 0.166.0 surfaces
   request_user_input_async in exec JSON. Both are for the lead's live captures; the fake engines use one stand-in
   form.
