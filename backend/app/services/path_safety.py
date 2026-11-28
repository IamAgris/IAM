"""Deterministic path-containment helpers used by security gates.

Each helper resolves symlinks and ``..`` segments before deciding containment.
Call sites keep their own policy (which root is trusted) and carry a narrow,
justified CodeQL suppression where the taint tracker cannot see the guard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

__all__ = ["UnsafePathError", "contained_path", "safe_child_name"]

PathLike = Union[str, Path]


class UnsafePathError(ValueError):
    """Raised when a supplied path escapes its trust boundary."""


def contained_path(root: PathLike, candidate: PathLike) -> Path:
    """Resolve *candidate* and require it to live under *root*.

    Absolute candidates are accepted only when they resolve inside *root*;
    traversal segments and symlinks are resolved before the comparison.
    """
    base = Path(root).resolve()
    # codeql[py/path-injection] this helper is the sanitizer: the resolved path is rejected below unless contained.
    resolved = (base / Path(candidate)).resolve()
    if resolved != base and base not in resolved.parents:
        raise UnsafePathError("path escapes the allowed root")
    return resolved


def safe_child_name(name: str) -> str:
    """Return a single safe path component, rejecting separators and traversal."""
    value = str(name)
    if not value or value in {".", ".."} or "\x00" in value:
        raise UnsafePathError("invalid path component")
    # codeql[py/path-injection] this helper is the sanitizer: separators and absolute paths are rejected.
    if "/" in value or "\\" in value or Path(value).is_absolute():
        raise UnsafePathError("path component contains a separator")
    if len(value) > 255:
        raise UnsafePathError("path component is too long")
    return value
