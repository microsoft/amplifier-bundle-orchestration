# Multi-Context Workflow Guide

The Multi-Context Workflow Orchestrator enables complex pipelines where different tasks execute in separate, isolated contexts, each maintaining its own conversation history.

## Core Concepts

### Execution Context
An isolated environment with its own conversation history. Contexts are named and can be reused across tasks.

### Workflow
A complete pipeline defined in YAML, containing phases and tasks.

### Phase
A collection of tasks that execute together. Phases execute sequentially, but tasks within a phase can be parallel or sequential.

### Task
A single unit of work assigned to a context with a specific prompt and optional profile.

## Architecture

```
Workflow
    |
    +-- Phase 1 (parallel)
    |       +-- Task A (context: research_1)
    |       +-- Task B (context: research_2)
    |       +-- Task C (context: research_3)
    |
    +-- Phase 2 (sequential)
    |       +-- Task D (context: synthesizer)
    |       +-- Task E (context: reviewer)
    |
    +-- Results
```

## Workflow Definition (YAML)

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

## Workflow Structure

### Workflow (top level)
| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Human-readable workflow name |
| `description` | No | Optional description |
| `default_profile` | No | Default profile for tasks without explicit profile |
| `phases` | Yes | List of phases to execute sequentially |
| `config` | No | Optional workflow-wide configuration |

### Phase
| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Human-readable phase name |
| `execution_mode` | No | "sequential" (default) or "parallel" |
| `tasks` | Yes | List of tasks to execute |

### Task
| Field | Required | Description |
|-------|----------|-------------|
| `context_name` | Yes | Name of execution context to use |
| `prompt` | Yes | Task instructions for the agent |
| `profile` | No | Optional profile override |

## Usage

### Basic Usage

```python
from amplifier_orchestrator_multi_context import (
    MultiContextOrchestrator,
    load_workflow
)

# Create orchestrator
orchestrator = MultiContextOrchestrator(
    loader=module_loader,
    mount_plans_dir=Path("./mount_plans"),
    max_context_history=50
)

# Load and execute workflow
workflow = load_workflow("workflow.yaml")
results = await orchestrator.execute_workflow(workflow)

# Check results
print(f"Workflow: {results['workflow_name']}")
print(f"Success: {results['success']}")
print(f"Tasks: {results['successful_tasks']}/{results['total_tasks']}")

# Cleanup
await orchestrator.cleanup()
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

## Best Practices

1. **Use parallel for independent tasks** - Research, data gathering
2. **Use sequential for dependent tasks** - Synthesis, review chains
3. **Name contexts meaningfully** - Reflects their purpose
4. **Match profiles to task types** - Researcher, writer, editor
5. **Keep context history bounded** - Prevents memory growth
6. **Plan phase dependencies** - Later phases can use earlier results

## Common Patterns

### Research -> Synthesis
```yaml
phases:
  - name: "Parallel Research"
    execution_mode: "parallel"
    tasks: [...]  # Multiple research contexts
  
  - name: "Synthesis"
    execution_mode: "sequential"
    tasks:
      - context_name: "synthesizer"
        prompt: "Combine research findings..."
```

### Pipeline with Review
```yaml
phases:
  - name: "Create"
    tasks: [...]
  
  - name: "Review"
    execution_mode: "parallel"
    tasks: [...]  # Multiple reviewers
  
  - name: "Refine"
    tasks:
      - context_name: "refiner"
        prompt: "Address review feedback..."
```
