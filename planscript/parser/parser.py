import re
from datetime import timedelta

from planscript.model.project import Project
from planscript.model.task import Task
from planscript.model.dependency import Dependency


class ParseError(Exception):
    pass


class Parser:

    TASK_PATTERN = re.compile(
        r"^task\s+"
        r"(?P<id>[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)\s+"
        r"(?P<description>.+?)"
        r"(?:\s+(?P<duration>\d+(?:\.\d+)?[hdwm]))?$",
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
        r"^project:\s*(?P<name>.+)$"
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
                project.calendar = match.group("calendar").strip()
                current_entry = project
                continue

            # Start target
            match = self.START_PATTERN.match(line)
            if match:
                project.start = match.group("date")
                current_entry = project
                continue

            # Finish target
            match = self.FINISH_PATTERN.match(line)
            if match:
                project.finish = match.group("date")
                current_entry = project
                continue

            # Task
            match = self.TASK_PATTERN.match(line)
            if match:
                task_id = match.group("id")
                description = match.group("description").strip()

                duration = self.parse_duration(match.group("duration"))

                if duration == None:
                    print("HERE")
                    print(task_id, duration)
                    continue
                task = Task(task_id, description, duration)

                project.add_task(task)

                current_entry = task
                continue

            # Dependency
            match = self.DEPENDENCY_PATTERN.match(line)
            if match:
                predecessor_id = match.group("predecessor")
                relationship = match.group("relationship")

                successor_id, dependency_type, lag = self.parse_dependency(relationship, project, line_number)

                if dependency_type is None:
                    dependency_type = "FS"
                else:
                    dependency_type = dependency_type.upper()

                if lag is None:
                    lag = "0d"
                lag = self.parse_duration(lag)

                if predecessor_id not in project.tasks:
                    raise ValueError(f"Line {line_number}: unknown predecessor task '{predecessor_id}'")
                if successor_id not in project.tasks:
                    raise ValueError(f"Line {line_number}: unknown successor task '{successor_id}'")

                predecessor = project.tasks[predecessor_id]
                successor = project.tasks[successor_id]
                
                print(predecessor, successor, dependency_type, lag)

                project.add_dependency(predecessor, successor, dependency_type, lag)

                current_entry = project
                continue

            raise ParseError(f"Line {line_number}: unrecognized syntax: {line}")

        if project is None:
            raise ParseError("No project declaration found")

        return project

    def parse_duration(self, value):
        if value is None:
            return None

        value = value.lower()

        if value[-1].lower() not in "hdwm":
                    value += "d"
        number = float(value[:-1])
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

    def parse_dependency ( self, relationship, project, line_number):
        relationship = relationship.strip()

        # ----------------------------------------
        # Normal form
        # ----------------------------------------
        match = re.fullmatch(
            r"(?P<successor>[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)"
            r"(?:\s+(?P<type>FS|SS|FF|SF))?"
            r"(?:\s*(?P<lag>[+-]\d+(?:\.\d+)?[hdwm]?))?",
            relationship,
            re.IGNORECASE
        )

        if match:
            successor_id = match.group("successor")
            if successor_id in project.tasks:
                return (
                    successor_id,
                    match.group("type"),
                    match.group("lag"),
                )
        # ----------------------------------------
        # Compact form
        # ----------------------------------------
        candidates = []

        for task_id in project.tasks:
            if not relationship.lower().startswith(task_id.lower()):
                continue
            remainder = relationship[len(task_id):]

            match = re.fullmatch(
                r"(?P<type>FS|SS|FF|SF)?"
                r"(?P<lag>[+-]\d+(?:\.\d+)?[hdwm]?)?",
                remainder,
                re.IGNORECASE
            )

            if match:
                candidates.append((task_id, match.group("type"), match.group("lag")))

        if len(candidates) == 1:
            return candidates[0]

        if len(candidates) == 0:
            raise ParseError(f"Line {line_number}: could not determine successor task or dependency type from '{relationship}'")

        raise ParseError(f"Line {line_number}: ambiguous dependency '{relationship}'; add a space between the task ID and dependency type")