"""Structural JSON diff used by run_parity.py."""
from __future__ import annotations


def walk(a, b, path, out):
    """Append (path, kind, old, new) for every difference between a and b."""
    if type(a) is not type(b):
        out.append((path, f"type {type(a).__name__} -> {type(b).__name__}", a, b))
        return
    if isinstance(a, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a:
                out.append((f"{path}.{key}", "added", None, b[key]))
            elif key not in b:
                out.append((f"{path}.{key}", "removed", a[key], None))
            else:
                walk(a[key], b[key], f"{path}.{key}", out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append((path, f"length {len(a)} -> {len(b)}", None, None))
        for index, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{index}]", out)
    elif a != b:
        out.append((path, "value", a, b))
