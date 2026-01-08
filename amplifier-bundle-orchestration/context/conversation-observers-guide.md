# Conversation Observer Pattern Guide

The Conversation Observer Pattern extends the observer concept to watch the main session's conversation transcript rather than output files. This gives observers visibility into the agent's reasoning, tool usage, and responses.

## Core Concepts

### Conversation Watching
Instead of monitoring files, observers read the main session's conversation history, including:
- User messages
- Assistant responses
- Tool calls and results
- Reasoning patterns

### Real-Time Feedback
Observers can provide feedback on the conversation itself, not just final artifacts.

## Key Differences from File-Watching

| Aspect | File-Watching | Conversation-Watching |
|--------|--------------|----------------------|
| What's watched | Output files | Conversation transcript |
| Observer sees | Final artifacts | Reasoning + tool usage |
| Best for | Work product quality | Conversation quality |
| Feedback timing | After work is written | During conversation |

## How It Works

1. **User sends message** to main session
2. **Main session responds**, building conversation history
3. **Observers periodically read** the conversation transcript
4. **Observers analyze** from their specialized perspective
5. **Observers create issues** for problems in the conversation
6. **Main session can address** feedback when prompted
7. **Continuous monitoring** as conversation evolves

## Observer Configuration

```python
from amplifier_module_orchestrator_conversation_observers import ObserverConfig

observer = ObserverConfig(
    name="Logic Checker",
    config=mount_plan_dict,
    role="Identifies logical fallacies and reasoning errors",
    focus="Look for circular reasoning, false premises, unsupported conclusions, contradictions"
)
```

## Orchestrator Configuration

```python
orchestrator = ConversationObserverOrchestrator(
    loader=module_loader,
    main_config=main_mount_plan,
    observer_configs=[observer1, observer2],
    workspace_root=Path("./workspace"),
    observer_interval=15.0,    # Seconds between reviews
)
```

## Example Observer Types

### Logic Checker
```python
ObserverConfig(
    name="Logic Checker",
    config=observer_config,
    role="Identifies logical fallacies and reasoning errors",
    focus="Look for: circular reasoning, false premises, unsupported conclusions, contradictions in responses"
)
```

### Completeness Monitor
```python
ObserverConfig(
    name="Completeness Monitor",
    config=observer_config,
    role="Ensures all user requirements are addressed",
    focus="Track whether all parts of the user's request are being handled, flag missed requirements"
)
```

### Tone Guardian
```python
ObserverConfig(
    name="Tone Guardian",
    config=observer_config,
    role="Monitors conversation tone and professionalism",
    focus="Watch for: inappropriate tone, unprofessional language, lack of empathy, dismissive responses"
)
```

### Tool Usage Auditor
```python
ObserverConfig(
    name="Tool Usage Auditor",
    config=observer_config,
    role="Reviews tool usage patterns",
    focus="Check for: unnecessary tool calls, missed opportunities to use tools, inefficient patterns"
)
```

## Best Practices

1. **Focus on conversation quality** - Different from work product quality
2. **Reference specific exchanges** - Point to exact conversation segments
3. **Consider context** - Observers see the full conversation flow
4. **Don't duplicate file observers** - Use file-watching for artifact quality
5. **Be mindful of privacy** - Observers see full conversation content
