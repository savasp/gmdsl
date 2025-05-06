import os

import pytest

from gmdsl.ast import (
    Document,
    EdgeDeclaration,
    Import,
    ImportDeclaration,
    Namespace,
    NamespaceDeclaration,
    NodeDeclaration,
    Property,
    PropertyDeclaration,
    Reference,
    Scalar,
    TypeDeclaration,
)
from gmdsl.loader import AstLoader
from gmdsl.parser import Parser
from gmdsl.validation import (
    AstValidator,
    ModelValidator,
    ValidationError,
    Validator,
    validate_asts,
)


class TestValidation:
    def test_valid_model(self, setup_test_files):
        """Test validation with a valid model that should pass all checks."""
        test_file_path = os.path.join(setup_test_files, "valid_model.gm")

        # Create a test file with a valid model
        with open(test_file_path, "w") as f:
            f.write("""
namespace ValidModel;

type Address {
    street: String
    city: String
    zipCode: String
}

node Person {
    name: String
    address: Address
}

node Company {
    name: String
    location: Address
}

edge WorksFor: Person -> Company {
    startDate: Date
    title: String
}

edge LivesAt: Person -> Address {
    isPrimary: Boolean
}
""")

        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the loaded ASTs
        validation_errors = validate_asts(loaded_asts)

        # Should have no validation errors
        assert len(validation_errors) == 0

    def test_undefined_type_reference(self, setup_test_files):
        """Test validation with references to undefined types."""
        test_file_path = os.path.join(setup_test_files, "undefined_type.gm")

        # Create a test file with an undefined type reference
        with open(test_file_path, "w") as f:
            f.write("""
namespace UndefinedTypeTest;

node Person {
    name: String
    address: Address  // Address type is not defined
}

edge LivesAt: Person -> Location {  // Location node is not defined
    since: Date
}
""")

        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the loaded ASTs
        validation_errors = validate_asts(loaded_asts)

        # Should have validation errors for undefined types
        assert len(validation_errors) == 2

        # Check that we have an error about the undefined Address type
        address_error = next(
            (e for e in validation_errors if "Address" in e.message), None
        )
        assert address_error is not None
        assert "undefined type" in address_error.message.lower()

        # Check that we have an error about the undefined Location node
        location_error = next(
            (e for e in validation_errors if "Location" in e.message), None
        )
        assert location_error is not None
        assert "target node" in location_error.message.lower()

    def test_duplicate_declarations(self, setup_test_files):
        """Test validation with duplicate declarations."""
        test_file_path = os.path.join(setup_test_files, "duplicate_declarations.gm")

        # Create a test file with duplicate declarations
        with open(test_file_path, "w") as f:
            f.write("""
namespace DuplicateTest;

type Address {
    street: String
    city: String
}

type Address {  // Duplicate type declaration
    name: String
}

node Person {
    name: String
}

node Person {  // Duplicate node declaration
    firstName: String
    lastName: String
}

edge WorksFor: Person -> Company {
    since: Date
}

edge WorksFor: Person -> Company {  // Duplicate edge declaration
    title: String
}

node Company {
    name: String
}
""")

        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the loaded ASTs
        validation_errors = validate_asts(loaded_asts)

        # Should have validation errors for duplicates
        assert len(validation_errors) == 3

        # Check for duplicate type error
        type_error = next(
            (
                e
                for e in validation_errors
                if "Address" in e.message and "type" in e.message.lower()
            ),
            None,
        )
        assert type_error is not None
        assert "duplicate" in type_error.message.lower()

        # Check for duplicate node error
        node_error = next(
            (
                e
                for e in validation_errors
                if "Person" in e.message and "node" in e.message.lower()
            ),
            None,
        )
        assert node_error is not None
        assert "duplicate" in node_error.message.lower()

        # Check for duplicate edge error
        edge_error = next(
            (e for e in validation_errors if "WorksFor" in e.message), None
        )
        assert edge_error is not None
        assert "duplicate" in edge_error.message.lower()

    def test_property_type_validation(self, setup_test_files):
        """Test validation of property types including primitive and custom types."""
        test_file_path = os.path.join(setup_test_files, "property_types.gm")

        # Create a test file with various property type usages
        with open(test_file_path, "w") as f:
            f.write("""
namespace PropertyTypesTest;

type Address {
    street: String  // Valid primitive type
    city: String    // Valid primitive type
    zipCode: String // Valid primitive type
}

node Person {
    name: String       // Valid primitive type
    age: Integer       // Valid primitive type
    height: Float      // Valid primitive type
    isActive: Boolean  // Valid primitive type
    birthDate: Date    // Valid primitive type
    address: Address   // Valid custom type
    nickname: Unknown  // Invalid type - doesn't exist
}

edge LivesAt: Person -> Address {
    primaryResidence: Boolean   // Valid primitive type
    invalidProp: NonExistent    // Invalid type - doesn't exist
}
""")

        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the loaded ASTs
        validation_errors = validate_asts(loaded_asts)

        # Should have validation errors for undefined types
        assert len(validation_errors) == 2

        # Check for error about Unknown type
        unknown_error = next(
            (e for e in validation_errors if "Unknown" in e.message), None
        )
        assert unknown_error is not None
        assert "undefined type" in unknown_error.message.lower()

        # Check for error about NonExistent type
        nonexistent_error = next(
            (e for e in validation_errors if "NonExistent" in e.message), None
        )
        assert nonexistent_error is not None
        assert "undefined type" in nonexistent_error.message.lower()

    def test_edge_reference_validation(self, setup_test_files):
        """Test validation of edge source and target references."""
        test_file_path = os.path.join(setup_test_files, "edge_references.gm")

        # Create a test file with edge reference issues
        with open(test_file_path, "w") as f:
            f.write("""
namespace EdgeReferenceTest;

node Person {
    name: String
}

node Company {
    name: String
}

type Address {  // This is a type, not a node
    street: String
    city: String
}

edge WorksFor: Person -> Company {  // Valid edge
    title: String
}

edge InvalidSource: NonExistentNode -> Company {  // Invalid source node
    since: Date
}

edge InvalidTarget: Person -> NonExistentNode {  // Invalid target node
    role: String
}

edge InvalidTypeReference: Person -> Address {  // Invalid - Address is a type, not a node
    isPrimary: Boolean
}
""")

        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the loaded ASTs
        validation_errors = validate_asts(loaded_asts)

        # Should have validation errors for edge references
        assert len(validation_errors) == 3

        # Check for error about NonExistentNode as source
        source_error = next(
            (
                e
                for e in validation_errors
                if "NonExistentNode" in e.message and "source" in e.message.lower()
            ),
            None,
        )
        assert source_error is not None

        # Check for error about NonExistentNode as target
        target_error = next(
            (
                e
                for e in validation_errors
                if "NonExistentNode" in e.message and "target" in e.message.lower()
            ),
            None,
        )
        assert target_error is not None

        # Check for error about Address as target (type used where node expected)
        type_error = next(
            (e for e in validation_errors if "Address" in e.message), None
        )
        assert type_error is not None
        assert "node" in type_error.message.lower()


