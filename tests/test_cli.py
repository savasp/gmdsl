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
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gmdsl.cli import cli, generate, validate
from gmdsl.loader import AstLoader
from gmdsl.validation import ValidationError


class TestCliCommands:
    """Test suite for the CLI commands."""

    @pytest.fixture
    def runner(self):
        """Provides a Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_ast_loader(self):
        """Mock for the AstLoader to avoid file system dependencies."""
        with patch("gmdsl.cli.AstLoader") as mock:
            # Setup mock for successful loading
            loader_instance = MagicMock()
            loader_instance.load.return_value = {"test.gm": MagicMock()}
            loader_instance.errors = []
            mock.return_value = loader_instance
            yield mock

    @pytest.fixture
    def mock_validation(self):
        """Mock for the validation function."""
        with patch("gmdsl.cli.validate_asts") as mock:
            # Default to no validation errors
            mock.return_value = []
            yield mock

    @pytest.fixture
    def mock_run_generation(self):
        """Mock for the code generation function."""
        with patch("gmdsl.cli.run_generation") as mock:
            yield mock

    def test_validate_command_success(self, runner, mock_ast_loader, mock_validation):
        """Test that the validate command works correctly with a valid model."""
        # Create a temporary test file
        with runner.isolated_filesystem():
            with open("valid_model.gm", "w") as f:
                f.write("namespace ValidTest; node Test { prop: String }")

            result = runner.invoke(cli, ["validate", "valid_model.gm"])

            assert result.exit_code == 0
            assert "Validation successful" in result.output
            mock_ast_loader.return_value.load.assert_called_once_with("valid_model.gm")
            mock_validation.assert_called_once()

    def test_validate_command_with_loader_errors(self, runner, mock_ast_loader):
        """Test that validation fails when there are loader errors."""
        # Setup loader with errors
        mock_ast_loader.return_value.errors = [
            MagicMock(source_path="test.gm", message="Failed to parse file")
        ]

        with runner.isolated_filesystem():
            with open("error_model.gm", "w") as f:
                f.write("invalid syntax")

            result = runner.invoke(cli, ["validate", "error_model.gm"])

            assert result.exit_code != 0
            assert "Loading Errors" in result.output

    def test_validate_command_with_validation_errors(
        self, runner, mock_ast_loader, mock_validation
    ):
        """Test that validation command reports validation errors."""
        # Setup validation errors
        mock_validation.return_value = [
            ValidationError(message="Invalid type reference", source_path="test.gm")
        ]

        with runner.isolated_filesystem():
            with open("invalid_model.gm", "w") as f:
                f.write("namespace InvalidTest; node Test { prop: InvalidType }")

            result = runner.invoke(cli, ["validate", "invalid_model.gm"])

            assert result.exit_code != 0
            assert "Validation Errors" in result.output
            assert "Invalid type reference" in result.output

    def test_generate_command_success(
        self, runner, mock_ast_loader, mock_validation, mock_run_generation
    ):
        """Test that the generate command works correctly."""
        with runner.isolated_filesystem():
            os.makedirs("output")
            with open("model.gm", "w") as f:
                f.write("namespace Test; node Test { prop: String }")

            result = runner.invoke(
                cli,
                ["generate", "model.gm", "--output", "output", "--generator", "csharp"],
            )

            assert result.exit_code == 0
            assert "Code generation completed successfully" in result.output
            mock_run_generation.assert_called_once()
            # Verify the correct arguments were passed
            args, kwargs = mock_run_generation.call_args
            assert args[0] == "csharp"  # generator name
            assert args[2] == "output"  # output directory

    def test_generate_command_with_options(
        self, runner, mock_ast_loader, mock_validation, mock_run_generation
    ):
        """Test the generate command with various options."""
        with runner.isolated_filesystem():
            os.makedirs("output")
            with open("model.gm", "w") as f:
                f.write("namespace Test; node Test { prop: String }")

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "model.gm",
                    "--output",
                    "output",
                    "--generator",
                    "csharp",
                    "--namespace",
                    "Custom.Namespace",
                    "--generate-incoming",
                    "--skip-validation",
                ],
            )

            assert result.exit_code == 0
            assert "Skipping validation step" in result.output
            assert "Using custom namespace: Custom.Namespace" in result.output
            assert "Generating incoming relationship properties" in result.output

            # Verify correct kwargs were passed to run_generation
            args, kwargs = mock_run_generation.call_args
            assert kwargs.get("namespace") == "Custom.Namespace"
            assert kwargs.get("generate_incoming") is True

    def test_generate_command_with_invalid_generator(
        self, runner, mock_ast_loader, mock_validation
    ):
        """Test generate command with a non-existent generator plugin."""
        with patch(
            "gmdsl.cli.run_generation", side_effect=ValueError("Generator not found")
        ):
            with runner.isolated_filesystem():
                os.makedirs("output")
                with open("model.gm", "w") as f:
                    f.write("namespace Test; node Test { prop: String }")

                result = runner.invoke(
                    cli,
                    [
                        "generate",
                        "model.gm",
                        "--output",
                        "output",
                        "--generator",
                        "nonexistent",
                    ],
                )

                assert result.exit_code != 0
                assert "Generation Error: Generator not found" in result.output

    def test_generate_command_with_include_paths(
        self, runner, mock_ast_loader, mock_validation, mock_run_generation
    ):
        """Test generate command with include paths for imports."""
        with runner.isolated_filesystem():
            os.makedirs("output")
            os.makedirs("includes")
            with open("model.gm", "w") as f:
                f.write('namespace Test; import "types.gm"; node Test { prop: String }')
            with open("includes/types.gm", "w") as f:
                f.write("namespace Types; type Custom { field: String }")

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "model.gm",
                    "--output",
                    "output",
                    "--generator",
                    "csharp",
                    "-I",
                    "includes",
                ],
            )

            assert result.exit_code == 0
            assert "Include paths: includes" in result.output

            # Verify AstLoader was created with include paths
            mock_ast_loader.assert_called_once_with(include_paths=["includes"])
