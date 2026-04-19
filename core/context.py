"""
Workflow execution context.
Stores shared state and configuration during workflow execution.
"""

from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    status: TaskStatus
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0


class WorkflowContext:
    """
    Shared context for workflow execution.
    Thread-safe for parallel task execution.
    """

    def __init__(self, workflow_config: Dict[str, Any]):
        self.workflow_config = workflow_config
        self.workflow_name = workflow_config.get("name", "unnamed")
        self.global_config = workflow_config.get("config", {})

        self._task_results: Dict[str, TaskResult] = {}
        self._shared_data: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def set_task_result(self, task_id: str, result: TaskResult) -> None:
        """Store a task result."""
        with self._lock:
            self._task_results[task_id] = result

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get a task result by ID."""
        with self._lock:
            return self._task_results.get(task_id)

    def get_all_results(self) -> Dict[str, TaskResult]:
        """Get all task results."""
        with self._lock:
            return dict(self._task_results)

    def set_data(self, key: str, value: Any) -> None:
        """Set shared data."""
        with self._lock:
            self._shared_data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get shared data."""
        with self._lock:
            return self._shared_data.get(key, default)

    def has_data(self, key: str) -> bool:
        """Check if shared data exists."""
        with self._lock:
            return key in self._shared_data

    def is_task_complete(self, task_id: str) -> bool:
        """Check if a task has completed (successfully or failed)."""
        result = self.get_task_result(task_id)
        return result is not None and result.status in (TaskStatus.SUCCESS, TaskStatus.FAILED)

    def is_task_success(self, task_id: str) -> bool:
        """Check if a task completed successfully."""
        result = self.get_task_result(task_id)
        return result is not None and result.status == TaskStatus.SUCCESS

    def get_task_ids_by_status(self, status: TaskStatus) -> list:
        """Get all task IDs with a specific status."""
        with self._lock:
            return [
                task_id for task_id, result in self._task_results.items()
                if result.status == status
            ]
