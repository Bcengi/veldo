"""Claude Code's login and usage reports as the launch receiver reads them, VELDO-0062.

Every format and name here is the installed CLI's own (Claude Code 2.1.281), read from the schema
its binary embeds for the stream JSON messages and from its credential tables; the extraction is
proof/VELDO-0062/extract_formats.py and its table cli-formats.json.

LOGIN. A Claude Code run logs in only through its subscription account's profile, the directory
CLAUDE_CONFIG_DIR names (control_accounts sets it from the account the dispatch recorded). CREDENTIALS
is every name the binary's own lists make a login: the API keys and bearer tokens, the provider
switches and their companions, the endpoint overrides, the skip-auth switches, its list of Anthropic
secrets with their INPUT_ forms, the session, bridge, trusted-device, background-session and
file-descriptor tokens, the variables a host credentials file may set, and every login, credential
redirect and settings redirect of the set of variables it refuses to take from a settings file
(CLAUDE_SECURESTORAGE_CONFIG_DIR, CLAUDE_CODE_HOST_CREDS_FILE, CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST, the
managed and remote settings paths, the OAuth, staging, bridge and federation overrides). None reaches
the engine from the inherited environment, and an adapter configuring one is refused by name.
SETTINGS are that set's Claude Code connection settings that are not a login: stripped from the
inherited environment (the owner's shell's), passed when the adapter configures them. The set's general
proxy, CA, runtime, cloud and home names are neither: the worker's tools need them. The model
configuration (the binary's model table, ANTHROPIC_MODEL and the rest) is not a login either: an adapter
configures it and it reaches the engine. (The subscription token of an account configured to use one
is VELDO-0155's, below.)

USAGE, FROM THE CLI'S OWN STREAM (print mode with stream JSON output). What is counted is only what
the CLI reports, at the granularity it reports it:
- an `assistant` event's `message.usage`, once per message id (a message is streamed in several
  events with the same id and usage, and a repeated delivery changes nothing), the main loop's and a
  subagent's alike (`parent_tool_use_id` set): tokens are the sum of its input, output, cache
  creation and cache read token counts (the nullable ones count when present; the nested
  `cache_creation` and `server_tool_use` objects are breakdowns, never added); messages are the
  distinct assistant messages seen. These are the live observations a cap is checked against;
- the `result` event's `modelUsage`, the conclusive total: per model, over every model call of the
  invocation (main loop, Task subagents, sidechains, compaction), cumulative, so the latest result
  is read. Its tokens are the sum over every model of inputTokens, outputTokens, cacheReadInputTokens
  and cacheCreationInputTokens. The binary says a resumed or forked session continues from the totals
  its transcript saved, so the first result already carries the earlier turns: an invocation whose
  contract resumes a session (`resumes`, its id) and whose CLI reports that same session id is charged
  its result's total less `prior`, the resumed session's running total the ledger settled last
  (Reservations.session); an unknown `prior`, or a total below it, leaves this invocation's tokens
  unknown, never the whole total. When the CLI reports another session id than the one resumed (it
  started a fresh session, or forked one), nothing places its total against the resumed session's, so
  the whole running total is charged: a fork that carried the earlier turns is over-counted, never
  under-counted. `session()` is the session this invocation ran, the CLI's running total for it, which
  the final report settles for the next resumption, and which case charged it (`charged`: `whole` for
  no resumption, `difference` for the resumed session, `whole_other_session` for another one). The result's `usage` is never read for accounting: the binary's schema
  says it is the MAIN AGENT LOOP ONLY and to prefer modelUsage. A result without a readable
  modelUsage leaves tokens unknown (never zero, never the main loop's usage) and their reservation is
  retained. Messages are the distinct assistant messages or `num_turns`, whichever is more; only a
  result makes them conclusive;
- a `rate_limit_event`'s `rate_limit_info`: `rateLimitType` names the window, `status` `rejected`
  means its allowance is exhausted (`allowed` and `allowed_warning` are not), `resetsAt` is its
  reported reset (Unix seconds) and `utilization` what the CLI reported. Nothing is invented: a missing
  reset stays missing.
`total_cost_usd` and `costUSD` are never read: subscription usage has no per-call price.

THE ACCOUNT'S LIMIT (VELDO-0160). `limit()` is the last limit the stream stated, with its window, reset
and signal: a `rate_limit_event` whose status is `rejected` (the stream reports its window exhausted,
`stream`), or the rate-limit result (`result`): a `result` with `is_error` whose text is the binary's
usage-limit message, "You've hit your <limit>" and, when it states one, " \u00b7 resets <time> (<zone>)"
(its limit names are the binary's table of rate-limit windows, LIMIT_NAMES; a name outside it is the
`unified` window), or one of the binary's other texts for the account refused (LIMIT_REJECTED: "You're
out of usage credits" with the reset it may state, and the org, seat, service, admin and $0-group texts),
each the `unified` window. The time is the binary's own format in the zone it names: "3pm" or "3:05pm" for a
reset within a day (the next such minute), "Sep 28, 3pm" with the year when it is another year. The reset
is the END of the stated minute (the message truncates to the minute, so the window never reopens before
it); a message stating none, or a time this reading cannot place, is a window with no reset, and the
account stays refused until a later observation says otherwise. The rate-limit result is also recorded
as a window. Any other message (the binary's "Server is temporarily limiting requests (not your usage
limit)", an overloaded model) is not the account's limit.

TOOL CALLS (VELDO-0160). `tool_calls(event, seen, redacted)` names the MCP tool calls an event of the
stream shows: each `tool_use` block of an `assistant` message whose name is `mcp__<server>__<tool>`, by
its id. It reads only the forms the binary's own tables list (proof/VELDO-0062/cli-formats.json,
claude_code tool_forms): the SDK message union (MESSAGES), the content blocks of an assistant and of a
user message, the streaming events of a `stream_event` and the built-in tool names (BUILTIN_TOOLS), and
fails closed on everything else. What may be a tool call and cannot be read is named `unreadable` (an
assistant message whose content is not a list, a content block that is not an object naming its type, a
`tool_use` block whose name is not a string, or, on a line whose `redacted` field is set, a `tool_use`
name that is neither `mcp__...` nor a built-in tool, since the redaction may have replaced it). A
tool-call form this reading does not recognize is named `unknown` with its form, never taken for no call:
an `mcp_tool_use`, `server_tool_use` or other server-tool block, a `stream_event` carrying any block that
is not tool-free (a `tool_use` first), a user `tool_result`, a `tool_progress` or a `tool_use_summary`
for a call id `seen` never held, a `tool_use` in a user message, and any message, subtype, block or
streaming event type the tables do not list. The frames the CLI writes outside the message union are
read by the binary's own table (TOOL_FREE_FRAMES): those whose schema provably carries no tool call
(`keep_alive`, `control_cancel_request`, `active_goal`, `autocompact_state` and the `post_turn_summary`
and `task_summary` system messages) are no call, and the rest (a control request or response, the
transcript mirror) are unknown. `seen` is the ids of every tool call shown so far, to which each
`tool_use` read is added.

A tool name a frame carries beside the content blocks counts too (TOOL_FIELDS lists every field of the
binary's messages whose name names a tool, and how it is read): a `tool_progress`'s `tool_name`, the REPL
tool's inner call, which reaches the stream only as a `tool_progress` of the REPL call carrying a
`repl_call` the schema omits (an `mcp__` inner name is that MCP call, a built-in one no call, any other
an unknown call; a `repl_call` that is not an object naming its inner tool is unreadable), a
`system/task_progress`'s `last_tool_name` and its `workflow_progress` entries' `lastToolName`, and an
assistant message's `attribution_mcp_server` and `attribution_mcp_tool` (the MCP tool that produced it)
and `batch_tool_uses` names. Each such name is read as a `tool_use` name is: `mcp__<server>__<tool>` is
that MCP call; on a redacted line a name neither `mcp__...` nor built in is `unreadable`. The built-in
names are BUILTIN_TOOL_NAMES and the current name of a tool it lists under an old one (the Agent tool,
listed as `Task`: BUILTIN_RENAMED).

A SUB-AGENT'S CALLS ARE COUNTED BY ITS TASK (`Tasks`). A sub-agent's own `tool_use` blocks reach the stream
only from a sub-agent the main thread started: an agent that one of those starts (depth 2 or more) has its
messages dropped unless the SDK's `forwardSubagentText` option is set, so its calls leave no block, and its
task's progress names only the last tool of each of its messages. What does reach the stream is each task's
count of its own calls: the `system/task_progress` and `system/task_notification` frames of a task (keyed by
the `tool_use_id` of the call that started it, as `system/task_started` names it) carry `usage.tool_uses`,
which the binary's tracker raises by one for every `tool_use` block of the task's own assistant messages, and
those messages, when they are forwarded, carry the task's id as their `parent_tool_use_id` (TASK_COUNTS, read
from the binary into cli-formats.json). `Tasks` compares, for each task, the highest count the stream
reported with the distinct `tool_use` blocks it showed under that parent; any shortfall is that many calls the
record cannot name, an unknown call of form `task_tool_uses` naming the task and the shortfall (`unshown`),
at the line that reported the count. A count frame whose count cannot be read (a `task_progress` without a
count of calls as a whole number, a `task_notification` whose usage has none, either without the task's id) is
unreadable, and so is a count lower than one the same task reported before, since a count only rises.

HIDDEN NESTED WORK (VELDO-0160, the structural rule). `nested_work(event)` names each construct through which
an event shows the run doing work its stream may not show, by class (NESTED_TOOLS and NESTED, the binary's,
cli-formats.json nested_work): `agent` (the Agent tool, its old name Task, SendMessage to a teammate), `skill`
(the Skill tool), `repl` (the REPL tool, or its inner call on a tool_progress), `workflow` (the Workflow tool, or
a task frame of a workflow), each tool wherever a tool that ran is named (a `tool_use` block, streamed or not, a
tool_progress's tool or REPL inner tool, a task's last tool or its workflow agents', a batch tool name);
`remote` (the RemoteTrigger tool, a deferred tool that manages the account's cloud agent routines) and `cron`
(the CronCreate tool, a prompt scheduled to fire later), each wherever a tool is named the same way;
`task_frames` (any system frame of a task); `nested_progress` (a message that names its task in
`parent_tool_use_id`, as the CLI forwards a sub-agent's or forked skill's `agent_progress` and `skill_progress`,
or such a progress frame itself); and `fork` (the Skill tool's result when it forked an agent).

WORK OUTSIDE THE RUN (VELDO-0160, the lead's decision). `remote_agents(event)` names each call through which an
event shows the run starting an agent outside itself, which may act through the account's claude.ai connectors
whatever the run's configuration (REMOTE_AGENT, the binary's, cli-formats.json nested_work remote_agent): any
RemoteTrigger call (`remote`; its create, update and run start a cloud agent routine), and a durable CronCreate
(`cron`; its prompt persists to the project's scheduled tasks and fires after the run). A CronCreate is durable
unless the call's own input, a `tool_use` block of an assistant message or the REPL tool's inner call, leaves its
`durable` field out or gives it a value the binary reads as false; a CronCreate named where its input is not
given (a streamed block, a tool_progress's tool, a task's last tool) may be durable and is named too.

Each observation carries the raw line it came from (the receipt) and that line's digest.

THE PINNED EXECUTABLE, VELDO-0060. A Claude Code adapter names the version it runs (`executable:
{version}`), never a path. The qualification record (QUALIFICATION, the installed
`.veldo/runtime/claude-qualification.json` beside this module, canonical at engine/runtime/) lists each
qualified version with its digest, the flags of print mode with stream JSON output (read from the
binary's own options, proof/VELDO-0060/cli-options.json), the environment it runs with
(DISABLE_AUTOUPDATER, the binary's switch that turns its updater off), its terminal protocol, its
subscription login and the usage units and rate-limit windows it reports. `pin` copies the versioned
file the installer keeps (~/.local/share/claude/versions/<version>) under the factory state root, at
<state root>/engines/claude_code/<version>, and refuses a copy whose digest is not the qualified one;
the interactive updater may remove an old version, and the auto-updating ~/.local/bin/claude link is
never read. `bind` is the check every launch makes before acceptance, so before anything is spawned: a
version the record does not list, a pinned copy that is absent, a link or not a regular file, and a
copy whose digest differs are each refused by name, as are a linked directory on the way to it, a copy
that is not this account's own, and one that is writable or carries a setuid, setgid or sticky bit (the pin
writes it 0555). `command` is the adapter's prefix, the pinned path and the qualified flags; the role's own
selections are VELDO-0127's; the everything-off baseline (VELDO-0155) follows the flags.

THE TERMINAL RECORD AND THE ARTIFACT, VELDO-0060. `Terminal` reads the same stream and returns what an
invocation's output yields, judged by the receiver and never by the worker: the decoded `result` event
(its subtype, error flag, turns, session, stop reason, the digest of its result text, its errors and
its tokens, modelUsage's total or None when the result carries no readable modelUsage, never its
main-loop `usage`),
the digest of the line it came from, how many lines the stream had and how many were not a JSON event,
and the verdict. Only a zero exit with no signal, no stop and no deadline, a stream of well-formed
events and a `result` whose subtype is `success` and whose `is_error` is false is `complete`; a zero
exit whose stream has no result is `missing_result`, never a completion. The usage of that invocation
is the Meter's: a result without readable usage leaves it unknown and its reservation retained.

THE EVERYTHING-OFF BASELINE AND THE PAID-API GUARD, VELDO-0155. A version is qualified with BASELINE (the
record's `baseline`, which must equal it, else `missing_evidence:engine_baseline:<version>` before
acceptance). `baseline(binding, run)` is what every run adds right after its qualified flags: no setting
source but the run's generated `--settings` file (`disableAllHooks`), `--strict-mcp-config` with the run's
generated `--mcp-config` file (no server until VELDO-0127 lists them), `--disable-slash-commands`, and
CLAUDE_CODE_DISABLE_CLAUDE_MDS and CLAUDE_CODE_DISABLE_AUTO_MEMORY; the files are written into the run's
own configuration directory (control_launch). On 2.1.281 the setting-sources restriction also keeps the
profile's and the clone's MCP servers, skills, instruction files and hooks out (the binary gates each by
its source); the other switches keep out what no source covers: the claude.ai connectors of the account's
login, the bundled skills, the managed instruction files and the flag, plugin and session hooks
(proof/VELDO-0155/README.md). A version is also qualified with stream JSON input (INPUT_FLAGS among its
flags, else `missing_evidence:engine_input_protocol:<version>` before acceptance), so nothing reaches the
model until the receiver writes the prompt. `Guard` is the handshake and the stream check: the receiver
writes the initialize control request first and the prompt only once the binary's answer names a
subscription login (the first-party backend, no API key, a claude.ai subscription, whose subscriptionType
is one of the binary's Enterprise, Team, Max and Pro labels, or the account's own subscription token); any
other answer stops the run by name before any prompt is written
(`paid_api:<field>:<value>`, stop cause `paid_api`), and so does every init event of the stream whose
apiKeySource is not `none`. `login_problem` is the check before acceptance for the login apiKeySource
cannot show: an Anthropic profile (user_oauth or oidc_federation) the engine environment reaches through
XDG_CONFIG_HOME or HOME, which the binary takes ahead of the claude.ai login and reports as `none`, is
refused by name (`paid_api:anthropic_profile:<type>`) from the profile's configuration alone, a relative
path resolved against the engine's working directory as the binary resolves it. The subscription token
of an account configured to use one reaches the engine as CLAUDE_CODE_OAUTH_TOKEN from the receiver's
configuration (control_launch).
Standard library only.
"""
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import time
import zoneinfo

