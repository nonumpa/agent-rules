"""Vision engine registry — delegates to the vision skill (single source of truth)."""

from __future__ import annotations

import sys
from pathlib import Path

# Import from vision skill
_vision_skill_dir = str(Path("~/.config/opencode/superpowers/skills/vision").expanduser())
if _vision_skill_dir not in sys.path:
    sys.path.insert(0, _vision_skill_dir)

from analyze import get_engine, GeminiVisionEngine, CloudVisionEngine  # noqa: E402, F401

__all__ = ["get_engine", "GeminiVisionEngine", "CloudVisionEngine"]
