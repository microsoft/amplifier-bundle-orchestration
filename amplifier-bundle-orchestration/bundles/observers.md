---
bundle:
  name: orchestration-observers
  version: 0.1.0
  description: File-watching observer pattern for bottom-up feedback loops

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-issues@main#subdirectory=behaviors/issues.yaml

session:
  orchestrator:
    module: orchestrator-observers
    source: file://../modules/amplifier-module-orchestrator-observers
    config:
      max_iterations: 50
      convergence_threshold: 2
      watch_paths:
        - work/
      observers:
        - name: Quality Reviewer
          role: Reviews work output for quality and completeness
          focus: Look for errors, inconsistencies, unclear sections, missing information, and areas for improvement
        - name: Fact Checker
          role: Verifies claims and checks for accuracy
          focus: Look for unsupported claims, potential inaccuracies, and statements that need citations or verification

agents:
  include:
    - orchestration-observers:observers/agents/observer-config
---

# Observer Pattern Orchestration

@orchestration-observers:observers/context/observers-guide.md

---

## How It Works

This bundle uses a custom orchestrator that implements the observer pattern:

1. **Main Loop**: You interact normally - asking questions, requesting work
2. **Observer Checks**: After each iteration, observers analyze any files in `work/`
3. **Feedback Injection**: Observer feedback is injected as system messages
4. **Convergence**: Process continues until observers have no more feedback

## Active Observers

| Observer | Focus |
|----------|-------|
| Quality Reviewer | Errors, inconsistencies, clarity, completeness |
| Fact Checker | Accuracy, unsupported claims, verification needs |

## Watch Paths

By default, observers watch the `work/` directory. Create files there and observers will review them.

## Configuration

The orchestrator can be configured in the bundle YAML:

```yaml
session:
  orchestrator:
    config:
      max_iterations: 50        # Max main loop iterations
      convergence_threshold: 2  # Iterations without feedback to converge
      watch_paths: [work/]      # Directories to watch
      observers:                # Observer definitions
        - name: "..."
          role: "..."
          focus: "..."
```

---

@foundation:context/shared/common-system-base.md
