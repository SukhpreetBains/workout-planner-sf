#!/usr/bin/env python3
"""Compatibility entry point for the weekly status preparation helper."""

from pathlib import Path
import runpy

_SCRIPT = Path(__file__).resolve().parents[1] / 'types/weekly-status/scripts/prepare.py'
_module = runpy.run_path(str(_SCRIPT))
prepare = _module['prepare']
validate = _module['validate']
SKILL = _module['SKILL']

if __name__ == '__main__':
    runpy.run_path(str(_SCRIPT), run_name='__main__')
