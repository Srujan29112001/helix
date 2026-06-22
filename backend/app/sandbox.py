"""Code-execution sandbox for agent-generated Python (Phase 3).

Two execution backends sit behind one interface (``execute_code``):

1. **E2B microVM** (preferred, hardened) — when ``E2B_API_KEY`` is set, code runs
   in a remote E2B sandbox: true VM isolation, controlled network, and a hard
   execution timeout. Native pandas/numpy/sklearn run normally inside it.
2. **RestrictedPython** (zero-dependency fallback) — in-process, AST-restricted
   execution with guarded attribute/item/iteration access, a curated builtins
   set, and an import whitelist (no os/sys/socket/subprocess/open). Used when no
   E2B key is configured, or if an E2B call fails — so a run never breaks.

Either backend captures stdout and tracebacks so the Critic can read failures
and self-correct — the literal "self-correcting code execution" from the proposal.
"""

from __future__ import annotations

import builtins as _py_builtins
import os
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
    "format", "repr", "divmod", "pow",
)


def _safe_import(name, *args, **kwargs):
    root = name.split(".")[0]
    if root in _ALLOWED_IMPORTS:
        return __import__(name, *args, **kwargs)
    raise ImportError(f"import of '{name}' is blocked in the sandbox")


def _safe_getattr(obj, name, default=None):
    """Permissive attribute access for real-world data code: allow normal methods
    (including str.format, which RestrictedPython otherwise blocks) but deny
    dunder/underscore access — the usual sandbox-escape vector."""
    if isinstance(name, str) and name.startswith("_"):
        raise AttributeError(f"access to '{name}' is blocked in the sandbox")
    return getattr(obj, name) if default is None else getattr(obj, name, default)


@dataclass
class SandboxResult:
    ok: bool
    stdout: str
    error: str  # short, last line of the traceback when ok is False
    engine: str = "restrictedpython"  # which backend executed the code
    note: str = ""  # e.g. why E2B was skipped and we fell back to RestrictedPython


def _short(msg: str) -> str:
    """Trim long errors (pandas dumps whole columns into some tracebacks)."""
    msg = str(msg)
    if len(msg) > 90:
        msg = msg[:60].rstrip() + " ... " + msg[-25:].lstrip()
    return msg


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
        "_getattr_": _safe_getattr,
        "_getitem_": default_guarded_getitem,
        "_getiter_": default_guarded_getiter,
        "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
        "_unpack_sequence_": guarded_unpack_sequence,
        "_write_": lambda obj: obj,  # allow item/attr assignment on sandboxed objects
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
        return SandboxResult(False, out, f"{type(exc).__name__}: {_short(str(exc))}")


def run_in_e2b(code: str, df: "pd.DataFrame", api_key: str | None = None) -> SandboxResult:
    """Execute ``code`` in an E2B microVM with ``df`` preloaded as a DataFrame.

    Hardened isolation: a fresh VM, controlled network, and a hard execution
    timeout. Requires an E2B key (``api_key`` arg or the ``E2B_API_KEY`` env var)
    and the ``e2b-code-interpreter`` SDK. Raises on setup failure so the caller
    can fall back to RestrictedPython.
    """
    from e2b_code_interpreter import Sandbox  # imported lazily (optional dep)

    csv = df.to_csv(index=False)
    # SDK v2.x: the bare ``Sandbox(...)`` constructor no longer accepts api_key/
    # timeout — use the ``create()`` factory. ``timeout`` here is the microVM
    # lifetime; the per-exec timeout is passed to ``run_code`` below.
    with Sandbox.create(api_key=api_key, timeout=120) as sbx:  # microVM auto-killed on context exit
        sbx.files.write("/home/user/data.csv", csv)
        prelude = (
            "import pandas as pd, numpy as np\n"
            "df = pd.read_csv('/home/user/data.csv')\n"
        )
        ex = sbx.run_code(prelude + code, timeout=45)
        stdout = "".join(getattr(ex.logs, "stdout", None) or [])
        err = getattr(ex, "error", None)
        if err:
            name = getattr(err, "name", "Error")
            value = getattr(err, "value", "")
            return SandboxResult(False, stdout.strip(), _short(f"{name}: {value}"), engine="e2b")
        return SandboxResult(True, stdout.strip(), "", engine="e2b")


def execute_code(code: str, df: "pd.DataFrame", e2b_key: str | None = None) -> SandboxResult:
    """Run agent-generated code with ``df`` available, choosing the best sandbox.

    Uses an E2B microVM when an E2B key is available (``e2b_key`` arg — e.g. from
    the Studio UI — or the ``E2B_API_KEY`` env var): hardened isolation, network
    controls, hard timeout. Otherwise — or if the E2B call errors — the in-process
    RestrictedPython sandbox. A run never breaks.
    """
    key = e2b_key or os.getenv("E2B_API_KEY")
    fallback_note = ""
    if key:
        try:
            return run_in_e2b(code, df, key)
        except Exception as exc:  # noqa: BLE001 — SDK missing / network / quota / bad key → fall back
            fallback_note = f"E2B unavailable ({type(exc).__name__}: {_short(str(exc))}) — using RestrictedPython"
            print(f"[sandbox] {fallback_note}")
    res = run_in_sandbox(code, {"df": df.copy()})
    res.note = fallback_note
    return res


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
