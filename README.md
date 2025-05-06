# gmdsl

A Domain-Specific Language (DSL) for Graph Data Models

## Overview

gmdsl is a DSL and toolchain for defining, validating, and generating code for graph-based data models. It allows you to describe nodes, edges, types, and annotations in a concise, readable format, and then generate code or schema definitions for various platforms such as C# and Neo4j Cypher.

## Features

- **Concise DSL** for modeling graph data structures
- **Namespace and import support** for modular models
- **Validation** of models for correctness and reference integrity
- **Plugin-based code generation** (C#, Cypher, and more)
- **Extensible**: add your own plugins for new targets

## Example DSL Usage

```gmdsl
namespace BrainExpanded.GraphModel
import GM.Core

type Address {
    street: String
    city: String
    state: String
    zipcode: Integer
    country: String
}

type Company {
    name: String
    address: Address
}

type Department {
    name: String
}

node Person {
    firstName: String
    lastName: String
    dateOfBirth: DateTime
    placeOfBirth: Location
}

node Company {
    name: String
    address: Address
}

node Department {
    name: String
}

edge Friend (Person <-> Person) {
    metOn: DateTime
}

edge WorksFor (Person -> Company) {
    role: String
}
```

## Core Types Example (GM.Core.gm)

```gmdsl
namespace GM.Core

type Boolean
type String
type Integer
type Float
type DateTime
type Location {
    longitude: Float
    latitude: Float
}
```

## Plugins

gmdsl supports plugins for code and schema generation. The main plugins included are:

### C# Plugin

- Generates C# classes for your graph model (nodes, types, edges)
- Maps core types (GM.Core.String, GM.Core.Integer, etc.) to .NET types (string, int, etc.)
- Skips generating C# classes for core types that map directly to .NET

### Cypher Plugin

- Generates Neo4j Cypher schema constraints and index suggestions
- Outputs constraints for node properties and relationship properties
- Suggests indexes for common property types

### Debug Plugin

- Outputs a debug representation of the parsed and validated model

## Setting Up GMDSL with [uv](https://github.com/astral-sh/uv)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager and workflow tool. You can use it to set up and manage your GMDSL development environment efficiently.

### 1. Install uv

If you don't have uv installed, you can install it with:

```sh
curl -Ls https://astral.sh/uv/install.sh | sh
```

Or see the [uv installation guide](https://github.com/astral-sh/uv#installation) for more options.

### 2. Install Project Dependencies

From the root of your gmdsl project, run:

```sh
uv pip install -r requirements.txt
```

Or, if you use a `pyproject.toml` (as in this project):

```sh
uv pip install -e .
```

This will install all dependencies in an isolated environment, similar to pip, but much faster.

### 3. Run the CLI

You can now use the `gmdsl` CLI as described above:

```sh
gmdsl generate --plugin csharp --plugin cypher --input examples/MyGraphDataModel.gm --output generated/
```

### 4. Running Tests

To run the test suite with uv:

```sh
uv pip install pytest
pytest
```

---

For more information on uv, see the [uv documentation](https://github.com/astral-sh/uv).

## Getting Started

1. **Write your model** in the DSL (see examples above).
2. **Run the CLI** to validate and generate code:
   ```sh
   gmdsl generate --plugin csharp --plugin cypher --input examples/MyGraphDataModel.gm --output generated/
   ```
3. **Check the generated code** in the `generated/` directory.

## Project Structure

- `src/gmdsl/` — Core source code, parser, validation, plugins
- `examples/` — Example DSL files
- `generated/` — Output directory for generated code and schemas
- `tests/` — Unit tests

## Extending gmdsl

You can add your own plugins by creating a new Python file in `src/gmdsl/plugins/` and registering it in the CLI. Plugins have access to the parsed and validated AST and can generate any output you need.

## License

Apache 2.0 (see [LICENSE](LICENSE) file)
