class TaskHierarchy:
    def __init__(self, tasks):
        self.tasks = tasks

        self.parents = {}
        self.children = {}
        for task_id in tasks:
            self.children[task_id]=[]
    
        self.build()

    def build(self):
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

    def get_parent(self, task_id):
        return self.parents.get(task_id)

    def get_children(self, task_id):
        return self.children.get(task_id, [])

    def get_roots(self):
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

    def has_children(self, task_id):
        return bool(self.children.get(task_id))

    def is_summary(self, task_id):
        return self.has_children(task_id)

    def get_descendants(self, task_id):
        descendants = []

        for child_id in self.get_children(task_id):
            descendants.append(child_id)
            descendants.extend(
                self.get_descendants(child_id)
            )

        return descendants

    def get_tree(self):
        tree = {}
        for root_id in self.get_roots():
            self._add_to_tree(root_id, tree, 0)
        return tree

    def _add_to_tree(self, task_id, tree, level):
        tree[task_id] = (" "*level+task_id)
        level += 1
        children = self.get_children(task_id)
        children.sort()

        for child_id in children:
            self._add_to_tree(child_id, tree, level)

        
