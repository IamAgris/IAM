#!/usr/bin/env python3
"""Mechanically annotate unannotated function signatures with ``Any``.

This is a debt-reduction aid, not semantic typing: it removes
``no-untyped-def``/``no-untyped-call`` noise so real typing issues become
visible. Always review the diff. Never run on files without tests.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import libcst as cst
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import AddImportsVisitor

ROOT = Path(__file__).resolve().parents[2]


class AnnotateFunctions(cst.CSTTransformer):
    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    def leave_FunctionDef(self, original_node, updated_node):
        changes = {}
        if updated_node.returns in (cst.MaybeSentinel.DEFAULT, None):
            changes["returns"] = cst.Annotation(cst.Name("Any"))
            self.count += 1

        params = updated_node.params

        def annotate(items, skip_first=False):
            result = []
            for index, param in enumerate(items):
                if isinstance(param, cst.Param) and param.annotation is None:
                    if skip_first and index == 0 and param.name.value in ("self", "cls"):
                        result.append(param)
                        continue
                    result.append(param.with_changes(annotation=cst.Annotation(cst.Name("Any"))))
                    self.count += 1
                else:
                    result.append(param)
            return result

        param_changes = {
            "params": annotate(params.params, skip_first=True),
            "posonly_params": annotate(params.posonly_params, skip_first=True),
            "kwonly_params": annotate(params.kwonly_params),
        }
        if isinstance(params.star_arg, cst.Param) and params.star_arg.annotation is None:
            param_changes["star_arg"] = params.star_arg.with_changes(
                annotation=cst.Annotation(cst.Name("Any")))
            self.count += 1
        if isinstance(params.star_kwarg, cst.Param) and params.star_kwarg.annotation is None:
            param_changes["star_kwarg"] = params.star_kwarg.with_changes(
                annotation=cst.Annotation(cst.Name("Any")))
            self.count += 1
        changes["params"] = params.with_changes(**param_changes)
        return updated_node.with_changes(**changes)


def transform(source: str) -> tuple[str, int]:
    module = cst.parse_module(source)
    annotate = AnnotateFunctions()
    updated = module.visit(annotate)
    if annotate.count:
        context = CodemodContext()
        visitor = AddImportsVisitor(context)
        visitor.add_needed_import(context, "typing", "Any")
        updated = visitor.transform_module(updated)
    return updated.code, annotate.count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    total = 0
    for raw in args.files:
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT / raw
        source = path.read_text(encoding="utf-8")
        code, count = transform(source)
        total += count
        print(f"{path.relative_to(ROOT).as_posix()}: {count} annotations")
        if args.apply and count:
            path.write_text(code, encoding="utf-8", newline="\n")
    print(f"TOTAL: {total} annotations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
