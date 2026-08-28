import re
from datetime import timedelta, date
from dataclasses import dataclass

from planscript.model.project import Project
from planscript.model.task import Task
from planscript.model.dependency import Dependency



class ParseError(Exception):
    pass

@dataclass
class PendingDependency:
    predecessor_id: str
    successor_id: str
    dependency_type: str
    lag: timedelta
    line_number: int

class Parser:

    TASK_PATTERN = re.compile(
        r"^task\s+"
        r"(?P<id>[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)\s+"
        r"(?P<description>.+?)"
        r"(?:\s+(?P<duration>\d+(?:\.\d+)?[hdwm]))?$",
        re.IGNORECASE
    )

    INVALID_TASK_DURATION_PATTERN = re.compile(
        r"^task\s+"
        r"(?P<id>[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)\s+"
        r"(?P<description>.+?)\s+"
        r"(?P<duration>[+-]\d+(?:\.\d+)?[hdwm]?)$",
        re.IGNORECASE
    )

    DEPENDENCY_PATTERN = re.compile(
        r"^dependency\s+"
        r"(?P<predecessor>[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)\s+"
        r">\s+"
        r"(?P<relationship>.+)$",
        re.IGNORECASE
    )

    PROJECT_PATTERN = re.compile(
        r"^project:\s*(?P<name>.+)$",
        re.IGNORECASE
    )

    CALENDAR_PATTERN = re.compile(
        r"^calendar:\s*(?P<calendar>.+)$"
    )

    START_PATTERN = re.compile(
        r"^start:\s*(?P<date>\d{4}-\d{2}-\d{2})$"
    )

    FINISH_PATTERN = re.compile(
        r"^finish:\s*(?P<date>\d{4}-\d{2}-\d{2})$"
    )

    METADATA_PATTERN = re.compile(
        r"^-\s+(?P<key>[^:]+):\s*(?P<value>.*)$"
    )

    def parse(self, text):

        project = None
        current_entry = None
        seen_project_attributes = set()
        pending_dependencies = []

        for line_number, raw_line in enumerate(text.splitlines(), start=1):

            line = raw_line.strip()

            # Blank line
            if not line:
                continue

            # Comment
            if line.startswith("#"):
                continue

            # Project
            match = self.PROJECT_PATTERN.match(line)
            if match:
                if project is not None:
                    raise ParseError(f"Line {line_number}: multiple project declarations")

                project = Project(match.group("name"))
                current_entry = project
                continue

            if project is None:
                raise ParseError(f"Line {line_number}: content found before project declaration")

            # Metadata
            match = self.METADATA_PATTERN.match(line)
            if match:
                if current_entry is None:
                    raise ParseError(f"Line {line_number}: metadata has no preceding entry")

                key = match.group("key").strip()
                value = match.group("value").strip()

                current_entry.metadata[key] = value
                continue

            # Calendar
            match = self.CALENDAR_PATTERN.match(line)
            if match:
                if "calendar" in seen_project_attributes:
                    raise ParseError(f"Line {line_number}: duplicate calendar declaration")
                
                project.calendar = match.group("calendar").strip()
                seen_project_attributes.add("calendar")
                current_entry = project
                continue

            # Start target
            match = self.START_PATTERN.match(line)
            if match:
                if "start" in seen_project_attributes:
                    raise ParseError(f"Line {line_number}: duplicate start declaration")
                
                project.start = self.parse_date(match.group("date"), line_number)
                seen_project_attributes.add("start")
                current_entry = project
                continue

            # Finish target
            match = self.FINISH_PATTERN.match(line)
            if match:
                if "finish" in seen_project_attributes:
                    raise ParseError(f"Line {line_number}: duplicate finish declaration")
                
                project.finish = self.parse_date(match.group("date"), line_number)
                seen_project_attributes.add("finish")
                current_entry = project
                continue

            # Invalid task duration
            match = self.INVALID_TASK_DURATION_PATTERN.match(line)
            if match:
                raise ParseError(f"Line {line_number}: task duration cannot be negative or signed '{match.group('duration')}')"
                )

            # Task
            match = self.TASK_PATTERN.match(line)
            if match:
                task_id = match.group("id")
                description = match.group("description").strip()
                duration = self.parse_duration(match.group("duration"))

                if duration == None:
                    # TODO implement milestones
                    print(f"{task_id} is summary")
                    continue

                if duration < timedelta(0):
                    raise ParseError(f"Duration cannot be negative: '{value}'")
                
                if task_id in project.tasks:
                    raise ParseError(f"Line {line_number}: duplicate task ID '{task_id}'")

                task = Task(task_id, description, duration)

                project.add_task(task)

                current_entry = task
                continue

            # Dependency
            # TODO parse dependency into temporary and only after loading all tasks, create dependency object
            match = self.DEPENDENCY_PATTERN.match(line)
            if match:
                predecessor_id = match.group("predecessor")
                relationship = match.group("relationship")

                successor_id, dependency_type, lag = self.parse_dependency(relationship, project, line_number)

                if dependency_type is None:
                    dependency_type = "FS"
                
                if lag is None:
                    lag = "0d"
                lag = self.parse_duration(lag)

                pending = PendingDependency(
                    predecessor_id=predecessor_id,
                    successor_id=successor_id,
                    dependency_type=dependency_type,
                    lag=lag, line_number=line_number)
                pending_dependencies.append(pending)
                

                current_entry = project
                continue

            raise ParseError(f"Line {line_number}: unrecognized syntax: {line}")

        if project is None:
            raise ParseError("No project declaration found")

        self.resolve_dependencies(project, pending_dependencies)
        self.validate_project(project)
        return project

    def parse_duration(self, value):
        if value is None:
            return None

        value = value.lower()

        if value[-1] not in "hdwm":
                    value += "d"

        try:            
            number = float(value[:-1])
        except ValueError:
            raise ParseError(f"Invalid duration: '{value}'")
        
        
        unit = value[-1]

        if unit == "h":
            return timedelta(hours=number)
        elif unit == "d":
            return timedelta(days=number)
        elif unit == "w":
            return timedelta(weeks=number)
        elif unit == "m":
            # Define what "month" means here before implementing this.
            
            print("Month durations are not yet supported")
            return timedelta(days=number*30)

        raise ParseError(f"Invalid duration: {value}")

    def parse_dependency(self, relationship, project, line_number):
        relationship = relationship.strip()

        if not relationship:
            raise ParseError(
                f"Line {line_number}: empty dependency relationship"
            )

        # ---------------------------------------------------------
        # Separate successor from the remainder.
        #
        # The successor is always the first whitespace-delimited
        # token.
        # ---------------------------------------------------------

        parts = relationship.split(maxsplit=1)

        successor_id = parts[0]
        remainder = parts[1].strip() if len(parts) > 1 else ""

        # ---------------------------------------------------------
        # Reject compact successor + dependency type.
        #
        # 1.2FS
        # 1.2SS
        # 1.2FF
        # 1.2SF
        # ---------------------------------------------------------

        if re.fullmatch(
            r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*(?:FS|SS|FF|SF)",
            successor_id,
            re.IGNORECASE,
        ):
            raise ParseError(
                f"Line {line_number}: dependency type must be separated "
                f"from successor task ID by whitespace"
            )

        dependency_type = None
        lag = None

        # No type or lag
        if not remainder:
            return successor_id, dependency_type, lag

        # ---------------------------------------------------------
        # Type + optional lag
        #
        # FS
        # FS2
        # FS+2
        # FS-2d
        # ---------------------------------------------------------

        type_match = re.fullmatch(
            r"(?P<type>FS|SS|FF|SF)"
            r"(?P<lag>[+-]?\d+(?:\.\d+)?[hdwm]?)?",
            remainder,
            re.IGNORECASE,
        )

        if type_match:
            dependency_type = type_match.group("type").upper()
            lag = type_match.group("lag")

            if lag is not None and lag[0] not in "+-":
                lag = "+" + lag

            return successor_id, dependency_type, lag

        # ---------------------------------------------------------
        # Type followed by separated lag
        #
        # FS 2
        # FS +2
        # FS -2d
        # ---------------------------------------------------------

        type_lag_match = re.fullmatch(
            r"(?P<type>FS|SS|FF|SF)"
            r"\s+"
            r"(?P<lag>[+-]?\d+(?:\.\d+)?[hdwm]?)",
            remainder,
            re.IGNORECASE,
        )

        if type_lag_match:
            dependency_type = type_lag_match.group("type").upper()
            lag = type_lag_match.group("lag")

            if lag[0] not in "+-":
                lag = "+" + lag

            return successor_id, dependency_type, lag

        # ---------------------------------------------------------
        # Lag without type
        #
        # 2
        # +2
        # -2d
        # ---------------------------------------------------------

        lag_match = re.fullmatch(
            r"[+-]?\d+(?:\.\d+)?[hdwm]?",
            remainder,
            re.IGNORECASE,
        )

        if lag_match:
            lag = lag_match.group(0)

            if lag[0] not in "+-":
                lag = "+" + lag

            return successor_id, dependency_type, lag

        # ---------------------------------------------------------
        # Anything else is invalid
        # ---------------------------------------------------------

        raise ParseError(
            f"Line {line_number}: invalid dependency relationship "
            f"'{relationship}'"
        )       
    def parse_date(self, value, line_number):
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise ParseError(f"Line {line_number}: invalid date '{value}'")

    def resolve_dependencies(self, project, pending_dependencies):
        for d in pending_dependencies:
            if d.predecessor_id not in project.tasks:
                raise ParseError(f"Line {d.line_number}: unknown predecessor task '{d.predecessor_id}'")
            if d.successor_id not in project.tasks:
                raise ParseError(f"Line {d.line_number}: unknown successor task '{d.successor_id}'")
            if d.predecessor_id == d.successor_id:
                raise ParseError(f"Line {d.line_number}: task cannot depend on itself '{d.predecessor_id}'")

            predecessor = project.tasks[d.predecessor_id]
            successor = project.tasks[d.successor_id]
            
            for existing in project.dependencies:
                if (
                    existing.predecessor is predecessor
                    and existing.successor is successor
                    and existing.dependency_type.value == d.dependency_type
                    and existing.lag == d.lag
                ):
                    raise ParseError(f"Line {d.line_number}: duplicate dependency '{d.predecessor_id}' > '{d.successor_id}'")
            project.add_dependency(predecessor, successor, d.dependency_type, d.lag)

    def validate_project(self, project):
        if (
            project.start is not None
            and project.finish is not None
            and project.start > project.finish
        ):
            raise ParseError("Project start date cannot be after finish date.")
        # TODO - add other validations?