PROVIDER = 'claude_code'
CREDENTIALS = frozenset((
    'AGENT_PROXY_AUTH_TOKEN', 'ALL_INPUTS', 'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN',
    'ANTHROPIC_AWS_API_KEY', 'ANTHROPIC_AWS_BASE_URL', 'ANTHROPIC_AWS_WORKSPACE_ID', 'ANTHROPIC_BASE_URL',
    'ANTHROPIC_BEDROCK_BASE_URL', 'ANTHROPIC_BEDROCK_MANTLE_BASE_URL', 'ANTHROPIC_CONFIG_DIR',
    'ANTHROPIC_CUSTOM_HEADERS', 'ANTHROPIC_FEDERATION_RULE_ID', 'ANTHROPIC_FOUNDRY_API_KEY',
    'ANTHROPIC_FOUNDRY_AUTH_TOKEN', 'ANTHROPIC_FOUNDRY_BASE_URL', 'ANTHROPIC_FOUNDRY_RESOURCE',
    'ANTHROPIC_GOOGLE_CLOUD_BASE_URL', 'ANTHROPIC_GOOGLE_CLOUD_LOCATION', 'ANTHROPIC_GOOGLE_CLOUD_PROJECT',
    'ANTHROPIC_GOOGLE_CLOUD_WORKSPACE_ID', 'ANTHROPIC_IDENTITY_TOKEN', 'ANTHROPIC_IDENTITY_TOKEN_FILE',
    'ANTHROPIC_ORGANIZATION_ID', 'ANTHROPIC_PROFILE', 'ANTHROPIC_SCOPE', 'ANTHROPIC_SERVICE_ACCOUNT_ID',
    'ANTHROPIC_UNIX_SOCKET', 'ANTHROPIC_VERTEX_BASE_URL', 'ANTHROPIC_VERTEX_PROJECT_ID',
    'ANTHROPIC_WORKSPACE_ID', 'AWS_BEARER_TOKEN_BEDROCK', 'CLAUDE_BG_AUTH_SNAPSHOT_PATH',
    'CLAUDE_BG_CLAIM_AUTH', 'CLAUDE_BG_PTY_AUTH', 'CLAUDE_BG_RV_AUTH', 'CLAUDE_BG_SOCKET_TOKENS_PATH',
    'CLAUDE_BRIDGE_BASE_URL', 'CLAUDE_BRIDGE_OAUTH_TOKEN', 'CLAUDE_BRIDGE_SESSION_INGRESS_URL',
    'CLAUDE_CODE_API_BASE_URL', 'CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR', 'CLAUDE_CODE_ARTIFACTS_API_BASE_URL',
    'CLAUDE_CODE_ARTIFACTS_API_TOKEN', 'CLAUDE_CODE_ARTIFACT_ASSET_BASE_URL',
    'CLAUDE_CODE_ARTIFACT_LIVE_BASE_URL', 'CLAUDE_CODE_ARTIFACT_SYNC_BASE_URL',
    'CLAUDE_CODE_ARTIFACT_VIEWER_BASE_URL', 'CLAUDE_CODE_CLIENT_CERT', 'CLAUDE_CODE_CLIENT_KEY',
    'CLAUDE_CODE_CLIENT_KEY_PASSPHRASE', 'CLAUDE_CODE_CUSTOM_OAUTH_URL',
    'CLAUDE_CODE_DISABLE_ADMIN_ENV_UNION', 'CLAUDE_CODE_ENVIRONMENT_KIND',
    'CLAUDE_CODE_FEDERATION_CACHE_DIR', 'CLAUDE_CODE_GATEWAY_TOKEN_FILE_DESCRIPTOR',
    'CLAUDE_CODE_HFI_BEARER_TOKEN', 'CLAUDE_CODE_HOST_AUTH_ENV_VAR', 'CLAUDE_CODE_HOST_CREDS_FILE',
    'CLAUDE_CODE_HOST_SESSION_ID', 'CLAUDE_CODE_MANAGED_SETTINGS_PATH', 'CLAUDE_CODE_MCP_SERVE_AUTH_TOKEN',
    'CLAUDE_CODE_MEMORY_API_BASE_URL', 'CLAUDE_CODE_MEMORY_API_TOKEN', 'CLAUDE_CODE_MOCK_REMOTE_SETTINGS',
    'CLAUDE_CODE_OAUTH_CLIENT_ID', 'CLAUDE_CODE_OAUTH_REFRESH_TOKEN', 'CLAUDE_CODE_OAUTH_SCOPES',
    'CLAUDE_CODE_OAUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR',
    'CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST', 'CLAUDE_CODE_REMOTE_SESSION_ID',
    'CLAUDE_CODE_REMOTE_SETTINGS_PATH', 'CLAUDE_CODE_SESSION_ACCESS_TOKEN',
    'CLAUDE_CODE_SKIP_ANTHROPIC_AWS_AUTH', 'CLAUDE_CODE_SKIP_ANTHROPIC_GOOGLE_CLOUD_AUTH',
    'CLAUDE_CODE_SKIP_BEDROCK_AUTH', 'CLAUDE_CODE_SKIP_FOUNDRY_AUTH', 'CLAUDE_CODE_SKIP_MANTLE_AUTH',
    'CLAUDE_CODE_SKIP_VERTEX_AUTH', 'CLAUDE_CODE_SLACK_TAG_TOKEN', 'CLAUDE_CODE_USE_ANTHROPIC_AWS',
    'CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD', 'CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_FOUNDRY',
    'CLAUDE_CODE_USE_GATEWAY', 'CLAUDE_CODE_USE_MANTLE', 'CLAUDE_CODE_USE_VERTEX',
    'CLAUDE_CODE_WEBSOCKET_AUTH_FILE_DESCRIPTOR', 'CLAUDE_CONFIG_DIR', 'CLAUDE_LOCAL_OAUTH_API_BASE',
    'CLAUDE_LOCAL_OAUTH_APPS_BASE', 'CLAUDE_LOCAL_OAUTH_CONSOLE_BASE', 'CLAUDE_REMOTE_TOOLS_BRIDGE_URL',
    'CLAUDE_SECURESTORAGE_CONFIG_DIR', 'CLAUDE_SESSION_INGRESS_TOKEN_FILE', 'CLAUDE_TRUSTED_DEVICE_TOKEN',
    'CLOUD_ML_REGION', 'INPUT_ALL_INPUTS', 'INPUT_ANTHROPIC_API_KEY', 'INPUT_ANTHROPIC_AUTH_TOKEN',
    'INPUT_ANTHROPIC_AWS_API_KEY', 'INPUT_ANTHROPIC_CUSTOM_HEADERS', 'INPUT_ANTHROPIC_FOUNDRY_API_KEY',
    'INPUT_ANTHROPIC_FOUNDRY_AUTH_TOKEN', 'INPUT_ANTHROPIC_IDENTITY_TOKEN',
    'INPUT_ANTHROPIC_IDENTITY_TOKEN_FILE', 'INPUT_CLAUDE_CODE_ARTIFACTS_API_TOKEN',
    'INPUT_CLAUDE_CODE_MEMORY_API_TOKEN', 'INPUT_CLAUDE_CODE_OAUTH_REFRESH_TOKEN',
    'INPUT_CLAUDE_CODE_OAUTH_TOKEN', 'INPUT_CLAUDE_CODE_SLACK_TAG_TOKEN', 'USE_LOCAL_OAUTH',
    'USE_STAGING_OAUTH', '_CLAUDE_CODE_ASSUME_FIRST_PARTY_BASE_URL'))
