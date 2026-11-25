"""Independently driven records closure of 86_veldo_0189_engine_upgrade.py."""

_speed_inputs = {
    'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
    'control_factory_setup_upgrade.py': ROOT / ".veldo" / "control_factory_setup_upgrade.py",
    'control_factory_setup_engines.py': ROOT / ".veldo" / "control_factory_setup_engines.py",
    'control_factory_setup_api.py': ROOT / ".veldo" / "control_factory_setup_api.py",
    'control_service.py': ROOT / ".veldo" / "control_service.py",
    'control_store.py': ROOT / ".veldo" / "control_store.py",
    'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
}
__import__('runpy').run_path(
    str(ROOT / "scripts/suites" / "86_veldo_0189_engine_upgrade.py"),
    init_globals=dict(globals(), __speed_closure__='records', __speed_inputs__=_speed_inputs),
)
