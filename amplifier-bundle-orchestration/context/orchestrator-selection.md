# Orchestration Pattern Selection Guide

## Available Patterns

### 1. Observer Pattern (`orchestrator-observers`)

**Use when:**
- You need bottom-up feedback on work products
- Multiple quality perspectives should review output
- Work should iterate until quality converges

**Architecture:**
```
Main Session -> Creates work -> Observers watch files
     ^                              |
     +-------- Feedback issues -----+
```

**Example use cases:**
- Code review with multiple reviewers (security, style, performance)
- Document creation with editorial feedback
- Research with fact-checking observers

### 2. Conversation Observer Pattern (`orchestrator-conversation-observers`)

**Use when:**
- Observers need to see the agent's reasoning, not just output
- Real-time monitoring of conversation quality
- Coaching or guidance during conversation

**Architecture:**
```
Main Session -> Conversation history -> Observers read
     ^                                      |
     +-------- Feedback issues -------------+
```

**Example use cases:**
- Conversation quality monitoring
- Real-time coaching for complex tasks
- Compliance monitoring

### 3. Multi-Context Workflow (`orchestrator-multi-context`)

**Use when:**
- Complex pipelines with distinct phases
- Parallel research or analysis tasks
- Different profiles for different task types

**Architecture:**
```
Workflow Definition (YAML)
    |
Phase 1 (parallel) -> Context A, Context B, Context C
    |
Phase 2 (sequential) -> Context D -> Context E
    |
Results aggregation
```

**Example use cases:**
- Research pipeline (parallel gather -> sequential synthesis)
- Content creation (research -> write -> review)
- Multi-perspective analysis

## Decision Matrix

| Need | Pattern |
|------|---------|
| Quality feedback on files | observer |
| Feedback on reasoning | conversation-observer |
| Complex multi-step pipeline | multi-context |
| Parallel independent tasks | multi-context |
| Iterative convergence | observer |
| Real-time coaching | conversation-observer |

## Comparison Table

| Feature | Observer | Conversation Observer | Multi-Context |
|---------|----------|----------------------|---------------|
| What's watched | Files | Conversation | N/A (workflow-driven) |
| Feedback mechanism | Issues | Issues | Phase results |
| Parallel execution | Observers run parallel | Observers run parallel | Tasks can be parallel |
| Context isolation | Main + observers | Main + observers | Multiple isolated contexts |
| Best for | Quality gates | Conversation quality | Complex pipelines |