SETTINGS = frozenset((
    'API_FORCE_IDLE_TIMEOUT', 'CLAUDE_CODE_CERT_STORE', 'CLAUDE_CODE_ENABLE_PROXY_AUTH_HELPER',
    'CLAUDE_CODE_PROXY_AUTH_HELPER_TTL_MS', 'CLAUDE_CODE_PROXY_RESOLVES_HOSTS'))
TOKEN_FIELDS = ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')
MODEL_TOKEN_FIELDS = ('inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens')
# VELDO-0160: the usage-limit message of the binary's rate-limit result, and its names of the windows
# (proof/VELDO-0062/cli-formats.json, claude_code usage_limit).
LIMIT_MESSAGE = "You've hit your "
LIMIT_NAMES = {'session limit': 'five_hour', 'weekly limit': 'seven_day', 'Opus limit': 'seven_day_opus',
               'Sonnet limit': 'seven_day_sonnet', 'Fable limit': 'seven_day_overage_included',
               'usage credit limit': 'overage'}
LIMIT_WINDOW = 'unified'
# The binary's other texts for the account refused, which do not start with LIMIT_MESSAGE (cli-formats.json,
# claude_code usage_limit rejected): each is the `unified` window, its reset the one it states, if any.
LIMIT_REJECTED = ("You're out of usage credits", 'Your org is out of usage \u00b7 add funds to continue',
                  'Your org is out of usage \u00b7 contact your admin', "Your seat type doesn't include usage",
                  "Your seat type doesn't include usage credits", 'This service is disabled for your org',
                  'Your usage allocation has been disabled by your admin', "Your group's usage limit is set to $0")
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
RESETS = re.compile(r'resets (?:(?P<month>[A-Z][a-z]{2}) (?P<day>\d{1,2}), (?:(?P<year>\d{4}), )?)?'
                    r'(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?(?P<half>am|pm) \((?P<zone>[^()]+)\)')
MCP_PREFIX = 'mcp__'
# The tool-call forms (VELDO-0160), from the binary's tables (proof/VELDO-0062/cli-formats.json, claude_code
# tool_forms). MESSAGES: the stream's message types, with the subtype of those that have one (SUBTYPED).
SUBTYPED = ('system', 'result')
MESSAGES = frozenset((
    ('assistant', None), ('auth_status', None), ('command_lifecycle', None), ('conversation_reset', None),
    ('prompt_suggestion', None), ('rate_limit_event', None), ('result', 'error_during_execution'),
    ('result', 'error_max_budget_usd'), ('result', 'error_max_structured_output_retries'), ('result', 'error_max_turns'),
    ('result', 'success'), ('stream_event', None), ('tool_progress', None), ('tool_use_summary', None), ('user', None),
) + tuple(('system', sub) for sub in (
    'api_retry', 'background_tasks_changed', 'cloud_session_delta', 'code_change_published', 'commands_changed',
    'compact_boundary', 'control_request_progress', 'dev_intent', 'elicitation_complete', 'feedback_draft_queued',
    'files_persisted', 'hook_progress', 'hook_response', 'hook_started', 'informational', 'init',
    'local_command_output', 'memory_recall', 'mirror_error', 'model_refusal_fallback', 'model_refusal_no_fallback',
    'notification', 'peer_message_hold', 'per_turn_effort_changed', 'permission_denied', 'plugin_install',
    'session_state_changed', 'status', 'task_notification', 'task_progress', 'task_started', 'task_updated',
    'thinking_tokens', 'turn_handoff_available', 'turn_preempted', 'vcs_state_changed', 'worker_shutting_down')))
# The content blocks, of an assistant message (RESPONSE_BLOCKS) and of a user message (REQUEST_BLOCKS), and
# of those the ones that are no tool call (TOOL_FREE_BLOCKS: text, reasoning, compaction; a user message's
# text, images, documents and search results). Every other listed block is a tool call or a tool's result.
RESPONSE_BLOCKS = ('text', 'tool_use', 'thinking', 'redacted_thinking', 'server_tool_use', 'web_search_tool_result',
                   'web_fetch_tool_result', 'advisor_tool_result', 'code_execution_tool_result',
                   'bash_code_execution_tool_result', 'text_editor_code_execution_tool_result',
                   'tool_search_tool_result', 'mcp_tool_use', 'mcp_tool_result', 'container_upload', 'compaction',
                   'fallback')
REQUEST_BLOCKS = ('text', 'image', 'document', 'search_result', 'tool_use', 'tool_result', 'thinking',
                  'redacted_thinking') + RESPONSE_BLOCKS[4:] + ('mid_conv_system',)
TOOL_FREE_BLOCKS = frozenset(('text', 'thinking', 'redacted_thinking', 'compaction', 'fallback'))
TOOL_FREE_REQUEST = TOOL_FREE_BLOCKS | {'image', 'document', 'search_result', 'mid_conv_system'}
STREAM_EVENTS = ('message_start', 'content_block_start', 'content_block_delta', 'content_block_stop',
                 'message_delta', 'message_stop')
# The binary's BUILTIN_TOOL_NAMES: a partial list of its own tools, so a redacted name it omits asks. It predates
# a rename: its `Task` is the Agent tool's old name (cli-formats.json builtin_renamed), so the tool's current
# name is built in too (BUILTIN).
BUILTIN_TOOLS = frozenset(('Bash', 'Read', 'Write', 'Edit', 'Glob', 'Grep', 'NotebookEdit', 'WebFetch', 'WebSearch',
                           'Task', 'TodoWrite', 'TaskCreate', 'TaskUpdate', 'TaskGet', 'TaskList', 'TaskStop', 'Skill',
                           'REPL', 'JavaScript', 'AskUserQuestion', 'ToolSearch', 'SendUserMessage'))
BUILTIN_RENAMED = {'Agent': ('Task',)}
BUILTIN = BUILTIN_TOOLS | frozenset(BUILTIN_RENAMED)
# The frames the CLI writes outside the SDK message union (cli-formats.json frames) whose schema provably carries
# no tool call; the others (control requests and responses, the transcript mirror) are unknown calls.
TOOL_FREE_FRAMES = frozenset((('active_goal', None), ('autocompact_state', None), ('control_cancel_request', None),
                              ('keep_alive', None), ('system', 'post_turn_summary'), ('system', 'task_summary')))
# Every field of a stream message whose name names a tool, as the binary's schema declares it (cli-formats.json
# tool_fields) and as its emitters write it beyond that schema (emitted_tool_fields), and how it is read. `call`:
# the name of a tool that ran or may run, read as that call (TOOL CALLS in the module docstring). `id`: a call's
# id, read against the ids shown. `free`: no call of its own: a count, a display or input copy of a block read
# in the content, a tool the run offers or discovered, a call denied or deferred and never run. `task`: the id of
# the task a frame or a sub-agent's message belongs to, and `count`: a task's count of its own calls, each read by
# `Tasks` (TASK_COUNTS).
TOOL_FIELDS = {
    'assistant': {'attribution_mcp_tool': 'call', 'batch_tool_uses': 'call', 'context_usage.mcp_tools': 'free',
                  'message.usage.server_tool_use': 'free', 'parent_tool_use_id': 'task', 'tool_use_meta': 'free',
                  'wire_tool_inputs': 'free'},
    'stream_event': {'parent_tool_use_id': 'free'},
    'system/compact_boundary': {'compact_metadata.pre_compact_discovered_tools': 'free'},
    'system/informational': {'tool_use_id': 'free'},
    'system/init': {'tools': 'free'},
    'system/permission_denied': {'tool_name': 'free', 'tool_use_id': 'free'},
    'system/task_notification': {'tool_use_id': 'task', 'usage.tool_uses': 'count'},
    'system/task_progress': {'last_tool_name': 'call', 'tool_use_id': 'task', 'usage.tool_uses': 'count',
                             'workflow_progress.lastToolName': 'call'},
    'system/task_started': {'tool_use_id': 'task'},
    'system/turn_handoff_available': {'tools': 'free'},
    'tool_progress': {'parent_tool_use_id': 'free', 'repl_call.inner_tool_input': 'free',
                      'repl_call.inner_tool_name': 'call', 'repl_call.inner_tool_use_id': 'id', 'tool_name': 'call',
                      'tool_use_id': 'id'},
    'tool_use_summary': {'preceding_tool_use_ids': 'id'},
    'user': {'parent_tool_use_id': 'free', 'source_tool_assistant_uuid': 'free', 'source_tool_use_id': 'free',
             'tool_result_meta': 'free', 'tool_use_result': 'free'},
}
# How a task's count of its calls is read (cli-formats.json tool_forms task_counts): the frames that carry the count,
# the field that holds it, the field of a frame naming its task, and the field of a sub-agent's message naming it.
TASK_COUNTS = {'frames': ('system/task_notification', 'system/task_progress'), 'count': 'usage.tool_uses',
               'task': 'tool_use_id', 'parent': 'parent_tool_use_id'}
# The constructs through which a run can do work its stream may not show (VELDO-0160, the structural rule; the
# binary's, cli-formats.json tool_forms nested_work), by class: the tools that run an agent, a skill, code or a
# workflow, by every name a frame may give them (NESTED_TOOLS); a task's own frames; the fields a task frame gives a
# workflow and a workflow's task type; the REPL tool's inner call on a tool_progress; the field a sub-agent's or a
# forked skill's forwarded message carries, and the progress kinds the CLI forwards that way; and the Skill tool's
# result when it forked an agent.
NESTED_TOOLS = {'agent': ('Agent', 'SendMessage', 'Task'), 'repl': ('REPL',), 'skill': ('Skill',),
                'cron': ('CronCreate',), 'remote': ('RemoteTrigger',),
                'workflow': ('RunWorkflow', 'Workflow')}
NESTED = {'task_frames': ('system/task_notification', 'system/task_progress', 'system/task_started',
                          'system/task_updated'),
          'workflow': {'system/task_progress': 'workflow_progress', 'system/task_started': 'workflow_name',
                       'task_type': 'local_workflow'},
          'repl': {'tool_progress': 'repl_call'},
          'forwarded': {'field': 'parent_tool_use_id', 'progress': ('agent_progress', 'skill_progress')},
          'fork': {'field': 'tool_use_result', 'status': 'forked'},
          # The calls that start an agent outside the run (remote_agents): any call of these tools, and a CronCreate
          # unless its input leaves `durable` out (false by default) or gives it a value the binary reads as false.
          'remote_agent': {'tools': ('RemoteTrigger',),
                           'durable': {'tool': 'CronCreate', 'field': 'durable', 'off': (False, 'false')}}}
# The built-in tools whose effects stay inside the run's clone and host session (VELDO-0160, the lead's allowlist; the
# binary's, cli-formats.json tool_forms in_run), with their aliases: a call of any other built-in tool asks (outward_tools).
IN_RUN_TOOLS = frozenset(('Agent', 'Bash', 'CronCreate', 'Edit', 'Glob', 'Grep', 'Monitor', 'NotebookEdit', 'REPL', 'Read',
                          'Skill', 'TaskStop', 'TodoWrite', 'ToolSearch', 'WebFetch', 'WebSearch', 'Workflow', 'Write'))
