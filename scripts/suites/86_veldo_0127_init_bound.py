"""Independently driven init-bound closure of 86_veldo_0127_agent_configuration.py."""

_speed_inputs = {
    'control_agent_config.py': ROOT / ".veldo" / "control_agent_config.py",
    'control_agent_config_handoff.py': ROOT / ".veldo" / "control_agent_config_handoff.py",
    'control_launch.py': ROOT / ".veldo" / "control_launch.py",
    'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
    'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
}
__import__('runpy').run_path(
    str(ROOT / "scripts/suites" / "86_veldo_0127_agent_configuration.py"),
    init_globals=dict(globals(), __speed_closure__='init-bound', __speed_inputs__=_speed_inputs),
)
