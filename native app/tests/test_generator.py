"""End-to-end integration test for batch certificate generation."""

import pytest
from pathlib import Path
from PIL import Image, ImageDraw

from src.certapp.core.models import LayoutConfig, LayoutElement
from src.certapp.core.sheet_loader import load_participants_from_file
from src.certapp.core.generator import CertificateGenerator
from src.certapp.core.state_store import ManifestStore


def test_batch_generator_end_to_end(tmp_path):
    # 1. Create sample sheet
    sheet_path = tmp_path / "participants.csv"
    sheet_path.write_text(
        "Full Name,Email\n"
        "User Alpha,alpha@example.com\n"
        "User Beta,beta@example.com\n"
        "User Gamma,invalid_email\n",
        encoding="utf-8"
    )

    # 2. Create sample template image
    template_path = tmp_path / "template.png"
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 590, 390], outline=(0, 0, 0), width=2)
    img.save(template_path)

    # 3. Load participants
    participants, cols, mapping = load_participants_from_file(sheet_path)
    assert len(participants) == 3

    # 4. Configure generator
    out_dir = tmp_path / "output"
    config = LayoutConfig(
        background_path=str(template_path),
        output_format="pdf",
        elements=[LayoutElement(name="name", x_frac=0.5, y_frac=0.5)]
    )

    generator = CertificateGenerator(config, out_dir)
    results = generator.generate_batch(participants)

    assert len(results) == 3
    assert results[0].success is True
    assert Path(results[0].output_path).exists()
    assert results[1].success is True
    assert Path(results[1].output_path).exists()
    assert results[2].success is False  # Invalid email skipped

    # 5. Verify manifest store persistence
    manifest = ManifestStore(out_dir)
    assert len(manifest._records) == 3
    assert manifest._records[1]["generation_status"] == "generated"
    assert manifest._records[3]["generation_status"] == "failed"
