# agent-rules

Personal AI agent skills.

## Writing Style

This repo uses two writing styles on purpose:

- **Superpowers-style** for behavior-enforcing skills:
  `no-remote-without-approval`, `cite-sources-with-verification`
- **Lighter Anthropic-style** for process and format skills:
  `session-history-logging`, `session-context`

The rule of thumb is simple: use a stricter, more forceful style for skills that prevent risky behavior; use a shorter, calmer structure for skills that define workflow, file layout, or formatting conventions.

## Skills

| Skill | Description |
|-------|-------------|
| **no-remote-without-approval** | Blocks all remote-writing operations (push, PR, review) until explicit user approval |
| **cite-sources-with-verification** | Research tasks must include reference links, each verified as real before presenting |
| **session-history-logging** | Maintains `.history/` in workdir with prompt log and response summaries, updated after every exchange |
| **session-context** | Creates structured context documents in `.history/context/` for cross-session continuity — git-aware staleness detection, parallel session conflict resolution |
