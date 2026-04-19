#!/usr/bin/env python3
"""
Workflow Generator Tool

Generates workflow YAML from templates or specifications.
Usage:
    python tools/generate_workflow.py --linear task1,task2,task3
    python tools/generate_workflow.py --diamond task1 task2 task3 task4
    python tools/generate_workflow.py --parallel task1 task2
    python tools/generate_workflow.py --interactive
"""

import sys
import os
import argparse
import yaml
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_linear_workflow(task_names: List[str], **kwargs) -> Dict[str, Any]:
    """
    Generate a linear workflow: task1 -> task2 -> task3 -> ...
    """
    tasks = []
    prev_task = None

    for i, name in enumerate(task_names):
        task_id = f"task{i+1}" if name.startswith("task") else name.lower().replace(" ", "_")

        task = {
            "id": task_id,
            "name": name,
            "plugin": kwargs.get("plugin", "command"),
            "config": kwargs.get("config", {"cmd": "echo", "args": [f"Executing {name}"]}),
        }

        if prev_task:
            task["depends_on"] = [prev_task]

        tasks.append(task)
        prev_task = task_id

    return {
        "name": kwargs.get("workflow_name", "Linear Workflow"),
        "config": kwargs.get("config", {}),
        "tasks": tasks,
    }


def generate_parallel_workflow(task_names: List[str], **kwargs) -> Dict[str, Any]:
    """
    Generate a parallel workflow: task1 -> [task2, task3, ...]
    All tasks depend on the first task.
    """
    if len(task_names) < 2:
        raise ValueError("Parallel workflow needs at least 2 tasks")

    first_name = task_names[0]
    parallel_names = task_names[1:]

    first_id = f"task1" if first_name.startswith("task") else first_name.lower().replace(" ", "_")

    tasks = [
        {
            "id": first_id,
            "name": first_name,
            "plugin": kwargs.get("plugin", "command"),
            "config": kwargs.get("config", {"cmd": "echo", "args": [f"Executing {first_name}"]}),
        }
    ]

    for i, name in enumerate(parallel_names):
        task_id = f"task{i+2}" if name.startswith("task") else name.lower().replace(" ", "_")
        tasks.append({
            "id": task_id,
            "name": name,
            "plugin": kwargs.get("plugin", "command"),
            "config": kwargs.get("config", {"cmd": "echo", "args": [f"Executing {name}"]}),
            "depends_on": [first_id],
        })

    return {
        "name": kwargs.get("workflow_name", "Parallel Workflow"),
        "config": kwargs.get("config", {}),
        "tasks": tasks,
    }


def generate_diamond_workflow(task_names: List[str], **kwargs) -> Dict[str, Any]:
    """
    Generate a diamond workflow:
           task1
          /    \
       task2    task3
          \    /
          task4
    """
    if len(task_names) < 4:
        raise ValueError("Diamond workflow needs at least 4 tasks")

    names = task_names[:4]
    ids = [n.lower().replace(" ", "_") for n in names]

    tasks = [
        {
            "id": ids[0],
            "name": names[0],
            "plugin": kwargs.get("plugin", "command"),
            "config": {"cmd": "echo", "args": [f"Executing {names[0]}"]},
        },
        {
            "id": ids[1],
            "name": names[1],
            "plugin": kwargs.get("plugin", "command"),
            "config": {"cmd": "echo", "args": [f"Executing {names[1]}"]},
            "depends_on": [ids[0]],
        },
        {
            "id": ids[2],
            "name": names[2],
            "plugin": kwargs.get("plugin", "command"),
            "config": {"cmd": "echo", "args": [f"Executing {names[2]}"]},
            "depends_on": [ids[0]],
        },
        {
            "id": ids[3],
            "name": names[3],
            "plugin": kwargs.get("plugin", "command"),
            "config": {"cmd": "echo", "args": [f"Executing {names[3]}"]},
            "depends_on": [ids[1], ids[2]],
        },
    ]

    return {
        "name": kwargs.get("workflow_name", "Diamond Workflow"),
        "config": kwargs.get("config", {}),
        "tasks": tasks,
    }


