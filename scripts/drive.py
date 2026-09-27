#!/usr/bin/env python3
"""VELDO-0165 proof driver entry point; implementation and records live with the proof."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parents[1] / 'proof' / 'VELDO-0165' / 'drive.py'),
               run_name='__main__')
