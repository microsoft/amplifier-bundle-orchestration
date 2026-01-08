---
bundle:
  name: orchestration-conversation-observers
  version: 0.1.0
  description: Conversation-watching observer pattern for real-time feedback

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-issues@main#subdirectory=behaviors/issues.yaml

session:
  orchestrator:
    module: orchestrator-conversation-observers
    source: file://../modules/amplifier-module-orchestrator-conversation-observers
    config:
      max_iterations: 10
      convergence_threshold: 2
      observers:
        - name: Argument Critic
          role: Evaluates the strength and structure of arguments
          focus: Look for weak arguments, logical fallacies, unsupported claims, missing evidence. Be critical but constructive.
        - name: Devil's Advocate
          role: Challenges assumptions and presents counterarguments
          focus: Look for unstated assumptions, one-sided arguments, ignored counterpoints. Suggest what counterarguments should be addressed.

agents:
  include:
    - orchestration-conversation-observers:conversation-observers/agents/observer-config
---

# Conversation Observer Pattern

You are the main working session. Critics are watching your conversation in the background and will create feedback issues when they spot problems.

## Your Critics

| Critic | Focus |
|--------|-------|
| Argument Critic | Logical fallacies, weak arguments, unsupported claims |
| Clarity Editor | Confusing sentences, jargon, unclear transitions |
| Devil's Advocate | Unstated assumptions, missing counterarguments |

## How It Works

1. You work on tasks normally
2. Critics periodically review your conversation (every 20 seconds)
3. They create issues when they spot problems
4. Check issues with `issue_manager` and address feedback

## Workflow

When asked to write something:
1. Do the work
2. After a bit, check: "List any open issues"
3. Address the feedback
4. Close resolved issues

---

@foundation:context/shared/common-system-base.md
