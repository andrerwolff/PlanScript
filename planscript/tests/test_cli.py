import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

from planscript import app
from planscript.exceptions import ValidationError
from planscript.parser.parser import Parser


ROOT = Path(__file__).resolve().parents[2]
VALID_PLAN = "project: Example\n    start: 2026-09-01\ntask 1 Work 2d\n"
CYCLE_PLAN = (
    "project: Cycle\n    start: 2026-09-01\n"
    "task 1 First 1d\n    depends 2\n"
    "task 2 Second 1d\n    depends 1\n"
)
TRACKED_PLAN = (
    "project: Example\n    start: 2026-09-01\n"
    "task 1 Work 2d\n"
    ";Tracking\n"
    "2026-09-01 1 start\n"
    "2026-09-03 1 complete\n"
)


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.file = Path(self.temp.name) / "example.plan"
        self.file.write_text(VALID_PLAN, encoding="utf-8")

    def run_cli(self, command, *options):
        return subprocess.run(
            [sys.executable, "-B", "-m", "planscript", command,
             str(self.file), *options],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            timeout=20,
        )

    def assert_failure(self, result, code, message):
        self.assertEqual(result.returncode, code, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn(message, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_agreed_cli_regressions(self):
        # Empty projects can be summarized without invoking the scheduler.
        self.file.write_text("project: Empty\n", encoding="utf-8")
        result = self.run_cli("summary")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("Tasks:         0", result.stdout)
        self.assertNotIn("Duration:", result.stdout)

        # Scheduling or budgeting an empty project is an expected failure,
        # not a traceback.
        for command in ("schedule", "status"):
            with self.subTest(command=command, case="empty"):
                self.assert_failure(self.run_cli(command), 1, "Scheduling error:")

        self.assert_failure(self.run_cli("budget"), 1, "Budgeting error:")

        # Shared validation rejects cycles for every command.
        self.file.write_text(CYCLE_PLAN, encoding="utf-8")
        for command in ("check", "summary", "schedule", "status", "budget"):
            with self.subTest(command=command, case="cycle"):
                self.assert_failure(
                    self.run_cli(command), 1,
                    "Validation error: Circular dependency detected",
                )

        self.file.write_text(VALID_PLAN, encoding="utf-8")
        self.assert_failure(
            self.run_cli("status", "--look-ahead", "-1"), 2,
            "must be a non-negative integer",
        )
        result = self.run_cli("status", "--look-ahead", "0",
                              "--as-of", "2026-09-01")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("Upcoming Deadlines (+0d)", result.stdout)

    def test_all_commands_succeed(self):
        for command in ("check", "summary", "schedule", "status", "budget"):
            with self.subTest(command=command):
                result = self.run_cli(command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(result.stdout)
                self.assertEqual(result.stderr, "")

    def test_file_and_parse_failures(self):
        for command in ("check", "summary", "schedule", "status", "budget"):
            for contents, message in (
                (b"not a plan", "Parse error:"),
                (b"\xff", "Error decoding"),
                (None, "Error: file not found:"),
            ):
                with self.subTest(command=command, message=message):
                    if contents is None:
                        self.file.unlink(missing_ok=True)
                    else:
                        self.file.write_bytes(contents)
                    self.assert_failure(self.run_cli(command), 1, message)

    def test_summary_does_not_schedule(self):
        with patch.object(app.Scheduler, "calculate") as calculate:
            with redirect_stdout(StringIO()):
                self.assertEqual(app.summary_command(self.file), 0)
        calculate.assert_not_called()

    def test_summary_reports_tracking_events(self):
        # Regression test for P0-1: summary crashed on tracked projects.
        self.file.write_text(TRACKED_PLAN, encoding="utf-8")
        result = self.run_cli("summary")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("Tracking events: 2", result.stdout)

        # An untracked project reports that tracking has not started.
        self.file.write_text(VALID_PLAN, encoding="utf-8")
        result = self.run_cli("summary")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("Tracking:      Not started", result.stdout)

    def test_model_validation_rejects_cycle(self):
        project = Parser().parse(VALID_PLAN + "task 2 More work 1d\n")
        project.add_dependency(project.tasks["1"], project.tasks["2"])
        project.add_dependency(project.tasks["2"], project.tasks["1"])
        with self.assertRaisesRegex(ValidationError, "Circular dependency"):
            project.validate()

    def test_loader_raises_without_printing(self):
        self.file.unlink()
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(FileNotFoundError):
                app.load_project(self.file)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_unexpected_errors_are_not_hidden(self):
        with patch.object(app.Scheduler, "calculate", side_effect=ValueError("bug")):
            with self.assertRaisesRegex(ValueError, "bug"):
                app.main(["schedule", str(self.file)])

    def test_dateless_project_is_calculated_only(self):
        self.file.write_text("project: NoDate\ntask 1 Work 2d\n", encoding="utf-8")

        result = self.run_cli("schedule", "--dates")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("Calculated schedule only", result.stdout)

        result = self.run_cli("schedule", "--gantt")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Gantt requires a project start date", result.stdout)

        self.assert_failure(self.run_cli("status"), 1, "Scheduling error:")


if __name__ == "__main__":
    unittest.main()
