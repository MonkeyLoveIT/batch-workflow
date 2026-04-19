#!/usr/bin/env python3
"""
Example: Running a workflow programmatically.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from core import WorkflowEngine
import plugins  # Load all plugins

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Example workflow configuration
workflow_config = {
    "name": "Example Workflow",
    "max_workers": 4,
    "tasks": [
        {
            "id": "task1",
            "plugin": "command",
            "config": {"cmd": "echo", "args": ["Starting workflow..."]},
            "notify_on": ["start", "success", "failure"],
        },
        {
            "id": "task2",
            "plugin": "command",
            "config": {"cmd": "sleep", "args": ["1"]},
            "depends_on": ["task1"],
        },
        {
            "id": "task3",
            "plugin": "command",
            "config": {"cmd": "sleep", "args": ["2"]},
            "depends_on": ["task1"],
        },
        {
            "id": "task4",
            "plugin": "command",
            "config": {"cmd": "echo", "args": ["All done!"]},
            "depends_on": ["task2", "task3"],
        },
    ],
    "notifications": [
        {
            "event": "workflow_start",
            "plugin": "wechat_work",
            "config": {
                "webhook_url": "YOUR_WEBHOOK_URL",
                "message": "Workflow started: {workflow_name}",
            },
        },
    ],
}


def main():
    print("=" * 50)
    print("Running Example Workflow")
    print("=" * 50)

    # Create and run engine
    engine = WorkflowEngine(workflow_config)
    context = engine.run()

    # Print results
    print("\n" + "=" * 50)
    print("Workflow Results")
    print("=" * 50)

    for task_id, result in context.get_all_results().items():
        status = result.status.value
        duration = result.duration
        print(f"  {task_id}: {status} ({duration:.2f}s)")


if __name__ == "__main__":
    main()
