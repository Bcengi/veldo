# VELDO-0124 native qualification run, 2026-10-28

Status: REMAINING (blocked on Mac Claude Code setup token under VELDO-0147; all Linux suites, all 9 Linux falsifiers, all 22 synthetic Mac rows, all 16 Mac native falsifiers red-then-green, and all 3 real Mac Codex CLI rows including real descendant and Seatbelt isolation observations passed).

No product code changed. Qualification stamp was not created (`qualification_created: false`), and `proof/VELDO-0124/manifest.json` remains pending because the 3 `native/qualified-claude_code/*` rows are blocked on Mac `claude-1` login under Keychain-denied Seatbelt.

## 1. Merge of main and generated indices

Branch `agent/codex/veldo-0124-b2` started at `412b9c3962ae3a527689fde5f95012b5cc038ad2` (230 commits behind `main` at `59b119a1c565c805b1c883fa56c2ce6685548d67`).

Exact merge and index verification commands on Linux:

```sh
git -c user.name="Dmitry Grinberg" -c user.email="dmitry@bcengi.com" merge --no-edit main
python3 scripts/run_scope.py --emit-requires
python3 scripts/update_index.py
bash scripts/check_generated.sh
```

Merge committed cleanly at `feabeec77912572dc1c8403402320f4a75e2fbe9` with zero conflicts. `scripts/suites/manifest.json` contains 171 entries (170 executable suites plus `shared`, retaining `103_veldo_0124_macos` and `104_veldo_0124_control` with no duplicates or missing files). Regenerating `requires.json` and `specs/index.md` produced no diff (`check_generated.sh` exited 0).

## 2. Linux suites and single-change falsifiers (red then green restored)

All multi-file runs on Linux executed inside `flock /home/dmitry/.local/state/core-gates/.gate.lock`:

```sh
flock /home/dmitry/.local/state/core-gates/.gate.lock python3 scripts/selftest.py --suite 103_veldo_0124_macos
flock /home/dmitry/.local/state/core-gates/.gate.lock python3 scripts/selftest.py --suite 104_veldo_0124_control
flock /home/dmitry/.local/state/core-gates/.gate.lock python3 proof/VELDO-0124/negative_controls.py --output proof/VELDO-0124/native-2026-10-28/linux-falsifiers
flock /home/dmitry/.local/state/core-gates/.gate.lock python3 scripts/selftest.py --suite 103_veldo_0124_macos
flock /home/dmitry/.local/state/core-gates/.gate.lock python3 scripts/selftest.py --suite 104_veldo_0124_control
```

Results (logs and `.exit` files in this directory and `linux-falsifiers/`):

* `103_veldo_0124_macos` baseline (`linux-suite-103.log`, `.exit`): 28 owning rows passed, 54 total passed, 0 failed, exit `2` (`PARTIAL_PASSED_EXIT`).
* `104_veldo_0124_control` baseline (`linux-suite-104.log`, `.exit`): 7 owning rows passed, 33 total passed, 0 failed, exit `2` (`PARTIAL_PASSED_EXIT`).
* `negative_controls.py` (`linux-falsifiers/negative-controls.json`, `linux-falsifiers.log`, `.exit`): exit `0`; all 9 single-change mutants (`AC1-qualification`, `AC1-session-type`, `AC1-claude-sandbox`, `AC2-deadline`, `AC2-capacity`, `AC3-parent-only`, `AC3-group-only`, `AC2-postcall`, `AC3-unknown-retire`) exited `1` with their named failed row.
* Restored green runs (`linux-suite-103-restored.log`, `linux-suite-104-restored.log`): both suites restored green (28/54 passed exit `2` for 103; 7/33 passed exit `2` for 104; 0 failed).

## 3. Target Mac host facts, manuals, and installed engine identities

Export and host capture commands:

```sh
git archive HEAD .veldo proof/VELDO-0124 | ssh -o BatchMode=yes dmitry@dmitrys-mac-mini 'mkdir -p ~/veldo-0124-check/native-2026-10-28 && tar -x -C ~/veldo-0124-check/native-2026-10-28'
ssh -o BatchMode=yes dmitry@dmitrys-mac-mini 'uname -s; uname -m; hostname; sw_vers; sysctl -n kern.boottime; /opt/homebrew/bin/python3.12 --version' > proof/VELDO-0124/native-2026-10-28/native-host.log 2>&1
```

Observed host facts (`native-host.log`, exit `0`):

