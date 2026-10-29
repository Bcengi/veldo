# VELDO-0227: open items

## 0. A footprint addition for the reviewer to confirm: suite 106 (VELDO-0185), one row

`scripts/suites/106_veldo_0185_dispatch_setup.py` row `rerun/over-earlier-host` re-runs setup over a host the
engine of commit 294e1933 laid down. That engine writes `api-process.json` without `ui` (it is after VELDO-0171),
and the row asserts the exact set of steps the re-run writes (`wrote == mine | {'engine_upgrade'}`, near its line
895). With this change the re-run also upgrades that file, as AC1 requires ("on a host set up before this change
... setup adds it and nothing else"), so `api_process_configuration` is `done` there and the row goes red. That
expectation is now stale, not this change wrong.

The fix is one line in that file, outside this spec's footprint, so it is NOT made here. Proposed, for an
independent reviewer to confirm as a footprint addition (`scripts/suites/106_veldo_0185_dispatch_setup.py`):

```python
        # VELDO-0227: the current setup names the factory UI in the API configuration the earlier engine wrote.
        if hasattr(h['FA'], 'ui_directory'):
            mine.add('api_process_configuration')
```

placed beside the VELDO-0142 `git_identities` addition to `mine`. No other suite archives an engine that writes
the API configuration (checked: every `git archive` commit in scripts/suites against
`def process_config` in that commit's control_factory_setup_api.py; only 294e1933 in suite 106 and 1aee02d4 in
suite 117 do). Suite 106 was not run here (owner rule 37191).

## 1. Suites that load the changed setup modules were not run here (owner rule 37191)

This change edits `control_factory_setup.py` and `control_factory_setup_api.py` (both copies). Per the owner's
rule only this ticket's suite (117) and its mutation cases were run. Other suites load these modules but none of
their files changed: 85_veldo_0171_setup_api, 73_veldo_0139_factory_setup, 86_veldo_0189_engine_upgrade,
91_veldo_0167_setup_records, 106_veldo_0185_dispatch_setup, 103_veldo_0142_git_identities and the other setup
suites. What could move in them:

- A fresh setup's `api-process.json` now carries `api.ui`. Suite 85 reads the file's fields one by one (listen,
  origin, rp_id, host, signer), not the whole object, so a new key does not change its rows.
- A re-run over a host laid down before this change now upgrades an `api-process.json` that lacks only `ui`
  (step `api_process_configuration` reported `done`, and the running API unit restarted once). A suite that
  re-runs setup over an earlier engine's host whose API configuration it expects `already_done`, or that
  counts the manager's restart calls (suite 85 `api/start-rules` counts them over the 7fefdb9a host, which has
  no API configuration, so it is written fresh there, not upgraded), would see that.
- Every other difference in that file is still refused by name (suite 85 `rerun/differs-refused`
  plants `127.0.0.2`, which stays refused; suite 117 `ui/differs-refused` checks it too).

The full gate decides these before merge.

## 2. The phone leg

VELDO-0145 OPEN item 1 step 2 (the manual edit of the API process configuration) is no longer needed once this
lands: `veldo factory setup` (run again on an existing host) writes `api.ui` and restarts the API unit.
