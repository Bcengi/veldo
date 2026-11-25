"""Independently driven service closure of 71_veldo_0130_api.py."""

_speed_inputs = {
    'control_api.py': ROOT / ".veldo" / "control_api.py",
    'control_api_webauthn.py': ROOT / ".veldo" / "control_api_webauthn.py",
    'control_api_credentials.py': ROOT / ".veldo" / "control_api_credentials.py",
    'control_api_assertion.py': ROOT / ".veldo" / "control_api_assertion.py",
    'control_api_signer.py': ROOT / ".veldo" / "control_api_signer.py",
    'control_api_authority.py': ROOT / ".veldo" / "control_api_authority.py",
    'control_api_models.py': ROOT / ".veldo" / "control_api_models.py",
    'control_channel_enrollment.py': ROOT / ".veldo" / "control_channel_enrollment.py",
    'control_signer_answers.py': ROOT / ".veldo" / "control_signer_answers.py",
    'authority_contract.py': ROOT / ".veldo" / "authority_contract.py",
    'control_request_settlement.py': ROOT / ".veldo" / "control_request_settlement.py",
    'control_intake.py': ROOT / ".veldo" / "control_intake.py",
    'control_client_api.py': ROOT / ".veldo" / "control_client_api.py",
    'control_event_projection.py': ROOT / ".veldo" / "control_event_projection.py",
    'control_service.py': ROOT / ".veldo" / "control_service.py",
    'control_service_api.py': ROOT / ".veldo" / "control_service_api.py",
    'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
}
__import__('runpy').run_path(
    str(ROOT / "scripts/suites" / "71_veldo_0130_api.py"),
    init_globals=dict(globals(), __speed_closure__='service', __speed_inputs__=_speed_inputs),
)
