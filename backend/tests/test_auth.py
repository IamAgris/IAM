"""Unit tests for API auth policy, credential hashing and rate limiting."""

import unittest

from app.core.auth_policy import has_scope, normalize_path, required_scope
from app.core.rate_limit import RateLimiter
from app.services.auth_service import generate_key, hash_key


class PolicyTests(unittest.TestCase):
    def test_public_paths(self):
        self.assertIsNone(required_scope("/health"))
        self.assertIsNone(required_scope("/"))
        self.assertIsNone(required_scope("/api/v1/docs"))
        self.assertIsNone(required_scope("/api/v1/access/requests"))
        self.assertIsNone(required_scope("/api/v1/creator/gateway/decision"))

    def test_protected_paths(self):
        self.assertEqual(required_scope("/api/v1/skill-forge/skills"), "admin")
        self.assertEqual(required_scope("/api/v1/skillforge/skills"), "admin")
        self.assertEqual(required_scope("/api/v1/cybersecurity/tasks"), "admin")
        self.assertEqual(required_scope("/api/v1/creator/requests"), "admin")
        self.assertEqual(required_scope("/api/v1/conversations/"), "user")
        self.assertEqual(required_scope("/api/v1/autonomy/goals"), "operator")

    def test_trailing_slash_normalised(self):
        self.assertEqual(normalize_path("/api/v1/skills/"), "/api/v1/skills")
        self.assertEqual(required_scope("/api/v1/skills/"), "user")

    def test_scope_hierarchy(self):
        self.assertTrue(has_scope("admin", "user"))
        self.assertTrue(has_scope("operator", "operator"))
        self.assertTrue(has_scope("service", "operator"))
        self.assertFalse(has_scope("service", "admin"))
        self.assertFalse(has_scope("user", "operator"))
        self.assertFalse(has_scope("service", "admin"))


class CredentialTests(unittest.TestCase):
    def test_hash_is_stable_sha256(self):
        key = "iam_test_key"
        self.assertEqual(len(hash_key(key)), 64)
        self.assertEqual(hash_key(key), hash_key(key))
        self.assertNotEqual(hash_key(key), hash_key("iam_other"))

    def test_generated_keys_are_unique(self):
        keys = {generate_key() for _ in range(50)}
        self.assertEqual(len(keys), 50)
        self.assertTrue(all(k.startswith("iam_") for k in keys))


class RateLimitTests(unittest.TestCase):
    def test_blocks_after_limit_and_reports_retry(self):
        limiter = RateLimiter(default_limit=2)
        self.assertTrue(limiter.check("client")[0])
        self.assertTrue(limiter.check("client")[0])
        allowed, retry = limiter.check("client")
        self.assertFalse(allowed)
        self.assertGreaterEqual(retry, 1)

    def test_keys_are_independent(self):
        limiter = RateLimiter(default_limit=1)
        self.assertTrue(limiter.check("a")[0])
        self.assertTrue(limiter.check("b")[0])
        self.assertFalse(limiter.check("a")[0])

    def test_reset(self):
        limiter = RateLimiter(default_limit=1)
        limiter.check("a")
        limiter.reset("a")
        self.assertTrue(limiter.check("a")[0])


if __name__ == "__main__":
    unittest.main()
