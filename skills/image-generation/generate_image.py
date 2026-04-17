#!/usr/bin/env python3
"""
Image generation CLI — supports OpenAI (gpt-image-1) and Google Imagen.
Generated images are automatically uploaded to Google Drive.
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
GDRIVE_SKILL_DIR = SKILL_DIR.parent / "gdrive"
VENV_PYTHON = SKILL_DIR / ".venv" / "bin" / "python"
CONFIG_PATH = SKILL_DIR / "config.json"


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())

    print("=" * 60)
    print("  Image Generation — First-time setup")
    print("=" * 60)
    print()

    gcp_project = input("GCP Project ID (for Vertex AI): ").strip()
    if not gcp_project:
        sys.exit("Error: GCP Project ID is required.")

    gdrive_folder = input("Google Drive folder ID (for auto-upload): ").strip()
    if not gdrive_folder:
        sys.exit("Error: Google Drive folder ID is required.")

    config = {
        "gcp_project_id": gcp_project,
        "gdrive_folder_id": gdrive_folder,
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")
    print(f"\nConfig saved to {CONFIG_PATH}")
    print()
    return config


def _make_filename(prefix: str) -> str:
    return datetime.now().strftime(f"{prefix}_%Y-%m-%d_%H-%M-%S.png")


def upload_to_gdrive(filepath: Path, folder_id: str) -> str | None:
    sys.path.insert(0, str(GDRIVE_SKILL_DIR))
    from gdrive import DriveClient

    client = DriveClient()
    print(f"[GDrive] Uploading {filepath.name}...")
    result = client.upload(filepath, parent_id=folder_id)

    file_id = result.get("id") if isinstance(result, dict) else None
    if not file_id:
        print(f"[GDrive] Upload result: {result}")
        return None

    drive_name = _make_filename(filepath.stem.split("_")[0])
    client._session.patch(
        f"https://www.googleapis.com/drive/v3/files/{file_id}",
        headers={**client._headers(), "Content-Type": "application/json"},
        data=json.dumps({"name": drive_name}),
    )

    url = f"https://drive.google.com/file/d/{file_id}/view"
    print(f"[GDrive] Uploaded → {url}  ({drive_name})")
    return url


def generate_openai(
    prompt: str, output_dir: Path, model: str, size: str, quality: str
) -> Path:
    from openai import OpenAI

    client = OpenAI()  # uses OPENAI_API_KEY env var

    print(f"[OpenAI] Generating with {model}...")
    response = client.images.generate(
        model=model,
        prompt=prompt,
        size=size,
        quality=quality,
        n=1,
        response_format="b64_json",
    )

    image_bytes = base64.b64decode(response.data[0].b64_json)
    filename = output_dir / _make_filename("openai")
    filename.write_bytes(image_bytes)

    revised = getattr(response.data[0], "revised_prompt", None)
    if revised:
        print(f"[OpenAI] Revised prompt: {revised}")

    print(f"[OpenAI] Saved → {filename} ({len(image_bytes):,} bytes)")
    return filename


def generate_google(
    prompt: str,
    output_dir: Path,
    aspect_ratio: str,
    use_vertex: bool,
    project_id: str | None,
) -> Path:

    if use_vertex:
        import vertexai
        from vertexai.preview.vision_models import ImageGenerationModel

        proj = project_id or os.environ.get("GCP_PROJECT_ID")
        if not proj:
            sys.exit("[Google] Error: set GCP_PROJECT_ID env var or pass --gcp-project")

        vertexai.init(project=proj, location="us-central1")
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")

        print("[Google] Generating with Vertex AI imagen-3.0-generate-002...")
        images = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio=aspect_ratio,
            safety_filter_level="block_some",
            person_generation="allow_adult",
        )

        filename = output_dir / _make_filename("google")
        images[0].save(location=str(filename), include_generation_parameters=False)
        byte_count = len(images[0]._image_bytes)

    else:
        import google.generativeai as genai

        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        imagen = genai.ImageGenerationModel("imagen-3.0-generate-001")

        print("[Google] Generating with Gemini API imagen-3.0-generate-001...")
        result = imagen.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio=aspect_ratio,
            safety_filter_level="block_only_high",
            person_generation="allow_adult",
        )

        filename = output_dir / _make_filename("google")
        result.images[0]._pil_image.save(str(filename))
        byte_count = len(result.images[0]._image_bytes)

    print(f"[Google] Saved → {filename} ({byte_count:,} bytes)")
    return filename


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using OpenAI or Google Imagen APIs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("prompt", help="Text description of the image to generate")
    parser.add_argument(
        "-p",
        "--platform",
        choices=["openai", "google", "both"],
        default="google",
        help="Which platform to use (default: google)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="./generated_images",
        help="Output directory (default: ./generated_images)",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip uploading to Google Drive",
    )
    parser.add_argument(
        "--gdrive-folder",
        default=None,
        help="Google Drive folder ID to upload to (default: from config.json)",
    )

    openai_group = parser.add_argument_group("OpenAI options")
    openai_group.add_argument(
        "--openai-model",
        default="gpt-image-1",
        help="OpenAI model (default: gpt-image-1)",
    )
    openai_group.add_argument(
        "--size",
        default="1024x1024",
        choices=["1024x1024", "1024x1792", "1792x1024"],
        help="Image size for OpenAI (default: 1024x1024)",
    )
    openai_group.add_argument(
        "--quality",
        default="standard",
        choices=["standard", "hd"],
        help="Image quality for OpenAI (default: standard)",
    )

    google_group = parser.add_argument_group("Google options")
    google_group.add_argument(
        "--aspect-ratio",
        default="1:1",
        choices=["1:1", "3:4", "4:3", "16:9", "9:16"],
        help="Aspect ratio for Google Imagen (default: 1:1)",
    )
    google_group.add_argument(
        "--vertex",
        action="store_true",
        default=True,
        help="Use Vertex AI SDK instead of Gemini API (requires GCP project)",
    )
    google_group.add_argument(
        "--gcp-project",
        default=None,
        help="GCP project ID for Vertex AI (default: from config.json)",
    )

    args = parser.parse_args()

    config = _load_config()
    if not args.gdrive_folder:
        args.gdrive_folder = config["gdrive_folder_id"]
    if not args.gcp_project:
        args.gcp_project = config["gcp_project_id"]

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f'Prompt: "{args.prompt}"')
    print(f"Output: {output_dir}/")
    print()

    generated: list[Path] = []

    if args.platform in ("openai", "both"):
        try:
            path = generate_openai(
                args.prompt, output_dir, args.openai_model, args.size, args.quality
            )
            generated.append(path)
        except Exception as e:
            print(f"[OpenAI] Error: {e}", file=sys.stderr)

    if args.platform in ("google", "both"):
        try:
            path = generate_google(
                args.prompt,
                output_dir,
                args.aspect_ratio,
                args.vertex,
                args.gcp_project,
            )
            generated.append(path)
        except Exception as e:
            print(f"[Google] Error: {e}", file=sys.stderr)

    if not generated:
        print("\nNo images generated.", file=sys.stderr)
        sys.exit(1)

    if not args.no_upload:
        print()
        for path in generated:
            try:
                upload_to_gdrive(path, args.gdrive_folder)
            except Exception as e:
                print(f"[GDrive] Upload failed for {path.name}: {e}", file=sys.stderr)

    print(f"\nDone — {len(generated)} image(s) generated.")


if __name__ == "__main__":
    main()
