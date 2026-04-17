---
name: doc-converter
description: Use when reading or converting PDF, DOCX, XLSX, PPTX, DOC, PPT files to Markdown
---

# doc-converter

Convert documents (PDF, DOCX, XLSX, PPTX, DOC, PPT) to high-quality Markdown using the best tool per format.

## When to Use

Use this skill whenever you need to read or understand the contents of a `.pdf`, `.doc`, `.docx`, `.xlsx`, `.ppt`, or `.pptx` file. This includes:

- Reading vendor documents for analysis
- Extracting data from spreadsheets
- Summarizing reports or manuals
- Any task that requires document content

## How to Use

### Step 1: Check for existing conversion

Before converting, check if `{filename}_converted.md` already exists in the same directory as the source file. If it exists and is sufficient, read it directly instead of re-converting.

### Step 2: Convert the document

Run the converter script from the skill directory:

```bash
python3 $SKILL_DIR/convert.py <file_path>
```

For multiple files or a directory:

```bash
python3 $SKILL_DIR/convert.py <file1> <file2> ...
python3 $SKILL_DIR/convert.py <directory>
```

### Step 3 (Optional): Enable vision for image analysis

If the document contains important images (architecture diagrams, screenshots, charts) and the user wants image descriptions:

```bash
python3 $SKILL_DIR/convert.py --vision <file_path>
```

To use Cloud Vision API instead of Gemini:

```bash
python3 $SKILL_DIR/convert.py --vision --vision-engine cloud_vision <file_path>
```

To save images as separate files:

```bash
python3 $SKILL_DIR/convert.py --vision --image-output referenced --images-dir ./images <file_path>
```

### Step 4: Read the output

The converted markdown is saved as `{original_filename}_converted.md` in the same directory as the source file. Read this file to get the document content.

## Format Routing

| Format | Tool | Why |
|--------|------|-----|
| PDF | Docling | Best tables, structure, noise filtering |
| DOCX | Docling | Best heading structure, clean image handling |
| XLSX | MarkItDown | Best sheet identification, newline preservation |
| PPTX | MarkItDown | Better PPTX support than Docling |
| .doc | LibreOffice -> Docling | Converts to .docx first |
| .ppt | LibreOffice -> MarkItDown | Converts to .pptx first |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--vision` | off | Enable vision API for image analysis |
| `--vision-engine` | `gemini` | `gemini` or `cloud_vision` |
| `--image-output` | `inline` | `inline` (text block) or `referenced` (save PNG + link) |
| `--images-dir` | `./images` | Directory for referenced images |
| `--output-dir` | same as source | Output directory |
| `--batch-size` | `15` | Pages per batch for large PDFs |
| `-v` | off | Verbose logging |

## Configuration (for Gemini engine)

Gemini engine config (GCP project, region, model) is managed by the vision skill's `config.json`. On first use of vision, the script will prompt interactively.

## Large PDF Handling

PDFs over 15 pages (configurable via `--batch-size`) are automatically split into batches to prevent timeouts. No user action needed.

## Caching Behavior

If `{filename}_converted.md` already exists and the source file hasn't been modified since, you can skip re-conversion. If you need to re-convert (e.g., with vision enabled), just run the command again — it overwrites the existing output.
