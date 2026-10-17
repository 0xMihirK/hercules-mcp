"""Capture receipts must never claim unverified Docker cleanup."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from website.capture.labs.juice_shop import JuiceShopLab


class CaptureCleanupTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.lab = JuiceShopLab.__new__(JuiceShopLab)
        self.lab.process = None
        self.lab.session = None
        self.lab.owner = "test-owned"
        self.lab.network = "test-owned-net"
        self.lab.address = "172.30.78.10"
        self.lab.directory = self.directory
        self.lab.created = [("network", self.lab.network)]

    def test_unavailable_engine_cannot_claim_cleanup(self):
        result = SimpleNamespace(returncode=1, stdout="", stderr="Cannot connect to the Docker daemon")
        with patch("website.capture.labs.juice_shop.subprocess.run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "could not verify"):
                self.lab.close()
        self.assertFalse((self.directory / "transaction.json").exists())

    def test_cleanup_refuses_a_different_owner(self):
        result = SimpleNamespace(returncode=0, stderr="", stdout=json.dumps([
            {"Labels": {"hercules.capture.owner": "another-capture"}}
        ]))
        with patch("website.capture.labs.juice_shop.subprocess.run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "unowned resource"):
                self.lab.close()
        self.assertFalse((self.directory / "transaction.json").exists())

    def test_confirmed_missing_resource_is_already_clean(self):
        result = SimpleNamespace(returncode=1, stdout="", stderr="network test-owned-net not found")
        with patch("website.capture.labs.juice_shop.subprocess.run", return_value=result):
            self.lab.close()
        receipt = json.loads((self.directory / "transaction.json").read_text())
        self.assertTrue(receipt["cleanupComplete"])


if __name__ == "__main__":
    unittest.main()
