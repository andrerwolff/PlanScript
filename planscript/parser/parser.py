import re
from datetime import timedelta, date
from dataclasses import dataclass
from decimal import Decimal

from planscript.exceptions import ParseError
from planscript.model.project import Project
from planscript.model.task import Task
from planscript.model.dependency import Dependency
#from planscript.model.invoice import Invoice
from planscript.model.hierarchy import TaskHierarchy
from planscript.engine.tracker import TaskEvent, EventDirective, Invoice

@dataclass
class PendingDependency:
    predecessor_id: str
    successor_id: str
    dep_type: str
    lag: timedelta
    lag_unit: str
    line_number: int

class Parser:

    #standard plan patterns
    PROJECT_PATTERN = re.compile(
        r"^project:\s*(?P<name>.+)$",
        re.IGNORECASE
    )

    CALENDAR_PATTERN = re.compile(
        r"^(?: {4}|\t)calendar:\s*(?P<calendar>.+)$"
    )

    START_PATTERN = re.compile(
        r"^(?: {4}|\t)start:\s*(?P<date>\d{4}-\d{2}-\d{2})$"
    )

    FINISH_PATTERN = re.compile(
        r"^(?: {4}|\t)finish:\s*(?P<date>\d{4}-\d{2}-\d{2})$"
    )

    METADATA_PATTERN = re.compile(
        r"^(?: {4}|\t)-\s+(?P<key>[^:]+):\s+(?P<value>.*)$"
    )

    TASK_PATTERN = re.compile(
        r"^task\s+"
        r"(?P<id>[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)\s+"
        r"(?P<name>.+?)"
        r"(?:\s+(?P<duration>\d+(?:\.\d+)?[hdw]))?$"
    )

    DEPENDENCY_PATTERN = re.compile(
        r"^(?: {4}|\t)depends\s+"
        r"(?P<predecessor>[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)"
        r"(?:\s+(?P<type>FS|SS|FF|SF))?"
        r"(?:\s+(?P<lag>[+-]?\d+(?:\.\d+)?[hdw]))?$"
    )

    BUDGET_PATTERN = re.compile(
        r"^(?: {4}|\t)budget\s[$](?P<budget>\d+(?:\.\d{1,2})?)$"
    )

    BUDGET_WT_PATTERN = re.compile(
        r"^(?: {4}|\t)budget\s(?P<budget_wt>\d+(?:\.\d+)?)[%]$"
    )

    #Error Plan patterns
    INVALID_TASK_DURATION_PATTERN = re.compile(
        r"^task\s+"
        r"(?P<id>[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)\s+"
        r"(?P<description>.+?)\s+"
        r"(?P<duration>[+-]\d+(?:\.\d+)?[hdwm]?)$"
    )

    ATTACHED_DEPENDENCY_TYPE_PATTERN = re.compile(
        r"^(?: {4}|\t)depends\s+"
        r"(?P<predecessor>[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)(?P<type>FS|SS|FF|SF)"
    )

    #Standard Tracking Patterns
    TRACKING_DATE_PATTERN = re.compile(
        r"^(?P<date>\d{4}-\d{2}-\d{2})$"
    )
    # TODO harden entry pattern vs "    budget 40"
    TRACKING_ENTRY_PATTERN = re.compile(
        r"^(?: {4}|\t)"
        r"(?P<id>[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)\s+"
        r"(?P<directive>.+?)$"
    )
    TRACKING_PATTERN = re.compile(
        r"^(?P<date>\d{4}-\d{2}-\d{2})\s+"
        r"(?P<id>[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)\s+"
        r"(?P<directive>.+?)$"
    )
    INVOICE_PATTERN = re.compile(
        r"^(?P<date>\d{4}-\d{2}-\d{2})\s+"
        r"invoice\s+"
        r"\$(?P<amount>\d+(?:\.\d{1,2})?)$"
    )
    INVOICE_ENTRY_PATTERN = re.compile(
        r"^(?: {4}|\t)"
        r"(?P<id>[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)\s+"
        r"\$(?P<amount>\d+(?:\.\d{1,2})?)$"
    )

    def parse(self, text):

        project = None
        current_object = None
        tracking_date = None

        seen_project_attributes = set()
        pending_dependencies = []


        for line_number, raw_line in enumerate(text.splitlines(), start=1):

            #print(repr(raw_line))
            line = raw_line.rstrip()

            # Blank line
            if not line:
                continue

            # Comment
            if line.startswith(";"):
                continue

            if line.startswith(("calendar:","start:","finish:","depends","- ")):
                raise ParseError(f"Line {line_number}: line must be indented")

            # Project
            match = self.PROJECT_PATTERN.match(line)
            if match:
                if project is not None:
                    raise ParseError(f"Line {line_number}: multiple project declarations")

                project = Project(match.group("name"))
                current_object = project
                continue

            if project is None:
                raise ParseError(f"Line {line_number}: content found before project declaration")

            # Metadata
            match = self.METADATA_PATTERN.match(line)
            if match:
                if current_object is None:
                    raise ParseError(f"Line {line_number}: metadata has no preceding entry")

                key = match.group("key").strip()
                value = match.group("value").strip()

                current_object.metadata[key] = value
                continue

            # Calendar
            match = self.CALENDAR_PATTERN.match(line)
            if match:
                if "calendar" in seen_project_attributes:
                    raise ParseError(f"Line {line_number}: duplicate calendar declaration")
                
                project.calendar = match.group("calendar").strip()
                seen_project_attributes.add("calendar")
                #current_object = project
                continue

            # Start target
            match = self.START_PATTERN.match(line)
            if match:
                if "start" in seen_project_attributes:
                    raise ParseError(f"Line {line_number}: duplicate start declaration")
                
                project.start_date = self.parse_date(match.group("date"), line_number)
                seen_project_attributes.add("start")
                #current_object = project
                continue

            # Finish target
            match = self.FINISH_PATTERN.match(line)
            if match:
                if "finish" in seen_project_attributes:
                    raise ParseError(f"Line {line_number}: duplicate finish declaration")
                
                project.finish_date = self.parse_date(match.group("date"), line_number)
                seen_project_attributes.add("finish")
                #current_object = project
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
                current_task = task_id
                name = match.group("name").strip()
                duration, duration_unit = self.parse_duration(match.group("duration"))

                if task_id in project.tasks:
                    raise ParseError(f"Line {line_number}: duplicate task ID '{task_id}'")

                if duration is not None and duration < timedelta(0):
                    # TODO is this tested anywhere?
                    raise ParseError(f"Duration cannot be negative: '{duration}'")
                
                task = Task(task_id, name, duration)

                project.add_task(task)

                current_object = task
                continue

            # Invalid Dependency
            match = self.ATTACHED_DEPENDENCY_TYPE_PATTERN.match(line)
            if match:
                raise ParseError(
                    f"Line {line_number}: dependency type must be separated "
                    f"from successor task ID by whitespace"
                )
            #Dependency
            match = self.DEPENDENCY_PATTERN.match(line)
            if match:
                predecessor_id = match.group("predecessor")
                successor_id = current_task
                dep_type = match.group("type")
                lag = match.group("lag")

                if dep_type is None:
                    dep_type = "FS"
                
                if lag is None:
                    lag = "0d"
                lag, lag_unit = self.parse_duration(lag)

                pending = PendingDependency(
                    predecessor_id=predecessor_id,
                    successor_id=successor_id,
                    dep_type=dep_type,
                    lag=lag, lag_unit=lag_unit, line_number=line_number)
                pending_dependencies.append(pending)
                continue

            match = self.BUDGET_PATTERN.match(line)
            if match:
                task_budget = match.group("budget")
                current_object.budget = Decimal(task_budget)
                continue

            match = self.BUDGET_WT_PATTERN.match(line)
            if match:
                task_budget_wt = match.group("budget_wt")
                current_object.budget_wt = Decimal(task_budget_wt)
                continue

            match = self.INVOICE_PATTERN.match(line)
            if match:
                invoice_date = self.parse_date(match.group("date"), line_number)
                invoice_amount = Decimal(match.group("amount"))
                invoice = Invoice(invoice_date, invoice_amount)
                current_object = invoice
                project.tracker.add_invoice_event(invoice)
                continue

            match = self.INVOICE_ENTRY_PATTERN.match(line)
            if match:
                if not isinstance(current_object, Invoice):
                    raise ParseError(f"Line {line_number}: Invoice entry has no preceeding invoice: {line}.")
                task_id = match.group("id")
                if task_id not in project.tasks:
                    raise ParseError(f"Line {line_number}: Task ID '{task_id}' is not in the project.")
                amount = Decimal(match.group("amount"))
                current_object.add_allocation(task_id, amount)
                continue

            #Tracking Main
            match = self.TRACKING_PATTERN.match(line)
            if match:
                event_date = self.parse_date(match.group("date"), line_number)
                task_id = match.group("id")
                full_directive = match.group("directive")

                if task_id not in project.tasks:
                    raise ParseError(f"Line {line_number}: Task ID '{task_id}' is not in the project.")

                directive, info = self.parse_event_directive(full_directive, line_number)
                task_event = TaskEvent(event_date, task_id, directive, info)
                    
                project.tracker.add_task_event(task_event)

                tracking_date = None
                current_object = project
                continue

            # Tracking date header for multi line
            match = self.TRACKING_DATE_PATTERN.match(line)
            if match:
                tracking_date = self.parse_date(match.group("date"),line_number)
                current_object = project
                continue

            # Tracking entry under a date
            match = self.TRACKING_ENTRY_PATTERN.match(line)
            if match:
                if tracking_date is None:
                    raise ParseError(f"Line {line_number}: Tracking entry has no date. {line}")

                task_id = match.group("id")
                full_directive = match.group("directive")

                if task_id not in project.tasks:
                    raise ParseError(f"Line {line_number}: Task ID '{task_id}' is not in the project.")

                directive, info = self.parse_event_directive(full_directive,line_number)
                task_event = TaskEvent(tracking_date,task_id,directive,info)

                project.tracker.add_task_event(task_event)

                current_object = project
                continue

            # nothing recognized
            raise ParseError(f"Line {line_number}: unrecognized syntax: {line}")

        if project is None:
            raise ParseError("No project declaration found")

        self.resolve_dependencies(project, pending_dependencies)
        project.validate()
        project.tracker.hierarchy = TaskHierarchy(project.tasks)

        return project

    def parse_duration(self, value):
        if value is None:
            return None, None

        value = value.lower()

        if value[-1] not in "hdwm":
                    value += "d"

        try:            
            number = float(value[:-1])
        except ValueError:
            raise ParseError(f"Invalid duration: '{value}'")
        
        
        unit = value[-1]

        if unit == "h":
            return (timedelta(hours=number),"h")
        elif unit == "d":
            return (timedelta(days=number), "d")
        elif unit == "w":
            return (timedelta(weeks=number), "w")
        elif unit == "m":
            # Define what "month" means here before implementing this.
            
           # print("Month durations are not yet supported")
            return (timedelta(days=number*30), "m")

        raise ParseError(f"Invalid duration: {value}")

    
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
                    and existing.dep_type.value == d.dep_type
                    and existing.lag == d.lag
                ):
                    raise ParseError(f"Line {d.line_number}: duplicate dependency '{d.predecessor_id}' > '{d.successor_id}'")
            project.add_dependency(predecessor, successor, d.dep_type, d.lag, d.lag_unit)

    def parse_event_directive(self, full_directive, line_number):
        parts = full_directive.strip().split(maxsplit=1)

        if len(parts) == 1:
            word = parts[0]
            if word in ["start", "complete"]:
                directive = word
                info = None
        elif len(parts) == 2:
            first, second = parts
            #temp parse error handling, expand when more directives
            if first == "progress" and "%" in second:
                directive = first
                info = second
            elif first == "note":
                directive = first
                info = second
            else:
                raise ParseError(f"Lineb {line_number}: Event Syntax Error '{full_directive}'")
        return (EventDirective(directive), info)