"""
DAG Scheduler for workflow task execution.
Handles dependency resolution and topological sorting.
"""

from typing import Any, Dict, List, Optional, Set
from collections import defaultdict, deque
import logging

from core.context import WorkflowContext, TaskResult, TaskStatus

logger = logging.getLogger(__name__)


class DAGValidationError(Exception):
    """Raised when DAG validation fails."""
    pass


class DAGScheduler:
    """
    DAG-based task scheduler.
    Resolves dependencies and determines execution order.
    """

    def __init__(self, tasks: List[Dict[str, Any]]):
        """
        Initialize scheduler with task definitions.

        Args:
            tasks: List of task configurations, each containing:
                - id: Unique task identifier
                - depends_on: List of task IDs this task depends on
                - plugin: Plugin name to use
                - config: Plugin configuration
                - retry: Number of retries on failure (default: 0)
                - continue_on_failure: Whether to continue if this task fails (default: False)
        """
        self.tasks = {task["id"]: task for task in tasks}
        self.task_ids = set(self.tasks.keys())
        self._validate_dag()
        self._build_graph()

    def _validate_dag(self) -> None:
        """Validate the DAG structure."""
        # Check for duplicate IDs
        if len(self.task_ids) != len(self.tasks):
            raise DAGValidationError("Duplicate task IDs found")

        # Check for self-dependencies
        for task_id, task in self.tasks.items():
            if task_id in task.get("depends_on", []):
                raise DAGValidationError(f"Task '{task_id}' depends on itself")

        # Check for non-existent dependencies
        for task_id, task in self.tasks.items():
            for dep_id in task.get("depends_on", []):
                if dep_id not in self.task_ids:
                    raise DAGValidationError(
                        f"Task '{task_id}' depends on non-existent task '{dep_id}'"
                    )

        # Check for circular dependencies using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            task = self.tasks.get(task_id)
            if task:
                for dep_id in task.get("depends_on", []):
                    if dep_id not in visited:
                        if has_cycle(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.remove(task_id)
            return False

        for task_id in self.task_ids:
            if task_id not in visited:
                if has_cycle(task_id):
                    raise DAGValidationError("Circular dependency detected")

    def _build_graph(self) -> None:
        """Build adjacency list representation of the DAG."""
        # in_degree[node] = number of tasks that must complete before node
        self.in_degree: Dict[str, int] = {task_id: 0 for task_id in self.task_ids}

        # adjacency[node] = list of tasks that depend on node
        self.adjacency: Dict[str, List[str]] = {task_id: [] for task_id in self.task_ids}

        # dependents[node] = list of tasks that node depends on
        self.dependents: Dict[str, List[str]] = {task_id: [] for task_id in self.task_ids}

        for task_id, task in self.tasks.items():
            depends_on = task.get("depends_on", [])
            self.in_degree[task_id] = len(depends_on)
            for dep_id in depends_on:
                self.adjacency[dep_id].append(task_id)
                self.dependents[task_id].append(dep_id)

    def get_ready_tasks(self, context: WorkflowContext) -> List[str]:
        """
        Get tasks that are ready to execute.

        A task is ready when:
        1. It hasn't been executed yet
        2. All its dependencies have completed successfully

        Args:
            context: Workflow execution context

        Returns:
            List of task IDs that are ready to execute
        """
        ready = []
        for task_id in self.task_ids:
            result = context.get_task_result(task_id)
            if result is not None:
                # Already executed
                continue

            # Check if all dependencies succeeded
            deps = self.dependents.get(task_id, [])
            if not deps:
                # No dependencies, ready immediately
                ready.append(task_id)
            elif all(context.is_task_success(dep_id) for dep_id in deps):
                ready.append(task_id)

        return ready

    def get_execution_order(self) -> List[List[str]]:
        """
        Get the topological order of task execution in levels.

        Returns:
            List of task ID lists, where each inner list contains tasks
            that can be executed in parallel (same level)
        """
        in_degree = dict(self.in_degree)
        levels = []
        remaining = set(self.task_ids)

        while remaining:
            # Find all tasks with no remaining dependencies
            level = [task_id for task_id in remaining if in_degree[task_id] == 0]

            if not level:
                raise DAGValidationError("Circular dependency detected")

            levels.append(level)

            # Remove processed tasks and update in_degrees
            for task_id in level:
                remaining.remove(task_id)
                for dependent in self.adjacency[task_id]:
                    in_degree[dependent] -= 1

        return levels

    def get_failed_dependencies(self, task_id: str, context: WorkflowContext) -> List[str]:
        """
        Get list of dependencies that failed for a given task.

        Args:
            task_id: Task ID to check
            context: Workflow execution context

        Returns:
            List of dependency task IDs that failed
        """
        failed = []
        for dep_id in self.dependents.get(task_id, []):
            result = context.get_task_result(dep_id)
            if result and result.status == TaskStatus.FAILED:
                failed.append(dep_id)
        return failed

    def is_complete(self, context: WorkflowContext) -> bool:
        """
        Check if all tasks are complete.

        Args:
            context: Workflow execution context

        Returns:
            True if all tasks have been executed (success or failed/skipped)
        """
        return all(
            context.get_task_result(task_id) is not None
            for task_id in self.task_ids
        )

    def has_failures(self, context: WorkflowContext) -> bool:
        """
        Check if any task has failed.

        Args:
            context: Workflow execution context

        Returns:
            True if any task has failed
        """
        return len(context.get_task_ids_by_status(TaskStatus.FAILED)) > 0

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task configuration by ID."""
        return self.tasks.get(task_id)
