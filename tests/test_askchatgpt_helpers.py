"""Behavior tests for AskChatGPT's dependency-free helper functions."""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPERS_PATH = ROOT / "askchatgpt" / "helpers.py"


def _load_helpers():
    """Load helpers.py directly so askchatgpt/__init__.py does not import Red."""

    spec = importlib.util.spec_from_file_location(
        "askchatgpt_helpers_under_test", HELPERS_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {HELPERS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MentionStrippingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.helpers = _load_helpers()

    def test_removes_both_discord_bot_mention_forms(self) -> None:
        result = self.helpers.strip_bot_mentions(
            "<@42> explain this, then ask <@!42>", 42
        )
        self.assertNotIn("<@42>", result)
        self.assertNotIn("<@!42>", result)
        self.assertEqual("explain this, then ask", " ".join(result.split()))

    def test_preserves_mentions_of_other_people(self) -> None:
        result = self.helpers.strip_bot_mentions("<@42> ask <@99> please", 42)
        self.assertIn("<@99>", result)
        self.assertNotIn("<@42>", result)

    def test_does_not_remove_id_prefix_collisions(self) -> None:
        result = self.helpers.strip_bot_mentions("<@42> keep <@420>", 42)
        self.assertEqual("keep <@420>", " ".join(result.split()))


class ProfileNormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.helpers = _load_helpers()

    def test_collapses_spacing_and_control_whitespace(self) -> None:
        result = self.helpers.normalize_profile(
            "  Likes   cats\nPronouns: they/them\t  "
        )
        self.assertEqual("Likes cats Pronouns: they/them", result)

    def test_strips_non_whitespace_control_characters(self) -> None:
        result = self.helpers.normalize_profile("Builder\x00\x07  Moderator")
        self.assertNotIn("\x00", result)
        self.assertNotIn("\x07", result)
        self.assertEqual("Builder Moderator", " ".join(result.split()))

    def test_does_not_apply_the_callers_length_limit(self) -> None:
        profile = "x" * 301
        self.assertEqual(profile, self.helpers.normalize_profile(profile))


class TruncationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.helpers = _load_helpers()

    def test_leaves_short_text_unchanged(self) -> None:
        self.assertEqual("short", self.helpers.truncate_text("short", 10))

    def test_truncated_text_never_exceeds_limit(self) -> None:
        result = self.helpers.truncate_text("a fairly long message", 10)
        self.assertLessEqual(len(result), 10)
        self.assertTrue(result.endswith("..."))

    def test_tiny_and_zero_limits_are_safe(self) -> None:
        self.assertEqual("", self.helpers.truncate_text("text", 0))
        self.assertLessEqual(len(self.helpers.truncate_text("text", 1)), 1)


class SafetyIdentifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.helpers = _load_helpers()

    def test_is_exact_hmac_sha256_of_the_discord_id(self) -> None:
        user_id = 123456789012345678
        salt = "server-private-salt"
        expected = hmac.new(
            salt.encode("utf-8"),
            str(user_id).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(expected, self.helpers.safety_identifier(user_id, salt))

    def test_is_stable_and_does_not_contain_the_raw_id(self) -> None:
        user_id = 123456789012345678
        first = self.helpers.safety_identifier(user_id, "salt")
        second = self.helpers.safety_identifier(user_id, "salt")
        self.assertEqual(first, second)
        self.assertNotIn(str(user_id), first)
        self.assertRegex(first, r"^[0-9a-f]{64}$")

    def test_changes_with_user_or_salt(self) -> None:
        baseline = self.helpers.safety_identifier(1, "salt-a")
        self.assertNotEqual(baseline, self.helpers.safety_identifier(2, "salt-a"))
        self.assertNotEqual(baseline, self.helpers.safety_identifier(1, "salt-b"))


if __name__ == "__main__":
    unittest.main()
