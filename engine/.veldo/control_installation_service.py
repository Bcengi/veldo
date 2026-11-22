"""Service wiring for the installation loader and its OS reference subscription."""
import importlib.util
import json
import os
from pathlib import Path


def organ(name):
    spec = importlib.util.spec_from_file_location('installation_service_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


I = organ('installation')
C = organ('control_installation_config')


def setup_module():
    """Setup uses the installed loader's module identities and ownership bindings."""
    return organ('control_installation_setup')


def start(service, store):
    folder = service.config.get('installation')
    if not folder:
        return None, None
    repo = I.Repository(folder, service.config.get('installation_branch', 'main'))
    os.environ[I.ENVIRONMENT] = repo.folder
    watch = I.RefChanges(repo)
    channel = service.channel
    decisions = None
    if channel is not None:
        activation = channel.record()
        owner = (activation or {}).get('owner')
        if owner:
            signature = organ('control_signer')
            decisions = organ('control_installation_decision').Decisions(channel.ingress.settlement, owner,
                service.principal, lambda body: signature.sign_bytes(service.config['journal_key'], body,
                    organ('authority_contract').SIGNATURE_NAMESPACE))

    def tell(event):
        if channel is None or decisions is None:
            return
        presenter = channel.ingress.presenter
        enrollment = channel._entity(presenter.P.enrollment_id(decisions.owner))
        if enrollment:
            presenter._send(enrollment['data']['chat_id'], json.dumps(event, sort_keys=True), None)

    keystore = organ('control_credential_keystore').SecretService()
    def exists(name):
        try:
            return keystore.contains(name)
        except Exception as error:
            raise C.Refused('installation_unreadable:keystore_metadata') from error

    workflow_repository = (service.api.config['workflows_repository'] if service.api is not None
                           else next(iter(service.repositories)))
    common = dict(domain=service.domain, workflow_repository=workflow_repository, signer=service.principal,
                  sign=service.sign, secret_exists=exists, decisions=decisions, notify=tell,
                  observe=lambda event: service._log(dict(event, kind='installation', operation='configuration_load')),
                  generation=service.generation)
    try:
        loader = C.Loader(store, service.conn, repo, **common)
        result = loader.reconcile()
        if loader.accepted_commit is None:
            raise C.Refused((result.get('problems') or ['installation_unreadable:no_accepted_commit'])[0])
        # The API and channel share their own connection. Both read the same accepted records.
        if service.api is not None and service.api.conn is not service.conn:
            C.Loader(store, service.api.conn, repo, **common)
        return loader, watch
    except BaseException:
        watch.close()
        raise
