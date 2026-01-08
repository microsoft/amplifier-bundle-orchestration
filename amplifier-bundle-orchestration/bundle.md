---
bundle:
  name: orchestration
  version: 0.1.0
  description: Advanced orchestration patterns for Amplifier - observers, multi-context workflows

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main

# Default orchestrator - the standard loop-streaming from foundation
# Use bundles/observers.md, bundles/conversation-observers.md, or bundles/multi-context.md
# for alternative orchestration patterns

agents:
  include:
    - orchestration:agents/workflow-designer
    - orchestration:agents/observer-config
---

# Orchestration Patterns Bundle

@orchestration:context/instructions.md

---

## Available Orchestration Patterns

This bundle provides access to advanced orchestration patterns:

1. **Observer Pattern** (`bundles/observers.md`) - File-watching observers for bottom-up feedback
2. **Conversation Observer Pattern** (`bundles/conversation-observers.md`) - Conversation-watching observers
3. **Multi-Context Workflow** (`bundles/multi-context.md`) - Complex pipelines with isolated contexts

## Agents Available

- **orchestration:workflow-designer** - Design multi-context workflows
- **orchestration:observer-config** - Configure observer patterns

## Documentation (load on demand)

- Pattern selection: orchestration:context/orchestrator-selection.md
- Observer guide: orchestration:context/observers-guide.md
- Conversation observer guide: orchestration:context/conversation-observers-guide.md
- Multi-context guide: orchestration:context/multi-context-guide.md

---

@foundation:context/shared/common-system-base.md
