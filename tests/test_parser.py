import os

import pytest

from gmdsl.ast import (
    Document,
    EdgeDeclaration,
    NodeDeclaration,
    RelationshipDirection,
    TypeDeclaration,
)
from gmdsl.parser import Parser


class TestParser:
    def test_parse_simple_model(self, setup_test_files):
        """Test parsing a simple model with node, edge, and type declarations."""
        test_file_path = os.path.join(setup_test_files, "simple_model.gm")

        # Create a test file with a simple model
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

edge LivesIn: Person -> Location {
    since: Date
}
""")

        parser = Parser()
        result = parser.parse_file(test_file_path)

        assert isinstance(result, Document)
        assert result.namespace.name == "TestModel"

        # Check declarations
        assert len(result.declarations) == 4

        # Check if we have 1 type, 1 node, and 2 edges
        type_decls = [d for d in result.declarations if isinstance(d, TypeDeclaration)]
        node_decls = [d for d in result.declarations if isinstance(d, NodeDeclaration)]
        edge_decls = [d for d in result.declarations if isinstance(d, EdgeDeclaration)]

        assert len(type_decls) == 1
        assert len(node_decls) == 1
        assert len(edge_decls) == 2

        # Check the type declaration
        location_type = type_decls[0]
        assert location_type.name == "Location"
        assert len(location_type.properties) == 3
        assert [p.name for p in location_type.properties] == [
            "name",
            "latitude",
            "longitude",
        ]
        assert [p.type_name for p in location_type.properties] == [
            "String",
            "Float",
            "Float",
        ]

        # Check the node declaration
        person_node = node_decls[0]
        assert person_node.name == "Person"
        assert len(person_node.properties) == 4
        assert [p.name for p in person_node.properties] == [
            "firstName",
            "lastName",
            "dateOfBirth",
            "placeOfBirth",
        ]

        # Check the edge declarations
        friend_edge = next((e for e in edge_decls if e.name == "Friend"), None)
        assert friend_edge is not None
        assert friend_edge.source_node == "Person"
        assert friend_edge.target_node == "Person"
        assert len(friend_edge.properties) == 1
        assert friend_edge.properties[0].name == "metOn"
        assert friend_edge.properties[0].type_name == "Date"

        lives_in_edge = next((e for e in edge_decls if e.name == "LivesIn"), None)
        assert lives_in_edge is not None
        assert lives_in_edge.source_node == "Person"
        assert lives_in_edge.target_node == "Location"
        assert len(lives_in_edge.properties) == 1
        assert lives_in_edge.properties[0].name == "since"

    def test_parse_model_with_imports(self, setup_test_files):
        """Test parsing a model that imports another file."""
        base_file_path = os.path.join(setup_test_files, "base_types.gm")
        main_file_path = os.path.join(setup_test_files, "main_model.gm")

        # Create base file with types
        with open(base_file_path, "w") as f:
            f.write("""
namespace BaseTypes;

type Location {
    name: String
    latitude: Float
    longitude: Float
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
    firstName: String
    lastName: String
    contact: ContactInfo
    location: Location
}}
""")

        parser = Parser()
        result = parser.parse_file(main_file_path)

        assert isinstance(result, Document)
        assert result.namespace.name == "MainModel"
        assert len(result.imports) == 1
        assert result.imports[0].path == f'"{os.path.basename(base_file_path)}"'

        # Check declarations (should have 1 node definition)
        assert len(result.declarations) == 1
        assert isinstance(result.declarations[0], NodeDeclaration)

        # Check the node declaration
        person_node = result.declarations[0]
        assert person_node.name == "Person"
        assert len(person_node.properties) == 4
        assert [p.name for p in person_node.properties] == [
            "firstName",
            "lastName",
            "contact",
            "location",
        ]
        assert [p.type_name for p in person_node.properties] == [
            "String",
            "String",
            "ContactInfo",
            "Location",
        ]

    def test_parse_complex_property_types(self, setup_test_files):
        """Test parsing a model with complex property types and nested structures."""
        test_file_path = os.path.join(setup_test_files, "complex_types.gm")

        # Create a test file with complex types
        with open(test_file_path, "w") as f:
            f.write("""
namespace ComplexTypes;

