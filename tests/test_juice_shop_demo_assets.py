"""Keep published Juice Shop evidence tied to its capture receipt."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "website" / "assets" / "demos"


class JuiceShopDemoAssetsTests(unittest.TestCase):
    def test_provenance_matches_every_published_asset(self):
        receipt = json.loads((DEMO / "provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["verifiedChallenges"], ["Login Admin", "Score Board"])
        self.assertEqual(receipt["challengeProgress"], "2/186")
        self.assertTrue(receipt["cleanupComplete"])
        for name, expected in receipt["assets"].items():
            payload = (DEMO / name).read_bytes()
            self.assertEqual(len(payload), expected["bytes"], name)
            self.assertEqual(hashlib.sha256(payload).hexdigest(), expected["sha256"], name)


if __name__ == "__main__":
    unittest.main()
