"""
Tests for Plugin system.
"""

import pytest
import plugins  # Load all plugins
from core.plugin import Plugin, PluginRegistry, register_plugin, get_plugin


class TestPluginRegistry:
    """Test PluginRegistry functionality."""

    def test_register_plugin(self):
        """Test plugin registration via decorator."""
        @register_plugin("test_plugin")
        class TestPlugin(Plugin):
            name = "test_plugin"

            def execute(self, context):
                return {"result": "test"}

        assert PluginRegistry.get("test_plugin") == TestPlugin

    def test_create_plugin(self):
        """Test plugin creation via registry."""
        @register_plugin("creatable_plugin")
        class CreatablePlugin(Plugin):
            name = "creatable_plugin"

            def execute(self, context):
                return {}

        plugin = PluginRegistry.create("creatable_plugin")
        assert plugin is not None
        assert isinstance(plugin, CreatablePlugin)

    def test_create_nonexistent_plugin(self):
        """Test that creating non-existent plugin returns None."""
        plugin = PluginRegistry.create("nonexistent_plugin")
        assert plugin is None

    def test_list_plugins(self):
        """Test listing all registered plugins."""
        plugins = PluginRegistry.list_plugins()
        assert isinstance(plugins, list)


class TestPluginInterface:
    """Test Plugin base class interface."""

    def test_validate_default(self):
        """Test that validate returns True by default."""
        class MyPlugin(Plugin):
            name = "my_plugin"

            def execute(self, context):
                return {}

        plugin = MyPlugin()
        assert plugin.validate({}) is True

    def test_initialize_flag(self):
        """Test that _initialized flag is set after initialize."""
        class MyPlugin(Plugin):
            name = "my_plugin"

            def execute(self, context):
                return {}

            def initialize(self, config):
                super().initialize(config)

        plugin = MyPlugin()
        assert plugin._initialized is False
        plugin.initialize({})
        assert plugin._initialized is True

    def test_execute_returns_dict(self):
        """Test that execute should return a dict."""
        class MyPlugin(Plugin):
            name = "my_plugin"

            def execute(self, context):
                return {"success": True, "data": "test"}

        plugin = MyPlugin()
        result = plugin.execute({})

        assert isinstance(result, dict)
        assert result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
