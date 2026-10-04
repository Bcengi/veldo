"""The VELDO-0073 host configuration of the real Telegram ingress over the VELDO-0088 fixture's store.

The production channel (control_service_channel.open_channel) constructs the ingress from it with
control_channel_ingress.open_ingress, which opens its own store connection, as `serve` does. Every key
is generated here with ssh-keygen and stays under `base`; the bot origin is the fixture's loopback
stand-in and the token file holds its stand-in name.
"""
import json
import os
from pathlib import Path
import subprocess


def _private(path, text):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write(text)
    return Path(path)


def config(f, base, workspace):
    """The 0600 ingress configuration path for the fixture's store, identities and journal key."""
    host = Path(base) / 'ingress-host'
    host.mkdir(mode=0o700)
    keys = {}
    for who in ('settler', 'edge-auth'):
        path = host / who
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v88-' + who, '-f', str(path)],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
        keys[who] = path
    settler = ' '.join(keys['settler'].with_name('settler.pub').read_text().split()[:2])
    settlement_signers = _private(host / 'settlement_signers',
                                  'settler namespaces="veldo-decision-settlement" %s\n' % settler)
    enrollment_signers = _private(host / 'enrollment_signers',
                                  'steward namespaces="veldo-enrollment" %s\n' % f['public']['steward'])
    host_trust = _private(host / 'host_trust.json', json.dumps({
        'schema': 'veldo.host_trust/v1', 'host_identity': 'fixture-host',
        'enrollment_signers': str(enrollment_signers), 'settlement_signers': str(settlement_signers)}))
    token = _private(host / 'bot-token', 'bot89\n')
    return _private(host / 'ingress.json', json.dumps({
        'schema': 'veldo.telegram_ingress/v1', 'channel': 'telegram_chat', 'store_path': str(f['db']),
        'authority_ids': dict(f['ids']), 'authority_generation': 1,
        'journal': {'principal': 'authority', 'key': str(f['keyfile']['authority'])},
        'workspace': str(workspace), 'host_trust': str(host_trust),
        'signer': {'config': str(host / 'signer.json'), 'edge_key_id': 'edge-telegram',
                   'connection_key': str(keys['edge-auth'])},
        'edge_principal': 'telegram-edge', 'api_edge': 'api-edge',
        'bot_api': {'origin': f['url'], 'token_file': str(token)},
        'decision_signer': {'principal': 'settler', 'key': str(keys['settler'])}}))
