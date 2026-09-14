from dataclasses import dataclass
from datetime import date

from planscript.model.hierarchy import TaskHierarchy

@dataclass
class Schedule:

    hierarchy: TaskHierarchy
    ordered_task_ids: list[str]
    early_start: dict[str, int]
    early_finish: dict[str, int]
    late_start: dict[str, int]
    late_finish: dict[str, int]
    total_float: dict[str, int]
    critical_tasks: list[str]
    critical_paths: list[list[str]]
    duration: int
    start_dates: dict[str, date]
    finish_dates: dict[str, date]

    def __post_init__(self):
        self._rollup_summary_dates()

    def _rollup_summary_dates(self):
        for task_id in reversed(self.ordered_task_ids):
            if self.hierarchy.is_summary(task_id):
                decendant_starts = []
                decendant_finishes = []
                for child in self.hierarchy.get_descendants(task_id):
                    decendant_starts.append(self.start_dates[child])
                    decendant_finishes.append(self.finish_dates[child])

                self.start_dates[task_id] = min(decendant_starts)
                self.finish_dates[task_id] = max(decendant_finishes)
                self.total_float[task_id] = "-"