* Host: `dmitrys-mini.lan`, `Darwin`, `arm64`, `macOS 26.5.1` (`BuildVersion 25F80`).
* Boot ID: `{ sec = 1791866372, usec = 996311 }`.
* Pinned trusted interpreter: `/opt/homebrew/bin/python3.12` (`Python 3.12.13`).
* Target host manuals archived under `manuals/` (`index.json` records raw byte counts and `sha256` digests): `launchctl.1`, `launchd.plist.5`, `sandbox-exec.1`, `ps.1`, `kqueue.2`.
* Installed Codex CLI vendor Mach-O arm64 binary:
  `/Users/dmitry/.local/share/veldo-engines/codex-0.154.0/node_modules/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex`
  version `0.154.0`, `sha256:4f85982624b3898c8991cb80c0981b2aa71070e3537046c9a95950318a95afcc`.
* Installed Claude Code Mach-O arm64 binary:
  `/Users/dmitry/.local/share/claude/versions/2.1.303`
  version `2.1.303`, `sha256:d2da3b003dc08b88b7230469014fe3e1dc6fe94bc8f648e89b34175d30269370`.
* Dedicated Veldo Mac subscription account directories:
  `codex-1` at `/Users/dmitry/.veldo-mac-accounts/codex-1` (`codex login status` inside Seatbelt: `Logged in using ChatGPT`, exit `0`);
  `claude-1` at `/Users/dmitry/.veldo-mac-accounts/claude-1` (`claude auth status --json` inside Seatbelt: `loggedIn: false, authMethod: "none"`, exit `1`).

## 4. Synthetic Mac native lifecycle, containment, and red-then-green falsifiers

Exact commands executed on `dmitrys-mac-mini`:

```sh
ssh -o BatchMode=yes dmitry@dmitrys-mac-mini 'cd ~/veldo-0124-check/native-2026-10-28 && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py lifecycle' > proof/VELDO-0124/native-2026-10-28/native-lifecycle.json 2>&1
ssh -o BatchMode=yes dmitry@dmitrys-mac-mini 'cd ~/veldo-0124-check/native-2026-10-28 && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py containment' > proof/VELDO-0124/native-2026-10-28/native-containment.json 2>&1
ssh -o BatchMode=yes dmitry@dmitrys-mac-mini 'cd ~/veldo-0124-check/native-2026-10-28 && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_falsifiers.py' > proof/VELDO-0124/native-2026-10-28/native-falsifiers.json 2> proof/VELDO-0124/native-2026-10-28/native-falsifiers.stderr.log
ssh -o BatchMode=yes dmitry@dmitrys-mac-mini 'cd ~/veldo-0124-check/native-2026-10-28 && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native-2026-10-28/native_falsifiers_red_green.py' > proof/VELDO-0124/native-2026-10-28/native-falsifiers-red-green.json 2> proof/VELDO-0124/native-2026-10-28/native-falsifiers-red-green.stderr.log
ssh -o BatchMode=yes dmitry@dmitrys-mac-mini 'cd ~/veldo-0124-check/native-2026-10-28 && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py lifecycle' > proof/VELDO-0124/native-2026-10-28/native-lifecycle-restored.json 2>&1
ssh -o BatchMode=yes dmitry@dmitrys-mac-mini 'cd ~/veldo-0124-check/native-2026-10-28 && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py containment' > proof/VELDO-0124/native-2026-10-28/native-containment-restored.json 2>&1
```

Results:

* `native_checks.py lifecycle` (`native-lifecycle.json`, exit `0`; `native-lifecycle-restored.json`, exit `0`): 12/12 rows passed (`native/claude_code/{natural,cooperative,deadline,descendant,hard-kill,supervisor-loss}` and `native/codex/{natural,cooperative,deadline,descendant,hard-kill,supervisor-loss}`).
* `native_checks.py containment` (`native-containment.json`, exit `0`; `native-containment-restored.json`, exit `0`): 10/10 rows passed (`native/claude_code/{write,read,launchd,keychain,signal}` and `native/codex/{write,read,launchd,keychain,signal}`).
* `native_falsifiers.py` (`native-falsifiers.json`, exit `0`): 14/14 native mutants rejected (`write`, `read-ssh`, `read-claude`, `read-codex`, `read-accounts`, `read-projects`, `read-dispatches`, `launchctl-exec`, `job-creation`, `keychain`, `signal`, `wrapper-backstop`, `coalition-kill`, `engine-group`).
* `native_falsifiers_red_green.py` (`native-falsifiers-red-green.json`, exit `0`): all 16 native Mac falsifiers (the 14 in `native_falsifiers.py` plus `session-type` and `supervisor-deadline`) were each driven RED (`exit_code: 1`, named row `failed`) and then restored to the exact `source_sha256` and observed GREEN (`exit_code: 0`, named row and suite `passed`).

## 5. Real CLI native qualification rows and authority ledger

Command executed from Linux (`drive_real_qualification.py` prepares genuine signed SQLite authority records in an ephemeral directory outside the repository, exports `candidate.json`, runs both unmodified `native_checks.py engines` and `run_qualified_engines.py` on `dmitrys-mac-mini`, settles non-secret usage, and cleans up remote probe state):

