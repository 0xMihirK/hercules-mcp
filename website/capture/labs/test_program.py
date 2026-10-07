"""Regression tests for capture validation boundaries, not fabricated demos."""
import unittest
from .program import Program, payload


class CaptureValidationTests(unittest.TestCase):
    def test_unexpected_evidence_does_not_advance(self):
        program = Program("network")
        program.next()
        with self.assertRaises(ValueError):
            program.accept({"structuredContent":{"status":"error","session_id":"missing","error":"startup failed"}})
        self.assertEqual(program.index,0)
        self.assertIsNotNone(program.pending)

    def test_missing_expected_branch_stops(self):
        program = Program("forensics")
        program.next()
        with self.assertRaises(ValueError):
            program.accept({"content":[{"type":"text","text":"{}"}]})
        self.assertEqual(program.verified,[])

    def test_cannot_issue_another_step_before_result(self):
        program = Program("recovery")
        program.next()
        with self.assertRaises(RuntimeError):
            program.next()

    def test_dynamic_job_requires_observed_id(self):
        program = Program("recovery")
        program.index = 3
        with self.assertRaises(ValueError):
            program.next()

    def test_structured_result_remains_authoritative(self):
        result = {"structuredContent":{"status":"error"},"content":[{"type":"text","text":"{\"status\":\"success\"}"}]}
        self.assertEqual(payload(result)["status"],"error")

    def test_all_investigations_have_bounded_call_counts(self):
        from .cases import CASES
        for name in CASES:
            with self.subTest(name=name):
                count = len(Program(name).steps)
                self.assertGreaterEqual(count,8)
                self.assertLessEqual(count,16)

    def test_codex_title_request_cannot_consume_pending_result(self):
        from .provider import LabProvider
        class Provider(LabProvider):
            client="codex"
            program=Program("network")
        Provider.program.next()
        handler=object.__new__(Provider)
        title,call=handler.advance({"input":[{"role":"user","content":[{"text":"Generate a concise, single-line task title"}]}]})
        self.assertEqual(title,"Investigate the local lab")
        self.assertIsNone(call)
        self.assertEqual(Provider.program.index,0)
        self.assertIsNotNone(Provider.program.pending)

    def test_codex_yield_waits_before_result_validation(self):
        from .provider import LabProvider
        class Provider(LabProvider):
            client="codex"
            initialized=True
            inventory_sent=True
            program=Program("network")
        Provider.program.next()
        handler=object.__new__(Provider)
        body={"input":[{"type":"additional_tools","tools":[{"tools":[{"type":"custom","name":"exec"}]}]},
                       {"type":"custom_tool_call_output","output":"Script running with cell ID capture-123"}]}
        _,call=handler.advance(body)
        self.assertEqual(call[0],"wait")
        self.assertEqual(call[1]["cell_id"],"capture-123")
        self.assertEqual(Provider.program.index,0)

    def test_observed_excerpt_is_not_a_future_action(self):
        from .publish import result_excerpt
        result=result_excerpt({"status":"success","parsed":{"ports":[{"state":"open","portid":8000}]}})
        self.assertIn("open",result)
        self.assertNotIn("I will",result)


if __name__ == "__main__":
    unittest.main()
