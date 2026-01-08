# Amplifier Multi-Context Workflow Orchestrator

A modular orchestration system for executing workflows across multiple isolated execution contexts using Amplifier Core.

## Overview

This module enables complex workflows where different tasks execute in separate contexts, each maintaining its own conversation history. Tasks can be organized into phases that execute either sequentially or in parallel, allowing for sophisticated workflow patterns like parallel research followed by sequential synthesis.

### Key Features

- **Isolated Contexts**: Each context maintains its own conversation history with automatic trimming
- **Flexible Execution**: Phases execute sequentially, tasks within phases can be sequential or parallel
- **YAML Configuration**: Define workflows in simple, readable YAML files
- **Profile Support**: Use different AI profiles for different task types
- **Amplifier Core Integration**: Built on top of Amplifier Core's session management

## Architecture

The module follows the "bricks and studs" philosophy with four independent components:

### 1. ExecutionContext (`context.py`)
Manages isolated conversation history for a single context with automatic trimming.

### 2. Workflow Models (`workflow.py`)
Pydantic models defining the structure of workflows, phases, and tasks.

### 3. Config Loader (`config.py`)
Loads and validates workflow definitions from YAML files.

### 4. MultiContextOrchestrator (`orchestrator.py`)
Main orchestrator that manages contexts and executes workflows through Amplifier Core.

## Installation

```bash
# Install from local directory
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

## Usage

### Basic Example

```python
import asyncio
from amplifier_orchestrator_multi_context import (
    MultiContextOrchestrator,
    load_workflow
)

async def main():
    # Assuming you have an AmplifierSession instance
    from amplifier_core import AmplifierSession

    session = AmplifierSession(
        data_dir="./my_data",
        profile="general-assistant"
    )

    # Create orchestrator
    orchestrator = MultiContextOrchestrator(
        amplifier_session=session,
        max_context_history=50
    )

    # Load and execute workflow
    workflow = load_workflow("workflow.yaml")
    results = await orchestrator.execute_workflow(workflow)

    # Check results
    print(f"Workflow: {results['workflow_name']}")
    print(f"Success: {results['success']}")
    print(f"Tasks: {results['successful_tasks']}/{results['total_tasks']}")

asyncio.run(main())
```

### Workflow Definition (YAML)

```yaml
name: "Content Creation Pipeline"
description: "Research, create, and review content"
default_profile: "general-assistant"

phases:
  # Phase 1: Parallel research
  - name: "Research Phase"
    execution_mode: "parallel"
    tasks:
      - context_name: "market_research"
        profile: "researcher"
        prompt: "Research current trends in AI development tools"

      - context_name: "technical_research"
        profile: "researcher"
        prompt: "Research multi-context orchestration approaches"

  # Phase 2: Sequential creation
  - name: "Content Creation"
    execution_mode: "sequential"
    tasks:
      - context_name: "content_writer"
        profile: "writer"
        prompt: "Draft blog post based on research findings"

      - context_name: "technical_writer"
        profile: "writer"
        prompt: "Create technical documentation with examples"

  # Phase 3: Parallel review
  - name: "Review Phase"
    execution_mode: "parallel"
    tasks:
      - context_name: "content_reviewer"
        profile: "editor"
        prompt: "Review blog post for clarity and engagement"

      - context_name: "technical_reviewer"
        profile: "technical-editor"
        prompt: "Review documentation for accuracy"
```

### Managing Contexts

```python
# Get or create a context
context = orchestrator.get_or_create_context("my_context")

# Access context history
history = context.get_history()
print(f"Context has {len(history)} messages")

# Clear specific context
orchestrator.clear_context("my_context")

# Clear all contexts
orchestrator.clear_all_contexts()
```

## Configuration

### Workflow Structure

**Workflow** (top level):
- `name`: Human-readable workflow name
- `description`: Optional description
- `default_profile`: Default profile for tasks without explicit profile
- `phases`: List of phases to execute sequentially
- `config`: Optional workflow-wide configuration

**Phase**:
- `name`: Human-readable phase name
- `execution_mode`: "sequential" or "parallel"
- `tasks`: List of tasks to execute

**Task**:
- `context_name`: Name of execution context to use
- `prompt`: Task instructions for the agent
- `profile`: Optional profile override

### Context History Management

Each context automatically trims its history when it exceeds `max_context_history` (default: 50 messages). This prevents unbounded memory growth in long-running workflows while preserving recent context.

## Integration with Amplifier Core

The orchestrator integrates with Amplifier Core through the `AmplifierSession` interface:

```python
# The orchestrator calls this method for each task
response = await amplifier_session.run_profile(
    profile=profile_name,
    prompt=task_prompt,
    history=context.get_history()
)
```

**Requirements**:
- `amplifier_session` must have an async `run_profile()` method
- Method should accept `profile`, `prompt`, and `history` parameters
- Method should return a string response

## Design Philosophy

This module follows the project's core principles:

### Ruthless Simplicity
- Minimal abstractions - only what's needed for multi-context workflows
- Direct integration with Amplifier Core
- Simple YAML configuration
- No premature optimization

### Modular Design ("Bricks and Studs")
- Self-contained module with clear boundaries
- Clean public API via `__init__.py`
- Each component (context, workflow, config, orchestrator) is independent
- Can be regenerated from specification without breaking integrations

### MVP Scope

**Included**:
- ✅ Isolated execution contexts with history management
- ✅ Sequential and parallel task execution
- ✅ YAML workflow definitions with validation
- ✅ Profile support for task specialization
- ✅ Basic error handling and logging

**Explicitly Not Included** (future enhancements):
- ❌ Cross-context communication (contexts are isolated)
- ❌ Dynamic workflow modification during execution
- ❌ Workflow persistence and resumption
- ❌ Advanced error recovery strategies
- ❌ Conditional branching or loops in workflows

## Examples

See `tests/fixtures/example_workflow.yaml` for a complete workflow example demonstrating:
- Parallel research phase
- Sequential content creation
- Parallel review phase
- Sequential refinement phase

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
ruff format .

# Lint code
ruff check --fix .
```

## License

MIT License - See LICENSE file for details.

## Contributing

This module is part of the Amplifier ecosystem. Contributions should:
- Follow the "bricks and studs" modular design philosophy
- Maintain ruthless simplicity
- Include tests and documentation
- Stay within the MVP scope or clearly document future enhancements
