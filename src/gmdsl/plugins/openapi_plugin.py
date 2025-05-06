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
from typing import Dict, Optional

try:
    import inflect
except ImportError:
    inflect = None

import yaml

try:
    from apispec import APISpec
except ImportError:
    APISpec = None

from gmdsl.ast import Document, EdgeDeclaration, NodeDeclaration, PropertyDeclaration
from gmdsl.codegen import CodeGeneratorPlugin


class OpenAPIGenerator(CodeGeneratorPlugin):
    """Generates an OpenAPI document from the graph data model."""

    def generate(
        self,
        loaded_asts: Dict[str, Document],
        output_dir: str,
        root: Optional[str] = "",
        openapi_version: str = "3.1.1",
        title: str = "GMDSL Graph API",
        version: str = "1.0.0",
        bearer_auth: bool = False,
        output_format: str = "yaml",
    ):
        if APISpec is None:
            raise ImportError(
                "apispec is required for OpenAPI generation. Please install it."
            )
        p = inflect.engine() if inflect else None

        def to_plural(name: str) -> str:
            if p:
                plural = p.plural(name)
                if plural:
                    return plural
            if name.endswith("s"):
                return name
            return name + "s"

        def to_kebab_case(name: str) -> str:
            import re

            s1 = re.sub("(.)([A-Z][a-z]+)", r"\1-\2", name)
            s2 = re.sub("([a-z0-9])([A-Z])", r"\1-\2", s1)
            return s2.replace("_", "-").lower()

        def node_path(root: str, node_name: str) -> str:
            plural = to_plural(to_kebab_case(node_name))
            if root:
                return f"/{root.strip('/')}/{plural}"
            return f"/{plural}"

        def instance_path(root: str, node_name: str) -> str:
            plural = to_plural(to_kebab_case(node_name))
            if root:
                return f"/{root.strip('/')}/{plural}/{{node-id}}"
            return f"/{plural}/{{node-id}}"

        def rel_path(root: str, node_name: str, rel_name: str) -> str:
            node_plural = to_plural(to_kebab_case(node_name))
            rel_plural = to_plural(to_kebab_case(rel_name))
            if root:
                return f"/{root.strip('/')}/{node_plural}/{{node-id}}/{rel_plural}"
            return f"/{node_plural}/{{node-id}}/{rel_plural}"

        def rel_instance_path(root: str, node_name: str, rel_name: str) -> str:
            node_plural = to_plural(to_kebab_case(node_name))
            rel_plural = to_plural(to_kebab_case(rel_name))
            if root:
                return f"/{root.strip('/')}/{node_plural}/{{node-id}}/{rel_plural}/{{relationship-id}}"
            return f"/{node_plural}/{{node-id}}/{rel_plural}/{{relationship-id}}"

        def property_to_schema(prop: PropertyDeclaration) -> dict:
            type_map = {
                "String": ("string", None),
                "Integer": ("integer", "int32"),
                "Float": ("number", "float"),
                "Boolean": ("boolean", None),
                "Date": ("string", "date"),
            }
            t = str(prop.type_name.simple_name)
            typ, fmt = type_map.get(t, ("string", None))
            schema = {"type": typ}
            if fmt:
                schema["format"] = fmt
            return schema

        # Create APISpec
        spec = APISpec(
            title=title,
            version=version,
            openapi_version=openapi_version,
            info=dict(description=f"OpenAPI spec for {title}"),
        )

        # Add bearer authentication if requested
        if bearer_auth:
            spec.components.security_scheme(
                "bearerAuth",
                {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                },
            )
            # Set global security requirement
            if "security" not in spec.options:
                spec.options["security"] = []
            spec.options["security"].append({"bearerAuth": []})

        nodes = {}
        edges = []
        # Collect nodes and edges
        for doc in loaded_asts.values():
            for decl in doc.declarations:
                if isinstance(decl, NodeDeclaration):
                    nodes[str(decl.name.simple_name)] = decl
                elif isinstance(decl, EdgeDeclaration):
                    edges.append(decl)

        # Add schemas for nodes
        for node_name, node in nodes.items():
            schema_name = to_kebab_case(node_name)
            properties = {
                prop.name: property_to_schema(prop) for prop in node.properties
            }
            spec.components.schema(
                schema_name, {"type": "object", "properties": properties}
            )

        # Add schemas for edges
        for edge in edges:
            rel_name = str(edge.name.simple_name)
            rel_schema = to_kebab_case(rel_name)
            properties = {
                prop.name: property_to_schema(prop) for prop in edge.properties
            }
            spec.components.schema(
                rel_schema, {"type": "object", "properties": properties}
            )

        # Paths for nodes
        for node_name, node in nodes.items():
            npath = node_path(root, node_name)
            ipath = instance_path(root, node_name)
            schema_name = to_kebab_case(node_name)
            # POST (create)
            spec.path(
                path=npath,
                operations={
                    "post": {
                        "summary": f"Create {node_name}",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": f"#/components/schemas/{schema_name}"
                                    }
                                }
                            },
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                },
            )
            # GET, PUT, DELETE (instance)
            spec.path(
                path=ipath,
                operations={
                    "get": {
                        "summary": f"Get {node_name} by ID",
                        "responses": {"200": {"description": "OK"}},
                    },
                    "put": {
                        "summary": f"Update {node_name} by ID",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": f"#/components/schemas/{schema_name}"
                                    }
                                }
                            },
                        },
                        "responses": {"200": {"description": "Updated"}},
                    },
                    "delete": {
                        "summary": f"Delete {node_name} by ID",
                        "responses": {"204": {"description": "Deleted"}},
                    },
                },
            )

        # Paths for edges/relationships
        for edge in edges:
            rel_name = str(edge.name.simple_name)
            src = str(edge.source_node.simple_name)
            tgt = str(edge.target_node.simple_name)
            direction = edge.direction
            rel_schema = to_kebab_case(rel_name)

            def rel_paths_for(node, rel, incoming=False, outgoing=False):
                suffix = ""
                if incoming:
                    suffix = "-incoming"
                elif outgoing:
                    suffix = "-outgoing"
                base_rel = rel + suffix
                return rel_path(root, node, base_rel), rel_instance_path(
                    root, node, base_rel
                )

            if direction == "->":
                rpath, ripath = (
                    rel_path(root, src, rel_name),
                    rel_instance_path(root, src, rel_name),
                )
                # POST (create relationship)
                spec.path(
                    path=rpath,
                    operations={
                        "post": {
                            "summary": f"Create {rel_name} from {src}",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": f"#/components/schemas/{rel_schema}"
                                        }
                                    }
                                },
                            },
                            "responses": {"201": {"description": "Created"}},
                        }
                    },
                )
                # GET, PUT, DELETE (relationship instance)
                spec.path(
                    path=ripath,
                    operations={
                        "get": {
                            "summary": f"Get {rel_name} by ID",
                            "responses": {"200": {"description": "OK"}},
                        },
                        "put": {
                            "summary": f"Update {rel_name} by ID",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": f"#/components/schemas/{rel_schema}"
                                        }
                                    }
                                },
                            },
                            "responses": {"200": {"description": "Updated"}},
                        },
                        "delete": {
                            "summary": f"Delete {rel_name} by ID",
                            "responses": {"204": {"description": "Deleted"}},
                        },
                    },
                )
            elif direction == "<->":
                if src == tgt:
                    for incoming, outgoing in [(True, False), (False, True)]:
                        rpath, ripath = rel_paths_for(
                            src, rel_name, incoming=incoming, outgoing=outgoing
                        )
                        spec.path(
                            path=rpath,
                            operations={
                                "post": {
                                    "summary": f"Create {rel_name}{'-incoming' if incoming else '-outgoing'} for {src}",
                                    "requestBody": {
                                        "required": True,
                                        "content": {
                                            "application/json": {
                                                "schema": {
                                                    "$ref": f"#/components/schemas/{rel_schema}"
                                                }
                                            }
                                        },
                                    },
                                    "responses": {"201": {"description": "Created"}},
                                }
                            },
                        )
                        spec.path(
                            path=ripath,
                            operations={
                                "get": {
                                    "summary": f"Get {rel_name}{'-incoming' if incoming else '-outgoing'} by ID",
                                    "responses": {"200": {"description": "OK"}},
                                },
                                "put": {
                                    "summary": f"Update {rel_name}{'-incoming' if incoming else '-outgoing'} by ID",
                                    "requestBody": {
                                        "required": True,
                                        "content": {
                                            "application/json": {
                                                "schema": {
                                                    "$ref": f"#/components/schemas/{rel_schema}"
                                                }
                                            }
                                        },
                                    },
                                    "responses": {"200": {"description": "Updated"}},
                                },
                                "delete": {
                                    "summary": f"Delete {rel_name}{'-incoming' if incoming else '-outgoing'} by ID",
                                    "responses": {"204": {"description": "Deleted"}},
                                },
                            },
                        )
                else:
                    for node in [src, tgt]:
                        rpath, ripath = (
                            rel_path(root, node, rel_name),
                            rel_instance_path(root, node, rel_name),
                        )
                        spec.path(
                            path=rpath,
                            operations={
                                "post": {
                                    "summary": f"Create {rel_name} for {node}",
                                    "requestBody": {
                                        "required": True,
                                        "content": {
                                            "application/json": {
                                                "schema": {
                                                    "$ref": f"#/components/schemas/{rel_schema}"
                                                }
                                            }
                                        },
                                    },
                                    "responses": {"201": {"description": "Created"}},
                                }
                            },
                        )
                        spec.path(
                            path=ripath,
                            operations={
                                "get": {
                                    "summary": f"Get {rel_name} by ID",
                                    "responses": {"200": {"description": "OK"}},
                                },
                                "put": {
                                    "summary": f"Update {rel_name} by ID",
                                    "requestBody": {
                                        "required": True,
                                        "content": {
                                            "application/json": {
                                                "schema": {
                                                    "$ref": f"#/components/schemas/{rel_schema}"
                                                }
                                            }
                                        },
                                    },
                                    "responses": {"200": {"description": "Updated"}},
                                },
                                "delete": {
                                    "summary": f"Delete {rel_name} by ID",
                                    "responses": {"204": {"description": "Deleted"}},
                                },
                            },
                        )

        # Serialize
        output_file_path = os.path.join(output_dir, f"openapi.{output_format}")
        spec_dict = spec.to_dict()
        if output_format == "json":
            import json

            with open(output_file_path, "w") as f:
                json.dump(spec_dict, f, indent=2)
        else:
            with open(output_file_path, "w") as f:
                yaml.dump(spec_dict, f, sort_keys=False)
        print(f"Successfully wrote OpenAPI spec to {output_file_path}")
