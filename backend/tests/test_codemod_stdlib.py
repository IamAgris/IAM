"""The stdlib annotation codemod works where libcst's native extension is blocked."""

import importlib.util
import unittest
from pathlib import Path

TOOL = (
    Path(__file__).resolve().parents[2]
    / "tools/quality/annotate_signatures_stdlib.py"
)


def _tool():
    spec = importlib.util.spec_from_file_location("annotate_stdlib", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CodemodTests(unittest.TestCase):
    def test_annotates_params_and_returns_without_libcst(self):
        tool = _tool()
        source = "def add(a, b=2):\n    return a + b\n"
        result = tool.transform(source)
        self.assertIn("from typing import Any", result)
        self.assertIn("a: Any", result)
        self.assertIn("-> Any:", result)
        compile(result, "fixture.py", "exec")

    def test_keeps_existing_annotations_and_docstring(self):
        tool = _tool()
        source = '"""Doc."""\n\ndef f(x: int) -> int:\n    return x\n'
        self.assertEqual(tool.transform(source), source)


if __name__ == "__main__":
    unittest.main()
