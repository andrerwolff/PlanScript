import unittest
import textwrap
from datetime import date, timedelta
from pathlib import Path

from planscript.model.project import Project
from planscript.exceptions import   ValidationError, ParseError
from planscript.engine.scheduler import Scheduler
from planscript.engine.reporter import ReportBuilder
from planscript.engine.analyzer import Analyzer
from planscript.parser.parser import Parser

class ValidatePerformance(unittest.TestCase):
    def setUp(self):
        file = Path("examples/Full_Plan.plan")
        text = file.read_text(encoding="utf-8")
        parser = Parser()
        self.project = parser.parse(text)

    def test_reporter(self):
        self.project.schedule = Scheduler().calculate(self.project)
        report = ReportBuilder(self.project).build()
        str = report.render_text()
        print(str)
