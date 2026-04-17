"""
Image analysis via Vertex AI Gemini or Google Cloud Vision.

Two modes:
  - ocr:      Extract text from images, preserve layout
  - describe: Describe image content (diagrams, charts, UI screenshots)

Usage:
    # CLI
    python3 analyze.py image.png                        # default: describe mode
    python3 analyze.py --mode ocr image.png             # OCR mode
    python3 analyze.py --mode describe screenshot.png   # describe mode
    python3 analyze.py image1.png image2.png            # batch
    python3 analyze.py --engine cloud_vision image.png  # use Cloud Vision API
    python3 analyze.py --context "安裝手冊" image.png   # with context hint

    # As module
    from analyze import analyze, analyze_batch, ocr

    text = ocr("screenshot.png")
    desc = analyze("architecture.png")
    desc = analyze("figure.png", context="這是系統架構圖")
    results = analyze_batch(["img1.png", "img2.png"])
"""

from __future__ import annotations

import io
import json
import mimetypes
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SKILL_DIR / "config.json"

_genai = None
_genai_types = None
_vision = None
_config = None


def _load_config() -> dict:
    global _config
    if _config is not None:
        return _config

    if CONFIG_PATH.exists():
        _config = json.loads(CONFIG_PATH.read_text())
        return _config

    print("=" * 60)
    print("  Vision Skill — First-time setup")
    print("=" * 60)
    print()

    gcp_project = input("GCP Project ID: ").strip()
    if not gcp_project:
        sys.exit("Error: GCP Project ID is required.")

    vertex_region = input("Vertex AI region [asia-east1]: ").strip() or "asia-east1"
    default_model = (
        input("Default Gemini model [gemini-2.5-flash]: ").strip() or "gemini-2.5-flash"
    )

    _config = {
        "gcp_project_id": gcp_project,
        "vertex_region": vertex_region,
        "default_model": default_model,
    }
    CONFIG_PATH.write_text(json.dumps(_config, indent=2) + "\n")
    print(f"\nConfig saved to {CONFIG_PATH}")
    print()
    return _config


def _ensure_genai():
    global _genai, _genai_types
    if _genai is None:
        from google import genai
        from google.genai import types as genai_types

        _genai = genai
        _genai_types = genai_types


def _ensure_cloud_vision():
    global _vision
    if _vision is None:
        from google.cloud import vision

        _vision = vision


OCR_PROMPT = "請完整擷取圖片中所有文字，保持原始排版結構，不要加任何說明"

DESCRIBE_PROMPT = (
    "請詳細描述這張圖片的內容。"
    "如果圖片包含文字，請完整擷取所有文字並保持原始排版。"
    "如果是架構圖、流程圖或示意圖，請描述其結構和各元素之間的關係。"
    "如果是表格截圖，請以 Markdown 表格格式重建表格內容。"
    "如果是 UI 截圖，請描述畫面上的主要元素和操作狀態。"
    "不要加上「這是一張...的圖片」等前綴說明，直接輸出內容。"
)

DESCRIBE_WITH_CONTEXT_PROMPT = (
    "以下是一份文件中的圖片，前後文如下：\n\n"
    "---前後文---\n{context}\n---前後文結束---\n\n"
    "請根據前後文脈絡，詳細描述這張圖片的內容。"
    "如果圖片包含文字，請完整擷取所有文字並保持原始排版。"
    "如果是架構圖、流程圖或示意圖，請描述其結構和各元素之間的關係。"
    "如果是表格截圖，請以 Markdown 表格格式重建表格內容。"
    "如果是 UI 截圖，請描述畫面上的主要元素和操作狀態。"
    "不要加上「這是一張...的圖片」等前綴說明，直接輸出內容。"
)

SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
}

_gemini_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        _ensure_genai()
        config = _load_config()
        _gemini_client = _genai.Client(
            project=config["gcp_project_id"],
            location=config["vertex_region"],
            vertexai=True,
            http_options=_genai_types.HttpOptions(api_version="v1"),
        )
    return _gemini_client


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def _load_image_bytes(image_path: str | Path) -> tuple[bytes, str]:
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")
    return path.read_bytes(), _guess_mime(path)


def _pil_to_bytes(pil_image) -> tuple[bytes, str]:
    buf = io.BytesIO()
    fmt = "PNG" if pil_image.mode == "RGBA" else "JPEG"
    pil_image.save(buf, format=fmt)
    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    return buf.getvalue(), mime


# ---------------------------------------------------------------------------
# Gemini engine
# ---------------------------------------------------------------------------


def _gemini_analyze(
    image_bytes: bytes, mime_type: str, prompt: str, model: str | None = None
) -> str:
    _ensure_genai()
    image_part = _genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    client = _get_gemini_client()
    config = _load_config()
    response = client.models.generate_content(
        model=model or config["default_model"],
        contents=[prompt, image_part],
    )
    return response.text


# ---------------------------------------------------------------------------
# Cloud Vision engine
# ---------------------------------------------------------------------------


