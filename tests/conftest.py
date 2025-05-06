import os
import shutil
import tempfile

import pytest


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test output files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)  # Clean up after the test


@pytest.fixture
def examples_dir():
    """Path to the examples directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "examples")


@pytest.fixture
def test_files_dir():
    """Path to test files directory."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_files")


@pytest.fixture(scope="function")
def setup_test_files(test_files_dir):
    """Create the test files directory if it doesn't exist."""
    os.makedirs(test_files_dir, exist_ok=True)
    yield test_files_dir
    # Files will be cleaned up by subsequent test runs
