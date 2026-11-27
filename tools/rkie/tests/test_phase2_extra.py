"""Tests for semantic, multi-repo, coordination and validation features."""

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parent / "quality"))

import agent_coordination  # noqa: E402
import index_migrations  # noqa: E402
import multi_repo  # noqa: E402
import semantic  # noqa: E402
from check_workflows import ROOT as QROOT  # noqa: E402
from intel_core import candidate_files  # noqa: E402


class ExtraFeatureTests(unittest.TestCase):
    def test_semantic_index_builds_and_returns_labelled_results(self):
        semantic.build()
        results = semantic.search("model router selection", 10)
        self.assertTrue(results)
        self.assertTrue(all(r["source"] == "semantic" for r in results))
        self.assertTrue(all("score" in r and "path" in r for r in results))

    def test_multi_repo_registry_labels_external_sources(self):
        registry = multi_repo.registry()
        names = {r["name"] for r in registry["repositories"]}
        self.assertIn("iam-core", names)
        self.assertIn("iam-research-notes", names)
        self.assertTrue(all(n["authority"] == "external" for n in multi_repo.external_notes()))

    def test_agent_claims_are_persistent_and_releasable(self):
        topic = "unit-test-topic"
        agent_coordination.release(topic, "unit-test")
        result = agent_coordination.claim(topic, "unit-test", ["AGENTS.md"], 60)
        self.assertTrue(result["ok"])
        self.assertEqual(agent_coordination.status(topic)["claim"]["agent"], "unit-test")
        blocked = agent_coordination.claim(topic, "other-agent", [], 60)
        self.assertFalse(blocked["ok"])
        self.assertTrue(agent_coordination.release(topic, "unit-test")["ok"])

    def test_index_schema_check_is_ok_after_apply(self):
        index_migrations.apply()
        self.assertTrue(index_migrations.check()["ok"])

    def test_snapshots_are_non_empty(self):
        from watch_index import snapshot
        self.assertTrue(snapshot())

    def test_workflow_validator_reports_no_problems(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, str(QROOT / "tools" / "quality" / "check_workflows.py"), "--json"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue('"ok": true' in result.stdout)

    def test_embedding_adapter_is_local_only(self):
        import embeddings
        settings = embeddings.config()
        self.assertEqual(settings["provider"], "ollama")
        self.assertEqual(settings["base_url"], "http://localhost:11434")
        self.assertEqual(settings["model"], "nomic-embed-text")

    def test_external_knowledge_sync_round_trip(self):
        import external_sync
        collected = external_sync.collect()
        self.assertTrue(collected["sources"])
        external_sync.INDEX_PATH.write_text(
            __import__("json").dumps(collected), encoding="utf-8"
        )
        self.assertTrue(external_sync.verify()["ok"])

    def test_os_watcher_available(self):
        import watchdog.observers  # noqa: F401
        import watch_index
        self.assertTrue(callable(watch_index.watch_os))

    def test_local_ci_runner_executes_a_subset(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, str(QROOT / "tools" / "quality" / "run_local_ci.py"),
             "--only", "workflows"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(__import__("embeddings").is_available(), "no local Ollama model")
    def test_neural_rerank_labels_results_and_falls_back_cleanly(self):
        import neural
        results = neural.rerank(
            "model router",
            [{"path": "backend/app/api/routes/modelrouter.py", "line": 0,
              "text": "model router", "score": 2.0}],
            5,
        )
        self.assertTrue(results)
        self.assertEqual(results[0]["source"], "neural_rerank")
        self.assertIn("neural_cosine", results[0])


if __name__ == "__main__":
    unittest.main()
