# agent-rules

Personal AI agent skills.

## Writing Style

This repo uses two writing styles on purpose:

- **Superpowers-style** for behavior-enforcing skills:
  `no-remote-without-approval`, `cite-sources-with-verification`
- **Lighter Anthropic-style** for process and format skills:
  `session-history-logging`, `session-context`
- **Tool-wrapper style** for skills that orchestrate external APIs/CLIs:
  `gdrive`, `image-generation`, `doc-converter`, `vision`

The rule of thumb is simple: use a stricter, more forceful style for skills that prevent risky behavior; use a shorter, calmer structure for skills that define workflow, file layout, or formatting conventions.

## Skills

| Skill | Description |
|-------|-------------|
| **no-remote-without-approval** | Blocks all remote-writing operations (push, PR, review) until explicit user approval |
| **cite-sources-with-verification** | Research tasks must include reference links, each verified as real before presenting |
| **session-history-logging** | Maintains `.history/` in workdir with prompt log and response summaries, updated after every exchange |
| **session-context** | Creates structured context documents in `.history/context/` for cross-session continuity — git-aware staleness detection, parallel session conflict resolution |
| **gdrive** | Google Drive file operations via Drive API v3 — list, download, upload, search, and export files |
| **image-generation** | Generate images from text descriptions using Vertex AI Imagen, with Google Drive upload support |
| **doc-converter** | Convert documents (PDF, DOCX, XLSX, PPTX, DOC, PPT) to high-quality Markdown using the best tool per format |
| **vision** | Analyze images using Vertex AI Gemini or Cloud Vision API — OCR text extraction and content description (diagrams, charts, UI screenshots, tables) |
