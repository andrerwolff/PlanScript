import unittest
from datetime import timedelta, date

from planscript.serializer.plan_serializer import PlanSerializer
from planscript.parser.parser import Parser, ParseError
from planscript.model.dependency import DependencyType

class ValidateSerializer(unittest.TestCase):
    def setUp(self):
            self.parser = Parser()
            self.serializer = PlanSerializer()

    def test_serializer_plan(self):
        text = """project: Water Treatment Plant

start: 2026-01-05
finish: 2026-12-31

task 1 Design 20d
task 1.1 Survey 5d
task 1.2 Preliminary Design 10d
task 1.3 Final Design 5d
task 2.1 Mobilization 0d
task 2.2 Construction 25d
task 2.3 Substantial Completion 0d

dependency 1.1 > 1.2 3
dependency 1.2 > 1.3 2w
dependency 1.3 > 2.1 -1
dependency 2.1 > 2.2 SS +2
dependency 2.2 > 2.3 0"""

        project = self.parser.parse(text)
        serial = self.serializer.serialize(project)
        print(serial)
        self.assertEqual(text, serial)