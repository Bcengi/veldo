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
    add(31, 'review-r3-contention-as-answer', '59_veldo_0031_review.py', 'control_claim.py',
        "                if exc.code == 'stale_version' and self._pins_moved(observation['accepted_versions']):",
        '                if False:  # defect: a moved pin on its own read is returned as the answer',
        ['claims/review-r3'])
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
    # Re-anchored 2026-09-24: VELDO-0135 rewrote the frontier; the selection check now holds the unit by name.
    floor('eligibility-frontier-bypass', 'frontier.py',
          '            if not decision["eligible"]:\n                return _hold(sid, decision["refusals"][0], decision["refusals"])\n',
          '            if False:\n                return _hold(sid, decision["refusals"][0], decision["refusals"])\n', 'entry-frontier')
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
    # Re-anchored 2026-09-24: VELDO-0135 split the frontier's completion read across its two readers; both read
    # status text in the defect.
    add(52, 'completion-frontier-reads-status-text', '60_veldo_0052_eligibility.py', 'frontier.py',
        '    # VELDO-0052 AC3: with the floor enabled, "shipped" means a landed revision, never status text.\n'
        '    status = EL.completion_status(gate, _status_map(idx))\n',
        '    # VELDO-0052 AC3: with the floor enabled, "shipped" means a landed revision, never status text.\n'
        '    status = _status_map(idx)\n', ['completion/readers-agree'],
        [('    idx = _spec_index(repo_root)\n    status = EL.completion_status(gate, _status_map(idx))\n',
          '    idx = _spec_index(repo_root)\n    status = _status_map(idx)\n')])
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
    # VELDO-0134 moved the record check to the schema: the defect now reads any state as accepted there.
    architecture('architecture-unaccepted-record-accepted', 'control_eligibility.py',
                 "        if accepted and AR.record_problems(item['id'], (item.get('value') or {}).get('kind'), record):\n",
                 "        if accepted and AR.record_problems(item['id'], (item.get('value') or {}).get('kind'),\n"
                 "                                           dict(record, state='accepted') if isinstance(record, dict) else record):\n",
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
    # VELDO-0068: each criterion's declared falsifier, and a second, different defect for every named row.
    def settlement(name, old, new, row, module='control_request_settlement.py', also=()):
        add(68, name, '69_veldo_0068_settlement.py', module, old, new, [row], also)

    # Installation: the settlement service is laid down by the scaffold and is not validator substrate.
    settlement('settlement-not-scaffolded', '    ".veldo/control_request_settlement.py",\n', '', 'install/assets',
               module='init_scaffold.py')
    settlement('settlement-claimed-as-substrate', 'REQUIRED_SUBSTRATE = [\n',
               'REQUIRED_SUBSTRATE = [\n    ".veldo/control_request_settlement.py",  # defect: claimed as substrate\n',
               'install/assets', module='init_scaffold.py')
    # AC1 (declared falsifier): every chosen option recorded as a generic decided value; then an effect
    # type that ignores the ruling.
    settlement('chosen-option-generic',
               "                      'choice': choice, 'ruling': ruling, 'rationale': winner['rationale'], 'principals': principals,\n",
               "                      'choice': 'decided', 'ruling': 'decided', 'rationale': winner['rationale'], 'principals': principals,\n",
               'ruling/offered-choice-and-reasoning',
               also=[("'proposal': terms['proposal'] if ruling == 'approve' else None, 'choice': choice, 'ruling': ruling,\n",
                      "'proposal': terms['proposal'] if ruling == 'approve' else None, 'choice': 'decided', 'ruling': 'decided',\n")])
    settlement('effect-type-ignores-ruling', "'type': JOURNEY[touchpoint]['effects'][ruling],",
               "'type': JOURNEY[touchpoint]['effects']['approve'],", 'ruling/offered-choice-and-reasoning')
    # AC2: the earliest binding answer wins, and every answer not counted is named on the settlement.
    settlement('latest-answer-wins', "        winner_id, _, channel, winner = valid[0]\n",
               "        winner_id, _, channel, winner = valid[-1]  # defect: the latest answer wins\n", 'settlement/one-winner')
    settlement('conflicting-answer-unrecorded', "        for eid, _ver, other_channel, answer in valid[1:]:\n",
               "        for eid, _ver, other_channel, answer in []:  # defect: answers not counted are not named\n",
               'settlement/one-winner')
    # AC2 (declared falsifier): the receipt inserted by a second command after the terminal transaction;
    # then a nonce per answer instead of the request version's.
    settlement('receipt-separate-transaction',
               "                rid: {'kind': RECEIPT_KIND, 'data': params['receipt']},\n", '', 'settlement/one-transaction',
               also=[("RECEIPT_KIND: (SETTLE,), TERMS_KIND: (TERMS,)", "RECEIPT_KIND: (SETTLE, TERMS), TERMS_KIND: (TERMS,)"),
                     ("kind not in (TERMS_KIND, API_KIND)", "kind not in (TERMS_KIND, API_KIND, RECEIPT_KIND)"),
                     ("        self._commit(SETTLE, sid, params, expected)\n",
                      "        self._commit(SETTLE, sid, params, expected)\n"
                      "        self._commit(TERMS, rec, dict(entity_id=rec, kind=RECEIPT_KIND, data=receipt_data), {rec: 0})  # defect\n")])
    settlement('settlement-nonce-per-answer', "        self._commit(SETTLE, sid, params, expected)\n",
               "        self._commit(SETTLE, sid + ':' + winner_id, params, expected)  # defect: one nonce per answer\n",
               'settlement/one-transaction')
    # AC2: the VELDO-0064 answer command moves a request with settlement terms to SUBMITTED with no
    # settlement, effect or receipt, so a later answer finds it closed.
    settlement('inbox-answer-bypasses-settlement',
               "                if (data.get('subject') or {}).get('kind') == SETTLEMENT_SUBJECT_KIND:\n",
               "                if False:  # defect: the inbox answers a request with settlement terms\n",
               'settlement/one-transaction', module='control_assignment.py')
    # Review decision: the VELDO-0064 decline command closes a request with terms as DECLINED with no
    # settlement; a rejection is a ruling the settlement service records with the owner's reasoning.
    settlement('inbox-decline-bypasses-settlement',
               "                if (data.get('subject') or {}).get('kind') == SETTLEMENT_SUBJECT_KIND:\n",
               "                if op == 'answer' and (data.get('subject') or {}).get('kind') == SETTLEMENT_SUBJECT_KIND:  # defect: decline bypasses settlement\n",
               'settlement/one-transaction', module='control_assignment.py')
    # AC3 (declared falsifier): the request left open after settlement; then an API answer accepted on a
    # settled request.
    settlement('request-left-open',
               "                rid: {'kind': RECEIPT_KIND, 'data': params['receipt']},\n"
               "                request: {'kind': self.I.ENTITY_KIND, 'data': terminal}}\n",
               "                rid: {'kind': RECEIPT_KIND, 'data': params['receipt']}}  # defect: the request stays open\n",
               'terminal/materialized-settlement')
    settlement('closed-request-answered-by-api',
               "            if item['data']['state'] not in self.I.PENDING:\n"
               "                raise Refused('request_closed', 'the request is no longer pending')\n", '',
               'terminal/materialized-settlement')
    # AC4 (declared falsifier): request.required_roles ignored when the policy roles pass; then the policy
    # roles ignored, and the requester counted as independent of itself.
    settlement('request-roles-ignored',
               "    roles = sorted(set(policy['roles']) | set(terms.get('required_roles') or []))\n",
               "    roles = sorted(set(policy['roles']))  # defect: the request's own roles are ignored\n",
               'authority/roles-and-independence')
    settlement('policy-roles-ignored',
               "    roles = sorted(set(policy['roles']) | set(terms.get('required_roles') or []))\n",
               "    roles = sorted(set(terms.get('required_roles') or []))  # defect: the journey's roles are ignored\n",
               'authority/roles-and-independence')
    settlement('requester-separation-ignored', "        if need['min_independence'] >= 1:\n",
               "        if False:  # defect: the requester may answer its own request\n", 'authority/roles-and-independence')
    # AC4: the owner and the API edge's signature are checked before an answer is accepted.
    settlement('api-answer-owner-unchecked',
               "            if a['principal'] != receipt['owner']:\n"
               "                raise Refused('not_owner', 'the principal is not the owner the presentation was shown to')\n", '',
               'authority/owner-and-presentation')
    settlement('api-edge-signature-unchecked',
               "        if not verified:\n            raise Refused('not_authorized', 'the signature does not verify')\n",
               "        if False:  # defect: the signature is not checked\n"
               "            raise Refused('not_authorized', 'the signature does not verify')\n",
               'authority/owner-and-presentation')
    # AC4: an unsupported quorum blocks: the request's count is never weakened to the policy's, and an
    # independence above one is never taken as supported.
    settlement('request-quorum-weakened',
               "    count = max(policy['quorum'].get('count') or 1, wanted.get('count') or 1)\n",
               "    count = policy['quorum'].get('count') or 1  # defect: the request's count is weakened\n",
               'authority/unsupported-quorum-blocks')
    settlement('independence-above-one-accepted', "SUPPORTED = {'count': (1,), 'min_independence': (0, 1)}\n",
               "SUPPORTED = {'count': (1,), 'min_independence': (0, 1, 2)}  # defect\n",
               'authority/unsupported-quorum-blocks')
    # VELDO-0069: each criterion's declared falsifier, and the threat model's cases, each on the row it names.
    def binding(name, old, new, row, module='control_request_settlement.py', also=()):
        add(69, name, '70_veldo_0069_bindings.py', module, old, new, [row], also)

    # AC1 (declared falsifier): only the receipt commits, without its governing binding; then a settlement
    # without a decision signer that commits its receipt anyway, and a binding that drops the chosen option.
    binding('receipt-without-binding',
            "            changes[binding['binding_id']] = {'kind': DECISION_SETTLEMENT_KIND, 'data': binding}\n",
            "            pass  # defect: only the receipt commits, without its governing binding\n",
            'eligibility/resolved-request')
    binding('binding-skipped-without-signer',
            "                 if terms['target'].get('kind') == GOVERNING_TARGET else None)\n",
            "                 if terms['target'].get('kind') == GOVERNING_TARGET and self.decision_signer is not None\n"
            "                 else None)  # defect: no signer, no binding, and the receipt commits\n",
            'binding/one-transaction')
    # The signed body's ruling is what every VELDO-0054 consumer reads: forced to approve, the owner's reject
    # would clear the work. The unsigned chosen option, fixed to accept whatever the owner chose.
    binding('ruling-forced-approve', "'scope_digest': question['scope_digest'], 'ruling': winner['ruling'],",
            "'scope_digest': question['scope_digest'], 'ruling': 'approve',", 'binding/owner-ruling')
    binding('binding-choice-forced-accept', "'signature': signature, 'choice': winner['choice'],",
            "'signature': signature, 'choice': 'accept',", 'binding/owner-ruling')
    # AC2 (declared falsifier): the subject digest the owner was shown is ignored during binding; then the
    # framing and the revision taken from the record at settlement instead of from the question.
    binding('binding-ignores-subject-digest', "'subject': dict(question['subject']),",
            "'subject': dict(question['subject'], digest=record['subject']['digest']),", 'refusal/wrong-subject')
    binding('binding-framing-from-record', "'framing_digest': question['framing_digest'],",
            "'framing_digest': record['framing_digest'],", 'refusal/wrong-framing')
    binding('binding-revision-from-record', "'decision_revision': question['revision'],",
            "'decision_revision': record['revision'],", 'refusal/wrong-version')
    # Threat model: an unsupported subject kind bound instead of stopped, at settlement and at the terms.
    binding('unsupported-subject-bound',
            "        if kind not in DD.SUBJECT_KINDS:\n            raise Refused('unsupported_subject', 'the governed",
            "        if False:  # defect: an unsupported governed subject is bound\n"
            "            raise Refused('unsupported_subject', 'the governed", 'refusal/unsupported-subject-stops')
    binding('unsupported-subject-terms-accepted',
            "    if subject['kind'] not in DD.SUBJECT_KINDS:\n        return 'unsupported_subject'",
            "    if False:  # defect: a question about an unsupported subject is recorded\n        return 'unsupported_subject'",
            'refusal/unsupported-subject-stops')
    # Threat model: a question at a revision above the record's is bound, so it clears the work once the
    # record reaches that revision and refuses the genuine question as already settled.
    binding('future-revision-accepted', "        if question['revision'] > record['revision']:\n",
            "        if False:  # defect: a question above the record's revision is bound\n", 'refusal/future-revision')
    # AC3 (declared falsifier): inline open_decisions text treated as authority by the plan readers; then
    # by the store-backed stations, and a record's own settled status treated as its settlement.
    binding('inline-status-authority', '                blocked.setdefault(s, []).append(d.get("id"))\n',
            '                if d.get("status") != "resolved":  # defect: inline status text resolves the decision\n'
            '                    blocked.setdefault(s, []).append(d.get("id"))\n',
            'consumers/inline-bypass', module='plan.py')
    binding('inline-status-authority-at-stations', "            out.append(entry.get('id'))\n",
            "            if entry.get('status') != 'resolved':  # defect: inline status text resolves the decision\n"
            "                out.append(entry.get('id'))\n",
            'consumers/inline-bypass', module='control_decision_dependency.py')
    binding('record-status-authority', "    if not mine:\n        return ['unresolved_decision:' + rid]\n",
            "    if not mine:\n        return [] if record.get('state') == 'settled' else ['unresolved_decision:' + rid]  # defect\n",
            'consumers/inline-bypass', module='control_decision_dependency.py')
    # VELDO-0042: each criterion's declared falsifier first, then a second, different defect per row.
    def clone(name, module, old, new, row, also=()):
        add(42, name, '66_veldo_0042_clones.py', module, old, new, ['clone/' + row], also)

    # AC1 (declared falsifier): provision from the source repository's current HEAD instead of the
    # accepted commit; the accepted-source tree comparison then refuses, so no clone stands at the
    # accepted commit. Then the tree comparison reads the wrong accepted field, refusing a correct clone.
    clone('clone-provision-from-head', 'control_clone.py',
          "            commit = accepted['commit']\n",
          "            commit = _git('-C', accepted['path'], 'rev-parse', 'HEAD', check=False).stdout.strip() or accepted['commit']\n",
          'accepted-commit')
    clone('clone-verify-wrong-accepted-field', 'control_clone.py',
          "        if head != accepted['commit'] or tree != accepted['tree'] or status.returncode or status.stdout.strip():\n",
          "        if head != accepted['tree'] or tree != accepted['tree'] or status.returncode or status.stdout.strip():\n",
          'accepted-commit')
    # AC1: a worker's direct writes to another clone, the store, the keys, the authority's Git
    # metadata and a cache are denied. Declared: the Landlock ruleset is never applied; then the
    # clone records no protected target, so the whole file system is granted.
    grants_line = "    return rules(protected['write'], protected['read'], write, [pin['cache'] for pin in manifest['pins']])\n"
    clone('clone-confinement-not-restricted', 'control_clone.py',
          "        if libc.syscall(ctypes.c_long(restrict_self), ctypes.c_int(ruleset), ctypes.c_uint32(0)) < 0:\n",
          "        if False:\n", 'worker-writes-confined')
    clone('clone-grants-everything', 'control_clone.py', grants_line,
          "    return rules([], [], write, [pin['cache'] for pin in manifest['pins']])\n", 'worker-writes-confined')
    # Every protected target, writes and reads: the read denial has no target, so an unnamed
    # repository's cache and the keys are readable; the cache root itself is granted back for
    # reading instead of the named caches; the clone root is granted back instead of the work tree,
    # so a worker rewrites its own manifest and entrance records.
    clone('clone-reads-not-denied', 'control_clone.py', grants_line,
          "    return rules(protected['write'], [], write, [pin['cache'] for pin in manifest['pins']])\n",
          'protected-targets-denied')
    clone('clone-cache-root-readable', 'control_clone.py', grants_line,
          "    return rules(protected['write'], protected['read'], write, [str(Path(manifest['pins'][0]['cache']).parent)])\n",
          'protected-targets-denied')
    clone('clone-own-root-writable', 'control_clone.py',
          "    write = [user['scratch']] + ([manifest['work']] if user.get('role') == 'worker' else [])\n",
          "    write = [user['scratch']] + ([manifest['root']] if user.get('role') == 'worker' else [])\n",
          'protected-targets-denied')
    # A confined engine keeps every capability outside the protected targets: the confinement is the
    # allow list again (everything denied but the clone and scratch); then the grant walks only the
    # protected targets' own parent directories, so the home directory's entries, the temporary
    # directories and /dev/shm are never granted.
    clone('clone-confinement-allow-list', 'control_clone.py', grants_line,
          "    return rules(['/'], protected['read'], write, [pin['cache'] for pin in manifest['pins']])\n",
          'real-engines-run-confined')
    clone('clone-chain-walked-one-level', 'control_clone.py',
          "    for ancestor in sorted(p for p in chain if not any(_beneath(p, t) for t in targets)):\n",
          "    for ancestor in sorted({t.parent for t in targets}):\n", 'real-engines-run-confined')
    # A consumer writes none of the clone: it is granted the work tree like a worker; then consumers
    # get the old allow list and lose their everyday locations.
    clone('clone-consumer-granted-work-tree', 'control_clone.py',
          "    write = [user['scratch']] + ([manifest['work']] if user.get('role') == 'worker' else [])\n",
          "    write = [user['scratch'], manifest['work']]\n", 'consumer-confined')
    clone('clone-consumer-allow-list', 'control_clone.py', grants_line,
          "    if user.get('role') != 'worker':\n"
          "        return rules(['/'], protected['read'], write, [pin['cache'] for pin in manifest['pins']])\n"
          + grants_line, 'consumer-confined')
    # AC2 (declared falsifier): a single pooled cache across repositories, so an alternate exposes an
    # unnamed repository's objects to a clone that never named it. Then an attachment is dropped from
    # the clone's alternate, so its named object is not exposed.
    clone('clone-pooled-cache', 'control_clone.py',
          "        name = hashlib.sha256(('%s\\n%s' % (domain, repository)).encode()).hexdigest()[:32]\n",
          "        name = 'pooled'\n", 'named-attachment-and-unnamed')
    clone('clone-attachment-ref-wrong-commit', 'control_clone.py',
          "                _git('-C', work, 'update-ref', ATTACHMENT_PREFIX + attachment['name'], attachment['commit'])\n",
          "                _git('-C', work, 'update-ref', ATTACHMENT_PREFIX + attachment['name'], accepted['commit'])\n",
          'named-attachment-and-unnamed')
    # AC2: ordinary garbage collection retains the live pinned objects. Declared: the fetch holds no
    # durable pin ref and the missing-pin guard is off, so gc prunes the objects under a running clone.
    # Then the fetch names no destination ref at all, which the guard catches before any clone exists.
    clone('clone-pin-not-held', 'control_clone.py',
          "        if seen != commit:\n",
          "        if False:\n", 'pins-survive-gc',
          also=(["'%s:%s' % (commit, ref),", "'%s' % commit,"],))
    clone('clone-pin-not-created', 'control_clone.py',
          "        _git('-C', cache, 'fetch', '-q', '--no-tags', '--no-write-fetch-head', source, '%s:%s' % (commit, ref),\n",
          "        _git('-C', cache, 'fetch', '-q', '--no-tags', '--no-write-fetch-head', source, '%s' % commit,\n",
          'pins-survive-gc')
    # AC3 (declared falsifier): cleanup releases a clone's pins while a child still reads it. Then a
    # user's ending is decided from the record alone, ignoring the kernel that says the process lives.
    clone('clone-release-while-child-reads', 'control_clone.py',
          "        if live:\n", "        if False:\n", 'retire-after-users-end')
    clone('clone-user-ended-ignores-kernel', 'control_clone.py',
          "        ended = (record.get('state') in ENDED and seen['terminated'] and seen['cleaned'] and not entered_alive\n"
          "                 and not unknown)\n",
          "        ended = record.get('state') in ENDED\n", 'retire-after-users-end')
    # The real VELDO-0040 group path: a user whose own process has exited but whose group still holds
    # a child reading the clone has ended when its group's emptiness is ignored; then a user entered on
    # this host whose group was never recorded counts as ended (retirement no longer fails closed).
    clone('clone-group-emptiness-ignored', 'control_clone.py',
          "        ended = (record.get('state') in ENDED and seen['terminated'] and seen['cleaned'] and not entered_alive\n",
          "        ended = (record.get('state') in ENDED and seen['terminated'] and not entered_alive\n",
          'retire-waits-for-group')
    clone('clone-unknown-group-ended', 'control_clone.py',
          "        unknown = bool(here) and (not cgroup or any(e.get('cgroup') != cgroup for e in here))\n",
          "        unknown = False\n", 'retire-waits-for-group')
    # Installation: each module this change installs is laid down by the scaffold.
    clone('clone-module-not-scaffolded', 'init_scaffold.py', '    ".veldo/control_clone.py",\n', '',
          'installed-assets')
    clone('clone-env-provision-not-scaffolded', 'init_scaffold.py', '    ".veldo/env_provision.py",\n', '',
          'installed-assets')

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
    # Since VELDO-0041 the loop's wait is the least of its timers (the deadline on the wall clock, the
    # stop, the missed-heartbeat deadline and the settling on the monotonic one) and a stop begins with
    # its cause alone, so the late deadline and the stop at close are made there.
    dispatch('dispatch-closed-output-late-deadline', 'control_launch.py',
             "                waits = [contract['deadline'] - time.time()] if live else []\n",
             "                waits = [contract['deadline'] + 30 - time.time()] if live else []\n",
             'deadline-after-closed-output')
    dispatch('dispatch-closed-output-killed-at-close', 'control_launch.py', closed,
             closed + "                            begin('deadline')  # defect: stopped when it closes\n",
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
    # Re-pointed by VELDO-0041 at the loop's least-timer wait and at the worker's exit, which leaves the
    # wrapper's own heartbeat SETTLE_SECONDS to end before what is left is stopped.
    contain('containment-exit-polled', 'control_launch.py',
            "                timeout = max(0, math.ceil(min(waits) * 1000)) if waits else None\n",
            "                timeout = 50  # defect: the reap wakes every 50 ms to look\n", 'exit-notified')
    contain('containment-exit-leaves-descendants', 'control_launch.py',
            "                if code is not None and (group is None or not group.populated()):\n",
            "                if code is not None:  # defect: the exit ends the reap while the group still runs\n",
            'ordinary-exit',
            also=[("                        if stop is not None and group.populated():\n"
                   "                            if group.members() or watch is None:\n"
                   "                                stop.adapter_exited(time.monotonic())\n"
                   "                            else:\n"
                   "                                # Only the wrapper's heartbeat is left, and it ends on the worker's exit.\n"
                   "                                settle = time.monotonic() + HB.SETTLE_SECONDS\n", "")])
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
    # VELDO-0041: each criterion's declared falsifier and further defects, each against the one suite
    # row it names. Anchors are exact text in the production modules suite 67 installs.
    def beat(name, module, old, new, row, also=()):
        add(41, name, '67_veldo_0041_heartbeat.py', module, old, new, [row], also)

    # AC1, declared: heartbeats are emitted only once the model call has returned.
    beat('heartbeat-after-model-return', 'control_heartbeat.py',
         "        started, seq = time.monotonic(), 0\n",
         "        started, seq = time.monotonic(), 0\n"
         "        poller.poll()  # defect: the heartbeat waits for the engine's model call to return\n",
         'heartbeat/blocked-call-liveness')
    beat('heartbeat-renewal-skipped', 'control_launch.py',
         "        renewed, refusal = self.renewals.renew(contract, contract_digest, process, beat['seq'], time.time())\n",
         "        renewed, refusal = None, None  # defect: a heartbeat does not renew the claim\n",
         'heartbeat/blocked-call-liveness')
    beat('heartbeat-configured-interval-ignored', 'control_launch.py',
         "                   '--heartbeat', str(beat), repr(float(interval))] + argv\n",
         "                   '--heartbeat', str(beat), repr(float(C.SETTINGS['heartbeat_seconds']['default']))] + argv"
         "  # defect: the wrapper beats at the shipped interval, not the configured one\n",
         'heartbeat/blocked-call-liveness')
    beat('heartbeat-missing-not-stopped', 'control_launch.py',
         "                elif cause is None and code is None and watch is not None and watch.expired(now):\n",
         "                elif False:  # defect: a missing heartbeat is never acted on\n",
         'heartbeat/missing-heartbeat-stop')
    beat('heartbeat-window-from-first', 'control_heartbeat.py',
         "        return (self.last if self.last is not None else self.released) + self.window\n",
         "        return (self.first if self.first is not None else self.released) + self.window  # defect\n",
         'heartbeat/missing-heartbeat-stop')
    beat('heartbeat-default-interval', 'control_containment.py',
         "    'heartbeat_seconds': dict(required=False, kind='seconds', default=10, controls=[],\n",
         "    'heartbeat_seconds': dict(required=False, kind='seconds', default=5, controls=[],  # defect\n",
         'heartbeat/shipped-defaults')
    beat('heartbeat-default-window', 'control_containment.py',
         "    'heartbeat_window_seconds': dict(required=False, kind='seconds', default=30, controls=[],\n",
         "    'heartbeat_window_seconds': dict(required=False, kind='seconds', default=60, controls=[],  # defect\n",
         'heartbeat/shipped-defaults')
    beat('stop-default-grace', 'control_containment.py',
         "    'stop_grace_seconds': dict(required=False, kind='seconds', default=10, controls=[],\n",
         "    'stop_grace_seconds': dict(required=False, kind='seconds', default=15, controls=[],  # defect\n",
         'heartbeat/shipped-defaults')
    # AC2, declared: termination is sent only to the parent.
    beat('stop-terminate-only-parent', 'control_containment.py',
         "        elif stage == 'terminate':\n            self.group.terminate()\n",
         "        elif stage == 'terminate':\n"
         "            with contextlib.suppress(ProcessLookupError):\n"
         "                os.kill(self.pid, signal.SIGTERM)  # defect: termination goes to the parent only\n",
         'stop/bounded-group-exit')
    beat('stop-configured-graces-ignored', 'control_launch.py',
         "        return self._settings('stop_grace_seconds', 'kill_grace_seconds')\n",
         "        return tuple(C.SETTINGS[n]['default'] for n in ('stop_grace_seconds', 'kill_grace_seconds'))  # defect\n",
         'stop/bounded-group-exit')
    beat('stop-kill-at-termination', 'control_containment.py',
         "{'cooperative': stop_grace, 'terminate': kill_grace,",
         "{'cooperative': stop_grace, 'terminate': 0,", 'stop/bounded-group-exit')
    # AC3, declared: the slot is released before the descendants have ended.
    beat('retire-before-descendant-termination', 'control_retirement.py',
         "        kernel = C.retirement(entry['group'], record.get('process'))\n",
         "        kernel = C.retirement(None, record.get('process'))  # defect: only the worker is looked at\n",
         'retirement/live-descendant')
    beat('retire-on-first-observation', 'control_retirement.py',
         "            seen = self._observe(dispatch_id, entry)\n            entry['observed'] = seen\n",
         "            seen = entry.setdefault('first_seen', self._observe(dispatch_id, entry))  # defect: stale\n"
         "            entry['observed'] = seen\n",
         'retirement/live-descendant')
    beat('retire-without-accounting', 'control_reservations.py',
         "            if any(r['state'] not in ('settled', 'unknown') for r in calls):\n"
         "                raise Refused('missing_accounting')\n",
         "", 'retirement/missing-accounting')
    beat('retire-pending-call-settled', 'control_reservations.py',
         "            if any(r['state'] not in ('settled', 'unknown') for r in calls):\n",
         "            if any(r['state'] not in ('settled', 'unknown', 'pending') for r in calls):  # defect\n",
         'retirement/missing-accounting')
    beat('retire-drops-unknown-accounting', 'control_retirement.py',
         "        retained = {'accounting_unknown': {r['invocation']: sorted(r['unknown']) for r in calls if r['unknown']}}\n",
         "        retained = {'accounting_unknown': {}}  # defect: what stays unknown is dropped\n",
         'retirement/missing-accounting')
    beat('retire-leaves-clone-files', 'control_retirement.py',
         "            'clone': dict(clone, open=clone['present']) if clone else {'open': False, 'clone_id': None},\n",
         "            'clone': {'open': False, 'clone_id': None},  # defect: the clone files are no obligation\n",
         'retirement/clone-files')
    beat('retire-clone-group-unrecorded', 'control_retirement.py',
         "                self.clones.record_group(dispatch_id, {k: entry['group'].get(k) for k in ('unit', 'slice', 'cgroup')})\n",
         "                pass  # defect: the receiver's group is not recorded on the clone's user\n",
         'retirement/clone-files')
    beat('retire-trusts-teardown-answer', 'control_retirement.py',
         "'present': bool(self.clones._is_live(clone['handle'])),",
         "'present': clone['teardown'] is None,  # defect: the teardown's answer, not the files", 'retirement/clone-files')
    beat('retire-unknown-outcome-conclusive', 'control_retirement.py',
         "CONCLUSIVE = ('prepared', 'exited', 'refused')\n",
         "CONCLUSIVE = ('prepared', 'exited', 'refused', 'unknown')  # defect\n", 'retirement/unknown-outcome')
    beat('retire-open-outcome-released', 'control_retirement.py',
         "            if first in ('outcome', 'clone'):\n",
         "            if first in ('clone',):  # defect: an open outcome does not hold the slot\n",
         'retirement/unknown-outcome')
    beat('retire-refusal-unclassified', 'control_retirement.py',
         "refusal=code, taxonomy=taxonomy(code),", "refusal=code, taxonomy=None,", 'retirement/observations')
    beat('retire-pending-unlisted', 'control_retirement.py',
         "            if slot is not None and not slot.get('retired'):\n",
         "            if False:  # defect: a held slot is not listed as pending\n", 'retirement/observations')
    # AC3, review of 5f53aa3: a refused retirement is retried by the runner itself when what it waits on is
    # completed, and the retry is the same single release.
    beat('retire-report-not-subscribed', 'control_retirement.py',
         "        reservations.observe = observe\n",
         "        pass  # defect: the final accounting report is never listened for\n",
         'retirement/missing-accounting')
    beat('retire-retry-releases-twice', 'control_retirement.py',
         "        request = 'retire/' + dispatch_id\n",
         "        request = 'retire/%s/%d' % (dispatch_id, entry['attempts'])  # defect: each attempt a request of its own\n",
         'retirement/missing-accounting',
         also=[("        if slot is not None and slot.get('retired'):\n"
                "            return self._refused(entry, event, 'already_retired')\n",
                "        pass  # defect: a released slot is not looked at before it is released again\n")])
    beat('retire-clone-removal-not-retried', 'control_retirement.py',
         "                    try:\n                        self._retry(other, 'clone_removed')\n",
         "                    try:\n                        pass  # defect: the retirements waiting on the removed clone wait on\n",
         'retirement/clone-files')
    beat('retire-pending-never-retried', 'control_retirement.py',
         "        self.counts['retried'] += 1\n        return self._attempt(dispatch_id, entry, basis)\n",
         "        return False  # defect: a pending retirement is never tried again\n",
         'retirement/clone-files')
    beat('retire-no-sweep-on-wait', 'control_launch.py',
         "        self.launches.pop(launch.dispatch_id, None)\n"
         "        # This dispatch's end may have completed another's obligation (a group the kernel emptied).\n"
         "        self.sweep()\n",
         "        self.launches.pop(launch.dispatch_id, None)  # defect: a wait sweeps no pending retirement\n",
         'retirement/live-descendant')
    beat('retire-no-sweep-on-prepare', 'control_launch.py',
         "        self.sweep()\n        now = self.clock()\n",
         "        now = self.clock()  # defect: a preparation sweeps no pending retirement\n",
         'retirement/unknown-outcome')
    beat('retire-sweep-retries-unchanged', 'control_retirement.py',
         "        if seen['open'] != entry['open']:\n            return True\n",
         "        return True  # defect: tried again whether or not anything it waits on changed\n",
         'retirement/unknown-outcome')
    # AC1, review of 5f53aa3: the heartbeat outlives a signal the engine sends its own group, and the engine
    # holds no end of the heartbeat channel.
    beat('heartbeat-shares-engine-session', 'control_heartbeat.py',
         "                os.setsid()\n", "", 'heartbeat/engine-group-signal')
    beat('heartbeat-channel-left-to-engine', 'control_heartbeat.py',
         "        os.close(engine)\n        os.close(fd)\n",
         "        os.close(engine)  # defect: the channel stays open into the engine\n",
         'heartbeat/channel-not-held')
    beat('heartbeat-not-installed', 'init_scaffold.py', '    ".veldo/control_heartbeat.py",\n', '',
         'retirement/installed-assets')
    beat('retirement-not-installed', 'init_scaffold.py', '    ".veldo/control_retirement.py",\n', '',
         'retirement/installed-assets')
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

    # VELDO-0056: each criterion's declared falsifier and further defects, each against the one suite 67
    # row it names. Anchors are exact text in .veldo/lander.py, the one production module suite 67 installs.
    def candidate(name, old, new, row, also=()):
        add(56, name, '67_veldo_0056_candidates.py', 'lander.py', old, new, ['candidate/' + row], also)

    init_anchor = '            self._git(workspace, "init", "-q", "--template=")\n'
    # AC1, declared: sync_main checks out the trunk (held by another worktree, so the checkout fails).
    candidate('candidate-checks-out-trunk', init_anchor,
              '            self._git(self.repo_root, "checkout", self.trunk, ok=None)  # defect: sync_main checks out the trunk\n'
              + init_anchor, 'detached-held-trunk')
    candidate('candidate-checkout-ignores-other-worktrees', init_anchor,
              '            self._git(self.repo_root, "checkout", "-q", "--ignore-other-worktrees", self.trunk, ok=None)'
              '  # defect: the trunk is checked out in the caller anyway\n' + init_anchor, 'detached-held-trunk')
    candidate('candidate-fetch-into-caller',
              '                self._git(workspace, "fetch", "-q", "--no-tags", "--no-write-fetch-head", self._absolute(url),\n',
              '                self._git(self.repo_root, "fetch", "-q", "--no-tags", "--no-write-fetch-head", self._absolute(url),'
              '  # defect: the fetch writes the caller\'s refs\n', 'detached-held-trunk')
    # AC1: the whole candidate, before verification.
    ancestry = ('            for older, what in ((c["watermark"], "watermark"), (implementation, "implementation"), '
                '(evidence, "evidence")):\n')
    unverified = '            for older, what in ():  # defect: the candidate\'s ancestry is not verified\n'
    candidate('candidate-evidence-not-merged',
              '            self._merge(workspace, evidence, "Land evidence %s of %s" % (evidence[:12], sid), identity, "evidence")\n',
              '            pass  # defect: the evidence commit is not merged\n', 'whole-candidate', also=[(ancestry, unverified)])
    candidate('candidate-projection-skipped', '            self._project(workspace, sid, identity)\n',
              '            pass  # defect: the projections are not derived\n', 'whole-candidate')
    candidate('candidate-watermark-from-caller-trunk',
              '            if self.push:\n                url = self._git(self.repo_root, "remote", "get-url", self.remote, profile="network")',
              '            if False:  # defect: the watermark is the caller\'s local trunk, never the published one\n'
              '                url = self._git(self.repo_root, "remote", "get-url", self.remote, profile="network")',
              'whole-candidate')
    # AC2, declared: a merge failure is ignored and the land continues to the gate. The fixed code refuses a
    # real conflict AND verifies the candidate's ancestry, so the defect needs both guards gone.
    candidate('candidate-merge-failure-ignored',
              '        if real:\n            raise CandidateRefused("conflict:" + real[0], "a real conflict the build must resolve",\n'
              '                                   operation="merge", conflicts=real)\n',
              '        if real:\n            self._git(workspace, "merge", "--abort")  # defect: the failed merge is ignored\n'
              '            return\n', 'git-failures-refuse', also=[(ancestry, unverified)])
    candidate('candidate-fetch-failure-ignored',
              '                          "+refs/heads/%s:%s" % (self.trunk, WATERMARK_REF), profile="network")\n',
              '                          "+refs/heads/%s:%s" % (self.trunk, WATERMARK_REF), profile="network", ok=None)'
              '  # defect: a failed fetch is ignored\n', 'git-failures-refuse')
    candidate('candidate-missing-evidence-accepted',
              '            if not listed.stdout.strip():\n'
              '                raise CandidateRefused("missing_evidence:proof/" + sid, path + " is absent at the evidence commit")\n'
              '            body = self._git(workspace, "cat-file", "blob", "%s:%s" % (evidence, path), text=False).stdout\n',
              '            if not listed.stdout.strip():\n'
              '                body = json.dumps({"commit": evidence}).encode()  # defect: a build without its proof lands as its own implementation\n'
              '            else:\n'
              '                body = self._git(workspace, "cat-file", "blob", "%s:%s" % (evidence, path), text=False).stdout\n',
              'git-failures-refuse')
    # AC2: every Git invocation of the candidate path is checked.
    candidate('candidate-projection-commit-unchecked',
              '                      % (", ".join(sorted(state)), sid, self.candidate["watermark"][:12]), identity=identity)\n',
              '                      % (", ".join(sorted(state)), sid, self.candidate["watermark"][:12]), identity=identity, ok=None)'
              '  # defect: a failed projection commit is ignored\n', 'every-git-operation-checked')
    candidate('candidate-tree-lookup-unchecked',
              '            tree = self._git(workspace, "rev-parse", "--verify", candidate + "^{tree}").stdout.strip()\n',
              '            tree = self._git(workspace, "rev-parse", "--verify", candidate + "^{tree}", ok=None).stdout.strip()'
              '  # defect: a failed object lookup is ignored\n', 'every-git-operation-checked')
    candidate('candidate-union-stage-read-as-empty',
              '                body = (self._git(workspace, "cat-file", "blob", stages[stage], text=False).stdout\n',
              '                body = (self._git(workspace, "cat-file", "blob", stages[stage], text=False, ok=None).stdout'
              '  # defect: an unreadable side is read as empty\n', 'every-git-operation-checked')
    # AC3, declared: the trunk moves before the policy accepts.
    policy_anchor = '        refusals, detail = [], {}\n        if self.policy is None:\n'
    candidate('candidate-trunk-moved-before-policy', policy_anchor,
              '        self._git(c["workspace"], "push", "-q", self._absolute(self._git(self.repo_root, "remote", "get-url", "--push",\n'
              '                  self.remote, profile="network").stdout.strip()), "%s:refs/heads/%s" % (c["commit"], self.trunk),\n'
              '                  profile="network", ok=None)  # defect: the trunk moves before the policy accepts\n' + policy_anchor,
              'rejection-leaves-trunk')
    # VELDO-0058: finalize accepts the gate's external observation again before anything moves, so a
    # red gate that is not a refusal is also accepted there: the defect is both edits.
    candidate('candidate-gate-result-ignored',
              '        if not green:\n            ran_red = exit_code != 0 or terminal != "GATE: GREEN (%s)" % c["commit"]\n',
              '        if False:  # defect: a red gate is not a refusal\n'
              '            ran_red = exit_code != 0 or terminal != "GATE: GREEN (%s)" % c["commit"]\n',
              'rejection-leaves-trunk',
              also=[('        accepted = verification_organ().accept((c.get("gate") or {}).get("observation"), c["workspace"], c["commit"],\n'
                     '                                               bind_refs=True)\n',
                     '        accepted = []  # defect: the gate\'s observation is not accepted again\n')])
    candidate('candidate-policy-refusal-ignored',
              '        if refusals:\n            error = CandidateRefused(refusals[0], "; ".join(refusals), operation="policy")\n',
              '        if False:  # defect: a policy refusal is not a refusal\n'
              '            error = CandidateRefused(refusals[0], "; ".join(refusals), operation="policy")\n',
              'rejection-leaves-trunk')
    # AC3: each decider the policy asks is asked, about this candidate.
    candidate('candidate-proof-not-resolved',
              '            bundle = self.CP.resolve(self.store, self.conn, domain=self.domain, repository=self.repository,\n'
              '                                     unit=sid, commit=candidate["evidence"])\n',
              '            bundle = {"implementation": {"commit": candidate.get("implementation")}}  # defect: the proof is not resolved\n',
              'named-policy-refusals')
    candidate('candidate-review-not-read',
              '        record = self.floor.record(sid) if self.floor is not None else None\n',
              '        record = {"state": "handoff", "handoff": {"source": {"commit": candidate["evidence"]},\n'
              '                  "proof": dict(candidate.get("proof") or {})}}  # defect: the review obligations are not read\n',
              'named-policy-refusals')
    candidate('candidate-findings-not-counted',
              '            refusals.extend("unresolved_finding:" + fid for fid, f in sorted((record.get("findings") or {}).items())\n'
              '                            if not (f or {}).get("resolved"))\n',
              '            pass  # defect: an unresolved finding is not a refusal\n', 'named-policy-refusals')
    candidate('candidate-publication-not-decided',
              '        decision = gate.decide("publication", sid, context=context)\n',
              '        decision = {"decision_id": None, "refusals": []}  # defect: the publication station is not asked\n',
              'named-policy-refusals')
    # Observability.
    candidate('candidate-refusal-not-observed',
              '        self._event(operation, "refused", error.code, detail=error.detail, failed=error.operation)\n',
              '        pass  # defect: a refusal is not observed\n', 'observations')
    candidate('candidate-unknown-classified',
              '    return TAXONOMY.get(str(code).split(":", 1)[0], "unknown_outcome")\n',
              '    return TAXONOMY.get(str(code).split(":", 1)[0], "missing_evidence")  # defect: an unknown code is classified\n',
              'observations')
    candidate('candidate-pending-hidden',
              '        pending = [c["id"]] if c.get("state") in ("synced", "built", "verified") else []\n',
              '        pending = []  # defect: pending work is not exposed\n', 'observations')

    # VELDO-0047: each criterion's declared falsifier and further defects, each against the one suite
    # row it names. The unit template is a production file like the modules beside it.
    def service(name, module, old, new, row, also=()):
        add(47, name, '66_veldo_0047_authority.py', module, old, new, ['authority/' + row], also)

    # AC1: the key directory is placed where no worker writes directly.
    service('authority-key-placement-worker-writable-ignored', 'control_service.py',
            "    if any(_within(real, os.path.realpath(root)) or _within(os.path.realpath(root), real) for root in writable):\n"
            "        problems.append('invalid_input:key_directory:worker_writable')\n",
            "    pass  # defect: a directory workers write into may hold the keys\n", 'key-directory-placement')
    service('authority-key-placement-mode-ignored', 'control_service.py',
            "    if stat.S_IMODE(info.st_mode) & 0o077:\n        problems.append('invalid_input:key_directory:mode')\n",
            "    pass  # defect: a key directory others can enter is accepted\n", 'key-directory-placement')
    service('authority-key-placement-link-followed', 'control_service.py',
            "    keys = str(key_directory) if key_directory else",
            "    keys = os.path.realpath(str(key_directory)) if key_directory else", 'key-directory-placement')
    # AC1: an absent key directory is judged by where it would be before whether it exists.
    service('authority-key-existence-judged-alone', 'control_service.py',
            "        return problems + ['missing_authority:key_directory:absent']\n",
            "        return ['missing_authority:key_directory:absent']  # defect: an absent directory is judged by existence alone\n",
            'key-directory-location-before-existence')
    service('authority-key-absent-not-located', 'control_service.py',
            "    if any(_within(real, os.path.realpath(root)) or _within(os.path.realpath(root), real) for root in writable):\n",
            "    if os.path.lexists(text) and any(_within(real, os.path.realpath(root)) or _within(os.path.realpath(root), real)\n"
            "                                     for root in writable):  # defect: an absent directory is not located\n",
            'key-directory-location-before-existence')
    # AC1: the one-time step creates only what is missing and changes no directory that exists.
    service('authority-key-guidance-names-the-parent', 'control_service.py',
            "        missing = _missing_below(path)\n",
            "        missing = [os.path.dirname(str(path)), str(path)]  # defect: the parent is named, and its mode set, whether or not it exists\n",
            'key-directory-guidance-changes-no-directory')
    service('authority-key-guidance-includes-the-ancestor', 'control_service.py',
            "    return list(reversed(missing))\n",
            "    return list(reversed(missing + [current]))  # defect: the first existing ancestor is named too\n",
            'key-directory-guidance-changes-no-directory')
    service('authority-key-guidance-changes-the-mode', 'control_service.py',
            "        return 'it is open to others; a key directory is one of its own, so ' + elsewhere\n",
            "        return 'close it to everyone else: chmod 0700 %s' % path  # defect: the guidance changes an existing directory\n",
            'key-directory-guidance-changes-no-directory')
    # AC1: a relative key directory is refused as relative before anything resolves it.
    service('authority-key-directory-made-absolute', 'control_service.py',
            "    keys = str(key_directory) if key_directory else os.path.join(DEFAULT_KEY_ROOT, service)\n",
            "    keys = os.path.abspath(str(key_directory)) if key_directory else os.path.join(DEFAULT_KEY_ROOT, service)  # defect: resolved first\n",
            'key-directory-relative-refused')
    service('authority-key-relative-not-refused', 'control_service.py',
            "    if not os.path.isabs(text):\n        return ['invalid_input:key_directory:relative']\n",
            "    pass  # defect: a relative key directory is judged wherever it resolves\n", 'key-directory-relative-refused')
    # AC1: the launch receiver's configuration carries this host's qualified worker profile.
    service('authority-receiver-profile-omitted', 'control_service.py',
            "                                'profile': profile, 'adapters': adapters}), 0o600)\n",
            "                                'adapters': adapters}), 0o600)  # defect: the receiver gets no worker profile\n",
            'receiver-configured-with-host-profile')
    service('authority-profile-not-qualified', 'control_service.py',
            "    if not qualification['qualified']:\n"
            "        raise Refused(qualification['refusal'], 'the worker profile is not qualified on this host')\n",
            "    pass  # defect: an unqualified worker profile is installed\n", 'receiver-configured-with-host-profile')
    # AC1: a fixed executable and a protected configuration, and installation starts nothing.
    service('authority-config-readable', 'control_service.py',
            "        _write(config_path, _json(config), 0o600)\n",
            "        _write(config_path, _json(config), 0o644)  # defect: the configuration is readable by everyone\n",
            'installed-fixed-and-protected')
    service('authority-install-starts-it', 'control_service.py',
            "    reload_rc, _out, _err = runner.run(['daemon-reload'])\n",
            "    reload_rc, _out, _err = runner.run(['daemon-reload'])\n"
            "    runner.run(['start', unit])  # defect: installation starts the authority\n", 'installed-fixed-and-protected')
    service('authority-runs-the-source-copy', 'control_service.py',
            "'EXECUTABLE': os.path.join(bin_dir, 'control_service.py'), 'CONFIG': config_path}\n",
            "'EXECUTABLE': str(HERE / 'control_service.py'), 'CONFIG': config_path}  # defect: the unit runs the source copy\n",
            'installed-fixed-and-protected')
    service('authority-unit-starts-at-login', 'services/veldo-authority.service',
            "TimeoutStopSec=15\n", "TimeoutStopSec=15\n\n[Install]\nWantedBy=default.target\n",
            'installed-fixed-and-protected')
    # AC1: the fixed executable holds what its programs load, the validator the receiver's recheck runs
    # included, so the installed receiver launches (the review's blocking finding).
    seeds = "    seeds = set(ENTRY_POINTS) | {name for _role, name in EL.VALIDATOR_ROLES}\n"
    # The defect the review found, restored: the hand list the installer copied before closure() existed.
    service('authority-closure-listed-by-hand', 'control_service.py',
            "    fixed = {name: (HERE / name).read_bytes() for name in closure()}\n",
            "    fixed = {name: (HERE / name).read_bytes() for name in (  # defect: the installed modules listed by hand\n"
            "        'authority_contract.py', 'claim.py', 'completion_contract.py', 'control_channel_attribution.py',\n"
            "        'control_channel_enrollment.py', 'control_channel_presentation.py', 'control_channel_projection.py',\n"
            "        'control_claim.py', 'control_client.py', 'control_containment.py', 'control_decision_dependency.py',\n"
            "        'control_dispatch.py', 'control_eligibility.py', 'control_enrollment.py', 'control_keys.py',\n"
            "        'control_keys_custody.py', 'control_launch.py', 'control_membership.py', 'control_reservations.py',\n"
            "        'control_service.py', 'control_signer.py', 'control_signer_answers.py', 'control_snapshot.py',\n"
            "        'control_store.py', 'git_process.py')}\n", 'installed-fixed-and-protected')
    # Re-aimed 2026-09-24: VELDO-0134 made control_eligibility load control_architecture, which loads the
    # validator, so the seed alone no longer decides it; the defect is the installed set lacking the validator.
    service('authority-closure-omits-the-validator', 'control_service.py',
            '        return sorted(members)\n',
            "        return sorted(members - {name for _role, name in EL.VALIDATOR_ROLES})  # defect: the validator the receiver's recheck runs is not installed\n",
            'installed-receiver-launches')
    service('authority-closure-ignores-loader-helpers', 'control_service.py',
            "            if not options:\n                continue\n",
            "            if True:  # defect: what a loader helper loads (organ('x')) is not followed\n"
            "                accounted.add(id(target))\n                continue\n", 'installed-receiver-launches')
    # AC1: a load the installer cannot derive, or of a module the engine lacks, refuses installation.
    service('authority-closure-unresolved-installed', 'control_service.py',
            "        if unresolved:\n            raise Refused('invalid_input:closure:unresolved',",
            "        if False:  # defect: a load no literal names is installed as if it were not there\n"
            "            raise Refused('invalid_input:closure:unresolved',", 'installation-refuses-an-underivable-closure')
    service('authority-closure-absent-installed', 'control_service.py',
            "        if absent:\n            raise Refused('invalid_input:closure:absent',",
            "        if False:  # defect: a module the engine lacks is left out of the installation\n"
            "            raise Refused('invalid_input:closure:absent',", 'installation-refuses-an-underivable-closure')
    service('authority-receiver-workspace-omitted', 'control_service.py',
            "'authority_generation': first['authority_generation'], 'workspace': members[0],\n",
            "'authority_generation': first['authority_generation'], 'workspace': None,  # defect: the receiver judges no workspace\n",
            'installed-receiver-launches')
    # AC1, declared: two instances acquire scheduling authority.
    service('authority-two-schedulers', 'control_service.py',
            "        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)\n",
            "        pass  # defect: a second instance takes scheduling authority too\n", 'one-instance-under-the-lock')
    service('authority-lock-file-replaced', 'control_service.py',
            "    fd = os.open(str(path), os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)\n",
            "    with contextlib.suppress(OSError):\n"
            "        os.unlink(str(path))  # defect: the lock file is replaced, so each instance locks its own\n"
            "    fd = os.open(str(path), os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)\n",
            'one-instance-under-the-lock')
    # AC2, declared: a success is returned without changing the configured store.
    service('authority-callback-success', 'control_service.py',
            "        receipt = S.execute(self.conn, {k: command.get(k) for k in S.COMMAND_FIELDS}, self.principal, self.sign,\n"
            "                            self.generation)\n",
            "        receipt = {'committed': True, 'command_id': command.get('command_id'), 'seq': self.watermark() + 1,\n"
            "                   'record_digest': 'sha256:' + '0' * 64}  # defect: success without a commit\n",
            'mutation-reaches-the-configured-store')
    service('authority-serves-another-store', 'control_service.py',
            "        conn = S.open_store(config['store_path'])\n",
            "        conn = S.open_store(config['store_path'] + '-local')  # defect: the service keeps a store of its own\n",
            'mutation-reaches-the-configured-store')
    # AC2: the wrong coordinates or the wrong actor refuse.
    service('authority-command-signature-unchecked', 'control_service.py',
            "        if not verified:\n            raise Refused('not_authorized', 'the command signature is not the principal\\'s')\n",
            "        pass  # defect: the command's own signature is not checked\n", 'wrong-coordinates-or-actor-refused')
    service('authority-command-coordinates-unchecked', 'control_service.py',
            "        if any(command.get(k) != v for k, v in expected.items()):\n"
            "            raise Refused('invalid_input:coordinates', 'the command names another domain, store or repository')\n",
            "        pass  # defect: the command's own coordinates are not compared\n", 'wrong-coordinates-or-actor-refused')
    # AC3, declared: a client starts the service on a missing socket.
    unavailable = '            seen = last_seen(enrollment, workspace, binding)\n            raise RoutingRefused("authority_unavailable",'

    def starts_on(error):
        return ("            if isinstance(e, %s) and not getattr(send, 'starting', False):\n"
                "                import subprocess  # defect: a client starts the authority itself\n"
                "                subprocess.run(['systemctl', '--user', 'start', service_unit(binding)], capture_output=True,\n"
                "                               timeout=30)\n"
                "                send.starting = True\n"
                "                try:\n"
                "                    return send(workspace, command, enrollment, verify, sign, host_identity, timeout, seen_at)\n"
                "                finally:\n"
                "                    send.starting = False\n" % error + unavailable)
    service('authority-client-starts-missing-service', 'control_client.py', unavailable, starts_on('FileNotFoundError'),
            'absent-service-refuses-by-name')
    service('authority-client-queues-locally', 'control_client.py', unavailable,
            "            queue = os.path.join(os.path.dirname(seen_path(enrollment, workspace)), 'pending.jsonl')\n"
            "            os.makedirs(os.path.dirname(queue), exist_ok=True)\n"
            "            with open(queue, 'a') as pending:  # defect: a client keeps the command until the authority returns\n"
            "                pending.write(json.dumps(command) + '\\n')\n"
            "            return {'schema': RESPONSE_SCHEMA, 'accepted': True, 'store_uuid': binding['store_uuid'],\n"
            "                    'watermark': None, 'result': {'ok': True, 'queued': True}}\n" + unavailable,
            'absent-service-refuses-by-name')
    # AC3: an unexpected exit stays stopped until an operator starts it.
    service('authority-unit-restarts-on-failure', 'services/veldo-authority.service',
            "Restart=no\n", "Restart=on-failure\nRestartSec=100ms\n", 'unexpected-exit-waits-for-an-operator')
    service('authority-client-starts-dead-service', 'control_client.py', unavailable,
            starts_on('ConnectionRefusedError'), 'unexpected-exit-waits-for-an-operator')
    # Observability: every refusal is observed by name and class.
    service('authority-refusal-not-observed', 'control_service.py',
            "        self._count(observation)\n        return result\n",
            "        if ok:  # defect: a refused command leaves no observation\n"
            "            self._count(observation)\n        return result\n", 'observations')
    service('authority-request-refusal-not-observed', 'control_service.py',
            "        if isinstance(response, dict) and response.get('accepted') is False:\n",
            "        if False:  # defect: a request refused before apply leaves no observation\n", 'observations')
    service('authority-unknown-classified', 'control_service.py',
            "    return head if head in CLASSES else NAMED.get(head, 'unknown_outcome')\n",
            "    return head if head in CLASSES else NAMED.get(head, 'missing_evidence')  # defect: an unknown code is classified\n",
            'observations')
    # Distribution: the service and its unit template are installed assets.
    service('authority-service-not-installed', 'init_scaffold.py', '    ".veldo/control_service.py",\n', '',
            'installed-assets')
    service('authority-unit-template-not-installed', 'init_scaffold.py',
            '    ".veldo/services/veldo-authority.service",\n', '', 'installed-assets')
    service('authority-supervisor-not-installed', 'init_scaffold.py', '    ".veldo/supervisor.py",\n', '',
            'installed-assets')
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
    # Review finding: every visit to an owner wait needs an answer newer than the one the cycle last used.
    workflow('workflow-owner-answer-reused', "            if used is not None and answer['version'] <= used['version']:\n",
             '            if False:  # defect: an owner wait routes on an answer an earlier visit already used\n',
             'owner-answer-per-visit', module=cycle)
    workflow('workflow-owner-answer-not-spent',
             "                record = dict(record, answered={'version': used['version'], 'digest': used['digest']})\n",
             '                pass  # defect: the answer a visit routed on is not recorded as spent\n',
             'owner-answer-per-visit', module=cycle)
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
    # VELDO-0051: each criterion's declared falsifier and further defects, each against the one suite 66
    # row it names. Anchors are exact text in the five production modules suite 66 installs.
    def events51(name, old, new, row, module='control_event_projection.py', also=()):
        add(51, name, '66_veldo_0051_events.py', module, old, new, ['events/' + row], also)

    vocabulary = 'control_event_vocabulary.py'
    # AC1, declared: the validator no longer recognizes run.done while the emitter still writes it.
    events51('events-validator-forgets-run-done', 'EVENT_TYPES = set(_EVENT_VOCABULARY.EVENT_TYPES)\n',
             'EVENT_TYPES = set(_EVENT_VOCABULARY.EVENT_TYPES) - {"run.done"}  # defect: the validator forgets run.done\n',
             'vocabulary-roundtrip', module='validate.py')
    events51('events-emitter-forgets-run-done', 'EVENT_TYPES = set(_VOCAB.EVENT_TYPES)\n',
             'EVENT_TYPES = set(_VOCAB.EVENT_TYPES) - {"run.done"}  # defect: the emitter forgets run.done\n',
             'vocabulary-roundtrip', module='events.py')
    events51('events-historical-spelling-dropped', 'SCHEMAS = (SCHEMA,) + HISTORICAL_SCHEMAS\n',
             'SCHEMAS = (SCHEMA,)  # defect: the historical schema spelling is no longer accepted\n',
             'vocabulary-roundtrip', module=vocabulary)
    events51('events-substitution-admitted', '    if requested is not None and ev.get("type") != requested:\n',
             '    if False:  # defect: a type substituted through an extra field is admitted\n',
             'unknown-refused', module='events.py')
    events51('events-unknown-schema-validates', '    if event.get("schema") not in schemas:\n',
             '    if False:  # defect: a schema no spelling admits validates\n', 'unknown-refused', module=vocabulary)
    # AC2, declared: a committed event is skipped while the watermark still advances.
    fresh = "            fresh = [e for e in events if e['id'] not in present]\n"
    events51('projection-skips-committed-event', fresh,
             "            fresh = [e for e in events if e['id'] not in present][1:]  # defect: a committed event is skipped\n",
             'projection-prefix')
    events51('projection-rewrites-history', "        with open(self.log, 'a+') as fh:\n",
             "        with open(self.log, 'w+') as fh:  # defect: the log is rewritten, not appended\n", 'projection-prefix')
    events51('projection-watermark-unbound', "'record_digest': digests.get(target, GENESIS),",
             "'record_digest': digests.get(after, GENESIS),  # defect: the watermark names the record it started from\n                     ",
             'projection-prefix')
    # AC3, declared: spec.shipped may be emitted directly, so a build-only run can ship.
    events51('events-direct-spec-shipped', 'PROJECTION_OWNED = frozenset(_VOCAB.PROJECTIONS)\n',
             'PROJECTION_OWNED = frozenset(_VOCAB.PROJECTIONS) - {"spec.shipped"}  # defect: spec.shipped is hand-emittable\n',
             'completion-owner', module='events.py')
    events51('vocabulary-spec-shipped-hand-owned', '    "spec.shipped": JOURNAL_PROJECTION,\n',
             '    "spec.shipped": HAND,  # defect: completion is registered as a hand emission\n',
             'completion-owner', module=vocabulary)
    events51('projection-dispatch-unit-unjoined', "            if publication.get('unit') != unit:\n",
             '            if False:  # defect: the dispatch is not joined to the receipt\'s unit\n', 'confirmed-landing-only')
    events51('projection-confirmation-unrequired', '            if not confirmed(publication):\n',
             '            if False:  # defect: an unconfirmed publication counts as a landing\n', 'confirmed-landing-only')
    events51('projection-duplicate-republished', fresh,
             '            fresh = list(events)  # defect: a landing already in the log is published again\n',
             'confirmed-landing-only')
    events51('scaffold-vocabulary-not-laid',
             '    # VELDO-0051: the canonical event vocabulary events.py and validate.py both load.\n'
             '    ".veldo/control_event_vocabulary.py",\n', '', 'installed-assets', module='init_scaffold.py')
    events51('scaffold-projection-not-laid', '    ".veldo/control_event_projection.py",\n', '', 'installed-assets',
             module='init_scaffold.py')
    events51('projection-refusal-unobserved', "        for item in judged:\n",
             "        for item in [i for i in judged if not i['refusals']]:  # defect: a refused receipt is not observed\n",
             'observations')
    events51('projection-unknown-taxonomy-classified', "    return head if head in TAXONOMY else 'unknown_outcome'\n",
             "    return head if head in TAXONOMY else 'missing_evidence'  # defect: an unknown code is classified\n",
             'observations')
    events51('projection-pending-unlisted', "                    pending_events=[e['id'] for e in events if e['id'] not in present])\n",
             "                    pending_events=[])  # defect: pending landings are not listed\n", 'observations')
    # The spend recorder (a landed producer VELDO-0051 broke): its records are spend.recorded, owned by
    # spend.py, and every reader of spend actuals reads that type and the historical spec.shipped one.
    spend_rows = ['events/spend-recorded', 'events/vocabulary-roundtrip']
    add(51, 'spend-records-as-spec-shipped', '66_veldo_0051_events.py', 'spend.py',
        'SCHEMA_EVENT_TYPE = "spend.recorded"\n',
        'SCHEMA_EVENT_TYPE = "spec.shipped"  # defect: a spend record is written as completion\n', spend_rows)
    add(51, 'vocabulary-forgets-spend-recorded', '66_veldo_0051_events.py', vocabulary,
        '    "spend.recorded": SPEND_RECORDER,\n', '', spend_rows)
    events51('judgment-spend-recorded-unkinded', '    "spend.recorded": "ship_bulk",\n', '', 'spend-recorded',
             module='judgment_load.py')
    events51('judgment-historical-spend-unkinded', '    "spec.shipped": "ship_bulk",\n', '', 'spend-recorded',
             module='judgment_load.py')
    # VELDO-0136: each criterion's declared falsifier, and at least one different defect per named row.
    def hints(name, module, old, new, row, also=()):
        add(136, name, '68_veldo_0136_hints.py', module, old, new, [row], also=also)

    # AC1 (declared falsifier): a plain message, one with no reply reference, is sent nothing. The
    # decision is the intake pass's, after intake has seen the message (review of VELDO-0136).
    hints('plain-message-not-hinted', 'control_intake.py',
          "        if (record.get('outcome') != 'refused' or record.get('reason') not in ORDINARY\n",
          "        if (record.get('outcome') != 'refused' or record.get('reason') != 'unknown_presentation'  # defect\n",
          'hint/tells-owner-to-reply')
    # AC1: the hint names only the first waiting request, so with two waiting one goes unnamed.
    hints('hint-names-first-only', 'control_channel_presentation.py',
          "        for r in receipts:\n            line = 'Request:",
          "        for r in receipts[:1]:\n            line = 'Request:", 'hint/tells-owner-to-reply')
    # AC2 (declared falsifier): the plain message is recorded as the answer to the waiting request.
    hints('plain-message-recorded-as-answer', 'control_channel_attribution.py',
          "        reply = message.get('reply_to_message')\n        if not isinstance(reply, dict):\n",
          "        reply = message.get('reply_to_message')\n"
          "        waiting = self.presenter.waiting(known['principal'], fields['chat_id']) if not isinstance(reply, dict) else []\n"
          "        if waiting:  # defect: a message that replies to nothing answers the waiting request\n"
          "            part = waiting[0]['platform_parts'][-1]\n"
          "            reply = {'message_id': part['message_id'], 'chat': {'id': part['chat_id']}, 'date': part['date'],\n"
          "                     'text': part['text'], 'from': {'id': record['bot_id'], 'is_bot': True}}\n"
          "            message = dict(message, reply_to_message=reply)\n"
          "            fields = dict(fields, reply_to_message_id=part['message_id'], reply_chat_id=part['chat_id'],\n"
          "                          reply_date=part['date'])\n"
          "        if not isinstance(reply, dict):\n", 'hint/owner-only-never-an-answer')
    # AC2: the waiting set is every pending presentation, not the sender's own in his own chat, so a
    # member with nothing waiting is told another owner's requests.
    hints('hint-to-anyone-waiting', 'control_channel_presentation.py',
          " or receipt.get('owner') != principal\n"
          "                    or receipt.get('chat_id') != chat or receipt.get('enrolled_chat') != chat\n",
          "\n", 'hint/owner-only-never-an-answer')
    # AC2: the hint is kept as an answer record.
    hints('hint-kept-as-answer', 'control_channel_presentation.py', "HINT_KIND = 'presentation_hint'\n",
          "HINT_KIND = 'presentation_answer'\n", 'hint/owner-only-never-an-answer')
    # AC3 (declared falsifier): a hint on every message. The one-hint rule is held in three places (the
    # due filter, the expected version 0 of each mark, the transition's create-once), all removed.
    permissive = (("                         dict({hid: 0}, **{k: 0 for k in marks}), command_id=hid + ':intent')\n",
                   "                         dict({hid: 0}, **{k: (self._entity(k) or {}).get('version', 0) for k in marks}),\n"
                   "                         command_id=hid + ':intent')\n"),
                  ("            if (not isinstance(mark, str) or mark in changes or (before.get(mark) or {}).get('data') is not None\n",
                   "            if (not isinstance(mark, str) or mark in changes\n"))
    hints('hint-every-message', 'control_channel_presentation.py',
          "        due = [r for r in waiting if self._entity(hinted_id(r['request_id'], r['request_version'], principal)) is None]\n",
          "        due = list(waiting)\n", 'hint/once-per-pending-request', also=permissive)
    # AC3: when a new request is due, the hint names again the requests already hinted.
    hints('hint-renames-hinted', 'control_channel_presentation.py',
          "        text, named = self._hint_text(m.get('cause'), due, taken, lead)\n",
          "        text, named = self._hint_text(m.get('cause'), waiting if due else due, taken, lead)\n",
          'hint/once-per-pending-request', also=permissive)
    # Review of VELDO-0136: one decision per owner message, taken after intake has seen it.
    # New work is told it answers nothing, as if intake had not taken it.
    hints('new-work-told-answers-nothing', 'control_intake.py',
          "                self._hint(payload, 'proposed' if result['outcome'] == 'proposed' else None)\n",
          "                self._hint(payload, None)  # defect: new work is told it answers nothing\n",
          'hint/new-work-one-reply')
    # The finding itself: the Acquirer hints when it refuses, before intake has seen the message.
    hints('hint-before-intake', 'control_channel_attribution.py',
          "        # A message refused as NOT_A_REPLY is not hinted here: the VELDO-0126 intake pass, which sees\n",
          "        if refusal in NOT_A_REPLY and known['principal'] is not None:  # defect: hinted before intake\n"
          "            self.presenter.hint_owner(dict(cause=refusal, principal=known['principal'],\n"
          "                                           chat_id=fields.get('chat_id'), sender_id=fields.get('sender_id'),\n"
          "                                           message_id=fields.get('message_id'), evidence_id=eid,\n"
          "                                           update_id=record.get('update_id')))\n"
          "        # A message refused as NOT_A_REPLY is not hinted here: the VELDO-0126 intake pass, which sees\n",
          'hint/answer-without-reply-one-reply')
    # Intake's project question and the note go out as two replies.
    hints('question-and-note-apart', 'control_intake.py',
          "        hinted = self._hint(where.get('evidence_id'), 'inbox', lead=question['prompt'])\n",
          "        hinted = dict(self._hint(where.get('evidence_id'), 'proposed'), attempted=False)  # defect: two replies\n",
          'hint/two-projects-one-reply')
    # A clarification and a Reply to intake's own question are hinted as if intake had not taken them.
    hints('intake-replies-hinted', 'control_intake.py',
          "            if not result.get('repeated') and result.get('outcome') in ('proposed', 'refused'):\n",
          "            if not result.get('repeated') and result.get('outcome') in ('proposed', 'refused', 'clarification',\n"
          "                                                                         'resolved'):  # defect\n",
          'hint/intake-replies-not-hinted')

    # VELDO-0137: policy_check reads a VELDO-0050 digest-form spec revision. Each case against the one
    # suite 68 row it names.
    def policy(name, old, new, row):
        add(137, name, '68_veldo_0137_policy_revision.py', 'policy_check.py', old, new, ['policy/' + row])

    # AC1, declared: the digest form read as an integer revision again (every factory proof stale).
    policy('policy-digest-read-as-integer', '        if isinstance(pr, str) and pr.startswith("sha256:"):\n',
           '        if False:  # defect: a digest-form revision is read with int() and is always stale\n',
           'digest-revision-current')
    policy('policy-digest-bound-to-head', '    then = _spec_at(commit, sid)\n',
           '    then = _spec_at("HEAD", sid)  # defect: the binding is not read at the proof\'s own commit\n',
           'digest-revision-current')
    # AC2, declared: a digest naming no committed spec accepted.
    policy('policy-digest-binding-unchecked',
           '    if then is None or "sha256:" + hashlib.sha256(then[0]).hexdigest() != pr:\n',
           '    if then is None:  # defect: the digest is never compared with the committed spec\n',
           'digest-revision-stale')
    # Review finding: a spec with no readable front matter at the proof's commit read as an empty mapping.
    policy('policy-digest-no-front-matter-current',
           '        fm = _Y.front_matter(b.stdout.decode("utf-8"), names[0])\n',
           '        fm = _Y.front_matter(b.stdout.decode("utf-8"), names[0]) or {}  # defect: no front matter reads as empty\n',
           'digest-revision-stale')
    policy('policy-digest-revision-raise-ignored',
           '        return int(current.get("revision", 1)) > int(then[1].get("revision", 1))\n',
           '        return False  # defect: a raised declared revision leaves a digest proof current\n',
           'digest-revision-stale')
    # VELDO-0126: each criterion's declared falsifier and a second different defect per named row, each
    # against the one suite 68 row it names. Anchors are exact text in the intake module.
    def intake(name, old, new, row):
        add(126, name, '68_veldo_0126_intake.py', 'control_intake.py', old, new, ['intake/' + row])

    # AC1, declared: API messages are written into a separate work queue.
    intake('api-into-separate-queue', "            result = self._submit(command)\n",
           "            if source_kind == 'api_request':  # defect: API messages go to a separate work queue\n"
           "                with __import__('contextlib').suppress(Exception):\n"
           "                    self.store.execute(self.conn, dict(command_id='queue:' + command['source_id'],\n"
           "                        principal=self.journal_signer, operation='upsert_entity', parameters=dict(\n"
           "                        entity_id='api_queue:' + command['source_id'], kind='api_work_queue', data=command),\n"
           "                        expected_versions={'api_queue:' + command['source_id']: 0}, artifact_digests=[],\n"
           "                        nonce='queue:' + command['source_id']), self.journal_signer, self.sign, self.generation)\n"
           "                result = {'outcome': 'queued', 'command': command}\n"
           "            else:\n"
           "                result = self._submit(command)\n", 'common-command')
    intake('api-principal-from-edge', "                'principal': request['principal'], 'text': request['text'],",
           "                'principal': request['edge'], 'text': request['text'],", 'common-command')
    intake('unresolved-first-candidate-wins',
           "or (candidates[0] if len(candidates) == 1 else None)\n",
           "or candidates[0]  # defect: the first candidate project is taken as the owner's\n",
           'unresolved-project-asks')
    intake('question-not-sent', "            self._ask(result['question_id'], command)\n",
           "            pass  # defect: the question is never sent\n", 'unresolved-project-asks')
    # AC2, declared: every message must carry a Jira ticket id.
    intake('ticket-id-required',
           "    if type(text) is not str or not text.strip() or len(text) > TEXT_LIMIT:\n        return 'invalid_input:text'\n",
           "    if type(text) is not str or not text.strip() or len(text) > TEXT_LIMIT:\n        return 'invalid_input:text'\n"
           "    if not __import__('re').search(r'\\b[A-Z][A-Z0-9]+-[0-9]+\\b', text):  # defect: a ticket id is required\n"
           "        return 'invalid_input:ticket'\n", 'plain-objective')
    intake('text-trimmed', "        principal, text = command['principal'], command['text']\n",
           "        principal, text = command['principal'], command['text'].strip()  # defect: the text is trimmed\n",
           'plain-objective')
    intake('follow-up-as-new-objective', "        clarifies = command['clarifies']\n",
           "        clarifies = None  # defect: a follow-up is taken as a new objective\n", 'follow-up-clarification')
    intake('clarification-replaces-objective-text',
           "'principal': principal, 'text': data['text'],\n",
           "'principal': principal, 'text': text,  # defect: the follow-up replaces the objective\n",
           'follow-up-clarification')
    intake('api-signature-unchecked', "        if not self._edge_verifies(request, signature):\n",
           "        if False:  # defect: the API edge's signature is not checked\n", 'authenticated-sources-only')
    intake('unsupported-source-rides-api', "        adapter = self._adapters.get(source_kind) if",
           "        adapter = self._adapters.get(source_kind, self._api) if", 'authenticated-sources-only')
    # AC3, declared: an executable unit is created directly from an accepted message.
    intake('accepted-message-creates-unit', "        changes[key] = {'kind': SOURCE_KIND, 'data': source}\n",
           "        changes['unit:' + key] = {'kind': 'execution_unit', 'data': {'state': 'READY',  # defect\n"
           "                                                                     'proposal': result['proposal_id']}}\n"
           "        changes[key] = {'kind': SOURCE_KIND, 'data': source}\n", 'no-admission')
    intake('accepted-message-prioritized', "'state': 'PROPOSED' if project else",
           "'state': 'PRIORITIZED' if project else", 'no-admission')
    intake('changed-content-overwrites', "            raise Refused('identity_conflict', key)\n",
           "            pass  # defect: changed content overwrites the recorded request\n", 'same-request-same-proposal')
    intake('repeat-refused-as-conflict', "                raise _Repeated(existing['data'])\n",
           "                raise Refused('identity_conflict', key)  # defect: a repeat is refused\n",
           'same-request-same-proposal')
    # Review of 8607f50: a follow-up to an inbox proposal already resolved lands on the live objective.
    intake('follow-up-lands-on-retired-inbox',
           "            if target['data'].get('state') != 'RESOLVED':\n",
           "            if True:  # defect: a resolved inbox proposal is not followed to its objective\n",
           'follow-up-clarification')
    intake('follow-up-to-resolved-refused', "            pid = onward\n",
           "            raise Refused('stale_version:clarifies', str(pid))  # defect: a follow-up to a resolved inbox is refused\n",
           'follow-up-clarification')
    # Authority at both ends: a Telegram sender must have been a member at the message's platform date.
    intake('member-checked-only-when-processed',
           "            why = self._member_when_sent(principal, command['provenance'].get('date'))\n",
           "            why = None  # defect: membership is checked only when the message is processed\n",
           'authenticated-sources-only')
    intake('member-when-sent-read-at-processing-time',
           "self._member_when_sent(principal, command['provenance'].get('date'))",
           "self._member_when_sent(principal, self.clock())", 'authenticated-sources-only')

    # VELDO-0058: each criterion's declared falsifier and a further defect, each against the one suite 69
    # row it names. verify.sh is the production gate script (scripts/, case field `dir`); the rest are
    # exact text in the .veldo modules suite 69 installs.
    def gate_output(name, module, old, new, row, also=(), directory=None):
        add(58, name, '69_veldo_0058_gate_output.py', module, old, new, ['gate-output/' + row], also)
        if directory:
            result[-1]['dir'] = directory

    # AC1, declared: the reconciliation still writes the candidate's own .veldo/events.jsonl while the
    # stamp goes to the sink.
    gate_output('gate-output-reconcile-writes-candidate', 'verify.sh',
                '  set -- --repo-root "$(pwd -P)" --log "$VELDO_OUT/events.jsonl"\n',
                '  set -- --repo-root "$(pwd -P)"  # defect: the reconciliation appends to the candidate\'s own log\n',
                'review-write', directory='scripts')
    gate_output('gate-output-stamp-written-to-candidate', 'verify.sh',
                '     && mv -f "$VELDO_OUT/.stamp.$$" "$VELDO_OUT/last_verify" 2>/dev/null \\\n',
                '     && mv -f "$VELDO_OUT/.stamp.$$" .veldo/last_verify 2>/dev/null \\\n',
                'review-write', directory='scripts')
    # AC1: a sink that refuses the final write, and a sink inside the candidate.
    gate_output('gate-output-sink-failure-still-green', 'verify.sh',
                '    echo "== gate output: NOT WRITTEN - the sink refused the stamp or the gate event; this run is not trusted success"\n'
                '    FAIL=1\n',
                '    echo "== gate output: NOT WRITTEN - the sink refused the stamp or the gate event; this run is not trusted success"\n'
                '    : # defect: a sink that refused the write is still trusted success\n',
                'sink-refusals', directory='scripts')
    gate_output('gate-output-sink-inside-candidate-accepted', 'verify.sh',
                '    case "$_veldo_sink/" in "$_veldo_root"/*) VELDO_REFUSE="the sink resolves inside the candidate" ;; esac\n',
                '    : # defect: a sink that resolves inside the candidate is accepted\n',
                'sink-refusals', directory='scripts')
    # AC2, declared: no post-run tree equality at acceptance, so a tracked file written after the final
    # check is accepted.
    gate_output('gate-output-acceptance-skips-tree-equality', 'control_verification.py',
                '    if now["head"] != commit or now["digest"] != (observation.get("candidate") or {}).get("state"):\n',
                '    if False:  # defect: no post-run tree equality at acceptance\n',
                'post-run-mutation')
    gate_output('gate-output-run-equality-not-judged', 'control_verification.py',
                '    if post.get("equal") is not True or post.get("state") != candidate.get("state"):\n',
                '    if False:  # defect: a candidate changed during the run is judged green\n',
                'post-run-mutation')
    gate_output('gate-output-observation-content-not-judged', 'control_verification.py',
                '    problems = judge(observation)\n    if observation.get("commit") != commit:\n',
                '    problems = []  # defect: the observation\'s content is not judged again at acceptance\n'
                '    if observation.get("commit") != commit:\n',
                'post-run-mutation')
    # AC3, declared: finalize launches the candidate's policy_check.py, a success stub.
    gate_output('gate-output-candidate-policy-launched', 'lander.py',
                '                returncode, policy_out = verification_organ().run_policy(self._installed(c), c["workspace"],\n'
                '                                                                         c["watermark"])\n',
                '                pc = subprocess.run([sys.executable, "-B", *POLICY_COMMAND], cwd=c["workspace"], capture_output=True,\n'
                '                                    text=True, stdin=subprocess.DEVNULL)  # defect: the candidate\'s policy decides\n'
                '                returncode, policy_out = pc.returncode, pc.stdout.strip()\n',
                'installed-policy')
    gate_output('gate-output-policy-module-from-candidate', 'control_verification.py',
                '    policy = root / POLICY_PATH\n',
                '    policy = Path(candidate) / POLICY_PATH  # defect: the candidate\'s policy module is run\n',
                'installed-policy',
                also=[('    if inside(policy, candidate):\n        return None, "missing_authority:policy/in_candidate"\n',
                       '    if False:\n        return None, "missing_authority:policy/in_candidate"\n'),
                      # The candidate's module brings the candidate's policy.yaml beside it; the source
                      # refusal would stop that run before the candidate's stub is asked.
                      ('def _policy_source_refusal(policy, candidate):\n',
                       'def _policy_source_refusal(policy, candidate):\n    return None  # defect: any policy source\n')])
    # AC3, the policy source: the installed policy's protected list is read from the candidate's own
    # policy.yaml, so a candidate that empties protected_paths lands a protected change unapproved.
    gate_output('gate-output-policy-source-not-set', 'control_verification.py',
                '    module.POLICY = Path(policy).parent / POLICY_SOURCE\n',
                '    pass  # defect: the policy source is left unset, so the candidate\'s policy.yaml decides\n',
                'installed-policy-list')
    gate_output('gate-output-protected-list-from-subject-root', 'policy_check.py',
                '    policy = _Y.read(policy_source())\n',
                '    policy = _Y.read(ROOT / ".veldo" / "policy.yaml")  # defect: the subject root\'s policy.yaml decides\n',
                'installed-policy-list')
    # AC3, the range base: the installed policy's push range is computed from the candidate's own
    # origin refs again, which its code can move to HEAD during the gate, so a protected change lands.
    gate_output('gate-output-range-base-ignored', 'policy_check.py',
                '    if BASE is not None:\n        return [str(BASE) + "..HEAD"]\n',
                '    if False:  # defect: the range is read from the subject\'s refs even when a base is set\n'
                '        return [str(BASE) + "..HEAD"]\n',
                'range-base-from-lander')
    gate_output('gate-output-range-base-not-set', 'control_verification.py',
                '    module.BASE = base\n',
                '    pass  # defect: the base is checked but never handed to the policy, so the refs decide\n',
                'range-base-from-lander')
    gate_output('gate-output-range-base-from-workspace-refs', 'lander.py',
                '                                                                         c["watermark"])\n',
                '                                                                         self._commit_of(c["workspace"], POLICY_BASE_REF % self.trunk,\n'
                '                                                                                         "missing_evidence:watermark"))'
                '  # defect: the base is read from the workspace\'s refs\n',
                'range-base-from-lander')
    gate_output('gate-output-range-base-not-validated', 'control_verification.py',
                'def _policy_base_refusal(base, candidate):\n',
                'def _policy_base_refusal(base, candidate):\n    return None  # defect: any base is accepted\n',
                'range-base-from-lander')
    # AC2, the refs: the candidate's state leaves out its refs, so a ref moved during or after the gate
    # is not noticed; or leaves out a symbolic ref's target, so a retargeted origin/HEAD is not.
    gate_output('gate-output-state-without-refs', 'control_verification.py',
                '    refs = _refs(root) if bind_refs else None\n',
                '    refs = None  # defect: the refs are not part of the state\n',
                'refs-bound')
    gate_output('gate-output-state-without-symref-targets', 'control_verification.py',
                '"--format=%(refname)%00%(objectname)%00%(symref)"',
                '"--format=%(refname)%00%(objectname)"',
                'refs-bound')
    # AC2, the ref binding is the caller's explicit input: LiveLoop binds the refs of the caller's own
    # repository, so a sibling worktree's commit during its gate fails it; GitLandOps does not bind its
    # workspace's refs, so a candidate that moves them during the gate is not refused.
    gate_output('gate-output-live-loop-binds-refs', 'executor.py',
                '                                                       bind_refs=False)\n',
                '                                                       bind_refs=True)  # defect: the caller\'s refs are bound\n',
                'live-loop-siblings')
    gate_output('gate-output-land-does-not-bind-refs', 'lander.py',
                'Path(c["observation_dir"]) / "gate",\n                                                  bind_refs=True)\n',
                'Path(c["observation_dir"]) / "gate",\n                                                  bind_refs=False)'
                '  # defect: the workspace\'s refs are not bound\n',
                'refs-bound',
                also=[('c["workspace"], c["commit"],\n                                               bind_refs=True)\n',
                       'c["workspace"], c["commit"],\n                                               bind_refs=False)\n')])
    # VELDO-0135: enrolled work offered from its floor record. Each criterion's declared falsifier and
    # further defects, each against the one suite 67 row it names; anchors are exact text in the
    # frontier and work loop the suite installs.
    def offers(name, old, new, row, module='frontier.py', also=()):
        add(135, name, '67_veldo_0135_offers.py', module, old, new, ['offers/' + row], also)

    # AC1, declared: every lane reads the lane status from the spec file.
    offers('offers-status-line-read', '    lanes.update({sid: e["lane"] for sid, e in entries.items()})\n',
           '    pass  # defect: every lane reads the spec file\'s status line\n', 'floor-station')
    offers('offers-review-line-without-record',
           '        if word == "review":\n            # The status line names a station no floor record backs.\n',
           '        if False:  # defect: a review status line with no floor record behind it is offered\n',
           'floor-station')
    offers('offers-returned-not-rebuilt', '        if to == "ready":\n',
           '        if to == "never":  # defect: a unit returned to ready is not offered to build\n', 'floor-station')
    offers('offers-unreadable-record-offered', '    if record is None and version:\n',
           '    if False:  # defect: a row that is not a floor record reads as no record\n', 'floor-station')
    # AC2, declared: a handed-off unit is claimable.
    offers('offers-handoff-claimable', '        return _held(entry, "handoff")\n',
           '        return dict(entry, station="build", lane="ready")  # defect: a handed-off unit is claimable\n',
           'no-reclaim')
    offers('offers-recheck-reads-status-line',
           '        if entry is not None:\n            if entry["station"] == unit.get("kind"):\n',
           '        if entry is not None and False:  # defect: the recheck reads the status line\n'
           '            if entry["station"] == unit.get("kind"):\n', 'no-reclaim', module='work.py')
    offers('offers-waiting-finding-offered',
           '        if not codes or any(c.startswith("awaiting_reviews") for c in codes):\n',
           '        if True:  # defect: a unit waiting on an open finding is offered for review\n', 'no-reclaim')
    offers('offers-unit-claim-stop-stops-the-read',
           '                if unit_stop.reason not in CLAIM_STOPS:\n                    raise\n',
           '                raise  # defect: one unadmitted unit\'s claim stop stops the whole frontier read\n',
           'no-reclaim')
    # AC3, declared: an enrolled unit is offered as build again after its build is accepted.
    offers('offers-build-again-after-acceptance', '    if state == "review":\n',
           '    if state == "review":\n'
           '        return dict(entry, station="build", lane="ready")  # defect: an accepted build is offered again\n',
           'end-to-end')
    offers('offers-recheck-refuses-review', '            if entry["station"] == unit.get("kind"):\n',
           '            if entry["station"] == "build":  # defect: a review offer never survives its recheck\n',
           'end-to-end', module='work.py')
    # The finding path (review of e5b4dad): with the review policy met and the last finding resolved,
    # the review station hands off without a reviewer; a review is assigned and launched only when the
    # handoff rule does not pass. And a failed review bars only its station, not the unit's rebuild.
    handoff_first = ('        if not floor.handoff_refusals(sid):\n'
                     '            # The review policy is already met and nothing blocks the handoff (the owner resolved the\n'
                     '            # last open finding): hand off now. A review the policy does not require is never assigned.\n'
                     '            return self._hand_off(floor, unit, decision, None, None)\n')
    assignment_refused = '            return self._floor_refused("review", sid, error, "review_assignment", **refused)\n'
    offers('offers-review-assigned-before-handoff-rule', handoff_first, '', 'finding-path', module='dispatch.py',
           also=[(assignment_refused, assignment_refused
                  + '        # defect: the review is assigned before the handoff rule is checked\n' + handoff_first)])
    offers('offers-reviewer-launched-before-handoff',
           '            return self._hand_off(floor, unit, decision, None, None)\n',
           '            with self._launch("review", unit, context, decision) as handle:  # defect: a reviewer still launches\n'
           '                self._reviewer.review(dict(self._resolve(sid), status="review"), unit, calls=handle)\n'
           '            return self._hand_off(floor, unit, decision, None, None)\n', 'finding-path', module='dispatch.py')
    offers('offers-failed-review-bars-rebuild', '            if (u["spec"], u["kind"]) in self._failed:\n',
           '            if any(spec == u["spec"] for spec, _ in self._failed):  # defect: a failed station bars the unit\n',
           'end-to-end', module='work.py')
    # Observability: the record version, the reason's class and the dispatch join.
    offers('offers-observed-without-version',
           '        event = dict(base, operation="floor_offer", unit=sid, record=e["record"], version=e["version"],\n',
           '        event = dict(base, operation="floor_offer", unit=sid, record=e["record"], version=0,  # defect\n',
           'observations')
    offers('offers-withheld-reason-unclassed', '    if reason.split(":", 1)[0] in FLOOR_HOLDS:\n',
           '    if True:  # defect: every withheld reason is classed as a hold\n', 'observations')
    offers('offers-dispatch-not-joined', '        if unit.get("floor"):\n            self._observe_dispatch(unit, result)\n',
           '        if False:  # defect: no dispatch is joined to the offer it came from\n'
           '            self._observe_dispatch(unit, result)\n', 'observations', module='work.py')
    # VELDO-0134: the architecture record's one writer. Each declared falsifier, a second and different
    # defect of its row, and more where one row covers several refusals.
    def acceptance(name, module, old, new, rows, also=()):
        add(134, name, '68_veldo_0134_acceptance.py', module, old, new, ['acceptance/' + r for r in rows], also)

    AR134 = 'control_architecture.py'
    acceptance('architecture-agent-run-signs', AR134,
               "        if entry.get('principal_type') != SIGNER_TYPE:\n",
               "        if entry.get('principal_type') not in (SIGNER_TYPE, 'agent_run'):  # defect: an agent_run member signs\n",
               ['signers'])
    acceptance('architecture-any-role-signs', AR134,
               "        if SIGNER_ROLE not in (entry.get('roles') or []):\n",
               "        if not (entry.get('roles') or []):  # defect: any role accepts\n", ['signers'])
    acceptance('architecture-scope-unchecked', AR134,
               "        if not self.membership.scope_covers(entry.get('scope'), self.ids['repository_uuid']):\n",
               "        if False:  # defect: the membership scope is never checked\n", ['signers'])
    acceptance('architecture-signature-unverified', AR134,
               "        if not verified:\n            raise Refused('not_authorized:signature'",
               "        if False:  # defect: the verdict is ignored\n            raise Refused('not_authorized:signature'",
               ['signature'])
    acceptance('architecture-revoked-key-verifies', AR134,
               "        key = self.AC.active_key(state['keyring'], principal, now)\n",
               "        key = next((k for k in state['keyring'] if k.get('principal') == principal), None)  # defect: revocation ignored\n",
               ['signature'])
    acceptance('architecture-digest-unchecked', AR134,
               "        if entry is not None and entry[2] is not None and raw_digest(entry[2]) != command['digest']:\n",
               "        if False:  # defect: the stated digest is never compared with the bytes\n", ['evidence'],
               also=[("        if parsed != digest:\n", "        if False:  # defect\n")])
    acceptance('architecture-missing-commit-as-absent', AR134,
               "        raise Refused('missing_evidence:commit', 'no commit %s in the bound repository' % commit)\n",
               "        return None  # defect: a missing commit reads as a commit with no contract\n", ['evidence'])
    acceptance('architecture-invalid-structure-accepted', AR134,
               "        if load.refused:\n",
               "        if load.refused and load.kind != 'invalid_structure':  # defect: the validator's verdict is ignored\n",
               ['contract-kinds'])
    acceptance('architecture-writer-policy-decides', AR134,
               "                load, parsed = validate.entry_contract(str(root), True, arch=validator)\n",
               "                load, parsed = validate.entry_contract(str(root), None, arch=validator)  # defect: absence is optional\n",
               ['contract-kinds'])
    acceptance('architecture-nonce-not-consumed', AR134,
               "        if self.conn.execute('SELECT 1 FROM nonces WHERE nonce=?', (command['nonce'],)).fetchone():\n",
               "        if False:  # defect: the signed nonce is not the one consumed\n", ['replay-and-coordinates'],
               also=[("                      nonce=command['nonce'])\n",
                      "                      nonce=command['nonce'] + ':' + command['command_id'])\n")])
    acceptance('architecture-coordinates-unchecked', AR134,
               "        if any(command[k] != v for k, v in self.ids.items()):\n",
               "        if False:  # defect: the command's coordinates are not compared\n", ['replay-and-coordinates'])
    acceptance('architecture-first-nonce-rewritten', AR134,
               "                      nonce=command['nonce'])\n",
               "                      nonce='consumed-' + command['nonce'])  # defect: another nonce is consumed\n", ['first'])
    acceptance('architecture-gate-policy-decides', 'control_eligibility.py',
               "            load, parsed = snapshot.contract(self.workspace, True if accepted else None)\n",
               "            load, parsed = snapshot.contract(self.workspace, None)  # defect: the policy decides under a record\n",
               ['first', 'worker-inputs'])
    acceptance('architecture-reader-open-mapping', AR134,
               "    problems.extend('record carries unknown field %s' % f for f in extra)\n", '', ['schema-oracle'])
    acceptance('architecture-reader-uppercase-hex', AR134,
               "_DIGEST = re.compile(r'sha256:[0-9a-f]{64}\\Z')\n",
               "_DIGEST = re.compile(r'sha256:[0-9a-fA-F]{64}\\Z')  # defect: uppercase hex is a digest\n", ['schema-oracle'])
    acceptance('architecture-reader-state-and-prefix-only', 'control_eligibility.py',
               "        if accepted and AR.record_problems(item['id'], (item.get('value') or {}).get('kind'), record):\n",
               "        if accepted and (not isinstance(record, dict) or record.get('state') != 'accepted'\n"
               "                         or not str(record.get('digest')).startswith('sha256:')):  # defect: the reader before the schema\n",
               ['schema-oracle'])
    acceptance('architecture-writer-accepted-by-command', AR134,
               "source=source, accepted_by=params['principal'],\n                        command_id",
               "source=source, accepted_by=params['command_id'],  # defect\n                        command_id",
               ['writer-schema'])
    acceptance('architecture-writer-superseded-rewritten', AR134,
               "superseded=list(prior['superseded']) + [_entry_of(prior)])",
               "superseded=list(prior['superseded']) + [dict(_entry_of(prior), command_id=params['command_id'])])",
               ['writer-schema'])
    RAW = "    return 'sha256:' + hashlib.sha256(body).hexdigest()\n"
    for name, hashed, row in [
            ('architecture-digest-normalizes-line-endings', "body.replace(b'\\r\\n', b'\\n')", 'raw-digest-crlf'),
            ('architecture-digest-universal-newlines',
             "__import__('io').TextIOWrapper(__import__('io').BytesIO(body), encoding='utf-8', errors='surrogateescape', "
             "newline=None).read().encode('utf-8', 'surrogateescape')", 'raw-digest-crlf'),
            ('architecture-digest-adds-final-newline', "body if body.endswith(b'\\n') else body + b'\\n'",
             'raw-digest-no-final-newline'),
            ('architecture-digest-one-final-newline', "body.rstrip(b'\\n') + b'\\n'", 'raw-digest-no-final-newline'),
            ('architecture-digest-strips-bom', "body[3:] if body.startswith(b'\\xef\\xbb\\xbf') else body", 'raw-digest-bom'),
            ('architecture-digest-decodes-utf8-sig',
             "body.decode('utf-8-sig', 'surrogateescape').encode('utf-8', 'surrogateescape')", 'raw-digest-bom')]:
        acceptance(name, AR134, RAW, "    return 'sha256:' + hashlib.sha256(%s).hexdigest()  # defect\n" % hashed, [row])
    acceptance('architecture-replacement-in-place', AR134,
               "            data = dict(prior, contract_version=version + 1, digest=params['digest'], source=source, "
               "accepted_by=params['principal'], command_id=params['command_id'], superseded=list(prior['superseded']) "
               "+ [_entry_of(prior)])\n",
               "            data = dict(prior, digest=params['digest'], source=source, accepted_by=params['principal'], "
               "command_id=params['command_id'])  # defect: the current entry is overwritten in place\n",
               ['version-history'])
    acceptance('architecture-superseded-entries-edited', AR134,
               "superseded=list(prior['superseded']) + [_entry_of(prior)])",
               "superseded=[dict(e, accepted_by=params['principal'] + '-edited') for e in prior['superseded']] "
               "+ [_entry_of(prior)])  # defect: earlier entries are rewritten",
               ['version-history'])
    acceptance('architecture-current-digest-reaccepted', AR134,
               "        if current is not None and current['data']['digest'] == command['digest']:\n",
               "        if False:  # defect: the current bytes are accepted again\n", ['replacement-refusals'])
    acceptance('architecture-changed-retry-replayed', AR134,
               "            if signed not in json.loads(prior[0]):\n",
               "            if False:  # defect: a changed retry is answered as the committed command\n",
               ['replacement-refusals'])
    acceptance('architecture-superseded-bytes-accepted', 'control_eligibility.py',
               "        elif accepted and parsed != accepted['digest']:\n",
               "        elif accepted and parsed != accepted['digest'] and parsed not in [\n"
               "                e.get('digest') for e in record.get('superseded', [])]:  # defect: replaced bytes pass\n",
               ['previous-bytes'])
    acceptance('architecture-first-version-accepted', 'control_eligibility.py',
               "                        'digest': record.get('digest') if isinstance(record, dict) else None}\n",
               "                        'digest': (record.get('superseded') or [record])[0].get('digest')\n"
               "                        if isinstance(record, dict) else None}  # defect: the first version stays accepted\n",
               ['previous-bytes'])
    STORE134 = 'control_store.py'
    WRITER = '    return operation == ARCHITECTURE_OPERATION\n'
    acceptance('architecture-generic-upsert-writes', STORE134, WRITER,
               '    return operation in (ARCHITECTURE_OPERATION, "upsert_entity")  # defect: the generic upsert writes it\n',
               ['generic-write'])
    acceptance('architecture-generic-retire-writes', STORE134, WRITER,
               '    return operation in (ARCHITECTURE_OPERATION, "retire_entity")  # defect: the generic retire writes it\n',
               ['generic-write'])
    acceptance('architecture-kind-unowned', STORE134,
               '    return (isinstance(entity_id, str) and entity_id.startswith(ARCHITECTURE_PREFIX)) or ARCHITECTURE_KIND in kinds\n',
               '    return isinstance(entity_id, str) and entity_id.startswith(ARCHITECTURE_PREFIX)  # defect: the kind is unowned\n',
               ['generic-write'])
    acceptance('architecture-later-operation-writes', STORE134,
               '            if architecture_entity(eid, kinds) and not architecture_writer(command["operation"]):\n',
               '            if False:  # defect: only a named write parameter is checked\n', ['generic-write'])
    acceptance('architecture-repository-from-environment', AR134,
               "        repo = self.store.bound_repository(self.conn, self.ids['domain_uuid'], self.ids['repository_uuid'])\n",
               "        repo = __import__('os').environ.get('VELDO_ARCHITECTURE_REPOSITORY') or self.store.bound_repository(\n"
               "            self.conn, self.ids['domain_uuid'], self.ids['repository_uuid'])  # defect: the environment names it\n",
               ['worker-inputs'])
    acceptance('architecture-git-inherits-environment', AR134,
               "        return _git_process.run(['git', '-C', str(repo)] + list(args), capture_output=True, timeout=60)\n",
               "        return subprocess.run(['git', '-C', str(repo)] + list(args), capture_output=True, timeout=60)  # defect\n",
               ['worker-inputs'])
    # VELDO-0073: each criterion's declared falsifier first, then the threat model's other shapes.
    def activation(name, module, old, new, row, also=()):
        add(73, name, '70_veldo_0073_activation.py', module, old, new, [row], also)

    activation('activation-not-scaffolded', 'init_scaffold.py', '    ".veldo/control_channel_activation.py",\n', '',
               'install/assets')
    # AC1 (declared falsifier): the doorbell sends because its token resolves.
    activation('doorbell-token-resolves-sends', 'request_doorbell.py',
               '        with projection.gated_open(self._activation, self.ORIGIN, req, 30, "sendMessage", self._chat_id) as resp:\n',
               '        with urllib.request.urlopen(req, timeout=30) as resp:  # defect: a resolving token sends\n',
               'activation/no-implicit')
    activation('ungated-edge-reaches-any-origin', 'control_channel_projection.py',
               "        if not is_stand_in(base_url):\n            raise EdgeRefused('not_activated'",
               "        if False:  # defect: an edge without a gate reaches any origin\n            raise EdgeRefused('not_activated'",
               'activation/no-implicit')
    activation('presentation-edge-bypasses-gate', 'control_channel_presentation.py',
               "            with self.P.gated_open(self.activation, self.base_url, request, self.timeout, 'sendMessage', chat) as response:\n",
               "            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # defect: ungated\n",
               'entry-points/enumerated')
    activation('entry-point-unlisted', 'control_channel_activation.py',
               ",\n                ('request_doorbell.py', 'TelegramSink.send', 'sendMessage'))\n", ")\n",
               'entry-points/enumerated')
    activation('steward-authorizes-owner-edge', 'control_channel_activation.py',
               "        if signer != params['owner']:\n", "        if False:  # defect: anyone with the role authorizes\n",
               'activation/explicit-bound-operates')
    activation('send-to-any-chat', 'control_channel_activation.py',
               "        if operation in SEND and chat != record.get('enrolled_chat'):\n",
               "        if False:  # defect: a send goes to any chat\n", 'activation/explicit-bound-operates')
    activation('production-acquisition-ungated', 'control_channel_ingress.py',
               "EV.TelegramAcquisitionEdge(P, origin, token, activation=gate)", "EV.TelegramAcquisitionEdge(P, origin, token)",
               'activation/explicit-bound-operates')
    # AC2 (declared falsifier): fixture-only evidence accepted as the platform's.
    activation('fixture-evidence-accepted', 'control_channel_activation.py',
               "    if not exchanges or not all(proven_exchange(x, origin) for x in exchanges):\n",
               "    if not exchanges:  # defect: any recorded exchange is evidence\n", 'qualification/real-platform-proof')
    activation('tls-host-unchecked', 'control_channel_activation.py',
               "    return (isinstance(tls, dict) and tls.get('verified') is True and tls.get('host') == TELEGRAM_HOST\n"
               "            and _names_cover(tls.get('dns_names'), TELEGRAM_HOST)\n",
               "    return (isinstance(tls, dict) and tls.get('verified') is True  # defect: any host's certificate\n",
               'qualification/real-platform-proof')
    activation('trust-store-from-environment', 'control_channel_activation.py',
               "    paths = ssl.get_default_verify_paths()\n",
               "    return ssl.create_default_context()  # defect: the environment names the trust store\n"
               "    paths = ssl.get_default_verify_paths()\n", 'qualification/real-platform-proof')
    activation('answer-not-the-platform-bytes', 'control_channel_activation.py',
               "              and x.get('response_digest') == answer.get('response_digest')\n", '',
               'qualification/real-platform-proof')
    activation('host-trust-optional', 'control_channel_ingress.py',
               "    if trust is None:\n        raise Refused('missing_authority', 'this host has installed no trust')\n", '',
               'settlement/production-construction')
    activation('decision-key-unverified', 'control_channel_ingress.py',
               "    if not settlement_trust.verify(probe, sign(probe), principal):\n", "    if False:  # defect: any key signs\n",
               'settlement/production-construction')
    # AC3 (declared falsifier): the notification payload is taken as the answer.
    activation('notification-settles', 'control_channel_ingress.py',
               "        acquired = []\n        for result in self.acquirer.acquire():\n",
               "        acquired = []\n"
               "        if isinstance(notification, dict) and type(notification.get('update_id')) is int:  # defect\n"
               "            self.acquirer._keep(self.acquirer.edge.get_me()['id'], notification, notification_digest(notification))\n"
               "        for result in self.acquirer.acquire():\n",
               'notification/wakes-only')
    # AC4 (declared falsifier): the explicit stopped record is ignored.
    activation('stop-ignored', 'control_channel_activation.py',
               "        if record.get('state') == 'stopped':\n"
               "            self._refuse(operation, 'edge_stopped', 'the edge was stopped by an explicit record')\n"
               "        if record.get('state') not in ('qualifying', 'active'):\n",
               "        if record.get('state') not in ('qualifying', 'active', 'stopped'):  # defect: stop ignored\n",
               'stop/halts-edge')
    activation('bindings-not-compared', 'control_channel_activation.py',
               "        for field in BOUND:\n            if current[field] != record.get(field):\n",
               "        for field in ():  # defect: bound versions never compared\n            if current[field] != record.get(field):\n",
               'stale/key-and-configuration')
    activation('origin-unbound', 'control_channel_activation.py',
               "        if not isinstance(origin, str) or origin.rstrip('/') != record.get('origin'):\n",
               "        if not isinstance(origin, str):  # defect: any origin\n", 'stale/key-and-configuration')
    activation('bot-unbound', 'control_channel_attribution.py', "        self.P.gated_bot(self.activation, result['id'])\n", '',
               'stale/key-and-configuration')
    # Review 1, B1: a listener at the configured origin redirects the exchange, token and all, elsewhere.
    activation('redirect-followed', 'control_channel_projection.py',
               '    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect(), *handlers)\n',
               '    return urllib.request.build_opener(urllib.request.ProxyHandler({}), *handlers)  # defect: redirects followed\n',
               'activation/no-redirect')
    activation('ungated-edge-default-opener', 'control_channel_projection.py',
               '        return bot_opener().open(request, timeout=timeout)\n',
               '        return urllib.request.urlopen(request, timeout=timeout)  # defect: the default opener\n',
               'activation/no-redirect')
    activation('stand-in-prefix-match', 'control_channel_projection.py',
               "    return url[len(STAND_IN_ORIGIN):].rstrip('/').isdigit()\n",
               "    return True  # defect: any text after the loopback prefix is a stand-in\n",
               'activation/no-redirect')
    activation('https-origin-unparsed', 'control_channel_projection.py',
               "    return bool(host) and all(c.isalnum() or c in '.-' for c in host)\n",
               "    return True  # defect: any https text is a Bot API origin\n",
               'activation/no-redirect')
    activation('gate-opener-own-build', 'control_channel_activation.py',
               '    return P.bot_opener(Handler())\n',
               '    return urllib.request.build_opener(urllib.request.ProxyHandler({}), Handler())  # defect: redirects followed\n',
               'activation/no-redirect')
    # VELDO-0130 phase 1: the authenticated API. Each criterion's declared falsifier (AC1: a decision
    # authorized by the body actor_id; AC3: a second settlement for the UI answer after Telegram settles),
    # and teeth for every row: the passkey checks, enrollment, sessions, forgery, the edge's signer purpose,
    # the authority's recheck, intake, settlement and the loopback transport.
    def api(name, module, old, new, rows, also=()):
        add(130, name, '71_veldo_0130_api.py', module, old, new, rows, also)

    API130, WA130, CR130 = 'control_api.py', 'control_api_webauthn.py', 'control_api_credentials.py'
    SG130, AU130, AS130 = 'control_api_signer.py', 'control_api_authority.py', 'control_api_assertion.py'
    api('body-actor-authorizes', API130,
        "    if any(f in body for f in ACTOR_FIELDS):\n        return 'invalid_input:actor_field'\n", '',
        ['routes/body-actor-refused'],
        also=[("    if set(body) - set(route.required) - set(route.optional) or",
               "    if set(body) - set(route.required) - set(route.optional) - set(ACTOR_FIELDS) or"),
              ("                         principal=session['principal'], credential_id=session['credential_id'],",
               "                         principal=body.get('actor_id') or session['principal'],"
               " credential_id=session['credential_id'],")])
    api('unknown-field-ignored', API130,
        "    if set(body) - set(route.required) - set(route.optional) or set(route.required) - set(body):",
        "    if set(route.required) - set(body):  # defect: unknown fields are ignored", ['routes/body-actor-refused'])
    api('domain-unchecked', API130, "        if 'domain' in params and params['domain'] != self.domain:",
        "        if False:  # defect: any domain in the path is served", ['routes/every-family'])
    api('expiry-unchecked', API130,
        "            if now - session['seen'] > IDLE_SECONDS or now - session['created'] > ABSOLUTE_SECONDS:",
        "            if False:  # defect: sessions never expire", ['session/cookie-and-expiry', 'routes/every-family'])
    api('absolute-lifetime-unchecked', API130,
        "            if now - session['seen'] > IDLE_SECONDS or now - session['created'] > ABSOLUTE_SECONDS:",
        "            if now - session['seen'] > IDLE_SECONDS:  # defect: no absolute lifetime", ['session/cookie-and-expiry'])
    api('session-not-rechecked', API130,
        "        why = self._credential_problem(session['credential_id'], session['principal'])[1]",
        "        why = None  # defect: the credential and member are not read again", ['session/revocation-ends'])
    api('follow-ignores-revocation', API130,
        "            if change.get('kind') == CR.KIND and data.get('revoked_at') is not None:",
        "            if False:  # defect: a revoked credential in the journal ends nothing", ['session/revocation-ends'])
    api('follow-ignores-membership', API130,
        "            elif change.get('kind') == 'membership' and data.get('revoked_at') is not None:",
        "            elif False:  # defect: a revoked membership in the journal ends nothing", ['session/revocation-ends'])
    api('token-unchecked', API130, "            if write and not hmac.compare_digest(",
        "            if False and not hmac.compare_digest(", ['session/forgery-refused'])
    api('origin-unchecked', API130, "            if headers.get('Origin') != self.origin:",
        "            if False:  # defect: any Origin writes", ['session/forgery-refused'])
    api('fetch-site-unchecked', API130, "            if headers.get('Sec-Fetch-Site') not in (None, 'same-origin'):",
        "            if False:  # defect: cross-site fetches write", ['session/forgery-refused'])
    api('content-type-unchecked', API130,
        "            if (headers.get('Content-Type') or '').split(';')[0].strip().lower() != 'application/json':",
        "            if False:  # defect: a form post writes", ['session/forgery-refused'])
    api('host-unchecked', API130, "        if (headers.get('Host') or '') != self.host:",
        "        if False:  # defect: any Host is served", ['session/forgery-refused', 'transport/loopback-only'])
    api('cookie-scriptable', API130,
        "        extra.append(('Set-Cookie', '%s=%s; Secure; HttpOnly; SameSite=Strict; Path=/' % (COOKIE, cookie)))",
        "        extra.append(('Set-Cookie', '%s=%s; Secure; SameSite=Lax; Path=/' % (COOKIE, cookie)))  # defect",
        ['session/cookie-and-expiry'])
    api('cookie-kept-plain', API130, "        return hashlib.sha256(cookie.encode('ascii', 'replace')).hexdigest()",
        "        return cookie  # defect: the cookie itself is kept", ['session/cookie-and-expiry'])
    api('challenge-reusable', API130,
        "            issued = self._challenges.pop(named, None) if isinstance(named, str) else None",
        "            issued = self._challenges.get(named) if isinstance(named, str) else None  # defect: reusable",
        ['session/cookie-and-expiry'])
    api('sign-out-keeps-session', API130, "        self.sessions.end(session['handle'])\n",
        "        pass  # defect: sign-out ends nothing\n", ['session/cookie-and-expiry'])
    api('pending-limit-unenforced', API130, "            if len(self._registrations) + len(self._pending_files()) >= PENDING_LIMIT:",
        "            if False:  # defect: unbounded pending registrations", ['enrollment/pending-grants-nothing'])
    api('hsts-omitted', API130,
        "               ('Strict-Transport-Security', HSTS), ('X-Content-Type-Options', 'nosniff')] + extra",
        "               ('X-Content-Type-Options', 'nosniff')] + extra  # defect: no HSTS", ['transport/loopback-only'])
    api('body-cap-unenforced', API130, "            if size < 0 or size > BODY_LIMIT:",
        "            if size < 0:  # defect: any body size is read", ['transport/loopback-only'])
    api('uv-unchecked', WA130, "    if not flags & USER_VERIFIED:\n        return ['user_not_verified']\n", '',
        ['webauthn/stand-in-browser', 'webauthn/independent-vectors'])
    api('up-unchecked', WA130, "    if not flags & USER_PRESENT:\n        return ['user_not_present']\n", '',
        ['webauthn/stand-in-browser'])
    api('origin-not-compared', WA130, "    if data.get('origin') != origin:\n        return 'wrong_origin'\n", '',
        ['webauthn/stand-in-browser', 'webauthn/independent-vectors', 'enrollment/pending-grants-nothing'])
    api('cross-origin-accepted', WA130,
        "    if 'crossOrigin' in data and data['crossOrigin'] is not False:\n        return 'cross_origin'\n", '',
        ['webauthn/stand-in-browser', 'webauthn/independent-vectors'])
    api('rp-hash-unchecked', WA130, "    if auth[:32] != hashlib.sha256(rp_id.encode('ascii')).digest():",
        "    if False:  # defect: the relying party is not bound", ['webauthn/stand-in-browser', 'webauthn/independent-vectors'])
    api('ceremony-type-unchecked', WA130, "    if data.get('type') != kind:\n        return 'wrong_ceremony'\n", '',
        ['webauthn/stand-in-browser'])
    api('challenge-unchecked', WA130,
        "    if not isinstance(challenge, str) or not challenge or data.get('challenge') != challenge:",
        "    if False:  # defect: any challenge", ['webauthn/stand-in-browser', 'enrollment/pending-grants-nothing'])
    api('user-handle-unchecked', WA130,
        "    if assertion.get('user_handle') != credential.get('user_handle'):",
        "    if False:  # defect: any user handle", ['webauthn/stand-in-browser'])
    api('signature-unverified', WA130, "        return done.returncode == 0",
        "        return True  # defect: the signature is not checked",
        ['webauthn/stand-in-browser', 'webauthn/independent-vectors', 'enrollment/steward-signed'])
    api('possession-not-rechecked', CR130,
        "            if W.possession_problems(binding, params['proof'], self.origin, self.rp_id, self.state_dir):",
        "            if False:  # defect: the possession proof is not checked at the host", ['enrollment/steward-signed'])
    api('steward-role-unchecked', CR130, "        if CM.STEWARD_ROLE not in (entry.get('roles') or []):",
        "        if False:  # defect: any person enrolls a passkey", ['enrollment/steward-signed'])
    api('steward-scope-unchecked', CR130, "        if not CM.scope_covers(entry.get('scope'), (member or {}).get('scope')):",
        "        if False:  # defect: the steward's scope is not checked", ['enrollment/steward-signed'])
    api('expired-registration-accepted', CR130, "            if binding['expires_at'] <= now:",
        "            if False:  # defect: an expired pending registration is enrolled", ['enrollment/steward-signed'])
    api('revoked-credential-current', CR130,
        "    if found.get('revoked_at') is not None and found['revoked_at'] <= now:\n        return found, 'credential_revoked'\n",
        '', ['session/revocation-ends', 'edge/signer-api-purpose'])
    api('revoked-member-credential-current', CR130,
        "    if not AC.active_member(member, now)[0]:\n        return found, 'principal_not_member'\n", '',
        ['session/revocation-ends'])
    api('signer-credential-unchecked', SG130,
        "    _record, why = CR.current(state, a['credential_id'], now, principal=a['principal'])",
        "    _record, why = None, None  # defect: the signer signs for any principal", ['edge/signer-api-purpose'])
    api('signer-expiry-unchecked', SG130, "    if AS.time_problem(a, now):\n        raise Refused('assertion-expired'",
        "    if False:\n        raise Refused('assertion-expired'", ['edge/signer-api-purpose'])
    api('signer-signs-any-shape', SG130, "        if AS.shape_problems(assertion):",
        "        if False:  # defect: any value is signed", ['edge/signer-api-purpose'])
    api('authority-signature-unverified', AU130, "        if not verified:\n            raise Refused('unauthenticated:signature'",
        "        if False:\n            raise Refused('unauthenticated:signature'", ['edge/authority-recheck'])
    api('authority-credential-unchecked', AU130,
        "        if why:\n            raise Refused('unauthenticated:' + why",
        "        if False:\n            raise Refused('unauthenticated:' + why", ['edge/authority-recheck', 'session/revocation-ends'])
    api('authority-expiry-unchecked', AU130, "        if AS.time_problem(a, now):\n            raise Refused('unauthenticated:expired'",
        "        if False:\n            raise Refused('unauthenticated:expired'", ['edge/authority-recheck'])
    api('authority-domain-unchecked', AU130,
        "        if a['domain'] != self.domain or any(a[f] != v for f, v in self.ids.items()):",
        "        if False:  # defect: any domain is executed", ['edge/authority-recheck'])
    api('ui-refusal-reported-settled', AU130,
        "        refusal = result.get('reason') if result.get('outcome') in ('refused', 'unknown_outcome') else None",
        "        refusal = None  # defect: every domain result is a success", ['decisions/one-ruling', 'decisions/exact-settlement'])
    api('message-speaker-is-edge', AS130,
        "                'principal': a['principal'], 'text': p['text'], 'project': p['project'], 'clarifies': p['clarifies']}",
        "                'principal': a['edge'], 'text': p['text'], 'project': p['project'], 'clarifies': p['clarifies']}",
        ['messages/common-intake'])
    api('message-text-trimmed', AS130,
        "                'principal': a['principal'], 'text': p['text'], 'project': p['project'], 'clarifies': p['clarifies']}",
        "                'principal': a['principal'], 'text': p['text'].strip(), 'project': p['project'], 'clarifies': p['clarifies']}",
        ['messages/common-intake'])
    api('answer-rationale-dropped', AS130, "                    presentation_version=p['presentation_version'], choice=p['choice'], rationale=p['rationale'])",
        "                    presentation_version=p['presentation_version'], choice=p['choice'], rationale='')  # defect",
        ['decisions/exact-settlement'])
    api('ui-answer-settles-again', 'control_request_settlement.py',
        "            if item['data']['state'] not in self.I.PENDING:\n                raise Refused('request_closed', 'the request is no longer pending')\n",
        '', ['decisions/one-ruling'],
        also=[("        if data['state'] not in self.I.PENDING:\n            raise Refused('already_settled' if",
               "        if False:\n            raise Refused('already_settled' if"),
              ("        winner_id, _, channel, winner = valid[0]", "        winner_id, _, channel, winner = valid[-1]"),
              ("        expected.update({sid: 0, eff: 0, rec: 0, terms['terms_id']",
               "        expected.update({sid: (self._entity(sid) or {}).get('version', 0), eff: (self._entity(eff) or {}).get("
               "'version', 0), rec: (self._entity(rec) or {}).get('version', 0), terms['terms_id']"),
              ("        self._commit(SETTLE, sid, params, expected)", "        self._commit(SETTLE, sid + ':' + winner_id, params, expected)"),
              ("        if any(x in before for x in (sid, eid, rid)):\n            raise refused('stale_subject', 'this request version is settled')\n", ''),
              ("\n                or data.get('state') not in self.I.PENDING):", "):")])
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
    # `dir`: the directory a production module lives in, relative to the root (.veldo by default;
    # VELDO-0058's gate script lives in scripts).
    base = root / 'scripts/fixtures' if fixture else root / case.get('dir', '.veldo')
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
    details = []  # a false row's own words after its colon: what the check saw, kept beside the row

    def observe(name, condition):
        rows.append([name.split(':', 1)[0], bool(condition)])
        if not condition and ':' in name:
            details.append([rows[-1][0], name.split(':', 1)[1].strip()])
    ns = {'__file__': str(shared), '__observe__': observe}
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
            anchor = 'ROOT / "' + case.get('dir', '.veldo') + '" / "' + case['module'] + '"'
            if not source.count(anchor):
                raise RuntimeError('suite production-copy anchor moved')
            source = source.replace(anchor, '__import__("pathlib").Path(' + repr(mutant) + ')')
        ns['__suite_file__'] = str(suite)
        exec(compile(source, str(suite), 'exec'), ns)
    return {'count': len(rows), 'observations': rows,
            'row_names': [name for name, _ in rows],
            'failed_rows': [name for name, ok in rows if not ok],
            'failed_details': details,
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
