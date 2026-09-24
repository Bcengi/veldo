#!/usr/bin/env python3
"""Require the teeth review's named assertions to fail on temporary defective production copies.

Run all findings, or --finding N. Workers run the entire named suite; exceptions, timeouts,
missing rows and process failures are errors, never successful mutation detections.
"""
import argparse
import ast
import concurrent.futures
import contextlib
import difflib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
SIGNED = '("schema", "workspace", "domain_uuid", "store_uuid", "command") + IDENTITY_FIELDS'
FIELDS = ('schema', 'workspace', 'domain_uuid', 'store_uuid', 'command',
          'repository_uuid', 'repository_root_commit', 'clone_uuid',
          'binding_digest', 'authority_generation')


def cases():
    result = []

    def add(finding, name, suite, module, old, new, rows, also=()):
        case = dict(finding=finding, name=name, suite=suite, module=module,
                    old=old, new=new, rows=rows)
        if also:
            # Further exact replacements in the same module, for a defect that one edit cannot
            # reintroduce because the fixed code guards it in several places.
            case['also'] = [list(pair) for pair in also]
        result.append(case)

    def signature(name, old, new, rows):
        add(1, name, '47_veldo_0107_ipc.py', 'control_client.py', old, new, rows)

    signature('command-only', SIGNED, '("command",)',
              ['ipc/signature-covers/' + f for f in FIELDS if f != 'command'])
    for field in FIELDS:
        signature('omit-' + field, SIGNED,
                  'tuple(k for k in (' + SIGNED + ') if k != ' + repr(field) + ')',
                  ['ipc/signature-covers/' + field])
    signature('unsigned-request-field', '    req.update({k: binding[k] for k in IDENTITY_FIELDS})',
              '    req["extra_coordinate"] = "added"\n'
              '    req.update({k: binding[k] for k in IDENTITY_FIELDS})',
              ['ipc/signature-fields-match-request'])
    signature('signed-nonrequest-field', SIGNED, SIGNED + ' + ("extra_coordinate",)',
              ['ipc/signature-fields-match-request'])
    empty_paths = {
        'unreachable': ('        return EXIT_UNREACHABLE',
                        'relay/an-unreachable-authority-is-reported-not-answered'),
        'usage': ('        return 64', 'relay/usage-has-zero-stdout'),
        'oversized-request': ('        return EXIT_TOO_LARGE\n    try:',
                              'relay/oversized-request-has-zero-stdout'),
        'oversized-response': ('        return EXIT_TOO_LARGE\n    stdout.write(answer)',
                               'relay/oversized-response-has-zero-stdout'),
    }
    for path, (anchor, row) in empty_paths.items():
        for name, payload in [('null', b'null'), ('newline', b'\n'), ('space', b' ')]:
            add(2, path + '-' + name, '48_veldo_0108_relay.py', 'control_relay.py',
                anchor, '        stdout.write(' + repr(payload) + ')\n' + anchor, [row])
    add(2, 'unreachable-object', '48_veldo_0108_relay.py', 'control_relay.py',
        '        return EXIT_UNREACHABLE',
        '        stdout.write(b"{}")\n        return EXIT_UNREACHABLE',
        ['relay/an-unreachable-authority-is-reported-not-answered'])
    scope = '    scope = start_line_scope(repo, start_line or "", commit, bundle_landed_at(repo, proof_dir))'
    # Preserve the scope expression: the suite also replaces it for its existing
    # precedence control. An additive assignment composes with that mutation.
    for name, assignment in [
        ('manifest-fallback', 'start_line or manifest.get("from_commit")'),
        ('nested-manifest-fallback', 'start_line or manifest.get("fix_validation", {}).get("from_commit")'),
        ('manifest-precedence', 'manifest.get("from_commit") or start_line'),
    ]:
        add(3, name, '44_veldo_0105_startline.py', 'fix_validation_record.py', scope,
            '    start_line = ' + assignment + '\n' + scope,
            ['proofcheck/start-line-not-author-writable'])
    add(5, 'clone-local-store', '46_veldo_0029_enrollment.py', 'control_enrollment.py',
        '             "problems": [p[0] for p in problems]})\n    return binding["store_path"]',
        '             "problems": [p[0] for p in problems]})\n'
        '    return binding["store_path"] + "." + binding["clone_uuid"]',
        ['enrollment/independent-clones-share-bound-store'])
    add(6, 'dead-socket-success', '49_veldo_0109_unavailable.py', 'control_client.py',
        '            seen = last_seen(enrollment, workspace, binding)',
        '            seen = last_seen(enrollment, workspace, binding)\n'
        '            if os.path.exists(address) and __import__("stat").S_ISSOCK(os.stat(address).st_mode):\n'
        '                return {"accepted": True, "watermark": seen.get("watermark") if seen else None}',
        ['unavailable/sigkill-refuses-generic-client'])
    add(12, 'exclusive-request-limit', '48_veldo_0108_relay.py', 'control_relay.py',
        '        if total > limit:', '        if total >= limit:',
        ['relay/exact-limit-request-is-carried'])
    add(12, 'exclusive-response-limit', '48_veldo_0108_relay.py', 'control_relay.py',
        '            if total > MAX_BYTES:', '            if total >= MAX_BYTES:',
        ['relay/exact-limit-response-is-carried'])
    def grammar(name, module, old, new, row):
        add(118, name, '54_veldo_0118_grammar.py', module, old, new, ['grammar/' + row])
        result[-1]['fixture'] = True

    grammar('omit-folded-block', 'grammar_cases.py',
            "    for identity, node, fmt in coverage_accepted(data):\n",
            "    for identity, node, fmt in coverage_accepted(data):\n"
            "        if 'folded' in coverage_seen(node, data)['production']:\n            continue\n",
            'all-coverage-targets-exist')
    grammar('omit-recursive-pair', 'grammar_cases.py',
            "    for site in sorted(required['pair']):\n",
            "    for site in sorted(required['pair']):\n"
            "        if site == ('flow-map', 'value', 'flow-map'):\n            continue\n",
            'all-coverage-targets-exist')
    for name, rule in [('omit-duplicate-key', 'duplicate-key'), ('omit-tab-edit', 'bad-indentation')]:
        grammar(name, 'grammar_cases.py',
                "    for rule, parent, slot, child in sorted(coverage_targets(data)['boundary']):\n",
                "    for rule, parent, slot, child in sorted(coverage_targets(data)['boundary']):\n"
                "        if rule == " + repr(rule) + ":\n            continue\n",
                'all-boundary-sites-exist')
    grammar('omit-oracle-observation', 'yaml_oracle.py',
            "    yaml = cap['module']\n",
            "    if text == 'a: a\\n':\n        return dict(result, state='unobserved')\n"
            "    yaml = cap['module']\n", 'oracle-observations-complete')
    grammar('oracle-runtime-error', 'yaml_oracle.py',
            "    yaml = cap['module']\n",
            "    if text == 'a: a\\n':\n        return dict(result, state='oracle_error')\n"
            "    yaml = cap['module']\n", 'oracle-observations-complete')
    grammar('delegate-oracle-to-reader', 'yaml_oracle.py',
            "return {'state': 'value', 'value': adapt_node(raw['tree'])}",
            "return {'state': 'value', 'value': __import__('yamlish').parse(raw['source'])}",
            'oracle-is-independent')
    grammar('delegate-oracle-to-front-matter', 'yaml_oracle.py',
            "return {'state': 'value', 'value': adapt_node(raw['tree'])}",
            "return {'state': 'value', 'value': __import__('yamlish').front_matter(raw['source'])}",
            'oracle-is-independent')
    grammar('absence-counts-as-agreement', 'yaml_oracle.py',
            "            result['unobserved'] += 1\n",
            "            result['unobserved'] += 1\n"
            "            if raw['state'] == 'oracle_unavailable':\n"
            "                result['compared'] += 1\n                result['agreed'] += 1\n",
            'missing-oracle-is-unproven')
    grammar('broken-dependency-counts-as-absence', 'yaml_oracle.py',
            "state = 'oracle_unavailable' if exc.name == 'yaml' else 'oracle_error'",
            "state = 'oracle_unavailable'",
            'missing-oracle-is-unproven')
    def agreement(name, module, old, new, row, fixture=False):
        add(119, name, '55_veldo_0119_agreement.py', module, old, new, ['reader/' + row])
        if fixture:
            result[-1]['fixture'] = True

    agreement('reader-strip-quoted-hash', 'yamlish.py',
              "                return ''.join(out)",
              "                return ''.join(out).split('#', 1)[0]",
              'generated-grammar-agrees')
    agreement('reader-coerce-leading-zero', 'yamlish.py',
              "return int(word) if _INT.fullmatch(word) else word",
              "return int(word) if re.fullmatch(r'-?[0-9]+', word) else word",
              'generated-grammar-agrees')
    agreement('reader-overwrite-duplicate', 'yamlish.py',
              "                if key in out:\n                    self.error(n, 'duplicate key ' + repr(key))",
              "                if False:\n                    self.error(n, 'duplicate key ' + repr(key))",
              'generated-boundaries-refuse')
    agreement('reader-accept-unclosed-flow', 'yamlish.py',
              "        self.error('unclosed collection')",
              "        return out",
              'generated-boundaries-refuse')
    agreement('reader-unavailable-counts-as-compared', 'reader_agreement.py',
              "            report['unobserved'] += 1",
              "            report['unobserved'] += 1\n"
              "            if raw['state'] == 'oracle_unavailable':\n"
              "                report['compared'] += 1",
              'agreement-requires-full-oracle-domain', fixture=True)
    agreement('reader-omit-from-required-domain', 'reader_agreement.py',
              "    required = Counter(identity(case) for case in cases)",
              "    if omit is not None:\n        cases = cases[1:]\n        omit = None\n"
              "    required = Counter(identity(case) for case in cases)",
              'agreement-requires-full-oracle-domain', fixture=True)
    def policy(name, module, old, new, row, fixture=False):
        add(120, name, '57_veldo_0120_policygrammar.py', module, old, new, ['policyread/' + row])
        if fixture:
            result[-1]['fixture'] = True

    policy('policy-strip-quoted-hash', 'yamlish.py',
           "                return ''.join(out)",
           "                return ''.join(out).split('#', 1)[0]",
           'generated-settings-agree')
    policy('policy-coerce-leading-zero', 'fix_validation_record.py',
           '        block[START_KEY] = str(block[START_KEY])',
           '        block[START_KEY] = str(int(block[START_KEY])) if str(block[START_KEY]).isdigit() else str(block[START_KEY])',
           'generated-settings-agree')
    policy('policy-syntax-becomes-absent', 'fix_validation_record.py',
           '        raise ValidationError(f"{policy_path}: {exc}") from exc',
           '        return {}', 'generated-invalid-is-not-absent')
    policy('policy-shape-becomes-absent', 'fix_validation_record.py',
           '        raise ValidationError(f"{policy_path}: {FLAG_KEY} must be a nonempty mapping")',
           '        return {}', 'generated-invalid-is-not-absent')
    policy('policy-absent-oracle-qualifies', 'policy_agreement.py',
           "    return (report['oracle_state'] == 'available' and report['inventory_complete']",
           "    return (report['oracle_state'] == 'oracle_unavailable' or report['oracle_state'] == 'available' and report['inventory_complete']",
           'generated-oracle-coverage-is-honest', fixture=True)
    policy('policy-omit-required-result', 'policy_agreement.py',
           '    executed = {name: Counter() for name in readers}',
           "    if omit is not None:\n        cases = cases[1:]\n        expected = expected.copy()\n        del expected[next(iter(expected))]\n        omit = None\n"
           '    executed = {name: Counter() for name in readers}',
           'generated-oracle-coverage-is-honest', fixture=True)

    def signing(name, module, old, new, row):
        add(27, name, '56_veldo_0027_signing.py', module, old, new, ['signing/' + row])

    signing('signing-prelock-clock', 'control_keys.py',
            "    at, kid = time.time(), params['key_id']",
            "    at, kid = params['admitted_at'], params['key_id']", 'transition-clock')
    signing('signing-truncated-clock', 'control_keys.py',
            "    at, kid = time.time(), params['key_id']",
            "    at, kid = int(time.time()), params['key_id']", 'transition-clock')
    restriction = "        if request.get('channel') != channel or request.get('edge_key_id') != key['key_id']:"
    signing('signing-remove-channel-restriction', 'control_signer.py', restriction,
            '        if False:', 'cross-channel')
    signing('signing-permit-foreign-channel', 'control_signer.py', restriction,
            "        if request.get('channel') == channel and request.get('edge_key_id') != key['key_id']:", 'cross-channel')
    auth = "        channel = authenticate(state, challenge, request, identity, authentication, now)"
    signing('signing-request-channel', 'control_signer.py', auth,
            auth + "\n        channel = request['channel']", 'channel-comes-from-the-connection')
    signing('signing-request-key-channel', 'control_signer.py', auth,
            auth + "\n        channel = K.entries(state)[request['edge_key_id']]['channel']", 'channel-comes-from-the-connection')
    selection = "        key = K.select(state, config['allowed_signers'], channel, now)"
    signing('signing-request-key', 'control_signer.py', selection,
            selection + "\n        key = K.entries(state).get(request.get('edge_key_id'), key)", 'key-comes-from-the-channel')
    signing('signing-ignore-key-crosscheck', 'control_signer.py', restriction,
            "        if request.get('channel') != channel:", 'key-comes-from-the-channel')
    attribution = "    if any(not attribution.get(field) for field in fields):"
    signing('signing-text-without-identity', 'control_signer.py', attribution,
            '    if False:', 'text-only')
    signing('signing-text-substitutes-identity', 'control_signer.py', attribution,
            "    if not payload.get('text') and any(not attribution.get(field) for field in fields):", 'text-only')
    accepted = """    if body != projection(state):
        raise Refused('projection-mismatch')
    return state['keyring']"""
    branch_keys = """    return [dict(k, public_key=' '.join(line.split()[-2:]))
            for k in state['keyring'] for line in body.splitlines()
            if line.split() and line.split()[0] == k['principal']]"""
    signing('signing-branch-projection-authority', 'control_keys.py', accepted, branch_keys, 'branch-key')
    signing('signing-branch-preflight-bypass', 'control_keys.py',
            "    keyring = administrative_keyring(state, projection_path)",
            "    if Path(projection_path).read_text() != projection(state):\n"
            "        return {'committed': True}\n"
            "    keyring = administrative_keyring(state, projection_path)", 'branch-key')
    content = "               for field in AC.DECISION_ASSERTION_FIELDS):"
    signing('signing-ignore-personal-content', 'control_signer.py', content,
            "               for field in ()):", 'personal-content-binding')
    signing('signing-ignore-personal-ruling', 'control_signer.py', content,
            "               for field in ('presentation_id',)):", 'personal-content-binding')
    signing('signing-bind-only-original-fields', 'control_signer.py', content,
            "               for field in ('ruling', 'presentation_id')):", 'personal-relabel/presentation_digest')
    signing('signing-default-missing-personal-fields', 'control_signer.py',
            "        if any(field not in parameters or field not in payload or parameters[field] != payload[field]",
            "        if any(parameters.get(field, payload.get(field)) != payload.get(field)",
            'personal-missing/presentation_digest')
    binding = "    if payload.get('edge_key_id') != request['edge_key_id']:"
    signing('signing-ignore-selected-key-binding', 'control_signer.py', binding,
            "    if False:", 'rotation-requires-rebound-delegation')
    signing('signing-retired-key-inherits-grant', 'control_signer.py', binding,
            "    if payload.get('edge_key_id') != request['edge_key_id'] and K.active(K.entries(state)[payload['edge_key_id']], now):",
            'rotation-requires-rebound-delegation')
    signing('signing-leak-source-before-auth', 'control_signer.py', auth,
            "        source = state['entities'].get(request.get('source_id'), {}).get('data', {})\n"
            "        diagnostic.update(principal=source.get('principal'), assertion_kind=source.get('assertion_kind'))\n" + auth,
            'unauthenticated-diagnostic-is-empty')
    signing('signing-leak-revision-before-auth', 'control_signer.py', auth,
            "        diagnostic['delegation_revision'] = state['delegation_version']\n" + auth,
            'unauthenticated-diagnostic-is-empty')
    envelope_check = "        if problems:\n            raise K.Refused('missing-attribution')"
    signing('signing-ignore-envelope-problems', 'control_signer.py', envelope_check,
            "        if False:\n            raise K.Refused('missing-attribution')", 'personal-envelope-expiry')
    signing('signing-ignore-envelope-expiry', 'control_signer.py', envelope_check,
            "        if any('expired' not in problem for problem in problems):\n            raise K.Refused('missing-attribution')",
            'personal-envelope-expiry')
    signing('signing-copy-envelope-coordinates', 'control_signer.py',
            "        authority = dict(authority_ids, membership_version=state['membership_version'],",
            "        authority = dict(envelope, membership_version=state['membership_version'],",
            'personal-foreign/store_uuid')
    signing('signing-ignore-coordinate-problems', 'control_signer.py', envelope_check,
            "        if any('wrong repository, domain or store' not in problem for problem in problems):\n"
            "            raise K.Refused('missing-attribution')", 'personal-foreign/domain_uuid')
    def effect(name, old, new, criterion, also=()):
        add(28, name, '58_veldo_0028_effects.py', 'control_effects.py', old, new,
            ['effects/' + criterion + '/' + kind for kind in ('provider', 'publication')], also)
    scope = "    if any(request.get(f) != contract[f] for f in BINDINGS):\n        raise Refused('scope-mismatch')"
    effect('effects-worker-scope', scope,
           "    contract = dict(contract, **{f: request[f] for f in BINDINGS})\n    entry = dict(entry, data=contract)", 'scope')
    effect('effects-overlong-handle', "expires_at=min(contract['deadline'] + 900, time.time() + 900)",
           "expires_at=contract['deadline'] + 901", 'scope')
    replay = """    if previous:
        if previous['data']['request_digest'] != SIG.digest(request):
            raise Refused('request-content-conflict')
        return previous['data'], False
    nonce = hid"""
    effect('effects-second-use-before-consumption', replay,
           """    if previous and previous['data']['request_digest'] != SIG.digest(request):
        raise Refused('request-content-conflict')
    nonce = hid if previous else secrets.token_hex(20)""", 'nonce')
    effect('effects-changed-content-replay', "        if previous['data']['request_digest'] != SIG.digest(request):",
           "        if False:", 'nonce')
    effect('effects-acceptance-is-completion', "    completed = status == 'completed' and bool(observation.get('evidence'))",
           "    completed = status in ('accepted', 'completed') and bool(observation.get('evidence'))", 'completion')
    effect('effects-unbound-result', "    matches = isinstance(observation, dict) and all(observation.get(f) == accepted[f] for f in bound)",
           "    matches = isinstance(observation, dict)", 'completion')
    revocation = "    if revoked(conn, principal, now):\n        raise Refused('revoked')"
    effect('effects-ignore-authorization-revocation', revocation,
           "    if False:\n        raise Refused('revoked')", 'revocation-committed')
    # Acceptance is ordered against revocation by VELDO-0026's accept_effect inside the store
    # transaction, with the ledger a declared version. Checking only the preflight means undoing
    # that ordering too: no revocable effect, no ledger declaration, no reconciliation.
    v26_accept = ("            changes = dict(S.COMMAND_REGISTRY['accept_effect']['transition'](\n"
                  "                {'effect_id': rid, 'principal': principal, 'receiver': contract['target'],\n"
                  "                 'kind': contract['kind'], 'at': time.time()}, before))")
    v26_reconcile = "        if completed or status == 'refused':\n            changes.update("
    effect('effects-revocation-preflight-only', revocation,
           "    if not consume and revoked(conn, principal, now):\n        raise Refused('revoked')", 'revocation-before-transaction',
           also=[(v26_accept, "            changes = {}"),
                 ("{'new_ids': [eid, rid, R.LEDGER_ENTITY]}", "{'new_ids': [eid]}"),
                 (v26_reconcile, "        if False:\n            changes.update(")])
    # R3 A: an accepted protected effect is in flight for VELDO-0026's revocation accounting.
    effect('effects-invisible-to-revocation', v26_accept,
           v26_accept.replace("'principal': principal,", "'principal': 'effect-executor',"), 'revocation-in-flight')
    effect('effects-pending-reconciled-as-settled', v26_reconcile,
           "        if status in ('accepted', 'completed'):\n            changes.update(", 'revocation-in-flight')
    # R3 B: a committed ledger entry applies from its commit, whatever its timestamp.
    ledger_read = "    return principal in R.ledger(S, conn)[0]['revoked'] or R.is_revoked(S, conn, principal, now)"
    effect('effects-future-dated-revocation-waits', ledger_read,
           "    return R.is_revoked(S, conn, principal, now)", 'revocation-future-dated')
    effect('effects-revocation-skew-allowance', ledger_read,
           "    return R.ledger(S, conn)[0]['revoked'].get(principal, {}).get('at', now + 2) <= now + 1 or R.is_revoked(S, conn, principal, now)",
           'revocation-future-dated')
    # R3 E: a review by a revoked principal satisfies nothing.
    reviewer = "        if revoked(conn, data['reviewer'], now):"
    add(28, 'effects-revoked-reviewer-accepted', '58_veldo_0028_effects.py', 'control_effects.py', reviewer,
        "        if False:", ['effects/publication-revoked-reviewer'])
    add(28, 'effects-reviewer-membership-only', '58_veldo_0028_effects.py', 'control_effects.py', reviewer,
        "        if state.get(data['reviewer'], {}).get('data', {}).get('revoked_at') is not None:",
        ['effects/publication-revoked-reviewer'])
    receiver_refused = ("            if isinstance(observation, dict) and observation.get('status') == 'refused':\n"
                        "                # A receiver that ran may already have acted, so its own \"refused\" is not\n"
                        "                # conclusive and its text is not repeated: recorded as unknown, a stop owed.\n"
                        "                observation = dict(accepted, status='unknown', evidence=None)\n")
    for name, new, kinds in (('effects-receiver-refused-conclusive', '', ('provider', 'publication')),
                             ('effects-receiver-refused-provider-only',
                              receiver_refused.replace("== 'refused':", "== 'refused' and contract.get('kind') == 'provider':"),
                              ('publication',))):
        add(28, name, '58_veldo_0028_effects.py', 'control_effect_executor.py', receiver_refused, new,
            ['effects/receiver-refused-is-unknown/' + kind for kind in kinds])
    def publication(name, old, new, criterion):
        add(28, name, '58_veldo_0028_effects.py', 'control_effect_executor.py', old, new,
            ['effects/' + criterion])
    push = ("        push = transport('-c', 'push.followTags=false', '-c', 'push.pushOption=', 'push', '--porcelain',\n"
            "                         '--no-follow-tags', '--recurse-submodules=no',")
    publication('effects-push-widened-by-clone-config', push,
                "        push = transport('push', '--porcelain',\n                         '--recurse-submodules=no',", 'publication-exact-ref')
    publication('effects-push-follows-tags', push,
                push.replace("'--no-follow-tags'", "'--follow-tags'"), 'publication-exact-ref')
    confirm = "after == expected else 'not-at-tip'"
    publication('effects-confirm-authorized-ref-only', confirm,
                "after.get(ref) == payload['commit'] else 'not-at-tip'", 'publication-confirms-one-change')
    publication('effects-confirm-ignores-new-refs', confirm,
                "all(after.get(k) == v for k, v in expected.items()) else 'not-at-tip'",
                'publication-confirms-one-change')
    # R4: an ordinary git push keeps what configured Git allows. Reintroducing send-pack loses
    # the clone's hooks, its URL rewrites and every HTTP(S) remote at once.
    send_pack = "        push = transport('send-pack',"
    add(28, 'effects-push-by-send-pack', '58_veldo_0028_effects.py', 'control_effect_executor.py', push, send_pack,
        ['effects/publication-' + name for name in ('pre-push-hook', 'url-rewrite', 'smart-http')])
    publication('effects-push-skips-hooks', push, push.replace("'push',", "'push', '--no-verify',"),
                'publication-pre-push-hook')
    newline_remote = "        if '\\n' in remote:\n"
    publication('effects-remote-must-exist-verbatim', newline_remote,
                "        if '\\n' in remote or not (Path(remote).exists() or '://' in remote):\n", 'publication-url-rewrite')
    publication('effects-push-transports-restricted', push,
                push.replace("transport('-c', 'push.followTags=false',", "transport('-c', 'protocol.http.allow=never', '-c', 'push.followTags=false',"),
                'publication-smart-http')
    # R4 P2: confirmation reads HEAD and its symbolic target, not only the refs namespace.
    listing = "            listed = transport('ls-remote', '--symref', url)"
    publication('effects-confirm-without-head', listing,
                "            listed = transport('ls-remote', '--refs', url)", 'publication-head-change')
    publication('effects-confirm-without-symref-targets', listing,
                "            listed = transport('ls-remote', url)", 'publication-head-change')
    # R5 1: push options from any configuration scope never reach the receiver. `--no-push-option`
    # looks like the fix and clears only options given on the command line.
    publication('effects-push-options-from-config', push, push.replace("'-c', 'push.pushOption=', ", ''),
                'publication-push-options')
    publication('effects-push-options-flag-only', push,
                push.replace("'-c', 'push.pushOption=', 'push',", "'push', '--no-push-option',"),
                'publication-push-options')
    # R6 1 and R7: the push is routed as the operator configured it; where it goes is git's own
    # resolution from configuration, and completion is each destination's state after the push.
    # Each mutant loses one part of that account or reads it from text the push prints.
    routed = 'publication-records-resolved-destination'
    add(28, 'effects-destination-not-recorded', '58_veldo_0028_effects.py', 'control_effects.py',
        "        result['destination'] = destination", "        pass",
        ['effects/' + routed, 'effects/publication-destination-without-credentials'])
    parsed = ("        pushed = []\n        for line in lines[1:]:\n            if not line.startswith('  Push  URL: '):\n"
              "                break\n            pushed.append(line[len('  Push  URL: '):])\n")
    shape = "                or lines[1 + len(pushed):2 + len(pushed)] != ['  HEAD branch: (not queried)']):"
    # The fetch-side resolution (`ls-remote --get-url`) in place of git's push resolution: it
    # misses pushInsteadOf and pushurl routing, so the record names the authorized repository.
    add(28, 'effects-destinations-from-fetch-url', '58_veldo_0028_effects.py', 'control_effect_executor.py', parsed,
        "        pushed = [transport('ls-remote', '--get-url', remote).stdout.strip()]\n",
        ['effects/' + routed, 'effects/publication-destination-despite-hook-text',
         'effects/publication-rejected-destination-recorded'], also=[(shape, "                or False):")])
    # The destinations read from the To lines a dry-run push prints: hook text reaches them.
    add(28, 'effects-destinations-from-dry-run-output', '58_veldo_0028_effects.py', 'control_effect_executor.py', parsed,
        "        pushed = [line[len('To '):] for line in transport('push', '--dry-run', '--porcelain', remote,\n"
        "                  payload['commit'] + ':' + ref).stdout.splitlines() if line.startswith('To ')]\n",
        ['effects/publication-destination-despite-hook-text', 'effects/publication-rejected-destination-recorded',
         'effects/publication-hook-text-without-newline'], also=[(shape, "                or False):")])
    # Git's resolution read in the isolated profile, so global routing is missed.
    add(28, 'effects-resolution-isolated-profile', '58_veldo_0028_effects.py', 'control_effect_executor.py',
        "        shown = transport('remote', 'show', '-n', '--', remote, env=dict(",
        "        shown = git('remote', 'show', '-n', '--', remote, env=dict(",
        ['effects/' + routed, 'effects/publication-config-selection-parity'])
    # The guard against a configured URL holding a line break removed.
    add(28, 'effects-newline-config-accepted', '58_veldo_0028_effects.py', 'control_effect_executor.py',
        "        if urls.returncode not in (0, 1) or any(", "        if False and any(",
        ['effects/' + routed, 'effects/publication-line-break-refused'])
    complete = "        complete = push.returncode == 0 and all(outcome == 'at-tip' for outcome in outcomes)"
    # Completion from the push's exit status alone, from the first destination only, or from the
    # To lines the push prints.
    add(28, 'effects-completion-from-exit-status', '58_veldo_0028_effects.py', 'control_effect_executor.py', complete,
        "        complete = push.returncode == 0",
        ['effects/publication-completion-from-destination-state', 'effects/publication-fan-out-agit-report'])
    add(28, 'effects-completion-first-destination', '58_veldo_0028_effects.py', 'control_effect_executor.py', complete,
        "        complete = push.returncode == 0 and outcomes[:1] == ['at-tip']",
        ['effects/publication-fan-out-agit-report'])
    publication('effects-completion-from-push-output', complete,
                complete + "\n        complete = complete and all('To ' + url in push.stdout.splitlines() for url in pushed)",
                'publication-hook-text-without-newline')
    # Each destination's state read at the authorized URL instead of at the destination.
    add(28, 'effects-state-read-at-authorized-url', '58_veldo_0028_effects.py', 'control_effect_executor.py',
        "            after = remote_refs(url)\n", "            after = remote_refs(remote)\n",
        ['effects/publication-completion-from-destination-state', 'effects/publication-fan-out-agit-report'],
        also=[("        before = [remote_refs(url) for url in pushed]", "        before = [remote_refs(remote) for url in pushed]")])
    # Output read strictly as UTF-8: the push's (a hook's Latin-1 byte) or a listing's (a ref name).
    publication('effects-push-output-read-strictly', "                         remote, payload['commit'] + ':' + ref, steps=len(pushed))\n",
                "                         remote, payload['commit'] + ':' + ref, steps=len(pushed))\n        push.stdout.encode('utf-8')\n",
                'publication-non-utf8-output')
    publication('effects-listing-read-strictly', "            if listed.returncode:\n                return None\n",
                "            listed.stdout.encode('utf-8')\n            if listed.returncode:\n                return None\n",
                'publication-non-utf8-output')
    # Credentials: the authorized URL, or the resolved destinations, recorded as given.
    publication('effects-destination-with-credentials', "        destination = {'authorized_url': scrubbed_url(remote),",
                "        destination = {'authorized_url': remote,", 'publication-destination-without-credentials')
    add(28, 'effects-destinations-not-scrubbed', '58_veldo_0028_effects.py', 'control_effect_executor.py',
        "                       'destinations': [{'url': scrubbed_url(url), 'outcome': outcome}",
        "                       'destinations': [{'url': url, 'outcome': outcome}",
        ['effects/publication-destination-without-credentials', 'effects/publication-scrub-transport-prefix'])
    # Scrubbing by parsing: an scp-style address's user information ends at its LAST `@`, a
    # transport-prefixed URL is scrubbed in its address, and a query or fragment is dropped.
    scp = "    rest = url[url.rfind('@', 0, len(url) if slash < 0 else slash) + 1:]"
    publication('effects-scrub-scp-first-at', scp, scp.replace('url.rfind(', 'url.find('), 'publication-scrub-scp-user-information')
    publication('effects-scrub-scp-unchanged', "    if colon < 0:\n        return url\n", "    if True:\n        return url\n",
                'publication-scrub-scp-user-information')
    publication('effects-scrub-transport-not-recursed', "    if scheme and url.startswith('::', scheme.end()):",
                "    if False:", 'publication-scrub-transport-prefix')
    publication('effects-scrub-keeps-query', "            tail = tail.partition('?')[0]\n", "", 'publication-scrub-query-fragment')
    publication('effects-scrub-keeps-fragment', "            tail = tail.partition('#')[0]\n", "", 'publication-scrub-query-fragment')
    # R8 B1: nothing is pushed unless every destination was listed first and holds the expected
    # old state (the old tip, or absent for a creation); the refusal is named, recorded as
    # conclusive, reconciled as stopped and returned again on a replay.
    stale_rows = ['effects/publication-refused-when-not-at-old-tip', 'effects/' + routed]
    precheck = ("        if any(state is None or (ref in state if absent else state.get(ref) != payload['old_tip'])\n"
                "               for state in before):")
    publication('effects-push-without-old-tip-check', precheck, "        if False:", 'publication-refused-when-not-at-old-tip')
    add(28, 'effects-old-tip-checked-at-first-destination', '58_veldo_0028_effects.py', 'control_effect_executor.py',
        precheck, precheck.replace('for state in before):', 'for state in before[:1]):'), stale_rows)
    add(28, 'effects-unlisted-destination-pushed', '58_veldo_0028_effects.py', 'control_effect_executor.py',
        precheck, precheck.replace('state is None or (', 'state is not None and ('),
        stale_rows + ['effects/publication-config-selection-parity'])
    add(28, 'effects-receiver-refusal-as-unknown', '58_veldo_0028_effects.py', 'control_effect_executor.py',
        "            observation = dict(accepted, status='refused', refusal=error.code, evidence=None)",
        "            observation = dict(accepted, status='unknown', evidence=None)",
        ['effects/publication-refused-when-not-at-old-tip', 'effects/publication-refusal-reaches-caller'])
    publication('effects-replayed-refusal-reads-accepted', "            if accepted.get('status') == 'refused':",
                "            if False:", 'publication-refusal-reaches-caller')
    add(28, 'effects-refusal-owes-a-stop', '58_veldo_0028_effects.py', 'control_effects.py',
        "                  stop=None if completed or status == 'refused' else",
        "                  stop=None if completed else", ['effects/publication-refusal-reaches-caller'])
    add(28, 'effects-refusal-left-in-flight', '58_veldo_0028_effects.py', 'control_effects.py',
        "        if completed or status == 'refused':", "        if completed:",
        ['effects/publication-refusal-reaches-caller'])
    publication('effects-creation-expects-zero-id', "        absent = set(payload['old_tip']) == {'0'}",
                "        absent = False", 'publication-ref-creation')
    publication('effects-creation-over-existing-ref', precheck, precheck.replace('(ref in state if absent', '(False if absent'),
                'publication-ref-creation')
    # R8 B2: every destination must resolve to itself for its listing, or it is refused.
    itself = ("        for url in pushed:\n            itself = transport('ls-remote', '--get-url', '--', url)\n"
              "            if itself.returncode or itself.stdout != url + '\\n':")
    publication('effects-destination-listing-unchecked', itself, itself.replace(
        "            if itself.returncode or itself.stdout != url + '\\n':", "            if False:"),
        'publication-destination-listed-as-resolved')
    publication('effects-destination-listing-first-only', itself,
                itself.replace('        for url in pushed:\n', '        for url in pushed[:1]:\n'),
                'publication-destination-listed-as-resolved')
    # R8 time limits: the push is bounded per destination, and the supervisor's limit follows
    # the windows the executor announces.
    publication('effects-push-timeout-not-scaled', "remote, payload['commit'] + ':' + ref, steps=len(pushed))",
                "remote, payload['commit'] + ':' + ref)", 'publication-call-covers-every-destination')
    publication('effects-call-window-not-extended', "                deadline = time.monotonic() + answer['window_seconds']",
                "                pass", 'publication-call-covers-every-destination')
    # R8 scrub: anything that does not parse into a well-formed host is over-scrubbed.
    malformed = 'publication-scrub-malformed-address'
    publication('effects-scrub-scp-user-at-first-colon', scp,
                "    rest = url[url.rfind('@', 0, colon) + 1:]", malformed)
    publication('effects-scrub-ext-command-kept', "        if scheme.group().lower() == 'ext':", "        if False:", malformed)
    publication('effects-scrub-malformed-host-kept', "        if not _AUTHORITY.fullmatch(host):", "        if False:", malformed)
    publication('effects-scrub-at-in-path-kept', "            if '@' in tail:", "            if False:", malformed)
    # R8 rules pinned by rows of their own: a clean push exit, the receiver-URL line-break guard,
    # the shape of git's report and the configuration read's exit status, and the C locale.
    exit_rule = 'publication-requires-clean-push-exit'
    publication('effects-completion-ignores-exit-status', complete,
                "        complete = all(outcome == 'at-tip' for outcome in outcomes)", exit_rule)
    publication('effects-completion-ignores-hook-failure', complete,
                complete.replace('push.returncode == 0', 'push.returncode != 128'), exit_rule)
    publication('effects-remote-line-break-accepted', "        if '\\n' in remote:\n", "        if False:\n",
                'publication-line-break-refused')
    report = 'publication-resolution-output-checked'
    publication('effects-show-exit-unchecked', "        if (shown.returncode or not lines", "        if (not lines", report)
    publication('effects-header-unchecked',
                "        lines = shown.stdout[len(head):].split('\\n') if shown.stdout.startswith(head) else []",
                "        lines = shown.stdout.split('\\n')[1:]", report)
    publication('effects-fetch-line-unchecked', "not lines[0].startswith('  Fetch URL: ') or ", "", report)
    publication('effects-empty-resolution-accepted', " or not pushed\n", "\n", report)
    publication('effects-head-line-unchecked', shape, "                or False):", report)
    publication('effects-config-exit-unchecked', "        if urls.returncode not in (0, 1) or any(", "        if any(", report)
    publication('effects-resolution-locale-not-forced', "env=dict(os.environ, LC_ALL='C'))", "env=None)",
                'publication-resolution-in-c-locale')
    publication('effects-resolution-messages-locale-only', "env=dict(os.environ, LC_ALL='C'))",
                "env=dict(os.environ, LC_MESSAGES='C'))", 'publication-resolution-in-c-locale')
    # R5 3: transport operations run in git_process's network profile. Reintroducing the isolated
    # profile loses global config and transport variables at once; each git_process mutant loses
    # one of them, or stops stripping the coordinates the profile must still strip.
    capability = ['effects/publication-' + name for name in
                  ('global-insteadof', 'global-credential-helper', 'env-ssh-command', 'global-ssh-command',
                   'config-selection-parity')]
    add(28, 'effects-transport-isolated-profile', '58_veldo_0028_effects.py', 'control_effect_executor.py',
        "            return git(*args, profile='network', env=env, steps=steps)", "            return git(*args, env=env, steps=steps)", capability)
    add(28, 'effects-network-profile-without-global-config', '58_veldo_0028_effects.py', 'git_process.py',
        '        result.update(GIT_NO_REPLACE_OBJECTS="1")',
        '        result.update(GIT_NO_REPLACE_OBJECTS="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")',
        [label for label in capability if 'global' in label or 'selection' in label])
    add(28, 'effects-network-profile-drops-transport-variables', '58_veldo_0028_effects.py', 'git_process.py',
        '        result.update({k: v for k, v in source.items() if k in TRANSPORT_VARIABLES})',
        '        pass', ['effects/publication-env-ssh-command'])
    add(28, 'effects-network-profile-keeps-coordinates', '58_veldo_0028_effects.py', 'git_process.py',
        '        result.update({k: v for k, v in source.items() if k in TRANSPORT_VARIABLES})',
        '        result.update({k: v for k, v in source.items() if k.startswith("GIT_")})',
        ['effects/publication-network-profile-strips-coordinates'])
    # R6 2 and 3: the network profile passes the variables that select or inject operator
    # configuration, as a plain git command honors them. One mutant strips the selectors (and
    # GIT_CONFIG_COUNT and GIT_CONFIG_PARAMETERS) as coordinates, which is the defect found; the
    # other keeps them but drops the numbered GIT_CONFIG_KEY_<n>/GIT_CONFIG_VALUE_<n> entries.
    configuration = ('        result.update({k: v for k, v in source.items()\n'
                     '                       if k in CONFIGURATION_VARIABLES or INJECTED_CONFIGURATION.fullmatch(k)})')
    selection_rows = ['effects/publication-config-selection-parity', 'effects/publication-network-profile-strips-coordinates']
    add(28, 'effects-network-profile-drops-config-selection', '58_veldo_0028_effects.py', 'git_process.py', configuration,
        '        result.update({k: v for k, v in source.items() if INJECTED_CONFIGURATION.fullmatch(k)})', selection_rows)
    add(28, 'effects-network-profile-drops-config-injection', '58_veldo_0028_effects.py', 'git_process.py', configuration,
        '        result.update({k: v for k, v in source.items() if k in CONFIGURATION_VARIABLES})', selection_rows)
    # VELDO-0036: each reservation assertion has two independently driven defects.
    def reservation(name, module, old, new, row):
        add(36, name, '58_veldo_0036_reservations.py', module, old, new,
            ['reservations/' + row])

    reservation('reservation-final-reuses-partial', 'control_reservations.py',
                "if unit in p['usage']:\n                        value['charge'][unit] = p['usage'][unit]",
                "if unit in value['observed']:\n                        value['charge'][unit] = value['observed'][unit]",
                'partial-final-retained')
    reservation('reservation-final-forgets-reservation', 'control_reservations.py',
                "            elif p['final']:",
                "            elif p['final']:\n                value['charge']['wall_seconds'] = p['usage'].get('wall_seconds', 0)",
                'partial-final-retained')
    reservation('reservation-report-before-enforcement', 'control_reservation_runtime.py',
                "        try:\n            reached = now - active['start'] >= active['wall_seconds']\n            if reached:\n                self._stop(active)\n            receipt = self.reservations.report(command_id, invocation, sequence, usage,\n                                               now=now, final=final, outcome=outcome)\n",
                "        receipt = self.reservations.report(command_id, invocation, sequence, usage,\n                                           now=now, final=final, outcome=outcome)\n        try:\n            reached = now - active['start'] >= active['wall_seconds']\n            if reached:\n                self._stop(active)\n", 'report-failure-stops')
    reservation('reservation-report-error-keeps-worker', 'control_reservation_runtime.py',
                "            # Reporting, authorization and policy reads must fail closed for the worker.\n            self._stop(active)",
                "            # Defect: report failure leaves the worker running.\n            pass",
                'report-failure-stops')
    reservation('reservation-active-ignores-wall-cap', 'control_reservation_runtime.py',
                "                for unit, cap in policy['caps'].items():",
                "                for unit, cap in policy['caps'].items():\n                    if unit == 'wall_seconds':\n                        continue",
                'current-caps')
    reservation('reservation-active-skips-project-cap', 'control_reservation_runtime.py',
                "            for policy in self.reservations._policies(call['context'], records):",
                "            for policy in self.reservations._policies(call['context'], records):\n                if policy['scope'] == 'project':\n                    continue",
                'current-caps')
    reservation('reservation-extra-slot', 'control_reservations.py',
                "if balance[unit] + wanted.get(unit, 0) > cap:",
                "if balance[unit] + wanted.get(unit, 0) > cap + 1:", 'ceilings')
    reservation('reservation-ignore-ceiling', 'control_reservations.py',
                "if balance[unit] + wanted.get(unit, 0) > cap:",
                "if False:", 'ceilings')
    reservation('reservation-check-outside-transaction', 'control_reservations.py',
                "        self._command = command",
                "        self._command = command\n"
                "        if action in ('worker', 'invocation'):\n"
                "            snapshot = self._records()\n"
                "            self._check = lambda context, wanted, records, now: type(self)._check(self, context, wanted, snapshot, now)",
                'atomic-last-slot')
    reservation('reservation-ignore-capacity-and-count', 'control_reservations.py',
                "if balance[unit] + wanted.get(unit, 0) > cap:",
                "if unit not in ('capacity', 'invocations') and balance[unit] + wanted.get(unit, 0) > cap:",
                'atomic-last-slot')
    reservation('reservation-follow-on-after-launch', 'control_reservation_runtime.py',
                "            receipt = self.reservations.reserve_call(command_id, dispatch, invocation, boundary, wall_seconds, now=now)",
                "            if boundary == 'follow_on':\n                self.launch(invocation, configuration)\n"
                "            receipt = self.reservations.reserve_call(command_id, dispatch, invocation, boundary, wall_seconds, now=now)",
                'pre-call-order')
    reservation('reservation-retry-after-launch', 'control_reservation_runtime.py',
                "            receipt = self.reservations.reserve_call(command_id, dispatch, invocation, boundary, wall_seconds, now=now)",
                "            if boundary == 'retry':\n                self.launch(invocation, configuration)\n"
                "            receipt = self.reservations.reserve_call(command_id, dispatch, invocation, boundary, wall_seconds, now=now)",
                'pre-call-order')
    reservation('reservation-ignore-wall-time', 'control_reservation_runtime.py',
                "            reached = now - active['start'] >= active['wall_seconds']",
                "            reached = False", 'usage-controls')
    reservation('reservation-ignore-window', 'control_reservations.py',
                "            for window in policy.get('windows', {}).values():",
                "            for window in ():", 'usage-controls')
    reservation('reservation-duplicate-settlement', 'control_reservations.py',
                "                return {}  # Duplicate sequence under a different delivery command settles nothing twice.",
                "                value['charge'] = {k: v * 2 for k, v in value['charge'].items()}\n"
                "                return {target: {'kind': 'subscription_reservation', 'data': value}}",
                'settles-once')
    reservation('reservation-double-reported-usage', 'control_reservations.py',
                "value['charge'][unit] = max(value['charge'].get(unit, 0), amount)",
                "value['charge'][unit] = max(value['charge'].get(unit, 0), amount) + amount",
                'settles-once')
    reservation('reservation-timeout-frees-exposure', 'control_reservations.py',
                "            elif p['final']:",
                "            elif p['final']:\n"
                "                if p['outcome'] == 'timeout':\n                    value['charge'] = dict.fromkeys(USAGE, 0)",
                'unknown-retained')
    reservation('reservation-cancel-frees-exposure', 'control_reservations.py',
                "            elif p['final']:",
                "            elif p['final']:\n"
                "                if p['outcome'] == 'cancelled':\n                    value['charge'] = dict.fromkeys(USAGE, 0)",
                'unknown-retained')
    reservation('reservation-parent-exit-releases-slot', 'control_reservations.py',
                "            if observation.get('terminated') is not True:",
                "            if False:", 'retirement')
    reservation('reservation-ignore-cleanup', 'control_reservations.py',
                "            if observation.get('cleaned') is not True:",
                "            if False:", 'retirement')
    # VELDO-0035: each declared falsifier and a distinct second mutation target
    # the same assertion row; the gate additionally drives an unchanged copy.
    def snapshots(name, module, old, new, row):
        add(35, name, '58_veldo_0035_snapshots.py', module, old, new, ['snapshots/' + row])

    snapshots('snapshot-project-only', 'control_readset.py',
              '                for name in sorted(set(current) | set(accepted)):',
              "                for name in ['entity/project']:", 'stale-input')
    snapshots('snapshot-ignore-collections', 'control_readset.py',
              '                    if current.get(name) != accepted.get(name):',
              "                    if not name.startswith('collection/') and current.get(name) != accepted.get(name):",
              'stale-input')
    snapshots('snapshot-checkout-bytes', 'control_snapshot.py',
              '    return body\n', '    return (Path(repo) / path).read_bytes()\n', 'accepted-bytes')
    snapshots('snapshot-head-bytes', 'control_snapshot.py',
              '    return body\n',
              "    return _git_process.check_output(['git', '-C', str(repo), 'cat-file', 'blob', 'HEAD:' + path])\n",
              'accepted-bytes')
    snapshots('snapshot-working-status', 'control_snapshot.py',
              '        result[safe_path(path)] = canonical(value)',
              '        result[safe_path(path)] = (Path(repo) / path).read_bytes()', 'materialized-revision')
    snapshots('snapshot-wrong-watermark', 'control_snapshot.py',
              "'accepted_commit': snapshot['accepted_commit'], 'watermark': snapshot['watermark'],",
              "'accepted_commit': snapshot['accepted_commit'], 'watermark': snapshot['watermark'] + 1,",
              'materialized-revision')
    snapshots('snapshot-unguarded-connection', 'control_store.py',
              '        if "snapshot_id" in command["parameters"] and "transaction_transition" not in reg:',
              '        if False:', 'connection-bound')
    snapshots('snapshot-deferred-transaction', 'control_readset.py',
              '        if not conn.in_transaction or not conn.command_transaction:',
              '        if not conn.in_transaction:', 'transaction-bound')
    snapshots('snapshot-allow-path-ancestors', 'control_snapshot.py',
              '            str(parent) in inventory for path in paths for parent in PurePosixPath(path).parents):',
              '            False for path in paths for parent in PurePosixPath(path).parents):',
              'path-prefix-inventory')
    snapshots('snapshot-check-only-direct-parent', 'control_snapshot.py',
              'for parent in PurePosixPath(path).parents):',
              'for parent in [PurePosixPath(path).parent]):', 'path-prefix-inventory')
    snapshots('snapshot-skip-empty-commit-validation', 'control_readset.py',
              "        SN.commit_id(self.repo, data['commit'])",
              "        if data['documents']:\n            SN.commit_id(self.repo, data['commit'])", 'status-only-commit')
    snapshots('snapshot-accept-noncommit-id', 'control_snapshot.py',
              '    if result.returncode or result.stdout.decode().strip() != commit:',
              '    if False:', 'status-only-commit')
    # VELDO-0043 AC3: the declared falsifier and two different defects target the isolated-
    # enforcement row (one each only the run, and only the static closure, can see); graph start
    # without a runtime has two of its own. The gate additionally drives an unchanged copy.
    def graph(name, module, old, new, row):
        add(43, name, '59_veldo_0043_graph.py', module, old, new, ['graph/' + row])

    graph('graph-authorization-imports-langgraph', 'authorization.py',
          'from pathlib import Path\nimport json\n',
          'from pathlib import Path\nimport json\nimport langgraph\n', 'isolated-enforcement')
    graph('graph-authorization-dynamic-runtime-import', 'authorization.py',
          '    req = request if isinstance(request, dict) else {}\n',
          "    __import__('lang' + 'graph')\n    req = request if isinstance(request, dict) else {}\n",
          'isolated-enforcement')
    graph('graph-authorization-unexercised-runtime-import', 'authorization.py',
          '        spec = importlib.util.spec_from_file_location("veldo_two_key_authz", p)\n',
          '        import langgraph.graph\n'
          '        spec = importlib.util.spec_from_file_location("veldo_two_key_authz", p)\n',
          'isolated-enforcement')
    graph('graph-start-without-runtime-launches', 'control_graph.py',
          '    if not available(runtime):\n', '    if False:\n', 'start-unavailable')
    graph('graph-start-unavailable-mislabelled', 'control_graph.py',
          "        raise Refused('runtime_unavailable', 'no graph runtime is installed for this operation",
          "        raise Refused('unknown_outcome', 'no graph runtime is installed for this operation",
          'start-unavailable')
    # VELDO-0043 AC1 and AC2 against the actual installed LangGraph: each declared falsifier, a
    # second different defect per row, and two for the tracing-off and typed-proposal rows.
    graph('graph-runner-emits-langgraph-object', 'control_graph_langgraph.py',
          '        body = json.dumps(closed(reply), allow_nan=False)\n',
          "        body = json.dumps(reply, allow_nan=False, default=lambda o: {'__class__': "
          "type(o).__module__ + '.' + type(o).__qualname__, 'repr': repr(o)})\n", 'runtime/plain-data')
    graph('graph-runner-tuple-as-plain', 'control_graph_langgraph.py',
          '    if kind is list:\n', '    if isinstance(value, (list, tuple)):\n', 'runtime/plain-data')
    graph('graph-child-inherits-working-directory', 'control_graph.py',
          'cwd=str(empty),', 'cwd=None,', 'authority/no-direct-write')
    graph('graph-child-inherits-store-descriptor', 'control_graph.py',
          'close_fds=True,', 'close_fds=False,', 'authority/no-direct-write')
    graph('graph-runner-accepts-untyped-assertion', 'control_graph_langgraph.py',
          '            if untyped:\n', '            if False:\n', 'authority/typed-proposals-only')
    graph('graph-untyped-proposal-read-as-priority', 'control_graph.py',
          "            if kind not in PROPOSALS:\n"
          "                raise Refused('invalid_response', where + ': untyped proposal')\n",
          "            if kind not in PROPOSALS:\n"
          "                item, kind = dict(item, type='priority'), 'priority'\n",
          'authority/typed-proposals-only')
    graph('graph-child-inherits-caller-environment', 'control_graph.py',
          'env=dict(ENVIRONMENT),', 'env=None,', 'runtime/tracing-off')
    graph('graph-tracing-switch-on', 'control_graph.py',
          "'LANGSMITH_TRACING_V2': 'false'", "'LANGSMITH_TRACING_V2': 'true'", 'runtime/tracing-off')
    # Review findings F5, F4, F3, F2 and F1 (2026-09-23): two different defects per new row.
    graph('graph-deep-answer-unbounded', 'control_graph.py',
          '    if text_depth(raw) > MAX_DEPTH:\n', '    if False:\n', 'shape/deep-answer')
    graph('graph-deep-answer-unnamed', 'control_graph.py',
          "        raise Refused('invalid_response', 'answer nests deeper than ' + str(MAX_DEPTH))",
          "        raise ValueError('answer nests deeper than ' + str(MAX_DEPTH))", 'shape/deep-answer')
    graph('graph-digest-prefix-only', 'control_graph.py',
          r"DIGEST = re.compile(r'sha256:[0-9a-f]{64}\Z')", r"DIGEST = re.compile(r'sha256:')",
          'shape/closed-request')
    graph('graph-request-path-unchecked', 'control_graph.py',
          '        if looks_like_path(text):\n', '        if False:\n', 'shape/closed-request')
    graph('graph-answer-resume-open', 'control_graph.py',
          "        _resume_shape(value['resume'], 'resume', 'invalid_response')\n", "        pass\n",
          'shape/closed-response')
    graph('graph-answer-notes-any-plain', 'control_graph.py',
          "    if type(value['notes']) is not str or len(value['notes']) > MAX_NOTES:\n",
          "    if len(value['notes']) > MAX_NOTES:\n", 'shape/closed-response')
    graph('graph-suspend-without-graph', 'control_graph_langgraph.py',
          '    return run_cycle(request, workflow, resume)\n',
          "    if request['operation'] == 'suspend':\n"
          "        return _reply(request, 'suspended', {'name': 'langgraph', 'version': '1.2.12'}, resume=resume)\n"
          '    return run_cycle(request, workflow, resume)\n', 'runtime/lifecycle')
    graph('graph-runtime-evidence-unchecked', 'control_graph.py',
          '            if self.evidence is not None and not evidenced(result, self.evidence):\n',
          '            if False:\n', 'runtime/lifecycle')
    graph('graph-runner-launched-in-place', 'control_graph.py',
          "            proc = subprocess.Popen([runtime['python'], '-I', '-B', str(staged)],",
          "            proc = subprocess.Popen([runtime['python'], '-I', '-B', runtime['runner']],",
          'authority/no-direct-write')
    # The stated limit's real falsifier (second review): the adapter makes itself non-dumpable,
    # which closes /proc/<parent>/cwd and fd to a same-account child. It replaces the two earlier
    # notes-path mutants, which broke the row's observation channel rather than the limit.
    graph('graph-proc-closed-by-nondumpable', 'control_graph.py',
          '        staged, work = stage(runtime)\n',
          "        __import__('ctypes').CDLL(None).prctl(4, 0, 0, 0, 0)\n        staged, work = stage(runtime)\n",
          'authority/proc-limit')
    # Second review (2026-09-23): links the adapter did not make, answer encodings, request
    # paths and sizes, process groups, the runtime's pyvenv.cfg.
    graph('graph-stage-links-unchecked', 'control_graph.py',
          "    runners, work = _unlinked(root, 'runners'), _unlinked(root, 'work')\n",
          "    runners, work = root / 'runners', root / 'work'\n"
          "    runners.mkdir(exist_ok=True)\n    work.mkdir(exist_ok=True)\n", 'authority/stage-links')
    graph('graph-stage-link-checks-off', 'control_graph.py',
          "    if path.is_symlink():\n"
          "        raise Refused('runtime_unavailable', 'the stage ' + name + ' is a link the adapter did not make')\n"
          "    if path.exists() and not path.is_dir():\n"
          "        raise Refused('runtime_unavailable', 'the stage ' + name + ' is not a directory')\n"
          "    path.mkdir(mode=0o700, exist_ok=True)\n"
          "    if path.is_symlink() or not path.is_dir() or path.resolve() != path:\n",
          "    if path.exists() and not path.is_dir():\n"
          "        raise Refused('runtime_unavailable', 'the stage ' + name + ' is not a directory')\n"
          "    path.mkdir(mode=0o700, exist_ok=True)\n"
          "    if False:\n", 'authority/stage-links')
    graph('graph-runners-repository-unchecked', 'control_graph.py',
          '    if inside_repository(runners):\n', '    if False:\n', 'authority/stage-links')
    graph('graph-git-not-asked', 'control_graph.py',
          '        if _shaped_like_repository(place) or any(git_finds_repository(start) for start in _discovery_starts(place)):\n',
          '        if _shaped_like_repository(place):\n', 'authority/stage-links')
    graph('graph-runtime-loop-escapes', 'control_graph.py',
          '    except (OSError, RuntimeError, ValueError) as error:\n'
          "        raise Refused('runtime_unavailable', 'the runtime cannot be judged: '",
          '    except OSError as error:\n'
          "        raise Refused('runtime_unavailable', 'the runtime cannot be judged: '", 'authority/stage-shapes')
    graph('graph-stage-loop-escapes', 'control_graph.py',
          '    except (OSError, RuntimeError, ValueError) as error:\n        reason = ',
          '    except (OSError, ValueError) as error:\n        reason = ', 'authority/stage-shapes')
    graph('graph-nul-path-judged', 'control_graph.py',
          "    if '\\x00' in os.fspath(path):\n", '    if False:\n', 'authority/stage-shapes')
    # Round 5 review: undriven behaviors, the reviewer's mutants (renamed graph-*), and new code.
    graph('graph-command-runs-removed', 'control_graph.py',
          "        pieces = value.split(' ')\n",
          '        pieces = []\n', 'runtime/pyvenv-clean')
    graph('graph-command-shlex-removed', 'control_graph.py',
          '            words = shlex.split(value)\n',
          '            words = []\n', 'runtime/pyvenv-clean')
    graph('graph-quote-strip-removed', 'control_graph.py',
          '    elif len(value) >= 2 and value[0] == value[-1] and value[0] in \'"\\\'\':\n',
          '    elif False:\n', 'runtime/pyvenv-clean')
    graph('graph-stage-written-place-dropped', 'control_graph.py',
          "    for place in (Path(os.path.abspath(runtime['stage'])), root):\n",
          '    for place in (root,):\n', 'authority/stage-shapes')
    graph('graph-stage-resolved-place-dropped', 'control_graph.py',
          "    for place in (Path(os.path.abspath(runtime['stage'])), root):\n",
          "    for place in (Path(os.path.abspath(runtime['stage'])),):\n", 'authority/stage-shapes')
    graph('graph-prefix-resolve-dropped', 'control_graph.py',
          'for base in (prefix, prefix.resolve())',
          'for base in (prefix,)', 'authority/stage-shapes')
    graph('graph-refused-workdir-kept', 'control_graph.py',
          "        _remove(path)\n        raise Refused('runtime_unavailable', 'the child working directory",
          "        raise Refused('runtime_unavailable', 'the child working directory", 'authority/stage-links')
    graph('graph-rebuild-message-dropped', 'control_graph.py',
          "'; '.join(problems) + '; rebuild it with: ' + REBUILD_COMMAND)",
          "'; '.join(problems))", 'runtime/pyvenv-clean')
    graph('graph-root-file-check-dropped', 'control_graph.py',
          "    if root.exists() and not root.is_dir():\n        raise Refused('runtime_unavailable', 'the stage root is not a directory')\n",
          '', 'authority/stage-shapes')
    graph('graph-option-values-unjudged', 'control_graph.py',
          "        words += [word.partition('=')[2] for word in words if word.startswith('-') and '=' in word]\n",
          '', 'runtime/pyvenv-clean')
    graph('graph-rebuild-no-restore', 'control_graph_install.py',
          '    except OSError:\n        os.rename(retired, target)\n        raise\n', '    except OSError:\n        raise\n',
          'runtime/rebuild-swap')
    graph('graph-rebuild-old-left', 'control_graph_install.py',
          '    if retired.is_symlink() or not retired.is_dir():\n        retired.unlink()\n    else:\n        shutil.rmtree(retired)\n',
          '', 'runtime/rebuild-swap')
    graph('graph-problems-repeated', 'control_graph.py',
          '    return list(dict.fromkeys(problems))\n', '    return problems\n', 'runtime/pyvenv-clean')
    graph('graph-shape-opinion-dropped', 'control_graph.py',
          '        if _shaped_like_repository(place) or any(git_finds_repository(start) for start in _discovery_starts(place)):\n',
          '        if any(git_finds_repository(start) for start in _discovery_starts(place)):\n', 'authority/stage-links')
    graph('graph-stage-oserror-unnamed', 'control_graph.py',
          "    except (OSError, RuntimeError, ValueError) as error:\n        reason = ",
          "    except FileNotFoundError as error:\n        reason = ",
          'authority/stage-shapes')
    graph('graph-staged-runner-shape-unchecked', 'control_graph.py',
          "    if target.exists() and not target.is_file():\n", "    if False:\n", 'authority/stage-shapes')
    graph('graph-stage-root-judged-resolved-only', 'control_graph.py',
          "    if inside_repository(runtime['stage']):\n", "    if inside_repository(root):\n", 'authority/stage-shapes')
    graph('graph-stage-inside-runtime-allowed', 'control_graph.py',
          "        if any(place == base or base in place.parents for base in (prefix, prefix.resolve())):\n",
          "        if False:\n", 'authority/stage-shapes')
    graph('graph-descriptors-in-parent-tmpdir', 'control_graph.py',
          'given, answer = tempfile.TemporaryFile(dir=work), tempfile.TemporaryFile(dir=work)',
          'given, answer = tempfile.TemporaryFile(), tempfile.TemporaryFile()', 'authority/no-direct-write')
    graph('graph-unserializable-escapes', 'control_graph.py',
          '    except (ValueError, TypeError, OverflowError, RecursionError) as error:\n'
          "        raise Refused('invalid_input', 'request cannot be serialized: ' + type(error).__name__) from error\n",
          '    except OverflowError as error:\n'
          "        raise Refused('invalid_input', 'request cannot be serialized: ' + type(error).__name__) from error\n",
          'shape/closed-request')
    graph('graph-pyvenv-unchecked', 'control_graph.py',
          '        raise Refused(\'runtime_unavailable\', \'the runtime cannot be judged: \' + str(error)[:120]) from error\n    if problems:\n',
          '        raise Refused(\'runtime_unavailable\', \'the runtime cannot be judged: \' + str(error)[:120]) from error\n    if False:\n',
          'runtime/pyvenv-clean')
    graph('graph-pyvenv-command-ignored', 'control_graph.py',
          "                if inside_repository(path):\n",
          "                if key.strip() != 'command' and inside_repository(path):\n", 'runtime/pyvenv-clean')
    graph('graph-pyvenv-values-split', 'control_graph.py',
          "    else:\n        words = [value]\n", "    else:\n        words = value.split()\n", 'runtime/pyvenv-clean')
    graph('graph-interpreter-final-hop-only', 'control_graph.py',
          '    for hop in visited_paths(python):\n', '    for hop in visited_paths(python)[-1:]:\n', 'runtime/pyvenv-clean')
    graph('graph-relative-link-misjoined', 'control_graph.py',
          "            if target.startswith('/'):\n                current = '/'\n",
          "            current = '/'\n", 'runtime/pyvenv-clean')
    graph('graph-repository-judged-resolved-only', 'control_graph.py',
          '    places = [os.path.abspath(path), visited_paths(path)[-1]]\n',
          '    places = [visited_paths(path)[-1]]\n', 'runtime/pyvenv-clean')
    graph('graph-answer-utf16-unguarded', 'control_graph.py',
          "        value = json.loads(text, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))\n"
          "    except RecursionError as error:\n"
          "        raise Refused('invalid_response', 'answer nests too deeply to parse') from error\n",
          "        value = json.loads(raw, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))\n",
          'shape/deep-answer')
    graph('graph-path-check-skips-keys', 'control_graph.py',
          '            stack.extend(item.keys())\n            stack.extend(item.values())\n',
          '            stack.extend(item.values())\n', 'shape/closed-request')
    graph('graph-request-size-unbounded', 'control_graph.py',
          'MAX_REQUEST_BYTES = 1 << 20\n', 'MAX_REQUEST_BYTES = 1 << 30\n', 'shape/closed-request')
    graph('graph-child-shares-session', 'control_graph.py',
          'close_fds=True, start_new_session=True)', 'close_fds=True, start_new_session=False)',
          'boundary/process-group')
    graph('graph-group-kept-on-exit', 'control_graph.py',
          '        try:\n            finished = _wait_unreaped(proc.pid, timeout)\n        finally:\n            _end_group(proc)\n',
          '        finished = _wait_unreaped(proc.pid, timeout)\n        if not finished:\n            _end_group(proc)\n'
          '        else:\n            proc.wait()\n        if True:\n', 'boundary/process-group')
    # VELDO-0037: each declared falsifier and a distinct second mutation turn the same named
    # row red; the gate additionally drives an unchanged copy. Two further rows get one each.
    def aliases(name, module, old, new, row):
        add(37, name, '59_veldo_0037_aliases.py', module, old, new, [row])

    aliases('alias-checkout-maximum', 'control_alias.py',
            "        number = kind['next']\n",
            "        number = 1 + maximum([p.relative_to(request['workspace']).as_posix()"
            " for p in Path(request['workspace']).rglob('*')], kind)\n", 'aliases/stale-checkouts')
    aliases('alias-counter-not-advanced', 'control_alias.py',
            'dict(kind, next=number + 1)', 'dict(kind, next=number)', 'aliases/stale-checkouts')
    aliases('document-ignore-digest', 'control_alias.py',
            "        if current['digest'] != p['expected_digest']:", '        if False:',
            'documents/stale-overwrite')
    aliases('document-current-version', 'control_alias.py',
            "            expected = request['expected_version']\n", '            expected = head_version\n',
            'documents/stale-overwrite')
    aliases('publication-altered-bytes', 'control_document.py',
            '                    output.write(body)\n                    output.flush()\n'
            '                    os.fsync(output.fileno())\n'
            '                observed = SN.digest(_read_at(parent, temporary, path))\n',
            "                    output.write(body + b'.')\n                    output.flush()\n"
            '                    os.fsync(output.fileno())\n                observed = digest\n',
            'publication/accepted-documents')
    aliases('publication-normalized-newlines', 'control_document.py',
            '                output.write(body)\n',
            "                output.write(body.replace(b'\\r\\n', b'\\n'))\n", 'publication/accepted-documents')
    aliases('reader-trusts-record', 'control_document.py',
            '    observed = SN.digest(body)\n', "    observed = obligation['observed_digest']\n",
            'publication/tampered-refused')
    # Review defects: every row gets its reintroducing mutation and a second, distinct one.
    aliases('publication-follow-parent-symlink', 'control_document.py',
            "_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)",
            "_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | getattr(os, 'O_CLOEXEC', 0)",
            'publication/no-symlink-escape')
    aliases('reader-follows-links', 'control_document.py',
            "        body = read_exact(os.path.realpath(root), data['path'])\n",
            "        body = (Path(root) / data['path']).read_bytes()\n", 'publication/no-symlink-escape')
    aliases('alias-overlap-unchecked', 'control_alias.py',
            '            if _meet(_items(data), _items(other)):', '            if False:', 'aliases/one-path-per-kind')
    aliases('alias-overlap-ignores-directories', 'control_alias.py',
            'def _meet(first, second, directories=True):', 'def _meet(first, second, directories=False):',
            'aliases/one-path-per-kind')
    aliases('alias-trusts-first-number', 'control_alias.py',
            '        elif first < floor:', '        elif False:', 'aliases/historical-floor')
    # Since the recorded-numbers fix the history is read once, at acceptance, by
    # control_readset.carrier_paths; this is the same defect at the code that now reads it: the
    # commit's tree listed instead of its history.
    aliases('alias-floor-ignores-history', 'control_readset.py',
            "    result = _git_process.run(['git', '-C', str(repo), 'log', *HISTORY_OPTIONS, '-z', '--format=', '--name-only',\n"
            "                                  '--ignore-missing', '--stdin', commit, '--'],",
            "    result = _git_process.run(['git', '-C', str(repo), 'ls-tree', '-r', '-z', '--name-only', commit],",
            'aliases/historical-floor')
    aliases('alias-owners-undeclared', 'control_alias.py',
            '    store.declare_owners(conn, OWNER, kinds=OWNED_KINDS, prefixes=OWNED_PREFIXES, module=__file__)', '    pass',
            'aliases/generic-writes-refused')
    aliases('store-owner-by-new-kind-only', 'control_store.py',
            '                hit = value in kinds if selector == "kind" else eid.startswith(value)',
            '                hit = selector == "kind" and value == new["kind"]', 'aliases/generic-writes-refused')
    aliases('publisher-any-repository', 'control_document.py',
            '            if repository != self.repository:', '            if False:', 'publication/bound-to-repository')
    aliases('reader-any-checkout', 'control_document.py',
            '    if enrolled_repository(root, store_file(conn), domain_uuid, verify, host_identity) != repository:',
            '    if False:', 'publication/bound-to-repository')
    aliases('record-trusts-supplied-digest', 'control_alias.py',
            "            visible = publisher.visible_digest(data['path'])", "            visible = p['observed_digest']",
            'publication/recorded-only-by-publisher')
    aliases('record-missing-file-accepted', 'control_alias.py',
            "        if visible is None:\n            self._refuse('missing_publication', '%s is not in the bound checkout' % data['path'])",
            "        if visible is None:\n            visible = data['digest']", 'publication/recorded-only-by-publisher')
    aliases('alias-prefix-case-sensitive', 'control_alias.py',
            "            if other['prefix'].casefold() == data['prefix'].casefold():",
            "            if other['prefix'] == data['prefix']:", 'aliases/case-insensitive-names')
    aliases('alias-paths-case-sensitive', 'control_alias.py',
            '    return [(frozenset(character), False) for character in text.casefold()]',
            '    return [(frozenset(character), False) for character in text]', 'aliases/case-insensitive-names')
    aliases('alias-reserved-unchecked', 'control_alias.py',
            '        problem = _reserved_problem(data)\n', '        problem = None\n', 'aliases/reserved-directories')
    aliases('alias-reserved-literal-only', 'control_alias.py',
            '            if _meet(items, _literal(name), directories=False):', '            if component == name:',
            'aliases/reserved-directories')
    aliases('alias-skip-unit-id', 'control_alias.py',
            "        problem = CLAIM.unit_id_problem(alias_for(data, data['next']))\n", '        problem = None\n',
            'aliases/invalid-unit-id')
    # Second review (2026-09-23): each row's reintroducing mutation, then a second, distinct one.
    # The history walk no longer narrows by a pathspec (it records every path holding a digit), so
    # the case-sensitive pathspec this replaced has no code left; the carrier pattern's case is
    # what now decides whether Specs/ counts for specs/.
    aliases('alias-floor-carrier-case-sensitive', 'control_alias.py',
            '    return re.compile(regex, re.IGNORECASE | re.DOTALL)', '    return re.compile(regex, re.DOTALL)',
            'aliases/floor-counts-every-carrier')
    aliases('alias-floor-slug-grammar', 'control_alias.py',
            "    regex += '([0-9]+)(?![0-9])[^/]*(?:/.*)?'",
            "    regex += '([0-9]+)(?![0-9])-[a-z0-9]+(?:-[a-z0-9]+)*[.][a-z]+'", 'aliases/floor-counts-every-carrier')
    aliases('store-owners-only-where-registered', 'control_store.py',
            '        owners = entity_owners(conn)\n', '        owners = entity_owners(conn) if conn.command_registry else []\n',
            'aliases/owned-on-every-connection')
    aliases('store-owners-unchecked', 'control_store.py',
            '                if hit and command["operation"] not in commands:', '                if False:',
            'aliases/owned-on-every-connection')
    aliases('store-owners-skip-registered-transitions', 'control_store.py',
            '        owners = entity_owners(conn)\n',
            '        owners = [] if "transaction_transition" in reg else entity_owners(conn)\n',
            'aliases/owned-whatever-registration-order')
    aliases('alias-floor-named-revision-only', 'control_alias.py',
            "        union = [path for record in records.values() for path in record['paths']]\n",
            "        union = list((records.get(accepted['commit']) or {}).get('paths', []))\n",
            'aliases/floor-from-every-accepted-revision')
    aliases('revision-regression-allowed', 'control_readset.py',
            "                if not _descends(repo, data['commit'], commit):", '                if False:',
            'aliases/floor-from-every-accepted-revision')
    aliases('publisher-infers-root-commits', 'control_document.py',
            '        repository = enrolled_repository(self.root, store_file(service.conn), service.domain_uuid, verify, host_identity)\n',
            '        repository = next((r for r, roots in service.identities.items() if roots == AL.root_commits(self.root)), None)\n',
            'publication/bound-by-enrollment')
    aliases('binding-signature-unchecked', 'control_document.py',
            '        problems = EN.verify_binding(root, binding, verify, host_identity, domain_uuid=domain_uuid)',
            '        problems = EN.verify_binding(root, binding, lambda message, signature: True, host_identity, domain_uuid=domain_uuid)',
            'publication/bound-by-enrollment')
    aliases('readset-snapshots-undeclared', 'control_readset.py',
            '    store.declare_owners(conn, OWNER, kinds=SNAPSHOT_KINDS, module=__file__)\n', '',
            'aliases/owned-whatever-registration-order')
    # Third review (2026-09-23): each row's reintroducing mutation, then distinct second ones.
    aliases('revision-any-repository', 'control_readset.py',
            '            if bound is None or not _holds(bound, commit):', '            if False:',
            'aliases/revision-in-enrolled-repository')
    aliases('enable-reads-unbound-repository', 'control_alias.py',
            '        if bound != os.path.realpath(self.paths[repository]):', '        if False:',
            'aliases/revision-in-enrolled-repository')
    aliases('repository-binding-unchecked', 'control_store.py',
            '            elif prior != target:', '            elif False:', 'aliases/revision-in-enrolled-repository')
    aliases('store-owner-by-name', 'control_store.py',
            '        if origin is not None:', '        if False:', 'aliases/owned-by-code-not-name')
    aliases('store-owner-ignores-digest', 'control_store.py',
            '    if module_digest(module) != digest:', '    if False:', 'aliases/owned-by-code-not-name')
    aliases('store-owner-outer-code-only', 'control_store.py',
            '        for cell in function.__closure__ or ():', '        for cell in ():', 'aliases/owned-by-code-not-name')
    aliases('owners-may-name-generic-commands', 'control_store.py',
            '            builtin = sorted(set(commands) & set(COMMAND_REGISTRY))', '            builtin = []',
            'aliases/owned-by-code-not-name')
    # Recorded numbers (2026-09-23): the floor reads what accept_revision recorded, and a revision
    # recorded before that rule whose commit is gone is refused by name, never skipped.
    aliases('floor-rederives-ignoring-record', 'control_alias.py',
            '            if commit in records:\n                continue\n', '', 'aliases/floor-from-recorded-numbers')
    aliases('legacy-lost-commit-skipped', 'control_alias.py',
            "            else:\n                self._refuse('accepted_revision_unavailable',",
            "            elif False:\n                self._refuse('accepted_revision_unavailable',", 'aliases/floor-from-recorded-numbers')
    aliases('acceptance-records-no-paths', 'control_readset.py',
            "'paths': carrier_paths(bound, commit, base)}}", "'paths': []}}",
            'aliases/floor-from-recorded-numbers')
    # Incremental records (2026-09-23): each record holds what its commit adds over every recorded
    # commit, and the floor reads the union of every record.
    aliases('floor-reads-current-records-only', 'control_alias.py',
            "        union = [path for record in records.values() for path in record['paths']]\n",
            "        union = [path for commit in commits if commit in records for path in records[commit]['paths']]\n",
            'aliases/records-hold-only-what-a-commit-adds')
    aliases('increment-against-head', 'control_readset.py',
            '                base = sorted(carrier_records(conn, self.domain_uuid, repository))',
            "                base = ['HEAD']", 'aliases/records-hold-only-what-a-commit-adds')
    aliases('named-revision-reads-git', 'control_alias.py',
            "        if named is not None:\n            roots = named['root_commits']",
            "        if False:\n            roots = named['root_commits']", 'aliases/records-hold-only-what-a-commit-adds')
    # Fourth check (2026-09-23): what acceptance reads does not follow repository configuration, an
    # increment after a lost recorded commit, and a shallow bound repository refused.
    aliases('history-merges-by-config', 'control_readset.py',
            "HISTORY_OPTIONS = ('--diff-merges=separate', '--root',", "HISTORY_OPTIONS = ('-m', '--root',",
            'aliases/history-read-whatever-repository-config')
    aliases('history-root-by-config', 'control_readset.py',
            "'--diff-merges=separate', '--root', '--no-renames',", "'--diff-merges=separate', '--no-renames',",
            'aliases/history-read-whatever-repository-config')
    aliases('increment-without-ignore-missing', 'control_readset.py',
            "'--ignore-missing', '--stdin', commit, '--'],", "'--stdin', commit, '--'],",
            'aliases/increment-after-a-lost-record')
    aliases('increment-ignores-recorded-base', 'control_readset.py',
            '                base = sorted(carrier_records(conn, self.domain_uuid, repository))', '                base = []',
            'aliases/increment-after-a-lost-record')
    aliases('shallow-accepted', 'control_readset.py',
            '    _require_complete_history(repo)\n', '', 'aliases/shallow-repository-refused')
    aliases('shallow-check-reads-bare', 'control_readset.py',
            "'rev-parse', '--is-shallow-repository'],", "'rev-parse', '--is-bare-repository'],",
            'aliases/shallow-repository-refused')
    # Fifth check (2026-09-23): a newline below the number, a gitlink under ignored submodules, and
    # a signed history under log.showSignature.
    aliases('alias-floor-carrier-single-line', 'control_alias.py',
            '    return re.compile(regex, re.IGNORECASE | re.DOTALL)', '    return re.compile(regex, re.IGNORECASE)',
            'aliases/floor-counts-every-carrier')
    # Sixth check (2026-09-23): a newline at every other carrier position the pattern reads.
    aliases('alias-floor-component-single-line', 'control_alias.py',
            "    regex += '([0-9]+)(?![0-9])[^/]*(?:/.*)?'", "    regex += '([0-9]+)(?![0-9])[^/\\n]*(?:/.*)?'",
            'aliases/floor-counts-every-carrier')
    aliases('alias-floor-prefix-single-line', 'control_alias.py',
            "        regex += '[^/]*?(?<![a-z0-9])' + re.escape(kind['prefix']) + '-'",
            "        regex += '[^/\\n]*?(?<![a-z0-9])' + re.escape(kind['prefix']) + '-'",
            'aliases/floor-counts-every-carrier')
    aliases('alias-floor-slug-directory-single-line', 'control_alias.py',
            "    return ''.join('[^/]*' if part == '{slug}' else re.escape(part)",
            "    return ''.join('[^/\\n]*' if part == '{slug}' else re.escape(part)",
            'aliases/floor-counts-every-carrier')
    aliases('history-submodules-by-config', 'control_readset.py',
            "'--no-relative', '--ignore-submodules=none',", "'--no-relative',",
            'aliases/gitlink-carrier-whatever-submodule-config')
    aliases('history-ignores-all-submodules', 'control_readset.py',
            "'--ignore-submodules=none',", "'--ignore-submodules=all',",
            'aliases/gitlink-carrier-whatever-submodule-config')
    aliases('history-signatures-by-config', 'control_readset.py',
            "'--no-notes', '--no-show-signature')", "'--no-notes')",
            'aliases/signed-history-whatever-signature-config')
    aliases('history-shows-signatures', 'control_readset.py',
            "'--no-notes', '--no-show-signature')", "'--no-notes', '--show-signature')",
            'aliases/signed-history-whatever-signature-config')
    # VELDO-0031: each declared falsifier and an independent defect per criterion.
    def claims(name, module, old, new, row):
        add(31, name, '58_veldo_0031_claims.py', module, old, new, ['claims/' + row])

    claims('claims-ownership-without-unit', 'control_claim.py',
           "'data': dict(u, state='CLAIMED')",
           "'data': dict(u, state=u['state'] if unit == 'unit' else 'CLAIMED')", 'atomic-activation')
    claims('claims-ownership-without-backlog', 'control_claim.py',
           "'data': dict(b, state='ACTIVE')",
           "'data': dict(b, state=b['state'] if unit == 'unit' else 'ACTIVE')", 'atomic-activation')
    claims('claims-ignore-use-generation', 'control_claim.py',
           "    if current.get('generation') != params['generation']:",
           "    if op != 'use' and current.get('generation') != params['generation']:", 'current-generation')
    claims('claims-ignore-use-holder', 'control_claim.py',
           "    if current.get('holder') != holder:",
           "    if op != 'use' and current.get('holder') != holder:", 'current-generation')
    claims('claims-uncertainty-as-contention', 'control_claim_client.py',
           "        if result.get('reason') in ('unanswerable', 'ownership_uncertain', 'missing_authority'):\n            raise CL.ClaimStopped(result['reason'])\n        return result",
           "        if result.get('reason') in ('unanswerable', 'ownership_uncertain', 'missing_authority'):\n            return {'ok': False, 'reason': 'claimed'}\n        return result", 'uncertainty-stop')
    claims('claims-detector-as-owned', 'control_claim.py',
           "        return 'unanswerable'",
           "        return 'owned'", 'uncertainty-stop')
    add(31, 'review-r1-command-crash', '59_veldo_0031_review.py', 'control_claim.py',
        '        if not isinstance(command, dict):\n            command = {}',
        '', ['claims/review-r1'])
    add(31, 'review-r1-signature-crash', '59_veldo_0031_review.py', 'control_claim.py',
        "                or not isinstance(packet.get('signature'), str)",
        '                or False', ['claims/review-r1'])
    add(31, 'review-r2-inspect-skips-consistency', '59_veldo_0031_review.py', 'control_claim.py',
        "            status = ownership(current, u['data'], b['data'])",
        "            status = 'owned' if current.get('holder') else 'unowned'", ['claims/review-r2'])
    add(31, 'review-r2-activation-without-owner', '59_veldo_0031_review.py', 'control_claim.py',
        "        return 'ownership_uncertain' if unit.get('state') in ACTIVE_UNIT_STATES else 'unowned'",
        "        return 'unowned'", ['claims/review-r2'])
    add(31, 'review-r6-private-stop-class', '59_veldo_0031_review.py', 'claim.py',
        'ClaimStopped = _claim_errors.ClaimStopped\n',
        '', ['claims/review-r6'])
    add(31, 'review-r6-routing-wrong-exception', '59_veldo_0031_review.py', 'control_claim_client.py',
        '            raise CL.ClaimStopped(exc.reason) from exc',
        '            raise RuntimeError(exc.reason) from exc', ['claims/review-r6'])
    add(31, 'review-r3-publish-without-use', '59_veldo_0031_review.py', 'lander.py',
        '                    self._check_ownership()',
        '                    pass  # omitted publication ownership check', ['claims/review-r3'])
    add(31, 'review-r3-swallow-heartbeat-stop', '59_veldo_0031_review.py', 'lander.py',
        '                self._hb_error = exc',
        '                self._hb_error = None', ['claims/review-r3'])
    add(31, 'review-r4-cwd-selects-enrollment', '59_veldo_0031_review.py', 'claim.py',
        '        ledgers = [claims_root(root)]',
        "        ledgers = [os.path.join(_enrollment_ledger() or os.sep, 'claims')]", ['claims/review-r4'])
    add(31, 'review-r4-refuse-unrelated-root', '59_veldo_0031_review.py', 'claim.py',
        "            if enrolled:\n                raise ClaimStopped('authority_required')",
        "            if enrolled or root:\n                raise ClaimStopped('authority_required')", ['claims/review-r4'])
    add(31, 'review-r5-expiry-revokes-owner', '59_veldo_0031_review.py', 'control_claim.py',
        "    if live == 'stale' and action in ('renew', 'release'):",
        '    if False:', ['claims/review-r5'])
    add(31, 'review-r5-release-ignores-holder', '59_veldo_0031_review.py', 'control_claim.py',
        "    if current.get('holder') != holder:",
        "    if op != 'release' and current.get('holder') != holder:", ['claims/review-r5'])
    # VELDO-0052: every declared falsifier and a second, different defect for its row, plus a
    # driven defect for every other row the suite asserts.
    def floor(name, module, old, new, row):
        add(52, name, '60_veldo_0052_eligibility.py', module, old, new, ['eligibility/' + row])

    review_gate = ('            decision = gate.decide("review", sid, context=context, ticket=unit.get("eligibility"))\n'
                   '            if not decision["eligible"]:\n'
                   '                return self._refused("review", sid, decision, verdict=None, shipped=False, landed=False)\n')
    floor('eligibility-review-bypass', 'dispatch.py', review_gate,
          '            pass  # defect: direct review launches without the shared review decision\n',
          'entry-dispatch-review')
    floor('eligibility-review-as-provider-request', 'dispatch.py',
          'gate.decide("review", sid, context=context,', 'gate.decide("provider_request", sid, context=context,',
          'entry-dispatch-review')
    floor('eligibility-status-only-recheck', 'control_eligibility.py',
          '        for label in sorted(set(before) | set(accepted)):',
          "        for label in ['unit']:  # defect: only the unit's own record, its current status",
          'stale-input')
    floor('eligibility-recheck-ignores-collections', 'control_eligibility.py',
          '            elif old != new:',
          "            elif 'members' not in (old or new or {}) and old != new:", 'stale-input')
    floor('eligibility-frontier-bypass', 'frontier.py',
          '            if not decision["eligible"]:\n                return\n',
          '            if False:\n                return\n', 'entry-frontier')
    floor('eligibility-executor-bypass', 'executor.py',
          '        return gate.decide("direct_execution", sid, context=self.context, ticket=ticket)',
          '        return dict(gate.decide("direct_execution", sid, context=self.context, ticket=ticket),\n'
          '                    eligible=True)  # defect: the direct executor ignores every refusal', 'entry-executor')
    floor('eligibility-plan-bypass', 'plan.py',
          '        reasons.extend("eligibility refused: %s" % r for r in decision["refusals"])',
          '        pass  # defect: the direct-execution refusals are dropped', 'entry-plan')
    floor('eligibility-build-bypass', 'dispatch.py',
          '            if not decision["eligible"]:\n                return self._refused("build", sid, decision, reviewed=False)',
          '            if False:\n                return self._refused("build", sid, decision, reviewed=False)',
          'entry-dispatch-build')
    floor('eligibility-publication-bypass', 'dispatch.py',
          '            if not decision["eligible"]:\n                return self._refused("publication",',
          '            if False:\n                return self._refused("publication",', 'entry-publication')
    floor('eligibility-work-no-preclaim-decision', 'work.py',
          '            if gate is not None and not gate.decide("claim", u["spec"], ticket=u.get("eligibility"))["eligible"]:\n'
          '                continue\n', '', 'entry-work-rechecks')
    floor('eligibility-work-no-postclaim-recheck', 'work.py',
          '                if not after["eligible"]:', '                if False:', 'entry-work-rechecks')
    floor('eligibility-enrolled-default-runs', 'control_eligibility.py',
          "        raise Stopped('eligibility_required')", '        return None', 'enrolled-entry-stops')
    floor('eligibility-unregistered-work-entry', 'control_eligibility.py',
          "    ('work.py', 'WorkLoop._claim_next', 'claim'),\n", '', 'registrations-from-call-sites')
    floor('eligibility-ignores-scope', 'control_eligibility.py',
          "            return [] if a.get('scope_digest') == data.get('scope_digest') and a.get('scope_digest') else ['stale_scope']",
          "            return []", 'named-refusals')
    floor('eligibility-refusals-not-pending', 'control_eligibility.py',
          "        self.last[decision['unit']] = outcome", "        self.last[decision['unit']] = 'accepted'",
          'observations')

    def completion(name, module, old, new, row):
        add(52, name, '60_veldo_0052_eligibility.py', module, old, new, ['completion/' + row])

    completion('completion-manifest-verdict-landed', 'work_state.py',
               '        facts = gate.completion(sid) if gate is not None else None',
               '        facts = (dict(gate.completion(sid), revision_landed=bool(concluded(entry, base, vc=vc, passing=passing)))\n'
               '                 if gate is not None else None)', 'readers-agree')
    completion('completion-frontier-reads-status-text', 'frontier.py',
               '    status = EL.completion_status(EL.gate_for(repo_root or ROOT, eligibility), _status_map(idx))',
               '    status = _status_map(idx)', 'readers-agree')
    completion('completion-any-revision-lands', 'control_eligibility.py',
               "            if CC.fact_problems('revision_landed', r, subject):",
               "            if CC.fact_problems('revision_landed', r, None):", 'readers-agree')
    completion('completion-unregistered-consumer', 'control_eligibility.py',
               "    ('work_state.py', 'completion_view'),\n", '', 'consumers-from-call-sites')

    def calls(name, old, new, row):
        add(52, name, '60_veldo_0052_eligibility.py', 'control_eligibility.py', old, new, ['reservations/' + row])

    invoke = "                receipt = guard.invoke(command_id or 'call/' + invocation, self.dispatch, invocation, boundary,"
    calls('reservation-review-follow-on-bypass', invoke,
          "                if self.station == 'review' and boundary == 'follow_on':\n"
          "                    guard.launch(invocation, configuration)  # defect: no reservation\n"
          "                    receipt = {'replayed': False}\n"
          "                else:\n  " + invoke, 'forbidden-call-observation')
    refused_call = ("                    raise  # a launch failure after its reservation: outcome unknown, exposure retained\n"
                    "                raise named from error")
    calls('reservation-refusal-fails-open', refused_call,
          "                    raise  # a launch failure after its reservation: outcome unknown, exposure retained\n"
          "                guard.launch(invocation, configuration)  # defect: a refused reservation still launches\n"
          "                receipt = {'replayed': False}", 'forbidden-call-observation')
    calls('reservation-retry-bypass', invoke,
          "                if boundary == 'retry':\n"
          "                    guard.launch(invocation, configuration)  # defect: retries skip the reservation\n"
          "                    receipt = {'replayed': False}\n"
          "                else:\n  " + invoke, 'unknown-usage-retained')
    # VELDO-0052, the 2026-09-23 review: each reproduced defect reintroduced, and a second, different
    # mutation for the same row.
    def review(name, module, old, new, row):
        add(52, name, '60_veldo_0052_eligibility.py', module, old, new, [row])

    review('enrolled-git-error-reads-unenrolled', 'control_eligibility.py',
           "        if _claims_a_repository(repo_root):\n            raise Stopped('enrollment_unanswerable') from error\n"
           "        return False\n",
           "        return False  # defect: any git error reads as not enrolled\n",
           'eligibility/enrollment-git-error-stops')
    review('enrolled-discovery-ignores-ancestors', 'git_process.py',
           "        parent = os.path.dirname(current)\n        if parent == current:\n            return False\n",
           "        return False  # defect: discovery looks only at the directory it was given\n",
           'eligibility/enrollment-git-error-stops')
    review('standalone-lane-reads-front-matter', 'frontier.py',
           '    return fm.get("lane") == "standalone" and _lane_status(fm, status) == "ready"',
           '    return fm.get("lane") == "standalone" and fm.get("status") == "ready"',
           'completion/landed-units-not-reoffered')
    review('review-lane-reads-front-matter', 'frontier.py',
           '        if _lane_status(fm, status) == "review":',
           '        if fm.get("status") == "review":',
           'completion/landed-units-not-reoffered')
    review('status-reader-reads-status-text', 'runstatus.py',
           '        status_by_id = PL._status(eligibility)',
           '        status_by_id = PL.spec_status_by_id()',
           'completion/status-reader-agrees')
    review('status-reader-drops-the-stop', 'runstatus.py',
           '    except EL.Stopped as stop:\n        return [], stop.reason',
           '    except EL.Stopped as stop:\n        return [], None  # defect: the stop reads as an empty burn-down',
           'completion/status-reader-agrees')
    # VELDO-0054 review A: veldo status reads decisions through the Gate, as plan status does.
    review('status-reader-decisions-inline', 'runstatus.py',
           "            blocked = PL._decision_blocks(fm, PL.EL.gate_for(Path(root), eligibility))\n", "            blocked = PL._decision_blocks(fm)\n", 'completion/status-reader-agrees')
    review('status-reader-decisions-dropped', 'runstatus.py',
           "            blocked = PL._decision_blocks(fm, PL.EL.gate_for(Path(root), eligibility))\n", "            blocked = {}\n", 'completion/status-reader-agrees')
    review('dispatch-without-identity', 'control_eligibility.py',
           '        dispatch = self.open_dispatch(unit, context=context)\n',
           "        dispatch = (context or {}).get('dispatch')  # defect: an identity nobody reserved\n",
           'reservations/work-loop-dispatch-identity')
    review('dispatch-identity-not-reserved', 'control_eligibility.py',
           "                self._reservations().reserve_worker('worker/' + dispatch, dispatch, self.account, project, unit,\n"
           "                                                    now=self.clock())",
           "                pass  # defect: an identity no worker slot was reserved for",
           'reservations/work-loop-dispatch-identity')
    review('executor-launches-unreserved', 'executor.py',
           '            if self.calls is None:\n'
           '                # The dispatcher stops here in the same situation: nothing launches unreserved.\n'
           '                raise EL.Stopped("reservation_required")\n',
           '            if self.calls is None:\n'
           '                gate = None  # defect: run on with no reservation handle and no later station\n',
           'eligibility/executor-station-decisions')
    review('executor-review-skips-review-station', 'executor.py',
           '            context = dict(self.context, reviewer=getattr(self.hooks, "reviewer_identity", None))\n'
           '            return gate.decide("review", sid, context=context, ticket=ticket)\n',
           '            return gate.decide("direct_execution", sid, context=self.context, ticket=ticket)  # defect\n',
           'eligibility/executor-station-decisions')
    recheck = '            current = self._decide(gate, sid, launch, decision)\n'
    review('executor-decides-once', 'executor.py', recheck,
           '            current = decision if launch == "build" else self._decide(gate, sid, launch, decision)  # defect\n',
           'eligibility/executor-rechecks-every-launch')
    review('executor-recheck-without-ticket', 'executor.py', recheck,
           '            current = self._decide(gate, sid, launch, None)  # defect: the recheck forgets what it consumed\n',
           'eligibility/executor-rechecks-every-launch')
    review('entry-gate-not-built', 'control_eligibility.py',
           '    return enrolled_gate(repo_root, trust, observe=observe)\n',
           "    raise Stopped('eligibility_required')  # defect: the production entries build no Gate\n",
           'eligibility/production-entries-build-the-gate')
    review('entry-gate-unverified-binding', 'control_eligibility.py',
           "    if problems:\n        raise Stopped('enrollment_refused:' + problems[0][0])\n",
           "    if False:  # defect: a binding that does not verify still builds a Gate\n"
           "        raise Stopped('enrollment_refused:' + problems[0][0])\n",
           'eligibility/production-entries-build-the-gate')
    # VELDO-0052, the second independent check (r52b): defect g reintroduced, and different defects
    # of the same row (a returned launch keeps its slot; closing forgets the calls' exposure).
    review('slot-opened-before-prelaunch-halts', 'dispatch.py',
           '            if self._calls is None:\n                raise EL.Stopped("reservation_required")\n'
           '            # The executor launches the build',
           '            if self._calls is None:\n                raise EL.Stopped("reservation_required")\n'
           '            self._calls.open_dispatch(sid, context=context)  # defect: reserved before the halts, never retired\n'
           '            # The executor launches the build',
           'reservations/dispatch-slot-retired')
    review('slot-kept-after-launch-returns', 'control_eligibility.py',
           "            raise\n        self.close_dispatch(dispatch, 'completed')\n",
           "            raise\n        # defect: a launch that returned normally keeps its worker slot\n",
           'reservations/dispatch-slot-retired')
    review('slot-close-zeroes-exposure', 'control_eligibility.py',
           "                                   final=True, now=self.clock())",
           "                                   final=True, outcome='not_executed', now=self.clock())  # defect",
           'reservations/dispatch-slot-retired')
    # Defect h reintroduced (a signers file inside the workspace vouches for it), then a relative path
    # accepted, and the containment judged on the unresolved path, so a symlink leads back inside.
    review('trust-accepts-workspace-signers', 'control_eligibility.py',
           "        if any(os.path.commonpath([resolved, area]) == area for area in _workspace_areas(workspace)):\n"
           "            raise Stopped('host_trust_refused:signers_inside_workspace')\n",
           "        pass  # defect: the workspace's own signers file vouches for the workspace\n",
           'eligibility/host-trust-outside-workspace')
    review('trust-accepts-relative-signers', 'control_eligibility.py',
           "        if not os.path.isabs(enrollment_signers):\n"
           "            raise Stopped('host_trust_refused:signers_not_absolute')\n",
           "        pass  # defect: a relative signers path resolves against the process's directory\n",
           'eligibility/host-trust-outside-workspace')
    review('trust-judges-unresolved-path', 'control_eligibility.py',
           "        resolved = os.path.realpath(self.enrollment_signers)\n",
           "        resolved = os.path.abspath(self.enrollment_signers)  # defect: symlinks not followed\n",
           'eligibility/host-trust-outside-workspace')
    # A refusal inside a launch escapes Executor.run again (the defect reintroduced), escapes the
    # dispatcher's review as an error, or halts without the name of what refused.
    review('provider-refusal-escapes-run', 'executor.py',
           '            except EL.Refused as error:\n                codes = "; ".join(',
           '            except EL.Refused as error:\n                if opened:\n'
           '                    raise  # defect: a refusal inside the launch escapes run()\n                codes = "; ".join(',
           'eligibility/provider-refusal-halts')
    review('provider-refusal-escapes-review', 'dispatch.py',
           '                    rv = self._reviewer.review(spec, unit, calls=handle) or {}\n',
           '                    try:\n                        rv = self._reviewer.review(spec, unit, calls=handle) or {}\n'
           '                    except EL.Refused as inner:\n'
           '                        raise RuntimeError(inner.code)  # defect: the refusal escapes as an error\n',
           'eligibility/provider-refusal-halts')
    review('provider-refusal-halt-unnamed', 'executor.py',
           '                        else "reservation refused before %s: %s") % (launch, codes)',
           '                        else "reservation refused before %s: %s") % (launch, "refused")  # defect',
           'eligibility/provider-refusal-halts')
    # r52b probe i: a launch entered without the boundary its calls face (reintroduced), or with that
    # boundary decided for the first cycle only.
    review('launch-skips-call-boundary', 'executor.py',
           '            if current["eligible"]:\n                boundary = self._decide_calls(',
           '            if False:  # defect: the builder is entered whatever its calls will be told\n'
           '                boundary = self._decide_calls(',
           'eligibility/launch-decides-its-calls')
    review('launch-call-boundary-first-cycle-only', 'executor.py',
           '            if current["eligible"]:\n                boundary = self._decide_calls(',
           '            if current["eligible"] and cycle == 1:  # defect\n                boundary = self._decide_calls(',
           'eligibility/launch-decides-its-calls')
    # VELDO-0053: architecture at every eligibility entry. Each declared falsifier, a second and
    # different defect of its row, and a driven defect for every other row the suite asserts.
    def architecture(name, module, old, new, rows):
        add(53, name, '60_veldo_0053_architecture.py', module, old, new, ['architecture/' + r for r in rows])

    IDENTITY = "            found['validator'] = {module: dict(entry) for module, entry in snapshot.identity.items()}"
    SEAM = "        return self.validate.entry_contract(workspace, required, arch=self.arch)"

    architecture('architecture-malformed-as-optional-absence', 'control_eligibility.py',
                 "        found.update(kind=load.kind, state=load.state, required=load.required,\n",
                 "        if load.kind == 'parse_failure':  # defect: a present malformed contract read as optional absence\n"
                 "            load = load._replace(state='absent', kind='optional_absence', problems=(), required=False)\n"
                 "        found.update(kind=load.kind, state=load.state, required=load.required,\n",
                 ['ready-refusal'])
    loader_parse = ('        kind = "unreadable" if getattr(e, "kind", None) == "unreadable" else "parse_failure"\n'
                    '        return ContractLoad(CONTRACT_INVALID, kind, arch, None, (str(e),), str(p), req)\n')
    architecture('architecture-loader-malformed-as-absence', 'contract_loader.py', loader_parse,
                 loader_parse.replace('        return ContractLoad(CONTRACT_INVALID',
                                      '        if kind == "parse_failure":  # defect: the shared loader reads malformed as absence\n'
                                      '            return ContractLoad(CONTRACT_ABSENT, "optional_absence", None, None, (), str(p), False)\n'
                                      '        return ContractLoad(CONTRACT_INVALID'),
                 ['ready-refusal', 'state-kinds'])
    architecture('architecture-loader-wrong-type-as-absence', 'contract_loader.py',
                 '    if not p.is_file():\n        # PRESENT AND NEVER OPENED',
                 '    if not p.is_file():\n'
                 '        return ContractLoad(CONTRACT_ABSENT, "optional_absence", None, None, (), str(p), False)  # defect\n'
                 '        # PRESENT AND NEVER OPENED',
                 ['ready-refusal', 'state-kinds'])
    architecture('architecture-review-skipped', 'control_eligibility.py',
                 "                      for s in FLOOR_STATIONS}\n# The refusal each refused architecture kind",
                 "                      for s in FLOOR_STATIONS}\n"
                 "STATION_PREDICATES['review'] = tuple(p for p in STATION_PREDICATES['review'] if p != ARCHITECTURE_PREDICATE)"
                 "  # defect: direct review skips the architecture\n# The refusal each refused architecture kind",
                 ['forbidden-review-launch'])
    architecture('architecture-review-decision-skips', 'control_eligibility.py',
                 "                    if name == ARCHITECTURE_PREDICATE:\n",
                 "                    if name == ARCHITECTURE_PREDICATE and station == 'review':\n"
                 "                        continue  # defect: the review decision never asks the architecture\n"
                 "                    if name == ARCHITECTURE_PREDICATE:\n",
                 ['forbidden-review-launch'])
    architecture('architecture-invalid-structure-passes', 'control_eligibility.py',
                 "        if load.refused:\n            found['refusals']",
                 "        if load.refused and load.kind != 'invalid_structure':  # defect: only unreadable input refuses\n"
                 "            found['refusals']",
                 ['entries-blocked'])
    architecture('architecture-record-not-required', 'control_eligibility.py',
                 "snapshot.contract(self.workspace, True if accepted else None)",
                 "snapshot.contract(self.workspace, None)  # defect: acceptance no longer makes the contract required",
                 ['entries-blocked', 'substitution'])
    architecture('architecture-provider-request-unasked', 'control_eligibility.py',
                 "STATION_PREDICATES = {s: tuple(dict.fromkeys(('admission_current', ARCHITECTURE_PREDICATE) + tuple(CC.ENTRY_PREDICATES[s])))",
                 "STATION_PREDICATES = {s: tuple(dict.fromkeys(('admission_current',) + ((ARCHITECTURE_PREDICATE,) if s != 'provider_request'"
                 " else ()) + tuple(CC.ENTRY_PREDICATES[s])))",
                 ['registrations', 'entries-blocked'])
    architecture('architecture-clone-validator', 'control_eligibility.py',
                 "            self._validator = ValidatorSnapshot()\n",
                 "            self._validator = ValidatorSnapshot(os.path.join(self.workspace, '.veldo'))"
                 "  # defect: the workspace's own validator judges the workspace\n",
                 ['substitution'])
    architecture('architecture-accepted-digest-ignored', 'control_eligibility.py',
                 "        elif accepted and parsed != accepted['digest']:",
                 "        elif False:  # defect: whatever bytes are at the path are the accepted architecture",
                 ['substitution'])
    architecture('architecture-identity-from-workspace', 'control_eligibility.py',
                 IDENTITY,
                 "            found['validator'] = {module: {'path': os.path.join(self.workspace, '.veldo', os.path.basename(entry['path'])),\n"
                 "                                           'digest': entry['digest']}\n"
                 "                                  for module, entry in snapshot.identity.items()}  # defect: names what the workspace carries",
                 ['substitution'])
    architecture('architecture-identity-not-recorded', 'control_eligibility.py',
                 "        if decision.get('architecture'):\n",
                 "        if False:  # defect: the decision's architecture is not in its observation\n",
                 ['observations'])
    architecture('architecture-unaccepted-record-accepted', 'control_eligibility.py',
                 "        if accepted and (not isinstance(record, dict) or record.get('state') != 'accepted'",
                 "        if accepted and (not isinstance(record, dict)",
                 ['record-states'])
    # Review fix: a Gate with no workspace never passes, record or no record.
    architecture('architecture-store-only-passes', 'control_eligibility.py',
                 "            found['basis'] = 'store_only'\n            found['refusals'] = ['missing_evidence:architecture/workspace']\n",
                 "            found['basis'] = 'store_only'\n"
                 "            if accepted:  # defect: without a record a store-only Gate passes\n"
                 "                found['refusals'] = ['missing_evidence:architecture/workspace']\n",
                 ['store-only-refuses'])
    architecture('architecture-store-only-reads-cwd', 'control_eligibility.py',
                 "        self.workspace = str(workspace) if workspace is not None else None\n",
                 "        self.workspace = str(workspace) if workspace is not None else os.getcwd()  # defect: the process directory\n",
                 ['store-only-refuses'])
    # Review fix: the Gate judges only through validate.py's public entry_contract.
    architecture('architecture-private-seam', 'control_eligibility.py', SEAM,
                 "        return self.validate._VC.entry_contract(workspace, required, arch=self.arch)  # defect: around the public name",
                 ['public-seam'])
    snapshot_load = ("        spec = self._named('eligibility_validator_snapshot', 'validate')\n"
                     "        module = importlib.util.module_from_spec(spec)\n"
                     "        spec.loader.exec_module(module)\n"
                     "        self.validate, self.arch = module, module.entry_validator()\n")
    architecture('architecture-validate-checks-direct', 'control_eligibility.py', snapshot_load,
                 snapshot_load.replace("'validate')", "'validate_checks')")
                 .replace("        self.validate, self.arch = module, module.entry_validator()\n",
                          "        module.parse_yamlish = module._Y.parse  # defect: around validate.py\n"
                          "        self.validate, self.arch = module, module._arch_module()\n"),
                 ['public-seam'])
    # Review fix: the snapshot runs from the bytes in memory; no copy on disk stands between digest and code.
    architecture('architecture-snapshot-private-copy', 'control_eligibility.py', snapshot_load,
                 "        import tempfile  # defect: a private copy on disk, loaded after it is written\n"
                 "        with tempfile.TemporaryDirectory(prefix='veldo-validator-') as private:\n"
                 "            engine = Path(private) / '.veldo'\n"
                 "            engine.mkdir()\n"
                 "            for held, body in self._bodies.items():\n"
                 "                (engine / (held + '.py')).write_bytes(body)\n"
                 "            spec = importlib.util.spec_from_file_location('eligibility_validator_snapshot', str(engine / 'validate.py'))\n"
                 "            module = importlib.util.module_from_spec(spec)\n"
                 "            spec.loader.exec_module(module)\n"
                 "            self.validate, self.arch = module, module.entry_validator()\n",
                 ['snapshot-in-memory'])
    architecture('architecture-siblings-from-disk', 'control_eligibility.py',
                 "        util.spec_from_file_location = self._spec\n",
                 "        pass  # defect: a sibling loaded by path is read from disk\n",
                 ['snapshot-in-memory'])
    # Review fix: the identity is taken once, from the bytes loaded, and every decision records that.
    architecture('architecture-identity-read-at-decision', 'control_eligibility.py', IDENTITY,
                 "            found['validator'] = {module: {'path': entry['path'], 'digest': 'sha256:' + hashlib.sha256(\n"
                 "                Path(entry['path']).read_bytes()).hexdigest()} for module, entry in snapshot.identity.items()}"
                 "  # defect: the files on disk now, not the bytes that ran",
                 ['identity-is-what-ran'])
    architecture('architecture-validator-reexecuted-per-call', 'control_eligibility.py', SEAM,
                 "        return self.validate.entry_contract(workspace, required, arch=_organ('arch'))"
                 "  # defect: the structural validator re-executed from disk at every call",
                 ['identity-is-what-ran'])
    architecture('architecture-snapshot-per-decision', 'control_eligibility.py',
                 "        if self._validator is None:\n            self._validator = ValidatorSnapshot()\n",
                 "        if True:  # defect: a new snapshot for every decision\n            self._validator = ValidatorSnapshot()\n",
                 ['identity-is-what-ran'])
    # Review fix: the digest compared is the loader's, of the very bytes it parsed.
    architecture('architecture-digest-second-read', 'control_eligibility.py',
                 "        elif accepted and parsed != accepted['digest']:",
                 "        elif accepted and 'sha256:' + hashlib.sha256(Path(load.path).read_bytes()).hexdigest() != accepted['digest']:"
                 "  # defect: a second read",
                 ['validated-is-digested'])
    reported = ("    if digested is not None:\n        digested(body_digest)\n    problems = []\n"
                "    arch.validate_contract(data, base, p, lambda _where, msg: (problems.append(msg), 1)[1])\n")
    architecture('architecture-loader-digest-second-read', 'contract_loader.py', reported,
                 "    problems = []\n    arch.validate_contract(data, base, p, lambda _where, msg: (problems.append(msg), 1)[1])\n"
                 "    if digested is not None:\n"
                 "        digested(arch.read_contract(p, parse)[1])  # defect: the digest of a second read, after validation\n",
                 ['validated-is-digested'])
    # Review fix: bytes that are not UTF-8 are a named parse failure with their digest.
    decode = ('    try:\n        text = io.TextIOWrapper(io.BytesIO(body), encoding="utf-8").read()\n'
              '    except UnicodeDecodeError as e:\n'
              '        raise ArchContractError("architecture contract is not UTF-8 text: %s" % e, digest=digest)\n')
    architecture('architecture-decode-outside-refusal', 'arch.py', decode,
                 '    text = io.TextIOWrapper(io.BytesIO(body), encoding="utf-8").read()  # defect: decoded outside the refusal\n',
                 ['not-text-refused'])
    # defect: a lossy decode replaces what is not UTF-8 and parses the rest
    architecture('architecture-decode-lossy', 'arch.py', 'io.TextIOWrapper(io.BytesIO(body), encoding="utf-8")',
                 'io.TextIOWrapper(io.BytesIO(body), encoding="utf-8", errors="replace")',
                 ['not-text-refused'])
    # Review fix (round 4, the lead's design): the snapshot is keyed by module NAME, never by a path; a name
    # not held is the named stop ImportError, recorded in the durable stop event.
    by_name = "        return self._named(name, file_name[:-3] if file_name.endswith('.py') else '')\n"
    architecture('architecture-snapshot-disk-fallback', 'control_eligibility.py', by_name,
                 "        held = file_name[:-3] if file_name.endswith('.py') else ''\n"
                 "        if held not in self._bodies:\n"
                 "            return importlib.util.spec_from_file_location(name, location, *args, **kwargs)  # defect: a miss read from disk\n"
                 "        return self._named(name, held)\n",
                 ['snapshot-by-name'])
    architecture('architecture-snapshot-keyed-by-path', 'control_eligibility.py', by_name,
                 "        by_path = {}\n"
                 "        for held in self._bodies:\n"
                 "            by_path[str(self._installed / (held + '.py'))] = held\n"
                 "            by_path[os.path.realpath(str(self._installed / (held + '.py')))] = held\n"
                 "        where = str(location) if location is not None else ''\n"
                 "        return self._named(name, by_path.get(os.path.abspath(where)) or by_path.get(os.path.realpath(where)) or '')"
                 "  # defect: keyed by path\n",
                 ['snapshot-by-name'])
    architecture('architecture-stop-error-unrecorded', 'control_eligibility.py',
                 "            if found.get('error'):\n                # The durable stop event",
                 "            if False:  # defect: the stop event does not name its error\n                # The durable stop event",
                 ['snapshot-by-name'])
    # Review fix: the bytes compiled are the bytes digested (a writer lands between the one read and the compile).
    architecture('architecture-exec-rereads-disk', 'control_eligibility.py',
                 "exec(compile(self.body, key, 'exec', dont_inherit=True), module.__dict__)",
                 "exec(compile(Path(module.__spec__.origin).read_bytes(), key, 'exec', dont_inherit=True),"
                 " module.__dict__)  # defect: compiled from a second read of the disk",
                 ['snapshot-in-memory'])
    architecture('architecture-arch-digest-reread', 'control_eligibility.py',
                 "        self.snapshot._executed[self.held] = 'sha256:' + hashlib.sha256(self.body).hexdigest()\n",
                 "        self.snapshot._executed[self.held] = 'sha256:' + hashlib.sha256(\n"
                 "            self.body if self.held != 'arch' else (self.snapshot._installed / 'arch.py').read_bytes()).hexdigest()"
                 "  # defect: arch.py digested from a second read\n",
                 ['snapshot-in-memory'])
    # Review fix: tracebacks and inspect show the code that ran.
    seed = ("        linecache.cache[key] = (len(self.body), None, importlib.util.decode_source(self.body).splitlines(True),"
            " key)\n")
    architecture('architecture-linecache-unseeded', 'control_eligibility.py', seed,
                 "        pass  # defect: linecache reads the file on disk by name\n", ['snapshot-source'])
    architecture('architecture-linecache-mtime-checked', 'control_eligibility.py', seed,
                 seed.replace("(len(self.body), None,", "(len(self.body), os.stat(module.__spec__.origin).st_mtime,")
                 .rstrip("\n") + "  # defect: checkcache drops it after an edit\n", ['snapshot-source'])
    architecture('architecture-get-source-missing', 'control_eligibility.py',
                 "        return importlib.util.decode_source(self.body)\n",
                 "        return None  # defect: the loader hands back no source\n", ['snapshot-source'])
    # Round 4: snapshot lines are kept under a key no other loader uses, unique to each snapshot.
    architecture('architecture-linecache-keyed-by-path', 'control_eligibility.py',
                 "        key = self.snapshot.source_key(self.held)\n",
                 "        key = str(self.snapshot._installed / (self.held + '.py'))  # defect: the installed path, shared\n",
                 ['snapshot-source'])
    architecture('architecture-linecache-key-shared', 'control_eligibility.py',
                 "        return '<veldo validator snapshot %s: %s>' % (self._id, self._installed / (held + '.py'))\n",
                 "        return '<veldo validator snapshot: %s>' % (self._installed / (held + '.py'))  # defect: one key for every snapshot\n",
                 ['snapshot-source'])
    # Round 5: the recorded identity is every held module the snapshot executes, not a fixed list.
    executed = ("        return {held: {'module': held, 'role': ROLE_LABELS.get(held), 'path': str(self._installed / (held + '.py')),\n"
                "                       'digest': digest}\n"
                "                for held, digest in self._executed.items()}\n")
    architecture('architecture-identity-static-five', 'control_eligibility.py', executed,
                 "        return {name[:-3]: {'module': name[:-3], 'role': role, 'path': str(self._installed / name),\n"
                 "                            'digest': 'sha256:' + hashlib.sha256(self._bodies[name[:-3]]).hexdigest()}\n"
                 "                for role, name in VALIDATOR_ROLES}  # defect: the hand-written list of five\n",
                 ['identity-covers-what-ran'])
    architecture('architecture-identity-roles-only', 'control_eligibility.py', executed,
                 executed.replace("for held, digest in self._executed.items()}",
                                  "for held, digest in self._executed.items() if held in ROLE_LABELS}  # defect: labelled modules only"),
                 ['identity-covers-what-ran'])
    # Round 6: the identity is keyed by module name; a file named after a role label takes no other module's place.
    architecture('architecture-identity-keyed-by-role', 'control_eligibility.py', executed,
                 executed.replace("        return {held: {'module': held,", "        return {ROLE_LABELS.get(held, held): {'module': held,")
                 .rstrip("\n") + "  # defect: keyed by role label\n",
                 ['identity-keyed-by-module'])
    architecture('architecture-identity-role-named-dropped', 'control_eligibility.py', executed,
                 executed.replace("for held, digest in self._executed.items()}",
                                  "for held, digest in self._executed.items()\n"
                                  "                if held not in ROLE_LABELS.values()}  # defect: a module named after a role is left out"),
                 ['identity-keyed-by-module'])
    # Round 5: only a non-empty module name is held and only a regular file is read.
    architecture('architecture-snapshot-holds-empty-name', 'control_eligibility.py',
                 " for path in sorted(installed.glob('*.py')) if path.name[:-3]}",
                 " for path in sorted(installed.glob('*.py'))}  # defect: a file named .py is held under the empty name",
                 ['snapshot-held-names'])
    architecture('architecture-snapshot-request-any-suffix', 'control_eligibility.py',
                 "        return self._named(name, file_name[:-3] if file_name.endswith('.py') else '')\n",
                 "        return self._named(name, os.path.splitext(file_name)[0])  # defect: any suffix names a held module\n",
                 ['snapshot-held-names'])
    architecture('architecture-snapshot-reads-any-file', 'control_eligibility.py',
                 "        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):\n",
                 "        if False:  # defect: a FIFO or other non-regular file is read like a file\n",
                 ['snapshot-held-names'])
    architecture('architecture-snapshot-blocking-read', 'control_eligibility.py',
                 "_read_engine_file(path) for path in sorted(installed.glob('*.py'))",
                 "path.read_bytes() for path in sorted(installed.glob('*.py'))",
                 ['snapshot-held-names'])
    # Round 6: a held file is read up to the stated limit and no further; one over it is the named stop.
    bounded_read = "        body = handle.read(ENGINE_FILE_LIMIT + 1)\n"
    over_limit = "    if len(body) > ENGINE_FILE_LIMIT:\n"
    architecture('architecture-snapshot-read-unbounded', 'control_eligibility.py', bounded_read,
                 "        body = handle.read()  # defect: the whole file is read before its length is judged\n",
                 ['snapshot-file-bounded'])
    architecture('architecture-snapshot-read-limit-short', 'control_eligibility.py', bounded_read,
                 "        body = handle.read(ENGINE_FILE_LIMIT)  # defect: a longer file is cut to the limit and held\n",
                 ['snapshot-file-bounded'])
    architecture('architecture-snapshot-length-unjudged', 'control_eligibility.py', over_limit,
                 "    if False:  # defect: a file over the limit is held\n",
                 ['snapshot-file-bounded'])
    architecture('architecture-snapshot-limit-exclusive', 'control_eligibility.py', over_limit,
                 "    if len(body) >= ENGINE_FILE_LIMIT:  # defect: a file of exactly the limit is refused\n",
                 ['snapshot-file-bounded'])
    # Round 5 pins: __file__ is the installed path of the name, and linecache is seeded before a module runs.
    origin = "origin=str(self._installed / (held + '.py')))\n"
    architecture('architecture-snapshot-file-resolved', 'control_eligibility.py', origin,
                 "origin=os.path.realpath(str(self._installed / (held + '.py'))))  # defect: the link's target\n",
                 ['snapshot-module-files'])
    architecture('architecture-snapshot-file-is-key', 'control_eligibility.py', origin,
                 "origin=self.source_key(held))  # defect: __file__ is the snapshot's cache key, not the installed path\n",
                 ['snapshot-module-files'])
    load_block = (seed + "        self.snapshot._keys.append(key)\n"
                  "        # Recorded before the module runs. A module whose load raises stays in the identity only when the module\n"
                  "        # loading it catches the error; a raise out of the snapshot refuses the decision with validator {}.\n"
                  "        self.snapshot._executed[self.held] = 'sha256:' + hashlib.sha256(self.body).hexdigest()\n"
                  "        exec(compile(self.body, key, 'exec', dont_inherit=True), module.__dict__)\n")
    architecture('architecture-linecache-seeded-after-load', 'control_eligibility.py', load_block,
                 load_block.replace(seed, "").rstrip("\n") + "  # defect: lines cached only after the module ran\n" + seed,
                 ['snapshot-module-files'])
    architecture('architecture-linecache-seeded-for-roles-only', 'control_eligibility.py', seed,
                 "        if self.held in ROLE_LABELS:  # defect: only the labelled modules' lines are cached\n    " + seed,
                 ['snapshot-module-files'])
    # VELDO-0046: retained Release 1 criteria, two independent defects per named row.
    def notification(name, old, new, row):
        add(46, name, '58_veldo_0046_notifications.py', 'control_notify.py',
            old, new, ['notify/' + row])

    notification('notify-stop-after-handler-failure',
                 "                self._observe('handler', event, 'unknown_outcome', stopped_consumer=consumer)",
                 "                return self._observe('handler', event, 'unknown_outcome', stopped_consumer=consumer)",
                 'subscriber-isolation')
    notification('notify-retry-successful-subscribers',
                 "        return self._observe('consume', event, 'unknown_outcome' if failed else 'delivered',",
                 "        if failed:\n            entry.owed = None  # defective: forget who accepted\n"
                 "        return self._observe('consume', event, 'unknown_outcome' if failed else 'delivered',", 'subscriber-isolation')
    notification('notify-drop-unavailable-first-attempt',
                 "if entry.owed is None and exc.reason != 'service_unavailable':",
                 "if entry.owed is None:", 'first-attempt-retained')
    # At-most-once: the subscriber is marked accepted before its callback returns.
    _dispatch = (
                 '        for consumer in ready:\n'
                 '            try:\n'
                 '                # A handler may mutate its argument; the next handler still sees the journal.\n'
                 '                self.handlers[consumer](json.loads(json.dumps(event)))\n'
                 '            except BaseException as exc:\n'
                 '                # The event stays owed to this subscriber, and to any not yet called, even\n'
                 '                # when an interrupt propagates. Only this subscriber waits out a delay.\n'
                 "                self._observe('handler', event, 'unknown_outcome', stopped_consumer=consumer)\n"
                 '                failed.append(consumer)\n'
                 '                self._defer(consumer)\n'
                 '                if not isinstance(exc, Exception):\n'
                 '                    raise\n'
                 '                continue\n'
                 '            self._accept(entry, consumer)\n'
                 '            delivered.append(consumer)\n')
    notification('notify-accept-before-callback', _dispatch,
                 _dispatch.replace('        for consumer in ready:\n',
                                   '        for consumer in ready:\n            self._accept(entry, consumer)\n')
                 .replace('            self._accept(entry, consumer)\n            delivered.append(consumer)\n',
                          '            delivered.append(consumer)\n'),
                 'first-attempt-retained')
    notification('notify-requeue-failed-at-tail',
                 "                self._defer(consumer)\n",
                 "                self._defer(consumer)\n"
                 "                with self._condition:\n"
                 "                    self._queue.remove(entry)\n"
                 "                    self._queue.append(entry)\n", 'subscriber-order')
    notification('notify-skip-head-of-line',
                 "            blocked |= owed\n", "", 'subscriber-order')
    notification('notify-retry-without-backoff',
                 "return min(self.retry_cap, self.retry_initial * 2.0 ** min(failures - 1, 64))",
                 "return 0.0", 'retry-backoff')
    notification('notify-uncapped-backoff',
                 "return min(self.retry_cap, self.retry_initial * 2.0 ** min(failures - 1, 64))",
                 "return self.retry_initial * 2.0 ** min(failures - 1, 64)", 'retry-backoff')
    notification('notify-retry-not-woken-when-due',
                 "bounds = self._retry_waits(now) + ",
                 "bounds = [] + ", 'retry-backoff')
    notification('notify-unbounded-observations',
                 "            while len(self._observations) > self.observation_limit:\n"
                 "                self._observations.popleft()\n",
                 "", 'retry-backoff')
    notification('notify-unbounded-watermark',
                 "or not 1 <= hint['watermark'] <= 2**63 - 1",
                 "or hint['watermark'] < 1", 'watermark-range')
    notification('notify-reject-valid-max-watermark',
                 "or not 1 <= hint['watermark'] <= 2**63 - 1",
                 "or not 1 <= hint['watermark'] < 2**63 - 1", 'watermark-range')
    notification('notify-before-commit',
                 "        # Only identity crosses the queue. Extra transport payload is not domain data.",
                 "        if 'event' in hint and 'transition' in hint['event']:\n"
                 "            for handler in self.handlers.values():\n"
                 "                handler(hint['event'])\n"
                 "        # Only identity crosses the queue. Extra transport payload is not domain data.",
                 'committed-event')
    notification('notify-omit-committed-wakeup',
                 "                self.notify(self.hint(result))",
                 "                pass  # defective: committed event never signals",
                 'committed-event')
    notification('notify-check-outside-idle-lock',
                 "        with self._condition:\n            while True:\n"
                 "                now = self.clock()\n                work = self._ready(now)\n",
                 "        ready = bool(self._queue)\n"
                 "        with self._condition:\n            while True:\n"
                 "                now = self.clock()\n                work = self._ready(now) if ready else None\n",
                 'event-in-the-gap')
    notification('notify-wait-without-queue-predicate',
                 "                now = self.clock()\n                work = self._ready(now)\n",
                 "                self._condition.wait(None if deadline is None else max(0.0, deadline - self.clock()))\n"
                 "                now = self.clock()\n                work = self._ready(now)\n",
                 'event-in-the-gap')
    notification('notify-trust-invented-event-identity',
                 "        if row[0] != hint['command_id'] or row[1] != hint['record_digest']:",
                 "        if row[1] != hint['record_digest']:", 'fabricated-event')
    notification('notify-trust-invented-event-digest',
                 "        if row[0] != hint['command_id'] or row[1] != hint['record_digest']:",
                 "        if row[0] != hint['command_id']:", 'fabricated-event')
    # VELDO-0064: the declared falsifiers plus a second, different defect per named row.
    def inbox(name, module, old, new, row):
        add(64, name, '60_veldo_0064_inbox.py', module, old, new, [row])

    inbox('inbox-retain-claim-while-waiting', 'control_assignment.py',
          "            if 'release' in params:\n                changes.update(self.claims.transition(params['release'], before))\n",
          "            if 'release' in params:\n                pass  # defective: the claim stays owned while the person is asked\n",
          'inbox/waiting-resources')
    inbox('inbox-requester-keeps-waiting', 'control_assignment.py',
          "'released_claim': released, 'stop_requester': op == 'open'}",
          "'released_claim': released, 'stop_requester': False}",
          'inbox/waiting-resources')
    inbox('projection-discard-message-id', 'control_channel_projection.py',
          "message_id=platform['message_id'],", "message_id=None,",
          'projection/correlation')
    inbox('inbox-admit-displayed-assigned-status', 'control_assignment.py',
          "        if item['problems']:\n            return 'invalid_record', inputs\n",
          "        if item['raw'].get('display_status') == 'assigned':\n            return 'admitted', inputs\n"
          "        if item['problems']:\n            return 'invalid_record', inputs\n",
          'inbox/unauthorized-admission')
    inbox('inbox-admit-without-journal-authority', 'control_assignment.py',
          "        if row is None or row[0] != data['owner'] or written.get('version') != item['version'] \\\n"
          "                or written.get('digest') != item['digest']:\n            return 'missing_authority', inputs\n",
          "", 'inbox/unauthorized-admission')
    inbox('inbox-admit-ignores-owner-membership', 'control_assignment.py',
          "        if not active or owner['principal_type'] != 'person' \\",
          "        if False and owner['principal_type'] != 'person' \\", 'inbox/unauthorized-admission')
    inbox('inbox-index-skips-invalid', 'control_assignment.py',
          "            if item['problems']:\n                entry['category'] = 'invalid'\n",
          "            if item['problems']:\n                continue\n", 'inbox/visible-invalid')
    inbox('inbox-trust-tampered-content', 'control_assignment.py',
          "        if raw is not None and self.store.digest_of({'kind': kind, 'data': raw, 'version': version}) != digest:\n"
          "            problems.append('stored data does not match its committed digest')\n",
          "", 'inbox/visible-invalid')
    # VELDO-0064 review r1: a unit parked on a pending person assignment is not claimable.
    inbox('inbox-park-as-plain-release', 'control_assignment.py',
          "params['release'] = dict(action='park',", "params['release'] = dict(action='release',",
          'inbox/parked-unit-unclaimable')
    inbox('claims-claim-ignores-park', 'control_claim.py',
          "        if op == 'claim' and parked:", "        if False and parked:", 'inbox/parked-unit-unclaimable')
    inbox('inbox-resume-without-admission', 'control_assignment.py',
          "        if reason != 'admitted':\n            raise Refused(reason, 'the assignment does not admit the blocked work')\n",
          "", 'inbox/parked-unit-unclaimable')
    # VELDO-0064 review r2: the parked unit is derived from the requester's own claim.
    inbox('inbox-release-only-named-unit', 'control_assignment.py',
          "            held = self._held_claims(entities, principal)\n",
          "            held = [c for c in self._held_claims(entities, principal)"
          " if c[1].get('unit_id') == content.get('unit_id')]\n", 'inbox/release-derived-from-claim')
    inbox('inbox-open-without-generation-keeps-claim', 'control_assignment.py',
          "        if type(generation) is not int:\n            raise Refused('invalid_input', 'releasing a claim names its generation')\n",
          "        if type(generation) is not int:\n            return None\n", 'inbox/release-derived-from-claim')
    inbox('inbox-open-skips-claim-recheck', 'control_assignment.py',
          "        if params['action'] == 'open':\n            rows = conn.execute(",
          "        if False:\n            rows = conn.execute(", 'inbox/release-derived-from-claim')
    # VELDO-0064 review r5: admission verifies the owner's signature over the exact answer.
    inbox('inbox-admit-skips-answer-signature', 'control_assignment.py',
          "        if not verified:\n            return 'missing_authority', inputs\n", "",
          'inbox/admit-verifies-owner-signature')
    inbox('inbox-admit-unbound-answer-signature', 'control_assignment.py',
          "        if not binds:\n            return 'missing_authority', inputs\n", "",
          'inbox/admit-verifies-owner-signature')
    # VELDO-0064 review r3: the intent is committed before the send; an unknown send never repeats.
    inbox('projection-retry-pending-intent', 'control_channel_projection.py',
          "RETRYABLE = ('refused',)", "RETRYABLE = ('refused', 'pending')", 'projection/intent-before-send')
    inbox('projection-send-before-intent', 'control_channel_projection.py',
          "            intent = self._commit(dict(phase='intent', projection_id=pid, record=record), expected)\n"
          "            completion = self._send(enrollment['chat'], text)\n",
          "            completion = self._send(enrollment['chat'], text)\n"
          "            intent = self._commit(dict(phase='intent', projection_id=pid, record=record), expected)\n",
          'projection/intent-before-send')
    # VELDO-0064 review r4: a differing echoed text keeps the returned identity as an anomaly.
    inbox('projection-mismatch-as-refusal', 'control_channel_projection.py',
          "        found = anomalies(data, platform)\n",
          "        if 'presentation_mismatch' in anomalies(data, platform):\n"
          "            return {pid: {'kind': ENTITY_KIND, 'data': dict(data, outcome='refused', refusal='presentation_mismatch')}}\n"
          "        found = anomalies(data, platform)\n", 'projection/echo-mismatch-kept')
    inbox('projection-ignore-echoed-text', 'control_channel_projection.py',
          "    if platform['text'].encode('utf-8') != record['presentation'].encode('utf-8'):\n        found.append('presentation_mismatch')\n",
          "", 'projection/echo-mismatch-kept')
    # VELDO-0064 review r7: each assignment goes to the chat enrolled for its own owner.
    inbox('projection-one-chat-for-every-owner', 'control_channel_projection.py',
          "        refusal, enrollment = self._enrollment(brief['content']['owner'])\n",
          "        refusal, enrollment = self._enrollment('owner')\n", 'projection/owner-enrolled-chat')
    inbox('projection-enrollment-ignores-principal', 'control_channel_projection.py',
          "    if data.get('principal') != principal:\n        problems.append('the enrollment names another principal')\n",
          "", 'projection/owner-enrolled-chat')
    # VELDO-0064 review r8: a message placed in another chat is a named anomaly, not a projection.
    inbox('projection-ignore-returned-chat', 'control_channel_projection.py',
          "    if platform['chat_id'] != record['enrolled_chat']:\n        found.append('chat_mismatch')\n",
          "", 'projection/returned-chat-checked')
    inbox('projection-record-enrolled-chat', 'control_channel_projection.py',
          "chat_id=platform['chat_id'],", "chat_id=data['enrolled_chat'],", 'projection/returned-chat-checked')
    # VELDO-0064 review r2-s4: only Telegram's own 4xx error answer is a definite refusal.
    range_guard = ("            if not 400 <= exc.code < 500:\n"
                   "                raise EdgeRefused('unknown_outcome', 'HTTP %d is not a definite refusal' % exc.code) from None\n")
    body_guard = ("            if not telegram_refusal(exc, exc.code):\n"
                  "                raise EdgeRefused('unknown_outcome', 'HTTP %d without the Bot API error answer' % exc.code) from None\n")
    inbox('projection-any-http-error-refused', 'control_channel_projection.py', range_guard + body_guard, '',
          'projection/only-telegram-refusal-retried')
    inbox('projection-any-4xx-refused', 'control_channel_projection.py', body_guard, '',
          'projection/only-telegram-refusal-retried')
    inbox('projection-telegram-5xx-refused', 'control_channel_projection.py', range_guard, '',
          'projection/only-telegram-refusal-retried')
    # VELDO-0064 review r2-s5: a malformed reply is an unknown outcome; nothing the edge raises stops the loop.
    inbox('projection-edge-protocol-error-escapes', 'control_channel_projection.py',
          "        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as exc:\n",
          "        except (urllib.error.URLError, OSError, ValueError) as exc:\n", 'projection/protocol-error-unknown')
    inbox('projection-edge-error-stops-loop', 'control_channel_projection.py',
          "        except Exception as exc:\n"
          "            return {'platform': None, 'refusal': None, 'detail': 'the edge raised %s' % type(exc).__name__}\n",
          "", 'projection/protocol-error-unknown')
    inbox('projection-protocol-error-as-refusal', 'control_channel_projection.py',
          "            raise EdgeRefused('unknown_outcome', 'no readable platform answer (%s)' % type(exc).__name__) from None\n",
          "            raise EdgeRefused('channel_refused', 'no readable platform answer (%s)' % type(exc).__name__) from None\n",
          'projection/protocol-error-unknown')
    # VELDO-0064 review r2-s7: an answer verifies against the key active when it was accepted.
    inbox('inbox-admit-current-active-key', 'control_assignment.py',
          "        key = self._answer_key(state, data, row, inputs)\n",
          "        key = self.AC.active_key(state['keyring'], data['owner'], now)\n", 'inbox/answer-survives-key-rotation')
    inbox('inbox-answer-key-from-current-entity', 'control_assignment.py',
          "        key = dict(stored['data'], key_id=kid)\n",
          "        key = dict(state['entities'].get(kid, {}).get('data') or {}, key_id=kid)\n",
          'inbox/answer-survives-key-rotation')
    inbox('inbox-answer-key-ignores-revocation', 'control_assignment.py',
          "            if current.get('revoked_at') is not None and current['revoked_at'] <= at:\n                return None\n",
          "", 'inbox/answer-survives-key-rotation')
    # VELDO-0064 review r2-s6: every parked unit is visible with its assignment and why it is parked.
    inbox('inbox-parked-only-awaiting', 'control_assignment.py',
          "            parked.append({'unit_id'",
          "            if reason != 'awaiting_answer':\n                continue\n            parked.append({'unit_id'",
          'inbox/parked-units-visible')
    inbox('inbox-parked-metric-omitted', 'control_assignment.py',
          "pending=pending, parked=len(parked),",
          "pending=pending, parked=sum(1 for u in parked if u['reason'] == 'awaiting_answer'),",
          'inbox/parked-units-visible')
    inbox('inbox-parked-refusal-shown-ready', 'control_assignment.py',
          "reason = 'ready_to_resume' if admission == 'admitted' else 'answer_not_admitted'",
          "reason = 'ready_to_resume'", 'inbox/parked-units-visible')
    # VELDO-0054: every declared falsifier and a second, different defect for its row, plus a
    # driven defect for every other row suite 62 asserts.
    def decisions(name, module, old, new, row):
        add(54, name, '62_veldo_0054_decisions.py', module, old, new, ['decisions/' + row])

    framing = "    if not _is_str(framing) or framing != record.get('framing_digest'):\n"
    decisions('framing-receipt-without-digest', 'control_decision_dependency.py', framing,
              "    if framing is not None and framing != record.get('framing_digest'):\n", 'wrong-framing')
    decisions('framing-shape-only', 'control_decision_dependency.py', framing,
              "    if not _is_str(framing):\n", 'wrong-framing')
    decisions('subject-currency-ignored', 'control_decision_dependency.py',
              "    if current is None or subject.get('digest') != current:\n", "    if False:\n", 'exact-binding')
    decisions('floor-stations-skip-decisions', 'control_eligibility.py',
              "            return self._decision_codes(unit, inputs)\n", "            return []\n", 'exact-binding')
    decisions('inline-status-as-ruling', 'control_decision_dependency.py',
              "    mine = [(sid, s) for sid, s in settlements if isinstance(s, dict) and s.get('decision') == rid]\n",
              "    if isinstance(record, dict) and record.get('state') == 'settled':\n        return []\n"
              "    mine = [(sid, s) for sid, s in settlements if isinstance(s, dict) and s.get('decision') == rid]\n",
              'unsigned-resolution')
    decisions('unsigned-settlement-accepted', 'control_decision_dependency.py',
              "        if verify is None or not isinstance(body, dict) or not _is_str(signature) or not _is_str(signer):\n"
              "            continue\n",
              "        if isinstance(body, dict) and not _is_str(signature):\n            verified.append(body)\n            continue\n"
              "        if verify is None or not isinstance(body, dict) or not _is_str(signer):\n            continue\n",
              'unsigned-resolution')
    decisions('plan-inline-resolution-honored', 'plan.py',
              '        if isinstance(d, dict):\n            for s in d.get("blocks") or []:\n',
              '        if isinstance(d, dict) and d.get("status") != "resolved":\n            for s in d.get("blocks") or []:\n',
              'unsigned-resolution')
    decisions('ambiguous-settlement-first', 'control_decision_dependency.py',
              "    if len(current) > 1:\n        return ['ambiguous_decision:' + rid]\n", "", 'named-blockers')
    decisions('unsupported-obligation-presumed', 'control_decision_dependency.py',
              "SUPPORTED_OBLIGATIONS = ()", "SUPPORTED_OBLIGATIONS = ('tripwire', 'adversarial_decision_review')",
              'named-blockers')
    decisions('missing-reference-ignored', 'control_decision_dependency.py',
              "            codes.append('missing_decision:%s' % ref)\n", "            pass\n", 'named-blockers')
    decisions('frontier-inline-decisions', 'frontier.py',
              "        blocked = PL._decision_blocks(fm, gate)\n", "        blocked = PL._decision_blocks(fm)\n",
              'named-blockers')
    decisions('run-check-ignores-file-references', 'plan.py',
              '        reasons.extend("decision refused: %s" % r for r in gate.decision_blockers(spec_id, references=refs)\n'
              '                       if r not in decision["refusals"])\n', '', 'named-blockers')
    decisions('scope-binding-ignored', 'control_decision_dependency.py',
              "    problems = []\n    if body.get('subject') != record.get('subject'):\n",
              "    return []\n    problems = []\n    if body.get('subject') != record.get('subject'):\n", 'scope-binding')
    decisions('scope-target-may-differ', 'control_decision_dependency.py',
              "    if body.get('scope_digest') != scope_digest(record.get('scope')) \\\n"
              "            or (record.get('scope') or {}).get('target') != (record.get('subject') or {}).get('id'):\n",
              "    if body.get('scope_digest') != scope_digest(record.get('scope')):\n", 'scope-binding')
    decisions('consumer-unregistered', 'control_decision_dependency.py',
              "    ('control_eligibility.py', 'Gate.decision_blockers'),\n", "", 'consumers-from-call-sites')
    decisions('production-trust-not-wired', 'control_eligibility.py',
              "                settlement_trust=settlements)\n", "                settlement_trust=None)\n",
              'production-gate-verifies')
    decisions('taxonomy-unbound-unknown', 'control_eligibility.py',
              "    'unbound_decision': 'stale_subject', 'decision_ruling': 'missing_authority',\n",
              "    'decision_ruling': 'missing_authority',\n", 'observations')
    decisions('status-reader-inline-decisions', 'runstatus.py',
              "            blocked = PL._decision_blocks(fm, PL.EL.gate_for(Path(root), eligibility))\n", "            blocked = PL._decision_blocks(fm)\n", 'status-reader-agrees')
    decisions('status-reader-ignores-decisions', 'runstatus.py',
              "            blocked = PL._decision_blocks(fm, PL.EL.gate_for(Path(root), eligibility))\n", "            blocked = {}\n", 'status-reader-agrees')
    # VELDO-0054 review B: malformed records are named invalid_input for the unit they concern.
    decisions('invalid-record-not-observed', 'control_eligibility.py',
              "                self._invalid_record(identity, 'decision')\n", "                pass\n",
              'malformed-records-named')
    decisions('record-invalid-ignored', 'control_decision_dependency.py',
              "    if invalid:\n        return invalid\n", "", 'malformed-records-named')
    decisions('settlement-invalid-ignored', 'control_decision_dependency.py',
              "    if malformed:\n        return malformed\n", "", 'malformed-records-named')
    decisions('reference-invalid-dropped', 'control_decision_dependency.py',
              "            codes.append('invalid_input:decision_reference')\n", "            continue\n",
              'malformed-records-named')
    # VELDO-0054 review 2, item 1: an unhashable subject field is named; veldo status names its stop.
    decisions('subject-digest-type-unchecked', 'control_decision_dependency.py',
              "all(_is_str(subject.get(k)) for k in ('kind', 'id', 'digest'))",
              "all(_is_str(subject.get(k)) for k in ('kind', 'id'))", 'malformed-subject-named')
    decisions('subject-kind-type-unchecked', 'control_decision_dependency.py',
              "all(_is_str(subject.get(k)) for k in ('kind', 'id', 'digest'))",
              "all(_is_str(subject.get(k)) for k in ('id', 'digest'))", 'malformed-subject-named')
    decisions('status-stop-crashes', 'runstatus.py',
              '    except Exception as error:  # noqa: BLE001 - a burn-down it cannot build is named, never a crash\n',
              '    except ZeroDivisionError as error:  # defect: any other failure escapes\n', 'status-names-its-stop')
    decisions('status-stop-unnamed', 'runstatus.py',
              '        return [], "burndown_unanswerable:" + type(error).__name__\n',
              '        return [], None\n', 'status-names-its-stop')
    # Item 2: a malformed blocks holds the unit it names and is recorded.
    decisions('malformed-blocks-govern-nothing', 'control_decision_dependency.py',
              "    named = _named_ids(blocks) if blocks_malformed(record) else set(blocks)\n",
              "    named = set(blocks) if _str_list(blocks) else set()\n", 'malformed-blocks-held')
    decisions('malformed-blocks-unrecorded', 'control_eligibility.py',
              "                self._invalid_record(identity, 'blocks')\n", "                pass\n",
              'malformed-blocks-held')
    # Item 3: a wrong-typed schema is invalid_input, decided before unsupported and unresolved.
    decisions('schema-type-unchecked', 'control_decision_dependency.py',
              "    for name, ok in (('schema', record.get('schema') is None or isinstance(record.get('schema'), str)),\n"
              "                     ('decision_id',",
              "    for name, ok in (('decision_id',", 'invalid-before-unsupported')
    decisions('invalid-after-unresolved', 'control_decision_dependency.py',
              "    invalid = record_invalid(rid, record)\n    if invalid:\n        return invalid\n"
              "    mine = [(sid, s) for sid, s in settlements if isinstance(s, dict) and s.get('decision') == rid]\n"
              "    if not mine:\n        return ['unresolved_decision:' + rid]\n",
              "    mine = [(sid, s) for sid, s in settlements if isinstance(s, dict) and s.get('decision') == rid]\n"
              "    if not mine:\n        return ['unresolved_decision:' + rid]\n"
              "    problems = record_problems(rid, record) if not record_invalid(rid, record) else []\n"
              "    if problems:\n        return problems\n"
              "    invalid = record_invalid(rid, record)\n    if invalid:\n        return invalid\n",
              'invalid-before-unsupported')
    # VELDO-0054 review 3, item 1: blocks walked without recursion; unexpected faults named.
    decisions('blocks-walk-recursive', 'control_decision_dependency.py',
              "    stack = [value]\n    while stack:\n        current = stack.pop()\n",
              "    stack = []\n    current = value\n    if isinstance(current, list):\n"
              "        for item in current:\n            yield from _named(item)\n        return\n"
              "    stack = [value]\n    while stack:\n        current = stack.pop()\n",
              'deep-blocks-named')
    decisions('decide-raises-unexpected', 'control_eligibility.py',
              "        except Exception as error:  # noqa: BLE001 - VELDO-0054: an unexpected fault is named, never raised\n"
              "            decision['refusals'] = [unexpected(error)]\n", "", 'deep-blocks-named')
    decisions('blockers-raise-unexpected', 'control_eligibility.py',
              "        except Exception as error:  # noqa: BLE001 - VELDO-0054: an unexpected fault is named, never raised\n"
              "            codes = [unexpected(error)]\n", "", 'deep-blocks-named')
    # Item 2: veldo status names a store refusal by its code, as decide does.
    decisions('status-store-refusal-generic', 'runstatus.py',
              '    except store_refusals as error:\n        return [], "refused:" + eligibility.refusal_code(error)\n',
              '', 'status-names-store-refusal')
    decisions('status-store-refusal-code-dropped', 'runstatus.py',
              '        return [], "refused:" + eligibility.refusal_code(error)\n',
              '        return [], "refused:" + type(error).__name__\n', 'status-names-store-refusal')
    decisions('blockers-store-refusal-renamed', 'control_eligibility.py',
              "            codes = [self.refusal_code(error)]\n", "            codes = ['invalid_input:' + error.code]\n",
              'status-names-store-refusal')
    # Item 3: a malformed settlement is invalid_input before its record is judged unsupported.
    decisions('unsupported-before-settlement-invalid', 'control_decision_dependency.py',
              "    malformed = [code for sid, s in mine for code in settlement_invalid(sid, s)]\n"
              "    if malformed:\n        return malformed\n"
              "    problems = record_problems(rid, record)\n    if problems:\n        return problems\n",
              "    problems = record_problems(rid, record)\n    if problems:\n        return problems\n"
              "    malformed = [code for sid, s in mine for code in settlement_invalid(sid, s)]\n"
              "    if malformed:\n        return malformed\n",
              'settlement-invalid-before-unsupported')
    decisions('settlement-signature-type-unchecked', 'control_decision_dependency.py',
              "    for name in ('signature', 'signer'):\n", "    for name in ('signer',):\n",
              'settlement-invalid-before-unsupported')
    # Minor: a blocks string names every id it lists; malformed references are recorded.
    decisions('blocks-string-not-split', 'control_decision_dependency.py',
              "        ids.update(text.replace(',', ' ').split())\n", "        pass\n", 'minor-shapes')
    decisions('plan-reference-unrecorded', 'control_eligibility.py',
              "                self._invalid_record(inputs['plan']['id'], 'open_decisions')\n", "                pass\n",
              'minor-shapes')
    decisions('decision-id-unrecorded', 'control_eligibility.py',
              "                self._invalid_record(identity, 'decision_id')\n", "                pass\n", 'minor-shapes')
    # VELDO-0054 review 4, item 1: signer and signature text the verifier cannot be handed is named.
    decisions('settlement-nul-passed', 'control_decision_dependency.py',
              "    if '\\x00' in text:\n        return False\n", "", 'settlement-text-encodable')
    decisions('settlement-unencodable-passed', 'control_decision_dependency.py',
              "    try:\n        text.encode('utf-8')\n    except UnicodeEncodeError:\n        return False\n", "",
              'settlement-text-encodable')
    # Item 2: a named stop under decide propagates as the stop it is.
    decisions('decide-holds-a-stop', 'control_eligibility.py',
              "            decision['refusals'] = ['unavailable_service:store']\n        except Stopped:\n"
              "            raise  # a named stop is the caller's, never a unit hold\n",
              "            decision['refusals'] = ['unavailable_service:store']\n", 'stops-propagate')
    decisions('blockers-hold-a-stop', 'control_eligibility.py',
              "            codes = ['unavailable_service:store']\n        except Stopped:\n"
              "            raise  # a named stop is the caller's, never a unit hold\n",
              "            codes = ['unavailable_service:store']\n", 'stops-propagate')
    # Item 3: an unexpected fault is named with its message, bounded and on one line.
    decisions('unexpected-message-dropped', 'control_eligibility.py',
              "    return code + '/' + message if message else code\n", "    return code\n", 'unexpected-message')
    decisions('unexpected-message-unbounded', 'control_eligibility.py',
              "    message = message[:UNEXPECTED_MESSAGE_LIMIT]\n", "", 'unexpected-message')
    decisions('unexpected-message-multiline', 'control_eligibility.py',
              "    message = ' '.join(text.split()).replace(';', ',')\n", "    message = text.replace(';', ',')\n",
              'unexpected-message')
    # VELDO-0054 review 5, item 1: what reaches the verifier is bounded.
    bound = "        return len(text) <= SIGNER_LIMIT and not any(ord(c) < 32 or ord(c) == 127 for c in text)\n"
    decisions('signer-unbounded', 'control_decision_dependency.py', bound, "        return True\n",
              'verifier-input-bounded')
    decisions('signer-controls-allowed', 'control_decision_dependency.py', bound,
              "        return len(text) <= SIGNER_LIMIT\n", 'verifier-input-bounded')
    # Review 6: the bounds refuse nothing real (a quoted principal with a space, 256 characters, an
    # RSA-4096 signature); a tightened limit reds the same row.
    decisions('signer-whitespace-refused', 'control_decision_dependency.py', bound,
              "        return len(text) <= SIGNER_LIMIT and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in text)\n",
              'verifier-input-bounded')
    decisions('signature-limit-1024', 'control_decision_dependency.py', "SIGNATURE_LIMIT = 16384\n",
              "SIGNATURE_LIMIT = 1024\n", 'verifier-input-bounded')
    decisions('signer-limit-exclusive', 'control_decision_dependency.py', bound,
              bound.replace('len(text) <= SIGNER_LIMIT', 'len(text) < SIGNER_LIMIT'), 'verifier-input-bounded')
    decisions('signature-unbounded', 'control_decision_dependency.py',
              "    return len(text) <= SIGNATURE_LIMIT\n", "    return True\n", 'verifier-input-bounded')
    # Item 2: an unexpected fault's message is plain, separator-free and always obtainable.
    decisions('unexpected-controls-kept', 'control_eligibility.py',
              "    message = ''.join('\\\\x%02x' % ord(c) if ord(c) < 32 or ord(c) == 127 else c for c in message)\n",
              "", 'unexpected-message')
    decisions('unexpected-separator-kept', 'control_eligibility.py',
              "    message = ' '.join(text.split()).replace(';', ',')\n", "    message = ' '.join(text.split())\n",
              'unexpected-message')
    decisions('unexpected-str-unguarded', 'control_eligibility.py',
              "    try:\n        text = str(error)\n    except Exception:  # noqa: BLE001 - an exception whose own text raises is still named\n"
              "        text = '<unprintable>'\n", "    text = str(error)\n", 'unexpected-message')
    decisions('verifier-unavailable-as-unsigned', 'control_decision_dependency.py',
              "            if not verified and str(detail).startswith('ssh-keygen unavailable'):\n",
              "            if False:\n", 'observations')
    # VELDO-0065: the declared falsifiers plus a second, different defect per named row.
    def presentation(name, old, new, row):
        add(65, name, '62_veldo_0065_presentations.py', 'control_channel_presentation.py', old, new, [row])

    presentation('request-digest-omits-version',
                 "    body = {'request_id': request_id, 'request_version': request_version}\n",
                 "    body = {'request_id': request_id}\n", 'presentation/revision-identity')
    presentation('bindings-ignore-request-identity',
                 "BOUND_FIELDS = ('request_id', 'request_version', 'request_digest', 'subject_digests', 'risk_statement',\n",
                 "BOUND_FIELDS = ('subject_digests', 'risk_statement',\n", 'presentation/revision-identity')
    presentation('render-omits-risk',
                 "             'Risk (stated by %s): %s' % (record['framed_by'], _words(record['risk_statement'])),\n", "",
                 'presentation/receipt-binds-shown-content')
    presentation('framing-signature-unchecked',
                 "                or not self._framing_signed(request, framing, state, c)):\n",
                 "                or False):\n", 'presentation/receipt-binds-shown-content')
    presentation('presentation-key-without-digest',
                 "    return 'presentation:%s:%s:%d:%s' % (CHANNEL, request_id, request_version, digest.split(':', 1)[-1])\n",
                 "    return 'presentation:%s:%s:%d' % (CHANNEL, request_id, request_version)\n",
                 'presentation/visible-supersession')
    presentation('replacement-without-reply-link',
                 "            payload['reply_parameters'] = {'message_id': reply_to, 'allow_sending_without_reply': True}\n",
                 "            pass\n", 'presentation/visible-supersession')
    presentation('answer-checks-subject-only',
                 "    return [f for f in BOUND_FIELDS if receipt.get(f) != current.get(f)]\n",
                 "    return [f for f in ('subject_digests',) if receipt.get(f) != current.get(f)]\n",
                 'answer/current-presentation-only')
    presentation('missing-reference-uses-current',
                 "        if not all(a.get(k) is not None for k in REFERENCE_FIELDS):\n"
                 "            raise Refused('missing_presentation', 'an answer names the presentation it addresses')\n",
                 "        if not all(a.get(k) is not None for k in REFERENCE_FIELDS):\n"
                 "            now_shown = self.current(a.get('request_id')) or {}\n"
                 "            a = dict(a, presentation_id=now_shown.get('presentation_id'), presentation_digest=now_shown.get('brief_digest'),\n"
                 "                     presentation_version=now_shown.get('presentation_version'))\n",
                 'answer/current-presentation-only')
    presentation('answer-drops-rationale',
                 "                  'rationale': a['rationale'], 'attribution': dict(ev),\n",
                 "                  'rationale': None, 'attribution': dict(ev),\n",
                 'answer/ruling-and-rationale')
    presentation('answer-skips-edge-signature',
                 "        if not verified:\n            raise Refused('not_authorized', 'the answer signature does not verify')\n",
                 "", 'answer/ruling-and-rationale')
    presentation('unsent-marked-published', "        data.update(outcome='refused', refusal=refusal)\n",
                 "        data.update(outcome='published', refusal=refusal)\n", 'answer/unseen-refused')
    presentation('unseen-only-refused-outcome',
                 "        if receipt['outcome'] != 'published':\n            raise Refused('unseen_presentation'",
                 "        if receipt['outcome'] == 'refused':\n            raise Refused('unseen_presentation'",
                 'answer/unseen-refused')
    # VELDO-0065 review r7: the answer record is what authority_contract.settle consumes.
    presentation('answer-records-typed-choice-as-ruling', "'choice': a['choice'], 'ruling': a['ruling'],\n",
                 "'choice': a['choice'], 'ruling': a['choice'],\n", 'answer/settle-consumes-answer')
    presentation('unmapped-choice-presented', "            return 'unmapped_choice', None, versions\n",
                 "            pass\n", 'answer/settle-consumes-answer')
    # VELDO-0065 review r1: only the requester frames, and the framer is named.
    presentation('project-owner-frames-again', "                    or principal != c['requested_by']):\n",
                 "                    or (principal != c['requested_by'] and 'project_owner' not in (entry.get('roles') or []))):\n",
                 'framing/requester-only')
    presentation('stored-framing-any-framer', "                or principal != content['requested_by'] or command.get('principal') != principal\n",
                 "                or command.get('principal') != principal\n",
                 'framing/requester-only')
    # VELDO-0065 review r2, r2b: a stored framing counts only as the frame operation accepted it.
    presentation('stored-framing-any-writer',
                 "        if written[1] != command['command_id'] or self.store.command_digest(accepted_by) != written[2]:\n",
                 "        if written[1] != command['command_id']:\n", 'framing/stored-framing-reverified')
    presentation('stored-framing-key-at-any-time', "        if not usable_key(key, principal, self.clock()):\n",
                 "        if key is None:\n", 'framing/stored-framing-reverified')
    # VELDO-0065 review r5: an answer cannot predate the presentation it answers.
    presentation('answer-time-unchecked',
                 "        if ev['platform_timestamp'] < receipt['published_at']:\n"
                 "            raise Refused('answer_before_publication', 'the platform dates the answer before the presentation it answers')\n",
                 "", 'answer/not-before-publication')
    presentation('answer-time-same-second-refused', "        if ev['platform_timestamp'] < receipt['published_at']:\n",
                 "        if ev['platform_timestamp'] <= receipt['published_at']:\n", 'answer/not-before-publication')
    # VELDO-0065 review r9: a decision is presented only in a person's private chat.
    presentation('group-chat-presented', "        if enrollment['data']['chat_id'] < 0:\n",
                 "        if False:\n", 'presentation/private-chat-only')
    presentation('unpresented-reason-not-counted',
                 "                unpresented[refusal] = unpresented.get(refusal, 0) + 1\n", "                pass\n",
                 'presentation/private-chat-only')
    # VELDO-0065 review r6: a replacement publishes when the superseded message is gone.
    presentation('replacement-requires-reply-target', "'message_id': reply_to, 'allow_sending_without_reply': True}",
                 "'message_id': reply_to, 'allow_sending_without_reply': False}", 'presentation/replacement-without-reply-target')
    presentation('reply-link-always-claimed', "    return record['reply_to'] is not None and replied == record['reply_to']\n",
                 "    return record['reply_to'] is not None\n", 'presentation/replacement-without-reply-target')
    # VELDO-0065 review r8: receipt verification binds the reply link.
    presentation('receipt-reply-link-unchecked',
                 "    if replied not in (receipt['reply_to'], None) or receipt.get('reply_linked') is not record_linked(receipt, replied):\n",
                 "    if False:\n", 'presentation/reply-link-verified')
    presentation('receipt-platform-reply-unchecked',
                 "        if h.get('reply_to') != (receipt.get('reply_to_message_id') if i == 0 else None):\n", "        if False:\n",
                 'presentation/reply-link-verified')
    # VELDO-0065 review r4: a presentation longer than one Telegram message is split, never truncated.
    presentation('part-length-in-characters', "    return len(text.encode('utf-16-le')) // 2\n",
                 "    return len(text)\n", 'presentation/long-brief-split')
    presentation('answer-only-to-last-part', "ev['reply_to_message_id'] not in receipt['message_ids']):",
                 "ev['reply_to_message_id'] != receipt['message_id']):", 'presentation/long-brief-split')
    # VELDO-0065 review r3: with presentations enabled, one decision message per request version.
    def one_message(name, old, new):
        add(65, name, '62_veldo_0065_presentations.py', 'control_channel_projection.py', old, new,
            ['projection/one-message-per-version'])

    one_message('projection-notice-beside-presentation',
                "        return self._project(entry) if receipts is None else self._presented(entry, receipts)\n",
                "        return self._project(entry)\n")
    one_message('projection-never-reports-presented',
                "            outcome = 'presented' if refusal is None and record is None else 'awaiting_presentation'\n",
                "            outcome = 'awaiting_presentation'\n")

    # VELDO-0065 second review n1: the store decides whether the projection sends, and an earlier
    # notice is visibly superseded by the first presentation.
    def projection(name, old, new, row):
        add(65, name, '62_veldo_0065_presentations.py', 'control_channel_projection.py', old, new, [row])

    projection('projection-ignores-presentations', "        in_use = enabled or framed or bool(mine)\n",
               "        in_use = enabled\n", 'projection/silent-from-store')
    projection('projection-ignores-enrollment-setting', "        in_use = enabled or framed or bool(mine)\n",
               "        in_use = framed or bool(mine)\n", 'projection/silent-from-store')
    presentation('presentation-ignores-notice',
                 "        notices = self._notices(request, b['enrolled_chat']) if prior is None else []\n",
                 "        notices = []\n", 'projection/notice-superseded')
    presentation('notice-not-marked-superseded',
                 "            changes[notice] = {'kind': held['kind'], 'data': dict(held['data'], superseded_by=pid)}\n",
                 "            pass\n", 'projection/notice-superseded')

    # VELDO-0065 second review n2: a definitely refused part is sent again after its retry_after.
    presentation('partial-never-sent-again', "RETRYABLE = ('refused', 'partial')\n", "RETRYABLE = ('refused',)\n",
                 'presentation/refused-part-sent-again')
    presentation('retry-after-ignored', "                and self.clock() < existing['retry_not_before']):\n",
                 "                and False):\n", 'presentation/refused-part-sent-again')
    # VELDO-0065 second review n5: choices match whatever case and spacing; a reply is never met with silence.
    presentation('choice-match-case-sensitive', "    text = unicodedata.normalize('NFKC', str(text)).casefold()\n",
                 "    text = unicodedata.normalize('NFKC', str(text))\n", 'answer/choice-matching-and-feedback')
    presentation('owner-not-told', "        sent = self._send(ev['chat_id'], text, ev['platform_message_id'])\n",
                 "        sent = {'platform': None, 'refusal': None}\n", 'answer/choice-matching-and-feedback')
    # VELDO-0065 third review item 6: only the projection's own notice of the same request is superseded.
    presentation('notice-kind-from-caller', "            if (held.get('kind') != notice_kind or not isinstance(held.get('data'), dict)\n",
                 "            if (held.get('kind') != data['supersedes'].get('notice_kind', held.get('kind')) or not isinstance(held.get('data'), dict)\n",
                 'presentation/notice-kind-fixed')
    presentation('notice-of-any-request', "                    or held['data'].get('assignment_id') != data['request_id']):\n",
                 "                    or False):\n", 'presentation/notice-kind-fixed')
    # VELDO-0065 third review item 4: frame() and the stored-framing check apply one key rule.
    presentation('frame-key-by-time', "            key = next((k for k in state['keyring'] if usable_key(k, principal, now)), None)\n",
                 "            key = self.AC.active_key(state['keyring'], principal, now)\n", 'framing/frame-and-presenter-agree')
    presentation('frame-ledger-unchecked', "            if principal in revoked:\n", "            if False:\n",
                 'framing/frame-and-presenter-agree')
    # VELDO-0065 fourth review item 1: pins come from the snapshot the checks read, not a later read.
    presentation('frame-ledger-pin-read-later',
                 "                        REVOCATION_LEDGER: seen.get(REVOCATION_LEDGER, {}).get('version', 0)}\n",
                 "                        REVOCATION_LEDGER: (self._entity(REVOCATION_LEDGER) or {}).get('version', 0)}\n",
                 'framing/frame-and-presenter-agree')
    presentation('frame-key-pin-read-later', "                        key['key_id']: seen.get(key['key_id'], {}).get('version', 0),\n",
                 "                        key['key_id']: (self._entity(key['key_id']) or {}).get('version', 0),\n",
                 'framing/frame-and-presenter-agree')
    # VELDO-0065 second review n6 (restored: dropped by 82576d5): the framing key by the journal's order.
    presentation('framing-key-read-now', "        key = self._as_of(data.get('key_id'), 'verification_key', written[0])\n",
                 "        key = self._as_of(data.get('key_id'), 'verification_key', 1 << 62)\n", 'framing/key-by-store-order')
    presentation('framing-ledger-unchecked', "        if not isinstance(revoked, dict) or principal in revoked:\n",
                 "        if False:\n", 'framing/key-by-store-order')
    # VELDO-0065 third review item 5: retry_after counts only as a bounded non-negative integer.
    presentation('retry-after-any-number', "min(wait, MAX_RETRY_AFTER) if type(wait) is int and wait >= 0 else None",
                 "min(wait, MAX_RETRY_AFTER) if type(wait) in (int, float) and wait >= 0 else None", 'presentation/retry-after-bounded')
    presentation('retry-after-boolean-accepted', "min(wait, MAX_RETRY_AFTER) if type(wait) is int and wait >= 0 else None",
                 "min(wait, MAX_RETRY_AFTER) if isinstance(wait, int) and wait >= 0 else None", 'presentation/retry-after-bounded')
    # VELDO-0065 fourth review item 5: a retry_after above the bound is capped, not ignored.
    presentation('retry-after-unbounded', "min(wait, MAX_RETRY_AFTER) if type(wait) is int and wait >= 0 else None",
                 "wait if type(wait) is int and wait >= 0 else None", 'presentation/retry-after-capped')
    presentation('retry-after-above-bound-ignored', "min(wait, MAX_RETRY_AFTER) if type(wait) is int and wait >= 0 else None",
                 "wait if type(wait) is int and 0 <= wait <= MAX_RETRY_AFTER else None", 'presentation/retry-after-capped')
    # VELDO-0065 third review item 8: choices under NFKC, case folding and separator equivalence.
    presentation('choice-without-nfkc', "    cut = next((i for i, ch in enumerate(text) if ':' in unicodedata.normalize('NFKC', ch)), None)\n",
                 "    cut = next((i for i, ch in enumerate(text) if ch == ':'), None)\n", 'answer/choice-normalization')
    presentation('choice-separators-distinct', "    text = text.translate(CHOICE_SEPARATORS)\n", "",
                 'answer/choice-normalization')
    # VELDO-0065 third review item 2: after a version is answered, a reply is told it is answered.
    presentation('answered-checked-after-choice', "        if recorded is not None:\n", "        if False:\n",
                 'answer/after-answered-reply')
    presentation('answered-not-told',
                 "            self._tell(ev, receipt, 'This request version is already answered: %s.' % recorded['data'].get('ruling'))\n",
                 "", 'answer/after-answered-reply')
    # VELDO-0065 third review item 3: one message back per inbound message, recorded.
    presentation('tell-not-deduplicated', "        if self._entity(tid) is not None:\n            return\n", "",
                 'answer/tell-once-per-message')
    presentation('tell-keyed-by-text', "        tid = tell_id(ev['chat_id'], ev['platform_message_id'])\n",
                 "        tid = tell_id(ev['chat_id'], len(text))\n", 'answer/tell-once-per-message')
    # VELDO-0065 third review item 1: a notice in flight or of unknown outcome at the first presentation.
    projection('notice-intent-without-framing-pin',
               "        versions[framing_entity_id(aid)] = 0  # decided with the request not framed: pinned as absent\n", "",
               'projection/in-flight-notice-superseded')
    presentation('pending-notice-never-marked', "        self._reconcile_notices(request)\n", "",
                 'projection/in-flight-notice-superseded')
    # VELDO-0065 fourth review item 8: an unreadable revocation ledger fails closed.
    presentation('journal-reader-ignores-kind', "            if (entry.get('kind') != kind or not isinstance(entry.get('data'), dict)",
                 "            if (not isinstance(entry.get('data'), dict)", 'framing/ledger-read-fails-closed')
    # VELDO-0065 fourth review item 6: the whole reply NFKC-normalized before the split; Unicode hyphens separate.
    presentation('split-before-nfkc', "    cut = next((i for i, ch in enumerate(text) if ':' in unicodedata.normalize('NFKC', ch)), None)\n",
                 "    cut = next((i for i, ch in enumerate(text) if ch in ':\\uff1a'), None)\n", 'answer/reply-nfkc-before-split')
    # VELDO-0065 fourth review item 2: the accepted answer delivered again gets no reply.
    presentation('redelivered-answer-told',
                 "        return recorded is not None and (was.get('chat_id'), was.get('platform_message_id')) == (ev['chat_id'], ev['platform_message_id'])\n",
                 "        return False\n", 'answer/redelivered-answer-silent')
    presentation('redelivery-by-chat-only',
                 "        return recorded is not None and (was.get('chat_id'), was.get('platform_message_id')) == (ev['chat_id'], ev['platform_message_id'])\n",
                 "        return recorded is not None and was.get('chat_id') == ev['chat_id']\n", 'answer/redelivered-answer-silent')
    # VELDO-0065 fifth review item 1: the recorded answer delivered again is silent even after the request closed.
    presentation('redelivery-silent-only-while-pending', "        if self._is_recorded_answer(recorded, ev):\n",
                 "        if self._is_recorded_answer(recorded, ev) and self.inbox.brief(request).get('category') == 'pending':\n",
                 'answer/redelivered-after-closed')
    # VELDO-0065 fourth review item 7: a reply after the request left pending is told so, once.
    presentation('closed-not-told',
                 "            self._tell(ev, receipt, 'This request is no longer open, so this reply changes nothing.')\n", "",
                 'answer/reply-after-closed')
    presentation('closed-reported-as-stale', "            raise Refused('request_closed', 'the request is no longer pending')\n",
                 "            raise Refused('stale_presentation', 'the request is no longer pending')\n", 'answer/reply-after-closed')
    # VELDO-0065 fourth review item 3: the notices of the presented version and older ones, current first.
    presentation('older-sent-notice-preferred', "        return sorted(found, key=lambda n: -n['request_version'])\n",
                 "        return sorted(found, key=lambda n: (n['notice_state'] != 'sent', -n['request_version']))\n",
                 'projection/notices-per-version')
    presentation('only-first-notice-marked', "        for named in (data['supersedes'] or {}).get('notices') or []:\n",
                 "        for named in ((data['supersedes'] or {}).get('notices') or [])[:1]:\n", 'projection/notices-per-version')
    # VELDO-0065 fourth review item 4: a pending notice is reconciled against every presentation that named it.
    presentation('reconcile-current-only', "        for named_by in self.receipts(request):\n",
                 "        for named_by in [self.current(request) or {}]:\n",
                 'projection/pending-notice-reconciled-after-replacement')
    # VELDO-0065 fifth review item 2: nothing is sent for an edge whose scope does not cover the request.
    presentation('edge-scope-unchecked',
                 "        if not self.membership.scope_covers(edge_entry.get('scope'), receipt['request']['scope']):\n",
                 "        if False:\n", 'answer/closed-tell-after-edge-scope')
    # VELDO-0065 fifth review item 3: frame() refuses an unreadable ledger as the presenter does.
    presentation('frame-ledger-any-kind', "            if ledger is not None and (ledger.get('kind') != 'revocation_ledger' or not isinstance(ledger.get('data'), dict)\n",
                 "            if ledger is not None and (not isinstance(ledger.get('data'), dict)\n", 'framing/ledger-read-fails-closed')
    presentation('frame-ledger-digest-unchecked', "                                       or ledger.get('digest') != self.store.digest_of(\n",
                 "                                       or False and self.store.digest_of(\n", 'framing/ledger-read-fails-closed')
    # VELDO-0065 fifth review item 4: the rationale recorded is the owner's own text.
    presentation('rationale-nfkc-folded', "    return text[:cut], text[cut + 1:]\n",
                 "    return text[:cut], unicodedata.normalize('NFKC', text[cut + 1:])\n", 'answer/rationale-original-text')
    presentation('rationale-keeps-the-colon', "    return text[:cut], text[cut + 1:]\n",
                 "    return text[:cut], text[cut:]\n", 'answer/rationale-original-text')
    # VELDO-0065 fifth review: a reply to a presentation that no longer binds is told a new one is coming,
    # and only a request that left pending is closed.
    presentation('stale-not-told',
                 "                self._tell(ev, receipt, 'This presentation is out of date; a new presentation is coming. Reply to that one.')\n",
                 "                pass\n", 'answer/stale-current-told')
    # VELDO-0065 fifth review: the reviewer's uncaught mutants, each now red by a row case.
    presentation('x-drop-2043', "for c in '_-\\u2010\\u2011\\u2012\\u2043\\u2212'})",
                 "for c in '_-\\u2010\\u2011\\u2012\\u2212'})", 'answer/reply-nfkc-before-split')
    presentation('x-membership-pin-later', "                        principal: entry['entity_version'],\n",
                 "                        principal: (self._entity(principal) or {}).get('version', 0),\n", 'framing/frame-and-presenter-agree')
    presentation('x-versions-pin-later', "self.membership.VERSIONS_ENTITY: seen.get(self.membership.VERSIONS_ENTITY, {}).get('version', 0),",
                 "self.membership.VERSIONS_ENTITY: (self._entity(self.membership.VERSIONS_ENTITY) or {}).get('version', 0),", 'framing/frame-and-presenter-agree')
    presentation('x-notice-transition-any-notice', "    if (receipt.get('outcome') != 'published' or notice not in named\n",
                 "    if (receipt.get('outcome') != 'published'\n", 'projection/pending-notice-reconciled-after-replacement')
    # VELDO-0065 sixth review item 1: a promise only where one will come; nothing for an owner no longer current;
    # the recorded answer before any other message.
    presentation('stale-neutral-not-told',
                 "                self._tell(ev, receipt, 'This presentation is no longer current, so this reply changes nothing.')\n",
                 "                pass\n", 'answer/stale-current-told')
    presentation('owner-enrollment-unchecked', "        return (enrollment is not None\n", "        return True or (enrollment is not None\n",
                 'answer/owner-not-current-silent')
    presentation('owner-membership-unchecked',
                 "        if (not self.AC.active_member(entry, self.clock())[0] or entry['principal_type'] != 'person'\n                or not self.membership.scope_covers(entry.get('scope'), receipt['request']['scope'])):\n            return False\n        if self._ledger_revokes",
                 "        if False:\n            return False\n        if self._ledger_revokes", 'answer/owner-not-current-silent')
    presentation('answered-told-only-while-pending', "        if recorded is not None:\n",
                 "        if recorded is not None and self.inbox.brief(request).get('category') == 'pending':\n",
                 'answer/redelivered-after-closed')
    # VELDO-0065 sixth review item 2: the edge scope check comes before the redelivery check.
    presentation('redelivery-before-edge-scope',
                 "        # Authority first: an edge that may not act here learns nothing more, not even which message\n",
                 "        if self._is_recorded_answer(self._entity(answer_id(request, receipt['request_version'], receipt['owner'])), ev):\n"
                 "            raise Refused('already_answered', 'this is the recorded answer, delivered again')\n"
                 "        # Authority first: an edge that may not act here learns nothing more, not even which message\n",
                 'answer/closed-tell-after-edge-scope')
    # VELDO-0065 sixth review item 3: a ledger whose revoked has the wrong shape is a named refusal.
    presentation('frame-ledger-any-shape', "            if not isinstance(revoked, dict):\n",
                 "            if not isinstance(revoked, (dict, list, int)):\n", 'framing/ledger-read-fails-closed')
    # VELDO-0065 seventh review: an owner the revocation ledger revokes is not current.
    presentation('owner-ledger-unread', "        if self._ledger_revokes(state, owner):\n            return False\n", "",
                 'answer/owner-ledger-revoked-silent')
    presentation('ledger-owner-not-looked-up', "        return not isinstance(revoked, dict) or principal in revoked\n",
                 "        return not isinstance(revoked, dict)\n", 'answer/owner-ledger-revoked-silent')
    presentation('bindings-ledger-unread', "\n                or self._ledger_revokes(state, c['owner'])):\n", "):\n",
                 'answer/owner-ledger-revoked-silent')
    # VELDO-0066: the three declared falsifiers plus at least one different defect per named row.
    def attribution(name, old, new, row):
        add(66, name, '63_veldo_0066_attribution.py', 'control_channel_attribution.py', old, new, [row])

    # AC1 acquisition: every canonical field is the platform's own, and a kept update is confirmed.
    attribution('platform-date-from-clock',
                "            'message_id': _int(message.get('message_id')), 'date': _int(message.get('date')),\n",
                "            'message_id': _int(message.get('message_id')), 'date': int(time.time()),\n",
                'acquisition/platform-fields-retained')
    attribution('cursor-not-advanced',
                "                                                    'next_offset': record['update_id'] + 1}}}\n",
                "                                                    'next_offset': cursor.get('next_offset', 0)}}}\n",
                'acquisition/platform-fields-retained')
    # AC1 identity (declared falsifier): the display name as principal identity misattributes the
    # stranger who copies the owner's name and loses the renamed owner.
    attribution('display-name-as-identity',
                "    return sorted(principal for principal, chat in enrollments.items() if chat == sender['id'])\n",
                "    return sorted(principal for principal, chat in enrollments.items()\n"
                "                  if principal == str(sender.get('first_name', '')).casefold())\n",
                'attribution/stable-sender-identity')
    attribution('ambiguous-sender-first-wins',
                "        if len(principals) > 1:\n            return 'ambiguous_sender', known\n", "",
                'attribution/stable-sender-identity')
    # AC2 (declared falsifier): a chat and message id alone accept a reply to another presentation.
    attribution('replied-content-unchecked',
                "    if reply.get('text') != part.get('text') or reply.get('date') != part.get('date'):\n",
                "    if False:\n", 'attribution/binds-replied-presentation')
    attribution('replied-sender-unchecked',
                "    if _map(reply.get('from')).get('id') != bot or _map(reply.get('from')).get('is_bot') is not True:\n",
                "    if False:\n", 'attribution/binds-replied-presentation')
    attribution('reply-chat-unchecked',
                "        if fields['reply_chat_id'] != fields['chat_id']:\n            return 'reply_in_another_chat', known\n", "",
                'attribution/binds-replied-presentation')
    attribution('evidence-digest-unchecked',
                "    if record['source_digest'] != source_digest(record['source']):\n", "    if False:\n",
                'attribution/binds-replied-presentation')
    attribution('evidence-fields-unchecked',
                "    if record['fields'] != fields:\n", "    if False:\n", 'attribution/binds-replied-presentation')
    # AC3 (declared falsifier): an automation sender treated as the enrolled owner, then each kind alone.
    attribution('automation-sender-as-owner',
                "    if _map(message.get('from')).get('is_bot') is not False:\n",
                "    return None\n    if _map(message.get('from')).get('is_bot') is not False:\n",
                'attribution/person-only-authority')
    attribution('inline-bot-as-owner',
                "    if message.get('via_bot') is not None:\n        return 'sent through an inline bot'\n", "",
                'attribution/person-only-authority')
    attribution('business-bot-as-owner',
                "    if message.get('sender_business_bot') is not None:\n        return 'sent by a business bot'\n", "",
                'attribution/person-only-authority')
    attribution('offline-message-as-person',
                "    if message.get('is_from_offline'):\n        return 'sent by an implicit action'\n", "",
                'attribution/person-only-authority')
    attribution('service-member-as-person',
                "        if entry.get('principal_type') != 'person':\n            return 'not_a_person'\n", "",
                'attribution/person-only-authority')
    # VELDO-0067: each criterion's declared falsifier, and a second, different defect for every named row.
    def edges(name, module, old, new, row):
        add(67, name, '65_veldo_0067_edges.py', module, old, new, [row])

    # Installation: each module this change installs is laid down by the scaffold.
    edges('edge-enrollment-not-scaffolded', 'init_scaffold.py', '    ".veldo/control_channel_enrollment.py",\n', '',
          'install/assets')
    edges('edge-custody-not-scaffolded', 'init_scaffold.py', '    ".veldo/control_keys_custody.py",\n', '',
          'install/assets')
    # AC1: the possession proof is required, and the enrolled record is the channel schema.
    edges('edge-possession-unchecked', 'control_channel_enrollment.py',
          "            if not ok:\n                raise Refused('key_possession_unproven',",
          "            if False:\n                raise Refused('key_possession_unproven',",
          'enrollment/schema-and-possession')
    edges('edge-record-drops-connection-key', 'control_channel_enrollment.py',
          "           'connection_public_key': _key_text(signed['connection_public_key']), 'scope': list(signed['scope']),\n",
          "           'scope': list(signed['scope']),\n", 'enrollment/schema-and-possession')
    # AC1 (declared falsifier): the public key left out of the enrollment command digest, so a key
    # substituted after the steward signed is accepted; then authority coordinates taken from the envelope.
    edges('edge-digest-omits-public-key', 'authority_contract.py',
          '    payload = {k: command.get(k) for k in COMMAND_FIELDS}\n',
          '    payload = {k: command.get(k) for k in COMMAND_FIELDS}\n'
          '    if payload.get("operation") == "enroll_channel_edge":\n'
          '        payload["parameters"] = {k: v for k, v in (payload.get("parameters") or {}).items() if k != "public_key"}\n',
          'enrollment/binds-key-and-authority')
    edges('edge-authority-from-envelope', 'control_channel_enrollment.py',
          "                         delegation_version=state['delegation_version'])\n",
          "                         delegation_version=state['delegation_version'])\n"
          "        authority.update({f: envelope.get(f) for f in ('domain_uuid', 'repository_uuid', 'store_uuid')})\n",
          'enrollment/binds-key-and-authority')
    # AC1: a current steward only, and never a key someone already holds.
    edges('edge-steward-role-unchecked', 'control_channel_enrollment.py',
          "        if CM.STEWARD_ROLE not in (entry.get('roles') or []):\n", "        if False:\n",
          'enrollment/current-member-only')
    edges('edge-key-in-use-unchecked', 'control_channel_enrollment.py',
          "            if any(_key_text(params[f]) in held for f in ('public_key', 'connection_public_key')):\n",
          "            if False:\n", 'enrollment/current-member-only')
    # AC2 (declared falsifier): the edge permitted to sign a membership command; then an answer with a
    # field more than the canonical answer's.
    edges('signer-signs-membership-command', 'control_signer_answers.py',
          "        answer = request.get('assertion')\n        if shape_problems(answer):\n",
          "        answer = request.get('assertion')\n"
          "        if isinstance(answer, dict) and answer.get('operation') in CM.ADMIN_OPERATIONS:\n"
          "            return signed(answer)\n"
          "        if shape_problems(answer):\n", 'signer/purpose-refusal')
    edges('signer-extra-fields-accepted', 'control_signer_answers.py',
          "    if not isinstance(a, dict) or set(a) != set(ANSWER_FIELDS):\n",
          "    if not isinstance(a, dict) or not set(ANSWER_FIELDS) <= set(a):\n", 'signer/purpose-refusal')
    # AC2: the delegation's scope, and the presentation the canonical evidence actually replies to.
    edges('signer-delegation-scope-unchecked', 'control_signer_answers.py',
          "    if not CM.scope_covers(d.get('authority_scope'), a['authority_scope']):\n", "    if False:\n",
          'signer/delegation-dimensions')
    edges('signer-presentation-not-from-evidence', 'control_signer_answers.py',
          "    if (f['chat_id'] != receipt['chat_id'] or f['reply_chat_id'] != receipt['chat_id']\n",
          "    if False and (f['chat_id'] != receipt['chat_id'] or f['reply_chat_id'] != receipt['chat_id']\n",
          'signer/delegation-dimensions')
    # AC2: the attribution is the evidence's own, and evidence is signed for once, before it is decided.
    edges('signer-attribution-unbound', 'control_signer_answers.py', "    if attribution != wanted:\n", "    if False:\n",
          'signer/canonical-evidence')
    edges('signer-decided-evidence-resigned', 'control_signer_answers.py',
          "    if record.get('outcome') != 'acquired':\n", "    if False:\n", 'signer/canonical-evidence')
    # AC3 (declared falsifier): an answer accepted with a retired edge key; then a retirement that does
    # not end the key.
    edges('acceptance-retired-edge-current', 'control_channel_presentation.py',
          "        return self.AC.active_key(keys, edge, now)\n",
          "        return self.AC.active_key([dict(k, retired_at=None) for k in keys], edge, now)\n",
          'acceptance/current-edge-and-actor')
    edges('retirement-dated-in-the-future', 'control_channel_enrollment.py',
          "    return {kid: {'kind': 'verification_key', 'data': dict(data, retired_at=at, retired_by=params['retired_by'])},\n",
          "    return {kid: {'kind': 'verification_key', 'data': dict(data, retired_at=at + 86400, retired_by=params['retired_by'])},\n",
          'acceptance/current-edge-and-actor')
    # AC3: a worker tool cannot read the private edge key.
    edges('custody-protected-directory-granted', 'control_keys_custody.py', "    chain = set(protected)\n",
          "    chain = set()\n", 'custody/worker-cannot-read-key')
    edges('custody-not-restricted', 'control_keys_custody.py',
          "        if libc.syscall(ctypes.c_long(restrict_self), ctypes.c_int(ruleset), ctypes.c_uint32(0)) < 0:\n",
          "        if False:\n", 'custody/worker-cannot-read-key')
    # Scope coverage (landed VELDO-0025, found through VELDO-0064's review): a plain-string inner scope
    # such as a repository id was read as the empty set, so every named scope covered it.
    def scope(name, old, new, rows=('membership/scope-covers-named-string',)):
        add(25, name, '61_scope_covers.py', 'control_membership.py', old, new, list(rows))
        result[-1]['siblings'] = True

    scope('scope-string-inner-as-empty',
          '    if isinstance(scope, str):\n        return {scope}\n',
          '    if isinstance(scope, str):\n        return set()\n')
    scope('scope-malformed-as-empty',
          '    if o is _MALFORMED or i is _MALFORMED:\n        return False\n',
          '    if o is _MALFORMED or i is _MALFORMED:\n        o = set() if o is _MALFORMED else o\n        i = set() if i is _MALFORMED else i\n')
    scope('scope-star-list-not-universal',
          '        return None if "*" in scope else set(scope)\n',
          '        return set(scope)\n', ('membership/scope-forms-agree',))
    # VELDO-0045: each criterion's declared falsifier, a second and different defect of its row, and a
    # driven defect for every other row the suite asserts.
    def runtime(name, module, old, new, row):
        add(45, name, '62_veldo_0045_runtime.py', module, old, new, [row])

    runtime('runtime-content-enforcement-bypassed', 'control_runtime.py',
            "    if content_digest(kept) != entry['content'].get('sha256'):\n",
            "    if False:  # defect: hash enforcement bypassed, the genuine wheel's content is never compared\n",
            'runtime/altered-wheel-refused')
    runtime('runtime-record-digest-unchecked', 'control_runtime.py',
            "            if algorithm != 'sha256' or not target.is_file() or _record_hash(target.read_bytes()) != value:\n",
            "            if algorithm != 'sha256' or not target.is_file():  # defect: a file is never hashed against RECORD\n",
            'runtime/altered-wheel-refused')
    runtime('runtime-lock-hash-unchecked', 'control_runtime.py',
            "        if entry.get('sha256') != pinned:\n",
            "        if False:  # defect: the lock's artifact hash is never compared with the registry's\n",
            'runtime/altered-hash-refused')
    runtime('runtime-lock-hash-prefix-only', 'control_runtime.py',
            "        if entry.get('sha256') != pinned:\n",
            "        if str(entry.get('sha256'))[:16] != pinned[:16]:  # defect: a digest prefix stands for the digest\n",
            'runtime/altered-hash-refused')
    runtime('runtime-requirements-ignored', 'control_runtime.py',
            "    for requirement in report['requirements']:\n",
            "    for requirement in []:  # defect: the installed requirements are never evaluated\n",
            'runtime/omitted-dependency-refused')
    runtime('runtime-installed-set-unchecked', 'control_runtime.py',
            "        if found is None:\n            problems.append('missing_dependency:' + name)\n            continue\n",
            "        if found is None:\n            continue  # defect: a locked distribution may be absent\n",
            'runtime/omitted-dependency-refused')
    runtime('runtime-license-unjudged', 'control_runtime.py',
            "    return ['license_unapproved:%s:%s' % (name, t) for t in identifiers if t not in APPROVED_LICENSES] or (\n",
            "    return [] or (  # defect: any recorded license is accepted\n",
            'runtime/records-cover-lock')
    runtime('runtime-unrecorded-package-passes', 'control_runtime.py',
            "        if entry is None:\n            problems.append('unrecorded_package:' + name)\n            continue\n",
            "        if entry is None:\n            continue  # defect: a locked package needs no record\n",
            'runtime/records-cover-lock')
    runtime('runtime-qualification-after-entry-point', 'control_runtime.py',
            "    return source.replace(guard, '\\n' + QUALIFICATION + guard, 1)\n",
            "    return source + '\\n' + QUALIFICATION  # defect: registered after the entry point has served\n",
            'runtime/workload')
    runtime('runtime-qualification-without-result', 'control_runtime.py',
            "answers['suspend'].get('resume'), supplied)\n",
            "answers['suspend'].get('resume'), [])  # defect: the cycle advances without its supplied result\n",
            'runtime/workload')
    runtime('runtime-taxonomy-unknown', 'control_runtime.py',
            "    report['taxonomy'] = sorted({TAXONOMY.get(p.split(':', 1)[0], 'unknown_outcome') for p in report['problems']})\n",
            "    report['taxonomy'] = sorted({'unknown_outcome' for p in report['problems']})  # defect: every refusal unclassified\n",
            'runtime/observations')
    runtime('runtime-counts-omitted', 'control_runtime.py',
            "    report['counts'] = dict(COUNTS)\n", "",
            'runtime/observations')
    runtime('scaffold-omits-runtime-lock', 'init_scaffold.py',
            '    ".veldo/control_graph_lock.py",\n', '',
            'journey/assets-installed')
    runtime('scaffold-omits-runtime-records', 'init_scaffold.py',
            '_RUNTIME_ASSETS = [("runtime/langgraph-records.json", ".veldo/runtime/langgraph-records.json")]\n',
            '_RUNTIME_ASSETS = []  # defect: the records are never laid down\n',
            'journey/assets-installed')
    runtime('runtime-records-source-fallback', 'control_runtime.py',
            "    return HERE / rel\n",
            "    return HERE / rel if (HERE / rel).is_file() else Path.cwd() / 'engine' / rel  # defect: the source tree\n",
            'journey/omitted-asset-named')
    runtime('runtime-missing-asset-unnamed', 'control_runtime.py',
            "    missing = ['missing_asset:.veldo/' + rel for rel in JOURNEY if not _asset(rel).is_file()]\n"
            "    if missing:\n        return _finish(report, missing)\n",
            "    missing = []  # defect: an omitted asset is found by whatever reads it first\n"
            "    if missing:\n        return _finish(report, missing)\n",
            'journey/omitted-asset-named')
    runtime('authorization-imports-langgraph', 'authorization.py',
            'from pathlib import Path\nimport json\n',
            'from pathlib import Path\nimport json\nimport langgraph\n',
            'enforcement/no-runtime')
    runtime('authorization-reads-runtime-by-path', 'authorization.py',
            'from pathlib import Path\nimport json\n',
            'from pathlib import Path\nimport json\n'
            'try:  # defect: reads the graph runtime by path, past every import check\n'
            '    import glob as _g, os as _o, pwd as _p\n'
            "    _g.glob(_p.getpwuid(_o.getuid()).pw_dir + '/.local/share/veldo/langgraph/*/lib/python3.12/site-packages/langgraph/*.py')\n"
            'except OSError:\n    pass\n',
            'enforcement/no-runtime')
    runtime('enforcement-catalog-unread', 'control_runtime.py',
            "            if declared and not declared.group(1).startswith('required:'):\n                continue\n",
            "            if declared:\n                continue  # defect: a required catalog slot is not an entry\n",
            'enforcement/entries-enumerated')
    runtime('enforcement-guard-unread', 'control_runtime.py',
            "    for script in (GATE, GUARD):\n",
            "    for script in (GATE,):  # defect: the guard's entries are not enumerated\n",
            'enforcement/entries-enumerated')
    runtime('graph-unavailable-mislabelled', 'control_runtime.py',
            "        raise graph.Refused('runtime_unavailable', 'the graph runtime is not activated ('",
            "        raise graph.Refused('unknown_outcome', 'the graph runtime is not activated ('",
            'enforcement/graph-unavailable')
    runtime('graph-probe-absent-only', 'control_runtime.py',
            "        for label, home in (('absent', empty), ('hidden', None)):\n",
            "        for label, home in (('absent', empty),):  # defect: the hidden runtime is never asked\n",
            'enforcement/graph-unavailable')
    runtime('runtime-hide-not-enforced', 'control_runtime.py',
            "            raise PermissionError('the graph runtime is hidden: ' + _hide_os.fsdecode(place))\n", "",
            'enforcement/graph-unavailable')
    # VELDO-0039: each criterion's declared falsifier and further defects, each against the one
    # suite row it names. Anchors are exact text in the production modules the suite installs.
    def dispatch(name, module, old, new, row, also=()):
        add(39, name, '62_veldo_0039_dispatch.py', module, old, new, ['dispatch/' + row], also)

    # Review of bb72994, B1: a worker that closes its output is still held to its deadline. Since
    # VELDO-0040 the reap is one notification loop, so the same three defects are made there: the end
    # of output waits for the worker with no deadline, the deadline is late, or it stops the worker.
    closed = ("                        if not chunk:\n"
              "                            poller.unregister(output)\n")
    dispatch('dispatch-closed-output-not-held', 'control_launch.py', closed,
             closed + "                            code = worker.wait()  # defect: the deadline ends with the output\n",
             'deadline-after-closed-output')
    dispatch('dispatch-closed-output-late-deadline', 'control_launch.py',
             "                due = min(contract['deadline'] if cause is None and code is None else math.inf,\n",
             "                due = min(contract['deadline'] + 30 if cause is None and code is None else math.inf,\n",
             'deadline-after-closed-output')
    dispatch('dispatch-closed-output-killed-at-close', 'control_launch.py', closed,
             closed + "                            begin('deadline', time.time())  # defect: stopped when it closes\n",
             'deadline-after-closed-output')
    # Review of bb72994, B2: a remote deadline stop is unknown and holds the unit.
    remote_stop = "        if remote and termination['deadline_stop']:\n"
    dispatch('dispatch-remote-stop-exits', 'control_launch.py', remote_stop,
             "        if False:\n", 'remote-stop-holds-unit')
    dispatch('dispatch-remote-stop-needs-signal', 'control_launch.py', remote_stop,
             "        if remote and termination['deadline_stop'] and termination['signal'] is None:\n",
             'remote-stop-holds-unit')
    # Integration with VELDO-0053: the receiver's recheck judges its configured workspace.
    dispatch('dispatch-receiver-store-only-gate', 'control_launch.py',
             "                           workspace=self.config.get('workspace'))",
             "                           workspace=None)", 'launch-results')
    # AC1, declared: the worker is spawned before the contract is recorded. The fixed code guards it
    # twice (the runner commits before invoking; the receiver spawns only after an acceptance that
    # needs the prepared record), so the defect is both edits.
    dispatch('dispatch-spawn-before-contract', 'control_launch.py',
             "            self.dispatches.prepare(contract, now=now)\n",
             "            self.early = self.receiver(contract)  # defect: invoked before the contract commits\n"
             "            self.dispatches.prepare(contract, now=now)\n",
             'contract-before-launch',
             also=[("        dispatch_id = contract['dispatch_id']\n        record = self.dispatches.record(dispatch_id)\n",
                    "        dispatch_id = contract['dispatch_id']\n"
                    "        self._spawn(dispatch_id, self.dispatches.receipt(dispatch_id, 'accept'),\n"
                    "                    self.config['adapters'][contract['capability']['adapter']]).stdin.close()  # defect\n"
                    "        record = self.dispatches.record(dispatch_id)\n")])
    dispatch('dispatch-spawn-before-acceptance', 'control_launch.py',
             "        me = dict(process_identity(os.getpid()), principal=self.config['principal'])\n",
             "        spawned = self._spawn(dispatch_id, self.dispatches.receipt(dispatch_id, 'accept'), adapter)  # defect\n"
             "        me = dict(process_identity(os.getpid()), principal=self.config['principal'])\n",
             'contract-before-launch',
             also=[("            worker = self._spawn(dispatch_id, acceptance, adapter)\n",
                    "            worker = spawned\n")])
    dispatch('dispatch-holder-not-consulted', 'control_dispatch.py',
             "        holder = index.get('dispatch_id')\n",
             "        holder = None  # defect: the unit and station's holder is not consulted\n",
             'one-active-per-unit-station')
    dispatch('dispatch-hold-not-recorded', 'control_dispatch.py',
             "        return {rid: {'kind': RECORD_KIND, 'data': record}, iid: {'kind': INDEX_KIND, 'data': slot}}\n",
             "        return {rid: {'kind': RECORD_KIND, 'data': record}}  # defect: nothing holds the unit and station\n",
             'one-active-per-unit-station')
    # AC2, declared: a new dispatch is created for an unknown result.
    dispatch('dispatch-new-dispatch-for-unknown', 'control_dispatch.py',
             "HOLDING = ('prepared', 'accepted', 'running', 'unknown')\n",
             "HOLDING = ('prepared', 'accepted', 'running')  # defect: an unknown outcome frees its unit\n",
             'unknown-never-relaunched')
    dispatch('dispatch-unknown-frees-unit', 'control_dispatch.py',
             "    if target not in HOLDING:\n",
             "    if target not in HOLDING or target == 'unknown':  # defect: an unknown outcome releases its unit\n",
             'unknown-never-relaunched')
    dispatch('dispatch-lost-answer-as-refused', 'control_launch.py',
             "            record = self.dispatches.unknown(self.dispatch_id, digest, 'launch_evidence_missing', now=self.clock(),\n"
             "                                             expected_state='accepted')\n",
             "            record = self.dispatches.refuse(self.dispatch_id, digest, 'launch_evidence_missing', now=self.clock(),\n"
             "                                            expected_state='accepted')\n",
             'launch-results')
    dispatch('dispatch-receiver-identity-recorded', 'control_launch.py',
             "            process = process_identity(worker.pid)\n",
             "            process = process_identity(os.getpid())  # defect: the receiver's own identity\n",
             'launch-results')
    dispatch('dispatch-spawn-failure-as-unknown', 'control_launch.py',
             "            refusal = 'spawn_failed:' + errno.errorcode.get(error.errno or 0, type(error).__name__)\n"
             "            self.dispatches.refuse(dispatch_id, contract_digest, refusal, now=time.time(), expected_state='accepted')\n",
             "            refusal = 'spawn_failed:' + errno.errorcode.get(error.errno or 0, type(error).__name__)\n"
             "            self.dispatches.unknown(dispatch_id, contract_digest, refusal, now=time.time(), expected_state='accepted')\n",
             'launch-results')
    dispatch('dispatch-identity-from-worker-output', 'control_launch.py',
             "        line, _, carry = pending.partition(b'\\n')\n        message = json.loads(line)\n",
             "        line, _, carry = pending.partition(b'\\n')\n"
             "        if b'\\n' in carry or select.select([worker.stdout], [], [], 5)[0]:  # defect: a later line is read\n"
             "            carry += b'' if b'\\n' in carry else os.read(worker.stdout.fileno(), 65536)\n"
             "            line, _, carry = carry.partition(b'\\n')\n"
             "        message = json.loads(line)\n",
             'launch-results')
    dispatch('dispatch-worker-environment-reduced', 'control_launch.py',
             "        environment = dict(os.environ)\n",
             "        environment = {'PATH': os.environ.get('PATH', os.defpath), 'LANG': 'C.UTF-8'}  # defect\n",
             'contract-before-launch')
    dispatch('dispatch-acceptance-without-recheck', 'control_launch.py',
             "            refusal = self._recheck(contract)\n",
             "            refusal = None  # defect: the accepting boundary does not recheck the station decision\n",
             'launch-results')
    # AC3, declared: one worker's result is applied to another dispatch.
    dispatch('dispatch-result-unbound', 'control_dispatch.py',
             "        if params.get('process') != record['process']:\n"
             "            raise Refused('binding_mismatch:process', 'this termination belongs to another process')\n",
             "        record['process'] = params.get('process')  # defect: the result's own process is taken as bound\n",
             'result-binding')
    dispatch('dispatch-contract-digest-unbound', 'control_dispatch.py',
             "    if params.get('contract_digest') != record['contract_digest']:\n"
             "        raise Refused('binding_mismatch:contract_digest', 'this observation belongs to another dispatch')\n",
             "    pass  # defect: an observation is not held to its dispatch's contract\n",
             'result-binding')
    guard = "    if record['state'] not in allowed or params.get('expected_state') not in (None, record['state']):\n"
    dispatch('dispatch-exited-moves-again', 'control_dispatch.py', guard,
             "    if (record['state'] not in allowed and record['state'] != 'exited')"
             " or params.get('expected_state') not in (None, record['state']):  # defect\n",
             'transitions-from-schema')
    dispatch('dispatch-ended-state-ignored', 'control_dispatch.py', guard,
             "    if record['state'] not in allowed:  # defect: the state an observation ends is not checked\n",
             'transitions-from-schema')
    dispatch('dispatch-unknown-after-exit', 'control_dispatch.py',
             "    'unknown': (('accepted', 'running'), 'unknown'),\n",
             "    'unknown': (('accepted', 'running', 'exited'), 'unknown'),  # defect: an ended dispatch reopens\n",
             'transitions-from-schema')
    dispatch('dispatch-exit-lands-unit', 'control_launch.py',
             "            self._retire(record['dispatch_id'], 'completed' if clean else 'failed', 'worker_reaped')\n",
             "            self._retire(record['dispatch_id'], 'completed' if clean else 'failed', 'worker_reaped')\n"
             "            if clean:  # defect: a clean exit is taken as the unit's landing\n"
             "                identity = 'receipt:revision_landed:' + record['dispatch_id']\n"
             "                self.dispatches.store.execute(self.dispatches.conn, dict(\n"
             "                    command_id='landed/' + record['dispatch_id'], principal=self.dispatches.principal,\n"
             "                    operation='upsert_entity', nonce='landed/' + record['dispatch_id'], artifact_digests=[],\n"
             "                    expected_versions={identity: 0}, parameters=dict(entity_id=identity, kind='completion_receipt',\n"
             "                    data={'fact': 'revision_landed', 'subject': {'id': record['contract']['unit'], 'revision': 1}})),\n"
             "                    self.dispatches.signer, self.dispatches.sign, self.dispatches.generation)\n",
             'terminal-not-completion')
    dispatch('dispatch-authority-unchecked', 'control_dispatch.py',
             "    _authorize(conn, params.get('principal'), params.get('repository'), now)\n",
             "    pass  # defect: the principal's authority is not checked\n",
             'service-principals-only')
    dispatch('dispatch-any-principal-type', 'control_dispatch.py',
             "entry.get('principal_type') not in AC.BOUNDARIES['dispatch_acceptance']",
             "entry.get('principal_type') not in AC.PRINCIPAL_TYPES",
             'service-principals-only')
    dispatch('dispatch-stopped-not-reported', 'control_dispatch.py',
             "stopped=sorted(d for d, s in states.items() if s == 'unknown'),",
             "stopped=sorted(d for d, s in states.items() if s == 'refused'),",
             'observations')
    dispatch('dispatch-refusal-not-observed', 'control_dispatch.py',
             "            self.observe(dict(event, outcome='refused', refusal=error.code, taxonomy=taxonomy(error.code)))\n",
             "            pass  # defect: a refusal is not observed\n",
             'observations')
    dispatch('dispatch-receiver-not-installed', 'init_scaffold.py',
             '    ".veldo/control_launch.py",\n', '', 'installed-assets')
    dispatch('dispatch-authority-not-installed', 'init_scaffold.py',
             '    ".veldo/control_dispatch.py",\n', '', 'installed-assets')

    # VELDO-0040: each criterion's declared falsifier and further defects, each against the one suite
    # row it names. Where the fixed code guards a defect twice (it installs a control and then checks
    # the control is installed), the defect is both edits.
    def contain(name, module, old, new, row, also=()):
        add(40, name, '63_veldo_0040_containment.py', module, old, new, ['containment/' + row], also)

    # AC1, declared: the worker is launched outside its dispatch group.
    contain('containment-launch-outside-group', 'control_containment.py',
            "        return head + ['--'] + list(argv)\n",
            "        return list(argv)  # defect: the worker is launched outside its dispatch group\n", 'dedicated-group')
    contain('containment-wrapper-leaves-group', 'control_launch.py',
            "    if held is not None and not C.released(0):\n        os._exit(125)\n",
            "    if held is not None and not C.released(0):\n        os._exit(125)\n"
            "    if held is not None:  # defect: the engine is started in the receiver's group, not its own\n"
            "        Path('/sys/fs/cgroup', C.cgroup_of(os.getppid()).lstrip('/'), 'cgroup.procs').write_text(str(os.getpid()))\n",
            'dedicated-group')
    contain('containment-shared-group', 'control_containment.py',
            "    return UNIT_PREFIX + hashlib.sha256(str(dispatch_id).encode()).hexdigest()[:32] + '.scope'\n",
            "    return UNIT_PREFIX + 'shared.scope'  # defect: dispatches share one group\n", 'dedicated-group')
    contain('containment-unknown-setting-ignored', 'control_containment.py',
            "    problems = ['invalid_input:profile:unknown:' + str(name) for name in profile\n"
            "                if name not in SETTINGS and name not in FIELDS]\n",
            "    problems = []  # defect: a setting the profile does not know is silently ignored\n",
            'unqualified-profile-refused')
    contain('containment-kind-unchecked', 'control_containment.py',
            "    if not problems and profile['kind'] != LINUX:\n        problems.append('unavailable_service:profile:kind')\n",
            "", 'unqualified-profile-refused')
    contain('containment-profile-after-acceptance', 'control_launch.py',
            "        self.qualification = C.qualify(self.profile)\n        return self.qualification['refusal']\n",
            "        return None  # defect: the host profile is not qualified before acceptance\n",
            'unqualified-profile-refused')
    # AC2, declared: the configured elapsed-runtime cap is ignored.
    contain('containment-runtime-cap-ignored', 'control_containment.py',
            "                 ('RuntimeMaxSec', _usec(s['runtime_seconds'])), ('TimeoutStopSec', _usec(s['kill_grace_seconds'])),\n",
            "                 ('TimeoutStopSec', _usec(s['kill_grace_seconds'])),  # defect: the runtime cap is ignored\n",
            'runtime-cap',
            also=[("            'runtime_seconds': {'RuntimeMaxUSec': round(s['runtime_seconds'] * 10 ** 6)},\n", "")])
    contain('containment-memory-cap-ignored', 'control_containment.py',
            "        props = [('MemoryMax', str(s['memory_bytes'])), ('MemorySwapMax', '0'), ('CPUQuota', '%d%%' % s['cpu_percent']),\n",
            "        props = [('CPUQuota', '%d%%' % s['cpu_percent']),  # defect: the memory cap is ignored\n",
            'caps-installed',
            also=[("            'memory_bytes': {'memory.max': str(s['memory_bytes'] // page * page), 'memory.swap.max': '0',\n"
                   "                             'OOMPolicy': 'stop'},\n", "")])
    contain('containment-cpu-cap-ignored', 'control_containment.py',
            "('MemorySwapMax', '0'), ('CPUQuota', '%d%%' % s['cpu_percent']),\n",
            "('MemorySwapMax', '0'),  # defect: the CPU cap is ignored\n",
            'caps-installed',
            also=[("            'cpu_percent': {'cpu.max': '%d 100000' % (s['cpu_percent'] * 1000)},\n", "")])
    contain('containment-file-limit-ignored', 'control_containment.py',
            "    resource.setrlimit(resource.RLIMIT_FSIZE, (size, size))\n",
            "    pass  # defect: the per-file storage limit is not applied\n",
            'caps-installed',
            also=[("            'file_bytes': {'Max file size': (str(s['file_bytes']), str(s['file_bytes']))},\n", "")])
    contain('containment-concurrency-uncounted', 'control_containment.py',
            "            if len(live) >= self.settings['concurrency']:\n",
            "            if False:  # defect: the live groups are not held to the concurrency cap\n", 'caps-installed')
    contain('containment-required-setting-optional', 'control_containment.py',
            "            if rule['required']:\n                problems.append('invalid_input:profile:%s:absent' % name)\n",
            "            pass  # defect: a required setting may be absent\n", 'required-settings-refused')
    contain('containment-zero-seconds-accepted', 'control_containment.py',
            "math.isfinite(value) and 0 < value <= 366 * 86400\n",
            "math.isfinite(value) and 0 <= value <= 366 * 86400  # defect: zero seconds is taken\n",
            'required-settings-refused')
    # AC3, declared: a stop stops only the parent.
    contain('containment-stop-only-parent', 'control_containment.py',
            "        elif stage == 'terminate':\n            self.group.terminate()\n"
            "        elif stage == 'kill':\n            self.group.kill()\n",
            "        elif stage == 'terminate':\n"
            "            with contextlib.suppress(ProcessLookupError):\n"
            "                os.kill(self.pid, signal.SIGTERM)  # defect: only the parent is stopped\n"
            "        elif stage == 'kill':\n"
            "            with contextlib.suppress(ProcessLookupError):\n"
            "                os.kill(self.pid, signal.SIGKILL)  # defect: only the parent is stopped\n",
            'stop-escalation')
    contain('containment-terminate-without-grace', 'control_containment.py',
            "{'cooperative': stop_grace, 'terminate': kill_grace,",
            "{'cooperative': 0, 'terminate': kill_grace,", 'stop-escalation')
    contain('containment-kill-without-grace', 'control_containment.py',
            "{'cooperative': stop_grace, 'terminate': kill_grace,",
            "{'cooperative': stop_grace, 'terminate': 0,", 'stop-escalation')
    contain('containment-no-cooperative-step', 'control_containment.py',
            "            self._step('cooperative' if adapter_alive else 'terminate', now)\n",
            "            self._step('terminate', now)  # defect: the adapter is not asked first\n", 'cooperative-stop')
    contain('containment-exit-polled', 'control_launch.py',
            "                timeout = None if due == math.inf else max(0, math.ceil((due - time.time()) * 1000))\n",
            "                timeout = 50  # defect: the reap wakes every 50 ms to look\n", 'exit-notified')
    contain('containment-exit-leaves-descendants', 'control_launch.py',
            "                if code is not None and (group is None or not group.populated()):\n",
            "                if code is not None:  # defect: the exit ends the reap while the group still runs\n",
            'ordinary-exit',
            also=[("                        if stop is not None and group.populated():\n"
                   "                            stop.adapter_exited(time.time())\n", "")])
    contain('containment-retire-without-looking', 'control_containment.py',
            "    return {'terminated': process is None or not alive(process), 'cleaned': observed != 'populated',\n",
            "    return {'terminated': process is None or not alive(process), 'cleaned': True,  # defect\n",
            'retire-after-empty')
    contain('containment-group-not-reported', 'control_launch.py',
            "                   'group': group.report() if group else None})\n",
            "                   'group': None})  # defect: the receiver does not report the worker's group\n",
            'observations')
    contain('containment-not-installed', 'init_scaffold.py',
            '    ".veldo/control_containment.py",\n', '', 'installed-assets')
    # VELDO-0049: each criterion's declared falsifier and further defects, each against the one
    # suite row it names. Anchors are exact text in the production modules suite 63 installs.
    def floor(name, old, new, row, also=(), module='dispatch.py'):
        add(49, name, '63_veldo_0049_floor.py', module, old, new, ['floor/' + row], also)

    guard = ('        if self._authority is not None or EL.enrolled(self.repo_root):\n'
             '            raise EL.Stopped("status_projection_owned")\n')
    unguarded = '        pass  # defect: an enrolled unit\'s status is written here\n'
    # AC1, declared: a review status written directly, without accepted proof; the build skips the
    # authority and its status write is not refused, so the spec file says review.
    floor('floor-status-written-directly',
          '        if floor is not None:\n            return self._accept_build(floor, unit, result)\n',
          '        if floor is not None and False:  # defect: the build writes its review status itself\n'
          '            return self._accept_build(floor, unit, result)\n',
          'authority-to-projection', also=[(guard, unguarded)])
    floor('floor-projection-before-acceptance',
          '        try:\n            floor.accept_build(sid, commit=',
          '        floor.publish(sid)  # defect: published before the authority accepted the build\n'
          '        try:\n            floor.accept_build(sid, commit=',
          'authority-to-projection',
          also=[('        projection = floor.publish(sid)\n        return {"ok": True, "kind": "build"',
                 '        projection = {}\n        return {"ok": True, "kind": "build"')])
    floor('floor-proof-not-judged', '    problems = proof_problems(manifest, unit)\n',
          '    problems = []  # defect: the proof is not judged\n', 'build-acceptance')
    floor('floor-gate-not-required', '    if not isinstance(gate, dict) or gate.get("green") is not True:\n',
          '    if False:  # defect: the gate\'s answer is not required\n', 'build-acceptance')
    floor('floor-stale-proof-accepted',
          '    if changed is None or any(not p.startswith(evidence) for p in changed):\n',
          '    if changed is None:  # defect: what changed after the proof\'s commit is not read\n', 'build-acceptance')
    floor('floor-claim-holder-unbound',
          '    if status != "owned" or not _text(holder) or claim.get("holder") != holder:\n',
          '    if status != "owned":  # defect: any holder may hand a build to review\n', 'build-acceptance')
    floor('floor-status-guard-removed', guard, unguarded, 'status-write-sites')
    floor('floor-status-write-unregistered', '    ("Dispatcher._dispatch_review", "shipped"),\n', '',
          'status-write-sites')
    floor('floor-authority-not-required',
          '            if EL.enrolled(self.repo_root):\n                raise EL.Stopped("authority_required")\n',
          '            pass  # defect: an enrolled repository runs without its authority\n', 'status-write-sites')
    floor('floor-rebuild-while-held',
          '            if state not in FLOOR_TRANSITIONS["accept_build"][0]:\n',
          '            if False:  # defect: a unit the authority holds in review is built again\n',
          'build-acceptance')
    floor('floor-land-retry-reassigns',
          '        if (floor.record(sid) or {}).get("state") == "handoff":\n',
          '        if False:  # defect: a failed land is not retried from its handoff\n',
          'land-retry-from-handoff')
    # AC2, declared: the builder is accepted as its own reviewer (both places the authority asks).
    floor('floor-builder-reviews-itself',
          '        raise FloorRefused("not_authorized:reviewer", str(reviewer))\n'
          '    if reviewer in (record.get("builders") or [record["builder"]]):\n'
          '        raise FloorRefused("reviewer_not_independent", "a builder of this unit cannot review it")\n',
          '        raise FloorRefused("not_authorized:reviewer", str(reviewer))\n'
          '    # defect: the builder may be assigned as its own reviewer\n',
          'review-independence',
          also=[('        raise FloorRefused("binding_mismatch:reviewer", "the receipt names another reviewer")\n'
                 '    if reviewer in (record.get("builders") or [record["builder"]]):\n'
                 '        raise FloorRefused("reviewer_not_independent", "a builder of this unit cannot review it")\n',
                 '        raise FloorRefused("binding_mismatch:reviewer", "the receipt names another reviewer")\n'
                 '    # defect: the builder\'s own receipt is accepted\n')])
    floor('floor-review-signature-unchecked',
          '    if not _signed_by(conn, reviewer, params["now"], body, signature):\n',
          '    if False:  # defect: the receipt\'s signature is not verified\n', 'review-independence')
    floor('floor-review-source-unbound',
          '    if body.get("source") != record["source"]["commit"]:\n'
          '        raise FloorRefused("binding_mismatch:source", "the receipt reviewed another commit")\n',
          '    pass  # defect: the receipt may review another commit\n', 'review-binding')
    floor('floor-review-proof-unbound',
          '    if body.get("proof") != record["proof"]["digest"]:\n',
          '    if False:  # defect: the receipt may review another proof\n', 'review-binding')
    floor('floor-review-output-unbound',
          '    if (dispatch.get("termination") or {}).get("output_digest") != _digest(printed):\n',
          '    if False:  # defect: the receipt need not be what the review dispatch printed\n', 'review-binding')
    floor('floor-review-context-unbound', '    if given.get("payload") != payload:\n',
          '    if False:  # defect: the reviewer may be launched with more than its assignment\n', 'review-binding')
    floor('floor-review-dispatch-source-unbound',
          '    if (contract.get("source") or {}).get("commit") != record["source"]["commit"]:\n',
          '    if False:  # defect: the reviewer may be launched at another commit\n', 'review-binding')
    floor('floor-duplicate-reviewer',
          '    if any(r["reviewer"] == reviewer and r["attempt"] == attempt for r in record["reviews"]):\n',
          '    if False:  # defect: one principal may fill a second review position\n', 'review-policy-count')
    floor('floor-policy-count-ignored', '    if len(passing) < need:\n',
          '    if len(passing) < 1:  # defect: one review hands off whatever the policy requires\n',
          'review-policy-count')
    # A builder of an EARLIER attempt is a builder of the unit: independence is not only from the latest.
    floor('floor-earlier-builder-reviews',
          '        raise FloorRefused("not_authorized:reviewer", str(reviewer))\n'
          '    if reviewer in (record.get("builders") or [record["builder"]]):\n',
          '        raise FloorRefused("not_authorized:reviewer", str(reviewer))\n'
          '    if reviewer == record["builder"]:  # defect: only the latest attempt\'s builder is refused\n',
          'no-builder-reviews',
          also=[('        raise FloorRefused("binding_mismatch:reviewer", "the receipt names another reviewer")\n'
                 '    if reviewer in (record.get("builders") or [record["builder"]]):\n',
                 '        raise FloorRefused("binding_mismatch:reviewer", "the receipt names another reviewer")\n'
                 '    if reviewer == record["builder"]:  # defect: only the latest attempt\'s builder is refused\n')])
    # Review of d46451c, B1: a blocking review dimension and a finding-less failing verdict stay open.
    floor('floor-dimension-block-not-kept',
          '        if dimension.dimension_blocks(body):\n            blocking.append({"dimension": label, "block": body.get(label)})\n',
          '        if False:  # defect: a blocking dimension returns the unit but opens no finding\n            blocking.append({"dimension": label, "block": body.get(label)})\n',
          'blocking-verdicts-stay-open')
    floor('floor-bare-fail-not-kept',
          '    if body.get("verdict") not in EX.PASSING_VERDICTS and not blocking:\n',
          '    if False:  # defect: a failing verdict with no listed finding opens nothing\n',
          'blocking-verdicts-stay-open')
    floor('floor-notes-counted-as-blocking',
          '    blocking = list(PC.blocking_findings(body))\n',
          '    blocking = list(PC.blocking_findings(body)) + list(body.get("findings") or [])  # defect: every note blocks\n',
          'blocking-verdicts-stay-open')
    # AC3, declared: a later pass discards the unresolved finding.
    floor('floor-pass-erases-finding', '    findings = dict(record["findings"])\n',
          '    findings = {} if verdict_passes(body) else dict(record["findings"])  # defect: a pass discards findings\n',
          'finding-not-erased')
    floor('floor-handoff-ignores-findings',
          '    codes.extend("unresolved_finding:" + fid for fid in unresolved)\n',
          '    codes.extend([])  # defect: an open finding does not block the handoff\n', 'finding-not-erased')
    floor('floor-findings-forgotten-on-rebuild',
          '    unresolved = sorted(fid for fid, f in record["findings"].items() if not f.get("resolved"))\n',
          '    unresolved = sorted(fid for fid, f in record["findings"].items() if not f.get("resolved")\n'
          '                        and f.get("attempt") == attempt)  # defect: a rebuild forgets earlier findings\n',
          'finding-not-erased')
    floor('floor-any-member-disposes',
          '    if builder or member is None or (member.get("principal_type") != "person" and by != finding["raised_by"]):\n',
          '    if member is None:  # defect: any member, the builder included, disposes a finding\n',
          'finding-not-erased')
    floor('floor-rejected-ruling-resolves', '    if body["ruling"] == "resolved":\n',
          '    if body["ruling"] in RULINGS:  # defect: a rejected ruling resolves the finding\n', 'finding-not-erased')
    floor('floor-land-without-handoff', '            if state != "handoff":\n',
          '            if False:  # defect: an enrolled unit lands without its handoff\n', 'finding-not-erased')
    floor('floor-dispatcher-establishes-completion',
          '        return {"ok": True, "kind": "review", "spec": sid, "verdict": verdict, "shipped": False,\n'
          '                "landed": True, "status": "handoff", "land": land, "projection": projection}\n',
          '        receipt = "receipt:revision_landed:" + sid  # defect: the dispatcher records the landing itself\n'
          '        floor.store.execute(floor.conn, dict(\n'
          '            command_id="landed/" + sid, principal=floor.principal, operation="upsert_entity",\n'
          '            nonce="landed/" + sid, artifact_digests=[], expected_versions={receipt: 0},\n'
          '            parameters=dict(entity_id=receipt, kind="completion_receipt",\n'
          '                            data={"fact": "revision_landed", "subject": {"id": sid, "revision": 1}})),\n'
          '            floor.signer, floor.sign, floor.generation)\n'
          '        return {"ok": True, "kind": "review", "spec": sid, "verdict": verdict, "shipped": False,\n'
          '                "landed": True, "status": "handoff", "land": land, "projection": projection}\n',
          'completion-by-lander-only')
    floor('floor-handoff-completes', '    record["state"] = "handoff"\n',
          '    record["state"] = "completed"  # defect: the handoff establishes completion\n',
          'completion-by-lander-only')
    # Tracker intake stays disabled for enrolled work.
    floor('floor-tracker-enrollment-unread', '        return self._EL.enrolled(str(root))\n',
          '        return False  # defect: the repository\'s enrollment is not asked\n',
          'tracker-disabled-when-enrolled', module='tracker_bridge.py')
    floor('floor-tracker-write-unguarded',
          '            raise SpecStoreError("write_spec needs the rendered draft markdown")\n'
          '        self._refuse_enrolled(repo)\n',
          '            raise SpecStoreError("write_spec needs the rendered draft markdown")\n'
          '        # defect: a direct write reaches an enrolled repository\n',
          'tracker-disabled-when-enrolled', module='tracker_bridge.py')
    floor('floor-refusal-not-observed',
          '            self.observe(dict(event, outcome="refused", refusal=error.code, refusals=codes,\n'
          '                              taxonomy=floor_taxonomy(error.code)))\n',
          '            pass  # defect: a refusal is not observed\n', 'observations')
    floor('floor-finding-taxonomy-unknown', '    "unresolved_finding": "missing_evidence",\n', '',
          'observations')
    # VELDO-0050: each criterion's declared falsifier and further defects, each against the one suite 64
    # row it names. Anchors are exact text in the production modules suite 64 installs.
    def proof(name, old, new, row, also=(), module='control_proof.py'):
        add(50, name, '64_veldo_0050_proof.py', module, old, new, ['proof/' + row], also)

    accept_block = ('        if self.proofs is not None:\n'
                    '            try:\n'
                    '                accepted = self.proofs.accept(sid, commit=commit, base=spec.get("base"), spec_path=spec.get("spec_path"),\n'
                    '                                              manifest=proof, observation=observation, builder=builder)\n'
                    '            except CP.Refused as error:\n'
                    '                return {"ok": False, "problems": list(error.codes), "bundle": None}\n'
                    '            return dict(accepted, ok=True, problems=[])\n')
    # AC1, declared: the manifest is kept only in temporary validation storage, so no fresh reviewer resolves it.
    proof('proof-kept-in-temporary-storage', accept_block,
          '        if self.proofs is not None:\n'
          '            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=True) as held:\n'
          '                held.write(json.dumps(proof))  # defect: the manifest is kept only in temporary validation storage\n'
          '                held.flush()\n'
          '            return {"ok": True, "problems": [], "bundle": None}\n',
          'fresh-reviewer-resolves', module='executor.py')
    proof('proof-implementation-is-the-built-commit',
          '              "implementation": {"commit": implementation}, "spec": spec,\n',
          '              "implementation": {"commit": commit}, "spec": spec,  # defect: the built commit named as the implementation\n',
          'fresh-reviewer-resolves')
    proof('proof-offered-without-acceptance',
          '            accepted = (self.hooks.accept_proof(spec, build, g, proof, context=self.context)\n'
          '                        if gate is not None else None)\n',
          '            accepted = None  # defect: the build is offered with its proof never accepted\n',
          'accepted-before-offer', module='executor.py')
    proof('proof-unstored-accepted',
          '        return {"ok": False, "problems": ["missing_authority:proof_service"], "bundle": None}\n',
          '        return {"ok": True, "problems": [], "bundle": None}  # defect: a proof nothing stored is accepted\n',
          'accepted-before-offer', module='executor.py')
    proof('proof-bundle-rewritable',
          '    if before.get(rid) is not None:\n        raise Refused("proof_immutable", rid)\n',
          '    pass  # defect: an accepted bundle may be rewritten\n', 'accepted-before-offer')
    proof('proof-kinds-unowned',
          '        store.declare_owners(conn, OWNER, kinds={BUNDLE_KIND: (ACCEPT,), OBSERVATION_KIND: (OBSERVE,)}, module=__file__)\n',
          '        pass  # defect: nothing declares who alone writes accepted proof\n', 'accepted-before-offer')
    # AC2, declared: check_json alone decides an empty-criteria proof naming a nonexistent commit.
    proof('proof-check-json-alone', accept_block,
          '        if self.proofs is not None:\n'
          '            ok, errors = self.validate_proof(proof)  # defect: check_json alone decides the proof\n'
          '            return {"ok": ok, "problems": [] if ok else ["validate_proof:%s" % errors], "bundle": None}\n',
          'contextual-refusals', module='executor.py')
    proof('proof-duplicates-uncounted',
          '    problems.extend("invalid_input:criteria/duplicate:%s" % cid for cid in sorted({i for i in ids if ids.count(i) > 1}, key=str))\n',
          '    pass  # defect: a criterion mapped twice is not noticed\n', 'contextual-refusals')
    proof('proof-spec-revision-unread', '    if manifest.get("spec_revision") != spec["revision"]:\n',
          '    if False:  # defect: the proof\'s spec revision is not compared with the accepted one\n',
          'contextual-refusals')
    proof('proof-criteria-from-manifest',
          '    problems.extend("missing_evidence:criteria/omitted:%s" % cid for cid in spec["criteria"] if cid not in ids)\n',
          '    problems.extend("missing_evidence:criteria/omitted:%s" % cid for cid in ids if cid not in ids)  # defect: the manifest names its own universe\n',
          'contextual-refusals')
    # AC3, declared: a default passed unit check is inserted when observations are absent.
    proof('proof-default-passed-check', '            "checks": list((build or {}).get("checks") or []),\n',
          '            "checks": list((build or {}).get("checks") or [{"name": "unit", "status": "passed"}]),  # defect: a default passed check\n',
          'no-default-success', module='executor.py')
    proof('proof-terminal-not-required',
          '        if terminal != "GATE: GREEN (%s)" % commit:\n            problems.append("missing_evidence:observation/terminal")\n',
          '        pass  # defect: a gate that printed no terminal result is not refused for it\n', 'no-default-success')
    proof('proof-absent-check-passes', '            if results.get(name) is None:\n',
          '            if False:  # defect: a check the gate never printed is not missing\n', 'no-default-success')
    proof('proof-observation-digest-unbound', '    elif stored["digest"] != reference.get("digest"):\n',
          '    elif False:  # defect: an altered observation reference is believed\n', 'no-default-success')
    proof('proof-checks-from-claims', '              "checks": checks, "producer": producer,',
          '              "checks": [dict(c) for c in claims if isinstance(c, dict)], "producer": producer,  # defect: the claims recorded as checks\n             ',
          'actual-checks')
    proof('proof-gate-exit-unrecorded',
          '                               "observed": "   %s: pass" % name, "gate_exit": observation.get("exit"),\n',
          '                               "observed": "   %s: pass" % name, "gate_exit": None,  # defect: the gate exit is not recorded\n',
          'actual-checks')
    # AC4, declared: the executor emits verdict.recorded itself.
    proof('proof-executor-emits-verdict', '            if gate is None:\n                # The pre-factory loop',
          '            if True:  # defect: the executor emits verdict.recorded itself\n                # The pre-factory loop',
          'owning-services', module='executor.py')
    proof('proof-executor-emits-gate-event',
          '                   **({"observation": seen["id"]} if seen.get("id") else {}))\n',
          '                   **({"observation": seen["id"]} if seen.get("id") else {}))\n'
          '            if gate_green:\n'
          '                self.hooks.emit("gate.passed", spec=spec.get("id"), commit=build.get("commit"))  # defect: the gate\'s own event\n',
          'owning-services', module='executor.py')
    proof('proof-build-only-lands',
          '                # Exactly one build/gate/proof cycle ran; verdict stays None.\n',
          '                # Exactly one build/gate/proof cycle ran; verdict stays None.\n'
          '                self.hooks.emit("merge.completed", spec=spec.get("id"), commit=build.get("commit"))  # defect: a landing\n',
          'build-only-no-landing', module='executor.py')
    proof('proof-build-only-reviews', '            if stop_after == "proof":\n',
          '            if stop_after == "proof" and False:  # defect: a build-only run goes on into review\n',
          'build-only-no-landing', module='executor.py')
    proof('proof-module-not-installed', '    ".veldo/control_proof.py",\n', '', 'installed-assets', module='init_scaffold.py')
    proof('proof-closure-not-installed', '    ".veldo/control_membership.py",\n', '', 'installed-assets',
          module='init_scaffold.py')
    proof('proof-refusal-not-observed',
          '            self.observe(dict(event, outcome="refused", refusal=error.code, refusals=codes,\n'
          '                              taxonomy=taxonomy(error.code)))\n',
          '            pass  # defect: a refusal is not observed\n', 'observations')
    proof('proof-unknown-taxonomy-classified', '    return TAXONOMY.get(str(code).split(":", 1)[0], "unknown_outcome")\n',
          '    return TAXONOMY.get(str(code).split(":", 1)[0], "missing_evidence")  # defect: an unknown code is classified\n',
          'observations')
    # VELDO-0132: each criterion's declared falsifier and further defects, each against the one suite 65
    # row it names. Anchors are exact text in the three production modules suite 65 installs.
    def workflow(name, old, new, row, module='control_workflow.py', also=()):
        add(132, name, '65_veldo_0132_workflow.py', module, old, new, ['workflow/' + row], also)

    cycle = 'control_workflow_cycle.py'
    # AC1, declared: an edge to a nonexistent node is accepted.
    workflow('workflow-dangling-edge-accepted', '        if source not in nodes or target not in nodes:\n',
             '        if source not in nodes:  # defect: an edge to a nonexistent node is accepted\n', 'validation')
    workflow('workflow-unbounded-cycle-accepted',
             "        if 'max' not in edge:\n            graph.setdefault(edge['from'], []).append(edge['to'])\n",
             "        if False:  # defect: a ring of unbounded transitions is not looked for\n"
             "            graph.setdefault(edge['from'], []).append(edge['to'])\n", 'validation')
    workflow('workflow-references-unresolved', '            if not resolve(kind, ref):\n',
             '            if False:  # defect: a configuration reference is never looked up in the store\n', 'validation')
    workflow('workflow-editor-unchecked',
             "    problem = editor_problem(conn, params.get('principal'), repository, params.get('now'))\n",
             '    problem = None  # defect: the editor is not judged\n', 'authorized-editor')
    workflow('workflow-editor-role-ignored', "            or not set(entry.get('roles') or []) & set(EDITOR_ROLES)\n", '',
             'authorized-editor')
    workflow('workflow-revision-kinds-unowned',
             '        store.declare_owners(conn, OWNER, kinds={REVISION_KIND: (SAVE,), HEAD_KIND: (SAVE,)}, module=__file__)\n',
             '        pass  # defect: nothing declares who alone writes workflow revisions\n', 'revisions-immutable')
    workflow('workflow-stale-base-accepted', "    if params.get('base') != current:\n",
             '    if False:  # defect: an edit that did not see the head is accepted\n', 'revisions-immutable')
    workflow('workflow-load-returns-head',
             '            if version is None:\n                version = head_version(self.conn, self.domain, self.repository, workflow)\n',
             '            if True:  # defect: an earlier revision cannot be read back\n'
             '                version = head_version(self.conn, self.domain, self.repository, workflow)\n',
             'revisions-immutable')
    workflow('workflow-layout-reaches-runner', "    text = WF.canonical(revision['definition']).decode()\n",
             "    text = WF.canonical(dict(revision['definition'], layout=revision['layout'])).decode()  # defect: the layout reaches execution\n",
             'canvas-round-trip', module=cycle)
    workflow('workflow-layout-dropped', "    definition, layout = params.get('definition'), params.get('layout')\n",
             "    definition, layout = params.get('definition'), {}  # defect: the canvas layout is not kept\n",
             'canvas-round-trip')
    # AC3, declared: a worker is launched while an edge is saved.
    workflow('workflow-save-launches-worker',
             "        row = _entity_row(self.conn, rid)\n        answer = {'workflow': workflow,",
             "        __import__('subprocess').run([__import__('sys').executable, '-c', 'pass'], check=False)  # defect: a worker is launched while the edge is saved\n"
             "        row = _entity_row(self.conn, rid)\n        answer = {'workflow': workflow,",
             'edit-without-execution')
    workflow('workflow-load-activates-runtime',
             '            row, data = verified_revision(self.store, self.conn, self.domain, self.repository, workflow, version)\n'
             '        except (Refused, sqlite3.Error) as error:\n',
             '            row, data = verified_revision(self.store, self.conn, self.domain, self.repository, workflow, version)\n'
             "            _organ('control_runtime').activation()  # defect: loading asks the graph runtime\n"
             '        except (Refused, sqlite3.Error) as error:\n',
             'edit-without-execution')
    # AC2, declared: an active cycle reads the canvas's current revision instead of its binding.
    workflow('workflow-cycle-reads-canvas-head',
             "                                         binding['version'])\n"
             "        if (row['id'], row['digest'], data['definition_digest']) != (binding['revision'], binding['entity_digest'],\n"
             "                                                                     binding['digest']):\n",
             "                                         WF.head_version(self.conn, self.domain, self.repository, binding['id']))  # defect: the canvas's current revision\n"
             "        if False:\n",
             'pinned-revision', module=cycle)
    workflow('workflow-cycle-binds-first-revision',
             '        version = WF.head_version(conn, domain, repository, workflow) if WF._identifier(workflow) else 0\n',
             '        version = 1 if WF._identifier(workflow) and WF.head_version(conn, domain, repository, workflow) else 0  # defect: a new cycle binds the first revision\n',
             'pinned-revision', module=cycle)
    workflow('workflow-runner-unregistered',
             "    block = '\\n' + (HERE / STEPS).read_text() + '\\nveldo_register_workflow(%r, %d)\\n' % (text, revision['version'])\n",
             "    block = '\\n' + (HERE / STEPS).read_text() + '\\n'  # defect: the runner registers no revision\n",
             'actual-langgraph', module=cycle)
    workflow('workflow-cancel-without-graph', "            if record['resume'] is not None:\n",
             '            if False:  # defect: a cycle is canceled without asking the graph\n', 'actual-langgraph', module=cycle)
    workflow('workflow-role-unchecked', '        problem = self.role_problem(definition, node)\n',
             '        problem = None  # defect: the assignment\'s role is not judged\n', 'ordinary-authorization', module=cycle)
    workflow('workflow-gate-not-asked', "        decision = self.gate.decide(STATION, record['subject'])\n",
             "        decision = {'eligible': True, 'refusals': [], 'decision_id': None, 'watermark': None}  # defect: the Gate is not asked\n",
             'ordinary-authorization', module=cycle)
    workflow('workflow-budget-unchecked', "            if record['steps'] >= definition['budget']['steps']:\n",
             '            if False:  # defect: the cycle budget is not enforced\n', 'ordinary-authorization', module=cycle)
    workflow('workflow-loop-bound-unchecked', "            if 'max' in taken and visits[taken['id']] > taken['max']:\n",
             '            if False:  # defect: a loop bound is not enforced\n', 'ordinary-authorization', module=cycle)
    workflow('workflow-completion-unvalidated',
             '        if not received or received not in evidence or not evidence <= offered:\n',
             '        if False:  # defect: an asserted completion is not checked against an accepted result\n',
             'ordinary-authorization', module=cycle)
    # AC4, declared: a terminal graph node sets the specification shipped directly.
    shipped_anchor = ("            return self._refuse(record, 'missing_evidence:completion', node=position, graph=command)\n"
                      "        record = dict(record, state='proposed', steps=record['steps'] + 1,\n")
    workflow('workflow-terminal-ships-spec', shipped_anchor,
             "            return self._refuse(record, 'missing_evidence:completion', node=position, graph=command)\n"
             "        for spec in Path(self.gate.workspace).glob('specs/%s-*.md' % record['subject']):  # defect: the terminal node ships the spec\n"
             "            spec.write_text(spec.read_text().replace('status: ready', 'status: shipped'))\n"
             "        record = dict(record, state='proposed', steps=record['steps'] + 1,\n",
             'no-workflow-authority', module=cycle)
    workflow('workflow-terminal-writes-unit', shipped_anchor,
             "            return self._refuse(record, 'missing_evidence:completion', node=position, graph=command)\n"
             "        unit = _entity_row(self.conn, record['subject'])  # defect: the terminal node writes the unit itself\n"
             "        self.store.execute(self.conn, {'command_id': 'shipped/' + record['cycle'], 'principal': self.principal,\n"
             "                                       'operation': 'upsert_entity', 'artifact_digests': [], 'nonce': 'shipped/' + record['cycle'],\n"
             "                                       'parameters': {'entity_id': record['subject'], 'kind': 'execution_unit',\n"
             "                                                      'data': dict(unit['data'], state='SHIPPED')},\n"
             "                                       'expected_versions': {record['subject']: unit['version']}},\n"
             "                           self.signer, self.sign, self.generation)\n"
             "        record = dict(record, state='proposed', steps=record['steps'] + 1,\n",
             'no-workflow-authority', module=cycle)
    workflow('workflow-cycle-refusal-unobserved', '        self.observations.append(event)\n        self.observe(event)\n',
             "        self.observations.append(event)\n        if outcome != 'refused':  # defect: a refusal is not observed\n"
             '            self.observe(event)\n', 'observations', module=cycle)
    workflow('workflow-save-refusal-unclassified',
             "        self.observe(dict(event, outcome='refused', refusal=error.code, refusals=codes, taxonomy=taxonomy(error.code)))\n",
             "        self.observe(dict(event, outcome='refused', refusal=error.code, refusals=codes, taxonomy=None))  # defect: unclassified\n",
             'observations')
    workflow('workflow-pending-unlisted', "(self.domain, self.repository) and data['state'] == 'waiting':\n",
             "(self.domain, self.repository) and data['state'] == 'running':  # defect: waiting work is not listed\n",
             'observations', module=cycle)
    return result


