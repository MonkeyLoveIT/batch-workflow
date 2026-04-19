"""
Tests for Workflow Engine.
"""

import pytest
import plugins  # Load all plugins
from core import WorkflowEngine
from core.context import TaskStatus


class TestWorkflowEngine:
    """Test WorkflowEngine functionality."""

    def test_simple_workflow(self):
        """Test running a simple linear workflow."""
        config = {
            "name": "Test Workflow",
            "tasks": [
                {
                    "id": "task1",
                    "plugin": "command",
                    "config": {"cmd": "echo", "args": ["hello"]},
                },
            ],
        }

        engine = WorkflowEngine(config)
        context = engine.run()

        results = context.get_all_results()
        assert len(results) == 1
        assert results["task1"].status == TaskStatus.SUCCESS

    def test_sequential_tasks(self):
        """Test sequential task execution."""
        config = {
            "name": "Sequential Test",
            "tasks": [
                {
                    "id": "task1",
                    "plugin": "command",
                    "config": {"cmd": "echo", "args": ["step1"]},
                },
                {
                    "id": "task2",
                    "plugin": "command",
                    "config": {"cmd": "echo", "args": ["step2"]},
                    "depends_on": ["task1"],
                },
            ],
        }

        engine = WorkflowEngine(config)
        context = engine.run()

        results = context.get_all_results()
        assert results["task1"].status == TaskStatus.SUCCESS
        assert results["task2"].status == TaskStatus.SUCCESS

    def test_parallel_tasks(self):
        """Test parallel task execution."""
        config = {
            "name": "Parallel Test",
            "tasks": [
                {
                    "id": "task1",
                    "plugin": "command",
                    "config": {"cmd": "echo", "args": ["start"]},
                },
                {
                    "id": "task2",
                    "plugin": "command",
                    "config": {"cmd": "sleep", "args": ["0.1"]},
                    "depends_on": ["task1"],
                },
                {
                    "id": "task3",
                    "plugin": "command",
                    "config": {"cmd": "sleep", "args": ["0.1"]},
                    "depends_on": ["task1"],
                },
            ],
        }

        engine = WorkflowEngine(config)
        context = engine.run()

        results = context.get_all_results()
        assert results["task1"].status == TaskStatus.SUCCESS
        assert results["task2"].status == TaskStatus.SUCCESS
        assert results["task3"].status == TaskStatus.SUCCESS

    def test_task_failure(self):
        """Test task failure handling."""
        config = {
            "name": "Failure Test",
            "stop_on_failure": False,  # Don't stop workflow on task failure
            "tasks": [
                {
                    "id": "failing_task",
                    "plugin": "command",
                    "config": {"cmd": "false"},  # Always returns non-zero
                },
            ],
        }

        engine = WorkflowEngine(config)
        context = engine.run()

        results = context.get_all_results()
        assert results["failing_task"].status == TaskStatus.FAILED

    def test_nonexistent_plugin(self):
        """Test handling of non-existent plugin."""
        config = {
            "name": "Plugin Error Test",
            "tasks": [
                {
                    "id": "task1",
                    "plugin": "nonexistent_plugin",
                    "config": {},
                },
            ],
        }

        engine = WorkflowEngine(config)
        context = engine.run()

        results = context.get_all_results()
        assert results["task1"].status == TaskStatus.FAILED
        assert "not found" in results["task1"].error.lower()

    def test_dag_execution_order(self):
        """Test that DAG executes in correct order."""
        execution_order = []

        def make_plugin(task_id):
            from core.plugin import Plugin, register_plugin
            @register_plugin(f"plugin_{task_id}")
            class CapturingPlugin(Plugin):
                name = f"plugin_{task_id}"

                def execute(self, context):
                    execution_order.append(task_id)
                    return {"success": True}

            return f"plugin_{task_id}"

        # Create unique plugins
        make_plugin("t1")
        make_plugin("t2")
        make_plugin("t3")
        make_plugin("t4")

        config = {
            "name": "Order Test",
            "tasks": [
                {"id": "t1", "plugin": "plugin_t1", "config": {}},
                {"id": "t2", "plugin": "plugin_t2", "config": {}, "depends_on": ["t1"]},
                {"id": "t3", "plugin": "plugin_t3", "config": {}, "depends_on": ["t1"]},
                {"id": "t4", "plugin": "plugin_t4", "config": {}, "depends_on": ["t2", "t3"]},
            ],
        }

        engine = WorkflowEngine(config)
        engine.run()

        # t1 must come before t2 and t3
        assert execution_order.index("t1") < execution_order.index("t2")
        assert execution_order.index("t1") < execution_order.index("t3")
        # t4 must come after t2 and t3
        assert execution_order.index("t4") > execution_order.index("t2")
        assert execution_order.index("t4") > execution_order.index("t3")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
