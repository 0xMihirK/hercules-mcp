import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .batch import main


class BatchFailureTests(unittest.TestCase):
    def test_shared_startup_failures_stop_the_queue_before_more_labs_start(self):
        with tempfile.TemporaryDirectory() as directory:
            args=["batch","--clients","claude","--cases","network","services","--workers","1"]
            with patch("sys.argv",args),patch("website.capture.labs.batch.RESULTS",Path(directory)),patch("website.capture.labs.batch.capture",side_effect=RuntimeError("Encoder startup rejected")) as capture,contextlib.redirect_stdout(io.StringIO()) as output:
                with self.assertRaises(SystemExit):main()
            self.assertEqual(capture.call_count,3)
            self.assertIn("Three consecutive capture failures",output.getvalue())


if __name__=="__main__":unittest.main()
