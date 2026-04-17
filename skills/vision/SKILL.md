# vision

Analyze images using Vertex AI Gemini (default) or Google Cloud Vision API.

Two modes: **OCR** (extract text) and **Describe** (understand content — diagrams, charts, UI screenshots, tables).

## When to Use

Use this skill when:

- User asks to analyze, describe, or extract text from an image
- User asks to OCR a screenshot or photo
- User says "幫我分析這張圖片", "解析圖片", "圖片裡面寫什麼"
- Another skill needs to understand image content (e.g., doc-converter uses this for document images)
- You encounter an image file (.png, .jpg, .jpeg, .gif, .bmp, .tiff, .webp) and need to understand its content

## How to Use

### Single image — describe content (default)

```bash
python3 ~/.config/opencode/superpowers/skills/vision/analyze.py image.png
```

### Single image — OCR (extract text only)

```bash
python3 ~/.config/opencode/superpowers/skills/vision/analyze.py --mode ocr screenshot.png
```

### With context hint (for document images)

```bash
python3 ~/.config/opencode/superpowers/skills/vision/analyze.py --context "這是安裝手冊中的架構圖" figure.png
```

### Multiple images

```bash
python3 ~/.config/opencode/superpowers/skills/vision/analyze.py img1.png img2.png img3.png
```

### Use Cloud Vision API instead of Gemini

```bash
python3 ~/.config/opencode/superpowers/skills/vision/analyze.py --engine cloud_vision image.png
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--mode`, `-m` | `describe` | `ocr` (text extraction) or `describe` (content understanding) |
| `--engine`, `-e` | `gemini` | `gemini` (Vertex AI) or `cloud_vision` (Google Cloud Vision) |
| `--model` | `gemini-2.5-flash` | Gemini model override |
| `--context`, `-c` | (empty) | Context hint for better descriptions |

## As a Python Module (for other skills)

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path("~/.config/opencode/superpowers/skills/vision").expanduser()))

from analyze import analyze, ocr, describe, analyze_batch, get_engine

# OCR
text = ocr("screenshot.png")

# Describe
desc = describe("architecture.png")
desc = describe("figure.png", context="系統架構圖")

# Batch
results = analyze_batch(["img1.png", "img2.png"], mode="ocr")

# VisionEngine adapter (for doc-converter compatibility)
engine = get_engine("gemini")
engine.analyze(pil_image, context="...")
```

## Environment Variables

- `GOOGLE_CLOUD_PROJECT` — GCP project ID
- `VERTEX_REGION` — Vertex AI region (default: asia-east1)
- `OCR_MODEL` — Gemini model name (default: gemini-2.5-flash)

## Mode Selection Guide

| Situation | Mode |
|-----------|------|
| Screenshot with text you need to copy | `ocr` |
| Architecture diagram | `describe` |
| Table screenshot | `describe` (rebuilds as Markdown table) |
| UI screenshot | `describe` |
| Handwritten notes | `ocr` |
| Chart / graph | `describe` |
| Photo of whiteboard | `ocr` or `describe` |

## Engine Selection Guide

| Engine | Best For | Cost |
|--------|----------|------|
| **Gemini** (default) | Understanding diagrams, describing architecture, context-aware analysis | ~$0.001/image |
| **Cloud Vision** | Pure text extraction, label detection | Free first 1K/month, then $1.50/1K |
