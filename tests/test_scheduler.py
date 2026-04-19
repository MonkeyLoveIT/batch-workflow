"""
Tests for DAG Scheduler.
"""

import pytest
from core.scheduler import DAGScheduler, DAGValidationError
from core.context import WorkflowContext, TaskStatus


class TestDAGScheduler:
    """Test DAGScheduler functionality."""

    def test_simple_linear_dependency(self):
        """Test linear task chain: task1 -> task2 -> task3"""
        tasks = [
            {"id": "task1", "depends_on": []},
            {"id": "task2", "depends_on": ["task1"]},
            {"id": "task3", "depends_on": ["task2"]},
        ]

        scheduler = DAGScheduler(tasks)
        order = scheduler.get_execution_order()

        assert len(order) == 3
        assert order[0] == ["task1"]
        assert order[1] == ["task2"]
        assert order[2] == ["task3"]

    def test_parallel_tasks(self):
        """Test parallel execution: task1 -> task2, task3"""
        tasks = [
            {"id": "task1", "depends_on": []},
            {"id": "task2", "depends_on": ["task1"]},
            {"id": "task3", "depends_on": ["task1"]},
        ]

        scheduler = DAGScheduler(tasks)
        order = scheduler.get_execution_order()

        assert len(order) == 2
        assert order[0] == ["task1"]
        assert set(order[1]) == {"task2", "task3"}

    def test_complex_dag(self):
        """Test complex DAG: task1 -> task2, task3 -> task4"""
        tasks = [
            {"id": "task1", "depends_on": []},
            {"id": "task2", "depends_on": ["task1"]},
            {"id": "task3", "depends_on": ["task1"]},
            {"id": "task4", "depends_on": ["task2", "task3"]},
        ]

        scheduler = DAGScheduler(tasks)
        order = scheduler.get_execution_order()

        assert len(order) == 3
        assert order[0] == ["task1"]
        assert set(order[1]) == {"task2", "task3"}
        assert order[2] == ["task4"]

    def test_self_dependency_error(self):
        """Test that self-dependency raises error."""
        tasks = [
            {"id": "task1", "depends_on": ["task1"]},
        ]

        with pytest.raises(DAGValidationError, match="depends on itself"):
            DAGScheduler(tasks)

    def test_nonexistent_dependency_error(self):
        """Test that non-existent dependency raises error."""
        tasks = [
            {"id": "task1", "depends_on": ["nonexistent"]},
        ]

        with pytest.raises(DAGValidationError, match="non-existent task"):
            DAGScheduler(tasks)

    def test_circular_dependency_error(self):
        """Test that circular dependency raises error."""
        tasks = [
            {"id": "task1", "depends_on": ["task3"]},
            {"id": "task2", "depends_on": ["task1"]},
            {"id": "task3", "depends_on": ["task2"]},
        ]

        with pytest.raises(DAGValidationError, match="Circular dependency"):
            DAGScheduler(tasks)

    def test_get_ready_tasks(self):
        """Test getting ready tasks based on completed dependencies."""
        tasks = [
            {"id": "task1", "depends_on": []},
            {"id": "task2", "depends_on": ["task1"]},
            {"id": "task3", "depends_on": ["task1"]},
        ]

        scheduler = DAGScheduler(tasks)
        context = WorkflowContext({"tasks": tasks})

        # Initially, only task1 is ready
        ready = scheduler.get_ready_tasks(context)
        assert ready == ["task1"]

        # After task1 completes, task2 and task3 are ready
        context.set_task_result("task1", MockTaskResult("task1", TaskStatus.SUCCESS))
        ready = scheduler.get_ready_tasks(context)
        assert set(ready) == {"task2", "task3"}

    def test_get_execution_order_multiple_levels(self):
        """Test execution order with multiple levels of parallelism."""
        tasks = [
            {"id": "task1", "depends_on": []},
            {"id": "task2", "depends_on": ["task1"]},
            {"id": "task3", "depends_on": ["task1"]},
            {"id": "task4", "depends_on": ["task2"]},
            {"id": "task5", "depends_on": ["task3"]},
            {"id": "task6", "depends_on": ["task4", "task5"]},
        ]

        scheduler = DAGScheduler(tasks)
        order = scheduler.get_execution_order()

        assert len(order) == 4
        assert order[0] == ["task1"]
        assert set(order[1]) == {"task2", "task3"}
        assert set(order[2]) == {"task4", "task5"}
        assert order[3] == ["task6"]


class MockTaskResult:
    """Mock task result for testing."""
    def __init__(self, task_id, status):
        self.task_id = task_id
        self.status = status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
