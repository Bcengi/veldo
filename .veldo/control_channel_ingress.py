#!/usr/bin/env python3
"""The activated Telegram ingress: a notification wakes canonical acquisition, never settles (VELDO-0073).

WHAT THIS MODULE IS. The production path from the Telegram edge to the one settlement. `open_ingress`
constructs it from the host's configuration: the authority's control store, its journal signer, the
host trust whose settlement signers VELDO-0054 readers verify against (control_eligibility), the
VELDO-0067 protected answer signer, the bot token from its file, and the VELDO-0073 activation gate
that every Telegram exchange of the edges it builds asks first. It returns an Ingress holding the
VELDO-0064 inbox, the VELDO-0065 presenter, the VELDO-0066 acquirer and the VELDO-0068 settlement
service, all on the one store connection.

A NOTIFICATION ONLY WAKES. `Ingress.wake` takes whatever woke it (a webhook body, a poll tick, an
invented payload) and keeps nothing of it but its digest: its fields are never read. It then asks the
gate, acquires through the platform's own getUpdates exchange (VELDO-0066 canonical evidence, sender,
message, chat and time read from what the platform returned), and runs the settlement service, which
settles only answers the presenter accepted from that evidence and the protected signer signed. A
payload that claims an answer settles nothing; the answer settles when the platform returns it. The
result preserves each acquired update's platform message identity.

A STOPPED EDGE. When the gate refuses (no activation, stopped, stale key or configuration), wake
acquires nothing and settles nothing, and every pending request stays pending.

THE DECISION SIGNER. The VELDO-0069 settlement service signs governing decision bindings with its
`decision_signer`. The configuration's `decision_signer` names its principal and its key, the host's
0600 file outside the workspace: the principal must be one of the host's settlement signers, and a
probe the key signs must verify under those signers as the VELDO-0054 readers verify a binding, so
the key is the one the host trusts. Without one a governing decision question refuses as
unavailable_service, as VELDO-0069 defines.

Observations carry identities, digests, outcomes and named refusals, never the token, a payload's
content, message text or a signature. Standard library only.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('ingress_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONFIG_SCHEMA = 'veldo.telegram_ingress/v1'
CONFIG_FIELDS = ('schema', 'channel', 'store_path', 'authority_ids', 'authority_generation', 'journal', 'workspace',
                 'host_trust', 'signer', 'edge_principal', 'api_edge', 'bot_api', 'decision_signer')
JOURNAL_NAMESPACE = 'veldo-journal'
RESULT_FIELDS = ('update_id', 'evidence_id', 'outcome', 'reason', 'request_id', 'presentation_id', 'answer_id')


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail = code, detail


def notification_digest(notification):
    """The digest of what woke the ingress: its bytes, or its canonical JSON. Nothing else is kept."""
    if isinstance(notification, (bytes, bytearray)):
        body = bytes(notification)
    else:
        body = json.dumps(notification, sort_keys=True, separators=(',', ':'), default=repr).encode()
    return 'sha256:' + hashlib.sha256(body).hexdigest()


class Ingress:
    """The Telegram ingress of one store connection: `gate`, the VELDO-0066 `acquirer` and the VELDO-0068
    `settlement` service, with the presenter and inbox they share."""

    def __init__(self, gate, acquirer, settlement, *, presenter=None, inbox=None, activations=None, conn=None):
        self.gate, self.acquirer, self.settlement = gate, acquirer, settlement
        self.presenter, self.inbox, self.activations, self.conn = presenter, inbox, activations, conn
        self.observations = []
        self.counts = {'woken': 0, 'refused': 0}

    def wake(self, notification):
        """Wake acquisition. The notification is digested, never read; only what the platform returns
        is acquired, and only answers accepted from it settle."""
        woken = notification_digest(notification)
        try:
            self.gate.admit('getUpdates', self.acquirer.edge.base_url)
        except Exception as exc:
            code = getattr(exc, 'code', None) or 'not_activated'
            self.counts['refused'] += 1
            self.observations.append({'operation': 'wake', 'woken_by': woken, 'outcome': 'refused', 'reason': code})
            return {'outcome': 'refused', 'reason': code, 'woken_by': woken, 'acquired': [], 'settled': []}
        acquired = []
        for result in self.acquirer.acquire():
            row = {k: result.get(k) for k in RESULT_FIELDS if k in result}
            evidence = (self.acquirer.evidence(result['evidence_id']) if result.get('evidence_id')
                        else self._any_evidence(result['update_id']) if result.get('update_id') is not None else None)
            if evidence:
                row['message_id'] = (evidence.get('fields') or {}).get('message_id')
                row['evidence_id'] = evidence.get('evidence_id')
            acquired.append(row)
        settled = [{k: r.get(k) for k in ('request_id', 'outcome', 'reason', 'settlement_id') if k in r}
                   for r in (self.settlement.run() if self.settlement is not None else [])]
        self.counts['woken'] += 1
        self.observations.append({'operation': 'wake', 'woken_by': woken, 'outcome': 'woken', 'reason': None,
                                  'acquired': len(acquired), 'settled': len(settled)})
        return {'outcome': 'woken', 'woken_by': woken, 'acquired': acquired, 'settled': settled}

    def _any_evidence(self, update_id):
        for (text,) in self.acquirer.conn.execute('SELECT data FROM entities WHERE kind=?', ('channel_evidence',)):
            data = json.loads(text)
            if data.get('update_id') == update_id:
                return data
        return None

    def metrics(self):
        return dict(self.counts, gate=dict(self.gate.counts),
                    pending=[e['id'] for e in (self.inbox.index()['entries'] if self.inbox is not None else [])
                             if e.get('category') == 'pending'])


# ---------------------------------------------------------------------------------------------
# The production construction
# ---------------------------------------------------------------------------------------------

def _private_file(path, what):
    """A regular file of this account that nobody else can read or write."""
    if not isinstance(path, str) or not os.path.isabs(path):
        raise Refused('invalid_input', '%s is an absolute path' % what)
    try:
        info = os.lstat(path)
    except OSError:
        raise Refused('missing_authority', '%s is absent' % what) from None
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise Refused('invalid_input', '%s is this account\'s own 0600 regular file' % what)
    return path


def load_config(path):
    try:
        config = json.loads(Path(_private_file(str(path), 'the ingress configuration')).read_text())
    except ValueError:
        raise Refused('invalid_input', 'the ingress configuration is not JSON') from None
    if not isinstance(config, dict) or config.get('schema') != CONFIG_SCHEMA or set(config) != set(CONFIG_FIELDS):
        raise Refused('invalid_input', 'the ingress configuration has exactly the %s fields' % CONFIG_SCHEMA)
    return config


def read_token(path):
    """The bot token from its custody file; never logged, returned or stored by this module."""
    token = Path(_private_file(path, 'the bot token file')).read_text().strip()
    if not token or any(c.isspace() for c in token):
        raise Refused('invalid_input', 'the bot token file holds one token')
    return token


def journal_signer(journal):
    """(principal, sign) for journal records, signed with the authority's journal key."""
    principal, key = journal.get('principal'), journal.get('key')
    _private_file(key, 'the journal key')

    def sign(message):
        done = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', key, '-n', JOURNAL_NAMESPACE], input=message,
                              capture_output=True, timeout=10, stdin=None,
                              env={k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')})
        if done.returncode:
            raise Refused('unavailable_service', 'the journal key did not sign')
        return done.stdout.decode()
    return principal, sign


def signer_principals(allowed_signers_text):
    return {line.split()[0] for line in allowed_signers_text.splitlines() if line.strip() and not line.startswith('#')}


def decision_signer(config, settlement_trust):
    """The VELDO-0069 decision signer the configuration names, or None when it names none."""
    named = config.get('decision_signer')
    if named is None:
        return None
    principal = named.get('principal') if isinstance(named, dict) else None
    if settlement_trust is None or principal not in signer_principals(settlement_trust.signers):
        raise Refused('missing_authority', 'the decision signer is not one of this host\'s settlement signers')
    key = named.get('key')
    _private_file(key, 'the decision key')
    workspace = os.path.realpath(config['workspace'])
    if os.path.commonpath([os.path.realpath(key), workspace]) == workspace:
        raise Refused('invalid_input', 'the decision key is kept outside the workspace')
    DD = organ('control_decision_dependency')

    def sign(message):
        done = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', key, '-n', DD.SETTLEMENT_NAMESPACE], input=message,
                              capture_output=True, timeout=10,
                              env={k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')})
        if done.returncode:
            raise Refused('unavailable_service', 'the decision key did not sign')
        return done.stdout.decode()
    # The key must be the one the host trusts for this principal: a probe it signs verifies under the
    # host's settlement signers exactly as the VELDO-0054 readers verify a binding.
    probe = b'veldo.decision_signer.probe/v1'
    if not settlement_trust.verify(probe, sign(probe), principal):
        raise Refused('missing_authority', 'the decision key is not the key the host trusts for its principal')
    return principal, sign


def open_ingress(config_path, clock=time.time):
    """THE PRODUCTION CONSTRUCTION of the activated Telegram ingress from the host configuration."""
    config = load_config(config_path)
    if config['channel'] != 'telegram_chat':
        raise Refused('invalid_input', 'Release 1 activates the Telegram chat channel only')
    ACT = organ('control_channel_activation')
    origin = (config['bot_api'] or {}).get('origin')
    if ACT.platform_of(origin) is None:
        raise Refused('invalid_input', 'the Bot API origin is the Telegram service or a loopback stand-in')
    token = read_token((config['bot_api'] or {}).get('token_file'))
    ids = config['authority_ids']
    generation = config['authority_generation']
    principal, sign = journal_signer(config['journal'])
    EL = organ('control_eligibility')
    try:
        trust = EL.load_host_trust(config['host_trust'])
        settlements = trust.settlement_trust(config['workspace']) if trust is not None else None
    except EL.Stopped as exc:
        raise Refused('missing_authority', str(exc)) from None
    if trust is None:
        raise Refused('missing_authority', 'this host has installed no trust')
    signer = decision_signer(config, settlements)
    claims = organ('control_claim')
    S, CM = claims.S, claims.CM
    K = organ('control_keys')
    I, P, V = organ('control_assignment'), organ('control_channel_projection'), organ('control_channel_presentation')
    EV, A, ST = organ('control_channel_attribution'), organ('control_signer_answers'), organ('control_request_settlement')
    contract = organ('entity_contract')
    conn = S.open_store(config['store_path'])
    CM.attach(S)
    K.attach(S)
    gate = ACT.Gate(S, conn, clock=clock)
    activations = ACT.Activations(S, conn, ids, principal, sign, generation, clock=clock)
    inbox = I.Inbox(S, CM, claims, contract, conn, ids, principal, sign)
    presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, origin, token, activation=gate), conn,
                            principal, sign, generation, clock, assignment=I)
    edge = config['signer']
    edge_sign = A.EdgeSigner(S, CM, conn, edge['config'], edge['edge_key_id'], edge['connection_key'], clock=clock)
    acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, origin, token, activation=gate), conn,
                           principal, sign, config['edge_principal'], edge_sign, generation, clock)
    settlement = ST.Settlement(S, CM, inbox, presenter, conn, principal, sign, assignment=I, presentation=V,
                               api_edge=config['api_edge'], authority_generation=generation, clock=clock,
                               decision_signer=signer)
    return Ingress(gate, acquirer, settlement, presenter=presenter, inbox=inbox, activations=activations, conn=conn)
