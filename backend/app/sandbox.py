"""RestrictedPython execution sandbox (Phase 3).

Runs LLM-generated Python with file-system, network, and dangerous imports
blocked. Captures stdout and tracebacks so the Critic can read failures and
self-correct — the literal "self-correcting code execution" from the proposal.

Safety model: RestrictedPython compiles the code with guarded attribute/item/
iteration access, a curated builtins set, and an import hook that only allows a
data-science whitelist (no os/sys/socket/subprocess/open).
"""

from __future__ import annotations

import builtins as _py_builtins
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from RestrictedPython import compile_restricted, safe_builtins, utility_builtins
from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter
from RestrictedPython.Guards import (
    full_write_guard,
    guarded_iter_unpack_sequence,
    guarded_unpack_sequence,
    safer_getattr,
)
from RestrictedPython.PrintCollector import PrintCollector

# Modules the generated code is allowed to import.
_ALLOWED_IMPORTS = {
    "pandas",
    "numpy",
    "math",
    "statistics",
    "random",
    "datetime",
    "collections",
    "itertools",
    "functools",
    "re",
    "json",
    "sklearn",
    "scipy",
}

# Extra safe builtins data-science code commonly needs (beyond safe_builtins).
_EXTRA_BUILTINS = (
    "enumerate", "sorted", "sum", "min", "max", "list", "dict", "set",
    "tuple", "map", "filter", "reversed", "any", "all", "len", "range",
    "abs", "round", "str", "int", "float", "bool", "zip", "isinstance",
)


def _safe_import(name, *args, **kwargs):
    root = name.split(".")[0]
    if root in _ALLOWED_IMPORTS:
        return __import__(name, *args, **kwargs)
    raise ImportError(f"import of '{name}' is blocked in the sandbox")


@dataclass
class SandboxResult:
    ok: bool
    stdout: str
    error: str  # short, last line of the traceback when ok is False


def run_in_sandbox(code: str, variables: dict | None = None) -> SandboxResult:
    """Compile + execute ``code`` under RestrictedPython. Never raises."""
    safe = dict(safe_builtins)
    safe.update(utility_builtins)
    for name in _EXTRA_BUILTINS:
        safe.setdefault(name, getattr(_py_builtins, name))
    safe["__import__"] = _safe_import

    glb = {
        "__builtins__": safe,
        "_print_": PrintCollector,
        "_getattr_": safer_getattr,
        "_getitem_": default_guarded_getitem,
        "_getiter_": default_guarded_getiter,
        "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
        "_unpack_sequence_": guarded_unpack_sequence,
        "_write_": full_write_guard,
        "pd": pd,
        "np": np,
    }
    if variables:
        glb.update(variables)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            byte_code = compile_restricted(code, "<agent-code>", "exec")
    except SyntaxError as exc:
        return SandboxResult(False, "", f"SyntaxError: {exc}")

    try:
        exec(byte_code, glb)  # noqa: S102 — sandboxed
        out = glb["_print"]() if "_print" in glb else ""
        return SandboxResult(True, out, "")
    except Exception as exc:  # noqa: BLE001 — sandboxed; report, never raise
        out = glb["_print"]() if "_print" in glb else ""
        msg = str(exc)
        if len(msg) > 90:  # pandas dumps whole columns into some errors
            msg = msg[:60].rstrip() + " ... " + msg[-25:].lstrip()
        return SandboxResult(False, out, f"{type(exc).__name__}: {msg}")


def strip_code_fences(text: str) -> str:
    """Strip ```python ... ``` fences that LLMs often wrap code in."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines)
    return t.strip()