IN_RUN_ALIASES = {'Agent': ('Task',), 'TaskStop': ('KillBash', 'KillShell'), 'Workflow': ('RunWorkflow',)}
IN_RUN = IN_RUN_TOOLS | frozenset(alias for names in IN_RUN_ALIASES.values() for alias in names)
# How an allowlisted call still acts outside the run: the Agent tool with its input's isolation remote, or naming an
# agent definition that is not built in (an agent file may set isolation remote); a file tool or Bash whose input's
# `_host` names another machine (routed there only when the remote-tools gate is on, off in this build); a task whose
# type is not one of the allowlisted tools' (a remote agent is a task of type remote_agent).
IN_RUN_AGENT = {'tools': ('Agent', 'Task'), 'field': 'isolation', 'values': ('worktree', 'remote'), 'outside': 'remote',
                'type_field': 'subagent_type',
                'builtin_types': ('Explore', 'Plan', 'claude', 'claude-code-guide', 'comment-thread-analyst', 'fork',
                                  'general-purpose', 'statusline-setup', 'web-fetch', 'worker', 'workflow-subagent')}
IN_RUN_SKILL = {'tool': 'Skill', 'field': 'context', 'inline': 'inline', 'parent': 'parent_tool_use_id'}
IN_RUN_HOST = {'field': '_host', 'local': ('', 'container', 'this-machine'),
               'tools': ('Bash', 'Edit', 'Glob', 'Grep', 'Read', 'Write')}
IN_RUN_TASKS = {'field': 'task_type',
                'in_run': ('in_process_teammate', 'local_agent', 'local_bash', 'local_workflow', 'monitor_ws')}
TOOL_FIELDS.update({'result/' + sub: {'deferred_tool_use': 'free', 'permission_denials.tool_input': 'free',
                                      'permission_denials.tool_name': 'free', 'permission_denials.tool_use_id': 'free',
                                      'usage.server_tool_use': 'free'}
                    for sub in ('error_during_execution', 'error_max_budget_usd', 'error_max_structured_output_retries',
                                'error_max_turns', 'success')})


def _count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _tokens(usage):
    """A message's tokens: its four counts, a nullable one counted when present; None if unreadable."""
    if not isinstance(usage, dict) or not all(_count(usage.get(f)) for f in TOKEN_FIELDS[:2]):
        return None
    counts = [usage[f] for f in TOKEN_FIELDS if usage.get(f) is not None]
    return sum(counts) if all(_count(c) for c in counts) else None


def _model_tokens(model_usage):
    """The invocation's tokens over every model in `modelUsage`; None if absent or unreadable."""
    if not isinstance(model_usage, dict):
        return None
    total = 0
    for entry in model_usage.values():
        if not isinstance(entry, dict) or not all(_count(entry.get(f)) for f in MODEL_TOKEN_FIELDS):
            return None
        total += sum(entry[f] for f in MODEL_TOKEN_FIELDS)
    return total


def receipt(line):
    return 'sha256:' + hashlib.sha256(line).hexdigest()


def _zone(name):
    try:
        return datetime.timezone.utc if name in ('UTC', 'Etc/UTC', 'GMT') else zoneinfo.ZoneInfo(name)
    except (ValueError, zoneinfo.ZoneInfoNotFoundError):
        return None


def limit_window(text):
    """The window a usage-limit message names, or None when the text is not the usage-limit message."""
    if isinstance(text, str) and text.startswith(LIMIT_REJECTED):
        return LIMIT_WINDOW
    if not isinstance(text, str) or not text.startswith(LIMIT_MESSAGE):
        return None
    name = text[len(LIMIT_MESSAGE):].split(' \u00b7 ', 1)[0]
    return LIMIT_NAMES.get(name, LIMIT_WINDOW)


def limit_reset(text, now):
    """The Unix time a usage-limit message says its window resets, the end of the stated minute in the zone
    it names; None when it states none or it cannot be placed. A time with no date is the next such minute."""
    found = RESETS.search(text or '')
    tz = _zone(found['zone']) if found else None
    if tz is None:
        return None
    hour = int(found['hour']) % 12 + (12 if found['half'] == 'pm' else 0)
    minute = int(found['minute'] or 0)
    try:
        today = datetime.datetime.fromtimestamp(now, tz).date()
        if found['month']:
            dates = [datetime.date(int(found['year'] or today.year), MONTHS.index(found['month']) + 1, int(found['day']))]
        else:
            dates = [today, today + datetime.timedelta(days=1)]
        for date in dates:
            end = max(datetime.datetime(date.year, date.month, date.day, hour, minute, fold=fold, tzinfo=tz).timestamp()
                      for fold in (0, 1)) + 60
            if found['month'] or end > now:
                return end
    except ValueError:
        return None
    return None


def _unreadable(ident=None):
    return {'id': ident, 'server': None, 'tool': None, 'unreadable': True}


def _unknown(form, ident=None):
    return {'id': ident, 'server': None, 'tool': None, 'unknown': form}


def _named(name, ident, redacted):
    """The call a tool name a frame carries shows: an `mcp__<server>__<tool>` name is that MCP call; a name that
    is not a string is unreadable; on a redacted line a name that is neither `mcp__...` nor built in is one the
    redaction may have replaced (unreadable); any other name is no MCP call."""
    if not isinstance(name, str):
        return [_unreadable(ident)]  # A tool call whose tool cannot be read.
    if name.startswith(MCP_PREFIX):
        server, _, tool = name[len(MCP_PREFIX):].partition('__')
        return [{'id': ident, 'server': server, 'tool': tool}]
    if redacted and name not in BUILTIN:
        return [_unreadable(ident)]  # the redaction may have replaced an MCP tool's name
    return []


def _repl_call(value, seen):
    """The call the REPL tool's inner tool call shows (a tool_progress's `repl_call`, which its schema omits):
    an `mcp__` inner name is that MCP call, a built-in one no MCP call, any other an unknown call; a repl_call
    that is not an object naming its inner tool is unreadable."""
    if not isinstance(value, dict) or not isinstance(value.get('inner_tool_name'), str):
        return [_unreadable()]
    name, ident = value['inner_tool_name'], value.get('inner_tool_use_id')
    ident = ident if isinstance(ident, str) else None
    if ident is not None:
        seen.add(ident)
    if name.startswith(MCP_PREFIX):
        return _named(name, ident, False)
    return [] if name in BUILTIN else [_unknown('repl_call:' + name, ident)]


def _task_progress(event, redacted):
    """The calls a task's progress names: its last tool (`last_tool_name`) and each workflow agent's
    (`workflow_progress` entries' `lastToolName`, which the schema omits)."""
    ident = event.get('tool_use_id') if isinstance(event.get('tool_use_id'), str) else None
    found = _named(event['last_tool_name'], ident, redacted) if event.get('last_tool_name') is not None else []
    entries = event.get('workflow_progress')
    if entries is None:
        return found
    if not isinstance(entries, list):
        return found + [_unreadable(ident)]
    for entry in entries:
        if not isinstance(entry, dict):
            found.append(_unreadable(ident))
        elif entry.get('lastToolName') is not None:
            found += _named(entry['lastToolName'], ident, redacted)
    return found


def _attributed(event, seen, redacted):
    """The calls an assistant message names beside its content: the MCP tool that produced it
    (`attribution_mcp_server`, `attribution_mcp_tool`) and the batch tool_use blocks it was decomposed from
    (`batch_tool_uses`, {id, name}); what is there and cannot be read is unreadable."""
    found = []
    server, tool = event.get('attribution_mcp_server'), event.get('attribution_mcp_tool')
    if isinstance(tool, str) and tool.startswith(MCP_PREFIX):
        found += _named(tool, None, redacted)
    elif server is not None or tool is not None:
        if isinstance(server, str) and server and (tool is None or isinstance(tool, str)):
            found.append({'id': None, 'server': server, 'tool': tool})
        else:
            found.append(_unreadable())
    batch = event.get('batch_tool_uses')
    if batch is None:
        return found
    if not isinstance(batch, list):
        return found + [_unreadable()]
    for use in batch:
        ident = use.get('id') if isinstance(use, dict) and isinstance(use.get('id'), str) else None
        if ident is not None:
            seen.add(ident)
        found += _named(use.get('name') if isinstance(use, dict) else None, ident, redacted)
    return found


def _blocks(content, seen, redacted, user):
    """The calls a message's content blocks show (the module docstring, TOOL CALLS)."""
    if user and isinstance(content, str):
        return []
    if not isinstance(content, list):
        return [_unreadable()]  # A message with no readable content may hold a tool call.
    found = []
    for block in content:
        kind = block.get('type') if isinstance(block, dict) else None
        if not isinstance(kind, str):
            found.append(_unreadable())
            continue
        if kind in (TOOL_FREE_REQUEST if user else TOOL_FREE_BLOCKS):
            continue
        if user and kind == 'tool_result':
            ident = block.get('tool_use_id')
            if not isinstance(ident, str):
                found.append(_unreadable())
            elif ident not in seen:
                found.append(_unknown('tool_result', ident))  # the result of a call the record never showed
            continue
        if user or kind != 'tool_use':
            found.append(_unknown(kind, block.get('id') if isinstance(block.get('id'), str) else None))
            continue
        name, ident = block.get('name'), block.get('id')
        if isinstance(ident, str):
            seen.add(ident)
        found += _named(name, ident, redacted)
    return found


def tool_calls(event, seen, redacted=False):
    """[{id, server, tool}]: the MCP tool calls an event of the stream shows (VELDO-0160); a block that may be
    a tool call and cannot be read is {id, server: None, tool: None, unreadable: True}, and a tool-call form
    this reading does not recognize {id, server: None, tool: None, unknown: <form>}. `seen` holds the ids of
    the tool calls shown so far; each tool_use read is added to it."""
    kind = event.get('type')
    tag = (kind, event.get('subtype') if kind in SUBTYPED else None)
    if tag in TOOL_FREE_FRAMES:
        return []
    if tag not in MESSAGES:
        return [_unknown('message:%s' % '/'.join(str(part) for part in tag if part is not None))]
    if kind in ('assistant', 'user'):
        message = event.get('message')
        found = _blocks(message.get('content') if isinstance(message, dict) else None, seen, redacted, kind == 'user')
        return found + _attributed(event, seen, redacted) if kind == 'assistant' else found
    if tag == ('system', 'task_progress'):
        return _task_progress(event, redacted)
    if kind == 'stream_event':
        stream = event.get('event')
        name = stream.get('type') if isinstance(stream, dict) else None
        if not isinstance(name, str):
            return [_unreadable()]
        if name not in STREAM_EVENTS:
            return [_unknown('stream_event:' + name)]
        if name == 'content_block_start':
            blocks = [stream.get('content_block')]
        elif name == 'message_start':
            message = stream.get('message')
            blocks = message.get('content') if isinstance(message, dict) else None
        else:
            return []
        if not isinstance(blocks, list):
            return [_unreadable()]
        found = []
        for block in blocks:
            tag = block.get('type') if isinstance(block, dict) else None
            if not isinstance(tag, str):
                found.append(_unreadable())
            elif tag not in TOOL_FREE_BLOCKS:
                found.append(_unknown('stream_event:' + tag))  # a streamed tool call this reading never reads
        return found
    if kind in ('tool_progress', 'tool_use_summary'):
        ids = [event.get('tool_use_id')] if kind == 'tool_progress' else event.get('preceding_tool_use_ids')
        if not isinstance(ids, list) or not all(isinstance(ident, str) for ident in ids):
            return [_unreadable()]
        found = [_unknown(kind, ident) for ident in ids if ident not in seen]
        if kind == 'tool_progress':
            # The tool the progress is of, and the REPL tool's inner call, which reaches the stream only here.
            found += _named(event.get('tool_name'), ids[0], redacted)
            if 'repl_call' in event:
                found += _repl_call(event['repl_call'], seen)
        return found
    return []