def _cloud_vision_analyze(image_bytes: bytes) -> str:
    _ensure_cloud_vision()
    image = _vision.Image(content=image_bytes)
    client = _vision.ImageAnnotatorClient()
    response = client.annotate_image(
        {
            "image": image,
            "features": [
                {"type_": _vision.Feature.Type.DOCUMENT_TEXT_DETECTION},
                {"type_": _vision.Feature.Type.LABEL_DETECTION},
            ],
        }
    )
    parts = []
    if response.label_annotations:
        labels = [la.description for la in response.label_annotations[:5]]
        parts.append(f"[{', '.join(labels)}]")
    if response.full_text_annotation and response.full_text_annotation.text:
        parts.append(response.full_text_annotation.text.strip())
    return "\n\n".join(parts) if parts else "[No text or labels detected]"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze(
    image: str | Path | object,
    *,
    mode: str = "describe",
    context: str = "",
    engine: str = "gemini",
    model: str | None = None,
) -> str:
    """Analyze a single image.

    Args:
        image: File path (str/Path) or PIL Image object.
        mode: "ocr" (extract text) or "describe" (describe content).
        context: Optional surrounding text for context-aware description.
        engine: "gemini" (default) or "cloud_vision".
        model: Gemini model override.

    Returns:
        Extracted text or description string.
    """
    if isinstance(image, (str, Path)):
        image_bytes, mime_type = _load_image_bytes(image)
    else:
        image_bytes, mime_type = _pil_to_bytes(image)

    if engine == "cloud_vision":
        return _cloud_vision_analyze(image_bytes)

    if mode == "ocr":
        prompt = OCR_PROMPT
    elif context.strip():
        prompt = DESCRIBE_WITH_CONTEXT_PROMPT.format(context=context[:2000])
    else:
        prompt = DESCRIBE_PROMPT

    return _gemini_analyze(image_bytes, mime_type, prompt, model)


def ocr(image: str | Path | object, *, model: str | None = None) -> str:
    """Shortcut: extract text from image (OCR mode)."""
    return analyze(image, mode="ocr", model=model)


def describe(
    image: str | Path | object, *, context: str = "", model: str | None = None
) -> str:
    """Shortcut: describe image content."""
    return analyze(image, mode="describe", context=context, model=model)


def analyze_batch(
    images: list[str | Path | object],
    *,
    mode: str = "describe",
    context: str = "",
    engine: str = "gemini",
    model: str | None = None,
) -> list[dict[str, str]]:
    """Analyze multiple images. Returns list of {path, text, error}."""
    results = []
    for img in images:
        path_str = str(img) if isinstance(img, (str, Path)) else f"<PIL:{id(img)}>"
        try:
            text = analyze(img, mode=mode, context=context, engine=engine, model=model)
            results.append({"path": path_str, "text": text, "error": ""})
        except Exception as e:
            results.append({"path": path_str, "text": "", "error": str(e)})
    return results


# ---------------------------------------------------------------------------
# Adapter: VisionEngine interface for doc-converter compatibility
# ---------------------------------------------------------------------------


class GeminiVisionEngine:
    """VisionEngine-compatible adapter for doc-converter skill."""

    def __init__(self, model: str | None = None, **kwargs):
        self._model = model

    def analyze(self, image, context: str = "") -> str:
        return describe(image, context=context, model=self._model)

    def analyze_batch(
        self, images: list, contexts: list[str] | None = None
    ) -> list[str]:
        contexts = contexts or [""] * len(images)
        return [self.analyze(img, ctx) for img, ctx in zip(images, contexts)]


class CloudVisionEngine:
    """VisionEngine-compatible adapter for doc-converter skill."""

    def analyze(self, image, context: str = "") -> str:
        return analyze(image, engine="cloud_vision")

    def analyze_batch(
        self, images: list, contexts: list[str] | None = None
    ) -> list[str]:
        return [self.analyze(img) for img in images]


def get_engine(name: str = "gemini", **kwargs):
    """Factory: get a VisionEngine-compatible adapter by name."""
    if name == "gemini":
        return GeminiVisionEngine(**kwargs)
    elif name == "cloud_vision":
        return CloudVisionEngine(**kwargs)
    else:
        raise ValueError(
            f"Unknown engine: {name!r}. Available: 'gemini', 'cloud_vision'"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Image analysis via Vertex AI Gemini / Cloud Vision"
    )
    parser.add_argument("images", nargs="+", help="Image file path(s)")
    parser.add_argument(
        "--mode",
        "-m",
        default="describe",
        choices=["ocr", "describe"],
        help="Analysis mode (default: describe)",
    )
    parser.add_argument(
        "--engine",
        "-e",
        default="gemini",
        choices=["gemini", "cloud_vision"],
        help="Vision engine (default: gemini)",
    )
    parser.add_argument("--model", default=None, help="Gemini model override")
    parser.add_argument(
        "--context", "-c", default="", help="Context hint for better descriptions"
    )
    args = parser.parse_args()

    for img in args.images:
        try:
            text = analyze(
                img,
                mode=args.mode,
                context=args.context,
                engine=args.engine,
                model=args.model,
            )
            if len(args.images) > 1:
                print(f"--- {img} ---")
            print(text)
        except Exception as e:
            print(f"ERROR [{img}]: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
