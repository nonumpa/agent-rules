---
name: session-history-logging
description: Use at the start of a work session or when continuing one that should keep durable prompt and summary logs in .history/
---

# Session History Logging

## Overview

Maintain two markdown files in `.history/` under the working directory so each session has a durable local record.

Use the prompt file for exact user messages and the summary file for concise summaries of the agent's responses.

## When to Use

This skill applies for any session that should preserve a portable record of the exchange.

Typical triggers:
- Starting a new session
- Continuing a multi-step task
- Working in a repo or directory where `.history/` is expected

## File Structure

```text
{workdir}/
  .history/
    {timestamp}_{topic}-prompt.md
    {timestamp}_{topic}-summary.md
```

- **Timestamp:** `YYYY-MM-DD_HH-MM` (24-hour local time)
- **Topic:** short kebab-case slug from the first user prompt, 2-4 words when possible

Examples:
- `2026-03-24_14-30_review-asana-pr-prompt.md`
- `2026-03-24_14-30_review-asana-pr-summary.md`
- `2026-03-24_15-45_create-agent-skills-prompt.md`

If a session starts in the same minute with the same topic, append a counter such as `-2`.

## Topic Derivation

Derive the topic from the first user prompt in the session:

1. Identify the main action and subject
2. Ignore filler words and system directives
3. Convert to kebab-case
4. Keep it short but still distinguishable from other sessions

Examples:

| First Prompt | Topic Slug |
|---|---|
| "幫我 review https://github.com/.../pull/4" | `review-asana-pr` |
| "Fix the login bug in auth.ts" | `fix-login-bug` |
| "建一個新的 skill" | `create-new-skill` |
| "What's the best way to handle caching?" | `caching-strategy` |

If the first prompt is too vague, use a temporary slug such as `session`.

## Session Start

On the first user message of a session:

1. Create `.history/` if it does not exist
2. Determine the timestamp
3. Derive the topic slug
4. Create both files with headers
5. Record the first prompt and first response summary

### Initial Templates

**Prompt file**

```markdown
# Prompt History — {YYYY-MM-DD HH:MM} — {topic}

## [1] {HH:MM}

{exact user prompt, verbatim}
```

**Summary file**

```markdown
# Response Summary — {YYYY-MM-DD HH:MM} — {topic}

## [1] {HH:MM}

{2-3 sentence summary of what the agent did or answered}
```

## After Each Exchange

Before ending each turn:

1. Append the latest user prompt to the prompt file
2. Append a short summary of the agent response to the summary file

### Append Format

**Prompt file**

```markdown

## [{N}] {HH:MM}

{exact user prompt, verbatim}
```

**Summary file**

```markdown

## [{N}] {HH:MM}

{2-3 sentence summary: what the agent did, key decisions, outputs}
```

## Silent Operation

History logging should run silently in the background.

- Do not print `.history/` contents to the terminal
- Do not announce each append operation unless the user asks
- Treat `.history/` updates as bookkeeping rather than user-facing output
- Mention history files only when debugging them, verifying them, or when the user asks where they are

## Summary Guidance

Good summaries usually include:
- What action was taken
- Important findings or decisions
- Concrete outputs such as files, URLs, or commands when relevant

Examples:

```markdown
## [3] 15:22

Reviewed PR #4 on nics-tw/asana-ai-bot. Identified 6 critical issues,
including broken webhook auth and a missing /health endpoint.
Recommended request-changes with a prioritized fix order.

## [4] 15:35

Created `no-remote-without-approval` skill.
The rule blocks remote Git and GitHub writes until explicit approval.
```

Avoid summaries that are too vague or that paste the full response.

## Edge Cases

- **Long user prompt:** still record it verbatim
- **Complex response:** summarize the outcome, not every intermediate step
- **Long session:** keep appending to the same pair of files
- **Multiple agents:** include agent identity in the summary when helpful, for example `**[Prometheus]** ...`

## Notes

- `.history/` is the durable record of the session
- `.history/` should be added to the repository's `.gitignore` to avoid committing session logs
- Keep the files structured and easy to scan
- If session logging is already in place, continue using the same file pair for the session
