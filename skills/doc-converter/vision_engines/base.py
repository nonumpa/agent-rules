"""VisionEngine type stub for type hints in convert.py.

Actual implementations live in the vision skill (analyze.py).
This module only provides the Protocol for type checking.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class VisionEngine(Protocol):
    """Interface for image analysis engines."""

    def analyze(self, image, context: str = "") -> str: ...

    def analyze_batch(
        self, images: list, contexts: list[str] | None = None
    ) -> list[str]: ...