def _named_tools(event, tag):
    """Every tool name an event gives where a tool that ran or may run is named: a `tool_use` block of its content
    (streamed or not), a tool_progress's tool and REPL inner tool, a task's last tool and its workflow agents',
    and an assistant message's batch tool names."""
    names, blocks = [], None
    message = event.get('message')
    if tag in ('assistant', 'user') and isinstance(message, dict):
        blocks = message.get('content')
    elif tag == 'stream_event' and isinstance(event.get('event'), dict):
        stream = event['event']
        start = stream.get('message') if isinstance(stream.get('message'), dict) else {}
        blocks = [stream.get('content_block')] + (start['content'] if isinstance(start.get('content'), list) else [])
    for block in blocks if isinstance(blocks, list) else ():
        if isinstance(block, dict) and block.get('type') == 'tool_use':
            names.append(block.get('name'))
    entries, field = None, None
    if tag == 'tool_progress':
        repl = event.get('repl_call')
        names += [event.get('tool_name'), repl.get('inner_tool_name') if isinstance(repl, dict) else None]
    elif tag == 'system/task_progress':
        names.append(event.get('last_tool_name'))
        entries, field = event.get('workflow_progress'), 'lastToolName'
    elif tag == 'assistant':
        entries, field = event.get('batch_tool_uses'), 'name'
    if isinstance(entries, list):
        names += [entry.get(field) for entry in entries if isinstance(entry, dict)]
    return [name for name in names if isinstance(name, str)]


def nested_work(event):
    """[(construct, form)]: each construct through which the event shows the run doing work its stream may not
    show (NESTED_TOOLS, NESTED): `agent`, `skill`, `repl`, `workflow` for a tool of that class named where a tool
    that ran is named, `task_frames` for a task's own frame, `workflow` also for a task frame of a workflow,
    `repl` also for a REPL inner call, `nested_progress` for a message a sub-agent or a forked skill produced (it
    names its task) or a progress frame of theirs, and `fork` for a forked skill's result."""
    kind = event.get('type')
    tag = '%s/%s' % (kind, event.get('subtype')) if kind == 'system' else kind
    found = []
    for name in _named_tools(event, tag):
        found += [(construct, 'tool:' + name) for construct, names in NESTED_TOOLS.items() if name in names]
    if tag in NESTED['task_frames']:
        found.append(('task_frames', tag))
        workflow = NESTED['workflow']
        if event.get(workflow.get(tag, '')) is not None or event.get('task_type') == workflow['task_type']:
            found.append(('workflow', tag + ':' + workflow.get(tag, 'task_type')))
    if tag in NESTED['repl'] and NESTED['repl'][tag] in event:
        found.append(('repl', tag + ':' + NESTED['repl'][tag]))
    parent = event.get(NESTED['forwarded']['field'])
    if isinstance(parent, str) and parent:
        found.append(('nested_progress', NESTED['forwarded']['field']))
    data = event.get('data')
    if kind == 'progress' and isinstance(data, dict) and data.get('type') in NESTED['forwarded']['progress']:
        found.append(('nested_progress', 'progress:' + data['type']))
    result = event.get(NESTED['fork']['field'])
    if kind == 'user' and isinstance(result, dict) and result.get('status') == NESTED['fork']['status']:
        found.append(('fork', NESTED['fork']['field'] + ':' + NESTED['fork']['status']))
    return list(dict.fromkeys(found))


def remote_agents(event):
    """[(construct, form)]: each call through which the event shows the run starting an agent outside itself
    (NESTED['remote_agent']): `remote` for any RemoteTrigger call, `cron` for a CronCreate that may be durable (its
    own input, where the event gives it, does not leave `durable` out or false), wherever a tool is named."""
    kind = event.get('type')
    tag = '%s/%s' % (kind, event.get('subtype')) if kind == 'system' else kind
    remote = NESTED['remote_agent']
    durable = remote['durable']
    # The inputs the event gives of the calls it names: an assistant message's tool_use blocks and the REPL tool's
    # inner call. Any other place naming the tool gives no input.
    given = []
    message = event.get('message')
    if tag == 'assistant' and isinstance(message, dict) and isinstance(message.get('content'), list):
        given += [(block.get('name'), block.get('input')) for block in message['content']
                  if isinstance(block, dict) and block.get('type') == 'tool_use']
    repl = event.get('repl_call') if tag == 'tool_progress' else None
    if isinstance(repl, dict):
        given.append((repl.get('inner_tool_name'), repl.get('inner_tool_input')))
    names = _named_tools(event, tag)
    found = []
    for name in names:
        if name in remote['tools']:
            found.append(('remote', 'tool:' + name))
        elif name == durable['tool']:
            inputs = [value for tool, value in given if tool == name]
            if inputs:
                # This name's own input: durable unless it leaves the field out or gives a value read as false.
                given.remove((name, inputs[0]))
                value = inputs[0].get(durable['field'], False) if isinstance(inputs[0], dict) else None
                if any(value is off or (isinstance(off, str) and value == off) for off in durable['off']):
                    continue
            found.append(('cron', 'tool:%s:%s' % (name, durable['field'])))
    return list(dict.fromkeys(found))


def tool_inputs(event):
    """[(key, input)]: the input the event gives of each call it names, an assistant or user message's tool_use block
    and the REPL tool's inner call, so that a frame naming the call elsewhere is judged by its input. The key is the
    call's id, and for a sub-agent's message (its task's id in parent_tool_use_id) also ('task', task id, tool name),
    since the task's progress names its last tool without the call's id."""
    kind = event.get('type')
    found = []
    message = event.get('message')
    parent = event.get(TASK_COUNTS['parent'])
    if kind in ('assistant', 'user') and isinstance(message, dict) and isinstance(message.get('content'), list):
        for block in message['content']:
            if not (isinstance(block, dict) and block.get('type') == 'tool_use' and 'input' in block):
                continue
            if isinstance(block.get('id'), str):
                found.append((block['id'], block['input']))
            if isinstance(parent, str) and isinstance(block.get('name'), str):
                found.append((('task', parent, block['name']), block['input']))
    repl = event.get('repl_call') if kind == 'tool_progress' else None
    if isinstance(repl, dict) and isinstance(repl.get('inner_tool_use_id'), str) and 'inner_tool_input' in repl:
        found.append((repl['inner_tool_use_id'], repl['inner_tool_input']))
    # A workflow's task (its start names the workflow, NESTED['workflow']): its progress's last tool is the label of
    # its current agent, not a tool, keyed ('workflow', the id of the call that started it).
    workflow = NESTED['workflow']
    if kind == 'system' and event.get('subtype') == 'task_started' and isinstance(event.get(TASK_COUNTS['task']), str) \
            and (event.get(workflow['system/task_started']) is not None or event.get('task_type') == workflow['task_type']):
        found.append((('workflow', event[TASK_COUNTS['task']]), True))
    return found


def _block_forms(blocks, user):
    """[(name, id, input, given)] of the tool_use blocks, and ('block:<kind>', ...) of every other block that calls a
    tool (not tool-free and not a tool's result: a server tool, an API-side MCP call, any block no table lists)."""
    found = []
    for block in blocks if isinstance(blocks, list) else ():
        kind = block.get('type') if isinstance(block, dict) else None
        if not isinstance(kind, str) or kind in (TOOL_FREE_REQUEST if user else TOOL_FREE_BLOCKS):
            continue  # a block that cannot be read is the call-by-call rules' (unreadable)
        if kind == 'tool_use':
            found.append((block.get('name'), block.get('id'), block.get('input'), 'input' in block))
        elif not kind.endswith('_result'):
            found.append(('block:' + kind, None, None, None))
    return found


def _named_calls(event, tag):
    """Every tool call the event names, as (name, id, input, given): its content's tool_use blocks (their input given,
    a streamed block's not yet), a tool_progress's tool and the REPL tool's inner call, a task's last tool and its
    workflow agents', an assistant message's batch tool names; and each other block that calls a tool as
    ('block:<kind>', None, None, None). A task's last tool is keyed ('task', task id, name), as tool_inputs keys the
    task's own shown calls."""
    found, message = [], event.get('message')
    if tag in ('assistant', 'user') and isinstance(message, dict):
        found += _block_forms(message.get('content'), tag == 'user')
    elif tag == 'stream_event' and isinstance(event.get('event'), dict):
        stream = event['event']
        start = stream.get('message') if isinstance(stream.get('message'), dict) else {}
        blocks = [stream.get('content_block')] + (start['content'] if isinstance(start.get('content'), list) else [])
        found += [(name, ident, None, False) for name, ident, _, _ in _block_forms(blocks, False)]
    if tag == 'tool_progress':
        found.append((event.get('tool_name'), event.get('tool_use_id'), None, False))
        repl = event.get('repl_call')
        if isinstance(repl, dict):
            found.append((repl.get('inner_tool_name'), repl.get('inner_tool_use_id'), repl.get('inner_tool_input'),
                          'inner_tool_input' in repl))
    elif tag == 'system/task_progress':
        if event.get('last_tool_name') is not None:
            task = event.get(TASK_COUNTS['task'])
            name = event['last_tool_name']
            found.append((name, ('task', task, name) if isinstance(task, str) and isinstance(name, str) else None,
                          None, False))
        entries = event.get('workflow_progress')
        found += [(entry['lastToolName'], None, None, False) for entry in entries if isinstance(entry, dict)
                  and entry.get('lastToolName') is not None] if isinstance(entries, list) else []
    elif tag == 'assistant' and isinstance(event.get('batch_tool_uses'), list):
        found += [(use.get('name'), use.get('id'), None, False) for use in event['batch_tool_uses'] if isinstance(use, dict)]
    return found


def _outside_input(name, value):
    """The forms through which an allowlisted call's own input acts outside the run: the Agent tool remote or naming
    an agent definition that is not built in, a file tool or Bash naming another machine."""
    # Skill's schema has only skill and args. A definition can supply context independently, so the parent check
    # below is unconditional. An explicit context in a record must exclude a fork; unreadable input cannot do so.
    if name == IN_RUN_SKILL['tool'] and (not isinstance(value, dict)
                                       or value.get(IN_RUN_SKILL['field'], IN_RUN_SKILL['inline']) != IN_RUN_SKILL['inline']):
        return ['tool:Skill:context']
    if not isinstance(value, dict):
        return ['tool:%s:input' % name] if name in IN_RUN_AGENT['tools'] else []
    found = []
    if name in IN_RUN_AGENT['tools']:
        isolation, kind = value.get(IN_RUN_AGENT['field']), value.get(IN_RUN_AGENT['type_field'])
        local = tuple(v for v in IN_RUN_AGENT['values'] if v != IN_RUN_AGENT['outside'])
        if isolation is not None and isolation not in local:
            found.append('tool:%s:%s:%s' % (name, IN_RUN_AGENT['field'], isolation))
        if kind is not None and kind not in IN_RUN_AGENT['builtin_types']:
            found.append('tool:%s:%s' % (name, IN_RUN_AGENT['type_field']))
    host = value.get(IN_RUN_HOST['field'])
    if name in IN_RUN_HOST['tools'] and isinstance(host, str) and host.strip() not in IN_RUN_HOST['local']:
        found.append('tool:%s:%s' % (name, IN_RUN_HOST['field']))
    return found


