import unittest
from datetime import timedelta, date

from planscript.parser.parser import Parser, ParseError
from planscript.model.dependency import DependencyType

class ValidatePlan(unittest.TestCase):
    def setUp(self):
            self.parser = Parser()

    def test_duplicate_task_id(self):
        text = """
        project: Test
        task 1.1 Design 5d
        task 1.1 Construction 10d
        """

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("duplicate task ID '1.1'", str(context.exception))

    def test_duplicate_start(self):
        text = """
        project: Test
        start: 2026-01-01
        start: 2026-02-01
        """

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("duplicate start declaration", str(context.exception))

    def test_duplicate_finish(self):
            text = """
            project: Test
            finish: 2026-01-01
            finish: 2026-02-01
            """
    
            with self.assertRaises(ParseError) as context:
                self.parser.parse(text)
    
            self.assertIn("duplicate finish declaration", str(context.exception))

    def test_duplicate_calendar(self):
            text = """
            project: Test
            calendar: standard
            calendar: custom
            """
    
            with self.assertRaises(ParseError) as context:
                self.parser.parse(text)
    
            self.assertIn("duplicate calendar declaration", str(context.exception))

    def test_start_after_finish(self):
        text = """
        project: Test
        start: 2026-12-31
        finish: 2026-01-01
        """

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("start date cannot be after finish date", str(context.exception))

    def test_negative_duration(self):
        text = """
        project: Test
        task 1.1 Design -5d
        """

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("cannot be negative or signed", str(context.exception))

    def test_negative_lag_is_valid(self):
        text = """
        project: Test
        task 1.1 Design 5d
        task 1.2 Construction 10d
        dependency 1.1 > 1.2 FS -2d
        """

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
        text = """
        project: Test
        task 1.1 A 5d
        task 1.2 B 5d
        dependency 1.1 > 1.2 XX
        """

        with self.assertRaises(ParseError):
            self.parser.parse(text)

    def test_duplicate_dependency(self):
        text = """
        project: Test

        task 1.1 A 5d
        task 1.2 B 5d

        dependency 1.1 > 1.2
        dependency 1.1 > 1.2
        """

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn(
            "duplicate dependency",
            str(context.exception)
        )

    def test_duplicate_dependency_2(self):
        text = """
        project: Test

        task 1.1 A 5d
        task 1.2 B 5d

        dependency 1.1 > 1.2 SS2
        dependency 1.1 > 1.2 SS2
        """

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn(
            "duplicate dependency",
            str(context.exception)
        )

    def test_duplicate_dependency_3(self):
        text = """
        project: Test

        task 1.1 A 5d
        task 1.2 B 5d

        dependency 1.1 > 1.2 SS4
        dependency 1.1 > 1.2 SS2
        dependency 1.1 > 1.2 FS4
        dependency 1.1 > 1.2 SS -4d
        dependency 1.1 > 1.2 SS 4w
        dependency 1.1 > 1.2 FS 4h
        """

        project = self.parser.parse(text)

        self.assertEqual(len(project.dependencies), 6)

    def test_self_dependency(self):
        text = """
        project: Test
        task 1.1 A 5d

        dependency 1.1 > 1.1
        """

        with self.assertRaises(ParseError):
            self.parser.parse(text)


