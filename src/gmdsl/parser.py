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
from typing import Optional, Union

from lark import Lark, Token, Transformer, Tree, v_args  # Import Tree

from . import ast

# Construct the path to the grammar file relative to this file
_GRAMMAR_PATH = os.path.join(os.path.dirname(__file__), "grammar.lark")


@v_args(inline=True)  # Makes rule processing methods receive children directly
class AstTransformer(Transformer):
    """Transforms the Lark parse tree into our custom AST nodes."""

    def __init__(self):
        super().__init__()
        self.current_namespace = None

    # --- Terminal conversions ---
    def IDENTIFIER(self, s):
        return str(s)

    def STRING(self, s):
        # Remove quotes from string literals
        return str(s)[1:-1]

    def NUMBER(self, s):
        # Try to convert to int first, then float if it has a decimal point
        if "." in str(s):
            return float(s)
        return int(s)

    # Helper method to qualify names with current namespace
    def qualify_name(self, name: Union[str, ast.QualifiedName]) -> ast.QualifiedName:
        if isinstance(name, ast.QualifiedName):
            return name

        if self.current_namespace and "." not in name:
            # If it's a simple name and we have a namespace, qualify it
            namespace_parts = self.current_namespace.name.parts
            return ast.QualifiedName(parts=namespace_parts + [name])
        else:
            # Either it's already qualified with dots or no namespace is set
            return ast.QualifiedName.from_str(name)

    # --- Annotation handling ---
    def annotation_param(self, name, type_name):
        qualified_type = self.qualify_name(type_name)
        return ast.AnnotationParameter(name=name, type_name=qualified_type)

    def annotation_params(self, *params):
        return [p for p in params if isinstance(p, ast.AnnotationParameter)]

    def annotation_decl(self, name, params=None):
        qualified_name = self.qualify_name(name)
        parameters = params if params else []
        return ast.AnnotationDeclaration(name=qualified_name, parameters=parameters)

    def annotation_arg(self, value):
        return ast.AnnotationArgument(value=value)

    def annotation_args(self, *args):
        return [a for a in args if isinstance(a, ast.AnnotationArgument)]

    def annotation_usage(self, name, args=None):
        qualified_name = self.qualify_name(name)
        arg_list = args if args else []
        return ast.AnnotationUsage(name=qualified_name, args=arg_list)

    # --- Rule conversions ---
    def property_decl(self, *items):
        # Extract annotations and property info
        annotations = []
        name = None
        type_name = None

        for item in items:
            if isinstance(item, ast.AnnotationUsage):
                annotations.append(item)
            elif name is None:
                name = item
            elif type_name is None:
                type_name = item

        # Do NOT qualify type_name here! Let validation handle it.
        qualified_type = type_name
        return ast.PropertyDeclaration(
            name=name, type_name=qualified_type, annotations=annotations
        )

    # Add methods for body rules
    def type_body(self, *properties):
        return [p for p in properties if isinstance(p, ast.PropertyDeclaration)]

    def node_body(self, *properties):
        return [p for p in properties if isinstance(p, ast.PropertyDeclaration)]

    def edge_body(self, *properties):
        return [p for p in properties if isinstance(p, ast.PropertyDeclaration)]

    def qualified_name(self, *parts):
        return ast.QualifiedName(parts=list(parts))

    def namespace_decl(self, name):
        self.current_namespace = ast.NamespaceDeclaration(name=name)
        return self.current_namespace

    def import_decl(self, module_name):
        # Accept qualified names for imports
        if isinstance(module_name, ast.QualifiedName):
            return ast.ImportDeclaration(module_name=module_name)
        elif isinstance(module_name, str):
            return ast.ImportDeclaration(
                module_name=ast.QualifiedName.from_str(module_name)
            )
        return ast.ImportDeclaration(module_name=module_name)

    # Simplify parent rules to use body results
    def type_decl(self, *items):
        # Extract annotations, name, and body
        annotations = []
        name = None
        body = None

        for item in items:
            if isinstance(item, ast.AnnotationUsage):
                annotations.append(item)
            elif name is None and isinstance(item, (str, ast.QualifiedName)):
                name = item
            elif isinstance(item, list):
                body = item

        # Qualify the name
        qualified_name = self.qualify_name(name)

        props = body if body else []
        return ast.TypeDeclaration(
            name=qualified_name, properties=props, annotations=annotations
        )

    def node_decl(self, *items):
        # Extract annotations, name, and body
        annotations = []
        name = None
        body = None

        for item in items:
            if isinstance(item, ast.AnnotationUsage):
                annotations.append(item)
            elif name is None and isinstance(item, (str, ast.QualifiedName)):
                name = item
            elif isinstance(item, list):
                body = item

        # Qualify the name
        qualified_name = self.qualify_name(name)

        props = body if body else []
        return ast.NodeDeclaration(
            name=qualified_name, properties=props, annotations=annotations
        )

    def edge_decl(self, *items):
        # Extract annotations and edge components
        annotations = []
        name = None
        source_node = None
        direction_value = None
        target_node = None
        body = None

        # Process items to extract annotations and other components
        non_annotation_items = []
        for item in items:
            if isinstance(item, ast.AnnotationUsage):
                annotations.append(item)
            else:
                non_annotation_items.append(item)

        # Process non-annotation items
        if len(non_annotation_items) >= 4:
            name = non_annotation_items[0]
            source_node = non_annotation_items[1]
            direction_value = non_annotation_items[2]
            target_node = non_annotation_items[3]
            if len(non_annotation_items) > 4:
                body = non_annotation_items[4]

        # Robustly flatten any nested lists for source_node and target_node
        def _flatten_first(item):
            while isinstance(item, list):
                if not item:
                    return None
                item = item[0]
            # Convert Token, Tree, or other types to string if needed
            from lark import Token, Tree

            if isinstance(item, Token):
                return str(item)
            if isinstance(item, Tree):
                # Try to extract a string from the tree's children if possible
                if item.children:
                    return str(item.children[0])
                return str(item)
            return item

        source_node = _flatten_first(source_node)
        target_node = _flatten_first(target_node)
        qualified_name = self.qualify_name(name)
        qualified_source = self.qualify_name(source_node)
        qualified_target = self.qualify_name(target_node)
        # Assert that qualified_source and qualified_target are QualifiedName
        assert isinstance(qualified_source, ast.QualifiedName), (
            f"source_node not QualifiedName: {qualified_source} ({type(qualified_source)})"
        )
        assert isinstance(qualified_target, ast.QualifiedName), (
            f"target_node not QualifiedName: {qualified_target} ({type(qualified_target)})"
        )

        # Explicitly handle if direction_value is Token or Tree
        direction = "->"  # Default direction
        if direction_value:
            if isinstance(direction_value, Token):
                direction = str(direction_value)
            elif (
                isinstance(direction_value, Tree)
                and direction_value.data == "edge_direction"
                and direction_value.children
            ):
                # If it's a Tree, assume the first child is the token we want
                direction = str(direction_value.children[0])
            else:
                # Fallback or error - use string representation
                print(
                    f"Warning: Unexpected type for edge direction: {type(direction_value)}"
                )
                direction = str(direction_value)

        props = body if body else []
        return ast.EdgeDeclaration(
            name=qualified_name,
            source_node=qualified_source,
            target_node=qualified_target,
            direction=direction,
            properties=props,
            annotations=annotations,
        )

    def edge_direction(self, *values):
        # Always return the direction as a string ("->" or "<->")
        return str(values[0]) if values else ""

    def document(self, *items):
        namespace = None
        imports = []
        declarations = []
        # Collect all items
        for item in items:
            if isinstance(item, Token) and item.type == "_NL":
                continue
            if item is None:
                continue
            if isinstance(item, ast.NamespaceDeclaration):
                if namespace:
                    print("Warning: Multiple namespace declarations found.")
                namespace = item
                self.current_namespace = item
            elif isinstance(item, ast.ImportDeclaration):
                imports.append(item)
            elif isinstance(
                item,
                (
                    ast.TypeDeclaration,
                    ast.NodeDeclaration,
                    ast.EdgeDeclaration,
                    ast.AnnotationDeclaration,
                ),
            ):
                declarations.append(item)
            elif isinstance(item, Token) and item.type == "COMMENT":
                pass
            else:
                print(
                    f"Warning: Unhandled item in document parsing: {type(item)} {item}"
                )
        return ast.Document(
            namespace=namespace, imports=imports, declarations=declarations
        )


def parse_gmdsl(text: str, source_path: Optional[str] = None) -> ast.Document:
    """Parses a GMDsl string and returns the AST Document."""
    # Read grammar only once (consider caching if performance critical)
    with open(_GRAMMAR_PATH, "r") as f:
        grammar = f.read()

    parser = Lark(
        grammar, start="document", parser="lalr", transformer=AstTransformer()
    )
    tree: ast.Document = parser.parse(text)
    if source_path is not None:
        tree = ast.Document(
            source_path=source_path,
            namespace=tree.namespace,
            imports=tree.imports,
            declarations=tree.declarations,
        )
    return tree