def outward_tools(event, inputs):
    """[form]: each call the event names that is not shown to stay inside the run (VELDO-0160, the lead's allowlist,
    rule A): a built-in tool that is not on the allowlist (IN_RUN; `tool:<name>`, a name that cannot be read
    `tool:unreadable`), any other block that calls a tool (`block:<kind>`), an allowlisted call whose input acts outside
    the run (_outside_input), an Agent call whose input is neither given here nor by its id elsewhere in the record
    (`inputs`, {key: [input]}, tool_inputs; it may be remote: an agent a sub-agent starts shows its input only in the
    sub-agent's forwarded message, and one a deeper agent starts nowhere), a task whose type is not one of the allowlisted tools', and a workflow
    agent whose isolation is remote. An MCP tool (`mcp__...`) is the configuration's to judge."""
    kind = event.get('type')
    tag = '%s/%s' % (kind, event.get('subtype')) if kind == 'system' else kind
    found = []
    workflow = tag == 'system/task_progress' and (event.get(NESTED['workflow'][tag]) is not None
                                                  or ('workflow', event.get(TASK_COUNTS['task'])) in inputs)
    for name, ident, value, given in _named_calls(event, tag):
        if workflow and isinstance(ident, tuple) and ident[0] == 'task':
            continue  # a workflow task's last tool is its current agent's label; its agents' tools are named beside it
        if not isinstance(name, str):
            found.append('tool:unreadable')
            continue
        if name.startswith('block:'):
            found.append(name)
            continue
        if name.startswith(MCP_PREFIX):
            continue
        if name not in IN_RUN:
            found.append('tool:' + name)
            continue
        # A skill definition can fork without saying so in its call. In a sub-agent the fork's messages are
        # dropped and its end has no tally, so the parent alone is enough to ask under rule A.
        if name == IN_RUN_SKILL['tool'] and event.get(IN_RUN_SKILL['parent']) is not None:
            found.append('tool:Skill:parent_tool_use_id')
        values = [value] if given else list(inputs.get(ident, ())) if isinstance(ident, (str, tuple)) else []
        if not values and name in IN_RUN_AGENT['tools']:
            found.append('tool:%s:input_not_given' % name)
        if not values and name == IN_RUN_SKILL['tool']:
            values = [None]
        for each in values:
            found += _outside_input(name, each)
    if tag in NESTED['task_frames'] and IN_RUN_TASKS['field'] in event:
        task_type = event[IN_RUN_TASKS['field']]
        if task_type not in IN_RUN_TASKS['in_run']:
            found.append('%s:%s' % (IN_RUN_TASKS['field'], task_type if isinstance(task_type, str) else 'unreadable'))
    entries = event.get('workflow_progress') if tag == 'system/task_progress' else None
    for entry in entries if isinstance(entries, list) else ():
        if isinstance(entry, dict) and entry.get(IN_RUN_AGENT['field']) == IN_RUN_AGENT['outside']:
            found.append('workflow_progress:%s:%s' % (IN_RUN_AGENT['field'], IN_RUN_AGENT['outside']))
    return list(dict.fromkeys(found))


