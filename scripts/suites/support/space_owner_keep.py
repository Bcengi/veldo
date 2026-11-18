"""The owner's Keep for the space suites, as VELDO-0318 made it: the signed space_disposition command.

Since VELDO-0318 (a9628b86) the Ledger's outcome refuses the owner's mark, whoever sends it. The
mark is written by one command only: the owner's signed space_disposition packet, for an item that
is deferred with a request, whose settled answer is Keep. The suites written before that marked
Keep through the outcome. This module is the one place they get the signed path from. It was
taken out of suite 156's fixture (VELDO-0343 fix 3, a7ef24a1), which now calls it.

Two ways, and each says what in it is real:

  Desk.owner_keeps   for a worktree (or a clone its table gives a request). Everything is the
                     production path on the fixture's own store: the request the Ledger holds, its
                     terms and inbox request, the presentation, the owner's answer through the API
                     edge, the settlement, and the owner's signed packet. Only the channel's send is
                     a stand-in. `reserve` writes the deferral and the request for a fixture that has
                     no Signal carrying the item to them.

  keep_planted       for an item of a kind the Ledger raises no request for (a scratch folder, an
                     image, a container, a private repository of table 1). No production path
                     settles a request for such an item, so the settled request is planted, as
                     VELDO-0318 did for suite 149 and suite 154_0335. The owner's signature, the
                     membership check and the one transition from deferred to kept are real.

Nothing here is a product module. The caller gives the modules its fixture loaded (the store, the
membership, the authority's codec), so one store module serves the whole fixture.
"""

import importlib.util
import json
import subprocess
import time
from pathlib import Path
from unittest.mock import patch


def keygen(path):
    """A new ed25519 key at `path`; its public half as text."""
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(path)],
                   check=True, capture_output=True)
    return Path(str(path) + '.pub').read_text().strip()


def signer(path, namespace):
    """What signs a message with the key at `path` under the authority's namespace."""
    def sign(message):
        return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(path), '-n', namespace],
                              input=message, capture_output=True, check=True).stdout.decode()
    return sign


def enroll(S, CM, AC, conn, ids, journal, by, by_sign, who, public, kind, roles, now, who_sign=None,
           scope='*'):
    """One enroll_principal command through the membership's own admission, signed by `by`. The
    first member enrols itself (`who` is `by`); any other signs its own enrolment too."""
    command = {'command_id': 'enroll-' + who, 'operation': 'enroll_principal', 'target': 'authority',
               'parameters': {'principal': who, 'principal_type': kind, 'roles': list(roles),
                              'public_key': public, 'independence_group': who, 'scope': scope},
               'artifact_digests': [], 'expected_versions': {}}
    membership = CM.authority_state(S, conn)
    envelope = dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=by,
                    request_revision=1, nonce='nonce-enroll-' + who, expires_at=now + 600,
                    membership_version=membership['membership_version'],
                    delegation_version=membership['delegation_version'],
                    command_digest=AC.canonical_command_digest(command))
    answer = CM.admit(S, conn, envelope, command, by_sign(AC.canonical_envelope_bytes(envelope)), ids, now,
                      journal_signer=('authority', journal),
                      enrollee_signature=None if who == by else who_sign(
                          AC.canonical_envelope_bytes(dict(envelope, principal=who))))
    assert answer['committed'], answer
    return answer


