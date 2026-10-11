"""Unit tests for Pillow and PyMuPDF certificate renderers."""

import pytest
from pathlib import Path
from PIL import Image, ImageDraw
import pymupdf as fitz

from src.certapp.core.models import LayoutConfig, LayoutElement, Participant
from src.certapp.core.renderer import PillowRenderer, PyMuPDFRenderer, get_renderer


@pytest.fixture
def sample_png_template(tmp_path):
    img_path = tmp_path / "template.png"
    img = Image.new("RGB", (800, 600), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 780, 580], outline=(0, 51, 102), width=5)
    img.save(img_path)
    return img_path


@pytest.fixture
def sample_pdf_template(tmp_path):
    pdf_path = tmp_path / "template.pdf"
    doc = fitz.open()
    page = doc.new_page(width=800, height=600)
    page.draw_rect(fitz.Rect(20, 20, 780, 580), color=(0, 0.2, 0.4), width=3)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_pillow_renderer_png(sample_png_template, tmp_path):
    config = LayoutConfig(
        background_path=str(sample_png_template),
        output_format="png",
        elements=[
            LayoutElement(name="name", x_frac=0.5, y_frac=0.5, font_size=40, color_hex="#003366")
        ]
    )
    participant = Participant(row_index=1, name="John Alexander Doe", email="john@example.com")
    output_path = tmp_path / "cert_john.png"

    renderer = PillowRenderer()
    out = renderer.render_participant(participant, config, output_path)

    assert Path(out).exists()
    img = Image.open(out)
    assert img.size == (800, 600)


def test_pillow_renderer_pdf(sample_png_template, tmp_path):
    config = LayoutConfig(
        background_path=str(sample_png_template),
        output_format="pdf",
        elements=[
            LayoutElement(name="name", x_frac=0.5, y_frac=0.5, font_size=40, color_hex="#FF0000")
        ]
    )
    participant = Participant(row_index=1, name="Jane Smith", email="jane@example.com")
    output_path = tmp_path / "cert_jane.pdf"

    renderer = PillowRenderer()
    out = renderer.render_participant(participant, config, output_path)

    assert Path(out).exists()
    doc = fitz.open(out)
    assert len(doc) == 1
    doc.close()


def test_pymupdf_renderer_pdf(sample_pdf_template, tmp_path):
    config = LayoutConfig(
        background_path=str(sample_pdf_template),
        output_format="pdf",
        elements=[
            LayoutElement(name="name", x_frac=0.5, y_frac=0.4, font_size=36, color_hex="#0000FF")
        ]
    )
    participant = Participant(row_index=1, name="Vector Participant", email="vector@example.com")
    output_path = tmp_path / "cert_vector.pdf"

    renderer = PyMuPDFRenderer()
    out = renderer.render_participant(participant, config, output_path)

    assert Path(out).exists()
    doc = fitz.open(out)
    page = doc[0]
    text_content = page.get_text()
    assert "Vector Participant" in text_content
    doc.close()
