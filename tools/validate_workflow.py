#!/usr/bin/env python3
"""
Workflow Validator Tool

Validates workflow YAML files and checks DAG structure.
Usage:
    python tools/validate_workflow.py config/workflows/example.yaml
    python tools/validate_workflow.py --check-deps config/workflows/example.yaml
"""

import sys
import os
import yaml
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_workflow(file_path: str) -> dict:
    """Load workflow from YAML file."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)


def validate_workflow_structure(workflow: dict) -> list:
    """Validate basic workflow structure."""
    errors = []

    # Required fields
    if "name" not in workflow:
        errors.append("Missing required field: 'name'")
    if "tasks" not in workflow:
        errors.append("Missing required field: 'tasks'")
        return errors

    # Tasks validation
    if not isinstance(workflow["tasks"], list):
        errors.append("'tasks' must be a list")
        return errors

    if len(workflow["tasks"]) == 0:
        errors.append("'tasks' cannot be empty")

    task_ids = set()
    for i, task in enumerate(workflow["tasks"]):
        if "id" not in task:
            errors.append(f"Task #{i+1} missing 'id' field")
        else:
            tid = task["id"]
            if tid in task_ids:
                errors.append(f"Duplicate task ID: '{tid}'")
            task_ids.add(tid)

        if "plugin" not in task:
            tid = task.get("id", f"#{i+1}")
            errors.append(f"Task '{tid}' missing 'plugin' field")

    return errors


def validate_task_dependencies(workflow: dict) -> list:
    """Validate task dependencies (circular deps, missing refs)."""
    errors = []
    warnings = []

    task_ids = {t["id"] for t in workflow.get("tasks", [])}
    dependents = {t["id"]: t.get("depends_on", []) for t in workflow.get("tasks", [])}

    # Check for self-dependency and missing dependencies
    for task_id, deps in dependents.items():
        for dep in deps:
            if dep == task_id:
                errors.append(f"Task '{task_id}' depends on itself")
            if dep not in task_ids:
                errors.append(f"Task '{task_id}' depends on non-existent task '{dep}'")

    # Check for circular dependencies using DFS
    def has_cycle(task_id: str, visited: set, rec_stack: set) -> tuple:
        visited.add(task_id)
        rec_stack.add(task_id)

        for dep in dependents.get(task_id, []):
            if dep not in visited:
                if has_cycle(dep, visited, rec_stack):
                    return True
            elif dep in rec_stack:
                return True

        rec_stack.remove(task_id)
        return False

    visited = set()
    for task_id in task_ids:
        if task_id not in visited:
            if has_cycle(task_id, visited, set()):
                errors.append(f"Circular dependency detected involving task '{task_id}'")

    # Check for unreachable tasks
    reachable = set()

    def find_reachable(task_id: str):
        if task_id in reachable:
            return
        reachable.add(task_id)
        for dep in dependents.get(task_id, []):
            find_reachable(dep)

    # Start from tasks with no dependencies
    roots = [tid for tid, deps in dependents.items() if not deps]
    for root in roots:
        find_reachable(root)

    unreachable = task_ids - reachable
    if unreachable:
        warnings.append(f"Unreachable tasks detected: {unreachable}")

    return errors, warnings


def validate_plugins(workflow: dict) -> list:
    """Validate that referenced plugins exist."""
    errors = []
    warnings = []

    from core.plugin import PluginRegistry

    available_plugins = set(PluginRegistry.list_plugins())
    referenced_plugins = {task.get("plugin") for task in workflow.get("tasks", [])}

    for plugin in referenced_plugins:
        if plugin not in available_plugins:
            errors.append(f"Plugin not found: '{plugin}' (available: {available_plugins})")

    return errors


def visualize_workflow(workflow: dict) -> str:
    """Generate ASCII visualization of workflow DAG."""
    tasks = {t["id"]: t for t in workflow.get("tasks", [])}
    dependents = {t["id"]: t.get("depends_on", []) for t in workflow.get("tasks", [])}

    lines = []
    lines.append("\n" + "="*50)
    lines.append(" Workflow DAG Visualization")
    lines.append("="*50)

    # Group tasks by dependency level
    levels = []
    remaining = set(tasks.keys())
    processed = set()

    while remaining:
        # Find tasks with all dependencies processed
        current_level = []
        for tid in remaining:
            deps = dependents.get(tid, [])
            if all(d in processed for d in deps):
                current_level.append(tid)

        if not current_level:
            lines.append("\n⚠️  Circular dependency detected!")
            break

        levels.append(current_level)
        for tid in current_level:
            remaining.remove(tid)
            processed.add(tid)

    # Draw levels
    for i, level in enumerate(levels):
        lines.append(f"\nLevel {i}:")
        for tid in level:
            deps = dependents.get(tid, [])
            task = tasks.get(tid, {})
            plugin = task.get("plugin", "?")
            if deps:
                lines.append(f"  {', '.join(deps)} --> {tid} ({plugin})")
            else:
                lines.append(f"  [START] --> {tid} ({plugin})")

    lines.append("="*50 + "\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Validate workflow YAML files")
    parser.add_argument("workflow_file", help="Path to workflow YAML file")
    parser.add_argument("--check-deps", action="store_true",
                        help="Check task dependencies")
    parser.add_argument("--check-plugins", action="store_true",
                        help="Check plugin availability")
    parser.add_argument("--visualize", "-v", action="store_true",
                        help="Show workflow visualization")

    args = parser.parse_args()

    # Load workflow
    try:
        workflow = load_workflow(args.workflow_file)
    except FileNotFoundError:
        print(f"❌ File not found: {args.workflow_file}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"❌ YAML parse error: {e}")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f" Validating: {args.workflow_file}")
    print(f" Workflow: {workflow.get('name', '?')}")
    print(f"{'='*50}")

    all_errors = []
    all_warnings = []

    # Validate structure
    print("\n📋 Checking structure...")
    errors = validate_workflow_structure(workflow)
    if errors:
        all_errors.extend(errors)
        for err in errors:
            print(f"   ❌ {err}")
    else:
        print("   ✅ Structure valid")

    # Validate dependencies
    if args.check_deps:
        print("\n🔗 Checking dependencies...")
        errors, warnings = validate_task_dependencies(workflow)
        if errors:
            all_errors.extend(errors)
            for err in errors:
                print(f"   ❌ {err}")
        else:
            print("   ✅ Dependencies valid")
        if warnings:
            all_warnings.extend(warnings)
            for warn in warnings:
                print(f"   ⚠️  {warn}")

    # Validate plugins
    if args.check_plugins:
        print("\n🔌 Checking plugins...")
        import plugins  # Load all plugins
        errors = validate_plugins(workflow)
        if errors:
            all_errors.extend(errors)
            for err in errors:
                print(f"   ❌ {err}")
        else:
            print("   ✅ All plugins available")

    # Visualize
    if args.visualize:
        print(visualize_workflow(workflow))

    # Summary
    print("\n" + "="*50)
    if all_errors:
        print(f"❌ Validation FAILED ({len(all_errors)} errors)")
        if all_warnings:
            print(f"⚠️  Warnings: {len(all_warnings)}")
        sys.exit(1)
    elif all_warnings:
        print(f"⚠️  Validation passed with warnings ({len(all_warnings)})")
        sys.exit(0)
    else:
        print("✅ Validation PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
