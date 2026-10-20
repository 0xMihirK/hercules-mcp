import unittest
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PIL import Image

from .publish import call_phase, capture_interval, investigation_transcript, recorder_fingerprint_matches, report_preview, stage_artifact, validate_browser_artifacts
from .cases import CASES
from .program import Program


class FindingPhaseTests(unittest.TestCase):
    def test_completion_keeps_investigation_results_separate_from_housekeeping(self):
        for scenario,case in CASES.items():
            with self.subTest(scenario=scenario):
                operations=Program(scenario).steps
                findings=[operation for i,operation in enumerate(operations) if call_phase(scenario,i)=="investigation"]
                self.assertEqual(len(findings),len(case["steps"]))
                self.assertNotIn("system_stop_container",[step["tool"] for step in findings])
                self.assertFalse(any(step["arguments"].get("path","").startswith("reports/") for step in findings))
                self.assertEqual(call_phase(scenario,len(operations)-1),"reporting")

    def test_report_preview_retains_final_verification_and_scope_with_original_bytes_unchanged(self):
        report="# CTF\n\nModel decisions are scripted.\n\n## Verified observations\n\n### 3. discovery\nearlier discovery\n\n### 4. decoy\ndecoy_match: false\n\n### 5. verification\nchecksum_match: true\n\n## Scope and limitations\nOnly the fixture was tested.\n"
        original=report.encode()
        preview=report_preview(report)
        self.assertIn("selected excerpt",preview);self.assertNotIn("earlier discovery",preview)
        self.assertIn("decoy_match: false",preview);self.assertIn("checksum_match: true",preview)
        self.assertIn("Only the fixture was tested.",preview);self.assertIn("Model decisions are scripted.",preview)
        self.assertEqual(report.encode(),original)
        self.assertEqual(report_preview("# Short report\n\nVerified result."),"# Short report\n\nVerified result.")


class SharedEvidenceTests(unittest.TestCase):
    def test_identical_large_outputs_share_unchanged_bytes_and_distinct_outputs_do_not(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);stage=root/"stage"
            first=root/"first.bin";second=root/"second.bin";different=root/"different.bin"
            original=b"retained diagnostics\r\n\x1b[31m"*50000
            first.write_bytes(original);second.write_bytes(original);different.write_bytes(original+b"distinct")
            a=stage_artifact(first,stage,Path("logs/first.bin"),"capture-120")
            b=stage_artifact(second,stage,Path("logs/second.bin"),"capture-48")
            c=stage_artifact(different,stage,Path("logs/third.bin"),"capture-80")
            self.assertEqual(a,b);self.assertNotEqual(a,c);self.assertEqual(a.read_bytes(),original)
            self.assertEqual(c.read_bytes(),original+b"distinct")
            self.assertEqual(first.read_bytes(),original)

    def test_small_artifacts_keep_their_capture_paths(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);file=root/"report.md";file.write_bytes(b"Verified report\r\n")
            target=stage_artifact(file,root/"stage",Path("reports/report.md"),"capture-120")
            self.assertEqual(target,root/"stage/evidence/capture-120/reports/report.md")
            self.assertEqual(target.read_bytes(),file.read_bytes())


class CaptureIntervalTests(unittest.TestCase):
    def test_retained_original_timestamps_cover_the_native_session(self):
        with TemporaryDirectory() as directory:
            master=Path(directory)/"master.mkv";master.write_bytes(b"timestamp validation fixture")
            with patch("website.capture.labs.publish.subprocess.check_output",return_value="98.000\n100.000\n220.100\n"):
                interval=capture_interval(master,100,120)
            self.assertTrue(interval["covered"])
            self.assertEqual(interval["firstFrameAt"],-2)
            self.assertAlmostEqual(interval["lastFrameAt"],120.1)

    def test_older_bundles_cannot_bypass_late_or_incomplete_capture_checks(self):
        for packets in ("100.940\n220.1\n","98.000\n219.900\n"):
            with self.subTest(packets=packets),TemporaryDirectory() as directory:
                master=Path(directory)/"master.mkv";master.write_bytes(b"timestamp validation fixture")
                with patch("website.capture.labs.publish.subprocess.check_output",return_value=packets),self.assertRaises(ValueError):
                    capture_interval(master,100,120)


