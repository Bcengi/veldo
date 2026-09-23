#!/usr/bin/env python3
"""Install the locked LangGraph runtime for this account (VELDO-0043). Standard library only.

  python3 .veldo/control_graph_install.py

Builds <account home>/.local/share/veldo/langgraph/<lock digest>/ as a virtual environment,
created from the RESOLVED base interpreter (so pyvenv.cfg names no repository virtual environment;
a creating interpreter or prefix inside a repository is refused), WITHOUT pip and installs exactly the wheels in control_graph_lock.py into it: a throwaway tool
environment's pip (the interpreter's own bundled copy, never kept) runs
`pip --python <runtime python> install --require-hashes --no-deps --only-binary=:all:` from the
lock's exact pins and sha256 hashes, so the runtime holds the locked distributions and nothing
else. The environment is built beside
its final name and renamed into place only after the install and an import of langgraph succeed,
so the adapter never finds a half-built runtime. The account home comes from the password
database, never $HOME. An existing runtime for this lock digest is left as it is.

Run it by hand; never from the gate or a suite. VELDO-0045 later owns distribution and activation.
"""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
COMMAND = 'python3 .veldo/control_graph_install.py'


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _lock():
    return _load('veldo_control_graph_lock', 'control_graph_lock.py')


def base_interpreter(python):
    """The resolved base interpreter behind `python` (never a virtual environment's wrapper), its
    resolved prefix, and its version. The runtime is created from this path, so pyvenv.cfg records
    it; an interpreter or prefix inside a repository is refused by name."""
    out = subprocess.run([python, '-I', '-c', 'import os, sys; print(os.path.realpath(getattr(sys, "_base_executable", '
                          'sys.executable))); print(os.path.realpath(sys.base_prefix)); print("%d.%d" % sys.version_info[:2])'],
                         capture_output=True, text=True, check=True).stdout.split('\n')
    base, prefix, version = out[0], out[1], out[2]
    graph = _load('veldo_control_graph', 'control_graph.py')
    for label, path in (('interpreter', base), ('prefix', prefix)):
        if graph.inside_repository(path):
            raise SystemExit('refused: the creating ' + label + ' ' + path + ' lies inside a repository')
    return base, version


def _environment():
    """The caller's environment with every pip, Python and virtual-environment override removed."""
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('PIP_', 'PYTHON', 'VIRTUAL_ENV', 'CONDA'))}
    env.update(PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK='1', PIP_NO_INPUT='1',
               PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
    return env


def install(python=sys.executable, home=None, out=sys.stdout):
    lock = _lock()
    target = lock.runtime_directory(home)
    if (target / 'bin' / 'python').is_file():
        out.write('present: ' + str(target) + '\n')
        return target
    python, version = base_interpreter(python)
    if version != lock.PYTHON:
        raise SystemExit('refused: the lock is for Python ' + lock.PYTHON + ', not ' + version)
    target.parent.mkdir(parents=True, exist_ok=True)
    building = Path(tempfile.mkdtemp(prefix='.building-', dir=target.parent))
    try:
        env = _environment()
        subprocess.run([python, '-I', '-m', 'venv', '--without-pip', str(building)], check=True, env=env)
        requirements = building / 'veldo-lock.txt'
        requirements.write_text(lock.requirements())
        with tempfile.TemporaryDirectory(prefix='veldo-pip-') as tool:
            subprocess.run([python, '-I', '-m', 'venv', tool], check=True, env=env)
            subprocess.run([str(Path(tool) / 'bin' / 'python'), '-I', '-m', 'pip', '--python',
                            str(building / 'bin' / 'python'), 'install', '--quiet', '--require-hashes',
                            '--no-deps', '--only-binary=:all:', '-r', str(requirements)],
                           check=True, env=env)
        subprocess.run([str(building / 'bin' / 'python'), '-I', '-B', '-c', 'import langgraph.graph'],
                       check=True, env=env)
        os.rename(building, target)
    finally:
        if building.exists():
            shutil.rmtree(building)
    out.write('installed: ' + str(target) + '\n')
    return target


if __name__ == '__main__':
    if len(sys.argv) != 1:
        sys.exit('usage: ' + COMMAND)
    install()