def _load(tag, path):
    spec = importlib.util.spec_from_file_location(tag, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Desk:
    """The owner's desk on one store: the production inbox, presenter and settlement, with a
    requester and an API edge the owner enrolled. It is made on first use. Only the channel's send is
    a stand-in.

    mods        the folder the fixture's production modules were copied to
    S, CM, AC   the store, membership and authority modules the store was opened with
    conn, ids   the store and its identifiers (domain, repository, store)
    journal     the authority's journal signer
    owner_sign  what signs as the owner, who is enrolled already, a person holding project_owner
    keys        a folder for the two service keys
    now         the time the fixture's commands carry
    """

    def __init__(self, mods, S, CM, AC, conn, ids, journal, owner_sign, keys, now, owner='owner',
                 tag='keepdesk', chat=31501, member=None):
        # `member`, when given, makes a service a member as the fixture made its own members (a
        # fixture whose membership is written as entities, with no steward to admit anyone):
        # member(who, public key). Without it the owner enrols the two through the admission.
        self.member = member
        self.mods, self.S, self.CM, self.AC, self.conn, self.ids = Path(mods), S, CM, AC, conn, ids
        self.journal, self.owner_sign, self.keys, self.now = journal, owner_sign, Path(keys), now
        self.owner, self.tag, self.chat = owner, tag, chat
        self.made, self.serial = {}, 0

    def open(self):
        if self.made:
            return self.made
        S, CM, AC = self.S, self.CM, self.AC
        I, V, PJ, ST, claims, contract = [
            _load('%s_%s' % (self.tag, name), self.mods / (name + '.py')) for name in (
                'control_assignment', 'control_channel_presentation', 'control_channel_projection',
                'control_request_settlement', 'control_claim', 'entity_contract')]
        # One store module and one membership module: the ones the store was opened with.
        claims.S, claims.CM, claims.AC = S, CM, AC
        signers = {}
        for who in ('requester', 'api-edge'):
            path = self.keys / ('key-' + who)
            public = keygen(path)
            signers[who] = signer(path, AC.SIGNATURE_NAMESPACE)
            if self.member is not None:
                self.member(who, public)
            else:
                enroll(S, CM, AC, self.conn, self.ids, self.journal, self.owner, self.owner_sign, who, public,
                       'service', [], self.now, who_sign=signers[who])
        eid = 'channel-enrollment:telegram_chat:' + self.owner
        S.execute(self.conn, dict(command_id='setup-channel-' + self.owner, nonce='setup-channel-' + self.owner,
                                  principal='authority', operation='upsert_entity',
                                  parameters=dict(entity_id=eid, kind='channel_enrollment',
                                                  data=dict(schema='veldo.channel_enrollment/v1',
                                                            channel='telegram_chat', principal=self.owner,
                                                            chat_id=self.chat, revoked_at=None)),
                                  expected_versions={eid: 0}, artifact_digests=[]), 'authority', self.journal, 1)

        class Transport:
            sent = []

            def send(self, chat, text, reply_to):
                self.sent.append(text)
                return dict(chat_id=chat, message_id=len(self.sent), date=int(time.time()), text=text,
                            reply_to_message_id=reply_to)

        inbox = I.Inbox(S, CM, claims, contract, self.conn, self.ids, 'authority', self.journal)
        presenter = V.Presenter(S, CM, PJ, inbox, Transport(), self.conn, 'authority', self.journal,
                                assignment=I)
        settlement = ST.Settlement(S, CM, inbox, presenter, self.conn, 'authority', self.journal,
                                   assignment=I, presentation=V, api_edge='api-edge')
        self.made.update(ST=ST, inbox=inbox, presenter=presenter, settlement=settlement, signers=signers)
        return self.made

    def publish(self, ledger, identity):
        """Publish the item's reserved request: its terms, its inbox request and its framing."""
        made = self.open()
        return ledger.publish_disposition(identity, made['settlement'], made['inbox'], made['presenter'],
                                          ('requester', made['signers']['requester']), self.owner)

    def owner_keeps(self, ledger, identity, item_kind):
        """The owner answers Keep to the item's request and signs the disposition. Returns the
        settlement's answer, what the Ledger says to the settled answer alone, and what it says to
        the owner's packet."""
        made, S = self.open(), self.S
        published = self.publish(ledger, identity)
        assert published['ok'], published
        rid = published['request']
        made['presenter'].present(rid)
        receipt = made['presenter'].current(rid)
        assert receipt, published
        self.serial += 1
        body = dict(self.ids, schema=made['ST'].API_SCHEMA, edge='api-edge', answer_id='answer-%d' % self.serial,
                    principal=self.owner, request_id=rid, request_version=receipt['request_version'],
                    presentation_id=receipt['presentation_id'], presentation_digest=receipt['brief_digest'],
                    presentation_version=receipt['presentation_version'], choice='accept keep',
                    rationale='Owner answer')
        settled = made['settlement'].api_answer(
            dict(answer=body, signature=made['signers']['api-edge'](S.canonical_bytes(body))))
        command = dict(operation='space_disposition', principal=self.owner, command_id='keep-%d' % self.serial,
                       nonce='keep-nonce-%d' % self.serial,
                       parameters=dict(item=identity, version=ledger._row(identity, item_kind)[0], request=rid))
        edge_alone = ledger.authorize_disposition(identity, rid)
        signed = ledger.disposition({'command': command, 'signature': self.owner_sign(S.canonical_bytes(command))},
                                    self.CM, self.now)
        return settled, edge_alone, signed


def reserve(ledger, remover, identity, commits=(), rule='unique_work', probe=None):
    """The deferral and the request Signal writes for an item with work in it, for a fixture with
    no Signal carrying the item there: the item, which is due, is deferred by the rule, and its
    request is reserved with the remover's own terms and the commit the work tree is at. A
    worktree gets the worktree's terms. With `probe`, the item is a clone its table gives a request
    (VELDO-0347 AC3) and gets the clone's terms, which offer Keep alone."""
    deferred = ledger.outcome(identity, 'deferred', {'rule': rule})
    if not deferred.get('ok'):
        return deferred
    record = ledger.item(identity)
    proposal = (remover.clone_proposal(ledger, probe, identity, record) if probe is not None
                else remover.disposition_proposal(ledger, identity, record, list(commits)))
    return ledger.request_disposition(identity, proposal, remover.disposition_head(record['locator']['path']))


_planted = [0]


def keep_planted(ledger, S, CM, conn, item_kind, identity, owner_sign, now, owner='owner'):
    """The owner's signed Keep of an item of a kind the Ledger raises no request for. The item, which
    is due, is deferred; the request and its settled answer are planted (no production path makes
    them for this kind); the owner's signature, the membership check and the one transition from
    deferred to kept, with the mark, are the Ledger's own. Returns the Ledger's answer."""
    deferred = ledger.outcome(identity, 'deferred', {'rule': 'unique_work'})
    if not deferred.get('ok'):
        return deferred
    _planted[0] += 1
    alias = 'fixture-keep-%d' % _planted[0]
    record = ledger.item(identity)
    record['disposition'] = {'state': 'requested', 'alias': alias}
    conn.execute('UPDATE entities SET data=?,digest=? WHERE id=?', (json.dumps(record), S.digest_of(record), identity))
    conn.commit()
    body = dict(operation='space_disposition', principal=owner, command_id='signed-' + alias, nonce='signed-' + alias,
                parameters=dict(item=identity, version=ledger._row(identity, item_kind)[0], request=alias))
    with patch.object(ledger, 'disposition_effect', return_value=({'choice': 'accept keep'}, owner)):
        return ledger.disposition(dict(command=body, signature=owner_sign(S.canonical_bytes(body))), CM, now)
