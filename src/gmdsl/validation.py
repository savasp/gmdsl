from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Union

from . import ast


@dataclass
class ValidationError:
    message: str
    source_path: Optional[str] = None
    # TODO: Add location info (line/column) if needed later


class Validator:
    """Performs semantic validation on a collection of loaded GMDsl ASTs."""

    def __init__(self):
        # State is now managed per-validation run
        pass

    def _add_error(self, message: str, source_path: Optional[str] = None):
        self.errors.append(ValidationError(message=message, source_path=source_path))

    def _resolve_property_types(self, loaded_asts: Dict[str, ast.Document]):
        ns_type_maps = {}
        for doc in loaded_asts.values():
            ns = str(doc.namespace.name) if doc.namespace else None
            if ns:
                type_map = {}
                for decl in doc.declarations:
                    if hasattr(decl, "name") and hasattr(decl, "properties"):
                        type_map[decl.name.simple_name] = decl.name
                ns_suffix = ns.split(".")[-1]
                ns_type_maps[ns_suffix] = type_map
                ns_type_maps[ns] = type_map  # Also allow full match

        for doc in loaded_asts.values():
            import_type_map = {}
            for imp in doc.imports:
                import_name = (
                    imp.module_name.simple_name
                    if hasattr(imp.module_name, "simple_name")
                    else str(imp.module_name)
                )
                for ns_key in [
                    import_name,
                    import_name.capitalize(),
                    import_name.lower(),
                    import_name.upper(),
                ]:
                    if ns_key in ns_type_maps:
                        import_type_map.update(ns_type_maps[ns_key])
                for ns_key in ns_type_maps:
                    if ns_key.lower().endswith(import_name.lower()):
                        import_type_map.update(ns_type_maps[ns_key])

            for i, decl in enumerate(doc.declarations):
                if hasattr(decl, "name") and hasattr(decl, "properties"):
                    new_properties = []
                    for prop in decl.properties:
                        t = prop.type_name
                        resolved_type = t
                        if (
                            not isinstance(t, ast.QualifiedName)
                            and isinstance(t, str)
                            and "." not in t
                        ):
                            if t in import_type_map:
                                resolved_type = import_type_map[t]
                            else:
                                ns = decl.name.parts[:-1]
                                resolved_type = ast.QualifiedName(parts=ns + [t])
                        # Create a new PropertyDeclaration with the resolved type
                        new_properties.append(
                            type(prop)(
                                name=prop.name,
                                type_name=resolved_type,
                                annotations=getattr(prop, "annotations", []),
                            )
                        )
                    # Replace the properties list (for frozen dataclasses, create a new declaration)
                    if isinstance(decl, ast.EdgeDeclaration):
                        new_decl = type(decl)(
                            name=decl.name,
                            source_node=decl.source_node,
                            target_node=decl.target_node,
                            direction=decl.direction,
                            properties=new_properties,
                            annotations=getattr(decl, "annotations", []),
                        )
                    elif hasattr(decl, "annotations"):
                        new_decl = type(decl)(
                            name=decl.name,
                            properties=new_properties,
                            annotations=getattr(decl, "annotations", []),
                        )
                    else:
                        new_decl = type(decl)(name=decl.name, properties=new_properties)
                    doc.declarations[i] = new_decl

    def validate(self, loaded_asts: Dict[str, ast.Document]) -> List[ValidationError]:
        """Validates the entire collection of loaded ASTs."""
        self._resolve_property_types(loaded_asts)
        self.errors: List[ValidationError] = []
        self.defined_types: Dict[str, ast.TypeDeclaration] = {}
        self.defined_nodes: Dict[str, ast.NodeDeclaration] = {}
        self.defined_annotations: Dict[str, ast.AnnotationDeclaration] = {}

        # --- First Pass: Collect all definitions ---
        core_types_namespace = ast.QualifiedName.from_str("gm.CoreTypes")
        core_types_doc: Optional[ast.Document] = None

        for doc_path, doc in loaded_asts.items():
            # Identify the core types document if present
            if doc.namespace and doc.namespace.name == core_types_namespace:
                core_types_doc = doc

            current_namespace = (
                doc.namespace.name if doc.namespace else ast.QualifiedName.from_str("")
            )

            for declaration in doc.declarations:
                # Only re-qualify names for declarations defined in this document
                if not isinstance(declaration.name, ast.QualifiedName):
                    declaration.name = ast.QualifiedName.from_str(declaration.name)

                # Determine if declaration is local (namespace matches current doc)
                is_local = (
                    doc.namespace
                    and declaration.name.parts[0 : len(current_namespace.parts)]
                    == current_namespace.parts
                ) or not doc.namespace

                # Only compute a qualified name for lookup, never mutate imported declaration.name
                if is_local:
                    # Local declaration: ensure fully qualified name for lookup
                    if (
                        current_namespace.parts
                        and declaration.name.parts
                        and not any(
                            part in declaration.name.parts[0:-1]
                            for part in current_namespace.parts
                        )
                    ):
                        qualified_parts = current_namespace.parts + [
                            declaration.name.simple_name
                        ]
                        qualified_name = ast.QualifiedName(parts=qualified_parts)
                    else:
                        qualified_name = declaration.name
                else:
                    # Imported declaration: always use its original qualified name
                    qualified_name = declaration.name

                def_name = str(qualified_name)

                if isinstance(declaration, ast.TypeDeclaration):
                    if def_name in self.defined_types:
                        self._add_error(
                            f"Duplicate type definition: '{def_name}'", doc_path
                        )
                    else:
                        self.defined_types[def_name] = declaration
                elif isinstance(declaration, ast.NodeDeclaration):
                    if def_name in self.defined_nodes:
                        self._add_error(
                            f"Duplicate node definition: '{def_name}'", doc_path
                        )
                    else:
                        self.defined_nodes[def_name] = declaration
                elif isinstance(declaration, ast.AnnotationDeclaration):
                    if def_name in self.defined_annotations:
                        self._add_error(
                            f"Duplicate annotation definition: '{def_name}'", doc_path
                        )
                    else:
                        self.defined_annotations[def_name] = declaration

        # --- Second Pass: Validate references within each document ---
        for doc_path, doc in loaded_asts.items():
            available_types = self._get_available_types(
                doc, core_types_doc, loaded_asts
            )
            available_nodes = self._get_available_nodes(doc)
            available_annotations = self._get_available_annotations(doc)

            for declaration in doc.declarations:
                if isinstance(
                    declaration,
                    (ast.TypeDeclaration, ast.NodeDeclaration, ast.EdgeDeclaration),
                ):
                    self._validate_properties(declaration, available_types, doc_path)

                    # Validate annotations in declaration
                    self._validate_annotations(
                        declaration.annotations, available_annotations, doc_path
                    )

                if isinstance(declaration, ast.EdgeDeclaration):
                    self._validate_edge(declaration, available_nodes, doc_path)

                if isinstance(declaration, ast.AnnotationDeclaration):
                    self._validate_annotation_declaration(
                        declaration, available_types, doc_path
                    )

        return self.errors

    def validate_model(self, model):
        """Validate a GraphDataModel for correctness."""
        self.errors = []

        # First, collect all defined types, nodes, edges, and annotations
        for decl in model.declarations:
            if hasattr(decl, "name"):
                name = decl.name
                if isinstance(decl, ast.TypeDecl):
                    self.defined_types[name] = decl
                elif isinstance(decl, ast.NodeDecl):
                    self.defined_nodes[name] = decl
                elif isinstance(decl, ast.EdgeDecl):
                    self.defined_edges[name] = decl
                elif isinstance(decl, ast.AnnotationDecl):
                    self.defined_annotations[name] = decl

        # Then validate all declarations
        for decl in model.declarations:
            if isinstance(decl, ast.TypeDecl):
                self._validate_type_decl(decl)
            elif isinstance(decl, ast.NodeDecl):
                self._validate_node_decl(decl)
            elif isinstance(decl, ast.EdgeDecl):
                self._validate_edge_decl(decl)
            elif isinstance(decl, ast.AnnotationDecl):
                self._validate_annotation_declaration(decl)

        # Validate all annotation usages across declarations
        for decl in model.declarations:
            if hasattr(decl, "annotations") and decl.annotations:
                self._validate_annotations(decl.annotations, decl)

            # Check annotations on fields for NodeDecl and TypeDecl
            if isinstance(decl, (ast.NodeDecl, ast.TypeDecl)) and hasattr(
                decl, "fields"
            ):
                for field in decl.fields:
                    if hasattr(field, "annotations") and field.annotations:
                        self._validate_annotations(field.annotations, field)

        return len(self.errors) == 0

    def _get_available_types(
        self,
        current_doc: ast.Document,
        core_types_doc: Optional[ast.Document],
        all_docs: Dict[str, ast.Document],
    ) -> Set[str]:
        """Determines the set of type names available in the scope of current_doc."""
        available = set()

        # 1. Types defined in the current document
        for decl in current_doc.declarations:
            if isinstance(decl, ast.TypeDeclaration):
                # Add both simple name and fully qualified name
                available.add(decl.name.simple_name)
                available.add(str(decl.name))

        # 2. Types imported explicitly
        for imp in current_doc.imports:
            import_name = (
                imp.module_name.simple_name
                if isinstance(imp.module_name, ast.QualifiedName)
                else str(imp.module_name)
            )
            for doc in all_docs.values():
                ns = str(doc.namespace.name) if doc.namespace else ""
                if ns.lower().endswith(import_name.lower()):
                    for decl in doc.declarations:
                        if isinstance(decl, ast.TypeDeclaration):
                            available.add(decl.name.simple_name)
                            available.add(str(decl.name))

        return available

    def _get_available_nodes(self, current_doc: ast.Document) -> Set[str]:
        available = set()
        for decl in current_doc.declarations:
            if isinstance(decl, ast.NodeDeclaration):
                available.add(decl.name.simple_name)
                available.add(str(decl.name))
        for name in self.defined_nodes.keys():
            node = self.defined_nodes[name]
            available.add(node.name.simple_name)
            available.add(str(node.name))
        return available

    def _get_available_annotations(self, current_doc: ast.Document) -> Set[str]:
        available = set()
        for decl in current_doc.declarations:
            if isinstance(decl, ast.AnnotationDeclaration):
                available.add(decl.name.simple_name)
                available.add(str(decl.name))
        for name in self.defined_annotations.keys():
            annotation = self.defined_annotations[name]
            available.add(annotation.name.simple_name)
            available.add(str(annotation.name))
        return available

    def _validate_properties(
        self,
        declaration: Union[
            ast.TypeDeclaration, ast.NodeDeclaration, ast.EdgeDeclaration
        ],
        available_types: Set[str],
        source_path: Optional[str],
    ):
        """Validates that all property types are defined or imported."""
        for prop in declaration.properties:
            if prop.type_name is None:
                continue  # Skip validation for properties without types

            # Convert to QualifiedName if it's a string
            prop_type = prop.type_name
            if not isinstance(prop_type, ast.QualifiedName):
                prop_type = ast.QualifiedName.from_str(prop.type_name)

            # Try both simple name and fully qualified name
            type_name = str(prop_type)
            simple_name = prop_type.simple_name

            if simple_name not in available_types and type_name not in available_types:
                self._add_error(
                    f"Unknown type '{type_name}' used in property '{prop.name}' of '{declaration.name}'",
                    source_path,
                )

    def _validate_edge(
        self, edge: ast.EdgeDeclaration, available_nodes: Set[str], source_path: str
    ):
        """Validates node references within an edge declaration."""
        # Compare using string representations to avoid unhashable errors
        source_str = str(edge.source_node)
        target_str = str(edge.target_node)
        if source_str not in available_nodes:
            self._add_error(
                f"Undefined source node '{source_str}' in edge '{edge.name}'",
                source_path,
            )
        if target_str not in available_nodes:
            self._add_error(
                f"Undefined target node '{target_str}' in edge '{edge.name}'",
                source_path,
            )

    def _validate_annotations(
        self,
        annotations: List[ast.AnnotationUsage],
        available_annotations: Set[str],
        source_path: Optional[str],
    ):
        """Validates that all annotations are defined."""
        for annotation in annotations:
            # Convert to QualifiedName if needed
            anno_name = annotation.name
            if not isinstance(anno_name, ast.QualifiedName):
                anno_name = ast.QualifiedName.from_str(annotation.name)

            full_name = str(anno_name)
            simple_name = anno_name.simple_name

            if (
                simple_name not in available_annotations
                and full_name not in available_annotations
            ):
                self._add_error(f"Unknown annotation '{full_name}'", source_path)

    def _validate_annotation_declaration(
        self,
        annotation: ast.AnnotationDeclaration,
        available_types: Set[str],
        source_path: Optional[str],
    ):
        """Validates that all parameter types in annotation declarations are defined."""
        for param in annotation.parameters:
            # Convert to QualifiedName if needed
            param_type = param.type_name
            if not isinstance(param_type, ast.QualifiedName):
                param_type = ast.QualifiedName.from_str(param.type_name)

            type_name = str(param_type)
            simple_name = param_type.simple_name

            if simple_name not in available_types and type_name not in available_types:
                self._add_error(
                    f"Unknown type '{type_name}' used in parameter '{param.name}' of annotation '{annotation.name}'",
                    source_path,
                )

    def _validate_annotation_arguments(
        self,
        annotation: ast.AnnotationUsage,
        declaration: ast.AnnotationDeclaration,
        source_path: str,
    ):
        """Validates that annotation arguments match the parameters defined in the declaration."""
        # Create a map of parameter names to their definitions for easy lookup
        param_map = {param.name: param for param in declaration.parameters}

        # Track which parameters have been provided
        provided_params = set()

        # Check each argument against the declaration
        for arg in annotation.arguments:
            if arg.name:
                # Named argument
                if arg.name not in param_map:
                    self._add_error(
                        f"Unknown parameter '{arg.name}' in annotation '@{annotation.name}'",
                        source_path,
                    )
                else:
                    provided_params.add(arg.name)
                    # TODO: Type checking for argument values when we have more complex types
            else:
                # Positional argument - not currently supported
                self._add_error(
                    f"Positional arguments are not supported in annotation '@{annotation.name}'",
                    source_path,
                )

        # Check for required parameters that weren't provided
        for param_name, param in param_map.items():
            if not param.optional and param_name not in provided_params:
                self._add_error(
                    f"Missing required parameter '{param_name}' in annotation '@{annotation.name}'",
                    source_path,
                )

    def _validate_argument_type(self, value, param, annotation_name, source_path=None):
        """Validates that an argument value matches the expected parameter type."""
        param_type = param.type_name if hasattr(param, "type_name") else None

        if param_type is None:
            return  # Cannot validate without type information

        # Basic type checking for common types
        if param_type == "string":
            if not isinstance(value, str):
                self._add_error(
                    f"Annotation '{annotation_name}': parameter '{param.name}' expects string, got '{type(value).__name__}'",
                    source_path,
                )
        elif param_type == "int" or param_type == "integer":
            if not isinstance(value, int) or isinstance(
                value, bool
            ):  # bool is a subclass of int in Python
                self._add_error(
                    f"Annotation '{annotation_name}': parameter '{param.name}' expects integer, got '{type(value).__name__}'",
                    source_path,
                )
        elif param_type == "float" or param_type == "number":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                self._add_error(
                    f"Annotation '{annotation_name}': parameter '{param.name}' expects number, got '{type(value).__name__}'",
                    source_path,
                )
        elif param_type == "bool" or param_type == "boolean":
            if not isinstance(value, bool):
                self._add_error(
                    f"Annotation '{annotation_name}': parameter '{param.name}' expects boolean, got '{type(value).__name__}'",
                    source_path,
                )
        elif param_type.startswith("[") and param_type.endswith("]"):
            # List type
            if not isinstance(value, list):
                self._add_error(
                    f"Annotation '{annotation_name}': parameter '{param.name}' expects array, got '{type(value).__name__}'",
                    source_path,
                )
            else:
                # Validate list elements if element type is specified
                element_type = param_type[1:-1].strip()
                if element_type:
                    for i, item in enumerate(value):
                        # Create a temporary parameter for the list item type
                        from gmdsl.ast import AnnotationParameter

                        temp_param = AnnotationParameter(param.name, element_type)
                        self._validate_argument_type(
                            item, temp_param, annotation_name, source_path
                        )

    def _validate_annotation_usage(
        self, usage: ast.AnnotationUsage, source_path: str
    ) -> None:
        """Validates that an annotation usage refers to a declared annotation
        and has the correct arguments."""
        # Check if the annotation is declared
        if usage.name not in self.annotations:
            self.errors.append(
                ValidationError(
                    f"Unknown annotation '@{usage.name}'",
                    source_path,
                    usage.line,
                    usage.column,
                )
            )
            return

        declaration = self.annotations[usage.name]

        # Check if the number of arguments matches the number of parameters
        required_params = [p for p in declaration.parameters if not p.default_value]
        if len(usage.arguments) < len(required_params):
            self.errors.append(
                ValidationError(
                    f"Annotation '@{usage.name}' requires at least {len(required_params)} arguments, but {len(usage.arguments)} were provided",
                    source_path,
                    usage.line,
                    usage.column,
                )
            )

        # Check if named arguments correspond to declared parameters
        param_dict = {param.name: param for param in declaration.parameters}
        used_params = set()

        for arg in usage.arguments:
            if arg.name:
                if arg.name not in param_dict:
                    self.errors.append(
                        ValidationError(
                            f"Unknown parameter '{arg.name}' in annotation '@{usage.name}'",
                            source_path,
                            arg.line,
                            arg.column,
                        )
                    )
                elif arg.name in used_params:
                    self.errors.append(
                        ValidationError(
                            f"Duplicate argument for parameter '{arg.name}' in annotation '@{usage.name}'",
                            source_path,
                            arg.line,
                            arg.column,
                        )
                    )
                else:
                    used_params.add(arg.name)

        # Check for positional arguments after named arguments
        has_named = False
        for arg in usage.arguments:
            if arg.name:
                has_named = True
            elif has_named:
                self.errors.append(
                    ValidationError(
                        f"Positional argument after named argument in annotation '@{usage.name}'",
                        source_path,
                        arg.line,
                        arg.column,
                    )
                )

    def _validate_annotations(self, usages, available_annotations, source_path=None):
        """Validates a list of annotation usages against available annotation declarations."""
        if not usages:
            return

        for usage in usages:
            if usage.name not in available_annotations:
                self._add_error(f"Unknown annotation: '{usage.name}'", source_path)
                continue

            declaration = available_annotations[usage.name]
            # Validate the arguments against the parameters
            self._validate_annotation_arguments(usage, declaration, source_path)


# Helper function updated
def validate_asts(loaded_asts: Dict[str, ast.Document]) -> List[ValidationError]:
    validator = Validator()
    return validator.validate(loaded_asts)