```sh
python3 proof/VELDO-0124/native-2026-10-28/drive_real_qualification.py
```

Remote commands invoked by `drive_real_qualification.py`:

```sh
ssh -o BatchMode=yes dmitry@dmitrys-mac-mini 'cd /Users/dmitry/veldo-0124-check/native-2026-10-28 && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py engines /Users/dmitry/veldo-0124-check/native-2026-10-28/qual-pool/candidate.json'
ssh -o BatchMode=yes dmitry@dmitrys-mac-mini 'cd /Users/dmitry/veldo-0124-check/native-2026-10-28 && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native-2026-10-28/run_qualified_engines.py /Users/dmitry/veldo-0124-check/native-2026-10-28/qual-pool/candidate.json'
```

Empirical findings and per-row results (`native-engines-unmodified.json` exit `1`, `native-engines-qualified.json` exit `2`, `authority-ledger.json`, **3 live model calls total**, within the 6-call cap):

* Mac Codex TLS root store finding: on macOS 26.5.1, `codex` `0.154.0` (`aarch64-apple-darwin`) uses `rustls` + `Security.framework` (`SecTrustSettingsCopyCertificates` via `com.apple.SecurityServer`) to load system root CAs when `SSL_CERT_FILE` is unset. Because the VELDO-0124 Seatbelt profile denies `mach-lookup` on `com.apple.SecurityServer`, `codex` without `SSL_CERT_FILE` fails TLS locally before sending any request. Configuring `SSL_CERT_FILE: "/etc/ssl/cert.pem"` in `contract.capability.configuration.environment` (permitted by `control_accounts.py` without product code changes) supplies macOS's public root CA bundle on disk without Keychain access.
* `native/qualified-claude_code/natural`: **blocked**. Production `Supervisor.admit` and `claude_settings` succeeded, and unmodified `native_checks.py engines` attempted `claude_code/natural` first, failing immediately (`returncode != 0`, 0 model calls, exit `1` in `native-engines-unmodified.json`). Offline `claude auth status --json` inside Seatbelt exited `1` (`loggedIn: false, authMethod: "none"`). Mac Claude setup token requires `CLAUDE_CODE_OAUTH_TOKEN`, which `project_runner_macos_control.CREDENTIALS` strips and `project_runner_macos_profile.claude_settings` refuses as `unsupported_configuration:claude_settings_source` (VELDO-0147 territory).
* `native/qualified-claude_code/cooperative`: **blocked** (same Mac `claude-1` setup-token blocker under VELDO-0147; `Supervisor.admit` passed, 0 model calls).
* `native/qualified-claude_code/deadline`: **blocked** (same Mac `claude-1` setup-token blocker under VELDO-0147; `Supervisor.admit` passed, 0 model calls).
* `native/qualified-codex/natural`: **passed** (`elapsed: 15.329s`, `returncode: 0`, `deadline_stop: false`, `coalition: 20110`, 1 turn, 35568 tokens settled in `authority-ledger.json`). During this live run, Codex executed `check_real_isolation.py`, establishing real-engine descendant and authority-isolation evidence (`real_isolation` in `native-engines-qualified.json`):
  * Real descendant (`pid: 89304`, `ppid: 89266`) and its `setsid()` grandchild (`pid: 89305`, `sid: 89305`) both remained in launchd job coalition `20110` under wrapper `pid: 89261`.
  * Real Seatbelt write denials from inside Codex tool execution: `authority`, `slots`, `veldo_code`, `owner_home`, and `authority_symlink_alias` all `denied`; `scratch` `allowed`.
  * Real Seatbelt read denials from inside Codex tool execution: `other_account_claude` (`claude-1/settings.json`), `decoy_account`, `decoy_project`, and `other_dispatch` all `denied`; `own_clone` `allowed`.
  * Real Seatbelt `launchctl` exec refused, Keychain `mach-lookup` returned `1100` across `SecurityServer`/`securityd`/`securityd.xpc`, and `SIGCONT` to `supervisor` and `wrapper` `denied` while `own_child` `allowed`.
* `native/qualified-codex/cooperative`: **passed** (`elapsed: 0.438s`, `steps: [cooperative]`, `cause: requested`, `returncode: -15`, coalition `20112` empty on exit).
* `native/qualified-codex/deadline`: **passed** (`elapsed: 65.562s`, `steps: [terminate]`, `cause: runtime_cap`, `returncode: -15`, `deadline_stop: true`, coalition `20114` empty on exit).
* Post-run Mac cleanup verified zero `org.veldo` launchd jobs and zero leftover `/private/var/folders/.../veldo-*` temporary directories; raw `engine.out` and `engine.err` files were unlinked on the Mac immediately after `Meter` accounting extraction.