def generate_custom_workflow(stages: List[List[str]], **kwargs) -> Dict[str, Any]:
    """
    Generate a custom workflow with specified stages.

    Each stage is a list of task names that run in parallel.
    Tasks in stage N depend on ALL tasks in stage N-1.

    Example:
        stages = [
            ["Start"],           # Stage 0: no dependencies
            ["TaskA", "TaskB"],  # Stage 1: both depend on Start
            ["TaskC", "TaskD"],  # Stage 2: both depend on TaskA, TaskB
            ["End"],             # Stage 3: depends on TaskC, TaskD
        ]
    """
    if len(stages) < 2:
        raise ValueError("Need at least 2 stages")

    tasks = []
    prev_stage_ids = []

    for stage_idx, stage_tasks in enumerate(stages):
        current_stage_ids = []

        for task_name in stage_tasks:
            task_id = task_name.lower().replace(" ", "_")

            task = {
                "id": task_id,
                "name": task_name,
                "plugin": kwargs.get("plugin", "command"),
                "config": {"cmd": "echo", "args": [f"Executing {task_name}"]},
            }

            if prev_stage_ids:
                task["depends_on"] = list(prev_stage_ids)

            tasks.append(task)
            current_stage_ids.append(task_id)

        prev_stage_ids = current_stage_ids

    return {
        "name": kwargs.get("workflow_name", "Custom Workflow"),
        "config": kwargs.get("config", {}),
        "tasks": tasks,
    }


def generate_custom_workflow_from_string(dag_spec: str, **kwargs) -> Dict[str, Any]:
    """
    Parse a DAG specification string and generate workflow.

    Format: comma-separated stages, semicolon-separated levels
    Example: "Start; A,B; B1,B2,B3; End"

    Means:
        Level 0: Start
        Level 1: A, B (both depend on Start)
        Level 2: B1, B2, B3 (all depend on A, B)
        Level 3: End (depends on B1, B2, B3)
    """
    levels = [level.strip() for level in dag_spec.split(";")]

    if len(levels) < 2:
        raise ValueError("DAG spec needs at least 2 levels (use ; to separate)")

    stages = []
    for level in levels:
        tasks_in_level = [t.strip() for t in level.split(",")]
        stages.append(tasks_in_level)

    return generate_custom_workflow(stages, **kwargs)


def add_notifications(
    workflow: Dict[str, Any],
    api_url: str,
    events: List[str],
    plugin: str = "custom_notify",
    targets: List[str] = None,
    target_field: str = "user_ids",
    headers: Dict[str, str] = None,
) -> Dict[str, Any]:
    """
    Add notification configuration to workflow.

    Args:
        workflow: Workflow dict to add notifications to
        api_url: Notification API endpoint
        events: List of events to notify on
        plugin: Notification plugin to use (default: custom_notify)
        targets: List of user IDs or targets to notify
        target_field: Field name for targets in API body
        headers: Optional HTTP headers for the API request
    """
    message_templates = {
        "workflow_start": "🚀 Workflow {workflow_name} started",
        "workflow_complete": "✅ Workflow {workflow_name} completed",
        "workflow_failed": "❌ Workflow {workflow_name} failed",
        "task_start": "→ Task {task_id} started",
        "task_success": "✅ Task {task_id} succeeded",
        "task_failure": "❌ Task {task_id} failed",
    }

    notifications = []
    for event in events:
        message_template = message_templates.get(event, f"Event: {event}")

        config = {
            "api_url": api_url,
            "body_template": message_template,
            "target_field": target_field,
        }

        if targets:
            config["targets"] = targets

        if headers:
            config["headers"] = headers

        notifications.append({
            "event": event,
            "plugin": plugin,
            "config": config,
        })

    workflow["notifications"] = notifications
    return workflow


def validate_workflow(workflow: Dict[str, Any]) -> tuple:
    """Validate workflow structure. Returns (is_valid, errors)."""
    errors = []

    if "name" not in workflow:
        errors.append("Missing required field: 'name'")

    if "tasks" not in workflow:
        errors.append("Missing required field: 'tasks'")
        return False, errors

    if not isinstance(workflow["tasks"], list):
        errors.append("'tasks' must be a list")
        return False, errors

    if len(workflow["tasks"]) == 0:
        errors.append("'tasks' cannot be empty")

    task_ids = set()
    for task in workflow["tasks"]:
        if "id" not in task:
            errors.append("Task missing 'id' field")
            continue
        if "plugin" not in task:
            errors.append(f"Task '{task.get('id', '?')}' missing 'plugin' field")

        tid = task["id"]
        if tid in task_ids:
            errors.append(f"Duplicate task ID: '{tid}'")
        task_ids.add(tid)

        # Check dependencies exist
        for dep in task.get("depends_on", []):
            if dep not in task_ids and dep not in [t["id"] for t in workflow["tasks"]]:
                # Allow forward references but check at runtime
                pass

    return len(errors) == 0, errors


