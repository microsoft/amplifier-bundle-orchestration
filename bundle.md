---
bundle:
  name: orchestration
  version: 0.1.0
  description: Event-driven orchestration primitives for multi-session coordination

modules:
  # No modules - this bundle provides Python library code only
  # Consumers import from amplifier_orchestration package
---

# Orchestration Bundle

Event-driven orchestration primitives for Amplifier sessions.

## Overview

This bundle provides infrastructure for:

- **Cross-session communication** via pub/sub events
- **Trigger-based session spawning** (timer, session events, manual)
- **Background session management** for long-running orchestration patterns

## Installation

```bash
uv pip install git+https://github.com/microsoft/amplifier-bundle-orchestration
```

## Components

### EventRouter

Pub/sub event routing between sessions:

```python
from amplifier_orchestration import EventRouter, SessionEvent

router = EventRouter()

# Subscribe to events
async for event in router.subscribe(["work:completed"]):
    print(f"Work done: {event.data}")

# Emit an event
await router.emit("work:completed", {"task_id": "123"}, session_id="abc")

# Wait for a single event with timeout
event = await router.wait_for_event(["session:end"], timeout=60.0)
```

### Triggers

Event sources that can spawn sessions:

```python
from amplifier_orchestration import TimerTrigger, SessionEventTrigger, ManualTrigger

# Timer trigger - fires at intervals
timer = TimerTrigger()
timer.configure({"interval_seconds": 60, "immediate": True})

# Session event trigger - fires on events from EventRouter
session_trigger = SessionEventTrigger(event_router)
session_trigger.configure({"event_names": ["work:completed"]})

# Manual trigger - fires programmatically
manual = ManualTrigger()
await manual.fire({"reason": "user requested"})
```

### BackgroundSessionManager

Manages long-running sessions that respond to triggers:

```python
from amplifier_orchestration import BackgroundSessionManager, BackgroundSessionConfig

manager = BackgroundSessionManager(parent_session, event_router)

# Start a background session
session_id = await manager.start(BackgroundSessionConfig(
    name="periodic-check",
    bundle="tools:health-check",
    triggers=[{"type": "timer", "config": {"interval_seconds": 300}}],
    instruction_template="Run health check: {event_summary}",
))

# Check status
status = manager.get_status()

# Stop when done
await manager.stop(session_id)
```

## Use Cases

### Worker Pools

Spawn worker sessions in response to events:

```python
config = BackgroundSessionConfig(
    name="worker",
    bundle="workers:task-processor",
    triggers=[{"type": "session_event", "config": {"event_names": ["task:queued"]}}],
    pool_size=5,  # Max 5 concurrent workers
)
```

### Periodic Tasks

Run sessions on a schedule:

```python
config = BackgroundSessionConfig(
    name="cleanup",
    bundle="maintenance:cleanup",
    triggers=[{"type": "timer", "config": {"interval_seconds": 3600}}],
)
```

### Event-Driven Orchestration

React to session completion events:

```python
# Parent emits when work is ready
await event_router.emit("work:ready", {"batch_id": "123"})

# Background session triggers on that event and spawns workers
```

## Dependencies

- `amplifier-core` - Kernel session infrastructure
- `amplifier-foundation` - spawn_bundle() primitive
