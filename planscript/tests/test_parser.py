import unittest
import textwrap
from datetime import timedelta, date
from decimal import Decimal

from planscript.engine.parser import Parser, ParseError
from planscript.model.project import ValidationError
from planscript.model.constraint import ConstraintType
from planscript.model.dependency import DependencyType

class ValidatePlan(unittest.TestCase):
    def setUp(self):
            self.parser = Parser()

    def test_duplicate_task_id(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 Design 5d
        task 1.1 Construction 10d
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("duplicate task ID '1.1'", str(context.exception))

    def test_duplicate_start(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-01
            start: 2026-02-01
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("duplicate start declaration", str(context.exception))

    def test_duplicate_finish(self):
        text = textwrap.dedent("""\
        project: Test
            finish: 2026-01-01
            finish: 2026-02-01
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("duplicate finish declaration", str(context.exception))

    def test_duplicate_calendar(self):
        text = textwrap.dedent("""\
        project: Test
            calendar: standard
            calendar: custom
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("duplicate calendar declaration", str(context.exception))

    def test_start_after_finish(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-12-31
            finish: 2026-01-01
        """)

        with self.assertRaises(ValidationError) as context:
            self.parser.parse(text)

        self.assertIn("start date cannot be after finish date", str(context.exception))

    def test_negative_duration(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 Design -5d
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("cannot be negative or signed", str(context.exception))

    def test_negative_lag_is_valid(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 Design 5d
        task 1.2 Construction 10d
            depends 1.1 FS -2d
        """)

        project = self.parser.parse(text)

        dependency = project.dependencies[0]

        self.assertEqual(
            dependency.lag,
            timedelta(days=-2)
        )

    def test_invalid_duration(self):
        with self.assertRaises(ParseError):
            self.parser.parse_duration("abc")

    def test_invalid_dependency_type(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 A 5d
        task 1.2 B 5d
            depends 1.1 XX
        """)

        with self.assertRaises(ParseError):
            self.parser.parse(text)

    def test_duplicate_dependency(self):
        text = textwrap.dedent("""\
        project: Test

        task 1.1 A 5d
        task 1.2 B 5d
            depends 1.1 SS 2d
            depends 1.1 SS 2d
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn(
            "duplicate dependency",
            str(context.exception)
        )

    def test_duplicate_dependency_2(self):
        text = textwrap.dedent("""\
        project: Test

        task 1.1 A 5d
        task 1.2 B 5d
            depends 1.1 SS 4d
            depends 1.1 SS 2d
            depends 1.1 FS 4d
            depends 1.1 SS -4d
            depends 1.1 SS 4w
            depends 1.1 FS 4h
        """)

        project = self.parser.parse(text)

        self.assertEqual(len(project.dependencies), 6)

    def test_self_dependency(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 A 5d
            depends 1.1
        """)

        with self.assertRaises(ParseError):
            self.parser.parse(text)


class TestParser(unittest.TestCase):
    def setUp(self):
        self.parser = Parser()

    # ---------------------------------------------------------
    # Complete Plan
    # ---------------------------------------------------------
    def test_complete_plan(self):
        text = textwrap.dedent("""\
        ; Example PlanScript project

        project: Water Treatment Plant

            - client: City of Denver
            - project_manager: Andre

            calendar: Standard
            start: 2026-01-05
            finish: 2026-12-31

        task 1 Design
            - discipline: Engineering

        task 1.1 Survey 5d
        task 1.2 Preliminary Design 10d
            depends 1.1 3d
        task 1.3 Final Design 5d
            depends 1.2 FS 2w

        task 2 Construction 
        task 2.1 Mobilization 0d
            depends 1.3 FS -1d
        task 2.2 Construction 25d
            depends 2.1 SS +2d
        task 2.3 Substantial Completion 0d
            depends 2.2 0d
        """)

        project = self.parser.parse(text)

        self.assertEqual(project.name, "Water Treatment Plant")
        self.assertEqual(project.calendar, "Standard")
        self.assertEqual(project.start_date, date(2026,1,5))
        self.assertEqual(project.finish_date, date(2026,12,31))

        self.assertEqual(len(project.tasks), 8)
        self.assertEqual(len(project.dependencies), 5)

        self.assertEqual(project.tasks["1.1"].duration, timedelta(days=5))
        self.assertEqual(project.tasks["2.1"].duration, timedelta(0))

        d1 = project.get_incoming_dependencies(project.tasks["1.2"])[0]
        d2 = project.get_incoming_dependencies(project.tasks["1.3"])[0]
        d3 = project.get_incoming_dependencies(project.tasks["2.1"])[0]
        d4 = project.get_incoming_dependencies(project.tasks["2.2"])[0]
        d5 = project.get_incoming_dependencies(project.tasks["2.3"])[0]
        self.assertEqual(d1.lag, timedelta(days = 3))
        self.assertEqual(d1.dep_type.value, "FS")
        self.assertEqual(d2.lag, timedelta(weeks = 2))
        self.assertEqual(d3.lag, timedelta(days = -1))
        self.assertEqual(d4.lag, timedelta(days = 2))
        self.assertEqual(d4.dep_type.value, "SS")
        self.assertEqual(d5.lag, timedelta(0))
        self.assertEqual(d5.dep_type.value, "FS")

    def test_forward_dependency_reference(self):
        text = textwrap.dedent("""\
        project: Test

        task 1.2 Construction 10d

            depends 1.1 

        task 1.1 Design 5d
        """)

        project = self.parser.parse(text)

        dependency = project.dependencies[0]

        self.assertEqual(dependency.predecessor.number, "1.1")
        self.assertEqual(dependency.successor.number, "1.2")

    

              
    # ---------------------------------------------------------
    # Project
    # ---------------------------------------------------------

    def test_project(self):
        text = textwrap.dedent("""\
        project: Test Project
        """)

        project = self.parser.parse(text)

        self.assertEqual(project.name, "Test Project")

    def test_missing_project(self):
        text = textwrap.dedent("""\
        task 1.1 Mobilization 2d
        """)

        with self.assertRaises(ParseError):
            self.parser.parse(text)

    def test_multiple_projects(self):
        text = textwrap.dedent("""\
        project: Project One
        project: Project Two
        """)

        with self.assertRaises(ParseError):
            self.parser.parse(text)

    # ---------------------------------------------------------
    # Tasks
    # ---------------------------------------------------------

    def test_task_with_duration(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 Mobilization 5d
        """)

        project = self.parser.parse(text)

        self.assertIn("1.1", project.tasks)

        task = project.tasks["1.1"]

        self.assertEqual(task.number, "1.1")
        self.assertEqual(task.name, "Mobilization")
        self.assertEqual(task.duration, timedelta(days=5))

    def test_task_0_duration_is_milestone(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 Notice to Proceed 0d
        """)

        project = self.parser.parse(text)

        self.assertIn("1.1", project.tasks)
    
        task = project.tasks["1.1"]

        self.assertEqual(task.duration, timedelta(0))
        self.assertTrue(project.tasks["1.1"].is_milestone)

    def test_task_without_duration_is_summary(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 Notice to Proceed
        task 1.1.1 Meeting 0d
        """)

        project = self.parser.parse(text)

        self.assertIn("1.1", project.tasks)
    
        task = project.tasks["1.1"]

        self.assertEqual(task.duration, None)

    def test_hierarchical_task_id(self):
        text = textwrap.dedent("""\
        project: Test
        task 1 Site Work
        task 1.1 Mobilization
        task 1.1.1 Survey 1d
        task 2 Closeout 3d
        """)

        project = self.parser.parse(text)

        self.assertEqual(
            list(project.tasks.keys()),
            ["1", "1.1", "1.1.1", "2"]
        )

    def test_task_description_can_contain_spaces(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 Prepare construction documents 10d
        """)

        project = self.parser.parse(text)

        self.assertEqual(
            project.tasks["1.1"].name,
            "Prepare construction documents"
        )

    # ---------------------------------------------------------
    # Durations
    # ---------------------------------------------------------

    def test_duration_days(self):
        self.assertEqual(
            self.parser.parse_duration("5d"),
            (timedelta(days=5),"d")
        )

    def test_duration_hours(self):
        self.assertEqual(
            self.parser.parse_duration("8h"),
            (timedelta(hours=8),"h")
        )

    def test_duration_weeks(self):
        self.assertEqual(
            self.parser.parse_duration("2w"),
            (timedelta(weeks=2),"w")
        )

    def test_duration_decimal(self):
        self.assertEqual(
            self.parser.parse_duration("2.5d"),
            (timedelta(days=2.5),"d")
        )

    def test_duration_without_unit_defaults_to_days(self):
        self.assertEqual(
            self.parser.parse_duration("5"),
            (timedelta(days=5),"d")
        )

    def test_duration_months(self):
        self.assertEqual(
            self.parser.parse_duration("2m"),
            (timedelta(days=60), "m")
        )

    def test_duration_is_case_insensitive(self):
        self.assertEqual(
            self.parser.parse_duration("5D"),
            (timedelta(days=5),"d")
        )

    # ---------------------------------------------------------
    # Project attributes
    # ---------------------------------------------------------

    def test_calendar(self):
        text = textwrap.dedent("""\
        project: Test
            calendar: Standard
        """)

        project = self.parser.parse(text)

        self.assertEqual(project.calendar, "Standard")
        self.assertIsInstance(project.calendar, str)
        self.assertEqual(project.calendars, {})

    def test_start(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-01
        """)

        project = self.parser.parse(text)

        self.assertEqual(project.start_date, date(2026,1,1))

    def test_finish(self):
        text = textwrap.dedent("""\
        project: Test
            finish: 2026-12-31
        """)

        project = self.parser.parse(text)

        self.assertEqual(project.finish_date, date(2026,12,31))

    # ---------------------------------------------------------
    # Metadata
    # ---------------------------------------------------------

    def test_project_metadata(self):
        text = textwrap.dedent("""\
        project: Test
            - client: City of Denver
            - phase: Design
        """)

        project = self.parser.parse(text)

        self.assertEqual(project.metadata["client"], "City of Denver")
        self.assertEqual(project.metadata["phase"], "Design")

    def test_task_metadata(self):
        text = textwrap.dedent("""\
        project: Test

        task 1.1 Design 5d
            - discipline: Civil
            - responsible: Andre
        """)

        project = self.parser.parse(text)

        task = project.tasks["1.1"]

        self.assertEqual(task.metadata["discipline"], "Civil")
        self.assertEqual(task.metadata["responsible"], "Andre")

    def test_metadata_attaches_to_previous_task(self):
        text = textwrap.dedent("""\
        project: Test
            - risk_level: High

        task 1.1 Design 5d
            - discipline: Civil

        task 1.2 Construction 10d
            - discipline: Construction
        """)

        project = self.parser.parse(text)

        self.assertEqual(
            project.metadata["risk_level"], 
            "High"
        )

        self.assertEqual(
            project.tasks["1.1"].metadata["discipline"],
            "Civil"
        )

        self.assertEqual(
            project.tasks["1.2"].metadata["discipline"],
            "Construction"
        )

    # ---------------------------------------------------------
    # Comments / blank lines
    # ---------------------------------------------------------

    def test_comments_and_blank_lines(self):
        text = textwrap.dedent("""\
        ; This is a comment

        project: Test

        ; Another comment
        task 1.1 Design 5d


        task 1.2 Construction 10d
        """)

        project = self.parser.parse(text)

        self.assertEqual(len(project.tasks), 2)

    # ---------------------------------------------------------
    # Dependencies - normal syntax
    # ---------------------------------------------------------

    def test_dependency_default_fs(self):
        text = textwrap.dedent("""\
        project: Test

        task 1.1 Design 5d
        task 1.2 Construction 10d

            depends 1.1
        """)

        project = self.parser.parse(text)

        dependencies = project.dependencies

        self.assertEqual(len(dependencies), 1)

        dependency = dependencies[0]

        self.assertEqual(dependency.predecessor.number, "1.1")
        self.assertEqual(dependency.successor.number, "1.2")
        self.assertEqual(dependency.dep_type.value, "FS")
        self.assertEqual(dependency.lag, timedelta(0))
        self.assertEqual(dependency.lag_unit, "d")

    def test_dependency_explicit_fs(self):
        text = textwrap.dedent("""\
        project: Test

        task 1.1 Design 5d
        task 1.2 Construction 10d

            depends 1.1 FS
        """)

        project = self.parser.parse(text)

        dependency = project.dependencies[0]

        self.assertEqual(dependency.dep_type.value, "FS")
        self.assertEqual(dependency.lag_unit, "d")

    def test_lag_without_type_defaults_to_fs(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 A 5d
        task 1.2 B 5d
            depends 1.1 2d
        """)

        project = self.parser.parse(text)

        dependency = project.dependencies[0]

        self.assertEqual(dependency.dep_type.value, "FS")
        self.assertEqual(dependency.lag, timedelta(days=2))
        self.assertEqual(dependency.lag_unit, "d")

    def test_negative_lag_without_type_defaults_to_fs(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 A 5d
        task 1.2 B 5d
            depends 1.1 -2d
        """)

        project = self.parser.parse(text)

        dependency = project.dependencies[0]

        self.assertEqual(dependency.dep_type.value, "FS")
        self.assertEqual(dependency.lag, timedelta(days=-2))
        self.assertEqual(dependency.lag_unit, "d")

    # ---------------------------------------------------------
    # Dependency types
    # ---------------------------------------------------------

    def test_dependency_ss(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 A 5d
        task 1.2 B 10d
            depends 1.1 SS
        """)

        project = self.parser.parse(text)

        self.assertEqual(
            project.dependencies[0].dep_type.value,
            "SS"
        )
        self.assertEqual(project.dependencies[0].lag_unit, "d")

    def test_dependency_ff(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 A 5d
        task 1.2 B 10d
            depends 1.1 FF
        """)

        project = self.parser.parse(text)

        self.assertEqual(
            project.dependencies[0].dep_type.value,
            "FF"
        )

    def test_dependency_sf(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 A 5d
        task 1.2 B 10d
            depends 1.1 SF
        """)

        project = self.parser.parse(text)

        self.assertEqual(
            project.dependencies[0].dep_type.value,
            "SF"
        )

    # ---------------------------------------------------------
    # Dependency lag
    # ---------------------------------------------------------

    def test_positive_lag(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 A 5d
        task 1.2 B 10d
            depends 1.1 FS +2d
        """)

        project = self.parser.parse(text)

        dependency = project.dependencies[0]

        self.assertEqual(
            dependency.lag,
            timedelta(days=2)
        )
        self.assertEqual(dependency.lag_unit, "d")

    def test_negative_lag(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 A 5d
        task 1.2 B 10d
            depends 1.1 FS -2d
        """)

        project = self.parser.parse(text)

        dependency = project.dependencies[0]

        self.assertEqual(
            dependency.lag,
            timedelta(days=-2)
        )
        self.assertEqual(dependency.lag_unit, "d")

    def test_lag_without_sign_defaults_to_positive(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 A 5d
        task 1.2 B 5d
            depends 1.1 FS 2w
        """)

        project = self.parser.parse(text)

        self.assertEqual(
            project.dependencies[0].lag,
            timedelta(weeks=2)
        )
        self.assertEqual(
            project.dependencies[0].lag_unit,
            "w"
        )

    # ---------------------------------------------------------
    # Dependency errors
    # ---------------------------------------------------------

    def test_unknown_predecessor(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.2 Construction 10d
            depends 1.1
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("Line 3", str(context.exception))
        self.assertIn("unknown predecessor task '1.1'", str(context.exception))

    def test_invalid_dependency_relationship(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 Design 5d
        task 1.2 Construction 10d
            depends nonsense -2w
        """)

        with self.assertRaises(ParseError):
            self.parser.parse(text)

    def test_compact_dependency_type_is_rejected(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 A 5d
        task 1.2 B 5d
            depends 1.1FS
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn(
            "dependency type must be separated",
            str(context.exception)
        )

    # ---------------------------------------------------------
    # General syntax errors
    # ---------------------------------------------------------

    def test_unrecognized_syntax(self):
        text = textwrap.dedent("""\
        project: Test
        this is not valid syntax
        """)

        with self.assertRaises(ParseError):
            self.parser.parse(text)

    def test_metadata_without_entry(self):
        text = textwrap.dedent("""\
        project: Test
            - client: Denver
        """)

        # Depending on intended syntax, this currently attaches
        # metadata to the project. If that's intentional, remove
        # this test.
        project = self.parser.parse(text)

        self.assertEqual(
            project.metadata["client"],
            "Denver"
        )


class TestConstraints(unittest.TestCase):
    def setUp(self):
        self.parser = Parser()

    # ---------------------------------------------------------
    # Constraint parsing
    # ---------------------------------------------------------

    def test_constraint_attaches_to_preceding_task(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
            constraint SNET 2026-01-15
        """)

        project = self.parser.parse(text)

        self.assertEqual(len(project.constraints), 1)

        constraint = project.constraints[0]
        self.assertIs(constraint.task, project.tasks["1.1"])
        self.assertEqual(constraint.con_type, ConstraintType.START_NO_EARLIER_THAN)
        self.assertEqual(constraint.con_date, date(2026, 1, 15))

    def test_all_constraint_type_codes(self):
        codes = {
            "SNET": ConstraintType.START_NO_EARLIER_THAN,
            "SNLT": ConstraintType.START_NO_LATER_THAN,
            "FNET": ConstraintType.FINISH_NO_EARLIER_THAN,
            "FNLT": ConstraintType.FINISH_NO_LATER_THAN,
            "MSON": ConstraintType.MANDATORY_START,
            "MFON": ConstraintType.MANDATORY_FINISH,
        }

        for code, expected in codes.items():
            with self.subTest(code=code):
                text = textwrap.dedent(f"""\
                project: Test
                    start: 2026-01-05
                task 1.1 Design 5d
                    constraint {code} 2026-01-15
                """)

                project = self.parser.parse(text)

                self.assertEqual(project.constraints[0].con_type, expected)

    def test_multiple_constraints_on_one_task(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
            constraint SNET 2026-01-10
            constraint FNLT 2026-01-20
        """)

        project = self.parser.parse(text)

        self.assertEqual(len(project.constraints), 2)
        self.assertEqual(
            project.constraints[0].con_type,
            ConstraintType.START_NO_EARLIER_THAN
        )
        self.assertEqual(
            project.constraints[1].con_type,
            ConstraintType.FINISH_NO_LATER_THAN
        )

    def test_constraint_may_follow_dependency_on_same_task(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 A 5d
        task 1.2 B 10d
            depends 1.1
            constraint FNLT 2026-02-02
        """)

        project = self.parser.parse(text)

        self.assertEqual(len(project.dependencies), 1)
        self.assertEqual(len(project.constraints), 1)
        self.assertIs(project.constraints[0].task, project.tasks["1.2"])

    def test_constraint_on_milestone(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Gate 0d
            constraint MFON 2026-01-30
        """)

        project = self.parser.parse(text)

        self.assertEqual(len(project.constraints), 1)
        self.assertIs(project.constraints[0].task, project.tasks["1.1"])
        self.assertEqual(
            project.constraints[0].con_type,
            ConstraintType.MANDATORY_FINISH
        )

    # ---------------------------------------------------------
    # Constraint errors
    # ---------------------------------------------------------

    def test_invalid_constraint_type(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
            constraint ASAP 2026-01-15
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("Line 4", str(context.exception))
        self.assertIn("invalid constraint type 'ASAP'", str(context.exception))

    def test_lowercase_constraint_type_is_rejected(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
            constraint snet 2026-01-15
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("Line 4", str(context.exception))
        self.assertIn("invalid constraint syntax", str(context.exception))

    def test_invalid_constraint_date(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
            constraint SNET 2026-13-45
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("Line 4", str(context.exception))
        self.assertIn("invalid date '2026-13-45'", str(context.exception))

    def test_malformed_constraint_date_is_rejected(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
            constraint SNET 2026-1-5
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("invalid constraint syntax", str(context.exception))

    def test_unindented_constraint_is_rejected(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
        constraint SNET 2026-01-15
        """)

        with self.assertRaises(ParseError):
            self.parser.parse(text)

    def test_constraint_without_preceding_task(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
            constraint SNET 2026-01-15
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("Line 3", str(context.exception))
        self.assertIn("constraint has no preceding task", str(context.exception))

    def test_constraint_after_invoice_is_rejected(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
        2026-02-01 invoice $100
            1.1 $100
            constraint SNET 2026-01-15
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("Line 6", str(context.exception))
        self.assertIn("constraint has no preceding task", str(context.exception))

    def test_constraint_on_summary_task_fails_validation(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1 Design
            constraint SNET 2026-01-15
        task 1.1 Layout 5d
        """)

        with self.assertRaises(ValidationError) as context:
            self.parser.parse(text)

        self.assertIn(
            "Summary task '1' cannot have a constraint",
            str(context.exception)
        )

    def test_constraint_requires_project_start_date(self):
        text = textwrap.dedent("""\
        project: Test
        task 1.1 Design 5d
            constraint SNET 2026-01-15
        """)

        with self.assertRaises(ValidationError) as context:
            self.parser.parse(text)

        self.assertIn("without a start date", str(context.exception))


class TestFallThroughErrors(unittest.TestCase):
    """Indented lines that look like budgets/constraints but fail their
    patterns must get a specific error, not a tracking fall-through."""

    def setUp(self):
        self.parser = Parser()

    def test_budget_with_three_decimal_places(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
            budget $10.555
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("Line 4", str(context.exception))
        self.assertIn("invalid budget syntax", str(context.exception))

    def test_budget_weight_without_percent_sign(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
            budget 40
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("Line 4", str(context.exception))
        self.assertIn("invalid budget syntax", str(context.exception))

    def test_budget_with_no_arguments(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
            budget
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("invalid budget syntax", str(context.exception))

    def test_valid_budgets_still_parse(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1 Summary
            budget $100
        task 1.1 Design 5d
            budget $10.5
        task 1.2 Build 5d
            budget $89.5
        """)

        project = self.parser.parse(text)

        self.assertEqual(project.tasks["1.1"].budget, Decimal("10.5"))

    def test_valid_budget_weight_still_parses(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1 Summary
            budget $100
        task 1.1 Design 5d
            budget 100%
        """)

        project = self.parser.parse(text)

        self.assertEqual(project.tasks["1.1"].budget_wt, Decimal("100"))


class TestTrackingDateGroups(unittest.TestCase):
    """A date-only tracking line opens a group that must contain at least
    one entry."""

    def setUp(self):
        self.parser = Parser()

    def test_empty_group_at_end_of_file(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
        2026-09-26
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("Line 4", str(context.exception))
        self.assertIn("tracking date has no entries", str(context.exception))

    def test_empty_group_before_next_date_header(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
        2026-09-26
        2026-09-27
            1.1 start
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("Line 4", str(context.exception))
        self.assertIn("tracking date has no entries", str(context.exception))

    def test_empty_group_before_single_line_event(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
        2026-09-26
        2026-09-27 1.1 start
        """)

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("Line 4", str(context.exception))
        self.assertIn("tracking date has no entries", str(context.exception))

    def test_group_with_entries_parses(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
        2026-09-26
            1.1 start
            1.1 complete
        """)

        project = self.parser.parse(text)

        self.assertEqual(len(project.tracker.task_events), 2)

    def test_sequential_groups_parse(self):
        text = textwrap.dedent("""\
        project: Test
            start: 2026-01-05
        task 1.1 Design 5d
        2026-09-26
            1.1 start
        2026-09-27
            1.1 complete
        """)

        project = self.parser.parse(text)

        self.assertEqual(len(project.tracker.task_events), 2)


if __name__ == "__main__":
    unittest.main()