# Observer Orchestrator Module

An Amplifier orchestrator module implementing the observer pattern for bottom-up feedback loops.

## Overview

This orchestrator extends the standard agent loop with observer checks:

1. Main loop processes user messages and executes tools
2. After each iteration, observers analyze work output files
3. Observer feedback is injected as system messages
4. Main session addresses feedback in subsequent iterations
5. Process converges when observers have no more feedback

## Installation

```bash
pip install -e .
```

## Usage

In your bundle configuration:

```yaml
session:
  orchestrator:
    module: orchestrator-observers
    source: file://./modules/amplifier-module-orchestrator-observers
    config:
      max_iterations: 50
      convergence_threshold: 2
      watch_paths:
        - work/
      observers:
        - name: Quality Reviewer
          role: Reviews work for quality
          focus: Look for errors and improvements
```

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `max_iterations` | 50 | Maximum main loop iterations (-1 for unlimited) |
| `convergence_threshold` | 2 | Iterations without feedback before converging |
| `watch_paths` | `["work/"]` | Directories/files observers watch |
| `observers` | 1 default | List of observer configurations |

## Observer Configuration

Each observer needs:

- `name`: Display name for the observer
- `role`: One-line description of what the observer does
- `focus`: Detailed guidance on what to look for

## License

MIT
