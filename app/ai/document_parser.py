"""Document parser for requirement analysis pipeline.

Supports PDF (PyMuPDF), DOCX (python-docx), and plain text (TXT/MD).
Returns a list of DocumentChunk objects suitable for downstream chunking.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    TXT = "txt"
    MD = "md"

    @classmethod
    def from_filename(cls, filename: str) -> "FileType":
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        try:
            return cls(ext)
        except ValueError:
            raise ValueError(f"Unsupported file type: '.{ext}'")


ALLOWED_EXTENSIONS = {ft.value for ft in FileType}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


@dataclass
class DocumentChunk:
    text: str
    page_no: int | None = None
    section_heading: str | None = None
    source_filename: str = ""

    def __post_init__(self) -> None:
        if not self.text or not self.text.strip():
            raise ValueError("DocumentChunk text must not be empty.")


@dataclass
class ParsedDocument:
    filename: str
    file_type: FileType
    chunks: List[DocumentChunk] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n".join(c.text for c in self.chunks)


def _parse_pdf(content: bytes, filename: str) -> List[DocumentChunk]:
    """Parse PDF bytes using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover
        raise ImportError("PyMuPDF is required for PDF parsing. pip install PyMuPDF") from exc

    chunks: List[DocumentChunk] = []
    with fitz.open(stream=content, filetype="pdf") as doc:
        for page_index, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                chunks.append(
                    DocumentChunk(
                        text=text,
                        page_no=page_index,
                        source_filename=filename,
                    )
                )
    if not chunks:
        raise ValueError(f"No extractable text found in PDF '{filename}'.")
    return chunks


def _parse_docx(content: bytes, filename: str) -> List[DocumentChunk]:
    """Parse DOCX bytes using python-docx."""
    try:
        from docx import Document
        from docx.oxml.ns import qn
    except ImportError as exc:  # pragma: no cover
        raise ImportError("python-docx is required for DOCX parsing. pip install python-docx") from exc

    doc = Document(io.BytesIO(content))
    chunks: List[DocumentChunk] = []
    current_heading: str | None = None
    buffer: list[str] = []

    def _flush(heading: str | None) -> None:
        text = "\n".join(buffer).strip()
        if text:
            chunks.append(
                DocumentChunk(
                    text=text,
                    section_heading=heading,
                    source_filename=filename,
                )
            )
        buffer.clear()

    for para in doc.paragraphs:
        style_name = para.style.name if para.style else ""
        text = para.text.strip()
        if style_name.startswith("Heading"):
            _flush(current_heading)
            current_heading = text or current_heading
        elif text:
            buffer.append(text)

    _flush(current_heading)

    if not chunks:
        raise ValueError(f"No extractable text found in DOCX '{filename}'.")
    return chunks


def _parse_text(content: bytes, filename: str) -> List[DocumentChunk]:
    """Parse plain-text (TXT/MD) bytes."""
    text = content.decode("utf-8", errors="replace").strip()
    if not text:
        raise ValueError(f"No text content found in '{filename}'.")
    # Split on double-newlines to produce natural paragraph chunks
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return [
        DocumentChunk(text=para, page_no=None, source_filename=filename)
        for para in paragraphs
    ]


def parse_document(content: bytes, filename: str) -> ParsedDocument:
    """Entry point: parse document bytes and return a ParsedDocument.

    Args:
        content: Raw file bytes.
        filename: Original filename (used to infer type and for source refs).

    Returns:
        ParsedDocument with a list of DocumentChunk objects.

    Raises:
        ValueError: Unsupported file type, oversized file, or no text extracted.
    """
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File '{filename}' exceeds maximum allowed size of "
            f"{MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )

    file_type = FileType.from_filename(filename)

    if file_type == FileType.PDF:
        chunks = _parse_pdf(content, filename)
    elif file_type in (FileType.DOCX, FileType.DOC):
        chunks = _parse_docx(content, filename)
    elif file_type in (FileType.TXT, FileType.MD):
        chunks = _parse_text(content, filename)
    else:  # pragma: no cover
        raise ValueError(f"Unhandled file type: {file_type}")

    return ParsedDocument(filename=filename, file_type=file_type, chunks=chunks)
