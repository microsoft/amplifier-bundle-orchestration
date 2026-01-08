# Orchestration Bundle Instructions

You have access to advanced orchestration patterns beyond the standard loop-streaming orchestrator.

## Available Orchestrators

| Orchestrator | Use Case |
|--------------|----------|
| **orchestrator-observers** | File-watching for bottom-up feedback loops |
| **orchestrator-conversation-observers** | Conversation-watching for real-time feedback |
| **orchestrator-multi-context** | Multi-phase workflows with isolated contexts |

## Agents Available

- **orchestration:workflow-designer** - Design multi-context workflows (YAML definitions)
- **orchestration:observer-config** - Configure observer patterns

## Documentation (load on demand)

- Pattern selection: orchestration:context/orchestrator-selection.md
- Observer guide: orchestration:context/observers-guide.md
- Conversation observer guide: orchestration:context/conversation-observers-guide.md
- Multi-context guide: orchestration:context/multi-context-guide.md

## Example Files

- Workflow examples: orchestration:examples/workflows/
- Observer configs: orchestration:examples/observer-configs/

## When to Recommend Alternative Orchestrators

If the user's task would benefit from:
- **Quality feedback loops** - Suggest using `bundles/observers.md`
- **Parallel research/analysis** - Suggest using `bundles/multi-context.md`
- **Conversation monitoring** - Suggest using `bundles/conversation-observers.md`

## Module Entry Points

| Module | Entry Point | Primary Export |
|--------|-------------|----------------|
| orchestrator-observers | `amplifier_module_orchestrator_observers` | ObserverOrchestrator |
| orchestrator-conversation-observers | `amplifier_module_orchestrator_conversation_observers` | ConversationObserverOrchestrator |
| orchestrator-multi-context | `amplifier_orchestrator_multi_context` | MultiContextOrchestrator |
