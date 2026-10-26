import contextlib
import io
import os
import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch

from .batch import main
from .sandbox import fresh_source, host_environment


class BatchFailureTests(unittest.TestCase):
    def test_low_disk_stops_before_starting_a_lab(self):
        with tempfile.TemporaryDirectory() as directory:
            args=["batch","--clients","claude","--cases","network","--geometries","48","--workers","3"]
            with patch("sys.argv",args),patch("website.capture.labs.batch.RESULTS",Path(directory)),patch("website.capture.labs.batch.shutil.disk_usage",return_value=SimpleNamespace(free=10 * 1024**3)),patch("website.capture.labs.batch.capture") as capture,contextlib.redirect_stdout(io.StringIO()) as output:
                with self.assertRaises(SystemExit):main()
            capture.assert_not_called()
            self.assertIn("preserve the 8 GiB reserve",output.getvalue())

    def test_first_capture_creates_results_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            results=Path(directory)/"labs"
            args=["batch","--clients","claude","--cases","network","--geometries","48","--workers","1"]
            with patch("sys.argv",args),patch("website.capture.labs.batch.RESULTS",results),patch("website.capture.labs.batch.shutil.disk_usage",return_value=SimpleNamespace(free=20 * 1024**3)),patch("website.capture.labs.batch.capture",side_effect=RuntimeError("pilot rejected")):
                with self.assertRaises(SystemExit):main()
            self.assertTrue(results.is_dir())

    def test_standalone_website_uses_explicit_source_without_copying_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/"source";target=root/"candidate"
            (source/"hercules/core").mkdir(parents=True)
            (source/"docker").mkdir()
            (source/"hercules/core/tool_catalog.py").write_text("# fixture\n")
            (source/"Dockerfile").write_text("FROM scratch\n")
            (source/".env").write_text("SECRET=not-for-capture\n")
            with patch.dict(os.environ,{"HERCULES_CAPTURE_SOURCE":str(source)}):
                fresh_source(target)
                environment=host_environment(target,root/"workspace","fixture-net")
            self.assertTrue((target/"Dockerfile").is_file())
            self.assertFalse((target/".env").exists())
            self.assertEqual(environment["HERCULES_INSTALLED_CAPABILITIES"],"all")
            self.assertEqual(environment["HERCULES_WORDLIST_ROOT"],str((Path(__file__).resolve().parents[3]/"wordlists").resolve()))

    def test_shared_startup_failures_stop_the_queue_before_more_labs_start(self):
        with tempfile.TemporaryDirectory() as directory:
            args=["batch","--clients","claude","--cases","network","services","--workers","1"]
            with patch("sys.argv",args),patch("website.capture.labs.batch.RESULTS",Path(directory)),patch("website.capture.labs.batch.shutil.disk_usage",return_value=SimpleNamespace(free=20 * 1024**3)),patch("website.capture.labs.batch.capture",side_effect=RuntimeError("Encoder startup rejected")) as capture,contextlib.redirect_stdout(io.StringIO()) as output:
                with self.assertRaises(SystemExit):main()
            self.assertEqual(capture.call_count,3)
            self.assertIn("Three consecutive capture failures",output.getvalue())


if __name__=="__main__":unittest.main()