class TranscriptTests(unittest.TestCase):
    def test_transcript_preserves_observed_data_and_labels_scripted_text(self):
        status={"client":"claude","version":"2.1.289","scenario":"network","mcpCalls":[
            {"name":"workspace_read_file","requestedAt":4.1234,"completedAt":5.6789,
             "arguments":{"path":"evidence/é.txt"}}]}
        validation={"verified":[{"step":{"observation":"Review the retained evidence."},
            "data":{"content":"Observed finding: café\r\nnext line","exit_code":0}}]}
        text=investigation_transcript(status,validation)
        self.assertIn("Scripted model: Review the retained evidence.",text)
        self.assertIn("[4.123s → 5.679s] workspace_read_file",text)
        self.assertIn('"path": "evidence/é.txt"',text)
        self.assertIn('"content": "Observed finding: café\\r\\nnext line"',text)
        self.assertIn("Actual Hercules result:",text)
        self.assertIn("Native menus, task UI and animation remain in the untouched ANSI",text)
        self.assertNotIn("\x1b",text)


class BrowserEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary=TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace=Path(self.temporary.name)
        self.file=self.workspace/"browser/review/artifacts/page.png"
        self.file.parent.mkdir(parents=True)
        Image.new("RGB",(4,3),"#d87950").save(self.file)
        self.data={"path":"/opt/workspace/browser/review/artifacts/page.png","bytes":self.file.stat().st_size,"width":4,"height":3}

    def validate(self,**changes):
        validate_browser_artifacts(self.workspace,{"verified":[{"step":{"tool":"browser_screenshot"},"data":{**self.data,**changes}}]})

    def test_observed_screenshot_exists_with_native_format_and_dimensions(self):
        self.validate()

    def test_missing_and_foreign_screenshot_paths_are_rejected(self):
        for path in ("/tmp/page.png","/opt/workspace/../page.png","/opt/workspace/browser/missing.png"):
            with self.subTest(path=path),self.assertRaises(ValueError):self.validate(path=path)

    def test_reported_bytes_and_dimensions_must_match(self):
        for changes in ({"bytes":self.data["bytes"]+1},{"width":5},{"height":4}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.validate(**changes)

    def test_a_misnamed_screenshot_is_rejected_without_reencoding(self):
        Image.new("RGB",(4,3),"#d87950").save(self.file,format="JPEG")
        with self.assertRaises(ValueError):self.validate(bytes=self.file.stat().st_size)



class RecorderProvenanceTests(unittest.TestCase):
    def test_git_newlines_preserve_verified_source_identity_but_semantic_edits_do_not(self):
        raw=b"def capture():\r\n    return 'native'\n"
        fingerprint=hashlib.sha256(raw).hexdigest();normalized=raw.replace(b"\r\n",b"\n")
        equivalents={fingerprint:hashlib.sha256(normalized).hexdigest()}
        with TemporaryDirectory() as directory,patch("website.capture.labs.publish.RECORDER_NEWLINE_EQUIVALENTS",equivalents):
            path=Path(directory)/"record.py";path.write_bytes(raw)
            self.assertTrue(recorder_fingerprint_matches(path,fingerprint))
            path.write_bytes(normalized);self.assertTrue(recorder_fingerprint_matches(path,fingerprint))
            path.write_bytes(normalized.replace(b"native",b"modified"))
            self.assertFalse(recorder_fingerprint_matches(path,fingerprint))
            self.assertFalse(recorder_fingerprint_matches(path,"unverified source hash"))


class RecordingArchiveTests(unittest.TestCase):
    def test_native_bytes_and_timestamps_round_trip_without_newline_conversion(self):
        from .publish import archive_recording
        import zipfile
        data=b'{"version":2,"timestamp":1791750799}\n[0.065,"o","\\u001b[31m"]\n'+b'\r\n\x1b[0m'+"café".encode()
        with TemporaryDirectory() as directory:
            root=Path(directory);source=root/"native.cast";source.write_bytes(data)
            metadata=archive_recording(source,root)
            with zipfile.ZipFile(root/metadata["file"]) as archive:
                self.assertEqual(archive.namelist(),[source.name])
                self.assertEqual(archive.read(source.name),data)
            self.assertEqual(source.read_bytes(),data)
            self.assertEqual(metadata["payloadSha256"],hashlib.sha256(data).hexdigest())
            self.assertEqual(metadata["payloadBytes"],len(data))

    def test_repeated_native_redraws_compress_and_pack_deterministically(self):
        from .publish import archive_recording
        with TemporaryDirectory() as directory:
            root=Path(directory);source=root/"native.cast";source.write_bytes(b'\x1b[2J\r\n' * 10000)
            first=archive_recording(source,root);second=archive_recording(source,root)
            self.assertEqual(first,second)
            self.assertLess((root/first["file"]).stat().st_size,source.stat().st_size/2)


if __name__=="__main__":unittest.main()
