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
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from . import ast
from .parser import parse_gmdsl


@dataclass
class LoadError:
    message: str
    source_path: Optional[str] = None


class AstLoader:
    """Loads and parses a root GMDsl file and its imports."""

    def __init__(self, include_paths: Optional[List[str]] = None):
        """
        Args:
            include_paths: Optional list of directories to search for imports.
                           The directory of the importing file is always searched first.
        """
        self.loaded_asts: Dict[str, ast.Document] = {}
        self.errors: List[LoadError] = []
        self.processing: Set[str] = set()  # To detect circular imports
        self.include_paths = include_paths or []

    def _resolve_import(
        self, module_name: str, importing_file_path: str
    ) -> Optional[str]:
        """Finds the absolute path for an imported module name."""
        base_dir = os.path.dirname(importing_file_path)
        potential_rel_path = os.path.abspath(
            os.path.join(base_dir, f"{module_name}.gm")
        )

        # 1. Check relative path first
        if os.path.exists(potential_rel_path):
            return potential_rel_path

        # 2. Check include paths
        for include_path in self.include_paths:
            potential_abs_path = os.path.abspath(
                os.path.join(include_path, f"{module_name}.gm")
            )
            if os.path.exists(potential_abs_path):
                return potential_abs_path

        return None  # Not found

    def load(self, root_file_path: str) -> Dict[str, ast.Document]:
        """Loads the root file and all its imports recursively."""
        self.loaded_asts = {}
        self.errors = []
        self.processing = set()
        abs_root_path = os.path.abspath(root_file_path)

        self._load_recursive(abs_root_path)

        if self.errors:
            # Optionally raise an exception or handle errors as needed
            print("Errors encountered during loading:")
            for error in self.errors:
                print(f"- {error.message} (Source: {error.source_path or 'Unknown'})")

        return self.loaded_asts

    def _load_recursive(self, file_path: str):
        """Internal recursive loading function."""
        if file_path in self.loaded_asts:
            return  # Already loaded

        if file_path in self.processing:
            self.errors.append(
                LoadError(f"Circular import detected: {file_path}", file_path)
            )
            return  # Avoid infinite loop

        if not os.path.exists(file_path):
            # This error might be reported by _resolve_import caller, but double-check
            self.errors.append(LoadError(f"File not found: {file_path}", file_path))
            return

        self.processing.add(file_path)

        try:
            with open(file_path, "r") as f:
                content = f.read()
            # TODO: Handle LarkError during parsing
            parsed_ast = parse_gmdsl(content, source_path=file_path)
            self.loaded_asts[file_path] = parsed_ast

            # Process imports
            for imp in parsed_ast.imports:
                resolved_path = self._resolve_import(imp.module_name, file_path)
                if resolved_path:
                    self._load_recursive(resolved_path)
                else:
                    self.errors.append(
                        LoadError(
                            f"Cannot resolve import '{imp.module_name}'",
                            source_path=file_path,
                        )
                    )

        except Exception as e:
            # Catch potential file reading errors or Lark parsing errors
            self.errors.append(LoadError(f"Error processing file: {e}", file_path))
        finally:
            self.processing.remove(file_path)  # Remove from processing set once done
