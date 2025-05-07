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
from typing import Dict, Optional, Set

from gmdsl.ast import (
    Document,
    EdgeDeclaration,
    NodeDeclaration,
    TypeDeclaration,
)
from gmdsl.codegen import CodeGeneratorPlugin


class CSharpGenerator(CodeGeneratorPlugin):
    """C# code generator plugin."""

    def __init__(self):
        self.namespace = None
        self.loaded_asts = None

    def generate(
        self,
        loaded_asts: Dict[str, Document],
        output_dir: str,
        namespace: Optional[str] = None,
        *args,
        **kwargs,
    ):
        """Generate C# code from the loaded ASTs."""
        # Use provided namespace, or extract from first document, or fallback
        if namespace is not None:
            self.namespace = namespace
        else:
            # Try to get namespace from the first loaded AST document
            first_doc = next(iter(loaded_asts.values()), None)
            ns = None
            if first_doc and getattr(first_doc, "namespace", None):
                ns_decl = first_doc.namespace
                if ns_decl and getattr(ns_decl, "name", None):
                    ns = str(ns_decl.name)
            self.namespace = ns or "GraphDataModel"
        self.loaded_asts = loaded_asts

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Extract all node and edge declarations
        node_declarations = []
        edge_declarations = []
        type_declarations = []

        for ast in loaded_asts.values():
            for decl in ast.declarations:
                if isinstance(decl, NodeDeclaration):
                    node_declarations.append(decl)
                elif isinstance(decl, EdgeDeclaration):
                    edge_declarations.append(decl)
                elif isinstance(decl, TypeDeclaration):
                    type_declarations.append(decl)

        # Skip generating C# classes for GM.Core types that map to .NET types
        dotnet_core_types = {
            "GM.Core.String",
            "GM.Core.DateTime",
            "GM.Core.Boolean",
            "GM.Core.Integer",
            "GM.Core.Float",
        }
        node_declarations = [
            d for d in node_declarations if str(d.name) not in dotnet_core_types
        ]
        edge_declarations = [
            d for d in edge_declarations if str(d.name) not in dotnet_core_types
        ]
        type_declarations = [
            d for d in type_declarations if str(d.name) not in dotnet_core_types
        ]

        # Generate C# classes for nodes
        for node_decl in node_declarations:
            self._generate_node_class(node_decl, output_dir)

        # Generate C# classes for edges
        for edge_decl in edge_declarations:
            self._generate_edge_class(edge_decl, output_dir)

        # Generate C# classes for complex types
        for type_decl in type_declarations:
            self._generate_type_class(type_decl, output_dir)

    def _generate_node_class(self, node_decl: NodeDeclaration, output_dir: str):
        """Generate a C# class for a node declaration."""
        class_name = str(node_decl.name)
        file_path = os.path.join(output_dir, f"{class_name}.cs")

        # Check for annotations that affect code generation
        serializable = self.has_annotation(node_decl, "Serializable")
        immutable = self.has_annotation(node_decl, "Immutable")
        ignore_annotation = self.get_annotation(node_decl, "Ignore")
        ignored_properties = self._get_ignored_properties(ignore_annotation)

        with open(file_path, "w") as f:
            f.write("using System;\n")
            f.write("using System.Collections.Generic;\n\n")

            if serializable:
                f.write("using System.Text.Json.Serialization;\n\n")

            f.write(f"namespace {self.namespace}\n{{\n")

            # Apply class-level annotations
            if serializable:
                f.write("    [Serializable]\n")

            f.write(f"    public class {class_name}\n    {{\n")

            # Add properties
            for prop in node_decl.properties:
                # Skip ignored properties
                if prop.name in ignored_properties:
                    continue

                # Check for property-level annotations
                prop_annotations = self.get_annotations(prop)
                display_name = None
                for anno in prop_annotations:
                    if anno.name == "DisplayName" and anno.args and len(anno.args) > 0:
                        display_name = anno.args[0].value

                if display_name:
                    f.write(f'        [DisplayName("{display_name}")]\n')

                if serializable:
                    f.write(f'        [JsonPropertyName("{prop.name}")]\n')

                cs_type = self._to_csharp_type(str(prop.type_name))
                access = "{ get; }" if immutable else "{ get; set; }"
                f.write(f"        public {cs_type} {prop.name} {access}\n")

            f.write("    }\n")
            f.write("}")

    def _generate_edge_class(self, edge_decl: EdgeDeclaration, output_dir: str):
        """Generate a C# class for an edge declaration."""
        class_name = str(edge_decl.name)
        file_path = os.path.join(output_dir, f"{class_name}.cs")

        # Check for annotations that affect code generation
        serializable = self.has_annotation(edge_decl, "Serializable")
        immutable = self.has_annotation(edge_decl, "Immutable")
        ignore_annotation = self.get_annotation(edge_decl, "Ignore")
        ignored_properties = self._get_ignored_properties(ignore_annotation)

        with open(file_path, "w") as f:
            f.write("using System;\n")
            f.write("using System.Collections.Generic;\n\n")

            if serializable:
                f.write("using System.Text.Json.Serialization;\n\n")

            f.write(f"namespace {self.namespace}\n{{\n")

            # Apply class-level annotations
            if serializable:
                f.write("    [Serializable]\n")

            f.write(f"    public class {class_name}\n    {{\n")

            # Source and target references
            source_type = str(edge_decl.source_node)
            target_type = str(edge_decl.target_node)
            access = "{ get; }" if immutable else "{ get; set; }"

            f.write(f"        public string SourceId {access}\n")
            f.write(f"        public string TargetId {access}\n")

            # Add references to source and target objects if needed
            rel_annotation = self.get_annotation(edge_decl, "RelationshipType")
            if (
                rel_annotation
                and self.get_annotation_arg_value(rel_annotation, 0, "Reference")
                == "Navigation"
            ):
                f.write(f"        public {source_type} Source {access}\n")
                f.write(f"        public {target_type} Target {access}\n")

            # Add properties
            for prop in edge_decl.properties:
                # Skip ignored properties
                if prop.name in ignored_properties:
                    continue

                # Check for property-level annotations
                prop_annotations = self.get_annotations(prop)
                display_name = None
                for anno in prop_annotations:
                    if anno.name == "DisplayName" and anno.args and len(anno.args) > 0:
                        display_name = anno.args[0].value

                if display_name:
                    f.write(f'        [DisplayName("{display_name}")]\n')

                if serializable:
                    f.write(f'        [JsonPropertyName("{prop.name}")]\n')

                cs_type = self._to_csharp_type(str(prop.type_name))
                f.write(f"        public {cs_type} {prop.name} {access}\n")

            f.write("    }\n")
            f.write("}")

    def _generate_type_class(self, type_decl: TypeDeclaration, output_dir: str):
        """Generate a C# class for a type declaration."""
        class_name = str(type_decl.name)
        file_path = os.path.join(output_dir, f"{class_name}.cs")

        # Check for annotations that affect code generation
        serializable = self.has_annotation(type_decl, "Serializable")
        immutable = self.has_annotation(type_decl, "Immutable")
        struct_anno = self.has_annotation(type_decl, "Struct")
        ignore_annotation = self.get_annotation(type_decl, "Ignore")
        ignored_properties = self._get_ignored_properties(ignore_annotation)

        with open(file_path, "w") as f:
            f.write("using System;\n")
            f.write("using System.Collections.Generic;\n\n")

            if serializable:
                f.write("using System.Text.Json.Serialization;\n\n")

            f.write(f"namespace {self.namespace}\n{{\n")

            # Apply class-level annotations
            if serializable:
                f.write("    [Serializable]\n")

            # Use struct instead of class if annotated as Struct
            type_keyword = "struct" if struct_anno else "class"
            f.write(f"    public {type_keyword} {class_name}\n    {{\n")

            # Add properties
            for prop in type_decl.properties:
                # Skip ignored properties
                if prop.name in ignored_properties:
                    continue

                # Check for property-level annotations
                prop_annotations = self.get_annotations(prop)
                display_name = None
                for anno in prop_annotations:
                    if anno.name == "DisplayName" and anno.args and len(anno.args) > 0:
                        display_name = anno.args[0].value

                if display_name:
                    f.write(f'        [DisplayName("{display_name}")]\n')

                if serializable:
                    f.write(f'        [JsonPropertyName("{prop.name}")]\n')

                cs_type = self._to_csharp_type(str(prop.type_name))
                access = "{ get; }" if immutable else "{ get; set; }"
                f.write(f"        public {cs_type} {prop.name} {access}\n")

            f.write("    }\n")
            f.write("}")

    def _to_csharp_type(self, gm_type: str) -> str:
        gm_type = str(gm_type)
        # Only map GM.Core.* types to .NET types
        if gm_type.startswith("GM.Core."):
            simple_type = gm_type[len("GM.Core.") :]
            gm_map = {
                "String": "string",
                "DateTime": "System.DateTime",
                "Boolean": "bool",
                "Integer": "int",
                "Float": "float",
            }
            if simple_type in gm_map:
                return gm_map[simple_type]
        elif gm_type.startswith("list<"):
            element_type = gm_type[5:-1]
            return f"List<{self._to_csharp_type(element_type)}>"
        elif gm_type.startswith("map<"):
            parts = gm_type[4:-1].split(",")
            key_type = self._to_csharp_type(parts[0].strip())
            value_type = self._to_csharp_type(parts[1].strip())
            return f"Dictionary<{key_type}, {value_type}>"
        else:
            # Assume it's a custom type
            return gm_type

    def _get_ignored_properties(self, ignore_annotation) -> Set[str]:
        """Extract property names to ignore from the Ignore annotation."""
        ignored_properties = set()
        if ignore_annotation and ignore_annotation.args:
            for arg in ignore_annotation.args:
                ignored_properties.add(arg.value)
        return ignored_properties
