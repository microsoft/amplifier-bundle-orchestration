# Amplifier Orchestration Bundle

Event-driven orchestration primitives for multi-session coordination in the Amplifier ecosystem.

## Overview

This bundle provides infrastructure for:

| Component | Purpose |
|-----------|---------|
| **EventRouter** | Cross-session pub/sub communication |
| **Triggers** | Timer, session event, and manual trigger sources |
| **BackgroundSessionManager** | Long-running sessions that respond to triggers |

## Installation

```bash
uv pip install git+https://github.com/microsoft/amplifier-bundle-orchestration
```

## Quick Start

### Event Routing

```python
from amplifier_orchestration import EventRouter

router = EventRouter()

# Subscribe to events
async for event in router.subscribe(["work:completed"]):
    print(f"Work done by {event.source_session_id}: {event.data}")

# Emit an event
await router.emit("work:completed", {"task_id": "123"}, source_session_id="worker-1")

# Wait for a single event with timeout
event = await router.wait_for_event(["session:end"], timeout=60.0)
```

### Triggers

```python
from amplifier_orchestration import TimerTrigger, SessionEventTrigger, ManualTrigger

# Timer trigger - fires at intervals
timer = TimerTrigger()
timer.configure({"interval_seconds": 60, "immediate": True})
async for event in timer.watch():
    print(f"Timer fired: {event.data}")

# Session event trigger - fires on events from EventRouter
session_trigger = SessionEventTrigger(event_router)
session_trigger.configure({"event_names": ["work:completed"]})

# Manual trigger - fires programmatically
manual = ManualTrigger()
await manual.fire({"reason": "user requested"})
```

### Background Session Manager

```python
from amplifier_orchestration import BackgroundSessionManager, BackgroundSessionConfig

manager = BackgroundSessionManager(parent_session, event_router)

# Start a background session that runs periodically
session_id = await manager.start(BackgroundSessionConfig(
    name="periodic-check",
    bundle="tools:health-check",
    triggers=[{"type": "timer", "config": {"interval_seconds": 300}}],
    instruction_template="Run health check: {event_summary}",
    pool_size=1,  # Max concurrent instances
))

# Check status
status = manager.get_status()
print(f"Running: {status['running']}, Total triggers: {status['sessions'][session_id]['trigger_count']}")

# Stop when done
await manager.stop(session_id)
```

## Use Cases

### Worker Pools

Spawn worker sessions in response to queued tasks:

```python
config = BackgroundSessionConfig(
    name="worker",
    bundle="workers:task-processor",
    triggers=[{"type": "session_event", "config": {"event_names": ["task:queued"]}}],
    pool_size=5,  # Max 5 concurrent workers
    instruction_template="Process task: {event_data}",
)
```

### Periodic Tasks

Run maintenance sessions on a schedule:

```python
config = BackgroundSessionConfig(
    name="cleanup",
    bundle="maintenance:cleanup",
    triggers=[{"type": "timer", "config": {"interval_seconds": 3600}}],
)
```

### Event-Driven Pipelines

Chain sessions together via events:

```python
# Stage 1 emits when complete
await event_router.emit("stage1:complete", {"output": result})

# Stage 2 triggers on stage 1 completion
stage2_config = BackgroundSessionConfig(
    name="stage2",
    bundle="pipeline:stage2",
    triggers=[{"type": "session_event", "config": {"event_names": ["stage1:complete"]}}],
)
```

## API Reference

### EventRouter

| Method | Description |
|--------|-------------|
| `emit(name, data, source_session_id)` | Emit an event to all subscribers |
| `subscribe(event_names, source_sessions, queue_size)` | Subscribe to events (async iterator) |
| `wait_for_event(event_names, source_sessions, timeout)` | Wait for a single event |
| `create_session_emitter(session_id)` | Create a bound emitter for a session |

### TriggerSource Protocol

| Method | Description |
|--------|-------------|
| `configure(config)` | Configure the trigger from a dict |
| `watch()` | Async iterator yielding TriggerEvent objects |
| `stop()` | Stop watching for events |

### BackgroundSessionManager

| Method | Description |
|--------|-------------|
| `start(config)` | Start a background session, returns session_id |
| `stop(session_id)` | Stop a specific background session |
| `stop_all()` | Stop all background sessions |
| `get_status(session_id=None)` | Get status of one or all sessions |
| `fire_manual(session_id, data)` | Programmatically trigger a session |

## Dependencies

- `amplifier-core` - Kernel session infrastructure
- `amplifier-foundation` - `spawn_bundle()` primitive for session spawning

## License

MIT License