class TestValidator:
    def test_duplicate_declaration_names(self):
        """Test validation of duplicate declaration names."""
        parser = Parser()
        source = """
        namespace TestDuplicates;
        
        node Person {
            name: String
        }
        
        // Duplicate node name
        node Person {
            firstName: String
            lastName: String
        }
        """

        doc = parser.parse(source)
        validator = Validator()
        errors = validator.validate(doc)

        # Should have validation error about duplicate node names
        assert any(
            e.message.lower().find("duplicate") >= 0 and "person" in e.message.lower()
            for e in errors
        )

    def test_undefined_type_references(self):
        """Test validation of undefined type references."""
        parser = Parser()
        source = """
        namespace TestUndefinedTypes;
        
        node Person {
            name: String
            address: Address  // Address is not defined
        }
        """

        doc = parser.parse(source)
        validator = Validator()
        errors = validator.validate(doc)

        # Should have validation error about undefined type
        assert any(
            "address" in e.message.lower() and "undefined" in e.message.lower()
            for e in errors
        )

    def test_edge_with_undefined_nodes(self):
        """Test validation of edge references to undefined nodes."""
        parser = Parser()
        source = """
        namespace TestUndefinedNodes;
        
        node Person {
            name: String
        }
        
        // Order is not defined
        edge PlacedOrder: Person -> Order {
            orderDate: Date
        }
        """

        doc = parser.parse(source)
        validator = Validator()
        errors = validator.validate(doc)

        # Should have validation error about undefined node reference
        assert any(
            "order" in e.message.lower() and "undefined" in e.message.lower()
            for e in errors
        )

    def test_self_referential_types(self):
        """Test validation of self-referential type definitions."""
        parser = Parser()
        source = """
        namespace TestSelfReference;
        
        type Person {
            name: String
            friend: Person  // Self-reference is allowed
        }
        """

        doc = parser.parse(source)
        validator = Validator()
        errors = validator.validate(doc)

        # Should not have errors for self-references
        assert not any(
            "friend" in e.message.lower() and "reference" in e.message.lower()
            for e in errors
        )

    def test_circular_type_references(self):
        """Test validation of circular type references."""
        parser = Parser()
        source = """
        namespace TestCircularReferences;
        
        type Person {
            name: String
            company: Company
        }
        
        type Company {
            name: String
            ceo: Person
        }
        """

        doc = parser.parse(source)
        validator = Validator()
        errors = validator.validate(doc)

        # Circular references are allowed in graph models, so there should be no errors
        assert not any(
            "circular" in e.message.lower() or "recursive" in e.message.lower()
            for e in errors
        )

    def test_invalid_property_types(self):
        """Test validation of invalid property types."""
        parser = Parser()
        source = """
        namespace TestInvalidTypes;
        
        node Product {
            name: String
            price: Money  // Money is not a basic type or defined type
        }
        """

        doc = parser.parse(source)
        validator = Validator()
        errors = validator.validate(doc)

        # Should have validation error about undefined type
        assert any(
            "money" in e.message.lower() and "type" in e.message.lower() for e in errors
        )

    def test_invalid_relationships(self):
        """Test validation of invalid relationship definitions."""
        parser = Parser()
        source = """
        namespace TestInvalidRelationships;
        
        node Person {
            name: String
        }
        
        // Invalid: using a node that doesn't exist
        edge Likes: Person -> Movie {
            rating: Integer
        }
        """

        doc = parser.parse(source)
        validator = Validator()
        errors = validator.validate(doc)

        # Should have validation error about undefined node reference
        assert any("movie" in e.message.lower() for e in errors)

    def test_reserved_keywords(self):
        """Test validation against usage of reserved keywords as names."""
        parser = Parser()
        source = """
        namespace TestReservedKeywords;
        
        node node {  // 'node' is a reserved keyword
            name: String
        }
        """

        doc = parser.parse(source)
        validator = Validator()
        errors = validator.validate(doc)

        # Should have validation error about reserved keyword usage
        assert any(
            "node" in e.message.lower() and "reserved" in e.message.lower()
            for e in errors
        )

    def test_multiple_namespaces(self):
        """Test validation against multiple namespace declarations."""
        parser = Parser()
        source = """
        namespace First;
        
        node Person {
            name: String
        }
        
        namespace Second;  // Multiple namespaces not allowed
        
        node Product {
            name: String
        }
        """

        doc = parser.parse(source)
        validator = Validator()
        errors = validator.validate(doc)

        # Should have validation error about multiple namespaces
        assert any(
            "namespace" in e.message.lower()
            and (
                "multiple" in e.message.lower() or "more than one" in e.message.lower()
            )
            for e in errors
        )

    def test_valid_model(self):
        """Test validation of a fully valid model."""
        parser = Parser()
        source = """
        namespace ValidModel;
        
        type Address {
            street: String
            city: String
            zipCode: String
        }
        
        node Person {
            name: String
            email: String
            address: Address
        }
        
        node Product {
            name: String
            price: Float
            description: String
        }
        
        edge Purchased: Person -> Product {
            purchaseDate: Date
            quantity: Integer
        }
        """

        doc = parser.parse(source)
        validator = Validator()
        errors = validator.validate(doc)

        # Should have no validation errors
        assert len(errors) == 0


