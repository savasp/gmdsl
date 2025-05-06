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
import re
from typing import Dict, List

import pytest

from gmdsl.ast import Document
from gmdsl.codegen import run_generation
from gmdsl.parser import Parser
from gmdsl.plugins.csharp_plugin import CSharpGenerator


class TestCSharpGenerator:
    """Test suite for the C# code generator plugin."""

    def test_basic_generation(self, setup_test_files, tmp_path):
        """Test basic C# code generation with a simple model."""
        # Create a test model file
        test_file_path = os.path.join(setup_test_files, "simple_model.gm")
        with open(test_file_path, "w") as f:
            f.write("""
namespace TestModel;

type Location {
    name: String
    latitude: Float
    longitude: Float
}

node Person {
    firstName: String
    lastName: String
    dateOfBirth: Date
    placeOfBirth: Location
}

edge Friend: Person <-> Person {
    metOn: Date
}

edge Parent: Person -> Person {
    role: String
}
""")

        # Parse the test file
        parser = Parser()
        ast = parser.parse_file(test_file_path)
        loaded_asts = {test_file_path: ast}

        # Generate C# code
        generator = CSharpGenerator()
        output_dir = str(tmp_path)
        generator.generate(loaded_asts, output_dir)

        # Check if output directory and model directory were created
        model_dir = os.path.join(output_dir, "Models")
        assert os.path.exists(model_dir)

        # Check if all expected files were created
        expected_files = [
            "GraphModel.cs",
            "Person.cs",
            "Location.cs",
            "Friend.cs",
            "Parent.cs",
        ]
        for file_name in expected_files:
            assert os.path.exists(os.path.join(model_dir, file_name))

        # Check if Person.cs has the correct properties
        with open(os.path.join(model_dir, "Person.cs")) as f:
            person_content = f.read()
            assert "public string FirstName { get; set; }" in person_content
            assert "public string LastName { get; set; }" in person_content
            assert "public DateTime DateOfBirth { get; set; }" in person_content
            assert "public Location PlaceOfBirth { get; set; }" in person_content
            # By default, should generate only outgoing relationship properties without "Outgoing" suffix
            assert "public ICollection<Friend> Friends { get; set; }" in person_content
            assert "public ICollection<Parent> Parents { get; set; }" in person_content
            # Should not generate incoming properties by default
            assert "FriendsIncoming" not in person_content
            assert "ParentsIncoming" not in person_content

        # Check if Friend.cs has the correct relationship and properties
        with open(os.path.join(model_dir, "Friend.cs")) as f:
            friend_content = f.read()
            assert "public Person SourcePerson { get; set; }" in friend_content
            assert "public Person TargetPerson { get; set; }" in friend_content
            assert "public DateTime MetOn { get; set; }" in friend_content
            assert "Direction: <->" in friend_content

        # Check if Parent.cs has the correct relationship
        with open(os.path.join(model_dir, "Parent.cs")) as f:
            parent_content = f.read()
            assert "Direction: ->" in parent_content

    def test_custom_namespace(self, setup_test_files, tmp_path):
        """Test C# code generation with a custom namespace."""
        # Create a test model file
        test_file_path = os.path.join(setup_test_files, "simple_model.gm")
        with open(test_file_path, "w") as f:
            f.write("""
namespace DefaultNamespace;

node Person {
    name: String
}
""")

        # Parse the test file
        parser = Parser()
        ast = parser.parse_file(test_file_path)
        loaded_asts = {test_file_path: ast}

        # Generate C# code with custom namespace
        generator = CSharpGenerator()
        output_dir = str(tmp_path)
        custom_namespace = "MyCustom.Namespace"
        generator.generate(loaded_asts, output_dir, namespace=custom_namespace)

        # Check if the generated code uses the custom namespace
        with open(os.path.join(output_dir, "Models", "Person.cs")) as f:
            content = f.read()
            assert f"namespace {custom_namespace}.Models" in content

    def test_generate_incoming_properties(self, setup_test_files, tmp_path):
        """Test C# code generation with incoming relationship properties."""
        # Create a test model file
        test_file_path = os.path.join(setup_test_files, "model_with_relationships.gm")
        with open(test_file_path, "w") as f:
            f.write("""
namespace TestModel;

node Person {
    name: String
}

node Document {
    title: String
}

edge Authored: Person -> Document {
    date: Date
}

edge Friend: Person <-> Person {
    since: Date
}
""")

        # Parse the test file
        parser = Parser()
        ast = parser.parse_file(test_file_path)
        loaded_asts = {test_file_path: ast}

        # Generate C# code with generate_incoming=True
        generator = CSharpGenerator()
        output_dir = str(tmp_path)
        generator.generate(loaded_asts, output_dir, generate_incoming=True)

        # Check Person.cs for both outgoing and incoming properties
        with open(os.path.join(output_dir, "Models", "Person.cs")) as f:
            person_content = f.read()
            # Should have outgoing property for Authored with Outgoing suffix
            assert (
                "public ICollection<Authored> AuthoredsOutgoing { get; set; }"
                in person_content
            )
            # Should have both outgoing and incoming for Friend
            assert (
                "public ICollection<Friend> FriendsOutgoing { get; set; }"
                in person_content
            )
            assert (
                "public ICollection<Friend> FriendsIncoming { get; set; }"
                in person_content
            )

        # Check Document.cs for incoming properties
        with open(os.path.join(output_dir, "Models", "Document.cs")) as f:
            document_content = f.read()
            # Should have incoming property for Authored
            assert (
                "public ICollection<Authored> AuthoredsIncoming { get; set; }"
                in document_content
            )

    def test_complex_types(self, setup_test_files, tmp_path):
        """Test C# code generation with complex types and nested properties."""
        # Create a test model file
        test_file_path = os.path.join(setup_test_files, "complex_types_model.gm")
        with open(test_file_path, "w") as f:
            f.write("""
namespace ComplexTypesTest;

type Address {
    street: String
    city: String
    country: String
}

type ContactInfo {
    email: String
    phone: String
    address: Address
}

node Person {
    name: String
    contact: ContactInfo
}
""")

        # Parse the test file
        parser = Parser()
        ast = parser.parse_file(test_file_path)
        loaded_asts = {test_file_path: ast}

        # Generate C# code
        generator = CSharpGenerator()
        output_dir = str(tmp_path)
        generator.generate(loaded_asts, output_dir)

        # Check if all complex types were created
        assert os.path.exists(os.path.join(output_dir, "Models", "Address.cs"))
        assert os.path.exists(os.path.join(output_dir, "Models", "ContactInfo.cs"))
        assert os.path.exists(os.path.join(output_dir, "Models", "Person.cs"))

        # Check if ContactInfo has the Address property
        with open(os.path.join(output_dir, "Models", "ContactInfo.cs")) as f:
            content = f.read()
            assert "public Address Address { get; set; }" in content

        # Check if Person has the ContactInfo property
        with open(os.path.join(output_dir, "Models", "Person.cs")) as f:
            content = f.read()
            assert "public ContactInfo Contact { get; set; }" in content

    def test_multiple_files_generation(self, setup_test_files, tmp_path):
        """Test C# code generation from multiple input files."""
        # Create first file with types
        types_file_path = os.path.join(setup_test_files, "types.gm")
        with open(types_file_path, "w") as f:
            f.write("""
namespace SharedTypes;

type Address {
    street: String
    city: String
}
""")

        # Create second file with nodes and edges
        model_file_path = os.path.join(setup_test_files, "model.gm")
        with open(model_file_path, "w") as f:
            f.write("""
namespace TestModel;

import "types.gm";

node Person {
    name: String
    address: Address
}

edge Lives: Person -> Address {}
""")

        # Parse both files
        parser = Parser()
        types_ast = parser.parse_file(types_file_path)
        model_ast = parser.parse_file(model_file_path)
        loaded_asts = {types_file_path: types_ast, model_file_path: model_ast}

        # Generate C# code
        generator = CSharpGenerator()
        output_dir = str(tmp_path)
        generator.generate(loaded_asts, output_dir)

        # Check for all expected files
        expected_files = ["Address.cs", "Person.cs", "Lives.cs", "GraphModel.cs"]
        for file_name in expected_files:
            assert os.path.exists(os.path.join(output_dir, "Models", file_name))

    def test_relationships_default_mode(self, setup_test_files, tmp_path):
        """Test relationship properties in default mode (no incoming properties)."""
        test_file_path = os.path.join(setup_test_files, "relationships.gm")
        with open(test_file_path, "w") as f:
            f.write("""
namespace RelationshipsTest;

node Person {
    name: String
}

node Company {
    name: String
}

edge WorksAt: Person -> Company {
    position: String
    startDate: Date
}

edge Manages: Person -> Person {
    since: Date
}

edge Friend: Person <-> Person {
    since: Date
}
""")

        parser = Parser()
        ast = parser.parse_file(test_file_path)
        loaded_asts = {test_file_path: ast}

        # Generate C# code in default mode (no incoming properties)
        generator = CSharpGenerator()
        output_dir = str(tmp_path)
        generator.generate(loaded_asts, output_dir, generate_incoming=False)

        # Check Person.cs
        with open(os.path.join(output_dir, "Models", "Person.cs")) as f:
            person_content = f.read()
            # Should have clean property names without Outgoing suffix
            assert (
                "public ICollection<WorksAt> WorksAts { get; set; }" in person_content
            )
            assert "public ICollection<Manages> Manages { get; set; }" in person_content
            assert "public ICollection<Friend> Friends { get; set; }" in person_content
            # Shouldn't have incoming properties
            assert "Incoming" not in person_content

        # Check Company.cs
        with open(os.path.join(output_dir, "Models", "Company.cs")) as f:
            company_content = f.read()
            # Shouldn't have relationship properties in default mode
            assert "WorksAt" not in company_content

    def test_relationships_with_incoming(self, setup_test_files, tmp_path):
        """Test relationship properties with incoming properties enabled."""
        test_file_path = os.path.join(setup_test_files, "relationships.gm")
        with open(test_file_path, "w") as f:
            f.write("""
namespace RelationshipsTest;

node Person {
    name: String
}

node Company {
    name: String
}

edge WorksAt: Person -> Company {
    position: String
    startDate: Date
}

edge Manages: Person -> Person {
    since: Date
}

edge Friend: Person <-> Person {
    since: Date
}
""")

        parser = Parser()
        ast = parser.parse_file(test_file_path)
        loaded_asts = {test_file_path: ast}

        # Generate C# code with incoming properties
        generator = CSharpGenerator()
        output_dir = str(tmp_path)
        generator.generate(loaded_asts, output_dir, generate_incoming=True)

        # Check Person.cs
        with open(os.path.join(output_dir, "Models", "Person.cs")) as f:
            person_content = f.read()
            # Should have Outgoing suffix
            assert (
                "public ICollection<WorksAt> WorksAtsOutgoing { get; set; }"
                in person_content
            )
            assert (
                "public ICollection<Manages> ManagesOutgoing { get; set; }"
                in person_content
            )
            assert (
                "public ICollection<Friend> FriendsOutgoing { get; set; }"
                in person_content
            )
            # Should also have incoming for self-references (Friend and Manages)
            assert (
                "public ICollection<Manages> ManagesIncoming { get; set; }"
                in person_content
            )
            assert (
                "public ICollection<Friend> FriendsIncoming { get; set; }"
                in person_content
            )

        # Check Company.cs
        with open(os.path.join(output_dir, "Models", "Company.cs")) as f:
            company_content = f.read()
            # Should have incoming WorksAt since generate_incoming is True
            assert (
                "public ICollection<WorksAt> WorksAtsIncoming { get; set; }"
                in company_content
            )

    def test_relationship_classes(self, setup_test_files, tmp_path):
        """Test the generation of relationship classes with source and target properties."""
        test_file_path = os.path.join(setup_test_files, "relationship_classes.gm")
        with open(test_file_path, "w") as f:
            f.write("""
namespace RelationshipClassesTest;

node Person {
    name: String
}

node Document {
    title: String
}

edge Authored: Person -> Document {
    date: Date
    role: String
}
""")

        parser = Parser()
        ast = parser.parse_file(test_file_path)
        loaded_asts = {test_file_path: ast}

        # Generate C# code
        generator = CSharpGenerator()
        output_dir = str(tmp_path)
        generator.generate(loaded_asts, output_dir)

        # Check Authored.cs relationship class
        with open(os.path.join(output_dir, "Models", "Authored.cs")) as f:
            authored_content = f.read()
            # Should have source and target properties with proper names
            assert "public Person SourcePerson { get; set; }" in authored_content
            assert "public Document TargetDocument { get; set; }" in authored_content
            # Should have edge properties
            assert "public DateTime Date { get; set; }" in authored_content
            assert "public string Role { get; set; }" in authored_content

    def test_type_mapping(self, setup_test_files, tmp_path):
        """Test proper mapping of GMDsl types to C# types."""
        test_file_path = os.path.join(setup_test_files, "type_mapping.gm")
        with open(test_file_path, "w") as f:
            f.write("""
namespace TypeMappingTest;

node Entity {
    stringProp: String
    intProp: Integer
    floatProp: Float
    boolProp: Boolean
    dateProp: Date
}
""")

        parser = Parser()
        ast = parser.parse_file(test_file_path)
        loaded_asts = {test_file_path: ast}

        # Generate C# code
        generator = CSharpGenerator()
        output_dir = str(tmp_path)
        generator.generate(loaded_asts, output_dir)

        # Check Entity.cs for proper type mapping
        with open(os.path.join(output_dir, "Models", "Entity.cs")) as f:
            entity_content = f.read()
            # Check each type mapping
            assert "public string StringProp { get; set; }" in entity_content
            assert "public int IntProp { get; set; }" in entity_content
            assert "public double FloatProp { get; set; }" in entity_content
            assert "public bool BoolProp { get; set; }" in entity_content
            assert "public DateTime DateProp { get; set; }" in entity_content

    def test_cli_run_generation(self, setup_test_files, tmp_path):
        """Test C# code generation through the run_generation function."""
        test_file_path = os.path.join(setup_test_files, "cli_test.gm")
        with open(test_file_path, "w") as f:
            f.write("""
namespace CliTest;

node Person {
    name: String
}

edge Friend: Person <-> Person {}
""")

        parser = Parser()
        ast = parser.parse_file(test_file_path)
        loaded_asts = {test_file_path: ast}

        # Run generation through the CLI interface function
        output_dir = str(tmp_path)
        run_generation("csharp", loaded_asts, output_dir, namespace="Custom.Cli.Test")

        # Verify files were created with the custom namespace
        with open(os.path.join(output_dir, "Models", "Person.cs")) as f:
            person_content = f.read()
            assert "namespace Custom.Cli.Test.Models" in person_content

    def test_pluralization(self, setup_test_files, tmp_path):
        """Test the pluralization logic for relationship property names."""
        test_file_path = os.path.join(setup_test_files, "pluralization_test.gm")
        with open(test_file_path, "w") as f:
            f.write("""
namespace PluralizationTest;

node Person { name: String }
node Company { name: String }
node Box { name: String }
node Bus { name: String }
node Buzz { name: String }
node Match { name: String }
node Dish { name: String }
node City { name: String }

edge WorksAt: Person -> Company {}
edge Contains: Box -> Person {}
edge Drives: Person -> Bus {}
edge Creates: Person -> Buzz {}
edge Plays: Person -> Match {}
edge Uses: Person -> Dish {}
edge LivesIn: Person -> City {}
""")

        parser = Parser()
        ast = parser.parse_file(test_file_path)
        loaded_asts = {test_file_path: ast}

        # Generate C# code
        generator = CSharpGenerator()
        output_dir = str(tmp_path)
        generator.generate(loaded_asts, output_dir)

        # Check Person.cs for proper pluralization
        with open(os.path.join(output_dir, "Models", "Person.cs")) as f:
            person_content = f.read()
            # Regular plurals
            assert (
                "public ICollection<WorksAt> WorksAts { get; set; }" in person_content
            )
            assert (
                "public ICollection<Contains> Contains { get; set; }" in person_content
            )
            # Words ending in 's', 'x', 'z', 'ch', 'sh' should add 'es'
            assert "public ICollection<Drives> Driveses { get; set; }" in person_content
            assert (
                "public ICollection<Creates> Createses { get; set; }" in person_content
            )
            assert "public ICollection<Plays> Playses { get; set; }" in person_content
            assert "public ICollection<Uses> Useses { get; set; }" in person_content
            # Words ending in 'y' should change to 'ies'
            assert (
                "public ICollection<LivesIn> LivesInies { get; set; }" in person_content
            )
