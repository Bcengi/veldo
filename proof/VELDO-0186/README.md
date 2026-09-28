# VELDO-0186 proof

Factory setup now carries the runtime files its installed modules name and binds qualified host
engines. The service census retains its Python closure and derives runtime assets from full path
literals and the Path expression used by Codex. The runtime qualification entry point is included
so its LangGraph record is part of that census. Missing source assets refuse installation by name.
The service configuration records each installed asset's path and SHA256 digest.

Setup resolves the Claude and Codex commands on PATH without executing either. Claude's resolved
versioned filename must occur in its qualification record. Codex's package version and vendor path
must match its record. Both digests are checked before any setup write. After service installation,
the existing Claude pin writer copies the version at mode 0555 under the state root, and both
engines bind against the installed qualification records. Their paths, versions and digests are
written to host/engines.json and returned by setup, together with the asset and pin counts. The
installed receiver configuration names that same state root. No account adapters are created here;
VELDO-0185 owns them.

| Criterion | Behavior row | What the production path proves |
| --- | --- | --- |
| AC1 | `runtime/assets` | Factory CLI setup installs all three current records plus a planted future runtime literal, byte-identical with recorded digests and the correct asset count. Only the fixture manager's daemon reload is requested. |
| AC1 | `runtime/missing` | The real service installer refuses a loaded module's missing runtime source by its exact path before creating the installation. |
| AC2 | `bind/engines` | The installed receiver's engine protocol binds Claude using the installed receiver configuration's state root and Codex using its vendor path. The Claude copy is regular, byte-identical and 0555; both bindings equal setup's persistent and returned records. |
| AC2 | `engines/unlisted` | Real setup refuses each engine's unlisted version with missing_evidence:engine_baseline:9.9.9, leaving its fresh state root empty. |
| AC2 | `engines/digest` | Real setup refuses changed bytes for each engine with binding_mismatch:engine_digest, leaving its fresh state root empty. |

The suite uses generated OpenSSH keys, a generated token stand-in, real Git repositories, the real
store, enrollment, service installation and pin writers. Containment host qualification and daemon
reload are fixture seams: no real service manager is contacted. Engine fixtures are inert executable
bytes, never launched. They carry VELDO-0172's shared constructor and each suite using them calls
conform_fake at teardown. They emit no stream events, so that supporting row compares zero events
and makes no claim about engine stream formats. Codex qualification is written by its production
writer; the Claude fixture uses the committed qualification entry with the fixture's digest.

`drive.py` runs the current suite against an unchanged Git archive of the pre-change commit.
`red-at-9f1a0445.json` records all five behavior rows red by assertion, with no raised test section.
Every behavior row is reported once. The supporting format hook is outside the behavior red count.

Finding 186 registers eight uniquely named mutations:

| Mutation | Named failing rows |
| --- | --- |
| `setup186-python-only` | runtime/assets, bind/engines |
| `setup186-skip-claude-pin` | bind/engines |
| `setup186-missing-runtime-ignored` | runtime/missing |
| `setup186-claude-unlisted-taxonomy` | engines/unlisted |
| `setup186-codex-unlisted-taxonomy` | engines/unlisted |
| `setup186-claude-digest-unchecked` | engines/digest |
| `setup186-codex-digest-unchecked` | engines/digest |
| `setup186-receiver-without-state-root` | bind/engines |

The Python-only mutant also prevents binding because the installed qualification records are
absent. The digest mutants remove the preflight check: any later pin refusal is too late because
setup has already written the state root. Mutation execution is reserved for the reviewer by the
owner's instructions. `mutations.json` records registration and pending execution, not rejection.

The footprint includes the existing service installer fixtures in suites 66 (0047), 71 (0130 and
0138), and 83 (0154). They copy the runtime directory into their source trees. Both factory setup
fixtures, suites 73 (0139) and 74 (0140), use this proof's `fixtures.install` helper to supply runtime
records and qualified inert engine bytes. Suite 74 was added to the footprint in the review repair:
its Python-only source tree caused all eight standing-delegation rows to fail before their scenarios
could run. It now also checks the shared fake-format constructor at teardown and restores PATH.
The scaffold ships the setup helper. No production refusal was weakened.

The review repair audited all setup and service-install calls in the suites and shared helpers.
The setup callers are 73, 74 and 86; the other real service installers are 66, 71 (0130 and 0138),
and 83. No additional shared helper lays down a factory. The other suites that load the service
construct service objects without calling its installer.

The mutation checker observes each `expect` call, removes any detail after a colon, and matches the
last whitespace-separated word against each mutation target. Finding 186 previously registered
`VELDO-0186 runtime/assets` where that reader requires `runtime/assets`; the honest run therefore
found no matching observation even though the suite passed. All eight registrations now use the
final labels shown above. The suite reports each full behavior row exactly once and returns
normally; the checker's worker can then exit zero. Static inspection checked target coverage of all
five rows, unique mutation names, and unique production edit anchors. This is not a mutation run.

`verification.json` records the normal and clean-environment runs of suite 86, the affected fixture
suites, and footprint, anchor, validation and engine-copy checks. The selftest selector's process
exit is separately governed by `RunScope`: a passing selected run exits 2 because it is partial.
This status does not apply to the mutation worker, which executes the suite directly and returns
its captured assertions. The shared preamble and fixture-format hooks are included in selector
counts. The full selftest, gate and mutation runners remain reserved for the reviewer.
This proof is ready for independent review; it is not a gate stamp or a landing authorization.
