"""Inspect the retained Mac qualification account without printing credentials.

This is a prerequisite diagnostic, not a native qualification or an AC falsifier.
It makes no model request and does not create a login. Run on the selected Mac.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def main():
    if sys.platform != 'darwin':
        print(json.dumps({'status': 'not_run', 'reason': 'requires_selected_mac'}))
        return 2
    owner = Path(pwd.getpwuid(os.getuid()).pw_dir)
    profile = owner / '.veldo-mac-accounts' / 'claude-1'
    executable = owner / '.local/share/claude/versions/2.1.303'
    claude = json.loads((ROOT / 'engine/runtime/claude-qualification.json').read_text())
    codex = json.loads((ROOT / 'engine/runtime/codex-qualification.json').read_text())
    result = {
        'schema': 'veldo.macos_prerequisite_observation/v1',
        'qualification': False,
        'account': 'claude-1',
        'profile_exists': profile.is_dir(),
        'profile_file_credential_exists': (profile / '.credentials.json').is_file(),
        'linux_claude_versions': sorted(claude['versions']),
        'linux_codex_version': codex['version'],
        'mac_claude_versions_present': [v for v in sorted(claude['versions'])
            if (owner / '.local/share/claude/versions' / v).is_file()],
        'retained_codex_installations': sorted(p.name for p in
            (owner / '.local/share/veldo-engines').glob('codex-*')),
        'diagnostic_claude_version': '2.1.303',
    }
    if not executable.is_file() or not profile.is_dir():
        result.update(status='blocked', reason='retained_diagnostic_installation_missing')
    else:
        spec = importlib.util.spec_from_file_location('mac_profile', ROOT / '.veldo/project_runner_macos_profile.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Own scratch only; leave existing qualification folders and profiles intact.
        scratch = Path(tempfile.mkdtemp(prefix='veldo-0147-preflight-')).resolve()
        policy = module.sandbox([str(scratch), str(profile)], [str(ROOT / '.veldo')],
            str(owner), accounts=[str(profile.parent)])
        result['policy_digest'] = module.digest(policy)
        result['binary_digest'] = module.file_digest(executable)
        result['profile_module_digest'] = 'sha256:' + hashlib.sha256(
            (ROOT / '.veldo/project_runner_macos_profile.py').read_bytes()).hexdigest()
        environment = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin', HOME=str(scratch), TMPDIR=str(scratch),
                           CLAUDE_CONFIG_DIR=str(profile), DISABLE_AUTOUPDATER='1')
        try:
            done = subprocess.run(['/usr/bin/sandbox-exec', '-p', policy, str(executable),
                'auth', 'status', '--json'], env=environment, cwd=scratch,
                stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
            # Raw stdout can contain account identifiers. Neither stream is logged.
            report = json.loads(done.stdout)
            logged_in = report.get('loggedIn') is True
            method = report.get('authMethod')
            result.update(auth_exit=done.returncode, logged_in=logged_in,
                subscription_method=method == 'claude.ai', no_method=method in (None, 'none'))
            result.update(status='available' if logged_in and method == 'claude.ai' else 'blocked',
                          reason='subscription_login_observed' if logged_in and method == 'claude.ai'
                          else 'no_subscription_login_in_keychain_denying_sandbox')
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            result.update(status='blocked', reason='login_status_unreadable', error=type(error).__name__)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result['status'] == 'available' else 2


if __name__ == '__main__':
    sys.exit(main())
