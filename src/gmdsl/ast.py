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

from dataclasses import dataclass, field
from typing import Any, List, Optional, Union


# Base class for all AST nodes (optional, but can be useful)
@dataclass(frozen=True)
class ASTNode:
    pass


# Represents an annotation parameter in an annotation declaration
@dataclass(frozen=True)
class AnnotationParameter(ASTNode):
    name: str  # Parameter names are local to the annotation, so they remain strings
    type_name: "QualifiedName"  # Always qualified


# Represents an annotation argument in an annotation usage
@dataclass(frozen=True)
class AnnotationArgument(ASTNode):
    value: Any  # Can be string, identifier, or number


# Represents an annotation usage (@SomeName(arg1, arg2))
@dataclass(frozen=True)
class AnnotationUsage(ASTNode):
    name: "QualifiedName"  # Always qualified
    args: List[AnnotationArgument] = field(default_factory=list)


# Represents an annotation declaration
@dataclass(frozen=True)
class AnnotationDeclaration(ASTNode):
    name: "QualifiedName"  # Always qualified
    parameters: List[AnnotationParameter] = field(default_factory=list)


# Represents a property declaration (e.g., firstName: String)
@dataclass(frozen=True)
class PropertyDeclaration(ASTNode):
    name: str  # Property names are local to their container, so they remain strings
    type_name: "QualifiedName"  # Always qualified
    annotations: List[AnnotationUsage] = field(default_factory=list)


# Represents a qualified name (e.g., gm.CoreTypes)
@dataclass(frozen=True)
class QualifiedName(ASTNode):
    parts: List[str]

    def __str__(self):
        return ".".join(self.parts)

    @classmethod
    def from_str(cls, name: str) -> "QualifiedName":
        """Create a QualifiedName from a string representation."""
        if not name:
            return cls(parts=[])
        return cls(parts=name.split("."))

    @property
    def simple_name(self) -> str:
        """Return just the last part of the qualified name."""
        return self.parts[-1] if self.parts else ""


# Represents a namespace declaration
@dataclass(frozen=True)
class NamespaceDeclaration(ASTNode):
    name: QualifiedName


# Represents an import declaration
@dataclass(frozen=True)
class ImportDeclaration(ASTNode):
    module_name: QualifiedName  # Always qualified


# Represents a type declaration (simple or complex)
@dataclass(frozen=True)
class TypeDeclaration(ASTNode):
    name: QualifiedName  # Always qualified
    properties: List[PropertyDeclaration] = field(default_factory=list)
    annotations: List[AnnotationUsage] = field(default_factory=list)


# Represents a node declaration
@dataclass(frozen=True)
class NodeDeclaration(ASTNode):
    name: QualifiedName  # Always qualified
    properties: List[PropertyDeclaration] = field(default_factory=list)
    annotations: List[AnnotationUsage] = field(default_factory=list)


# Represents an edge declaration
@dataclass(frozen=True)
class EdgeDeclaration(ASTNode):
    name: QualifiedName  # Always qualified
    source_node: QualifiedName  # Always qualified
    target_node: QualifiedName  # Always qualified
    direction: str  # "->" or "<->"
    properties: List[PropertyDeclaration] = field(default_factory=list)
    annotations: List[AnnotationUsage] = field(default_factory=list)


# Represents the entire document/module
@dataclass(frozen=True)
class Document(ASTNode):
    source_path: Optional[str] = None  # Store the file path it was loaded from
    namespace: Optional[NamespaceDeclaration] = None
    imports: List[ImportDeclaration] = field(default_factory=list)
    declarations: List[
        Union[TypeDeclaration, NodeDeclaration, EdgeDeclaration, AnnotationDeclaration]
    ] = field(default_factory=list)
