from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from argparse import ArgumentParser
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from argcomplete import CompletionFinder, shellcode

TEST_DIR = Path(__file__).resolve().parent
POWERSHELL = shutil.which("pwsh")


class TestPowerShell(unittest.TestCase):
    candidates = [
        "xplain",
        "x;Invoke-ArgcompleteMarker",
        "x`;Invoke-ArgcompleteMarker",
        "x`ncalc",
        "x$(Invoke-ArgcompleteMarker)",
        "x$env:PATH",
        "x with space ",
        "x'quote",
        'x"quote',
        "x\u2019;Invoke-ArgcompleteMarker",
        "x\u2018left\u2019right\u201alow\u201breversed",
        r"xC:\some path\end\\",
        "x|Invoke-ArgcompleteMarker",
        "x&Invoke-ArgcompleteMarker",
        "x(a)[b]{c}*?",
        "x,comma",
        "x\ttab",
        "x`",
        "x/",
        "x:",
        "x=",
    ]

    def test_raw_completion_values(self):
        # The shell must receive the original values, including literal trailing spaces.
        for quote in ("", "'", '"'):
            for candidate in self.candidates:
                with self.subTest(quote=quote, candidate=candidate):
                    parser = ArgumentParser(add_help=False)
                    parser.add_argument("--value", choices=[candidate])
                    command = "prog --value " + quote + "x"
                    environment = {
                        "_ARGCOMPLETE": "1",
                        "_ARGCOMPLETE_SHELL": "powershell",
                        "_ARGCOMPLETE_IFS": "\n",
                        "_ARGCOMPLETE_COMP_WORDBREAKS": ":",
                        "COMP_LINE": command,
                        "COMP_POINT": str(len(command)),
                    }
                    output = StringIO()
                    with patch.dict(os.environ, environment), self.assertRaises(SystemExit) as result:
                        CompletionFinder()(parser, output_stream=output, exit_method=sys.exit)
                    self.assertEqual(result.exception.code, 0)
                    self.assertEqual(output.getvalue(), candidate)

    def test_raw_path_completion(self):
        parser = ArgumentParser(add_help=False)
        parser.add_argument("--value", choices=["C:/some path/file"])
        command = "prog --value C:/some"
        environment = {
            "_ARGCOMPLETE": "1",
            "_ARGCOMPLETE_SHELL": "powershell",
            "_ARGCOMPLETE_IFS": "\n",
            "_ARGCOMPLETE_COMP_WORDBREAKS": ":",
            "COMP_LINE": command,
            "COMP_POINT": str(len(command)),
        }
        output = StringIO()
        with patch.dict(os.environ, environment), self.assertRaises(SystemExit) as result:
            CompletionFinder()(parser, output_stream=output, exit_method=sys.exit)
        self.assertEqual(result.exception.code, 0)
        self.assertEqual(output.getvalue(), "C:/some path/file")

    @unittest.skipUnless(POWERSHELL, "PowerShell (pwsh) is not installed")
    def test_native_quoting(self):
        self.check_native_quoting(self.candidates)

    @unittest.skipUnless(POWERSHELL, "PowerShell (pwsh) is not installed")
    def test_single_native_completion(self):
        self.check_native_quoting(["x with space "])

    def check_native_quoting(self, candidates):
        environment = os.environ.copy()
        environment.update(
            ARGCOMPLETE_TEST_PYTHON=sys.executable,
            ARGCOMPLETE_TEST_SCRIPT=str(TEST_DIR / "powershell_prog.py"),
            ARGCOMPLETE_TEST_CHOICES=json.dumps(candidates),
            PYTHONUTF8="0",
        )
        # Use the call operator with environment values, so paths are passed as data.
        registration = shellcode(
            [Path(sys.executable).name],
            shell="powershell",
            argcomplete_script="& $env:ARGCOMPLETE_TEST_PYTHON $env:ARGCOMPLETE_TEST_SCRIPT",
        )
        with TemporaryDirectory() as directory:
            registration_file = Path(directory) / "register.ps1"
            registration_file.write_text(registration, encoding="utf-8")
            result = subprocess.run(
                [
                    POWERSHELL,
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-File",
                    str(TEST_DIR / "powershell_quoting.ps1"),
                    str(registration_file),
                ],
                env=environment,
                check=False,
                capture_output=True,
                encoding="utf-8",
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        results = json.loads(result.stdout)
        self.assertEqual(len(results), 7 * len(candidates))
        for result in results:
            with self.subTest(input=result["Input"], display=result["Display"]):
                self.assertIn(result["Value"], candidates)
                expected_display = result["Value"]
                if result["Input"].startswith("--value="):
                    expected_display = "--value=" + expected_display
                self.assertEqual(result["Display"], expected_display)
                self.assertFalse(result["MarkerCalled"])


if __name__ == "__main__":
    unittest.main()
