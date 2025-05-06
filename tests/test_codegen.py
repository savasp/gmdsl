# Copyright 2025 Savas Parastatidis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from unittest.mock import MagicMock, call, patch

import pytest

from gmdsl.ast import Document
from gmdsl.codegen import CodeGeneratorPlugin, discover_plugins, run_generation


class MockPlugin(CodeGeneratorPlugin):
    """Mock plugin for testing purposes."""

    def __init__(self):
        self.called = False
        self.args = None
        self.kwargs = None

    def generate(self, loaded_asts, output_dir, **kwargs):
        self.called = True
        self.args = (loaded_asts, output_dir)
        self.kwargs = kwargs


class MockPluginWithCustomParams(CodeGeneratorPlugin):
    """Mock plugin that accepts custom parameters."""

    def __init__(self):
        self.called = False
        self.args = None
        self.kwargs = None

    def generate(self, loaded_asts, output_dir, custom_param=None, another_param=None):
        self.called = True
        self.args = (loaded_asts, output_dir)
        self.kwargs = {"custom_param": custom_param, "another_param": another_param}


class TestCodeGenerator:
    """Tests for the code generator and plugin system."""

    @pytest.fixture
    def mock_entry_points(self):
        """Mock for entry points to simulate plugin discovery."""
        mock_entry_point1 = MagicMock()
        mock_entry_point1.name = "mock"
        mock_entry_point1.load.return_value = MockPlugin

        mock_entry_point2 = MagicMock()
        mock_entry_point2.name = "custom"
        mock_entry_point2.load.return_value = MockPluginWithCustomParams

        # Non-compliant plugin
        mock_entry_point3 = MagicMock()
        mock_entry_point3.name = "invalid"
        mock_entry_point3.load.return_value = str  # Not a CodeGeneratorPlugin

        # Entry point that raises an exception when loaded
        mock_entry_point4 = MagicMock()
        mock_entry_point4.name = "error"
        mock_entry_point4.load.side_effect = ImportError("Failed to load plugin")

        return [
            mock_entry_point1,
            mock_entry_point2,
            mock_entry_point3,
            mock_entry_point4,
        ]

    @patch("gmdsl.codegen._plugin_cache", {})
    @patch("importlib.metadata.entry_points")
    def test_discover_plugins(self, mock_entry_points_func, mock_entry_points):
        """Test plugin discovery from entry points."""
        mock_entry_points_func.return_value = mock_entry_points

        # Discover plugins
        plugins = discover_plugins()

        # Verify correct plugins were discovered
        assert len(plugins) == 2
        assert "mock" in plugins
        assert "custom" in plugins
        assert plugins["mock"] == MockPlugin
        assert plugins["custom"] == MockPluginWithCustomParams

        # Verify invalid plugins were filtered out
        assert "invalid" not in plugins
        assert "error" not in plugins

        # Verify plugin caching works
        with patch("importlib.metadata.entry_points") as mock_entry_points_func2:
            # This should not be called because of the cache
            mock_entry_points_func2.assert_not_called()
            plugins_again = discover_plugins()
            assert plugins_again == plugins

    @patch("gmdsl.codegen.discover_plugins")
    @patch("os.makedirs")
    def test_run_generation_with_valid_plugin(
        self, mock_makedirs, mock_discover_plugins
    ):
        """Test running a valid plugin for code generation."""
        # Create mock plugin
        mock_plugin = MockPlugin()
        mock_plugin_class = MagicMock(return_value=mock_plugin)

        # Setup mock discovery to return our plugin
        mock_discover_plugins.return_value = {"test_plugin": mock_plugin_class}

        # Create test data
        loaded_asts = {
            "test.gm": Document(namespace="test", imports=[], definitions=[])
        }
        output_dir = "/tmp/output"

        # Run generation
        run_generation("test_plugin", loaded_asts, output_dir)

        # Verify plugin was instantiated and called correctly
        mock_plugin_class.assert_called_once()
        assert mock_plugin.called
        assert mock_plugin.args[0] == loaded_asts
        assert mock_plugin.args[1] == output_dir

        # Verify output directory was created
        mock_makedirs.assert_called_once_with(output_dir, exist_ok=True)

    @patch("gmdsl.codegen.discover_plugins")
    def test_run_generation_with_invalid_plugin(self, mock_discover_plugins):
        """Test running a non-existent plugin causes appropriate error."""
        # Setup mock discovery to return empty dict
        mock_discover_plugins.return_value = {}

        # Create test data
        loaded_asts = {
            "test.gm": Document(namespace="test", imports=[], definitions=[])
        }
        output_dir = "/tmp/output"

        # Attempt to run non-existent plugin
        with pytest.raises(ValueError) as excinfo:
            run_generation("non_existent", loaded_asts, output_dir)

        # Verify error message contains plugin name
        assert "non_existent" in str(excinfo.value)

    @patch("gmdsl.codegen.discover_plugins")
    @patch("os.makedirs")
    def test_run_generation_with_custom_params(
        self, mock_makedirs, mock_discover_plugins
    ):
        """Test running a plugin that accepts custom parameters."""
        # Create mock plugin that accepts custom parameters
        mock_plugin = MockPluginWithCustomParams()
        mock_plugin_class = MagicMock(return_value=mock_plugin)

        # Setup mock discovery to return our plugin
        mock_discover_plugins.return_value = {"custom_plugin": mock_plugin_class}

        # Create test data
        loaded_asts = {
            "test.gm": Document(namespace="test", imports=[], definitions=[])
        }
        output_dir = "/tmp/output"

        # Run generation with custom parameters
        run_generation(
            "custom_plugin",
            loaded_asts,
            output_dir,
            custom_param="value",
            another_param=42,
            unsupported_param="ignored",
        )

        # Verify plugin was called with supported parameters only
        assert mock_plugin.called
        assert mock_plugin.args[0] == loaded_asts
        assert mock_plugin.args[1] == output_dir
        assert mock_plugin.kwargs["custom_param"] == "value"
        assert mock_plugin.kwargs["another_param"] == 42

    @patch("gmdsl.codegen.discover_plugins")
    @patch("os.makedirs")
    def test_run_generation_handles_plugin_exceptions(
        self, mock_makedirs, mock_discover_plugins
    ):
        """Test that exceptions from plugins are properly handled."""
        # Create mock plugin that raises an exception
        mock_plugin_class = MagicMock()
        mock_plugin_class.return_value.generate.side_effect = RuntimeError(
            "Plugin failed"
        )

        # Setup mock discovery
        mock_discover_plugins.return_value = {"error_plugin": mock_plugin_class}

        # Create test data
        loaded_asts = {
            "test.gm": Document(namespace="test", imports=[], definitions=[])
        }
        output_dir = "/tmp/output"

        # Run generation and expect exception to be propagated
        with pytest.raises(RuntimeError) as excinfo:
            run_generation("error_plugin", loaded_asts, output_dir)

        assert "Plugin failed" in str(excinfo.value)
