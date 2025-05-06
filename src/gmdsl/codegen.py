import importlib
import importlib.metadata
import os
from abc import ABC, abstractmethod
from importlib.metadata import entry_points
from typing import Any, Dict, List, Optional, Type

from gmdsl.ast import (
    AnnotationUsage,
    Document,
)


class CodeGeneratorPlugin(ABC):
    """Abstract base class for code generator plugins."""

    @abstractmethod
    def generate(
        self,
        loaded_asts: Dict[str, Document],
        output_dir: str,
        namespace: Optional[str] = None,
        *args,
        **kwargs,
    ):
        """Generate code from the loaded ASTs."""
        pass

    def get_annotations(self, declaration) -> List[AnnotationUsage]:
        """Get all annotations for a declaration."""
        return getattr(declaration, "annotations", []) or []

    def has_annotation(self, declaration, annotation_name: str) -> bool:
        """Check if a declaration has a specific annotation."""
        for annotation in self.get_annotations(declaration):
            if annotation.name == annotation_name:
                return True
        return False

    def get_annotation(
        self, declaration, annotation_name: str
    ) -> Optional[AnnotationUsage]:
        """Get a specific annotation from a declaration if it exists."""
        for annotation in self.get_annotations(declaration):
            if annotation.name == annotation_name:
                return annotation
        return None

    def get_annotation_arg_value(
        self, annotation: AnnotationUsage, arg_index: int, default: Any = None
    ) -> Any:
        """Get the value of a positional annotation argument or return default if not found."""
        if annotation and annotation.args and len(annotation.args) > arg_index:
            return annotation.args[arg_index].value
        return default

    def get_annotation_named_arg_value(
        self, annotation: AnnotationUsage, arg_name: str, default: Any = None
    ) -> Any:
        """Get the value of a named annotation argument or return default if not found."""
        if annotation and annotation.args:
            for arg in annotation.args:
                # Check if arg has a name attribute and it matches
                if hasattr(arg, "name") and arg.name == arg_name:
                    return arg.value
        return default


# Define the entry point group name
PLUGIN_GROUP = "gmdsl.plugins"

_plugin_cache: Dict[str, Type[CodeGeneratorPlugin]] = {}


def discover_plugins() -> Dict[str, Type[CodeGeneratorPlugin]]:
    """Discovers installed code generator plugins using entry points."""
    global _plugin_cache
    if _plugin_cache:
        return _plugin_cache

    discovered_plugins = {}
    try:
        entry_points = importlib.metadata.entry_points(group=PLUGIN_GROUP)
        for entry_point in entry_points:
            try:
                plugin_class = entry_point.load()
                if issubclass(plugin_class, CodeGeneratorPlugin):
                    # Use entry_point.name as the unique identifier for the plugin
                    discovered_plugins[entry_point.name] = plugin_class
                else:
                    print(
                        f"Warning: Plugin '{entry_point.name}' does not inherit from CodeGeneratorPlugin."
                    )
            except Exception as e:
                print(f"Warning: Failed to load plugin '{entry_point.name}': {e}")
    except Exception as e:
        print(f"Error discovering plugins: {e}")

    _plugin_cache = discovered_plugins
    return discovered_plugins


def run_generation(
    plugin_name: str, loaded_asts: Dict[str, Document], output_dir: str, **kwargs
):
    """
    Finds and runs the specified code generator plugin.

    Args:
        plugin_name: The registered name of the plugin to run.
        loaded_asts: The dictionary of loaded ASTs.
        output_dir: The directory to write generated files to.
        **kwargs: Additional parameters to pass to the plugin's generate method.

    Raises:
        ValueError: If the plugin is not found or fails to instantiate.
        Exception: If the plugin's generate method raises an error.
    """
    plugins = discover_plugins()
    plugin_class = plugins.get(plugin_name)

    if not plugin_class:
        raise ValueError(
            f"Code generator plugin '{plugin_name}' not found. Available: {list(plugins.keys())}"
        )

    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        plugin_instance = plugin_class()
        print(f"Running generator plugin: {plugin_name}...")

        # Pass additional parameters to the generate method if they're supported
        import inspect

        generate_params = inspect.signature(plugin_instance.generate).parameters
        supported_kwargs = {}

        for key, value in kwargs.items():
            if key in generate_params:
                supported_kwargs[key] = value

        plugin_instance.generate(loaded_asts, output_dir, **supported_kwargs)
        print(f"Generator plugin '{plugin_name}' finished.")

    except Exception as e:
        print(f"Error running generator plugin '{plugin_name}': {e}")
        # Re-raise the exception to signal failure
        raise


# Loads all installed code generator plugins
def load_generator_plugins() -> Dict[str, CodeGeneratorPlugin]:
    """
    Load all installed code generator plugins.

    Returns:
        Dict mapping plugin names to plugin instances.
    """
    plugins = {}

    # Load built-in plugins from this package
    for entry_point in entry_points(group="gmdsl.generators"):
        try:
            plugin_class = entry_point.load()
            plugin_name = entry_point.name
            plugins[plugin_name] = plugin_class()
        except Exception as e:
            print(f"Error loading plugin {entry_point.name}: {e}")

    return plugins
