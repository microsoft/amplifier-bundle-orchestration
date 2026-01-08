# Amplifier Orchestration Bundle

Advanced orchestration patterns for the Amplifier ecosystem.

## Overview

This bundle provides three orchestration patterns beyond the standard loop-streaming orchestrator:

| Pattern | Description | Best For |
|---------|-------------|----------|
| **Observer** | File-watching for bottom-up feedback | Code review, quality assurance |
| **Conversation Observer** | Conversation-watching for real-time feedback | Conversation quality, coaching |
| **Multi-Context** | Complex pipelines with isolated contexts | Research pipelines, content creation |

## Installation

```bash
# Clone the bundle
git clone https://github.com/payneio/amplifier-bundle-orchestration

# Install module dependencies
pip install -e ./modules/amplifier-module-orchestrator-observers
pip install -e ./modules/amplifier-module-orchestrator-conversation-observers
pip install -e ./modules/amplifier-module-orchestrator-multi-context
```

## Usage

### Default Bundle (adds agents, uses standard orchestrator)

```bash
amplifier run --bundle ./amplifier-bundle-orchestration/bundle.md "Help me design a workflow"
```

### Observer Pattern Bundle

```bash
amplifier run --bundle ./amplifier-bundle-orchestration/bundles/observers.md "Review my code"
```

### Conversation Observer Bundle

```bash
amplifier run --bundle ./amplifier-bundle-orchestration/bundles/conversation-observers.md "Monitor my conversation"
```

### Multi-Context Workflow Bundle

```bash
amplifier run --bundle ./amplifier-bundle-orchestration/bundles/multi-context.md "Run my research pipeline"
```

## Bundle Structure

```
amplifier-bundle-orchestration/
├── bundle.md                          # Main bundle (default orchestrator + agents)
├── bundles/                           # Alternative session configurations
│   ├── observers.md                   # File-watching observer pattern
│   ├── conversation-observers.md      # Conversation-watching pattern
│   └── multi-context.md               # Multi-context workflow pattern
├── behaviors/                         # Reusable behaviors
│   └── orchestration-knowledge.yaml   # Adds docs and agents
├── agents/                            # Orchestration-specific agents
│   ├── workflow-designer.md           # Designs multi-context workflows
│   └── observer-config.md             # Configures observer patterns
├── context/                           # Documentation
│   ├── instructions.md                # Main instructions
│   ├── orchestrator-selection.md      # Pattern selection guide
│   ├── observers-guide.md             # Observer pattern guide
│   ├── conversation-observers-guide.md
│   └── multi-context-guide.md
├── modules/                           # Orchestrator modules
│   ├── amplifier-module-orchestrator-observers/
│   ├── amplifier-module-orchestrator-conversation-observers/
│   └── amplifier-module-orchestrator-multi-context/
├── examples/                          # Example configurations
│   ├── workflows/
│   │   ├── research-pipeline.yaml
│   │   ├── content-creation.yaml
│   │   └── code-review-pipeline.yaml
│   └── observer-configs/
│       ├── code-review-observers.yaml
│       └── quality-observers.yaml
└── README.md
```

## Agents

### workflow-designer

Designs multi-context workflows. Helps with:
- Creating YAML workflow definitions
- Phase planning (sequential vs parallel)
- Context isolation strategy
- Profile mapping

### observer-config

Configures observer patterns. Helps with:
- Defining observer roles and focus areas
- Choosing between file-watching and conversation-watching
- Setting up feedback loops

## Documentation

- [Pattern Selection Guide](context/orchestrator-selection.md)
- [Observer Pattern Guide](context/observers-guide.md)
- [Conversation Observer Guide](context/conversation-observers-guide.md)
- [Multi-Context Guide](context/multi-context-guide.md)

## License

MIT License
