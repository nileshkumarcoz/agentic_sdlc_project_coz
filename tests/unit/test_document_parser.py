"""Unit tests for app/ai/document_parser.py.

PDF and DOCX tests use in-memory fixture generation so they run without
external files and without a live PyMuPDF / python-docx installation being
strictly required in CI (import-skip guards handle missing optional deps).
"""
from __future__ import annotations

import io
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_docx_bytes(paragraphs: list[tuple[str, str]]) -> bytes:
    """Build an in-memory DOCX. Each tuple is (style, text)."""
    from docx import Document

    doc = Document()
    for style, text in paragraphs:
        p = doc.add_paragraph(text)
        p.style = doc.styles[style]
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_pdf_bytes(pages: list[str]) -> bytes:
    """Build an in-memory single-page PDF using fitz."""
    import fitz

    doc = fitz.open()
    for page_text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), page_text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# FileType inference
# ---------------------------------------------------------------------------

class TestFileTypeFromFilename:
    def test_pdf(self):
        from app.ai.document_parser import FileType
        assert FileType.from_filename("spec.pdf") == FileType.PDF

    def test_docx(self):
        from app.ai.document_parser import FileType
        assert FileType.from_filename("BRD.docx") == FileType.DOCX

    def test_md(self):
        from app.ai.document_parser import FileType
        assert FileType.from_filename("README.md") == FileType.MD

    def test_unsupported_raises(self):
        from app.ai.document_parser import FileType
        with pytest.raises(ValueError, match="Unsupported file type"):
            FileType.from_filename("malware.exe")

    def test_no_extension_raises(self):
        from app.ai.document_parser import FileType
        with pytest.raises(ValueError):
            FileType.from_filename("nodotfile")


# ---------------------------------------------------------------------------
# Text / Markdown parsing
# ---------------------------------------------------------------------------

class TestParseText:
    def test_basic_paragraphs(self):
        from app.ai.document_parser import parse_document

        content = b"Hello world\n\nSecond paragraph"
        doc = parse_document(content, "notes.txt")
        assert len(doc.chunks) == 2
        assert doc.chunks[0].text == "Hello world"
        assert doc.chunks[1].text == "Second paragraph"

    def test_source_filename_propagated(self):
        from app.ai.document_parser import parse_document

        doc = parse_document(b"Some text", "reqs.md")
        assert all(c.source_filename == "reqs.md" for c in doc.chunks)

    def test_empty_content_raises(self):
        from app.ai.document_parser import parse_document

        with pytest.raises(ValueError, match="No text content"):
            parse_document(b"   ", "empty.txt")

    def test_full_text_property(self):
        from app.ai.document_parser import parse_document

        doc = parse_document(b"A\n\nB\n\nC", "abc.txt")
        assert "A" in doc.full_text and "C" in doc.full_text


# ---------------------------------------------------------------------------
# File-size guard
# ---------------------------------------------------------------------------

class TestFileSizeGuard:
    def test_oversized_file_raises(self):
        from app.ai.document_parser import parse_document, MAX_FILE_SIZE_BYTES

        oversized = b"x" * (MAX_FILE_SIZE_BYTES + 1)
        with pytest.raises(ValueError, match="exceeds maximum"):
            parse_document(oversized, "big.txt")


# ---------------------------------------------------------------------------
# DOCX parsing
# ---------------------------------------------------------------------------

pytest.importorskip("docx", reason="python-docx not installed")


class TestParseDocx:
    def test_body_paragraphs_extracted(self):
        from app.ai.document_parser import parse_document

        content = _make_docx_bytes([
            ("Normal", "Introduction paragraph."),
            ("Normal", "Another paragraph."),
        ])
        doc = parse_document(content, "spec.docx")
        combined = doc.full_text
        assert "Introduction paragraph." in combined
        assert "Another paragraph." in combined

    def test_heading_becomes_section_heading(self):
        from app.ai.document_parser import parse_document

        content = _make_docx_bytes([
            ("Heading 1", "Functional Requirements"),
            ("Normal", "The system shall allow login."),
        ])
        doc = parse_document(content, "brd.docx")
        assert any(c.section_heading == "Functional Requirements" for c in doc.chunks)

    def test_empty_docx_raises(self):
        from app.ai.document_parser import parse_document
        from docx import Document

        buf = io.BytesIO()
        Document().save(buf)
        with pytest.raises(ValueError, match="No extractable text"):
            parse_document(buf.getvalue(), "empty.docx")


# ---------------------------------------------------------------------------
# PDF parsing
# ---------------------------------------------------------------------------

pytest.importorskip("fitz", reason="PyMuPDF not installed")


class TestParsePdf:
    def test_page_text_extracted(self):
        from app.ai.document_parser import parse_document

        content = _make_pdf_bytes(["Requirements document page one."])
        doc = parse_document(content, "reqs.pdf")
        assert len(doc.chunks) >= 1
        assert "Requirements document page one" in doc.chunks[0].text

    def test_page_numbers_set(self):
        from app.ai.document_parser import parse_document

        content = _make_pdf_bytes(["Page one text.", "Page two text."])
        doc = parse_document(content, "two_pages.pdf")
        page_nos = [c.page_no for c in doc.chunks]
        assert 1 in page_nos
        assert 2 in page_nos
