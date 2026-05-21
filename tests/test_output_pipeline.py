"""
Unit tests for the hercules/output/ pipeline modules.
"""

from hercules.output.sanitizer import strip_ansi, compress_whitespace, sanitize
from hercules.output.truncator import truncate_output
from hercules.output.banners import strip_known_banners
from hercules.output.filters import filter_hydra, filter_john, filter_amass
from hercules.output.msf_parser import parse_msf_console_output, parse_session_output


# ====================================================================
# sanitizer.py
# ====================================================================

class TestStripAnsi:
    def test_color_codes_removed(self):
        inp = "\x1b[31mRED\x1b[0m text"
        assert strip_ansi(inp) == "RED text"

    def test_broad_ansi_coverage(self):
        # cursor movement, bold, underline
        inp = "\x1b[2J\x1b[1mBOLD\x1b[4mUNDERLINE\x1b[0m"
        result = strip_ansi(inp)
        assert "\x1b" not in result
        assert "BOLD" in result
        assert "UNDERLINE" in result

    def test_no_ansi_passthrough(self):
        inp = "plain text with no escapes"
        assert strip_ansi(inp) == inp

    def test_preserves_nmap_xml(self):
        inp = '<?xml version="1.0"?><nmaprun scanner="nmap"><host><status state="up"/></host></nmaprun>'
        assert strip_ansi(inp) == inp


class TestCompressWhitespace:
    def test_collapses_blank_lines(self):
        inp = "line1\n\n\n\n\nline2"
        assert compress_whitespace(inp) == "line1\n\nline2"

    def test_two_newlines_preserved(self):
        inp = "line1\n\nline2"
        assert compress_whitespace(inp) == "line1\n\nline2"

    def test_single_newline_preserved(self):
        inp = "line1\nline2"
        assert compress_whitespace(inp) == "line1\nline2"


class TestSanitize:
    def test_combined(self):
        inp = "\x1b[32mGreen\x1b[0m\n\n\n\n\nEnd"
        result = sanitize(inp)
        assert "\x1b" not in result
        assert result == "Green\n\nEnd"


# ====================================================================
# truncator.py
# ====================================================================

class TestTruncateOutput:
    def test_under_limit_passthrough(self):
        text = "short text"
        result, was_truncated = truncate_output(text, max_chars=8000)
        assert result == text
        assert was_truncated is False

    def test_exactly_at_limit(self):
        text = "x" * 8000
        result, was_truncated = truncate_output(text, max_chars=8000)
        assert result == text
        assert was_truncated is False

    def test_head_tail_split(self):
        text = "A" * 10000 + "B" * 10000
        result, was_truncated = truncate_output(text, max_chars=8000, artifact_path="/test/log.txt")
        assert was_truncated is True
        assert result.startswith("A")
        assert result.endswith("B")
        assert "OUTPUT TRUNCATED" in result
        assert "/test/log.txt" in result

    def test_truncation_notice_contains_artifact(self):
        text = "x" * 20000
        result, _ = truncate_output(text, max_chars=8000, artifact_path="/opt/workspace/logs/nmap_001.txt")
        assert "/opt/workspace/logs/nmap_001.txt" in result


# ====================================================================
# banners.py
# ====================================================================

class TestStripKnownBanners:
    def test_sqlmap_banner_stripped(self):
        inp = "        ___\n       __H__\n       |_|\n[!] legal disclaimer: Usage of sqlmap...\nreal output here"
        result = strip_known_banners(inp, "sqlmap")
        assert "___" not in result
        assert "__H__" not in result
        assert "legal disclaimer" not in result
        assert "real output here" in result

    def test_hydra_banner_stripped(self):
        inp = "Hydra v9.5 (c) 2023 by van Hauser/THC\n(c) 2023 van Hauser blah\n[22][ssh] host: 10.0.0.1   login: admin   password: pass"
        result = strip_known_banners(inp, "hydra")
        assert "Hydra v9.5" not in result
        assert "van Hauser" not in result
        assert "login: admin" in result

    def test_unknown_tool_passthrough(self):
        inp = "some output"
        assert strip_known_banners(inp, "unknown_tool_xyz") == inp

    def test_hex_dump_survives(self):
        # Hex dumps should NOT be stripped even if they look weird
        inp = "00000000: 4865 6c6c 6f20 576f 726c 640a  Hello World.\n00000010: 5465 7374 696e 6720 3132 330a  Testing 123."
        result = strip_known_banners(inp, "sqlmap")
        assert result == inp

    def test_base64_survives(self):
        inp = "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSURYVENDQWtXZ0F3SUJB..."
        result = strip_known_banners(inp, "commix")
        assert result == inp


# ====================================================================
# filters.py
# ====================================================================

class TestFilterHydra:
    def test_keeps_credentials(self):
        inp = """Hydra v9.5 starting
[DATA] attacking ssh://10.0.0.1:22/
[22][ssh] host: 10.0.0.1   login: admin   password: pass123
[STATUS] 50 tries done
[22][ssh] host: 10.0.0.1   login: root   password: toor
1 of 1 target successfully completed, 2 valid passwords found"""
        result = filter_hydra(inp)
        assert "login: admin" in result
        assert "login: root" in result
        assert "successfully completed" in result
        assert "[STATUS]" not in result
        assert "[DATA]" not in result

    def test_empty_input(self):
        assert filter_hydra("") == ""


class TestFilterJohn:
    def test_keeps_cracked(self):
        inp = """Using default input encoding: UTF-8
Loaded 1 password hash (md5crypt)
Press 'q' or Ctrl-C to abort
admin:password123
1g 0:00:00:01 DONE 1/3 0.5000g/s 100.0p/s
Session completed, 1 cracked"""
        result = filter_john(inp)
        assert "admin:password123" in result
        assert "cracked" in result
        assert "Using default" not in result
        assert "Loaded" not in result
        assert "Press" not in result

    def test_empty_input(self):
        assert filter_john("") == ""


class TestFilterAmass:
    def test_keeps_domains(self):
        inp = """[INFO] Starting enumeration
Querying Crtsh
www.example.com
mail.example.com
api.example.com
OWASP Amass v4.0"""
        result = filter_amass(inp)
        assert "www.example.com" in result
        assert "mail.example.com" in result
        assert "[INFO]" not in result
        assert "Querying" not in result
        assert "OWASP" not in result


# ====================================================================
# msf_parser.py
# ====================================================================

class TestParseMsfConsoleOutput:
    def test_strips_prompts_and_banners(self):
        inp = """msf6 >
+ -- --=[ metasploit v6.3.40
=[ 2435 exploits - 1280 auxiliary
msf6 > search vsftpd
Matching Modules
================
exploit/unix/ftp/vsftpd_234_backdoor
msf6 >"""
        result = parse_msf_console_output(inp)
        assert "vsftpd_234_backdoor" in result
        assert "msf6 >" not in result
        assert "-- --=[ " not in result

    def test_empty_input(self):
        assert parse_msf_console_output("") == ""


class TestParseSessionOutput:
    def test_extracts_output(self):
        result = parse_session_output("root\n")
        assert result["output"] == "root"
        assert result["line_count"] == 1

    def test_empty(self):
        result = parse_session_output("")
        assert result["output"] == ""
        assert result["line_count"] == 0