class TestParser(unittest.TestCase):
    def setUp(self):
        self.parser = Parser()

    # ---------------------------------------------------------
    # Complete Plan
    # ---------------------------------------------------------
    def test_complete_plan(self):
        text = """
        # Example PlanScript project

        project: Water Treatment Plant

        - client: City of Denver
        - project_manager: Andre

        calendar: Standard
        start: 2026-01-05
        finish: 2026-12-31

        task 1 Design 20d
        - discipline: Engineering

        task 1.1 Survey 5d
        task 1.2 Preliminary Design 10d
        task 1.3 Final Design 5d

        task 2 Construction 
        task 2.1 Mobilization 0d
        task 2.2 Construction 25d
        task 2.3 Substantial Completion 0d

        dependency 1.1 > 1.2 3
        dependency 1.2 > 1.3 FS 2w
        dependency 1.3 > 2.1 FS-1
        dependency 2.1 > 2.2 SS+2d
        dependency 2.2 > 2.3 0
        """

        project = self.parser.parse(text)

        self.assertEqual(project.name, "Water Treatment Plant")
        self.assertEqual(project.calendar, "Standard")
        self.assertEqual(project.start_date, date(2026,1,5))
        self.assertEqual(project.finish_date, date(2026,12,31))

        self.assertEqual(len(project.tasks), 7)
        self.assertEqual(len(project.dependencies), 5)

        self.assertEqual(project.tasks["1.1"].duration, timedelta(days=5))
        self.assertEqual(project.tasks["2.1"].duration, timedelta(0))

        d1 = project.get_incoming_dependencies(project.tasks["1.2"])[0]
        d2 = project.get_incoming_dependencies(project.tasks["1.3"])[0]
        d3 = project.get_incoming_dependencies(project.tasks["2.1"])[0]
        d4 = project.get_incoming_dependencies(project.tasks["2.2"])[0]
        d5 = project.get_incoming_dependencies(project.tasks["2.3"])[0]
        self.assertEqual(d1.lag, timedelta(days = 3))
        self.assertEqual(d1.dependency_type.value, "FS")
        self.assertEqual(d2.lag, timedelta(weeks = 2))
        self.assertEqual(d3.lag, timedelta(days = -1))
        self.assertEqual(d4.lag, timedelta(days = 2))
        self.assertEqual(d4.dependency_type.value, "SS")
        self.assertEqual(d5.lag, timedelta(0))
        self.assertEqual(d5.dependency_type.value, "FS")

    def test_forward_dependency_reference(self):
        text = """
        project: Test

        task 1.2 Construction 10d

        dependency 1.1 > 1.2

        task 1.1 Design 5d
        """

        project = self.parser.parse(text)

        dependency = project.dependencies[0]

        self.assertEqual(dependency.predecessor.number, "1.1")
        self.assertEqual(dependency.successor.number, "1.2")

    

              
    # ---------------------------------------------------------
    # Project
    # ---------------------------------------------------------

    def test_project(self):
        text = """
        project: Test Project
        """

        project = self.parser.parse(text)

        self.assertEqual(project.name, "Test Project")

    def test_missing_project(self):
        text = """
        task 1.1 Mobilization 2d
        """

        with self.assertRaises(ParseError):
            self.parser.parse(text)

    def test_multiple_projects(self):
        text = """
        project: Project One
        project: Project Two
        """

        with self.assertRaises(ParseError):
            self.parser.parse(text)

    # ---------------------------------------------------------
    # Tasks
    # ---------------------------------------------------------

    def test_task_with_duration(self):
        text = """
        project: Test
        task 1.1 Mobilization 5d
        """

        project = self.parser.parse(text)

        self.assertIn("1.1", project.tasks)

        task = project.tasks["1.1"]

        self.assertEqual(task.number, "1.1")
        self.assertEqual(task.name, "Mobilization")
        self.assertEqual(task.duration, timedelta(days=5))

    def test_task_without_duration_is_summary(self):
        # TODO - update this once summary items are stored somewhere
        text = """
        project: Test
        task 1.1 Notice to Proceed
        """

        project = self.parser.parse(text)

        #self.assertIn("1.1", project.tasks)
    
        #task = project.tasks["1.1"]

        #self.assertEqual(task.duration, timedelta(0))
        self.assertEqual({},project.tasks)

    def test_hierarchical_task_id(self):
        text = """
        project: Test
        task 1 Site Work 5d
        task 1.1 Mobilization 2d
        task 1.1.1 Survey 1d
        task 2 Closeout 3d
        """

        project = self.parser.parse(text)

        self.assertEqual(
            list(project.tasks.keys()),
            ["1", "1.1", "1.1.1", "2"]
        )

    def test_task_description_can_contain_spaces(self):
        text = """
        project: Test
        task 1.1 Prepare construction documents 10d
        """

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
            timedelta(days=60)
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
        text = """
        project: Test
        calendar: Standard
        """

        project = self.parser.parse(text)

        self.assertEqual(project.calendar, "Standard")

    def test_start(self):
        text = """
        project: Test
        start: 2026-01-01
        """

        project = self.parser.parse(text)

        self.assertEqual(project.start_date, date(2026,1,1))

    def test_finish(self):
        text = """
        project: Test
        finish: 2026-12-31
        """

        project = self.parser.parse(text)

        self.assertEqual(project.finish_date, date(2026,12,31))

    # ---------------------------------------------------------
    # Metadata
    # ---------------------------------------------------------

    def test_project_metadata(self):
        text = """
        project: Test
        - client: City of Denver
        - phase: Design
        """

        project = self.parser.parse(text)

        self.assertEqual(project.metadata["client"], "City of Denver")
        self.assertEqual(project.metadata["phase"], "Design")

    def test_task_metadata(self):
        text = """
        project: Test

        task 1.1 Design 5d
        - discipline: Civil
        - responsible: Andre
        """

        project = self.parser.parse(text)

        task = project.tasks["1.1"]

        self.assertEqual(task.metadata["discipline"], "Civil")
        self.assertEqual(task.metadata["responsible"], "Andre")

    def test_metadata_attaches_to_previous_task(self):
        text = """
        project: Test

        task 1.1 Design 5d
        - discipline: Civil

        task 1.2 Construction 10d
        - discipline: Construction
        """

        project = self.parser.parse(text)

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
        text = """
        # This is a comment

        project: Test

        # Another comment
        task 1.1 Design 5d


        task 1.2 Construction 10d
        """

        project = self.parser.parse(text)

        self.assertEqual(len(project.tasks), 2)

    # ---------------------------------------------------------
    # Dependencies - normal syntax
    # ---------------------------------------------------------

    def test_dependency_default_fs(self):
        text = """
        project: Test

        task 1.1 Design 5d
        task 1.2 Construction 10d

        dependency 1.1 > 1.2
        """

        project = self.parser.parse(text)

        dependencies = project.dependencies

        self.assertEqual(len(dependencies), 1)

        dependency = dependencies[0]

        self.assertEqual(dependency.predecessor.number, "1.1")
        self.assertEqual(dependency.successor.number, "1.2")
        self.assertEqual(dependency.dependency_type.value, "FS")
        self.assertEqual(dependency.lag, timedelta(0))
        self.assertEqual(dependency.lag_unit, "d")

    def test_dependency_explicit_fs(self):
        text = """
        project: Test

        task 1.1 Design 5d
        task 1.2 Construction 10d

        dependency 1.1 > 1.2 FS
        """

        project = self.parser.parse(text)

        dependency = project.dependencies[0]

        self.assertEqual(dependency.dependency_type.value, "FS")
        self.assertEqual(dependency.lag_unit, "d")

    def test_lag_without_type_defaults_to_fs(self):
        text = """
        project: Test
        task 1.1 A 5d
        task 1.2 B 5d
        dependency 1.1 > 1.2 2d
        """

        project = self.parser.parse(text)

        dependency = project.dependencies[0]

        self.assertEqual(dependency.dependency_type.value, "FS")
        self.assertEqual(dependency.lag, timedelta(days=2))
        self.assertEqual(dependency.lag_unit, "d")

    def test_negative_lag_without_type_defaults_to_fs(self):
        text = """
        project: Test
        task 1.1 A 5d
        task 1.2 B 5d
        dependency 1.1 > 1.2 -2d
        """

        project = self.parser.parse(text)

        dependency = project.dependencies[0]

        self.assertEqual(dependency.dependency_type.value, "FS")
        self.assertEqual(dependency.lag, timedelta(days=-2))
        self.assertEqual(dependency.lag_unit, "d")

    # ---------------------------------------------------------
    # Dependency types
    # ---------------------------------------------------------

    def test_dependency_ss(self):
        text = """
        project: Test
        task 1.1 A 5d
        task 1.2 B 10d
        dependency 1.1 > 1.2 SS
        """

        project = self.parser.parse(text)

        self.assertEqual(
            project.dependencies[0].dependency_type.value,
            "SS"
        )
        self.assertEqual(project.dependencies[0].lag_unit, "d")

    def test_dependency_ff(self):
        text = """
        project: Test
        task 1.1 A 5d
        task 1.2 B 10d
        dependency 1.1 > 1.2 FF
        """

        project = self.parser.parse(text)

        self.assertEqual(
            project.dependencies[0].dependency_type.value,
            "FF"
        )

    def test_dependency_sf(self):
        text = """
        project: Test
        task 1.1 A 5d
        task 1.2 B 10d
        dependency 1.1 > 1.2 SF
        """

        project = self.parser.parse(text)

        self.assertEqual(
            project.dependencies[0].dependency_type.value,
            "SF"
        )

    # ---------------------------------------------------------
    # Dependency lag
    # ---------------------------------------------------------

    def test_positive_lag(self):
        text = """
        project: Test
        task 1.1 A 5d
        task 1.2 B 10d
        dependency 1.1 > 1.2 FS +2d
        """

        project = self.parser.parse(text)

        dependency = project.dependencies[0]

        self.assertEqual(
            dependency.lag,
            timedelta(days=2)
        )
        self.assertEqual(dependency.lag_unit, "d")

    def test_negative_lag(self):
        text = """
        project: Test
        task 1.1 A 5d
        task 1.2 B 10d
        dependency 1.1 > 1.2 FS -2d
        """

        project = self.parser.parse(text)

        dependency = project.dependencies[0]

        self.assertEqual(
            dependency.lag,
            timedelta(days=-2)
        )
        self.assertEqual(dependency.lag_unit, "d")

    def test_lag_without_sign_defaults_to_positive(self):
        text = """
        project: Test
        task 1.1 A 5d
        task 1.2 B 5d
        dependency 1.1 > 1.2 FS 2w
        """

        project = self.parser.parse(text)

        self.assertEqual(
            project.dependencies[0].lag,
            timedelta(weeks=2)
        )
        self.assertEqual(
            project.dependencies[0].lag_unit,
            "w"
        )
        

    def test_compact_type_lag_defaults_positive(self):
        text = """
        project: Test
        task 1.1 A 5d
        task 1.2 B 5d
        dependency 1.1 > 1.2 FS2
        """

        project = self.parser.parse(text)

        dependency = project.dependencies[0]

        self.assertEqual(dependency.dependency_type.value, "FS")
        self.assertEqual(dependency.lag, timedelta(days=2))
        self.assertEqual(dependency.lag_unit, "d")
        

    def test_compact_type_positive_lag(self):
        text = """
        project: Test
        task 1.1 A 5d
        task 1.2 B 5d
        dependency 1.1 > 1.2 FS+2
        """

        project = self.parser.parse(text)

        self.assertEqual(
            project.dependencies[0].lag,
            timedelta(days=2)
        )

    def test_compact_type_negative_lag(self):
        text = """
        project: Test
        task 1.1 A 5d
        task 1.2 B 5d
        dependency 1.1 > 1.2 FS-2d
        """

        project = self.parser.parse(text)

        self.assertEqual(
            project.dependencies[0].lag,
            timedelta(days=-2)
        )


    # ---------------------------------------------------------
    # Dependency errors
    # ---------------------------------------------------------

    def test_unknown_predecessor(self):
        text = """
        project: Test
        task 1.2 Construction 10d

        dependency 1.1 > 1.2
        """

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("Line 5", str(context.exception))
        self.assertIn("unknown predecessor task '1.1'", str(context.exception))


    def test_unknown_successor(self):
        text = """
        project: Test
        task 1.1 Design 5d

        dependency 1.1 > 1.2
        """

        with self.assertRaises(ParseError) as context:
            self.parser.parse(text)

        self.assertIn("unknown successor task '1.2'", str(context.exception))

    def test_invalid_dependency_relationship(self):
        text = """
        project: Test
        task 1.1 Design 5d
        task 1.2 Construction 10d

        dependency 1.1 > nonsense
        """

        with self.assertRaises(ParseError):
            self.parser.parse(text)

    def test_compact_dependency_type_is_rejected(self):
        text = """
        project: Test
        task 1.1 A 5d
        task 1.2 B 5d
        dependency 1.1 > 1.2FS
        """

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
        text = """
        project: Test
        this is not valid syntax
        """

        with self.assertRaises(ParseError):
            self.parser.parse(text)

    def test_metadata_without_entry(self):
        text = """
        project: Test
        - client: Denver
        """

        # Depending on intended syntax, this currently attaches
        # metadata to the project. If that's intentional, remove
        # this test.
        project = self.parser.parse(text)

        self.assertEqual(
            project.metadata["client"],
            "Denver"
        )


if __name__ == "__main__":
    unittest.main()