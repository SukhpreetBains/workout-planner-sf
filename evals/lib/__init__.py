"""Deterministic cost-and-time telemetry for the Ascent evaluation suites.

Standard library only, Python 3.9+. No model is ever invoked anywhere in this
package: every number it emits is parsed out of an agent session log with code.
See docs/sgaf-717-evals-redesign-spec.md for the schemas this package produces.
"""

__all__ = ["telemetry", "aggregate", "emit_summary"]
