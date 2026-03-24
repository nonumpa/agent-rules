---
name: session-context
description: Use when ending a session, switching tasks, or when a workstream needs a structured context file in .history/context/ for the next session to resume from
---

# Session Context

## Overview

Create structured context documents that help the next session resume work with the right state, decisions, and next steps.

Context files complement `.history/` logs: history records the exchange, while context captures the current state of the work.

## When to Use

Use this skill when:
- A session is ending after meaningful work
- The user asks to save or write context
- Work is switching to a different task or phase

It is usually unnecessary for pure Q&A or brief exploratory sessions with no durable state.

## File Structure

```text
{workdir}/
  .history/
    context/
      {timestamp}_{topic}-context.md
```

- **Timestamp:** `YYYY-MM-DD_HH-MM`
- **Topic:** short kebab-case slug for the primary task
- **Suffix:** `-context.md`

Examples:
- `2026-03-24_14-30_auth-refactor-context.md`
- `2026-03-24_16-00_fix-webhook-bug-context.md`

## Required Sections

Every context document should include:
- **Goal**
- **Current State**
- **Key Decisions**

Include these additional sections when relevant:
- **Completed Work**
- **Not Yet Done**
- **Failed Approaches**
- **Code Context**
- **Resume Instructions**

## Context Template

```markdown
# Context: {topic}

**Created**: {YYYY-MM-DD HH:MM}
**Branch**: {current git branch, or "no repo"}
**Status**: {In Progress | Complete | Blocked}

## Goal

{One sentence describing the task or outcome.}

## Current State

{What is working, what is incomplete, what is blocked. Include file paths or errors when useful.}

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| {what was decided} | {why it was chosen} |

## Completed Work

- [x] {completed item}

## Not Yet Done

- [ ] {next actionable step}

## Failed Approaches

{Optional notes on approaches that should not be retried without new information.}

## Code Context

{Optional technical details, files, functions, APIs, or constraints that matter for resuming the work.}

## Resume Instructions

1. {first step}
2. {second step}
```

## Writing Guidance

Good context files are:
- Specific about current state
- Actionable for a fresh agent or session
- Honest about uncertainty or blockers
- Concise enough to scan quickly

Avoid:
- Reproducing the full conversation
- Vague status such as "mostly done"
- Large pasted code blocks when a file path would be clearer
- Secrets, tokens, or credentials

## New Session Behavior

At the start of a new session:

1. Check whether `{workdir}/.history/context/` exists
2. List available context files, newest first
3. Review likely candidates before starting work

When presenting a context file, summarize the key fields:
- filename
- status
- goal
- branch, if available

## Staleness Check

If the workdir is a git repository, treat context files as snapshots that may become stale.

Useful checks:

```bash
# Count commits since the context file was written
git log --oneline --since="$CONTEXT_DATE"

# Check whether files mentioned in the context changed
git diff --name-only "$CONTEXT_DATE"..HEAD
```

If there have been relevant changes since the context file was written, load it with a warning and flag the sections most likely to be outdated.

Example presentation:

```markdown
📋 Found context file: `2026-03-24_14-30_auth-refactor-context.md`
- Status: In Progress
- Goal: Implement OAuth2 authentication
- ⚠️ 3 commits since this context was written
- ⚠️ `src/auth/oauth.ts` changed after this context was saved
```

## Parallel Context Files

If multiple context files appear to describe overlapping work, show both and let the user choose how to proceed.

This commonly happens when:
- Files were created within a short time window
- Topics are closely related
- Goals reference the same modules or files

Example presentation:

```markdown
📋 Found 2 related context files:

**[A]** `2026-03-24_14-30_auth-refactor-context.md`
- Status: In Progress
- Goal: Refactor OAuth2 to use httpOnly cookies

**[B]** `2026-03-24_16-00_auth-token-fix-context.md`
- Status: Complete
- Goal: Fix token refresh 500 error

Options:
1. Load [A]
2. Load [B]
3. Load both and reconcile
4. Ignore both and start fresh
```

## Relationship to Session History

| | session-history-logging | session-context |
|---|---|---|
| **Purpose** | Chronological log | State snapshot |
| **When written** | Every exchange | Session end or on demand |
| **Format** | Append-only entries | Structured summary |
| **Location** | `.history/{ts}_{topic}-prompt.md` and summary | `.history/context/{ts}_{topic}-context.md` |

Context files may reference specific `.history/` files when more detail is useful.

## Notes

- Prefer file paths and short explanations over long pasted content
- Use context files to capture what matters for resuming the work
- Keep them current enough to be useful, but concise enough to scan quickly
