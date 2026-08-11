# Veldo CLI / process runner (reference)

Real proof for command-line tools and processes: drives a command as a genuine
subprocess and asserts its observable contract - exit code, stdout, stderr, and
a wall-clock budget. Terminal tools have a contract just like an HTTP endpoint
does; this runner pins it down so a regression in what a command prints or the
status it returns fails the gate instead of shipping silently.

## Use

```
cli_runner.py <fixture.json>     # exit 0 = every case met its contract
test_cli_runner.sh               # on-demand self-test over the fixture pair
```

Stdlib only, so a reviewer reruns it with no setup. The runner is tool-agnostic:
a case names the argv, so a repo points it at its own binary.

## Fixture format

A fixture is a JSON list of cases. Each case names a command and the
expectations it must meet:

```json
[
  {
    "name": "help prints usage and exits 0",
    "cmd": ["mytool", "help"],
    "expect": {"exit_code": 0, "stdout_contains": "Usage"}
  },
  {
    "name": "bad flag is rejected on stderr",
    "cmd": ["mytool", "nonsense"],
    "expect": {"exit_code": 2, "stderr_contains": "unknown"}
  },
  {
    "name": "reads stdin and stays fast",
    "cmd": ["mytool", "count"],
    "stdin": "one\ntwo\n",
    "expect": {"exit_code": 0, "stdout_equals": "2\n", "max_seconds": 5}
  }
]
```

Expectation keys, all optional (a case asserts only what it declares):

- `exit_code` - the exact exit status.
- `stdout_contains` / `stderr_contains` - a substring, or a list of substrings.
- `stdout_equals` - an exact stdout match.
- `max_seconds` - the process is killed and the case fails if it runs longer.

`stdin` (optional) is fed to the process. Commands run WITHOUT a shell, so each
argument is a literal argv element.

The `fixtures/` pair drives commands present on any POSIX system, so it runs
anywhere with no tool to install: `pass.cases.json` (echo, printf, false, cat,
sh, true - every expectation kind exercised, all passing) and
`fail.cases.json` (asserts output a command never produces, so the run exits 1
with the broken expectation named).

## Why it is a reference

The runner drives real processes, but a repo wires it to its own CLI and gate
slot. Its control logic (running a case, evaluating every expectation, naming
the failure) is unit-tested by driving the fixture pair in
`scripts/selftest.py`, so the runner is proven here without depending on any
particular tool. It is marked `reference` in `capabilities.yaml`: the veldo repo
ships it but does not run it in its own gate, because the veldo repo is not the
CLI under test.
