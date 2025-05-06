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
from typing import Dict

from gmdsl.ast import Document, NodeDeclaration, TypeDeclaration
from gmdsl.codegen import CodeGeneratorPlugin


class DebugGenerator(CodeGeneratorPlugin):
    """A simple plugin that prints discovered types and nodes."""

    def generate(self, loaded_asts: Dict[str, Document], output_dir: str):
        print(f"DebugGenerator running. Output directory (ignored): {output_dir}")
        print("Found files:")
        for path in loaded_asts.keys():
            print(f"  - {path}")

        all_types = []
        all_nodes = []

        for doc_path, doc in loaded_asts.items():
            current_namespace = str(doc.namespace.name) if doc.namespace else ""
            for decl in doc.declarations:
                name = (
                    f"{current_namespace}.{decl.name}"
                    if current_namespace
                    else decl.name
                )
                if isinstance(decl, TypeDeclaration):
                    all_types.append(name)
                elif isinstance(decl, NodeDeclaration):
                    all_nodes.append(name)

        print("\nDiscovered Types:")
        if all_types:
            for t in sorted(all_types):
                print(f"  - {t}")
        else:
            print("  (None)")

        print("\nDiscovered Nodes:")
        if all_nodes:
            for n in sorted(all_nodes):
                print(f"  - {n}")
        else:
            print("  (None)")
