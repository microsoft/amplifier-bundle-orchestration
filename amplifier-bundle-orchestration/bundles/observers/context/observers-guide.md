# Observer Pattern Guide

The Observer Pattern implements bottom-up feedback loops where specialized observers watch the main session's work and provide feedback through an issue system.

## Core Concepts

### Main Session
The primary session that does actual work (research, coding, writing). It receives tasks from users and can address feedback from observers.

### Observers
Background sessions that continuously monitor output files and create feedback issues when they spot problems in their domain.

### Issue-Based Feedback
Observers communicate through an issue system, creating structured feedback that the main session can query and address.

## How It Works

1. **User sends message** to main session
2. **Main session executes** the task, creating output files
3. **Observers detect changes** in watched files
4. **Observers review** from their specialized perspective
5. **Observers create issues** for problems they find
6. **Main session addresses feedback** when prompted
7. **Process converges** when observers have no more feedback

## Observer Configuration

```python
from amplifier_module_orchestrator_observers import ObserverConfig

observer = ObserverConfig(
    name="skeptic",                    # Observer identity
    config=mount_plan_dict,            # Session configuration
    role="Questions unsupported claims",  # Brief role description
    focus="Look for claims lacking evidence, unsupported assertions, or missing citations"
)
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Observer identity (used in issue attribution) |
| `config` | dict | Mount plan configuration for observer sessions |
| `role` | str | Brief description of observer's focus area |
| `focus` | str | Detailed instructions for what to look for |

## Orchestrator Configuration

```python
orchestrator = ObserverOrchestrator(
    loader=module_loader,
    main_config=main_mount_plan,
    observer_configs=[observer1, observer2],
    workspace_root=Path("./workspace"),
    observer_interval=15.0,    # Seconds between checks
    watch_paths=["work/"],     # Paths to monitor
)
```

## Example Observer Types

### Skeptic
```python
ObserverConfig(
    name="skeptic",
    config=observer_config,
    role="Questions unsupported claims",
    focus="Look for: claims without evidence, unsupported assertions, logical fallacies, missing citations"
)
```

### Clarity Editor
```python
ObserverConfig(
    name="clarity-editor",
    config=observer_config,
    role="Ensures clear, concise writing",
    focus="Look for: confusing passages, unnecessary jargon, redundant content, unclear structure"
)
```

### Security Reviewer
```python
ObserverConfig(
    name="security-reviewer",
    config=observer_config,
    role="Identifies security concerns",
    focus="Look for: hardcoded secrets, injection vulnerabilities, insecure patterns, missing validation"
)
```

## Best Practices

1. **Keep observers focused** - Each observer should have a single, clear domain
2. **Limit issue creation** - Observers create at most 2 issues per review cycle
3. **Avoid duplicates** - Observers check existing issues before creating new ones
4. **Use appropriate intervals** - Balance responsiveness with resource usage
5. **Watch relevant paths** - Only monitor directories where work is created
