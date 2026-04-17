---
name: image-generation
description: Use when asked to generate, create, or produce images from text descriptions, or when a task requires AI-generated visuals
---

# Image Generation

Generate images via OpenAI (gpt-image-1) or Google Imagen (Vertex AI), auto-upload to Google Drive.

## Triggers

- "generate an image", "create a picture", "make me an image"
- "draw", "illustrate", "visualize"
- Any task requiring AI-generated images from text prompts

## Prerequisites

- Vertex AI venv: `~/.config/opencode/superpowers/skills/image-generation/.venv/`
- GCP auth: `gcloud auth application-default login`
- OpenAI (optional): `OPENAI_API_KEY` env var
- GDrive skill configured (for auto-upload)

First-time setup:
```bash
python3 -m venv ~/.config/opencode/superpowers/skills/image-generation/.venv
~/.config/opencode/superpowers/skills/image-generation/.venv/bin/pip install google-cloud-aiplatform openai
```

On first run, the script will interactively prompt for **GCP Project ID** and **Google Drive folder ID**, then save them to `config.json` (git-ignored).

## Script

```
~/.config/opencode/superpowers/skills/image-generation/generate_image.py
```

Run with the skill's venv python:
```
~/.config/opencode/superpowers/skills/image-generation/.venv/bin/python
```

## Commands

### Google Imagen (default, Vertex AI)
```bash
VENV=~/.config/opencode/superpowers/skills/image-generation/.venv/bin/python
$VENV ~/.config/opencode/superpowers/skills/image-generation/generate_image.py "a sunset over mountains" -p google
```

### OpenAI
```bash
$VENV ~/.config/opencode/superpowers/skills/image-generation/generate_image.py "a sunset over mountains" -p openai
```

### Both platforms
```bash
$VENV ~/.config/opencode/superpowers/skills/image-generation/generate_image.py "a sunset over mountains" -p both
```

### Skip GDrive upload
```bash
$VENV ~/.config/opencode/superpowers/skills/image-generation/generate_image.py "a sunset" -p google --no-upload
```

### Custom options
```bash
$VENV ~/.config/opencode/superpowers/skills/image-generation/generate_image.py "a sunset" -p google --aspect-ratio 16:9
$VENV ~/.config/opencode/superpowers/skills/image-generation/generate_image.py "a sunset" -p openai --size 1792x1024 --quality hd
```

## Options Quick Reference

| Flag | Values | Default |
|------|--------|---------|
| `-p` | `google`, `openai`, `both` | `google` |
| `-o` | output directory path | `./generated_images` |
| `--no-upload` | flag | uploads by default |
| `--gdrive-folder` | Drive folder ID | from `config.json` |
| `--aspect-ratio` | `1:1`, `3:4`, `4:3`, `16:9`, `9:16` | `1:1` |
| `--size` | `1024x1024`, `1024x1792`, `1792x1024` | `1024x1024` |
| `--quality` | `standard`, `hd` | `standard` |
| `--openai-model` | `gpt-image-1`, etc. | `gpt-image-1` |

## Output

- Local: `./generated_images/{platform}_{YYYY-MM-DD}_{HH-MM-SS}.png`
- GDrive: auto-uploaded with same date-time naming to the configured folder