def _whole(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


class Tasks:
    """The calls each task of a record reported against the calls the record showed for it (A SUB-AGENT'S CALLS
    ARE COUNTED BY ITS TASK, in the module docstring). `line(event, sequence)` reads one event and returns what
    it cannot read ({id, server: None, tool: None, unreadable: True}); `close()` returns each task's shortfall,
    {id, sequence, server: None, tool: None, unknown: 'task_tool_uses', task, unshown}."""

    def __init__(self):
        self.reported = {}  # task id -> (the highest count, the sequence of the line that first reported it)
        self.shown = {}  # task id -> the ids of the tool_use blocks shown under it

    def line(self, event, sequence):
        kind = event.get('type')
        if kind == 'assistant':
            parent = event.get(TASK_COUNTS['parent'])
            message = event.get('message')
            content = message.get('content') if isinstance(message, dict) else None
            if isinstance(parent, str) and isinstance(content, list):
                shown = self.shown.setdefault(parent, set())
                shown.update(block['id'] for block in content if isinstance(block, dict)
                             and block.get('type') == 'tool_use' and isinstance(block.get('id'), str))
            return []
        tag = '%s/%s' % (kind, event.get('subtype')) if kind == 'system' else None
        if tag not in TASK_COUNTS['frames']:
            return []
        holder, _, field = TASK_COUNTS['count'].partition('.')
        usage = event.get(holder)
        if tag == 'system/task_notification' and usage is None:
            return []  # a task's end with no usage reports no count
        task, count = event.get(TASK_COUNTS['task']), usage.get(field) if isinstance(usage, dict) else None
        if not isinstance(task, str) or not _whole(count):
            return [_unreadable(task if isinstance(task, str) else None)]
        highest = self.reported.get(task)
        if highest is not None and count < highest[0]:
            return [_unreadable(task)]  # a count only rises: a lower one is not the count this reading knows
        if highest is None or count > highest[0]:
            self.reported[task] = (count, sequence)
        return []

    def close(self):
        found = []
        for task, (count, sequence) in self.reported.items():
            unshown = count - len(self.shown.get(task, ()))
            if unshown > 0:
                found.append({'id': task, 'sequence': sequence, 'server': None, 'tool': None,
                              'unknown': 'task_tool_uses', 'task': task, 'unshown': unshown})
        return sorted(found, key=lambda call: call['sequence'])


class Meter:
    """Reads one invocation's stream line by line. `feed(bytes)` returns the observations the
    complete lines in it make: {'kind': 'usage', 'usage': cumulative {tokens, messages}} or
    {'kind': 'window', 'window_id', 'status', 'reset_at', 'utilization'}, each with its `line` and
    `receipt`. `final()` is the conclusive total, without tokens when the result had no readable
    modelUsage and empty when the CLI reported no result. `clock` and `zone` are the engine's clock
    and local time zone, for a CLI that states times in local time (this one does not)."""

    def __init__(self, clock=time.time, zone=None, resumes=None, prior=None):
        self.pending = b''
        self.messages = {}
        self.result = None
        self.resumes = resumes if isinstance(resumes, str) and resumes else None
        self.prior = prior if _count(prior) else None
        self.session_id = None
        self.session_total = None
        self.clock = clock
        self.limited = None

    def charged(self):
        """Which case charges this invocation: `whole` when its contract resumes no session, `difference`
        when the CLI reports the session the contract resumes, `whole_other_session` when it reports
        another one (or none)."""
        if self.resumes is None:
            return 'whole'
        return 'difference' if self.session_id == self.resumes else 'whole_other_session'

    def _own(self, total):
        """This invocation's share of a result's running total: all of it in a new session, or when the CLI
        reports another session than the one resumed; in the resumed session the total less its settled
        total, unknown when that is unknown or the total is below it (the running total cannot then be
        placed)."""
        if total is None or self.charged() != 'difference':
            return total
        if self.prior is None or total < self.prior:
            return None
        return total - self.prior

    def session(self):
        """{provider, id, tokens, charged}: the CLI session this invocation ran, its running token total at
        the end (None without a result carrying modelUsage) and which case charged it (`charged()`); None
        when the CLI named no session."""
        if self.session_id is None:
            return None
        return {'provider': PROVIDER, 'id': self.session_id, 'tokens': self.session_total,
                'charged': self.charged()}

    def limit(self):
        """{window, reset_at, signal}: the last limit the stream stated (VELDO-0160), or None."""
        return dict(self.limited) if self.limited else None

    def _result_limit(self, event, seen):
        """The rate-limit result as its window, exhausted: a result with `is_error` whose text is the
        usage-limit message, with the reset it states (or none)."""
        text = event.get('result')
        window = limit_window(text) if event.get('is_error') is True else None
        if window is None:
            return []
        reset = limit_reset(text, self.clock())
        self.limited = {'window': window, 'reset_at': reset, 'signal': 'result'}
        return [dict(seen, kind='window', window_id=window, status='rejected', reset_at=reset, utilization=None)]

    def feed(self, chunk):
        self.pending += chunk
        found = []
        while b'\n' in self.pending:
            line, _, self.pending = self.pending.partition(b'\n')
            found.extend(self.line(line))
        return found

    def close(self):
        """The last line when the stream ended without a newline."""
        line, self.pending = self.pending, b''
        return self.line(line) if line.strip() else []

    def cumulative(self):
        tokens = sum(self.messages.values())
        messages = len(self.messages)
        if self.result is not None:
            messages = max(messages, self.result['messages'])
            if self.result['tokens'] is not None:
                tokens = max(tokens, self.result['tokens'])
        return {'tokens': tokens, 'messages': messages}

    def final(self):
        if self.result is None:
            return {}
        total = self.cumulative()
        if self.result['tokens'] is None:
            del total['tokens']  # No modelUsage: the tokens stay unknown.
        return total

    def line(self, line):
        try:
            event = json.loads(line)
        except ValueError:
            return []
        if not isinstance(event, dict):
            return []
        kind = event.get('type')
        seen = {'line': line, 'receipt': receipt(line)}
        if isinstance(event.get('session_id'), str) and event['session_id']:
            self.session_id = event['session_id']
        if kind == 'assistant':
            message = event.get('message')
            message = message if isinstance(message, dict) else {}
            tokens = _tokens(message.get('usage'))
            ident = message.get('id')
            if tokens is None or not isinstance(ident, str) or not ident:
                return []
            if self.messages.get(ident, -1) >= tokens:
                return []  # The same message again: nothing new to count.
            self.messages[ident] = tokens
            return [dict(seen, kind='usage', usage=self.cumulative())]
        if kind == 'result':
            found = self._result_limit(event, seen)
            turns = event.get('num_turns')
            if not _count(turns):
                return found
            running = _model_tokens(event.get('modelUsage'))
            if running is not None:
                self.session_total = running if self.session_total is None else max(self.session_total, running)
            total = {'tokens': self._own(running), 'messages': turns}
            prior = self.result
            if prior is not None:
                # Cumulative: the latest result's totals, never below what an earlier one reported.
                total = {'messages': max(turns, prior['messages']),
                         'tokens': None if total['tokens'] is None and prior['tokens'] is None
                         else max(t for t in (total['tokens'], prior['tokens']) if t is not None)}
                if total == prior:
                    return found  # The same total again settles nothing twice.
            self.result = total
            return found + [dict(seen, kind='usage', usage=self.cumulative())]
        if kind == 'rate_limit_event':
            info = event.get('rate_limit_info')
            info = info if isinstance(info, dict) else {}
            status = info.get('status')
            if not isinstance(status, str):
                return []
            reset = info.get('resetsAt')
            utilization = info.get('utilization')
            if status == 'rejected':
                # VELDO-0160: the stream reports its window exhausted.
                self.limited = {'window': str(info.get('rateLimitType') or LIMIT_WINDOW),
                                'reset_at': reset if _number(reset) else None, 'signal': 'stream'}
            elif (self.limited or {}).get('signal') == 'stream' and self.limited['window'] == str(
                    info.get('rateLimitType') or LIMIT_WINDOW):
                self.limited = None  # The same window reported open again: the run is no longer at its limit.
            return [dict(seen, kind='window', window_id=str(info.get('rateLimitType') or 'unified'),
                         status='rejected' if status == 'rejected' else 'allowed',
                         reset_at=reset if _number(reset) else None,
                         utilization=utilization if _number(utilization) and utilization >= 0 else None)]
        return []


# VELDO-0060: the pinned executable, its command line and the terminal record.

QUALIFICATION = 'runtime/claude-qualification.json'
QUALIFICATION_SCHEMA = 'veldo.engine_qualification/v1'
ARTIFACT_SCHEMA = 'veldo.engine_artifact/v1'
# The adapter registration (control_launch.ENGINE_PROTOCOL): its lifecycle operations, each with what
# performs it for this engine, in the order the receiver drives them; the suite enumerates them here.
REGISTRATION = {
    'engine': PROVIDER,
    'lifecycle': {
        'accept': 'control_launch.Receiver.launch: the executable bound (bind) and the acceptance recorded before the spawn',
        'launch': 'control_launch.Receiver._spawn: the pinned command (command) in the dispatch\'s wrapper',
        'observe': 'Meter.feed and Terminal.feed over the stream JSON the engine prints',
        'stop': 'control_launch.Launch.stop: the runner\'s stop request to the receiver',
        'exit': 'control_launch.Receiver._reap: the reaped exit recorded on the dispatch',
        'artifacts': 'Terminal.document: the decoded terminal record and its verdict, the exit record\'s artifact',
    },
}
VERSION_TEXT = re.compile(r'[0-9]+(?:\.[0-9]+){1,3}')
STOPS = ('requested', 'usage_cap', 'heartbeat_missing', 'paid_api')


class Refused(Exception):
    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail
        super().__init__(code + (': ' + detail if detail else ''))


def _file_digest(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return 'sha256:' + digest.hexdigest()


def qualification(path=None):
    """The installed qualification record, beside this module; refused by name when unreadable."""
    path = Path(path) if path is not None else Path(__file__).resolve().parent / QUALIFICATION
    try:
        record = json.loads(path.read_text())
    except (OSError, ValueError):
        raise Refused('missing_evidence:engine_qualification', str(path))
    if (not isinstance(record, dict) or record.get('schema') != QUALIFICATION_SCHEMA
            or record.get('engine') != PROVIDER or not isinstance(record.get('versions'), dict)):
        raise Refused('invalid_input:engine_qualification', str(path))
    return record


def qualified(version, record=None):
    """The qualified entry of `version`: refused by name when the record does not list it."""
    record = qualification() if record is None else record
    entry = record['versions'].get(version) if isinstance(version, str) and VERSION_TEXT.fullmatch(version) else None
    if (not isinstance(entry, dict) or not isinstance(entry.get('sha256'), str)
            or not isinstance(entry.get('flags'), list)):
        raise Refused('invalid_input:engine_version:%s' % version, 'no qualified Claude Code version')
    return entry


def pinned_path(state_root, version):
    return Path(state_root) / 'engines' / PROVIDER / version


def pin(version, *, versions, state_root, record=None):
    """Copy the installer's versioned executable `versions/<version>` under the factory state root and
    return its binding. The copy is a new regular file (written beside, then renamed into place) whose
    digest must be the qualified one; a source that is a link, or that the record does not qualify, is
    refused and nothing is left in place."""
    entry = qualified(version, record)
    source = Path(versions) / version
    try:
        info = os.lstat(source)
    except OSError:
        raise Refused('missing_evidence:engine_source', str(source))
    if not stat.S_ISREG(info.st_mode):
        raise Refused('binding_mismatch:engine_source', 'the versioned executable is not a regular file')
    target = pinned_path(state_root, version)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    partial = target.parent / ('.%s.%s.partial' % (version, os.urandom(6).hex()))
    try:
        with open(source, 'rb') as reading, open(partial, 'xb') as writing:
            shutil.copyfileobj(reading, writing, 1 << 20)
        os.chmod(partial, 0o555)
        if _file_digest(partial) != entry['sha256']:
            raise Refused('binding_mismatch:engine_digest', 'the versioned executable is not the qualified one')
        os.replace(partial, target)
    finally:
        if partial.exists():
            partial.unlink()
    return bind({'executable': {'version': version}}, state_root, record)


def bind(adapter, state_root, record=None):
    """{engine, version, path, sha256, flags}: the executable a launch of `adapter` runs, checked before
    anything is accepted or spawned (control_launch.ENGINE_PROTOCOL). The adapter names a qualified
    version (`executable: {version}`); its pinned copy under the state root must be a regular file (not
    a link) whose digest is the qualified one."""
    executable = adapter.get('executable') if isinstance(adapter, dict) else None
    version = executable.get('version') if isinstance(executable, dict) else None
    entry = qualified(version, record)
    if not isinstance(state_root, str) or not os.path.isabs(state_root):
        raise Refused('missing_authority:engine_state_root', 'the receiver names no factory state root')
    path = pinned_path(state_root, version)
    try:
        info = os.lstat(path)
    except OSError:
        raise Refused('missing_evidence:engine_executable', str(path))
    if not stat.S_ISREG(info.st_mode):
        raise Refused('binding_mismatch:engine_executable', 'the pinned executable is not a regular file')
    if os.path.realpath(path.parent) != os.path.normpath(str(path.parent)):
        raise Refused('binding_mismatch:engine_path', 'a directory on the way to the pinned executable is a link')
    if info.st_uid != os.geteuid():
        raise Refused('binding_mismatch:engine_owner', 'the pinned executable is not this account\'s own copy')
    if info.st_mode & 0o7222:
        raise Refused('binding_mismatch:engine_mode', 'the pinned executable is writable or carries a special bit')
    if _file_digest(path) != entry['sha256']:
        raise Refused('binding_mismatch:engine_digest', 'the pinned executable is not the qualified one')
    # VELDO-0155: the version is qualified with the everything-off baseline, or nothing is accepted.
    base = qualified_baseline({'version': version}, record)
    # VELDO-0155 AC3: and with stream JSON input, so the prompt waits for the login check (Guard).
    if not input_protocol(entry['flags']):
        raise Refused('missing_evidence:engine_input_protocol:%s' % version,
                      'the version is not qualified with stream JSON input')
    return {'engine': PROVIDER, 'version': version, 'path': str(path), 'sha256': entry['sha256'],
            'flags': list(entry['flags']), 'baseline': base}


def command(bound, adapter):
    """The engine's argv: the adapter's configured prefix (its clone entrance, or a transport's trusted
    wrapper), then the pinned path and its version's qualified flags."""
    return list(adapter.get('argv') or []) + [bound['path']] + list(bound['flags'])


def environment(bound, record=None):
    """What the engine's environment always carries for its version (DISABLE_AUTOUPDATER)."""
    return dict(qualified(bound['version'], record).get('environment') or {})


# VELDO-0155: the everything-off baseline, the paid-API guard. Every name is the 2.1.281 binary's own
# (proof/VELDO-0155/claude-baseline.json, read from its bytes): `--setting-sources` with an empty list
# (its KIr("") is no source, so only the `--settings` file and managed policy load; the binary spawns
# itself with `--setting-sources=` for the same), `--strict-mcp-config` with the run's `--mcp-config`
# file, `--disable-slash-commands` (no skill is listed until VELDO-0127), CLAUDE_CODE_DISABLE_CLAUDE_MDS
# and CLAUDE_CODE_DISABLE_AUTO_MEMORY, and `disableAllHooks` in the generated settings. Neither bare
# mode (it refuses subscription logins) nor safe mode (it ignores the `--mcp-config` servers) is used.
BASELINE = {
    'options': ['--setting-sources', '', '--strict-mcp-config', '--disable-slash-commands'],
    'settings_option': '--settings',
    'mcp_option': '--mcp-config',
    'environment': {'CLAUDE_CODE_DISABLE_CLAUDE_MDS': '1', 'CLAUDE_CODE_DISABLE_AUTO_MEMORY': '1'},
    'settings': {'disableAllHooks': True},
    'mcp_config': {'mcpServers': {}},
}
SETTINGS_FILE, MCP_FILE = 'settings.json', 'mcp.json'
# The init event's apiKeySource of a run on no API key (the binary's M_ source "none"): a claude.ai
# subscription login and a subscription token (CLAUDE_CODE_OAUTH_TOKEN) alike report it.
SUBSCRIPTION_SOURCE = 'none'
# The input protocol (proof/VELDO-0155/claude-baseline.json, input_protocol, read from the 2.1.281 bytes):
# stream JSON input among the qualified flags (the binary requires stream JSON output and print mode with
# it); the initialize control request the receiver writes first; in its answer's `account` (the binary's
# Kfe()), the backend of a subscription login and the one token source the receiver itself configures.
INPUT_FLAGS = ('--input-format', 'stream-json')
INITIALIZE = {'subtype': 'initialize'}
SUBSCRIPTION_PROVIDER = 'firstParty'
# The subscriptionType labels of a claude.ai subscription (the binary's wBn(), proof/VELDO-0155/claude-baseline.json,
# subscriptions): Enterprise, Team, Max and Pro. Its default label for any other tier, "Claude API", is not one.
SUBSCRIPTIONS = ('Claude Enterprise', 'Claude Team', 'Claude Max', 'Claude Pro')
TOKEN_SOURCE = 'CLAUDE_CODE_OAUTH_TOKEN'
# The Anthropic profile store the binary reads when ANTHROPIC_CONFIG_DIR is unset (it is stripped):
# XDG_CONFIG_HOME/anthropic, else HOME/.config/anthropic; the active profile named by its active_config
# file, else `default`; a profile of either type below logs a run in ahead of the claude.ai login.
PROFILE_TYPES = ('user_oauth', 'oidc_federation')


def input_protocol(flags):
    """Whether qualified flags carry stream JSON input (INPUT_FLAGS, the option and its value together)."""
    flags = list(flags or [])
    return any(tuple(flags[at:at + 2]) == INPUT_FLAGS for at in range(len(flags) - 1))


def qualified_baseline(bound, record=None):
    """The baseline the version's qualification record lists, which must be this module's BASELINE: a
    version not qualified with it is refused by name before anything is accepted or spawned."""
    entry = qualified(bound['version'], record)
    if entry.get('baseline') != BASELINE:
        raise Refused('missing_evidence:engine_baseline:%s' % bound['version'],
                      'the version is not qualified with the everything-off baseline')
    return BASELINE


def baseline(bound, run, environment=None, record=None):
    """{argv, environment, files}: what the run adds after its qualified flags. `run` names the run's own
    `config` directory, where `files` ({name: bytes}) are written before the spawn and which the
    generated `--settings` and `--mcp-config` options name."""
    base = bound.get('baseline') if record is None else qualified_baseline(bound, record)
    if base != BASELINE:
        raise Refused('missing_evidence:engine_baseline:%s' % bound.get('version'))
    config = Path(run['config'])
    files = {SETTINGS_FILE: (json.dumps(base['settings'], sort_keys=True) + '\n').encode(),
             MCP_FILE: (json.dumps(base['mcp_config'], sort_keys=True) + '\n').encode()}
    argv = (list(base['options'][:2]) + [base['settings_option'], str(config / SETTINGS_FILE),
                                         base['mcp_option'], str(config / MCP_FILE)] + list(base['options'][2:]))
    return {'argv': argv, 'environment': dict(base['environment']), 'files': files}


class Unresolved(Exception):
    """A relative path whose engine working directory is unknown."""


def _resolved(path, cwd):
    """`path` as the engine opens it: a relative one against the engine's working directory (the binary
    joins it and reads it relative to its own), which must then be known."""
    path = Path(path)
    if path.is_absolute():
        return path
    if cwd is None:
        raise Unresolved(str(path))
    return Path(cwd) / path


def _profile_store(environment, cwd=None):
    """The Anthropic profile directory the engine would read, as the binary resolves it, or None."""
    given = (environment.get('XDG_CONFIG_HOME') or '').strip()
    if given:
        return _resolved(given, cwd) / 'anthropic'
    home = (environment.get('HOME') or '').strip()
    return _resolved(home, cwd) / '.config' / 'anthropic' if home else None


def profile_problem(bound, environment, cwd=None):
    """THE ENGINE PROTOCOL's check of the account profile before acceptance: on 2.1.281 nothing of the
    profile's reaches a run past the baseline (the setting sources are off, and each item is gated by its
    source or its own switch, proof/VELDO-0155/README.md), so there is nothing to refuse."""
    return None


def login_problem(bound, environment, cwd=None):
    """VELDO-0155 AC3, before anything is accepted: a login the engine would take ahead of the account's
    claude.ai subscription and report as apiKeySource `none`, so the init event cannot show it: an
    Anthropic profile (user_oauth or oidc_federation) in the profile store the engine environment
    reaches. Only the profile's configuration is read, never its credentials file (whose size alone
    says whether a user_oauth profile is usable). `cwd` is the engine's working directory (THE ENGINE
    PROTOCOL): a relative XDG_CONFIG_HOME, HOME or credentials_path is the binary's relative to it, and
    one whose working directory is unknown (None) is refused by name. None, or the named refusal."""
    try:
        return _profile_login(environment, cwd)
    except Unresolved:
        return 'paid_api:anthropic_profile:unresolved'


def _profile_login(environment, cwd):
    store = _profile_store(environment, cwd)
    if store is None or not store.is_dir():
        return None
    try:
        active = (store / 'active_config').read_text().strip()
    except OSError:
        active = ''
    active = active or 'default'
    try:
        profile = json.loads((store / 'configs' / (active + '.json')).read_text())
    except (OSError, ValueError):
        return None
    authentication = profile.get('authentication') if isinstance(profile, dict) else None
    kind = authentication.get('type') if isinstance(authentication, dict) else None
    if kind not in PROFILE_TYPES:
        return None
    if kind == 'user_oauth':
        given = authentication.get('credentials_path')
        if given is not None and (not isinstance(given, str) or not given):
            return None  # The binary reads no file there, so the profile is not usable.
        credentials = store / 'credentials' / (active + '.json') if given is None else _resolved(given, cwd)
        try:
            if os.stat(credentials).st_size == 0:
                return None
        except OSError:
            return None
    return 'paid_api:anthropic_profile:' + kind


class Guard:
    """VELDO-0155 AC3: the handshake that holds the prompt back, and the stream stop. The run is launched
    with stream JSON input (INPUT_FLAGS, among its qualified flags), so nothing reaches the model until the
    receiver writes the prompt. `opening(prompt)` is what the receiver writes first: the initialize control
    request, the engine's input left open and the prompt held. The binary answers it with a control
    response whose `account` is its Kfe(): the backend (apiProvider), apiKeySource only when an API key is
    in use (the source the init event reports), tokenSource for a token login that is not a claude.ai
    subscription (CLAUDE_CODE_OAUTH_TOKEN among them), subscriptionType for a claude.ai subscription, and
    neither for an Anthropic profile. `feed(bytes)` reads the stream: that answer confirms the login only
    when it is a success on the first-party backend, with no API key, and a claude.ai subscription or the
    token the receiver configures (TOKEN_SOURCE); a subscriptionType other than the binary's Enterprise, Team,
    Max and Pro labels (SUBSCRIPTIONS; its default "Claude API" among them) and anything else stops the run by name
    (`paid_api:<field>:<value>`), returned once, and the prompt is never written. `release()` returns the
    prompt, as the user message of stream JSON input, once and only after that confirmation with no stop.
    Every init event the stream carries is read as well: one whose apiKeySource is not `none` stops the
    run by name. `source` is the login the engine reported (`none` for a subscription), `stop` the named
    stop, else None."""

    def __init__(self):
        self.pending = b''
        self.source = None
        self.stop = None
        self.request_id = 'veldo-initialize-' + os.urandom(8).hex()
        self.prompt = None
        self.confirmed = False
        self.released = False

    def opening(self, prompt):
        """(bytes, close): the initialize control request, written at once with the engine's input left open;
        the prompt is held until the answer confirms a subscription login."""
        self.prompt = bytes(prompt)
        request = {'type': 'control_request', 'request_id': self.request_id, 'request': dict(INITIALIZE)}
        return (json.dumps(request) + '\n').encode(), False

    def release(self):
        """The prompt as the user message of stream JSON input, once, after a confirmed subscription login and
        with no stop; None otherwise (and ever after)."""
        if not self.confirmed or self.stop is not None or self.prompt is None or self.released:
            return None
        self.released = True
        message = {'type': 'user', 'message': {'role': 'user', 'content': self.prompt.decode('utf-8', 'replace')},
                   'parent_tool_use_id': None}
        return (json.dumps(message) + '\n').encode()

    def feed(self, chunk):
        self.pending += chunk
        found = None
        while b'\n' in self.pending:
            line, _, self.pending = self.pending.partition(b'\n')
            found = self._line(line) or found
        return found

    def _stopped(self, field, value):
        self.source = value if isinstance(value, str) else repr(value)
        if self.stop is None:
            self.stop = 'paid_api:%s:%s' % (field, self.source)
            return self.stop
        return None

    def _answer(self, answer):
        """The initialize answer: None when it confirms a subscription login, else the named stop."""
        if answer.get('subtype') != 'success':
            return self._stopped('initialize', answer.get('subtype'))
        response = answer.get('response')
        account = response.get('account') if isinstance(response, dict) else None
        if not isinstance(account, dict):
            return self._stopped('initialize', 'no_account')
        if account.get('apiProvider') != SUBSCRIPTION_PROVIDER:
            return self._stopped('apiProvider', account.get('apiProvider'))
        key = account.get('apiKeySource')
        if key is not None and key != SUBSCRIPTION_SOURCE:
            return self._stopped('apiKeySource', key)
        token = account.get('tokenSource')
        if token is not None and token != TOKEN_SOURCE:
            return self._stopped('tokenSource', token)
        subscription = account.get('subscriptionType')
        if token is None and subscription not in SUBSCRIPTIONS:
            return self._stopped('subscriptionType', subscription)
        if self.stop is None:
            self.source, self.confirmed = SUBSCRIPTION_SOURCE, True
        return None

    def _line(self, line):
        try:
            event = json.loads(line)
        except ValueError:
            return None
        if not isinstance(event, dict):
            return None
        if event.get('type') == 'control_response':
            answer = event.get('response')
            if isinstance(answer, dict) and answer.get('request_id') == self.request_id and not self.confirmed:
                return self._answer(answer)
            return None
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            source = event.get('apiKeySource')
            if source != SUBSCRIPTION_SOURCE:
                return self._stopped('apiKeySource', source)
            if self.source is None:
                self.source = SUBSCRIPTION_SOURCE
        return None


def _text(value):
    return isinstance(value, str)


def _terminal(event):
    """The decoded `result` event, or None when it is not one the CLI's schema declares."""
    subtype, turns = event.get('subtype'), event.get('num_turns')
    errors = event.get('errors')
    if (not _text(subtype) or not isinstance(event.get('is_error'), bool) or not _count(turns)
            or not _text(event.get('session_id')) or not (event.get('stop_reason') is None or _text(event['stop_reason']))):
        return None
    if subtype == 'success':
        if not _text(event.get('result')):
            return None
        text, errors = event['result'], []
    elif subtype.startswith('error_') and isinstance(errors, list) and all(_text(e) for e in errors):
        text = None
    else:
        return None
    # Its usage is modelUsage's total over every model, the invocation's; without a readable modelUsage the
    # tokens are unknown (None), never the result's `usage`, which is the main agent loop's alone.
    return {'subtype': subtype, 'is_error': event['is_error'], 'num_turns': turns, 'session_id': event['session_id'],
            'stop_reason': event.get('stop_reason'), 'errors': list(errors),
            'tokens': _model_tokens(event.get('modelUsage')),
            'result_digest': None if text is None else 'sha256:' + hashlib.sha256(text.encode()).hexdigest()}


class Terminal:
    """What one invocation's stdout returns: `feed(bytes)` line by line, `close()` for the last line, then
    `document(termination, cause)`. A line that is not a JSON object with a string `type`, or a `result`
    the schema does not declare, is malformed; the latest well-formed result is the terminal record."""

    def __init__(self):
        self.pending = b''
        self.lines = 0
        self.malformed = 0
        self.result = None
        self.receipt = None

    def feed(self, chunk):
        self.pending += chunk
        while b'\n' in self.pending:
            line, _, self.pending = self.pending.partition(b'\n')
            self._line(line)

    def close(self):
        line, self.pending = self.pending, b''
        self._line(line)

    def _line(self, line):
        if not line.strip():
            return
        self.lines += 1
        try:
            event = json.loads(line)
        except ValueError:
            event = None
        if not isinstance(event, dict) or not _text(event.get('type')):
            self.malformed += 1
            return
        if event['type'] == 'result':
            decoded = _terminal(event)
            if decoded is None:
                self.malformed += 1
                return
            self.result, self.receipt = decoded, receipt(line)

    def problems(self, termination, cause):
        """Every reason the output is not a completion, the first the verdict; [] when it is one."""
        if termination is None:
            return ['not_executed']
        found = []
        if cause in STOPS:
            found.append('stopped')
        if termination.get('deadline_stop'):
            found.append('timeout')
        if termination.get('signal') is not None:
            found.append('signal')
        elif termination.get('returncode') != 0:
            found.append('nonzero_exit')
        if self.malformed:
            found.append('malformed_output')
        if self.result is None:
            found.append('missing_result')
        elif self.result['subtype'] != 'success' or self.result['is_error']:
            found.append('engine_error')
        return found

    def document(self, termination, cause):
        """The artifact of the invocation (control_launch.ENGINE_PROTOCOL's shape: schema, engine, verdict,
        complete): its verdict, every problem, the terminal record and the stream."""
        problems = self.problems(termination, cause)
        return {'schema': ARTIFACT_SCHEMA, 'engine': PROVIDER, 'verdict': problems[0] if problems else 'complete',
                'complete': not problems, 'problems': problems, 'terminal': self.result, 'terminal_receipt': self.receipt,
                'stream': {'lines': self.lines, 'malformed': self.malformed,
                           'output_digest': (termination or {}).get('output_digest'),
                           'output_bytes': (termination or {}).get('output_bytes')},
                'exit': {'returncode': (termination or {}).get('returncode'), 'signal': (termination or {}).get('signal'),
                         'deadline_stop': (termination or {}).get('deadline_stop'), 'cause': cause}}
