# agent-rules

Personal AI agent skills.

## Skills

| Skill | Description |
|-------|-------------|
| **no-remote-without-approval** | Blocks all remote-writing operations (push, PR, review) until explicit user approval |
| **cite-sources-with-verification** | Research tasks must include reference links, each verified as real before presenting |
| **session-history-logging** | Maintains `.history/` in workdir with prompt log and response summaries, updated after every exchange |
| **session-context** | Creates structured context documents in `.history/context/` for cross-session continuity — git-aware staleness detection, parallel session conflict resolution |
