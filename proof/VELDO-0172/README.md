# VELDO-0172 proof

Implementation in progress. The scrubbed capture contains the two engine streams, the Claude initialize
answer and the Codex login status with its observed stream. No other tap record is retained.

`allowlist.json` names the only string fields and values preserved and the token-count fields preserved.
All other strings become `<string>`; other numbers become zero of their original numeric type.
`grep_schema_constants` names protocol constants excluded from the exhaustive host grep, including
constants that occur as substrings of retained field names. This list does not permit preserving values.

`readback.json` records the host-only comparison: 462 typed paths equal, two tap answers, and no literal
matches among 810 non-allowlisted source strings longer than three characters. `readback.py` uses a
fixed-string grep with its patterns supplied on stdin, printing no source values. The source is read
only. The repository secret scanner reports no findings in `capture.json`.
