# VELDO-0158 implementation proof

A dispatch configuration names the MCP servers it uses in `mcp`, a list of `{server, revision}` catalog
selections (the form VELDO-0127 later fills from the role's accepted revision). Immediately before the spawn
the launch receiver calls `control_credential_delivery.resolve`: it reads each listed `mcp_server` revision
from the store and resolves exactly the credential references in that revision's environment and headers,
each through secretref's `keychain` scheme over the Secret Service adapter of VELDO-0144. A literal is passed
as it is and resolves nothing; a server not listed contributes nothing. Every value is held in a secretref
handle until the engine module reveals it where it delivers it.

Delivery is the engine protocol's `baseline(binding, run, environment, servers=())`, so the values enter the
configuration the everything-off baselines of VELDO-0155 and VELDO-0156 generate. Claude Code's generated MCP
configuration gains one entry per selected server (stdio: command, args and env; http: url and headers), values
included, written 0600 into the run's own `config` directory (0700, under the factory state root's `runs`,
outside the clone, never the engine's `XDG_RUNTIME_DIR`) and removed with the run. Codex's `-c mcp_servers`
table carries only the command, arguments, literals and names: a stdio credential reaches the engine environment
under the name its definition gives it and the table lists it in `env_vars`; an http server's bearer
Authorization header reaches it through `bearer_token_env_var` (any other header through `env_http_headers`, the
same route, since the catalog's headers are all references). The receiver installs those values with the
engine's own overrides, after the wrapper's strip. A name two servers claim with different values, or a name the
receiver already sets, is refused by name as delivery failed, never overridden.

A selection whose credential does not resolve (keystore locked, keystore unreachable, a reference whose record is
gone or whose keystore item holds nothing) raises `Undeliverable`, and the receiver refuses the accepted dispatch
as `credential_unavailable:<id>` before any engine process starts, attesting the reserved invocation not
executed. A selection on an adapter with no engine, or on another host's (the Mac leg is VELDO-0147), is refused
as `invalid_input:mcp_delivery:<adapter>`. The new resolver `keystore_credentials` in `control_launch.RESOLVERS`
adds every resolved value, and the bearer token as delivered, to the run's set of resolved values, so VELDO-0141's
receiver replaces them as `[REDACTED:mcp_credential]` before the scanner runs.

The receiver reports a `credentials` event per launch (catalog revisions, credential ids, the route each took and
counts) and puts the same account, with the credential, the reason and the selected revisions, on a refusal. No
value is in either. The new module is a scaffold asset; every changed module's engine copy is byte-identical.

## Criterion rows

Suite: `scripts/suites/85_veldo_0158_credential_delivery.py` (about 3 s). Credentials are set and servers saved
through the VELDO-0144 API routes on a signed-in passkey session; runs go through the real Runner, receiver,
wrapper, Landlock clone entrance and transient scopes. While each main run holds, the suite reads every process
of the account from /proc. Each row reports once.

- AC1, `delivery/claude-private-file`: the file Claude Code's `--mcp-config` names holds exactly the selected
  servers with their values; it is 0600 in a 0700 run directory under the state root, outside the clone and the
  runtime directory; the engine's environment and command line hold no value; each server received its own.
- AC1, `delivery/codex-environment`: the `mcp_servers` table names `env_vars` and `bearer_token_env_var` and holds
  no value; the engine environment carries each value under its name; each server received it through `env_vars`.
- AC1, `delivery/command-lines` (the falsifier's row): no process of the account holds a value on its command
  line; for Claude Code the environments holding one are its servers' alone, for Codex its servers', its engine's
  and the wrapper's forked heartbeat, all inside the run's own containment group; keystore calls carry references.
- AC1, `delivery/own-server-only`: each server holds only its own credential, and the keystore is asked only for
  the selected servers' references.
- AC1, `delivery/not-in-packet-contract-journal`: the servers received the values, while the contracts, dispatch
  records, packets, journal, every byte of the store and the receiver's events hold none.
- AC1, `delivery/private-dir-removed`: each run's directory and the configuration file holding the values are gone
  after the reap; refused launches leave none.
- AC1, `delivery/report`: the credentials event names each revision, credential id and route, never a value.
- AC2, `refusal/keystore-locked`, `refusal/keystore-unreachable`, `refusal/reference-not-found`: the dispatch is
  refused as `credential_unavailable:<id>`, the keystore was asked for that reference, no engine process started,
  and the refusal names the revision, credential and reason.
- AC2, `refusal/no-credential-launches`: with the keystore still locked, a run whose server needs no credential
  exits normally with that server and no keystore lookup.
- AC3, `redaction/claude-keystore-value`, `redaction/codex-keystore-value` (the falsifier's rows): each run prints
  the low-entropy, pattern-free keystore values alone, inside a command's output and on its error stream; every
  occurrence is the `mcp_credential` marker, no line holds any word of either value, and each line names the kind.
- AC3, `redaction/per-run-set`: a run selecting only another server has its own value replaced, while the tracker
  value it prints from a suite file is kept as printed, since it was never resolved for that run.
- Controls: `fixture/route-set` (route writes and store metadata), `fixture/control-word` (a word no credential
  names is kept), `format/fake-lines` (every fake line against the binaries' tables) and VELDO-0172's
  `fake/capture:0158_credential_delivery`.

## Red record and mutations

`red-at-7851ae9b.json`: the current suite against the unchanged tree of the commit before this change. All 14
behavior rows (and `format/fake-lines`) fail by assertion; only the two fixture rows hold.

`mutations.json` (`python3 -B proof/VELDO-0158/drive.py`): a green baseline, green no-op copies of the three
mutated modules, and six finding-158 mutations, each red on its named rows by assertion, with its diff beside it.
`python3 scripts/check_teeth_mutations.py --finding 158 --jobs 2` rejects all six.

| Mutation | Named rows |
|---|---|
| `delivery158-codex-value-on-argv` (AC1 falsifier) | `delivery/command-lines` |
| `delivery158-run-without-server` (AC2 falsifier) | the three `refusal/` rows |
| `delivery158-value-not-in-set` (AC3 falsifier) | `redaction/claude-keystore-value`, `redaction/codex-keystore-value` |
| `delivery158-claude-value-in-environment` | `delivery/claude-private-file` |
| `delivery158-every-server-variable` | `delivery/own-server-only` |
| `delivery158-run-directory-kept` | `delivery/private-dir-removed` |

No real engine, login, keyring or credential is used: the Secret Service is a generated `secret-tool` first on
PATH, and every value is assembled at run time.
