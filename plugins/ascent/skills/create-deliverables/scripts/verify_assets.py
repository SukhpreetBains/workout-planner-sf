#!/usr/bin/env python3
"""Compatibility entry point for the weekly status asset check."""

from pathlib import Path
import runpy

_SCRIPT = Path(__file__).resolve().parents[1] / 'types/weekly-status/scripts/verify_assets.py'
_module = runpy.run_path(str(_SCRIPT))
verify = _module['verify']

if __name__ == '__main__':
    runpy.run_path(str(_SCRIPT), run_name='__main__')
