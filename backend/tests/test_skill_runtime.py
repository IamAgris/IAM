"""Unit tests for Skill Runtime adapters (no container execution)."""

import asyncio
import unittest
from pathlib import Path

from app.services.skillruntime.adapters import (
    DockerAdapter,
    ExecutionPlan,
    SkillRuntimeAdapterError,
    StubAdapter,
)


def plan(**overrides):
    values = dict(
        skill_id="iam.native.testing.demo",
        skill_dir=Path("/tmp/skill"),
        script="scripts/demo.py",
        arguments={},
        network=False,
        filesystem="none",
        checksum="abc",
    )
    values.update(overrides)
    return ExecutionPlan(**values)


class StubTests(unittest.TestCase):
    def test_stub_simulates_without_executing(self):
        result = asyncio.run(StubAdapter().execute(plan()))
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["simulated"])


class DockerPlanTests(unittest.TestCase):
    def setUp(self):
        self.adapter = DockerAdapter()

    def test_script_must_be_under_scripts(self):
        with self.assertRaises(SkillRuntimeAdapterError):
            self.adapter._container_script("../../etc/passwd")
        with self.assertRaises(SkillRuntimeAdapterError):
            self.adapter._container_script("/absolute.py")
        self.assertEqual(
            self.adapter._container_script("scripts/demo.py"),
            "/skill/scripts/demo.py",
        )

    def test_network_execution_is_rejected(self):
        with self.assertRaises(SkillRuntimeAdapterError):
            self.adapter._command(plan(network=True))

    def test_command_has_no_network_and_read_only_mount(self):
        command = self.adapter._command(plan())
        self.assertIn("none", command)
        self.assertIn("--read-only", command)
        self.assertIn("no-new-privileges", command)
        self.assertTrue(any(arg.endswith(":/skill:ro") for arg in command))


if __name__ == "__main__":
    unittest.main()
