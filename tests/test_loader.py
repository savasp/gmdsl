import os
import shutil
import tempfile

import pytest

from gmdsl.loader import AstLoader
from gmdsl.parser import Parser


class TestAstLoader:
    def test_load_single_file(self, setup_test_files):
        """Test loading a single file without imports."""
        test_file_path = os.path.join(setup_test_files, "single_file.gm")

        # Create a test file
        with open(test_file_path, "w") as f:
            f.write("""
namespace SingleFile;

node Person {
    name: String
    age: Integer
}

node Company {
    name: String
}

edge WorksAt: Person -> Company {
    position: String
}
""")

        # Load the file
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Check that AST was loaded correctly
        assert len(loaded_asts) == 1
        assert test_file_path in loaded_asts

        doc = loaded_asts[test_file_path]
        assert doc.namespace.name == "SingleFile"
        assert len(doc.declarations) == 3

        # Verify node declarations
        nodes = [
            d
            for d in doc.declarations
            if hasattr(d, "properties") and not hasattr(d, "source_node")
        ]
        assert len(nodes) == 2

        # Verify edge declarations
        edges = [d for d in doc.declarations if hasattr(d, "source_node")]
        assert len(edges) == 1
        edge = edges[0]
        assert edge.name == "WorksAt"
        assert edge.source_node == "Person"
        assert edge.target_node == "Company"

    def test_load_with_imports(self, setup_test_files):
        """Test loading a file with imports."""
        base_file_path = os.path.join(setup_test_files, "base_types.gm")
        main_file_path = os.path.join(setup_test_files, "main_model.gm")

        # Create base file with types
        with open(base_file_path, "w") as f:
            f.write("""
namespace BaseTypes;

type Address {
    street: String
    city: String
    zipCode: String
}

type ContactInfo {
    email: String
    phone: String
}
""")

        # Create main file that imports the base file
        with open(main_file_path, "w") as f:
            f.write(f"""
namespace MainModel;

import "{os.path.basename(base_file_path)}";

node Person {{
    name: String
    contact: BaseTypes.ContactInfo
    address: BaseTypes.Address
}}
""")

        # Load the main file (which should also load the imported file)
        loader = AstLoader(include_paths=[setup_test_files])
        loaded_asts = loader.load(main_file_path)

        # Check that both ASTs were loaded
        assert len(loaded_asts) == 2
        assert main_file_path in loaded_asts
        assert (
            base_file_path in loaded_asts
            or os.path.abspath(base_file_path) in loaded_asts
        )

        # Check main document
        main_doc = loaded_asts[main_file_path]
        assert main_doc.namespace.name == "MainModel"
        assert len(main_doc.imports) == 1
        assert len(main_doc.declarations) == 1

        # Check base document
        base_key = (
            base_file_path
            if base_file_path in loaded_asts
            else os.path.abspath(base_file_path)
        )
        base_doc = loaded_asts[base_key]
        assert base_doc.namespace.name == "BaseTypes"
        assert len(base_doc.declarations) == 2

    def test_load_with_nested_imports(self, setup_test_files):
        """Test loading a file with nested imports."""
        types_file_path = os.path.join(setup_test_files, "common_types.gm")
        nodes_file_path = os.path.join(setup_test_files, "nodes.gm")
        edges_file_path = os.path.join(setup_test_files, "edges.gm")

        # Create types file
        with open(types_file_path, "w") as f:
            f.write("""
namespace CommonTypes;

type Address {
    street: String
    city: String
    country: String
}
""")

        # Create nodes file that imports types
        with open(nodes_file_path, "w") as f:
            f.write(f"""
namespace Nodes;

import "{os.path.basename(types_file_path)}";

node Person {{
    name: String
    address: CommonTypes.Address
}}

node Company {{
    name: String
    headquarters: CommonTypes.Address
}}
""")

        # Create edges file that imports nodes (which imports types)
        with open(edges_file_path, "w") as f:
            f.write(f"""
namespace Edges;

import "{os.path.basename(nodes_file_path)}";

edge WorksAt: Nodes.Person -> Nodes.Company {{
    position: String
    startDate: Date
}}

edge LivesAt: Nodes.Person -> CommonTypes.Address {{}}
""")

        # Load the edges file (which should load all imports recursively)
        loader = AstLoader(include_paths=[setup_test_files])
        loaded_asts = loader.load(edges_file_path)

        # Check that all ASTs were loaded
        assert len(loaded_asts) == 3
        assert edges_file_path in loaded_asts
        assert (
            nodes_file_path in loaded_asts
            or os.path.abspath(nodes_file_path) in loaded_asts
        )
        assert (
            types_file_path in loaded_asts
            or os.path.abspath(types_file_path) in loaded_asts
        )

        # Verify all documents were loaded
        edges_doc = loaded_asts[edges_file_path]
        assert edges_doc.namespace.name == "Edges"
        assert len(edges_doc.imports) == 1

    def test_circular_imports(self, setup_test_files):
        """Test handling of circular imports."""
        file_a_path = os.path.join(setup_test_files, "file_a.gm")
        file_b_path = os.path.join(setup_test_files, "file_b.gm")

        # Create file A that imports file B
        with open(file_a_path, "w") as f:
            f.write(f"""
namespace FileA;

import "{os.path.basename(file_b_path)}";

node Person {{
    name: String
    company: FileB.Company
}}
""")

        # Create file B that imports file A
        with open(file_b_path, "w") as f:
            f.write(f"""
namespace FileB;

import "{os.path.basename(file_a_path)}";

node Company {{
    name: String
    owner: FileA.Person
}}
""")

        # Load file A (which should detect and handle the circular import)
        loader = AstLoader(include_paths=[setup_test_files])
        loaded_asts = loader.load(file_a_path)

        # Both files should be loaded exactly once
        assert len(loaded_asts) == 2
        assert file_a_path in loaded_asts
        assert file_b_path in loaded_asts or os.path.abspath(file_b_path) in loaded_asts

    def test_import_file_not_found(self, setup_test_files):
        """Test behavior when an import file is not found."""
        test_file_path = os.path.join(setup_test_files, "missing_import.gm")

        # Create a file that imports a non-existent file
        with open(test_file_path, "w") as f:
            f.write("""
namespace MissingImport;

import "non_existent_file.gm";

node Person {
    name: String
}
""")

        # Loading should raise an exception for the missing file
        loader = AstLoader(include_paths=[setup_test_files])
        with pytest.raises(FileNotFoundError):
            loaded_asts = loader.load(test_file_path)

    def test_include_paths(self, setup_test_files):
        """Test loading with multiple include paths."""
        # Create subdirectories for include paths
        lib_dir = os.path.join(setup_test_files, "lib")
        models_dir = os.path.join(setup_test_files, "models")
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(models_dir, exist_ok=True)

        # Create files in different directories
        lib_file_path = os.path.join(lib_dir, "common_types.gm")
        model_file_path = os.path.join(models_dir, "user_model.gm")

        with open(lib_file_path, "w") as f:
            f.write("""
namespace CommonLib;

type Address {
    street: String
    city: String
}
""")

        with open(model_file_path, "w") as f:
            f.write("""
namespace UserModel;

import "common_types.gm";  // No path, should find in include paths

node User {
    name: String
    address: CommonLib.Address
}
""")

        # Load with multiple include paths
        loader = AstLoader(include_paths=[lib_dir, models_dir])
        loaded_asts = loader.load(model_file_path)

        # Both files should be loaded
        assert len(loaded_asts) == 2
        assert model_file_path in loaded_asts

        # The lib file should be found via include paths
        lib_path_found = any(
            path
            for path in loaded_asts.keys()
            if os.path.basename(path) == "common_types.gm"
        )
        assert lib_path_found

    def test_load_syntax_error(self, setup_test_files):
        """Test handling of syntax errors in loaded files."""
        test_file_path = os.path.join(setup_test_files, "syntax_error.gm")

        # Create a file with syntax errors
        with open(test_file_path, "w") as f:
            f.write("""
namespace SyntaxError;

node Person {
    name: String
    age: Integer  # Missing semicolon or other syntax issue
    address Address  # Missing colon
}
""")

        # Loading should raise a parsing exception
        loader = AstLoader()
        with pytest.raises(Exception):
            loaded_asts = loader.load(test_file_path)

    def test_load_directory(self, setup_test_files):
        """Test loading all files from a directory."""
        # Create multiple files in the directory
        file1_path = os.path.join(setup_test_files, "model1.gm")
        file2_path = os.path.join(setup_test_files, "model2.gm")

        with open(file1_path, "w") as f:
            f.write("""
namespace Model1;

node Person {
    name: String
}
""")

        with open(file2_path, "w") as f:
            f.write("""
namespace Model2;

node Company {
    name: String
}
""")

        # Load all files from the directory
        loader = AstLoader()
        loaded_asts = loader.load_directory(setup_test_files)

        # Should load both files
        assert len(loaded_asts) >= 2
        assert any(path.endswith("model1.gm") for path in loaded_asts.keys())
        assert any(path.endswith("model2.gm") for path in loaded_asts.keys())

    def test_load_with_absolute_imports(self, setup_test_files):
        """Test loading with absolute import paths."""
        # Create files for testing
        base_file_path = os.path.join(setup_test_files, "base.gm")
        main_file_path = os.path.join(setup_test_files, "main.gm")

        with open(base_file_path, "w") as f:
            f.write("""
namespace Base;

type Address {
    street: String
    city: String
}
""")

        # Use absolute path in import statement
        with open(main_file_path, "w") as f:
            f.write(f"""
namespace Main;

import "{base_file_path}";  // Absolute path

node Person {{
    name: String
    address: Base.Address
}}
""")

        # Load the file with absolute import path
        loader = AstLoader()
        loaded_asts = loader.load(main_file_path)

        # Both files should be loaded
        assert len(loaded_asts) == 2
        assert main_file_path in loaded_asts
        assert base_file_path in loaded_asts

        # Verify imports
        main_doc = loaded_asts[main_file_path]
        assert len(main_doc.imports) == 1
        assert main_doc.imports[0].path == base_file_path

    def test_import_resolution_precedence(self, setup_test_files):
        """Test import resolution precedence between relative and include paths."""
        # Create subdirectory
        subdir = os.path.join(setup_test_files, "subdir")
        os.makedirs(subdir, exist_ok=True)

        # Create two files with the same name but in different locations
        types1_path = os.path.join(setup_test_files, "types.gm")
        types2_path = os.path.join(subdir, "types.gm")
        main_path = os.path.join(subdir, "main.gm")

        with open(types1_path, "w") as f:
            f.write("""
namespace GlobalTypes;

type Address {
    street: String
}
""")

        with open(types2_path, "w") as f:
            f.write("""
namespace LocalTypes;

type Address {
    street: String
    city: String  // Added field to differentiate
}
""")

        with open(main_path, "w") as f:
            f.write("""
namespace Main;

import "types.gm";  // Should resolve to the local file in the same directory first

node Person {
    name: String
    address: LocalTypes.Address  // Using namespace to verify which file was imported
}
""")

        # Load with both global and local include paths
        loader = AstLoader(include_paths=[setup_test_files, subdir])
        loaded_asts = loader.load(main_path)

        # Check that the local types.gm was loaded
        assert len(loaded_asts) == 2
        assert main_path in loaded_asts

        # Find the loaded types module
        types_loaded = next(
            (doc for path, doc in loaded_asts.items() if path.endswith("types.gm")),
            None,
        )
        assert types_loaded is not None
        assert types_loaded.namespace.name == "LocalTypes"  # Should be the local one

    def test_custom_parser(self):
        """Test loading with a custom parser."""

        # Create a mock custom parser
        class MockParser(Parser):
            def parse(self, source):
                doc = super().parse(source)
                # Add a custom marker to verify this parser was used
                doc.custom_parser_used = True
                return doc

        # Use temp directory for this test
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file_path = os.path.join(temp_dir, "test.gm")

            with open(test_file_path, "w") as f:
                f.write("""
namespace Test;

node Person {
    name: String
}
""")

            # Load with custom parser
            loader = AstLoader(parser=MockParser())
            loaded_asts = loader.load(test_file_path)

            # Verify custom parser was used
            assert len(loaded_asts) == 1
            assert test_file_path in loaded_asts
            assert hasattr(loaded_asts[test_file_path], "custom_parser_used")
            assert loaded_asts[test_file_path].custom_parser_used is True

    def test_load_with_search_paths_only(self):
        """Test loading a file using only search paths without direct file path."""
        # Use temp directory for this test
        with tempfile.TemporaryDirectory() as temp_dir:
            lib_dir = os.path.join(temp_dir, "lib")
            os.makedirs(lib_dir, exist_ok=True)

            test_file_path = os.path.join(lib_dir, "model.gm")

            with open(test_file_path, "w") as f:
                f.write("""
namespace TestModel;

node Person {
    name: String
}
""")

            # Load by filename only, using search paths
            loader = AstLoader(include_paths=[lib_dir])
            loaded_asts = loader.load("model.gm")  # No path, just filename

            # Should find and load the file
            assert len(loaded_asts) == 1
            loaded_path = next(iter(loaded_asts.keys()))
            assert os.path.basename(loaded_path) == "model.gm"

            # Verify contents
            doc = next(iter(loaded_asts.values()))
            assert doc.namespace.name == "TestModel"

    def test_file_extension_validation(self, setup_test_files):
        """Test validation of file extensions."""
        test_file_path = os.path.join(setup_test_files, "invalid_extension.txt")

        with open(test_file_path, "w") as f:
            f.write("""
namespace InvalidExtension;

node Person {
    name: String
}
""")

        # Should reject non-.gm files by default
        loader = AstLoader()
        with pytest.raises(Exception):
            loaded_asts = loader.load(test_file_path)

        # Should accept with allow_any_extension=True
        loader = AstLoader(allow_any_extension=True)
        loaded_asts = loader.load(test_file_path)
        assert len(loaded_asts) == 1

    def test_error_recovery(self, setup_test_files):
        """Test error recovery when some files fail to load."""
        valid_file_path = os.path.join(setup_test_files, "valid.gm")
        invalid_file_path = os.path.join(setup_test_files, "invalid.gm")

        with open(valid_file_path, "w") as f:
            f.write("""
namespace Valid;

node Person {
    name: String
}
""")

        with open(invalid_file_path, "w") as f:
            f.write("""
namespace Invalid;

node Person {
    name String  # Missing colon (syntax error)
}
""")

        # Should still load the valid file even if invalid file fails
        loader = AstLoader(error_on_invalid_file=False)
        loaded_asts = loader.load_directory(setup_test_files)

        # At least the valid file should be loaded
        assert valid_file_path in loaded_asts
        assert len(loaded_asts) >= 1
