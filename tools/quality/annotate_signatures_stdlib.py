#!/usr/bin/env python3
"""Add ``Any`` annotations to unannotated function signatures (stdlib only).

A libcst-free replacement for ``annotate_signatures.py`` for hosts where the
libcst native extension is blocked. It edits only signature lines using the
token stream, preserving comments and formatting elsewhere. This is debt
reduction, not semantic typing: review the diff and never run it on files
without tests.

Usage:
    python tools/quality/annotate_signatures_stdlib.py --dry-run path/to/file.py
    python tools/quality/annotate_signatures_stdlib.py --apply path/to/file.py
"""

from __future__ import annotations

import argparse
import io
import tokenize
from pathlib import Path
from typing import List, Tuple

SKIP_PARAMS = frozenset({"self", "cls"})


def _insertions(source: str) -> List[Tuple[int, int, str]]:
    """Return (line, column, text) insertions, sorted in file order."""
    result: List[Tuple[int, int, str]] = []
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.type != tokenize.NAME or token.string != "def":
            index += 1
            continue

        # find '(' after the function name
        open_index = index + 2
        while open_index < len(tokens) and tokens[open_index].string != "(":
            if tokens[open_index].type == tokenize.NEWLINE:
                break
            open_index += 1
        if open_index >= len(tokens) or tokens[open_index].string != "(":
            index += 1
            continue

        depth = 1  # we start inside the opening parenthesis
        expect_param = True
        cursor = open_index + 1
        while cursor < len(tokens):
            current = tokens[cursor]
            if current.string == "(":
                depth += 1
            elif current.string == ")":
                if depth == 1:
                    break
                depth -= 1
            elif current.string == "," and depth == 1:
                expect_param = True
            if (
                depth == 1
                and expect_param
                and current.type == tokenize.NAME
                and current.string not in SKIP_PARAMS
            ):
                following = tokens[cursor + 1] if cursor + 1 < len(tokens) else None
                if following is None or following.string != ":":
                    result.append(
                        (current.start[0], current.end[1], ": Any")
                    )
                expect_param = False
            cursor += 1

        # return annotation: after the matching ')' and optional '-> ...' before ':'
        after = cursor + 1
        if after < len(tokens) and tokens[after].string != "->":
            while after < len(tokens) and tokens[after].string != ":":
                after += 1
            if after < len(tokens):
                closing = tokens[cursor]
                result.append((closing.end[0], closing.end[1], " -> Any"))
        index = cursor + 1
    return result


def transform(source: str) -> str:
    insertions = _insertions(source)
    lines = source.splitlines(keepends=True)
    for line, column, text in sorted(insertions, reverse=True):
        target = lines[line - 1]
        lines[line - 1] = target[:column] + text + target[column:]
    updated = "".join(lines)
    if insertions and "Any" in updated and "from typing import Any" not in updated:
        import ast

        tree = ast.parse(updated)
        last_import = 0
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                last_import = max(last_import, node.end_lineno or node.lineno)
        if last_import == 0 and tree.body and isinstance(tree.body[0], ast.Expr):
            first = tree.body[0]
            if isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                last_import = first.end_lineno or first.lineno
        lines = updated.splitlines(keepends=True)
        lines.insert(last_import, "from typing import Any\n")
        updated = "".join(lines)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()
    if args.apply == args.dry_run:
        parser.error("choose exactly one of --apply or --dry-run")

    total = 0
    for name in args.files:
        path = Path(name)
        source = path.read_text(encoding="utf-8")
        updated = transform(source)
        changed = updated != source
        total += int(changed)
        print(f"{'WOULD UPDATE' if args.dry_run else 'UPDATED' if changed else 'unchanged'}: {name}")
        if args.apply and changed:
            path.write_text(updated, encoding="utf-8", newline="")
    print(f"files changed: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