class TestAstValidator:
    def test_valid_document(self, setup_test_files):
        """Test validation of a valid document."""
        test_file_path = os.path.join(setup_test_files, "valid_model.gm")

        # Create a test file with a valid model
        with open(test_file_path, "w") as f:
            f.write("""
namespace ValidModel;

type Location {
    name: String
    latitude: Float
    longitude: Float
}

node Person {
    firstName: String
    lastName: String
    age: Integer
    location: Location
}

node Company {
    name: String
    founded: Date
    address: Location
}

edge WorksAt: Person -> Company {
    position: String
    startDate: Date
}
""")

        # Load the AST
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the AST
        validator = AstValidator()
        validation_result = validator.validate(loaded_asts)

        # Should be valid with no errors
        assert validation_result.is_valid
        assert len(validation_result.errors) == 0

    def test_duplicate_node_declarations(self, setup_test_files):
        """Test validation detects duplicate node declarations."""
        test_file_path = os.path.join(setup_test_files, "duplicate_nodes.gm")

        # Create a test file with duplicate node declarations
        with open(test_file_path, "w") as f:
            f.write("""
namespace DuplicateTest;

node Person {
    name: String
}

node Person {
    firstName: String
    lastName: String
}
""")

        # Load the AST
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the AST
        validator = AstValidator()
        validation_result = validator.validate(loaded_asts)

        # Should be invalid with error about duplicate declaration
        assert not validation_result.is_valid
        assert len(validation_result.errors) > 0
        assert any("duplicate" in err.lower() for err in validation_result.errors)

    def test_unknown_type_reference(self, setup_test_files):
        """Test validation detects references to unknown types."""
        test_file_path = os.path.join(setup_test_files, "unknown_type.gm")

        # Create a test file with reference to unknown type
        with open(test_file_path, "w") as f:
            f.write("""
namespace UnknownTypeTest;

node Person {
    name: String
    address: Address  // Address type is not defined
}
""")

        # Load the AST
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the AST
        validator = AstValidator()
        validation_result = validator.validate(loaded_asts)

        # Should be invalid with error about unknown type
        assert not validation_result.is_valid
        assert len(validation_result.errors) > 0
        assert any("unknown type" in err.lower() for err in validation_result.errors)

    def test_invalid_edge_reference(self, setup_test_files):
        """Test validation detects edges referencing undefined nodes."""
        test_file_path = os.path.join(setup_test_files, "invalid_edge.gm")

        # Create a test file with edge referencing undefined nodes
        with open(test_file_path, "w") as f:
            f.write("""
namespace InvalidEdgeTest;

node Person {
    name: String
}

edge WorksAt: Person -> Company {  // Company is not defined
    position: String
}
""")

        # Load the AST
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the AST
        validator = AstValidator()
        validation_result = validator.validate(loaded_asts)

        # Should be invalid with error about undefined node
        assert not validation_result.is_valid
        assert len(validation_result.errors) > 0
        assert any("undefined node" in err.lower() for err in validation_result.errors)

    def test_invalid_property_type(self, setup_test_files):
        """Test validation detects invalid property types."""
        test_file_path = os.path.join(setup_test_files, "invalid_property.gm")

        # Create a test file with invalid property type
        with open(test_file_path, "w") as f:
            f.write("""
namespace InvalidPropertyTest;

node Person {
    name: String
    age: NotAValidType
}
""")

        # Load the AST
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the AST
        validator = AstValidator()
        validation_result = validator.validate(loaded_asts)

        # Should be invalid with error about unknown type
        assert not validation_result.is_valid
        assert len(validation_result.errors) > 0
        assert any("unknown type" in err.lower() for err in validation_result.errors)

    def test_valid_primitive_types(self, setup_test_files):
        """Test validation accepts all valid primitive types."""
        test_file_path = os.path.join(setup_test_files, "valid_primitives.gm")

        # Create a test file with all primitive types
        with open(test_file_path, "w") as f:
            f.write("""
namespace PrimitiveTypesTest;

node TestPrimitives {
    stringValue: String
    intValue: Integer
    floatValue: Float
    boolValue: Boolean
    dateValue: Date
}
""")

        # Load the AST
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the AST
        validator = AstValidator()
        validation_result = validator.validate(loaded_asts)

        # Should be valid with no errors
        assert validation_result.is_valid
        assert len(validation_result.errors) == 0

    def test_cyclic_type_references(self, setup_test_files):
        """Test validation detects cyclic type references."""
        test_file_path = os.path.join(setup_test_files, "cyclic_types.gm")

        # Create a test file with cyclic type references
        with open(test_file_path, "w") as f:
            f.write("""
namespace CyclicTypeTest;

type Person {
    name: String
    contact: ContactInfo
}

type ContactInfo {
    email: String
    owner: Person  // Cyclic reference
}
""")

        # Load the AST
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the AST
        validator = AstValidator()
        validation_result = validator.validate(loaded_asts)

        # Should be invalid with error about cyclic references
        assert not validation_result.is_valid
        assert len(validation_result.errors) > 0
        assert any("cyclic" in err.lower() for err in validation_result.errors)

    def test_valid_with_imports(self, setup_test_files):
        """Test validation with valid imports."""
        base_file_path = os.path.join(setup_test_files, "base_types.gm")
        main_file_path = os.path.join(setup_test_files, "main_model_valid.gm")

        # Create base file with types
        with open(base_file_path, "w") as f:
            f.write("""
namespace BaseTypes;

type Location {
    name: String
    latitude: Float
    longitude: Float
}
""")

        # Create main file that imports the base file and uses types correctly
        with open(main_file_path, "w") as f:
            f.write(f"""
namespace MainModel;

import "{os.path.basename(base_file_path)}";

node Person {{
    name: String
    home: BaseTypes.Location
}}
""")

        # Load the AST with import resolution
        loader = AstLoader(include_paths=[setup_test_files])
        loaded_asts = loader.load(main_file_path)

        # Validate the AST
        validator = AstValidator()
        validation_result = validator.validate(loaded_asts)

        # Should be valid with no errors
        assert validation_result.is_valid
        assert len(validation_result.errors) == 0

    def test_invalid_import_reference(self, setup_test_files):
        """Test validation with invalid import references."""
        base_file_path = os.path.join(setup_test_files, "base_types_invalid.gm")
        main_file_path = os.path.join(setup_test_files, "main_model_invalid.gm")

        # Create base file with types
        with open(base_file_path, "w") as f:
            f.write("""
namespace BaseTypes;

type Location {
    name: String
}
""")

        # Create main file that imports the base file but uses non-existent type
        with open(main_file_path, "w") as f:
            f.write(f"""
namespace MainModel;

import "{os.path.basename(base_file_path)}";

node Person {{
    name: String
    home: BaseTypes.Address  // Address doesn't exist in BaseTypes
}}
""")

        # Load the AST with import resolution
        loader = AstLoader(include_paths=[setup_test_files])
        loaded_asts = loader.load(main_file_path)

        # Validate the AST
        validator = AstValidator()
        validation_result = validator.validate(loaded_asts)

        # Should be invalid with error about unknown type
        assert not validation_result.is_valid
        assert len(validation_result.errors) > 0
        assert any(
            "Address" in err and "unknown type" in err.lower()
            for err in validation_result.errors
        )

    def test_import_file_not_found(self, setup_test_files):
        """Test validation with non-existent import file."""
        main_file_path = os.path.join(setup_test_files, "main_model_not_found.gm")

        # Create main file that imports non-existent file
        with open(main_file_path, "w") as f:
            f.write("""
namespace MainModel;

import "NonExistentFile.gm";

node Person {
    name: String
}
""")

        # Load the AST with import resolution
        loader = AstLoader(include_paths=[setup_test_files])

        # Should raise an exception for file not found
        with pytest.raises(Exception):
            loaded_asts = loader.load(main_file_path)

    def test_complex_validation_scenario(self, setup_test_files):
        """Test validation with a complex scenario involving multiple types and relationships."""
        test_file_path = os.path.join(setup_test_files, "complex_validation.gm")

        # Create a test file with complex validation scenario
        with open(test_file_path, "w") as f:
            f.write("""
namespace ComplexValidation;

type Address {
    street: String
    city: String
    country: String
}

type ContactInfo {
    email: String
    phone: String
}

node Person {
    firstName: String
    lastName: String
    birthDate: Date
    address: Address
    contact: ContactInfo
}

node Organization {
    name: String
    founded: Date
    address: Address
}

node Department {
    name: String
    budget: Float
}

edge BelongsTo: Department -> Organization {}

edge WorksIn: Person -> Department {
    role: String
    since: Date
}

edge WorksFor: Person -> Organization {
    position: String
    salary: Float
}

edge LivesAt: Person -> Address {}

edge Knows: Person <-> Person {
    since: Date
}
""")

        # Load the AST
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the AST
        validator = AstValidator()
        validation_result = validator.validate(loaded_asts)

        # Should be valid with no errors
        assert validation_result.is_valid
        assert len(validation_result.errors) == 0

    def test_edge_between_node_and_complex_type(self, setup_test_files):
        """Test validation detects invalid edge between node and complex type."""
        test_file_path = os.path.join(setup_test_files, "invalid_edge_type.gm")

        # Create a test file with edge between node and complex type
        with open(test_file_path, "w") as f:
            f.write("""
namespace InvalidEdgeType;

type Address {
    street: String
    city: String
}

node Person {
    name: String
}

edge LivesAt: Person -> Address {}  // Invalid: edge can only connect nodes
""")

        # Load the AST
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the AST
        validator = AstValidator()
        validation_result = validator.validate(loaded_asts)

        # Should be invalid with error about invalid edge target
        assert not validation_result.is_valid
        assert len(validation_result.errors) > 0
        assert any(
            "edge" in err.lower() and "node" in err.lower()
            for err in validation_result.errors
        )

    def test_duplicate_property_names(self, setup_test_files):
        """Test validation detects duplicate property names within a declaration."""
        test_file_path = os.path.join(setup_test_files, "duplicate_properties.gm")

        # Create a test file with duplicate property names
        with open(test_file_path, "w") as f:
            f.write("""
namespace DuplicatePropertyTest;

node Person {
    name: String
    age: Integer
    name: String  // Duplicate property name
}
""")

        # Load the AST
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the AST
        validator = AstValidator()
        validation_result = validator.validate(loaded_asts)

        # Should be invalid with error about duplicate property
        assert not validation_result.is_valid
        assert len(validation_result.errors) > 0
        assert any(
            "duplicate property" in err.lower() for err in validation_result.errors
        )

    def test_complex_type_imported_validation(self, setup_test_files):
        """Test validation of complex types across import boundaries."""
        base_file_path = os.path.join(setup_test_files, "types_module.gm")
        nodes_file_path = os.path.join(setup_test_files, "nodes_module.gm")
        edges_file_path = os.path.join(setup_test_files, "edges_module.gm")

        # Create base types file
        with open(base_file_path, "w") as f:
            f.write("""
namespace Types;

type Location {
    latitude: Float
    longitude: Float
    name: String
}

type ContactInfo {
    email: String
    phone: String
}
""")

        # Create nodes file that imports types
        with open(nodes_file_path, "w") as f:
            f.write(f"""
namespace Nodes;

import "{os.path.basename(base_file_path)}";

node Person {{
    firstName: String
    lastName: String
    contact: Types.ContactInfo
    homeLocation: Types.Location
}}

node Place {{
    name: String
    location: Types.Location
}}
""")

        # Create edges file that imports nodes
        with open(edges_file_path, "w") as f:
            f.write(f"""
namespace Edges;

import "{os.path.basename(nodes_file_path)}";

edge VisitedPlace: Nodes.Person -> Nodes.Place {{
    visitDate: Date
    rating: Integer
}}
""")

        # Load the ASTs with import resolution
        loader = AstLoader(include_paths=[setup_test_files])
        loaded_asts = loader.load(
            edges_file_path
        )  # This will load all imports recursively

        # Validate the AST
        validator = AstValidator()
        validation_result = validator.validate(loaded_asts)

        # Should be valid with no errors
        assert validation_result.is_valid
        assert len(validation_result.errors) == 0

    def test_reserved_words(self, setup_test_files):
        """Test validation detects use of reserved words as identifiers."""
        test_file_path = os.path.join(setup_test_files, "reserved_words.gm")

        # Create a test file using reserved words
        with open(test_file_path, "w") as f:
            f.write("""
namespace ReservedWordsTest;

node node {  // 'node' is a reserved word
    type: String  // 'type' is a reserved word
    edge: Integer  // 'edge' is a reserved word
}
""")

        # Load the AST
        loader = AstLoader()
        loaded_asts = loader.load(test_file_path)

        # Validate the AST
        validator = AstValidator()
        validation_result = validator.validate(loaded_asts)

        # Should be invalid with error about reserved words
        assert not validation_result.is_valid
        assert len(validation_result.errors) > 0
        assert any("reserved word" in err.lower() for err in validation_result.errors)

    def test_programmatic_ast_validation(self):
        """Test validation of a programmatically constructed AST."""
        # Create a namespace declaration
        namespace = NamespaceDeclaration(name="TestNamespace")

        # Create a simple type declaration
        address_props = [
            PropertyDeclaration(name="street", type_name="String"),
            PropertyDeclaration(name="city", type_name="String"),
        ]
        address_type = TypeDeclaration(name="Address", properties=address_props)

        # Create a node declaration
        person_props = [
            PropertyDeclaration(name="name", type_name="String"),
            PropertyDeclaration(name="age", type_name="Integer"),
            PropertyDeclaration(name="address", type_name="Address"),
        ]
        person_node = NodeDeclaration(name="Person", properties=person_props)

        # Create an edge declaration
        friendship_props = [PropertyDeclaration(name="since", type_name="Date")]
        friendship_edge = EdgeDeclaration(
            name="Friendship",
            source_node="Person",
            target_node="Person",
            direction="<->",
            properties=friendship_props,
        )

        # Create a document
        doc = Document(
            namespace=namespace,
            declarations=[address_type, person_node, friendship_edge],
            imports=[],
        )

        # Validate the AST
        validator = AstValidator()
        validation_result = validator.validate({"test_doc": doc})

        # Should be valid with no errors
        assert validation_result.is_valid
        assert len(validation_result.errors) == 0


