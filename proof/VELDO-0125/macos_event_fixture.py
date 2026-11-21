"""Event simulation sharing VELDO-0124's evidence-bound logic fixtures.

Synthetic documents are test inputs, never real host qualification.
"""
import importlib.util
from pathlib import Path
_spec = importlib.util.spec_from_file_location('v124_event_support', Path(__file__).resolve().parents[1] / 'VELDO-0124/checks.py')
_support = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_support)
globals().update({name: value for name, value in vars(_support).items() if not name.startswith('_')})