def visualize_workflow(workflow: Dict[str, Any]) -> str:
    """Generate ASCII visualization of workflow."""
    tasks = {t["id"]: t for t in workflow["tasks"]}

    lines = []
    lines.append("\nWorkflow DAG:")
    lines.append("=" * 40)

    for task in workflow["tasks"]:
        tid = task["id"]
        deps = task.get("depends_on", [])

        if not deps:
            lines.append(f"  [START] --> {tid}")
        else:
            dep_str = ", ".join(deps)
            lines.append(f"  {dep_str} --> {tid}")

    lines.append("=" * 40 + "\n")
    return "\n".join(lines)


def interactive_mode(output_file: str = None):
    """Interactive workflow generation."""
    print("\n" + "="*50)
    print("  Workflow Generator (Interactive Mode)")
    print("="*50)

    workflow_name = input("Workflow name [My Workflow]: ").strip() or "My Workflow"
    workflow_type = input(
        "Workflow type:\n"
        "  1. Linear (A -> B -> C)\n"
        "  2. Parallel (A -> [B, C, D])\n"
        "  3. Diamond (A -> B,C -> D)\n"
        "  4. Fan-in/Fan-out (A -> [B,C,D] -> E)\n"
        "Select [1-4]: "
    ).strip()

    task_names = []
    while True:
        task = input(f"Task {len(task_names) + 1} name (or Enter to finish): ").strip()
        if not task:
            break
        task_names.append(task)

    if len(task_names) < 2:
        print("Need at least 2 tasks!")
        return None

    add_notify = input("Add WeChat notifications? [y/N]: ").strip().lower() == 'y'
    webhook_url = None
    notify_events = []

    if add_notify:
        webhook_url = input("Webhook URL: ").strip()
        if not webhook_url:
            webhook_url = os.environ.get("WECOM_WEBHOOK_URL", "")
        print("Select events to notify:")
        print("  1. workflow_start")
        print("  2. workflow_complete")
        print("  3. task_failure")
        print("  4. all")
        events_input = input("Select [1-4]: ").strip()

        event_map = {
            "1": ["workflow_start"],
            "2": ["workflow_complete"],
            "3": ["task_failure"],
            "4": ["workflow_start", "workflow_complete", "task_failure"],
        }
        notify_events = event_map.get(events_input, [])

    # Generate workflow
    kwargs = {"workflow_name": workflow_name}

    if workflow_type == "1":
        workflow = generate_linear_workflow(task_names, **kwargs)
    elif workflow_type == "2":
        workflow = generate_parallel_workflow(task_names, **kwargs)
    elif workflow_type == "3":
        workflow = generate_diamond_workflow(task_names, **kwargs)
    elif workflow_type == "4":
        workflow = generate_fan_in_out_workflow(task_names, **kwargs)
    else:
        print("Invalid workflow type")
        return None

    if add_notify and webhook_url:
        workflow = add_notifications(workflow, webhook_url, notify_events)

    # Ask for output file if not specified
    if not output_file:
        save_path = input("\nSave to file? (path or Enter to skip): ").strip()
        if save_path:
            output_file = save_path

    # Output
    yaml_str = yaml.dump(workflow, allow_unicode=True, default_flow_style=False, sort_keys=False)

    if output_file:
        with open(output_file, 'w') as f:
            f.write(yaml_str)
        print(f"✅ Saved to: {output_file}")
        print(visualize_workflow(workflow))
    else:
        print("\n" + "="*50)
        print("Generated Workflow:")
        print("="*50)
        print(yaml_str)
        print(visualize_workflow(workflow))

    return workflow


