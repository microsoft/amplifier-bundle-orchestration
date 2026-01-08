---
bundle:
  name: orchestration-multi-context
  version: 0.1.0
  description: Multi-context workflow orchestrator with phases and parallel tasks

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-issues@main#subdirectory=behaviors/issues.yaml

agents:
  include:
    - orchestration-multi-context:multi-context/agents/workflow-designer
---

# Multi-Context Workflow Orchestration

@orchestration-multi-context:multi-context/context/multi-context-guide.md

---

## Quick Start

This bundle provides documentation and agents for multi-context workflows.
The orchestrator module is available at:
`./modules/amplifier-module-orchestrator-multi-context/`

## Pattern Overview

Complex pipelines with isolated execution contexts:

```
Workflow (YAML)
    |
Phase 1 (parallel) -> Context A, B, C
    |
Phase 2 (sequential) -> Context D -> E
    |
Results
```

**Best for**: Research pipelines, content creation, parallel analysis.

---

@foundation:context/shared/common-system-base.md
