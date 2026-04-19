"""
Plugin loader.
Automatically imports all plugins to register them with the plugin registry.
"""

import importlib
import pkgutil
import logging

logger = logging.getLogger(__name__)


def load_plugins():
    """
    Load and register all plugins.
    Call this before running a workflow to ensure all plugins are available.
    """
    plugin_packages = [
        "plugins.builtin",
        "plugins.notification",
        "plugins.alert",
    ]

    total_loaded = 0

    for package_name in plugin_packages:
        try:
            package = importlib.import_module(package_name)

            # Walk through the package and import all submodules
            for importer, modname, ispkg in pkgutil.walk_packages(
                package.__path__,
                package.__name__ + "."
            ):
                if not ispkg and not modname.endswith("__"):
                    try:
                        importlib.import_module(modname)
                        total_loaded += 1
                    except Exception as e:
                        logger.warning(f"Failed to load plugin module {modname}: {e}")

        except ImportError as e:
            logger.warning(f"Failed to import plugin package {package_name}: {e}")

    logger.info(f"Loaded {total_loaded} plugin modules")


def get_available_plugins():
    """Return list of available plugin names."""
    from core.plugin import PluginRegistry
    return PluginRegistry.list_plugins()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_plugins()
    print("Available plugins:", get_available_plugins())

# Auto-load plugins when package is imported
load_plugins()
