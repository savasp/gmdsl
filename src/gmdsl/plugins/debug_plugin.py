import os
from typing import Dict
from gmdsl.codegen import CodeGeneratorPlugin
from gmdsl.ast import Document, NodeDeclaration, TypeDeclaration

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
                name = f"{current_namespace}.{decl.name}" if current_namespace else decl.name
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