type Address {
    street: String
    city: String
    country: String
    postalCode: String
}

type ContactMethod {
    type: String  // "email", "phone", etc.
    value: String
    preferred: Boolean
}

type Person {
    name: String
    addresses: Address   // Complex type
    contactMethods: ContactMethod  // Another complex type
    active: Boolean
}

node User {
    username: String
    password: String
    profile: Person      // Reference to complex type with nested types
    lastLogin: Date
    loginCount: Integer
}
""")

        parser = Parser()
        result = parser.parse_file(test_file_path)

        assert isinstance(result, Document)
        assert result.namespace.name == "ComplexTypes"

        # Check declarations
        assert len(result.declarations) == 4

        # Find the User node
        user_node = next(
            (
                d
                for d in result.declarations
                if isinstance(d, NodeDeclaration) and d.name == "User"
            ),
            None,
        )
        assert user_node is not None

        # Check User node properties
        assert len(user_node.properties) == 5
        profile_prop = next(
            (p for p in user_node.properties if p.name == "profile"), None
        )
        assert profile_prop is not None
        assert profile_prop.type_name == "Person"

        # Find the Person type
        person_type = next(
            (
                d
                for d in result.declarations
                if isinstance(d, TypeDeclaration) and d.name == "Person"
            ),
            None,
        )
        assert person_type is not None

        # Check Person type properties for nested types
        assert len(person_type.properties) == 4
        addresses_prop = next(
            (p for p in person_type.properties if p.name == "addresses"), None
        )
        assert addresses_prop is not None
        assert addresses_prop.type_name == "Address"

        contact_methods_prop = next(
            (p for p in person_type.properties if p.name == "contactMethods"), None
        )
        assert contact_methods_prop is not None
        assert contact_methods_prop.type_name == "ContactMethod"

    def test_parse_namespace(self):
        """Test parsing a namespace declaration."""
        parser = Parser()
        source = "namespace TestNamespace;"

        result = parser.parse(source)

        assert len(parser.errors) == 0
        assert isinstance(result, Document)
        assert result.namespace is not None
        assert result.namespace.name == "TestNamespace"

    def test_parse_type_declaration(self):
        """Test parsing a type declaration with properties."""
        parser = Parser()
        source = """
        namespace TestTypes;
        
        type Address {
            street: String
            city: String
            zipCode: String
            country: String
        }
        """

        result = parser.parse(source)

        assert len(parser.errors) == 0
        assert isinstance(result, Document)
        assert result.namespace.name == "TestTypes"

        # Should have one type declaration
        assert len(result.declarations) == 1
        type_decl = result.declarations[0]
        assert isinstance(type_decl, TypeDeclaration)
        assert type_decl.name == "Address"

        # Check properties
        assert len(type_decl.properties) == 4
        prop_names = [p.name for p in type_decl.properties]
        assert "street" in prop_names
        assert "city" in prop_names
        assert "zipCode" in prop_names
        assert "country" in prop_names

        # Check property types
        for prop in type_decl.properties:
            assert prop.type_name == "String"

    def test_parse_node_declaration(self):
        """Test parsing a node declaration with properties."""
        parser = Parser()
        source = """
        namespace TestNodes;
        
        node Person {
            firstName: String
            lastName: String
            age: Integer
            isActive: Boolean
            salary: Float
            birthDate: Date
        }
        """

        result = parser.parse(source)

        assert len(parser.errors) == 0
        assert isinstance(result, Document)
        assert result.namespace.name == "TestNodes"

        # Should have one node declaration
        assert len(result.declarations) == 1
        node_decl = result.declarations[0]
        assert isinstance(node_decl, NodeDeclaration)
        assert node_decl.name == "Person"

        # Check properties with different types
        assert len(node_decl.properties) == 6

        # Find properties by name and check their types
        first_name_prop = next(p for p in node_decl.properties if p.name == "firstName")
        assert first_name_prop.type_name == "String"

        age_prop = next(p for p in node_decl.properties if p.name == "age")
        assert age_prop.type_name == "Integer"

        active_prop = next(p for p in node_decl.properties if p.name == "isActive")
        assert active_prop.type_name == "Boolean"

        salary_prop = next(p for p in node_decl.properties if p.name == "salary")
        assert salary_prop.type_name == "Float"

        birth_prop = next(p for p in node_decl.properties if p.name == "birthDate")
        assert birth_prop.type_name == "Date"

    def test_parse_edge_declarations(self):
        """Test parsing edge declarations with different relationship directions."""
        parser = Parser()
        source = """
        namespace TestEdges;
        
        node Person {
            name: String
        }
        
        node Movie {
            title: String
        }
        
        edge ActedIn: Person -> Movie {
            role: String
        }
        
        edge Knows: Person <-> Person {
            since: Date
        }
        """

        result = parser.parse(source)

        assert len(parser.errors) == 0
        assert isinstance(result, Document)
        assert result.namespace.name == "TestEdges"

        # Should have 3 declarations (2 nodes, 2 edges)
        assert len(result.declarations) == 4

        # Filter out node and edge declarations
        node_decls = [d for d in result.declarations if isinstance(d, NodeDeclaration)]
        edge_decls = [d for d in result.declarations if isinstance(d, EdgeDeclaration)]

        assert len(node_decls) == 2
        assert len(edge_decls) == 2

        # Check directed edge (->)
        acted_in_edge = next(e for e in edge_decls if e.name == "ActedIn")
        assert acted_in_edge.source_node == "Person"
        assert acted_in_edge.target_node == "Movie"
        assert acted_in_edge.direction == RelationshipDirection.OUTGOING

        # Check bidirectional edge (<->)
        knows_edge = next(e for e in edge_decls if e.name == "Knows")
        assert knows_edge.source_node == "Person"
        assert knows_edge.target_node == "Person"
        assert knows_edge.direction == RelationshipDirection.BIDIRECTIONAL

    def test_parse_imports(self):
        """Test parsing import statements."""
        parser = Parser()
        source = """
        namespace TestImports;
        
        import "Types.gm";
        import "Nodes.gm";
        
        node Product {
            name: String
            price: Float
            category: Category
        }
        """

        result = parser.parse(source)

        assert len(parser.errors) == 0
        assert isinstance(result, Document)
        assert result.namespace.name == "TestImports"

        # Check imports
        assert len(result.imports) == 2
        import_paths = [i.path for i in result.imports]
        assert "Types.gm" in import_paths
        assert "Nodes.gm" in import_paths

        # Should also have one node declaration
        node_decls = [d for d in result.declarations if isinstance(d, NodeDeclaration)]
        assert len(node_decls) == 1
        assert node_decls[0].name == "Product"

    def test_parse_complex_model(self):
        """Test parsing a complex model with multiple declarations."""
        parser = Parser()
        source = """
        namespace ComplexModel;
        
        import "CommonTypes.gm";
        
        type ProductDetails {
            dimensions: String
            weight: Float
            color: String
        }
        
        node Customer {
            name: String
            email: String
            address: Address
            phoneNumber: String
        }
        
        node Order {
            orderNumber: String
            orderDate: Date
            status: String
            totalAmount: Float
        }
        
        node Product {
            name: String
            price: Float
            description: String
            details: ProductDetails
        }
        
        edge PlacedOrder: Customer -> Order {
            orderDate: Date
            paymentMethod: String
        }
        
        edge ContainsProduct: Order -> Product {
            quantity: Integer
            unitPrice: Float
        }
        
        edge ViewedProduct: Customer -> Product {
            viewDate: Date
            duration: Integer
        }
        """

        result = parser.parse(source)

        assert len(parser.errors) == 0
        assert isinstance(result, Document)
        assert result.namespace.name == "ComplexModel"

        # Check import
        assert len(result.imports) == 1
        assert result.imports[0].path == "CommonTypes.gm"

        # Filter declarations by type
        type_decls = [d for d in result.declarations if isinstance(d, TypeDeclaration)]
        node_decls = [d for d in result.declarations if isinstance(d, NodeDeclaration)]
        edge_decls = [d for d in result.declarations if isinstance(d, EdgeDeclaration)]

        assert len(type_decls) == 1
        assert len(node_decls) == 3
        assert len(edge_decls) == 3

        # Check specific nodes
        customer_node = next(n for n in node_decls if n.name == "Customer")
        order_node = next(n for n in node_decls if n.name == "Order")
        product_node = next(n for n in node_decls if n.name == "Product")

        # Check specific edges
        placed_order_edge = next(e for e in edge_decls if e.name == "PlacedOrder")
        assert placed_order_edge.source_node == "Customer"
        assert placed_order_edge.target_node == "Order"

        contains_product_edge = next(
            e for e in edge_decls if e.name == "ContainsProduct"
        )
        assert contains_product_edge.source_node == "Order"
        assert contains_product_edge.target_node == "Product"

    def test_syntax_errors(self):
        """Test parser error handling for syntax errors."""
        parser = Parser()
        source = """
        namespace ErrorTest;
        
        type MissingBrace {
            name: String
            description: String
        // Missing closing brace
        
        node Person {
            firstName: String
            // Missing property type
            lastName
        }
        """

        result = parser.parse(source)

        # Should have syntax errors
        assert len(parser.errors) > 0
        # The actual content of errors will depend on the specifics of your parser implementation

    def test_property_without_type(self):
        """Test parser error handling for properties without a type."""
        parser = Parser()
        source = """
        namespace TestMissingType;
        
        node User {
            username: String
            password  // Missing type
            email: String
        }
        """

        result = parser.parse(source)

        # Should have an error about the missing type
        assert len(parser.errors) > 0
        # At least one error should mention 'password' or a missing type
        assert any(
            "password" in e.message.lower() or "type" in e.message.lower()
            for e in parser.errors
        )

    def test_basic_parsing(self):
        """Test basic parsing of a simple GMDSL document."""
        parser = Parser()
        source = """
        namespace TestBasic;
        
        node Person {
            name: String
            age: Integer
        }
        """

        doc = parser.parse(source)

        assert isinstance(doc, Document)
        assert doc.namespace.name == "TestBasic"
        assert len(doc.declarations) == 1

        person = doc.declarations[0]
        assert isinstance(person, NodeDeclaration)
        assert person.name == "Person"
        assert len(person.properties) == 2

        name_prop = person.properties[0]
        assert name_prop.name == "name"
        assert name_prop.type == "String"

        age_prop = person.properties[1]
        assert age_prop.name == "age"
        assert age_prop.type == "Integer"

    def test_node_declaration(self):
        """Test parsing of node declarations."""
        parser = Parser()
        source = """
        namespace TestNodes;
        
        node Person {
            firstName: String
            lastName: String
            age: Integer
            isActive: Boolean
        }
        
        node Product {}  // Empty node
        """

        doc = parser.parse(source)

        assert isinstance(doc, Document)
        assert doc.namespace.name == "TestNodes"
        assert len(doc.declarations) == 2

        # Check Person node
        person = doc.declarations[0]
        assert isinstance(person, NodeDeclaration)
        assert person.name == "Person"
        assert len(person.properties) == 4

        # Check property types
        prop_types = {p.name: p.type for p in person.properties}
        assert prop_types["firstName"] == "String"
        assert prop_types["lastName"] == "String"
        assert prop_types["age"] == "Integer"
        assert prop_types["isActive"] == "Boolean"

        # Check empty Product node
        product = doc.declarations[1]
        assert isinstance(product, NodeDeclaration)
        assert product.name == "Product"
        assert len(product.properties) == 0

    def test_edge_declaration(self):
        """Test parsing of edge declarations."""
        parser = Parser()
        source = """
        namespace TestEdges;
        
        node Person {}
        node Product {}
        
        edge Purchased: Person -> Product {
            purchaseDate: Date
            quantity: Integer
        }
        
        edge Viewed: Person -> Product {}  // Edge with no properties
        """

        doc = parser.parse(source)

        assert isinstance(doc, Document)
        assert doc.namespace.name == "TestEdges"
        assert len(doc.declarations) == 4

        # Find edge declarations
        edges = [d for d in doc.declarations if isinstance(d, EdgeDeclaration)]
        assert len(edges) == 2

        # Check Purchased edge
        purchased = next(e for e in edges if e.name == "Purchased")
        assert purchased.from_node == "Person"
        assert purchased.to_node == "Product"
        assert len(purchased.properties) == 2

        # Check property types
        prop_types = {p.name: p.type for p in purchased.properties}
        assert prop_types["purchaseDate"] == "Date"
        assert prop_types["quantity"] == "Integer"

        # Check Viewed edge
        viewed = next(e for e in edges if e.name == "Viewed")
        assert viewed.from_node == "Person"
        assert viewed.to_node == "Product"
        assert len(viewed.properties) == 0

    def test_type_declaration(self):
        """Test parsing of type declarations."""
        parser = Parser()
        source = """
        namespace TestTypes;
        
        type Address {
            street: String
            city: String
            zipCode: String
            country: String
        }
        
        type GeoPoint {
            latitude: Float
            longitude: Float
        }
        """

        doc = parser.parse(source)

        assert isinstance(doc, Document)
        assert doc.namespace.name == "TestTypes"
        assert len(doc.declarations) == 2

        # Check types
        types = [d for d in doc.declarations if isinstance(d, TypeDeclaration)]
        assert len(types) == 2

        # Check Address type
        address = next(t for t in types if t.name == "Address")
        assert len(address.properties) == 4

        # Check property types
        address_prop_types = {p.name: p.type for p in address.properties}
        assert address_prop_types["street"] == "String"
        assert address_prop_types["city"] == "String"
        assert address_prop_types["zipCode"] == "String"
        assert address_prop_types["country"] == "String"

        # Check GeoPoint type
        geopoint = next(t for t in types if t.name == "GeoPoint")
        assert len(geopoint.properties) == 2

        # Check property types
        geopoint_prop_types = {p.name: p.type for p in geopoint.properties}
        assert geopoint_prop_types["latitude"] == "Float"
        assert geopoint_prop_types["longitude"] == "Float"

    def test_complex_model(self):
        """Test parsing of a complex model with multiple elements."""
        parser = Parser()
        source = """
        namespace TestComplex;
        
        type Address {
            street: String
            city: String
            zipCode: String
        }
        
        node Person {
            firstName: String
            lastName: String
            email: String
            homeAddress: Address
            workAddress: Address
        }
        
        node Company {
            name: String
            industry: String
            founded: Date
            address: Address
        }
        
        edge WorksFor: Person -> Company {
            position: String
            startDate: Date
            salary: Float
        }
        
        edge Located: Company -> Address {}
        """

        doc = parser.parse(source)

        assert isinstance(doc, Document)
        assert doc.namespace.name == "TestComplex"
        assert len(doc.declarations) == 5

        # Count declaration types
        nodes = [d for d in doc.declarations if isinstance(d, NodeDeclaration)]
        edges = [d for d in doc.declarations if isinstance(d, EdgeDeclaration)]
        types = [d for d in doc.declarations if isinstance(d, TypeDeclaration)]

        assert len(nodes) == 2
        assert len(edges) == 2
        assert len(types) == 1

        # Check Person node references Address type
        person = next(n for n in nodes if n.name == "Person")
        address_props = [p for p in person.properties if p.type == "Address"]
        assert len(address_props) == 2

        # Check WorksFor edge
        works_for = next(e for e in edges if e.name == "WorksFor")
        assert works_for.from_node == "Person"
        assert works_for.to_node == "Company"
        assert len(works_for.properties) == 3

    def test_comments(self):
        """Test parsing of comments in the GMDSL syntax."""
        parser = Parser()
        source = """
        namespace TestComments;
        
        // This is a comment about Person node
        node Person {
            name: String  // This is an inline comment
            /* This is a 
               multi-line comment */
            age: Integer
        }
        
        /* Another multi-line comment
           spanning multiple lines */
        node Comment {}
        """

        doc = parser.parse(source)

        # Comments should be ignored and parsing should succeed
        assert isinstance(doc, Document)
        assert doc.namespace.name == "TestComments"
        assert len(doc.declarations) == 2

        # Verify nodes were parsed correctly despite comments
        person = next(
            d
            for d in doc.declarations
            if isinstance(d, NodeDeclaration) and d.name == "Person"
        )
        assert len(person.properties) == 2

        comment_node = next(
            d
            for d in doc.declarations
            if isinstance(d, NodeDeclaration) and d.name == "Comment"
        )
        assert len(comment_node.properties) == 0

    def test_array_types(self):
        """Test parsing of array type declarations."""
        parser = Parser()
        source = """
        namespace TestArrays;
        
        node Person {
            name: String
            emails: [String]
            phoneNumbers: [String]
        }
        
        type Address {
            street: String
            tags: [String]
        }
        """

        doc = parser.parse(source)

        assert isinstance(doc, Document)
        assert doc.namespace.name == "TestArrays"

        # Check Person node with array properties
        person = next(d for d in doc.declarations if isinstance(d, NodeDeclaration))
        emails_prop = next(p for p in person.properties if p.name == "emails")
        assert emails_prop.type == "[String]"

        # Check Address type with array property
        address = next(d for d in doc.declarations if isinstance(d, TypeDeclaration))
        tags_prop = next(p for p in address.properties if p.name == "tags")
        assert tags_prop.type == "[String]"

    def test_invalid_syntax(self):
        """Test parser behavior with invalid syntax."""
        parser = Parser()
        invalid_source = """
        namespace TestInvalid
        
        node Person {
            name: String
            missing colon and type
        }
        """

        with pytest.raises(Exception):
            parser.parse(invalid_source)

    def test_empty_document(self):
        """Test parsing of an empty document."""
        parser = Parser()
        empty_source = """
        // Just a comment, no actual declarations
        """

        with pytest.raises(Exception):
            # Should raise an exception because no namespace is defined
            parser.parse(empty_source)

    def test_namespace_only(self):
        """Test parsing of a document with only a namespace."""
        parser = Parser()
        namespace_source = """
        namespace EmptyNamespace;
        """

        doc = parser.parse(namespace_source)

        assert isinstance(doc, Document)
        assert doc.namespace.name == "EmptyNamespace"
        assert len(doc.declarations) == 0

    def test_parse_empty_file(self):
        """Test parsing an empty file."""
        parser = Parser()
        ast = parser.parse("")
        assert ast is not None
        assert ast.namespace is None
        assert len(ast.declarations) == 0
        assert len(ast.imports) == 0

    def test_parse_namespace_only(self):
        """Test parsing a file with only a namespace declaration."""
        parser = Parser()
        ast = parser.parse("namespace TestNamespace;")
        assert ast is not None
        assert ast.namespace is not None
        assert ast.namespace.name == "TestNamespace"
        assert len(ast.declarations) == 0

    def test_parse_node_declaration(self):
        """Test parsing a node declaration."""
        parser = Parser()
        source = """
        namespace TestNamespace;
        
        node Person {
            name: String
            age: Integer
            isActive: Boolean
        }
        """
        ast = parser.parse(source)
        assert ast is not None
        assert ast.namespace.name == "TestNamespace"
        assert len(ast.declarations) == 1

        node = ast.declarations[0]
        assert node.name == "Person"
        assert len(node.properties) == 3

        props = {p.name: p.type_name for p in node.properties}
        assert props["name"] == "String"
        assert props["age"] == "Integer"
        assert props["isActive"] == "Boolean"

    def test_parse_type_declaration(self):
        """Test parsing a type declaration."""
        parser = Parser()
        source = """
        namespace TestNamespace;
        
        type Address {
            street: String
            city: String
            zipCode: String
        }
        """
        ast = parser.parse(source)
        assert ast is not None
        assert len(ast.declarations) == 1

        type_decl = ast.declarations[0]
        assert type_decl.name == "Address"
        assert len(type_decl.properties) == 3

        props = {p.name: p.type_name for p in type_decl.properties}
        assert props["street"] == "String"
        assert props["city"] == "String"
        assert props["zipCode"] == "String"

    def test_parse_edge_declaration(self):
        """Test parsing an edge declaration."""
        parser = Parser()
        source = """
        namespace TestNamespace;
        
        node Person { name: String }
        node Company { name: String }
        
        edge WorksAt: Person -> Company {
            position: String
            startDate: Date
        }
        """
        ast = parser.parse(source)
        assert ast is not None
        assert len(ast.declarations) == 3

        edge = [d for d in ast.declarations if hasattr(d, "source_node")][0]
        assert edge.name == "WorksAt"
        assert edge.source_node == "Person"
        assert edge.target_node == "Company"
        assert edge.direction == "->"
        assert len(edge.properties) == 2

        props = {p.name: p.type_name for p in edge.properties}
        assert props["position"] == "String"
        assert props["startDate"] == "Date"

    def test_parse_bidirectional_edge(self):
        """Test parsing a bidirectional edge."""
        parser = Parser()
        source = """
        namespace TestNamespace;
        
        node Person { name: String }
        
        edge Friend: Person <-> Person {
            since: Date
        }
        """
        ast = parser.parse(source)
        assert ast is not None

        edge = [d for d in ast.declarations if hasattr(d, "source_node")][0]
        assert edge.name == "Friend"
        assert edge.source_node == "Person"
        assert edge.target_node == "Person"
        assert "<->" in str(edge.direction)  # Direction might be a Tree object
        assert len(edge.properties) == 1
        assert edge.properties[0].name == "since"

    def test_parse_import_declaration(self):
        """Test parsing an import statement."""
        parser = Parser()
        source = """
        namespace TestNamespace;
        
        import "BaseTypes.gm";
        
        node Person {
            name: String
        }
        """
        ast = parser.parse(source)
        assert ast is not None
        assert len(ast.imports) == 1
        assert ast.imports[0].path == "BaseTypes.gm"

    def test_parse_complex_model(self):
        """Test parsing a complex model with multiple declarations."""
        parser = Parser()
        source = """
        namespace TestModel;
        
        import "CommonTypes.gm";
        
        type Address {
            street: String
            city: String
            country: String
        }
        
        node Person {
            firstName: String
            lastName: String
            birthDate: Date
            address: Address
        }
        
        node Company {
            name: String
            foundedDate: Date
            location: Address
        }
        
        edge WorksAt: Person -> Company {
            position: String
            startDate: Date
            salary: Float
        }
        
        edge LocatedAt: Company -> Address {}
        
        edge Manages: Person -> Person {
            since: Date
        }
        """
        ast = parser.parse(source)
        assert ast is not None
        assert ast.namespace.name == "TestModel"
        assert len(ast.imports) == 1
        assert len(ast.declarations) == 5

        # Count declarations by type
        node_count = len(
            [
                d
                for d in ast.declarations
                if hasattr(d, "properties") and not hasattr(d, "source_node")
            ]
        )
        type_count = len(
            [
                d
                for d in ast.declarations
                if hasattr(d, "properties")
                and not hasattr(d, "source_node")
                and not hasattr(d, "name")
                or (hasattr(d, "name") and d.name in ["Address"])
            ]
        )
        edge_count = len([d for d in ast.declarations if hasattr(d, "source_node")])

        assert node_count >= 2  # Person and Company
        assert type_count >= 1  # Address
        assert edge_count == 3  # WorksAt, LocatedAt, Manages

        # Check self-reference edge
        manages_edge = [
            d for d in ast.declarations if hasattr(d, "name") and d.name == "Manages"
        ][0]
        assert manages_edge.source_node == "Person"
        assert manages_edge.target_node == "Person"

    def test_parse_error_handling(self):
        """Test parser error handling with invalid syntax."""
        parser = Parser()

        # Missing closing brace
        with pytest.raises(Exception):
            parser.parse("""
            namespace TestNamespace;
            
            node Person {
                name: String
            """)

        # Invalid edge syntax
        with pytest.raises(Exception):
            parser.parse("""
            namespace TestNamespace;
            
            edge Invalid: Person >> Company {
                field: String
            }
            """)

        # Missing type name
        with pytest.raises(Exception):
            parser.parse("""
            namespace TestNamespace;
            
            node Person {
                name: 
            }
            """)

    def test_parse_with_comments(self):
        """Test parsing a file with comments."""
        parser = Parser()
        source = """
        // This is a comment
        namespace TestNamespace;
        
        /* This is a multi-line comment
           describing the Person node */
        node Person {
            // Name property
            name: String
            // Age property
            age: Integer  // End of line comment
        }
        """
        ast = parser.parse(source)
        assert ast is not None
        assert ast.namespace.name == "TestNamespace"
        assert len(ast.declarations) == 1

        node = ast.declarations[0]
        assert node.name == "Person"
        assert len(node.properties) == 2