def edits(case):
    return [(case['old'], case['new'])] + [tuple(pair) for pair in case.get('also', ())]


def mutate(text, case):
    """Apply every replacement of `case` to `text` (str or bytes); each anchor must occur exactly
    once in the text it is applied to."""
    for old, new in edits(case):
        if isinstance(text, bytes):
            old, new = old.encode(), new.encode()
        if text.count(old) != 1:
            raise RuntimeError((case['name'], 'mutation anchor moved', text.count(old)))
        text = text.replace(old, new)
    return text


def materialize(case, mode, directory, root=ROOT):
    """Own case paths, exact replacement and file/directory copies for every driver.

    Digests describe the actual module bytes, even when the suite receives a directory.
    Baselines use the original input; no-op and mutant copies never edit that input.
    """
    if mode not in ('baseline', 'noop', 'mutant'):
        raise ValueError('unknown mutation mode: ' + mode)
    fixture = case.get('fixture') is True
    base = root / 'scripts/fixtures' if fixture else root / '.veldo'
    source = base / case['module']
    before = source.read_bytes()
    old = case['old'].encode()
    count = before.count(old)
    if count != 1:
        raise RuntimeError((case['name'], 'mutation anchor moved', count))
    mutated = mutate(before, case)
    mutant = None
    after = before
    if mode != 'baseline':
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        mutant = destination / ('fixtures' if fixture else case['module'])
        if fixture:
            shutil.copytree(base, mutant, ignore=shutil.ignore_patterns('__pycache__'))
        elif case.get('siblings') is True:
            # A module that loads its siblings by its own path (control_membership loads
            # authority_contract and control_store next to itself) gets a whole .veldo copy.
            shutil.copytree(base, destination / 'veldo', ignore=shutil.ignore_patterns('__pycache__'))
            mutant = destination / 'veldo' / case['module']
        target = mutant / case['module'] if fixture else mutant
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(before if mode == 'noop' else mutated)
        after = target.read_bytes()
    return dict(source=source, mutant=mutant, replacement_count=count,
                old_digest=hashlib.sha256(before).hexdigest(),
                new_digest=hashlib.sha256(after).hexdigest())


