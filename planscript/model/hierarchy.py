class TaskHierarchy:
    """Represent the parent-child hierarchy of a set of PlanScript tasks.

    Hierarchy is derived from the structure of task numbers. For example,
    task ``1.2.3`` has ``1.2`` as its parent when that task exists.

    If an implied parent task does not exist, the task is treated as a root.
    This allows projects to use hierarchical numbering without requiring
    placeholder tasks for every hierarchy level.

    The hierarchy is distinct from the project's dependency graph.
    """

    def __init__(self, tasks):
        """Build a hierarchy from the project's task identifiers."""

        self.tasks = dict(tasks)

        self.parents = {}
        self.children = {}
        for task_id in tasks:
            self.children[task_id]=[]
    
        self._build()

    def _build(self) -> None:
        """Rebuild parent and child relationships from the current tasks."""

        self.parents = {}
        self.children = {}
        for task_id in self.tasks:
            self.children[task_id]=[]


        for task_id in self.tasks:

            parts = task_id.split(".")

            if len(parts) == 1:
                self.parents[task_id] = None
                continue

            parent_id = ".".join(parts[:-1])

            if parent_id in self.tasks:
                self.parents[task_id] = parent_id
                self.children[parent_id].append(task_id)
            else:
                # TODO Parse error for implied parent not existing 
                self.parents[task_id] = None

    def get_parent(self, task_id: str) -> str | None:
        """Return the immediate parent task ID, or None for a root task."""

        return self.parents.get(task_id)

    def get_children(self, task_id: str) -> list[str]:
        """Return the immediate child task IDs."""

        return self.children.get(task_id, [])

    def get_roots(self) -> list[str]:
        """Return task IDs that have no parent in the hierarchy."""
        
        roots = []
        for task_id, parent_id in self.parents.items():
            if parent_id is None:
                roots.append(task_id)
        return roots

    def get_leaves(self, task_id: str) -> list[str]:
        """Return all terminal descendants of a task."""
        if not self.has_children(task_id):
            return [task_id]

        leaves = []

        for child_id in self.get_children(task_id):
            leaves.extend(self.get_leaves(child_id))

        return leaves

    def get_leaf_ids(self) -> list[str]:
        leaf_ids = []
        for task_id in self.tasks:
            if not self.has_children(task_id):
                leaf_ids.append(task_id)
        return leaf_ids


    def has_children(self, task_id: str) -> bool:
        """Return True if the task has one or more immediate children."""

        return bool(self.children.get(task_id))

    def is_summary(self, task_id: str) -> bool:
        """Return True if the task has one or more children."""

        return self.has_children(task_id)

    def get_descendants(self, task_id: str) -> list[str]:
        """Return all descendants of a task in depth-first order."""

        descendants = []

        for child_id in self.get_children(task_id):
            descendants.append(child_id)
            descendants.extend(
                self.get_descendants(child_id)
            )

        return descendants

    def get_tree(self) -> dict[str, str]:
        """Return a display-oriented tree of the project's task hierarchy."""

        tree = {}
        for root_id in self.get_roots():
            self._add_to_tree(root_id, tree, 0)
        return tree

    def _add_to_tree(self, task_id: str, tree: dict[str, str], level: int) -> None:
        """Add a task and its descendants to a display tree."""
        tree[task_id] = (" "*level+task_id)
        level += 1
        children = self.get_children(task_id)
        children.sort()

        for child_id in children:
            self._add_to_tree(child_id, tree, level)

        
