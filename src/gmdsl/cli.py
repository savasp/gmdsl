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

import click

from .codegen import discover_plugins, run_generation
from .loader import AstLoader
from .validation import validate_asts


@click.group()
def cli():
    """Graph Model DSL (GMDsl) Tool"""
    pass


@cli.command()
@click.argument("root_file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "-I",
    "--include",
    "include_paths",
    multiple=True,
    type=click.Path(exists=True, file_okay=False),
    help="Add directory to search for imported modules.",
)
def validate(root_file: str, include_paths: tuple[str]):
    """Loads and validates a GMDsl file and its imports."""
    click.echo(f"Validating {root_file}...")
    if include_paths:
        click.echo(f"Include paths: {', '.join(include_paths)}")

    loader = AstLoader(include_paths=list(include_paths))
    loaded_asts = loader.load(root_file)

    # Check for loading errors first
    if loader.errors:
        click.secho("Loading Errors:", fg="red", bold=True)
        for error in loader.errors:
            source = error.source_path or "Unknown"
            click.echo(f"- [{source}] {error.message}")
        # Decide if validation should proceed despite loading errors
        # For now, let's stop if there were loading errors
        raise click.Abort()

    click.echo(f"Loaded {len(loaded_asts)} file(s) successfully.")

    # Perform validation
    validation_errors = validate_asts(loaded_asts)

    if validation_errors:
        click.secho("Validation Errors:", fg="red", bold=True)
        for error in validation_errors:
            source = error.source_path or "Entry File"
            click.echo(f"- [{os.path.basename(source)}] {error.message}")
        raise click.Abort()  # Exit with non-zero code on validation errors
    else:
        click.secho("Validation successful!", fg="green")


@cli.command()
@click.argument("root_file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "-I",
    "--include",
    "include_paths",
    multiple=True,
    type=click.Path(exists=True, file_okay=False),
    help="Add directory to search for imported modules.",
)
@click.option(
    "-o",
    "--output",
    "output_dir",
    required=True,
    type=click.Path(file_okay=False),
    help="Directory to write generated output files.",
)
@click.option(
    "-g",
    "--generator",
    "generator_name",
    required=True,
    help="Name of the code generator plugin to use.",
)
@click.option(
    "--skip-validation",
    is_flag=True,
    default=False,
    help="Skip the validation step before generation.",
)
@click.option(
    "--namespace",
    "namespace",
    type=str,
    default=None,
    help="Custom namespace to use for C# generation (only used with csharp generator).",
)
@click.option(
    "--generate-incoming",
    is_flag=True,
    default=False,
    help="Generate properties for incoming relationships in C# classes (only used with csharp generator).",
)
def generate(
    root_file: str,
    include_paths: tuple[str],
    output_dir: str,
    generator_name: str,
    skip_validation: bool,
    namespace: str,
    generate_incoming: bool,
):
    """Loads, validates (optional), and generates code using a plugin."""
    click.echo(f"Processing {root_file} for generator '{generator_name}'...")
    if include_paths:
        click.echo(f"Include paths: {', '.join(include_paths)}")

    # --- Loading ---
    loader = AstLoader(include_paths=list(include_paths))
    loaded_asts = loader.load(root_file)

    if loader.errors:
        click.secho("Loading Errors:", fg="red", bold=True)
        for error in loader.errors:
            source = error.source_path or "Unknown"
            click.echo(f"- [{source}] {error.message}")
        raise click.Abort()

    click.echo(f"Loaded {len(loaded_asts)} file(s) successfully.")

    # --- Validation (Optional) ---
    if not skip_validation:
        click.echo("Running validation...")
        validation_errors = validate_asts(loaded_asts)
        if validation_errors:
            click.secho("Validation Errors:", fg="red", bold=True)
            for error in validation_errors:
                source = error.source_path or "Entry File"
                click.echo(f"- [{os.path.basename(source)}] {error.message}")
            click.echo(
                "Validation failed. Aborting generation. Use --skip-validation to override."
            )
            raise click.Abort()
        else:
            click.secho("Validation successful.", fg="green")
    else:
        click.echo("Skipping validation step.")

    # --- Generation ---
    try:
        click.echo(f"Generating code into {output_dir}...")

        # Special handling for generators that accept additional parameters
        if generator_name == "csharp":
            kwargs = {}
            if namespace:
                click.echo(f"Using custom namespace: {namespace}")
                kwargs["namespace"] = namespace

            if generate_incoming:
                click.echo("Generating incoming relationship properties")
                kwargs["generate_incoming"] = True

            run_generation(generator_name, loaded_asts, output_dir, **kwargs)
        else:
            run_generation(generator_name, loaded_asts, output_dir)

        click.secho("Code generation completed successfully!", fg="green")
    except ValueError as e:
        # Specific error for plugin not found
        click.secho(f"Generation Error: {e}", fg="red", bold=True)
        # Suggest available plugins
        available_plugins = list(discover_plugins().keys())
        if available_plugins:
            click.echo(f"Available generators: {', '.join(available_plugins)}")
        else:
            click.echo("No generators found. Have you installed any plugins?")
        raise click.Abort()
    except Exception as e:
        # General errors during generation
        click.secho(f"Generation Error: {e}", fg="red", bold=True)
        # Consider adding traceback logging here for debugging
        raise click.Abort()


# Entry point for the script execution (e.g., python -m gmdsl.cli validate ...)
if __name__ == "__main__":
    cli()


# Main function for the console script entry point defined in pyproject.toml
def main():
    cli()
