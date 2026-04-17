"""Document to Markdown converter."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from vision_engines import get_engine
from vision_engines.base import VisionEngine

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt",
    ".xlsx", ".xls", ".html", ".htm", ".txt", ".md",
    ".csv", ".rtf", ".odt", ".ods", ".odp",
}

FORMAT_ROUTING = {
    "docling": {".pdf", ".docx"},
    "markitdown": {".xlsx", ".pptx", ".txt", ".md", ".csv", ".rtf", ".html", ".htm"},
    "libreoffice_docx": {".doc", ".odt"},
    "libreoffice_pptx": {".ppt", ".odp"},
    "libreoffice_xlsx": {".ods"},
}


class ConversionError(Exception):
    pass


class UnsupportedFormatError(ConversionError):
    pass


@dataclass
class ExtractedImage:
    index: int
    image: object
    page_number: int
    placeholder_pos: int
    context: str = ""


@dataclass
class VisionResult:
    index: int
    description: str
    error: Optional[str] = None


@dataclass
class ConversionStats:
    source_path: Path
    output_path: Path
    images_found: int = 0
    images_processed: int = 0
    pages: int = 0
    tool_used: str = ""
    vision_used: bool = False


@dataclass
class ConversionResult:
    markdown: str
    stats: ConversionStats
    images: list[ExtractedImage] = field(default_factory=list)
    vision_results: list[VisionResult] = field(default_factory=list)


class DocConverter:
    def __init__(
        self,
        vision: bool = False,
        vision_engine: str = "gemini",
        image_output: str = "inline",
        images_dir: Optional[Path] = None,
        page_batch_size: int = 15,
        images_scale: float = 2.0,
        output_dir: Optional[Path] = None,
    ):
        self._vision = vision
        self._vision_engine_name = vision_engine
        self._image_output = image_output
        self._images_dir = images_dir
        self._page_batch_size = page_batch_size
        self._images_scale = images_scale
        self._output_dir = output_dir
        self._engine: Optional[VisionEngine] = None

    def _get_engine(self) -> VisionEngine:
        if self._engine is None:
            self._engine = get_engine(self._vision_engine_name)
        return self._engine

    def convert(self, file_path: Path) -> ConversionResult:
        file_path = Path(file_path).expanduser().resolve()
        if not file_path.exists():
            raise ConversionError(f"File not found: {file_path}")

        suffix = file_path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise UnsupportedFormatError(f"Unsupported format: {suffix}")

        output_path = self._get_output_path(file_path)
        stats = ConversionStats(
            source_path=file_path,
            output_path=output_path,
        )

        if suffix in FORMAT_ROUTING["docling"]:
            result = self._convert_docling(file_path)
            stats.tool_used = "docling"
        elif suffix in FORMAT_ROUTING["markitdown"]:
            result = self._convert_markitdown(file_path)
            stats.tool_used = "markitdown"
        elif suffix in FORMAT_ROUTING["libreoffice_docx"]:
            result = self._convert_via_libreoffice(file_path, "docx")
            stats.tool_used = "libreoffice->docx->docling"
        elif suffix in FORMAT_ROUTING["libreoffice_pptx"]:
            result = self._convert_via_libreoffice(file_path, "pptx")
            stats.tool_used = "libreoffice->pptx->docling"
        elif suffix in FORMAT_ROUTING["libreoffice_xlsx"]:
            result = self._convert_via_libreoffice(file_path, "xlsx")
            stats.tool_used = "libreoffice->xlsx->docling"
        else:
            raise UnsupportedFormatError(f"No routing for: {suffix}")

        markdown, images = result
        stats.images_found = len(images)

        vision_results = []
        if self._vision and images:
            vision_results = self._run_vision(markdown, images)
            markdown = self._merge_vision_results(
                markdown, images, vision_results, file_path.stem
            )
            stats.vision_used = True
            stats.images_processed = sum(1 for r in vision_results if r.error is None)

        stats.output_path = output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")

        return ConversionResult(
            markdown=markdown,
            stats=stats,
            images=images,
            vision_results=vision_results,
        )

    def convert_dir(self, dir_path: Path, recursive: bool = False) -> list[ConversionResult]:
        dir_path = Path(dir_path).expanduser().resolve()
        pattern = "**/*" if recursive else "*"
        results = []
        for p in sorted(dir_path.glob(pattern)):
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                try:
                    results.append(self.convert(p))
                except ConversionError:
                    pass
        return results

    def _get_output_path(self, source: Path) -> Path:
        base = self._output_dir if self._output_dir else source.parent
        return base / f"{source.stem}_converted.md"

    def _convert_docling(self, path: Path) -> tuple[str, list[ExtractedImage]]:
        from docling.document_converter import DocumentConverter
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.datamodel.base_models import InputFormat
        from docling.document_converter import PdfFormatOption
        from docling.models.base_ocr_model import OcrOptions

        suffix = path.suffix.lower()

        if suffix == ".pdf":
            pipeline_opts = PdfPipelineOptions()
            if self._vision:
                pipeline_opts.generate_picture_images = True
                pipeline_opts.images_scale = self._images_scale

            try:
                from pypdf import PdfReader
                reader = PdfReader(str(path))
                page_count = len(reader.pages)
            except Exception:
                page_count = 0

            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts)
                }
            )

            if page_count > self._page_batch_size:
                return self._convert_docling_batched(path, converter, page_count)

            conv_result = converter.convert(str(path))
        else:
            converter = DocumentConverter()
            conv_result = converter.convert(str(path))

        markdown = conv_result.document.export_to_markdown()
        images = self._extract_docling_images(conv_result, markdown, 0, 0)
        return markdown, images

    def _convert_docling_batched(
        self, path: Path, converter, page_count: int
    ) -> tuple[str, list[ExtractedImage]]:
        all_markdown_parts = []
        all_images = []
        image_index_offset = 0
        char_offset = 0

        batch_size = self._page_batch_size
        for start in range(1, page_count + 1, batch_size):
            end = min(start + batch_size - 1, page_count)
            conv_result = converter.convert(str(path), page_range=(start, end))
            part_md = conv_result.document.export_to_markdown()
            images = self._extract_docling_images(
                conv_result, part_md, image_index_offset, start - 1
            )
            for img in images:
                img.placeholder_pos += char_offset
            all_markdown_parts.append(part_md)
            all_images.extend(images)
            image_index_offset += len(images)
            char_offset += len(part_md)

        return "\n\n".join(all_markdown_parts), all_images

    def _extract_docling_images(
        self, conv_result, markdown: str, offset: int, page_offset: int
    ) -> list[ExtractedImage]:
        from docling.datamodel.document import PictureItem

        images = []
        placeholder = "<!-- image -->"
        search_start = 0
        idx = offset

        for element, _level in conv_result.document.iterate_items():
            if not isinstance(element, PictureItem):
                continue

            pil_image = element.get_image(conv_result.document)
            if pil_image is None:
                continue

            pos = markdown.find(placeholder, search_start)
            if pos == -1:
                pos = len(markdown)
            else:
                search_start = pos + len(placeholder)

            page_num = page_offset
            if hasattr(element, "prov") and element.prov:
                try:
                    page_num = element.prov[0].page_no + page_offset
                except (IndexError, AttributeError):
                    pass

            context_start = max(0, pos - 300)
            context_end = min(len(markdown), pos + 300)
            context = markdown[context_start:context_end]

            images.append(ExtractedImage(
                index=idx,
                image=pil_image,
                page_number=page_num,
                placeholder_pos=pos,
                context=context,
            ))
            idx += 1

        return images

    def _convert_markitdown(self, path: Path) -> tuple[str, list[ExtractedImage]]:
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(str(path))
        return result.text_content, []

    def _convert_via_libreoffice(self, path: Path, tool: str) -> tuple[str, list[ExtractedImage]]:
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                "libreoffice", "--headless",
                "--convert-to", tool,
                "--outdir", tmpdir,
                str(path),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode != 0:
                raise ConversionError(
                    f"LibreOffice conversion failed: {proc.stderr}"
                )

            converted = list(Path(tmpdir).glob(f"*.{tool}"))
            if not converted:
                raise ConversionError(
                    f"LibreOffice produced no {tool} output in {tmpdir}"
                )

            # Route based on target format
            converted_ext = converted[0].suffix.lower()
            if converted_ext in FORMAT_ROUTING.get("markitdown", set()):
                return self._convert_markitdown(converted[0])
            else:
                return self._convert_docling(converted[0])

    def _run_vision(
        self, markdown: str, images: list[ExtractedImage]
    ) -> list[VisionResult]:
        engine = self._get_engine()
        pil_images = [img.image for img in images]
        contexts = [img.context for img in images]

        results = []
        for i, (pil_img, ctx) in enumerate(zip(pil_images, contexts)):
            try:
                description = engine.analyze(pil_img, ctx)
                results.append(VisionResult(index=images[i].index, description=description))
            except Exception as e:
                results.append(VisionResult(
                    index=images[i].index,
                    description="",
                    error=str(e),
                ))
        return results

    def _merge_vision_results(
        self,
        markdown: str,
        images: list[ExtractedImage],
        vision_results: list[VisionResult],
        doc_stem: str,
    ) -> str:
        placeholder = "<!-- image -->"
        result_map = {r.index: r for r in vision_results}

        paired = list(zip(images, [result_map.get(img.index) for img in images]))
        paired_sorted = sorted(paired, key=lambda x: x[0].placeholder_pos, reverse=True)

        for img, vr in paired_sorted:
            pos = markdown.find(placeholder)
            if pos == -1:
                continue

            figure_num = img.index + 1

            if vr is None or vr.error:
                replacement = f"<!-- image {figure_num} (vision failed) -->"
            elif self._image_output == "inline":
                desc = vr.description.strip().replace("\n", "\n> ")
                replacement = f"> **[Figure {figure_num}]** {desc}"
            else:
                images_dir = self._images_dir or Path(markdown).parent / f"{doc_stem}_images"
                images_dir.mkdir(parents=True, exist_ok=True)
                img_path = images_dir / f"figure_{figure_num:03d}.png"
                img.image.save(str(img_path), format="PNG")
                rel_path = img_path.name
                desc = vr.description.strip().replace("\n", "\n> ")
                replacement = (
                    f"![Figure {figure_num}]({img_path})\n\n"
                    f"> **[Figure {figure_num}]** {desc}"
                )

            all_occurrences = []
            search = 0
            while True:
                found = markdown.find(placeholder, search)
                if found == -1:
                    break
                all_occurrences.append(found)
                search = found + len(placeholder)

            if all_occurrences:
                target_pos = all_occurrences[-1]
                markdown = markdown[:target_pos] + replacement + markdown[target_pos + len(placeholder):]

        return markdown


def main():
    parser = argparse.ArgumentParser(
        description="Convert documents to Markdown"
    )
    parser.add_argument("input", nargs="+", help="Input file(s) or directory")
    parser.add_argument(
        "--vision", "-V", action="store_true",
        help="Enable vision AI for image analysis"
    )
    parser.add_argument(
        "--vision-engine", default="gemini",
        choices=["gemini", "cloud_vision"],
        help="Vision engine to use (default: gemini)"
    )
    parser.add_argument(
        "--image-output", default="inline",
        choices=["inline", "referenced"],
        help="Image output mode (default: inline)"
    )
    parser.add_argument(
        "--images-dir", type=Path, default=None,
        help="Directory for extracted images (referenced mode)"
    )
    parser.add_argument(
        "--page-batch-size", type=int, default=15,
        help="Pages per batch for large PDFs (default: 15)"
    )
    parser.add_argument(
        "--images-scale", type=float, default=2.0,
        help="Image scale factor for PDF extraction (default: 2.0)"
    )
    parser.add_argument(
        "--output-dir", "-o", type=Path, default=None,
        help="Output directory (default: same as input)"
    )
    parser.add_argument(
        "--recursive", "-r", action="store_true",
        help="Recurse into directories"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    converter = DocConverter(
        vision=args.vision,
        vision_engine=args.vision_engine,
        image_output=args.image_output,
        images_dir=args.images_dir,
        page_batch_size=args.page_batch_size,
        images_scale=args.images_scale,
        output_dir=args.output_dir,
    )

    for input_path_str in args.input:
        input_path = Path(input_path_str).expanduser().resolve()

        if input_path.is_dir():
            results = converter.convert_dir(input_path, recursive=args.recursive)
            for result in results:
                if args.verbose:
                    s = result.stats
                    print(
                        f"✓ {s.source_path.name} → {s.output_path.name} "
                        f"[{s.tool_used}]"
                        + (f" | {s.images_processed}/{s.images_found} images" if s.images_found else "")
                    )
        else:
            try:
                result = converter.convert(input_path)
                if args.verbose:
                    s = result.stats
                    print(
                        f"✓ {s.source_path.name} → {s.output_path.name} "
                        f"[{s.tool_used}]"
                        + (f" | {s.images_processed}/{s.images_found} images" if s.images_found else "")
                    )
                else:
                    print(result.stats.output_path)
            except ConversionError as e:
                print(f"✗ {input_path.name}: {e}", file=sys.stderr)
                sys.exit(1)


if __name__ == "__main__":
    main()