def worker(case, mutant=None):
    """Capture every assertion, including the shared preamble, with exact row identities."""
    shared = ROOT / 'scripts/suites/shared.py'
    rows = []
    ns = {'__file__': str(shared),
          '__observe__': lambda name, condition: rows.append([name.split(':', 1)[0], bool(condition)])}
    tree = ast.parse(shared.read_text(), str(shared))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'expect':
            node.body = ast.parse('__observe__(name, condition)').body
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
        suite = ROOT / 'scripts/suites' / case['suite']
        source = suite.read_text()
        if case.get('fixture'):
            if mutant:
                source = source.replace('ROOT / "scripts" / "fixtures"',
                                        '__import__("pathlib").Path(' + repr(mutant) + ')')
        elif mutant:
            anchor = 'ROOT / ".veldo" / "' + case['module'] + '"'
            if not source.count(anchor):
                raise RuntimeError('suite production-copy anchor moved')
            source = source.replace(anchor, '__import__("pathlib").Path(' + repr(mutant) + ')')
        ns['__suite_file__'] = str(suite)
        exec(compile(source, str(suite), 'exec'), ns)
    return {'count': len(rows), 'observations': rows,
            'row_names': [name for name, _ in rows],
            'failed_rows': [name for name, ok in rows if not ok],
            'targets': {label: [ok for name, ok in rows if name.split()[-1] == label]
                        for label in case['rows']}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--finding', type=int, choices=sorted({case['finding'] for case in cases()}))
    parser.add_argument('--diff-dir', type=Path, help='retain exact applied mutation diffs')
    parser.add_argument('--worker')
    parser.add_argument('--mutant')
    parser.add_argument('--jobs', type=int, default=min(8, os.cpu_count() or 1),
                        help='mutant runs in parallel (the honest run is once per suite)')
    args = parser.parse_args()
    selected = [c for c in cases() if args.finding is None or c['finding'] == args.finding]
    if args.worker:
        case = next(c for c in selected if c['name'] == args.worker)
        print(json.dumps(worker(case, args.mutant)))
        return
    def run(case, path=None):
        command = [sys.executable, __file__, '--worker', case['name']]
        if path:
            command += ['--mutant', str(path)]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=120)
        if proc.returncode:
            raise RuntimeError(f"{case['name']} did not complete its assertions: {proc.stderr}")
        return json.loads(proc.stdout)

    def targets(observed, case):
        return {label: [ok for name, ok in observed['observations'] if name.split()[-1] == label]
                for label in case['rows']}

    baselines = {}
    with tempfile.TemporaryDirectory(prefix='teeth-mutants-') as directory:
        prepared = {}
        for case in selected:
            prepared[case['name']] = materialize(case, 'mutant', Path(directory) / case['name'])
            if args.diff_dir:
                source = prepared[case['name']]['source'].read_text()
                changed = mutate(source, case)
                relative = str(prepared[case['name']]['source'].relative_to(ROOT))
                args.diff_dir.mkdir(parents=True, exist_ok=True)
                (args.diff_dir / (case['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
                    source.splitlines(keepends=True), changed.splitlines(keepends=True), n=0,
                    fromfile='a/' + relative, tofile='b/' + relative)))
        # The honest run of a suite does not depend on the mutant, so each suite runs honestly ONCE
        # and every case of it is judged against that run; the mutant runs are independent and run
        # in parallel. Each case's own targets are taken from the shared observations.
        first = {}
        for case in selected:
            first.setdefault(case['suite'], case)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            honest_runs = {suite: pool.submit(run, case) for suite, case in first.items()}
            broken_runs = {case['name']: pool.submit(run, case, prepared[case['name']]['mutant'])
                           for case in selected}
            for case in selected:
                honest = honest_runs[case['suite']].result()
                broken = broken_runs[case['name']].result()
                assert not honest['failed_rows'], honest
                assert set(honest['row_names']) <= set(broken['row_names']), (honest, broken)
                for label in case['rows']:
                    assert targets(honest, case)[label] == [True], (case['name'], label, honest['failed_rows'])
                    assert targets(broken, case)[label] == [False], (case['name'], label, broken['failed_rows'])
                baselines[case['suite']] = honest['count']
                print(json.dumps({'finding': case['finding'], 'mutation': case['name'],
                                  'baseline': 'green', 'assertions': honest['count'],
                                  'red_rows': broken['failed_rows']}), flush=True)
    print(json.dumps({'mutations_rejected': len(selected), 'green_suites': baselines}))


if __name__ == '__main__':
    main()
