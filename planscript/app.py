import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from planscript.model import Project
from planscript.exceptions import ParseError, SchedulingError, ValidationError, BudgetingError
from planscript.cli import display
from planscript.engine.budgeter import Budgeter
from planscript.engine.scheduler import Scheduler
from planscript.engine.reporter import ReportBuilder
from planscript.parser.parser import Parser
from planscript.cli.gantt import render_gantt


def main(argv=None) -> int:
    """Run a command, reporting expected failures on stderr with exit code 1.

    Successful commands return 0. argparse handles help (0) and usage errors
    (2). Unexpected programming errors are deliberately not caught.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "check":
            return check_command(args.file)
        if args.command == "summary":
            return summary_command(args.file)
        if args.command == "schedule":
            return schedule_command(args.file,
                                    calculated=args.calculated,
                                    dates=args.dates,
                                    gantt=args.gantt)
        if args.command == "status":
            return status_command(args.file,
                                  as_of=args.as_of,
                                  look_ahead=args.look_ahead)
        if args.command == "budget":
            return budget_command(args.file,
                                  as_of=args.as_of)



        
    except FileNotFoundError:
        print(f"Error: file not found: {args.file}", file=sys.stderr)
    except UnicodeDecodeError as e:
        print(f"Error decoding {args.file} as UTF-8: {e}", file=sys.stderr)
    except OSError as e:
        print(f"File error: {args.file}: {e}", file=sys.stderr)
    except ParseError as e:
        print(f"Parse error: {e}", file=sys.stderr)
    except ValidationError as e:
        print(f"Validation error: {e}", file=sys.stderr)
    except SchedulingError as e:
        print(f"Scheduling error: {e}", file=sys.stderr)
    except BudgetingError as e:
        print(f"Budgeting error: {e}", file=sys.stderr)
    else:
        parser.error(f"Unknown command: {args.command}")

    return 1


def load_project(file_path: Path) -> Project:
    """Parse and validate a UTF-8 file, returning a project or raising.

    This helper never prints; main handles expected failures for the CLI.
    """
    return Parser().parse(file_path.read_text(encoding="utf-8"))

def check_command(file_path: Path) -> int:
    """Validate a PlanScript file."""
    project = load_project(file_path)

    print(f"Project: {project.name}")
    print("Valid")

    return 0

def summary_command(file_path: Path) -> int:
    """Display a project summary."""
    project = load_project(file_path)
    display.view_project_summary(project)

    return 0

def schedule_command(file_path: Path, calculated:bool, dates:bool, gantt:bool) -> int:
    """Display project schedule"""
    project = load_project(file_path)
    project.schedule = Scheduler().calculate(project)
    if not calculated and not dates and not gantt:
        calculated = True
        dates = True
        gantt = True

        display.view_project_header(project)
        
    if calculated:
        display.view_schedule_calculated(project)
    if dates: 
        display.view_schedule_scheduled(project)
    if gantt:
        render_gantt(project)
        
    display.view_critical_paths(project)

    return 0

def status_command(file_path:Path, as_of:date, look_ahead:int) -> int:
    """Display project status."""
    project = load_project(file_path)
    project.schedule = Scheduler().calculate(project)
    report = ReportBuilder(project, as_of, timedelta(days=look_ahead)).build()
    print(report.render_text())

    return 0
    
def budget_command(file_path: Path, as_of:date) -> int:
    """Display project financials."""
    project = load_project(file_path)
    project.budget = Budgeter().calculate(project)
    display.view_project_header(project)
    display.view_budget(project)

    return 0

def non_negative_int(value: str) -> int:
    """Parse a non-negative CLI integer, including zero."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from None
    if number < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return number


def build_parser():
    parser = argparse.ArgumentParser(
        prog="planscript",
        description="PlanScript project planning and scheduling tool.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    check = subparsers.add_parser(
        "check",
        help="Validate a PlanScript file.",
    )
    check.add_argument("file", type=Path)

    summary = subparsers.add_parser(
        "summary",
        help="Display a project summary.",
    )
    summary.add_argument("file", type=Path)

    schedule = subparsers.add_parser(
        "schedule",
        help="Calculate and display the project schedule.",
    )
    schedule.add_argument("file", type=Path)
    schedule.add_argument(
        "-d","--dates",
        action="store_true",
        help="Display Scheduled dates."
    )
    schedule.add_argument(
        "-c","--calculated",
        action="store_true",
        help="Display calculated schedule values."
    )
    schedule.add_argument(
        "-g","--gantt",
        action="store_true",
        help="Display the project Gantt chart."
    )

    status = subparsers.add_parser(
        "status",
        help="Display current project status.",
    )
    status.add_argument("file", type=Path)
    status.add_argument(
        "-ao","--as-of",
        type=date.fromisoformat,
        default=date.today(),
        help="Date for the status report (YYYY-MM-DD). Default Today")
    status.add_argument(
        "-la","--look-ahead",
        type=non_negative_int,
        default=21,
        help="Number of days to look ahead (0 or greater). Default 21")

    budget = subparsers.add_parser(
        "budget",
        help = "Display project financials.")
    budget.add_argument("file", type=Path)
    budget.add_argument(
        "-ao","--as-of",
        type=date.fromisoformat,
        default=date.today(),
        help="Date for the status report (YYYY-MM-DD). Default Today")
    

    return parser