class TestModelValidator:
    def test_validate_basic_model(self):
        """Test validation of a basic valid model."""
        # Create a simple valid model
        doc = Document(
            namespace=Namespace("Test"),
            imports=[],
            declarations=[
                NodeDeclaration(
                    name="Person",
                    properties=[
                        Property(name="name", type=Scalar("String")),
                        Property(name="age", type=Scalar("Integer")),
                    ],
                ),
                NodeDeclaration(
                    name="Company",
                    properties=[Property(name="name", type=Scalar("String"))],
                ),
                EdgeDeclaration(
                    name="WorksAt",
                    source_node="Person",
                    target_node="Company",
                    properties=[Property(name="role", type=Scalar("String"))],
                ),
            ],
        )

        # Validate the document
        validator = ModelValidator()
        errors = validator.validate({"test.gm": doc})

        # Should not have any errors
        assert len(errors) == 0

    def test_undefined_node_in_edge(self):
        """Test validation of an edge referencing undefined nodes."""
        # Create a model with an edge referencing undefined nodes
        doc = Document(
            namespace=Namespace("Test"),
            imports=[],
            declarations=[
                NodeDeclaration(
                    name="Person",
                    properties=[Property(name="name", type=Scalar("String"))],
                ),
                EdgeDeclaration(
                    name="WorksAt",
                    source_node="Person",  # Defined
                    target_node="Company",  # Not defined
                    properties=[],
                ),
                EdgeDeclaration(
                    name="FriendsOf",
                    source_node="User",  # Not defined
                    target_node="Person",  # Defined
                    properties=[],
                ),
            ],
        )

        # Validate the document
        validator = ModelValidator()
        errors = validator.validate({"test.gm": doc})

        # Should have errors for undefined nodes
        assert len(errors) > 0

        # Check for specific error messages about undefined nodes
        error_messages = [str(error) for error in errors]
        assert any("Company" in msg and "not defined" in msg for msg in error_messages)
        assert any("User" in msg and "not defined" in msg for msg in error_messages)

    def test_duplicate_names(self):
        """Test validation of duplicate node/edge/type names."""
        # Create a model with duplicate names
        doc = Document(
            namespace=Namespace("Test"),
            imports=[],
            declarations=[
                NodeDeclaration(name="Person", properties=[]),
                NodeDeclaration(name="Person", properties=[]),  # Duplicate node name
                EdgeDeclaration(
                    name="WorksAt",
                    source_node="Person",
                    target_node="Company",
                    properties=[],
                ),
                TypeDeclaration(
                    name="WorksAt", properties=[]
                ),  # Duplicate name (edge and type)
            ],
        )

        # Validate the document
        validator = ModelValidator()
        errors = validator.validate({"test.gm": doc})

        # Should have errors for duplicate names
        assert len(errors) > 0

        # Check for specific error messages about duplicate names
        error_messages = [str(error) for error in errors]
        assert any(
            "duplicate" in msg.lower() and "Person" in msg for msg in error_messages
        )
        assert any(
            "duplicate" in msg.lower() and "WorksAt" in msg for msg in error_messages
        )

    def test_invalid_property_types(self):
        """Test validation of properties with invalid types."""
        # Create a model with invalid property types
        doc = Document(
            namespace=Namespace("Test"),
            imports=[],
            declarations=[
                NodeDeclaration(
                    name="Person",
                    properties=[
                        Property(name="name", type=Scalar("String")),  # Valid
                        Property(
                            name="age", type=Scalar("Int")
                        ),  # Invalid (should be Integer)
                        Property(
                            name="address", type=Reference("Address")
                        ),  # Reference to undefined type
                    ],
                )
            ],
        )

        # Validate the document
        validator = ModelValidator()
        errors = validator.validate({"test.gm": doc})

        # Should have errors for invalid types
        assert len(errors) > 0

        # Check for specific error messages about invalid types
        error_messages = [str(error) for error in errors]
        assert any(
            "Int" in msg and "not a valid" in msg.lower() for msg in error_messages
        )
        assert any(
            "Address" in msg and "not defined" in msg.lower() for msg in error_messages
        )

    def test_valid_property_types(self):
        """Test validation of all valid scalar property types."""
        # Create a model with all valid scalar types
        doc = Document(
            namespace=Namespace("Test"),
            imports=[],
            declarations=[
                NodeDeclaration(
                    name="AllTypes",
                    properties=[
                        Property(name="stringProp", type=Scalar("String")),
                        Property(name="integerProp", type=Scalar("Integer")),
                        Property(name="booleanProp", type=Scalar("Boolean")),
                        Property(name="floatProp", type=Scalar("Float")),
                        Property(name="dateProp", type=Scalar("Date")),
                        Property(name="datetimeProp", type=Scalar("DateTime")),
                        Property(name="timeProp", type=Scalar("Time")),
                    ],
                )
            ],
        )

        # Validate the document
        validator = ModelValidator()
        errors = validator.validate({"test.gm": doc})

        # Should not have any errors for valid types
        assert len(errors) == 0

    def test_cross_namespace_references(self):
        """Test validation of cross-namespace references."""
        # Create two documents with cross-namespace references
        doc1 = Document(
            namespace=Namespace("Models"),
            imports=[],
            declarations=[
                NodeDeclaration(
                    name="Person",
                    properties=[Property(name="name", type=Scalar("String"))],
                ),
                TypeDeclaration(
                    name="Address",
                    properties=[
                        Property(name="street", type=Scalar("String")),
                        Property(name="city", type=Scalar("String")),
                    ],
                ),
            ],
        )

        doc2 = Document(
            namespace=Namespace("Application"),
            imports=[Import("models.gm")],
            declarations=[
                NodeDeclaration(
                    name="User",
                    properties=[
                        Property(name="username", type=Scalar("String")),
                        # Cross-namespace references
                        Property(name="profile", type=Reference("Models.Person")),
                        Property(name="location", type=Reference("Models.Address")),
                    ],
                ),
                EdgeDeclaration(
                    name="HasProfile",
                    source_node="User",
                    target_node="Models.Person",  # Cross-namespace reference
                    properties=[],
                ),
            ],
        )

        # Validate both documents
        validator = ModelValidator()
        errors = validator.validate({"models.gm": doc1, "application.gm": doc2})

        # Should not have errors for valid cross-namespace references
        assert len(errors) == 0

    def test_invalid_cross_namespace_references(self):
        """Test validation of invalid cross-namespace references."""
        # Create documents with invalid cross-namespace references
        doc1 = Document(
            namespace=Namespace("Models"),
            imports=[],
            declarations=[
                NodeDeclaration(name="Person", properties=[])
                # Address is not defined here
            ],
        )

        doc2 = Document(
            namespace=Namespace("Application"),
            imports=[Import("models.gm")],
            declarations=[
                NodeDeclaration(
                    name="User",
                    properties=[
                        Property(
                            name="profile", type=Reference("Models.Person")
                        ),  # Valid
                        Property(
                            name="address", type=Reference("Models.Address")
                        ),  # Invalid - Address not defined
                    ],
                )
            ],
        )

        # Validate both documents
        validator = ModelValidator()
        errors = validator.validate({"models.gm": doc1, "application.gm": doc2})

        # Should have errors for invalid cross-namespace references
        assert len(errors) > 0

        # Check for specific error messages
        error_messages = [str(error) for error in errors]
        assert any(
            "Models.Address" in msg and "not defined" in msg.lower()
            for msg in error_messages
        )

    def test_validate_circular_references(self):
        """Test validation of models with circular references."""
        # Create a model with circular type references
        doc = Document(
            namespace=Namespace("Test"),
            imports=[],
            declarations=[
                TypeDeclaration(
                    name="Person",
                    properties=[
                        Property(name="name", type=Scalar("String")),
                        Property(name="address", type=Reference("Address")),
                    ],
                ),
                TypeDeclaration(
                    name="Address",
                    properties=[
                        Property(name="street", type=Scalar("String")),
                        Property(
                            name="resident", type=Reference("Person")
                        ),  # Circular reference
                    ],
                ),
            ],
        )

        # Circular references should be allowed in a graph model
        validator = ModelValidator()
        errors = validator.validate({"test.gm": doc})

        # No errors expected for circular references in a graph model
        assert len(errors) == 0

    def test_namespace_conflicts(self):
        """Test validation of namespace conflicts."""
        # Create multiple documents with the same namespace
        doc1 = Document(
            namespace=Namespace("Common"),
            imports=[],
            declarations=[NodeDeclaration(name="Person", properties=[])],
        )

        doc2 = Document(
            namespace=Namespace("Common"),  # Same namespace
            imports=[],
            declarations=[NodeDeclaration(name="User", properties=[])],
        )

        # Validate documents
        validator = ModelValidator()
        errors = validator.validate({"doc1.gm": doc1, "doc2.gm": doc2})

        # Should have errors for duplicate namespaces
        assert len(errors) > 0

        # Check for specific error messages
        error_messages = [str(error) for error in errors]
        assert any(
            "namespace" in msg.lower()
            and "Common" in msg
            and "already defined" in msg.lower()
            for msg in error_messages
        )

    def test_missing_imports(self):
        """Test validation of missing imports."""
        # Create a document referencing another namespace without importing it
        doc = Document(
            namespace=Namespace("App"),
            imports=[],  # No imports
            declarations=[
                NodeDeclaration(
                    name="User",
                    properties=[
                        # References Models namespace without importing it
                        Property(name="profile", type=Reference("Models.Person"))
                    ],
                )
            ],
        )

        # Validate document
        validator = ModelValidator()
        errors = validator.validate({"app.gm": doc})

        # Should have errors for missing imports
        assert len(errors) > 0

        # Check for specific error messages
        error_messages = [str(error) for error in errors]
        assert any(
            "Models" in msg and "not imported" in msg.lower() for msg in error_messages
        )

    def test_duplicate_property_names(self):
        """Test validation of duplicate property names."""
        # Create a model with duplicate property names
        doc = Document(
            namespace=Namespace("Test"),
            imports=[],
            declarations=[
                NodeDeclaration(
                    name="Person",
                    properties=[
                        Property(name="name", type=Scalar("String")),
                        Property(
                            name="name", type=Scalar("String")
                        ),  # Duplicate property name
                    ],
                )
            ],
        )

        # Validate document
        validator = ModelValidator()
        errors = validator.validate({"test.gm": doc})

        # Should have errors for duplicate property names
        assert len(errors) > 0

        # Check for specific error messages
        error_messages = [str(error) for error in errors]
        assert any(
            "name" in msg and "duplicate" in msg.lower() for msg in error_messages
        )

    def test_validate_parsed_model(self):
        """Test validation of a model parsed from string."""
        # Parse a model from string
        parser = Parser()
        doc = parser.parse("""
        namespace Test;
        
        node Person {
            name: String;
            age: Integer;
        }
        
        node Company {
            name: String;
            founded: Date;
        }
        
        edge WorksAt: Person -> Company {
            position: String;
            startDate: Date;
        }
        """)

        # Validate the parsed document
        validator = ModelValidator()
        errors = validator.validate({"test.gm": doc})

        # Should not have any errors
        assert len(errors) == 0

    def test_validate_invalid_parsed_model(self):
        """Test validation of an invalid model parsed from string."""
        # Parse an invalid model from string
        parser = Parser()
        doc = parser.parse("""
        namespace Test;
        
        node Person {
            name: String;
        }
        
        # Edge references undefined node
        edge WorksAt: Person -> Organization {
            position: String;
        }
        """)

        # Validate the parsed document
        validator = ModelValidator()
        errors = validator.validate({"test.gm": doc})

        # Should have errors for undefined node
        assert len(errors) > 0

        # Check for specific error messages
        error_messages = [str(error) for error in errors]
        assert any(
            "Organization" in msg and "not defined" in msg.lower()
            for msg in error_messages
        )

    def test_arrays_and_nullable_types(self):
        """Test validation of array and nullable types."""
        # Parse a model with array and nullable types
        parser = Parser()
        doc = parser.parse("""
        namespace Test;
        
        node Person {
            name: String;
            emails: String[];      # Array of strings
            phone: String?;        # Nullable string
            tags: String[]?;       # Nullable array of strings
        }
        
        type Address {
            street: String;
            city: String;
            zipCode: String?;      # Nullable
        }
        
        node Company {
            name: String;
            addresses: Address[];  # Array of complex type
        }
        """)

        # Validate the parsed document
        validator = ModelValidator()
        errors = validator.validate({"test.gm": doc})

        # Should not have any errors
        assert len(errors) == 0

    def test_validation_with_imports(self, parser, tmpdir):
        """Test validation of a model with imports."""
        # Create temporary files for testing
        base_file = tmpdir.join("base.gm")
        base_file.write("""
        namespace Base;
        
        type Address {
            street: String;
            city: String;
        }
        """)

        main_file = tmpdir.join("main.gm")
        main_file.write(f"""
        namespace Main;
        
        import "{base_file}";
        
        node Person {{
            name: String;
            address: Base.Address;
        }}
        """)

        # Parse files
        base_doc = parser.parse_file(str(base_file))
        main_doc = parser.parse_file(str(main_file))

        # Validate documents
        validator = ModelValidator()
        errors = validator.validate(
            {str(base_file): base_doc, str(main_file): main_doc}
        )

        # Should not have any errors
        assert len(errors) == 0
