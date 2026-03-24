---
name: session-history-logging
description: Use at the start of every session and after every user message - requires maintaining .history/ directory in workdir with prompt history and response summary markdown files, updated incrementally throughout the session
---

# Session History Logging

## Overview

Every session must maintain two markdown files in `.history/` under the working directory, updated after every exchange.

**Core principle:** Record every prompt. Summarize every response. Never lose history.

## The Iron Law

```
EVERY SESSION GETS HISTORY FILES
EVERY EXCHANGE GETS RECORDED IMMEDIATELY
```

## When This Applies

**Always.** This skill activates at the start of every session, for every agent.

## File Structure

```
{workdir}/
  .history/
    {timestamp}_{topic}-prompt.md      # User's prompts only
    {timestamp}_{topic}-summary.md     # Agent response summaries
```

**Timestamp format:** `YYYY-MM-DD_HH-MM` (24h, local time)
**Topic:** A short slug (2-4 words, kebab-case) derived from the first user prompt.

Examples:
- `2026-03-24_14-30_review-asana-pr-prompt.md`
- `2026-03-24_14-30_review-asana-pr-summary.md`
- `2026-03-24_15-45_create-agent-skills-prompt.md`

**If a session starts at the same minute with the same topic**, append a counter: `2026-03-24_14-30_review-pr-2-prompt.md`

### Topic Derivation Rules

Extract the topic from the user's **first prompt** in the session:

1. Identify the core action and subject (ignore filler words, system directives)
2. Convert to kebab-case, 2-4 words max
3. Be specific enough to distinguish from other sessions

| First Prompt | Topic Slug |
|---|---|
| "幫我 review https://github.com/.../pull/4" | `review-asana-pr` |
| "Fix the login bug in auth.ts" | `fix-login-bug` |
| "建一個新的 skill" | `create-new-skill` |
| "What's the best way to handle caching?" | `caching-strategy` |
| "Refactor the payment module" | `refactor-payment` |

**If the first prompt is ambiguous or too vague**, use a generic slug like `session` and update the filename when intent becomes clear.

## Session Start (First Message)

**On receiving the FIRST user message in a session:**

1. Create `.history/` directory if it doesn't exist
2. Determine timestamp from current time
3. Derive topic slug from the first prompt
4. Create both files with headers
5. Record the first prompt and first response summary

### Initial File Templates

**Prompt file** (`{timestamp}_{topic}-prompt.md`):
```markdown
# Prompt History — {YYYY-MM-DD HH:MM} — {topic}

## [1] {HH:MM}

{exact user prompt, verbatim}
```

**Summary file** (`{timestamp}_{topic}-summary.md`):
```markdown
# Response Summary — {YYYY-MM-DD HH:MM} — {topic}

## [1] {HH:MM}

{2-3 sentence summary of what the agent did/answered}
```

## After Every Exchange

**After EVERY agent response, BEFORE ending the turn:**

1. Append the user's prompt to the prompt file
2. Append a summary of the agent's response to the summary file

### Silent Operation

History logging should run **silently in the background**.

- Do **not** print history file contents to the terminal
- Do **not** announce each append operation unless the user explicitly asks
- Treat `.history/` updates as bookkeeping, not user-facing output
- Mention history logging only when debugging it, verifying it, or when the user asks where the files are

### Append Format

**Prompt file** — append:
```markdown

## [{N}] {HH:MM}

{exact user prompt, verbatim}
```

**Summary file** — append:
```markdown

## [{N}] {HH:MM}

{2-3 sentence summary: what the agent did, key decisions made, outputs produced}
```

## Summary Writing Guidelines

**Good summaries:**
- What action was taken (created file, reviewed PR, fixed bug)
- Key decisions or findings
- Outputs produced (file paths, URLs, commands run)

**Examples:**
```markdown
## [3] 15:22

Reviewed PR #4 on nics-tw/asana-ai-bot. Identified 6 critical issues
including broken webhook auth and missing /health endpoint.
Recommended request-changes with prioritized fix order.

## [4] 15:35

Created `no-remote-without-approval` skill at
~/.config/opencode/superpowers/skills/no-remote-without-approval/SKILL.md.
Rule blocks all remote git/GitHub write operations until explicit user approval.
```

**Bad summaries:**
- ❌ "Answered the user's question" (too vague)
- ❌ Copy-pasting the full response (that's not a summary)
- ❌ "Did what was asked" (zero information)

## Red Flags - STOP

- About to end a turn without updating history files
- Session started but no `.history/` directory created yet
- Multiple exchanges passed without recording
- Thinking "I'll update history at the end"
- Thinking "this exchange is too trivial to log"

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "I'll write it all at the end" | Session may crash. Write immediately. |
| "This exchange is trivial" | All prompts get recorded. No exceptions. |
| "History files slow me down" | 10 seconds of writing prevents total loss. |
| "The user can check chat history" | Chat history isn't structured or portable. |
| "I forgot at the start, I'll skip this session" | Create files NOW, backfill what you can. |

## Edge Cases

**User's prompt is very long (>50 lines):**
- Still record verbatim. The prompt file is a complete log.

**Agent response is complex (multi-step, many outputs):**
- Summary is still 2-3 sentences. Focus on outcomes, not process.

**Session continues across many exchanges:**
- Keep appending. One session = one pair of files, no matter the length.

**Multiple agents in same session:**
- Each agent notes its identity in summary: "**[Prometheus]** Created work plan for..."

## The Bottom Line

**If the session disappears, the history files remain.**

Create on first message. Update after every exchange. No exceptions.