def main():
    parser = argparse.ArgumentParser(
        description="Generate workflow YAML from templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate linear workflow
  python tools/generate_workflow.py --linear "Init" "Process" "Cleanup"

  # Generate diamond workflow
  python tools/generate_workflow.py --diamond "Start" "Task A" "Task B" "Finish"

  # Generate with notifications
  python tools/generate_workflow.py --diamond "Start" "A" "B" "End" --notify

  # Interactive mode
  python tools/generate_workflow.py --interactive

  # Validate existing workflow
  python tools/generate_workflow.py --validate config/workflows/example.yaml
        """
    )

    parser.add_argument("--linear", nargs='+', metavar="TASK",
                        help="Generate linear workflow: task1 -> task2 -> ...")
    parser.add_argument("--parallel", nargs='+', metavar="TASK",
                        help="Generate parallel workflow: task1 -> [task2, task3, ...]")
    parser.add_argument("--diamond", nargs='+', metavar="TASK",
                        help="Generate diamond workflow: task1 -> task2,task3 -> task4")
    parser.add_argument("--fanout", nargs='+', metavar="TASK",
                        help="Generate fan-in/fan-out workflow")
    parser.add_argument("--custom", metavar="STAGES",
                        help="Custom DAG: semicolon-separated levels, comma-separated tasks\n"
                             "Example: 'Start;A,B;C,D;End' creates: Start -> [A,B] -> [C,D] -> End")
    parser.add_argument("--name", help="Workflow name")
    parser.add_argument("--plugin", default="command", help="Plugin to use (default: command)")
    parser.add_argument("--notify", action="store_true", help="Add notifications")
    parser.add_argument("--api-url", help="Notification API endpoint URL")
    parser.add_argument("--targets", nargs='+', metavar="USER",
                        help="User IDs to notify (for notification API)")
    parser.add_argument("--target-field", default="user_ids",
                        help="Field name for targets in API body (default: user_ids)")
    parser.add_argument("--notify-header", action="append", dest="notify_headers",
                        metavar="KEY:VALUE", help="HTTP header for notification API (format: Key:Value)")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--validate", help="Validate existing workflow YAML file")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Interactive mode")

    args = parser.parse_args()

    # Handle validation mode
    if args.validate:
        with open(args.validate, 'r') as f:
            workflow = yaml.safe_load(f)
        valid, errors = validate_workflow(workflow)
        if valid:
            print(f"✅ Workflow '{workflow.get('name', '?')}' is valid")
            print(visualize_workflow(workflow))
        else:
            print(f"❌ Workflow validation failed:")
            for err in errors:
                print(f"   - {err}")
        return

    # Handle interactive mode
    if args.interactive:
        workflow = interactive_mode(args.output)
        if not workflow:
            return
    else:
        # Generate from template
        task_names = None
        workflow_type = None

        if args.linear:
            task_names = args.linear
            workflow = generate_linear_workflow(task_names)
        elif args.parallel:
            task_names = args.parallel
            workflow = generate_parallel_workflow(task_names)
        elif args.diamond:
            task_names = args.diamond
            workflow = generate_diamond_workflow(task_names)
        elif args.fanout:
            task_names = args.fanout
            workflow = generate_fan_in_out_workflow(task_names)
        elif args.custom:
            workflow = generate_custom_workflow_from_string(args.custom)
        else:
            parser.print_help()
            return

        if args.name:
            workflow["name"] = args.name

    # Add notifications if requested
    if args.notify:
        api_url = args.api_url or os.environ.get("NOTIFY_API_URL", "")
        if api_url:
            # Parse headers
            headers = None
            if args.notify_headers:
                headers = {}
                for h in args.notify_headers:
                    if ":" in h:
                        key, value = h.split(":", 1)
                        headers[key.strip()] = value.strip()

            workflow = add_notifications(
                workflow,
                api_url,
                ["workflow_start", "workflow_complete", "task_failure"],
                targets=args.targets,
                target_field=args.target_field,
                headers=headers,
            )
        else:
            print("⚠️  No API URL provided (use --api-url or set NOTIFY_API_URL)")

    # Validate
    valid, errors = validate_workflow(workflow)
    if not valid:
        print(f"❌ Generated workflow has validation errors:")
        for err in errors:
            print(f"   - {err}")
        return

    # Output
    yaml_str = yaml.dump(workflow, allow_unicode=True, default_flow_style=False, sort_keys=False)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(yaml_str)
        print(f"✅ Workflow saved to: {args.output}")
    else:
        print("\n" + "="*50)
        print("Generated Workflow:")
        print("="*50)
        print(yaml_str)

    print(visualize_workflow(workflow))


if __name__ == "__main__":
    main()
