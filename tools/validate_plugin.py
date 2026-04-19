#!/usr/bin/env python3
"""
Plugin Validator Tool

Validates plugin implementations against the Plugin base class interface.
Usage:
    python tools/validate_plugin.py plugins/builtin/script_plugin.py
    python tools/validate_plugin.py --dir plugins/builtin
    python tools/validate_plugin.py --all
"""

import sys
import os
import inspect
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_plugin_module(plugin_path: str):
    """Load a plugin module from file path."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("plugin_module", plugin_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_plugin_classes(module):
    """Find all classes in module that inherit from Plugin."""
    from core.plugin import Plugin

    plugin_classes = []
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, Plugin) and obj is not Plugin:
            plugin_classes.append((name, obj))
    return plugin_classes


def validate_plugin_class(class_name: str, plugin_class: type) -> list:
    """Validate a plugin class implementation."""
    errors = []
    warnings = []

    # Check required attributes
    if not hasattr(plugin_class, 'name'):
        errors.append(f"Missing class attribute: 'name'")

    # Check required methods
    if not hasattr(plugin_class, 'execute'):
        errors.append("Missing required method: 'execute(self, context)'")
    else:
        sig = inspect.signature(plugin_class.execute)
        params = list(sig.parameters.keys())
        if params != ['self', 'context']:
            warnings.append(f"execute() signature should be (self, context), got {params}")

    # Check validate method
    if hasattr(plugin_class, 'validate'):
        sig = inspect.signature(plugin_class.validate)
        params = list(sig.parameters.keys())
        if params != ['self', 'config']:
            warnings.append(f"validate() signature should be (self, config), got {params}")

    # Check optional callbacks
    optional_callbacks = ['on_start', 'on_success', 'on_failure', 'initialize', 'cleanup']
    for callback in optional_callbacks:
        if hasattr(plugin_class, callback):
            sig = inspect.signature(getattr(plugin_class, callback))
            if callback == 'initialize' and list(sig.parameters.keys()) != ['self', 'config']:
                warnings.append(f"{callback}() signature should be (self, config)")
            elif callback in ('on_start', 'on_success', 'on_failure') and list(sig.parameters.keys()) != ['self', 'context']:
                warnings.append(f"{callback}() signature should be (self, context)")

    return errors, warnings


def validate_plugin_file(plugin_path: str) -> bool:
    """Validate a single plugin file."""
    print(f"\n{'='*60}")
    print(f"Validating: {plugin_path}")
    print('='*60)

    try:
        module = load_plugin_module(plugin_path)
    except Exception as e:
        print(f"❌ ERROR: Failed to load module: {e}")
        return False

    plugin_classes = get_plugin_classes(module)

    if not plugin_classes:
        print(f"⚠️  WARNING: No Plugin subclasses found in module")
        return False

    all_valid = True
    for class_name, plugin_class in plugin_classes:
        print(f"\n📦 Plugin: {class_name}")
        print(f"   name: {getattr(plugin_class, 'name', 'NOT SET')}")
        print(f"   version: {getattr(plugin_class, 'version', 'NOT SET')}")

        errors, warnings = validate_plugin_class(class_name, plugin_class)

        if errors:
            print(f"   ❌ ERRORS:")
            for err in errors:
                print(f"      - {err}")
            all_valid = False

        if warnings:
            print(f"   ⚠️  WARNINGS:")
            for warn in warnings:
                print(f"      - {warn}")

        if not errors and not warnings:
            print(f"   ✅ Valid")

    return all_valid


def validate_plugin_directory(dir_path: str) -> bool:
    """Validate all plugin files in a directory."""
    dir_path = Path(dir_path)
    if not dir_path.exists():
        print(f"❌ ERROR: Directory not found: {dir_path}")
        return False

    all_valid = True
    for py_file in dir_path.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
        if not validate_plugin_file(str(py_file)):
            all_valid = False

    return all_valid


def validate_all_plugins() -> bool:
    """Validate all built-in plugins."""
    import plugins

    from core.plugin import PluginRegistry

    print("\n" + "="*60)
    print("Validating all registered plugins")
    print("="*60)

    plugin_names = PluginRegistry.list_plugins()

    if not plugin_names:
        print("⚠️  No plugins registered")
        return False

    print(f"\nFound {len(plugin_names)} registered plugins: {plugin_names}\n")

    all_valid = True
    for name in plugin_names:
        plugin_class = PluginRegistry.get(name)
        if plugin_class:
            print(f"\n📦 Plugin: {name}")
            errors, warnings = validate_plugin_class(name, plugin_class)

            if errors:
                print(f"   ❌ ERRORS:")
                for err in errors:
                    print(f"      - {err}")
                all_valid = False
            if warnings:
                print(f"   ⚠️  WARNINGS:")
                for warn in warnings:
                    print(f"      - {warn}")
            if not errors and not warnings:
                print(f"   ✅ Valid")

    return all_valid


def main():
    parser = argparse.ArgumentParser(description="Validate plugin implementations")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", "-f", help="Path to plugin file")
    group.add_argument("--dir", "-d", help="Path to plugin directory")
    group.add_argument("--all", "-a", action="store_true", help="Validate all registered plugins")

    args = parser.parse_args()

    if args.file:
        valid = validate_plugin_file(args.file)
    elif args.dir:
        valid = validate_plugin_directory(args.dir)
    else:
        valid = validate_all_plugins()

    print("\n" + "="*60)
    if valid:
        print("✅ All plugins valid")
        sys.exit(0)
    else:
        print("❌ Some plugins have errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
