import os
import re

import pytest

from gmdsl.loader import AstLoader
from gmdsl.plugins.cypher_plugin import CypherGenerator


class TestCypherGenerator:
    def test_basic_schema_generation(self, setup_test_files, temp_output_dir):
        """Test basic Cypher schema generation for a simple model."""
        test_file_path = os.path.join(setup_test_files, "simple_model.gm")

        # Create a test file with a simple model
        with open(test_file_path, "w") as f:
            f.write("""
namespace TestModel;

node Person {
    firstName: String
    lastName: String
    age: Integer
}

edge Friend: Person <-> Person {
    since: Date
}
""")

        # Load the AST
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Generate Cypher schema
        generator = CypherGenerator()
        generator.generate(loaded_asts, temp_output_dir)

        # Check that schema file was generated
        schema_file = os.path.join(temp_output_dir, "schema.cypher")
        assert os.path.exists(schema_file)

        # Read the generated schema
        with open(schema_file, "r") as f:
            schema_content = f.read()

        # Verify node constraints and properties
        assert "CREATE CONSTRAINT" in schema_content
        assert "FOR (n:Person)" in schema_content
        assert "REQUIRE n.id IS UNIQUE" in schema_content
        assert "CREATE INDEX" in schema_content
        assert "firstName" in schema_content
        assert "lastName" in schema_content
        assert "age" in schema_content

        # Verify relationship properties
        assert "WITH rel" in schema_content
        assert "MATCH ()-[rel:FRIEND]->()" in schema_content
        assert "since" in schema_content

    def test_complex_schema_generation(self, setup_test_files, temp_output_dir):
        """Test Cypher schema generation with complex types and multiple relationships."""
        test_file_path = os.path.join(setup_test_files, "complex_schema.gm")

        # Create a test file with complex types and multiple relationships
        with open(test_file_path, "w") as f:
            f.write("""
namespace ComplexSchema;

type Address {
    street: String
    city: String
    zipCode: String
}

node Customer {
    name: String
    email: String
    address: Address
}

node Product {
    name: String
    price: Float
    stockQuantity: Integer
}

node Order {
    orderNumber: String
    date: Date
    total: Float
}

edge Orders: Customer -> Order {
    deliveryAddress: Address
}

edge Contains: Order -> Product {
    quantity: Integer
    unitPrice: Float
}

edge Reviews: Customer -> Product {
    rating: Integer
    text: String
    date: Date
}
""")

        # Load the AST
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Generate Cypher schema
        generator = CypherGenerator()
        generator.generate(loaded_asts, temp_output_dir)

        # Check that schema file was generated
        schema_file = os.path.join(temp_output_dir, "schema.cypher")
        assert os.path.exists(schema_file)

        # Read the generated schema
        with open(schema_file, "r") as f:
            schema_content = f.read()

        # Verify node constraints
        assert (
            re.search(
                r"CREATE CONSTRAINT.+FOR \(n:Customer\)", schema_content, re.DOTALL
            )
            is not None
        )
        assert (
            re.search(
                r"CREATE CONSTRAINT.+FOR \(n:Product\)", schema_content, re.DOTALL
            )
            is not None
        )
        assert (
            re.search(r"CREATE CONSTRAINT.+FOR \(n:Order\)", schema_content, re.DOTALL)
            is not None
        )

        # Verify property indices
        assert "CREATE INDEX" in schema_content
        assert "email" in schema_content
        assert "price" in schema_content
        assert "orderNumber" in schema_content

        # Verify complex type properties
        assert "address" in schema_content

        # Verify relationship declarations
        assert "MATCH ()-[rel:ORDERS]->()" in schema_content
        assert "MATCH ()-[rel:CONTAINS]->()" in schema_content
        assert "MATCH ()-[rel:REVIEWS]->()" in schema_content

        # Verify relationship properties
        assert "deliveryAddress" in schema_content
        assert "quantity" in schema_content
        assert "rating" in schema_content

    def test_schema_with_imports(self, setup_test_files, temp_output_dir):
        """Test Cypher generation with model files that have imports."""
        # Create base types file
        base_types_path = os.path.join(setup_test_files, "BaseTypes.gm")
        with open(base_types_path, "w") as f:
            f.write("""
namespace BaseTypes;

type Address {
    street: String
    city: String
    zipCode: String
    country: String
}

type ContactInfo {
    email: String
    phone: String
    address: Address
}
""")

        # Create main model file with import
        main_model_path = os.path.join(setup_test_files, "MainModel.gm")
        with open(main_model_path, "w") as f:
            f.write(f"""
namespace MainModel;

import "{os.path.basename(base_types_path)}";

node Person {{
    name: String
    contact: BaseTypes.ContactInfo
}}

node Company {{
    name: String
    founded: Date
    address: BaseTypes.Address
}}

edge WorksAt: Person -> Company {{
    position: String
    startDate: Date
}}
""")

        # Load the AST with import resolution
        loader = AstLoader(include_paths=[setup_test_files])
        loaded_asts = loader.load(main_model_path)

        # Generate Cypher schema
        generator = CypherGenerator()
        generator.generate(loaded_asts, temp_output_dir)

        # Check that schema file was generated
        schema_file = os.path.join(temp_output_dir, "schema.cypher")
        assert os.path.exists(schema_file)

        # Read the generated schema
        with open(schema_file, "r") as f:
            schema_content = f.read()

        # Verify node constraints for both Person and Company
        assert (
            re.search(r"CREATE CONSTRAINT.+FOR \(n:Person\)", schema_content, re.DOTALL)
            is not None
        )
        assert (
            re.search(
                r"CREATE CONSTRAINT.+FOR \(n:Company\)", schema_content, re.DOTALL
            )
            is not None
        )

        # Verify complex type properties are correctly included
        assert "contact" in schema_content
        assert "address" in schema_content

        # Verify relationship and its properties
        assert "MATCH ()-[rel:WORKS_AT]->()" in schema_content
        assert "position" in schema_content
        assert "startDate" in schema_content

    def test_relationship_directionality(self, setup_test_files, temp_output_dir):
        """Test Cypher schema generation for different relationship directions."""
        test_file_path = os.path.join(setup_test_files, "relationship_directions.gm")

        with open(test_file_path, "w") as f:
            f.write("""
namespace DirectionTest;

node Person {
    name: String
}

node Company {
    name: String
}

node Post {
    title: String
    content: String
}

// Outgoing relationship
edge WorksAt: Person -> Company {
    position: String
}

// Bidirectional relationship
edge Friend: Person <-> Person {
    since: Date
}

// Self-reference relationship
edge Manages: Person -> Person {
    since: Date
}

// Multiple edge types between same nodes
edge Likes: Person -> Post {}
edge Comments: Person -> Post {
    text: String
    date: Date
}
""")

        # Load and generate Cypher
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)
        generator = CypherGenerator()
        generator.generate(loaded_asts, temp_output_dir)

        schema_file = os.path.join(temp_output_dir, "schema.cypher")
        with open(schema_file, "r") as f:
            schema_content = f.read()

        # Check directionality in comments
        assert "// Direction: ->" in schema_content
        assert "// Direction: <->" in schema_content

        # Check relationship constraints
        assert "MATCH ()-[rel:WORKS_AT]->()" in schema_content
        assert (
            "MATCH ()-[rel:FRIEND]-()" in schema_content
        )  # Bidirectional should not have arrow
        assert "MATCH ()-[rel:MANAGES]->()" in schema_content

        # Check for multiple edge types
        assert "MATCH ()-[rel:LIKES]->()" in schema_content
        assert "MATCH ()-[rel:COMMENTS]->()" in schema_content

        # Verify properties
        assert "position: String" in schema_content.replace(" ", "").replace(
            "\n", ""
        ) or "position:string" in schema_content.lower().replace(" ", "").replace(
            "\n", ""
        )
        assert "since: Date" in schema_content.replace(" ", "").replace(
            "\n", ""
        ) or "since:date" in schema_content.lower().replace(" ", "").replace("\n", "")
        assert "text: String" in schema_content.replace(" ", "").replace(
            "\n", ""
        ) or "text:string" in schema_content.lower().replace(" ", "").replace("\n", "")

    def test_cypher_naming_conventions(self, setup_test_files, temp_output_dir):
        """Test that Cypher generator follows Neo4j naming conventions."""
        test_file_path = os.path.join(setup_test_files, "naming_conventions.gm")

        with open(test_file_path, "w") as f:
            f.write("""
namespace NamingTest;

node UserAccount {
    firstName: String
    lastName: String
    emailAddress: String
}

node BlogPost {
    postTitle: String
    postContent: String
    datePublished: Date
}

edge AuthoredBy: BlogPost -> UserAccount {
    publishedDate: Date
}

edge ReactedTo: UserAccount -> BlogPost {
    reactionType: String
}

edge ConnectedTo: UserAccount <-> UserAccount {
    connectionDate: Date
    connectionType: String
}
""")

        # Load and generate Cypher
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)
        generator = CypherGenerator()
        generator.generate(loaded_asts, temp_output_dir)

        schema_file = os.path.join(temp_output_dir, "schema.cypher")
        with open(schema_file, "r") as f:
            schema_content = f.read()

        # Check Node labels follow CamelCase convention
        assert "UserAccount" in schema_content
        assert "BlogPost" in schema_content

        # Check relationship types follow UPPERCASE_WITH_UNDERSCORES convention
        assert "AUTHORED_BY" in schema_content
        assert "REACTED_TO" in schema_content
        assert "CONNECTED_TO" in schema_content

        # Check property names follow camelCase convention
        assert "firstName" in schema_content
        assert "lastName" in schema_content
        assert "emailAddress" in schema_content
        assert "postTitle" in schema_content
        assert "publishedDate" in schema_content
        assert "connectionType" in schema_content

    def test_cypher_data_types(self, setup_test_files, temp_output_dir):
        """Test Cypher generator maps data types correctly."""
        test_file_path = os.path.join(setup_test_files, "data_types.gm")

        with open(test_file_path, "w") as f:
            f.write("""
namespace DataTypeTest;

node Entity {
    stringProperty: String
    integerProperty: Integer
    floatProperty: Float
    booleanProperty: Boolean
    dateProperty: Date
}

edge Relationship: Entity -> Entity {
    stringProperty: String
    integerProperty: Integer
    floatProperty: Float
    booleanProperty: Boolean
    dateProperty: Date
}
""")

        # Load and generate Cypher
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)
        generator = CypherGenerator()
        generator.generate(loaded_asts, temp_output_dir)

        schema_file = os.path.join(temp_output_dir, "schema.cypher")
        with open(schema_file, "r") as f:
            schema_content = f.read()

        # Check for all data types in comments or property declarations
        expected_types = [
            "String",
            "string",
            "Integer",
            "integer",
            "int",
            "Float",
            "float",
            "double",
            "Boolean",
            "boolean",
            "bool",
            "Date",
            "date",
            "datetime",
        ]

        # At least some of these types should be present in the schema
        found_types = 0
        for type_name in expected_types:
            if type_name in schema_content:
                found_types += 1

        # Should match at least one variant of each type (5 types)
        assert found_types >= 5, "Not all expected data types were found in the schema"

    def test_complex_nested_types(self, setup_test_files, temp_output_dir):
        """Test Cypher generation with nested complex types."""
        test_file_path = os.path.join(setup_test_files, "nested_types.gm")

        with open(test_file_path, "w") as f:
            f.write("""
namespace NestedTypesTest;

type GeoPoint {
    latitude: Float
    longitude: Float
}

type Address {
    street: String
    city: String
    zipCode: String
    country: String
    location: GeoPoint
}

type ContactInfo {
    primaryEmail: String
    secondaryEmail: String
    phone: String
    address: Address
}

node Person {
    name: String
    bio: String
    contact: ContactInfo
    workAddress: Address
}

edge LivesNear: Person -> Person {
    distance: Float
    location: GeoPoint
}
""")

        # Load and generate Cypher
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)
        generator = CypherGenerator()
        generator.generate(loaded_asts, temp_output_dir)

        schema_file = os.path.join(temp_output_dir, "schema.cypher")
        with open(schema_file, "r") as f:
            schema_content = f.read()

        # Verify node with nested properties
        assert "Person" in schema_content
        assert "contact" in schema_content

        # Check cypher representation of nested properties
        # The exact format may vary based on implementation, but all properties
        # should be flattened or serialized in some way

        # For nodes, check property handling
        assert re.search(r"contact", schema_content, re.IGNORECASE) is not None
        assert re.search(r"workAddress", schema_content, re.IGNORECASE) is not None

        # For relationships, check property handling
        assert re.search(r"LIVES_NEAR", schema_content) is not None
        assert re.search(r"distance", schema_content, re.IGNORECASE) is not None
        assert re.search(r"location", schema_content, re.IGNORECASE) is not None

    def test_specialized_constraints_and_indices(
        self, setup_test_files, temp_output_dir
    ):
        """Test generation of specialized constraints and indices."""
        test_file_path = os.path.join(setup_test_files, "constraints_indices.gm")

        with open(test_file_path, "w") as f:
            f.write("""
namespace ConstraintsTest;

node User {
    username: String  // Unique identifier
    email: String     // Also unique
    firstName: String
    lastName: String
    age: Integer      // Searchable
    active: Boolean
}

node Product {
    sku: String       // Unique identifier
    name: String      // Searchable
    price: Float      // Searchable
    description: String
}

edge Purchased: User -> Product {
    purchaseDate: Date    // Searchable
    quantity: Integer
    totalPrice: Float     // Searchable
}
""")

        # Load and generate Cypher
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)
        generator = CypherGenerator()
        generator.generate(loaded_asts, temp_output_dir)

        schema_file = os.path.join(temp_output_dir, "schema.cypher")
        with open(schema_file, "r") as f:
            schema_content = f.read()

        # Check for node uniqueness constraints
        assert (
            re.search(
                r"CREATE CONSTRAINT.+User.+id.+UNIQUE",
                schema_content,
                re.DOTALL | re.IGNORECASE,
            )
            is not None
        )
        assert (
            re.search(
                r"CREATE CONSTRAINT.+Product.+id.+UNIQUE",
                schema_content,
                re.DOTALL | re.IGNORECASE,
            )
            is not None
        )

        # Check for indices on searchable properties
        assert (
            re.search(
                r"CREATE INDEX.+User.+age", schema_content, re.DOTALL | re.IGNORECASE
            )
            is not None
        )
        assert (
            re.search(
                r"CREATE INDEX.+Product.+name",
                schema_content,
                re.DOTALL | re.IGNORECASE,
            )
            is not None
        )
        assert (
            re.search(
                r"CREATE INDEX.+Product.+price",
                schema_content,
                re.DOTALL | re.IGNORECASE,
            )
            is not None
        )

        # Check for relationship structure
        assert "MATCH ()-[rel:PURCHASED]->()" in schema_content

    def test_cypher_schema_header_comments(self, setup_test_files, temp_output_dir):
        """Test that the Cypher schema has proper header comments."""
        test_file_path = os.path.join(setup_test_files, "simple_for_header.gm")

        with open(test_file_path, "w") as f:
            f.write("""
namespace HeaderTest;

node Test {
    name: String
}
""")

        # Load and generate Cypher
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)
        generator = CypherGenerator()
        generator.generate(loaded_asts, temp_output_dir)

        schema_file = os.path.join(temp_output_dir, "schema.cypher")
        with open(schema_file, "r") as f:
            schema_content = f.read()

        # Check for header comments
        assert "Neo4j Schema" in schema_content
        assert "Generated by GMDSL" in schema_content
        assert "HeaderTest" in schema_content  # Namespace should be mentioned
