import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock

from .readiness import wait_first_frame


class CaptureReadinessTests(unittest.TestCase):
    def test_delayed_capture_cannot_release_the_agent_before_a_real_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            progress=Path(directory)/"progress.txt"
            progress.write_text("frame=0\nprogress=continue\n")
            release=threading.Event()
            def write_frame():
                release.wait()
                progress.write_text("frame=0\nprogress=continue\nframe=1\nprogress=continue\n")
            thread=threading.Thread(target=write_frame)
            thread.start()
            process=Mock(poll=Mock(return_value=None))
            timer=threading.Timer(.075,release.set)
            timer.start()
            try:
                self.assertEqual(wait_first_frame(process,progress,timeout=1),1)
                self.assertGreaterEqual(process.poll.call_count,2)
            finally:
                release.set();thread.join();timer.cancel()

    def test_zero_frames_and_stopped_encoder_never_release_the_agent(self):
        with tempfile.TemporaryDirectory() as directory:
            progress=Path(directory)/"progress.txt"
            progress.write_text("frame=0\nprogress=continue\n")
            with self.assertRaisesRegex(RuntimeError,"did not encode"):
                wait_first_frame(Mock(poll=Mock(return_value=None)),progress,timeout=.06)
            with self.assertRaisesRegex(RuntimeError,"stopped before"):
                wait_first_frame(Mock(poll=Mock(return_value=1)),progress,timeout=1)


if __name__=="__main__":unittest.main()
