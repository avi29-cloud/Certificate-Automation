"""Tests for filename sanitization and utilities."""

import pytest
from src.certapp.core.utils import sanitize_filename, get_project_root
from src.certapp.core.models import Participant, LayoutConfig, LayoutElement


def test_sanitize_filename_basic():
    assert sanitize_filename("John Doe") == "John_Doe"
    assert sanitize_filename("  Jane   Smith  ") == "Jane_Smith"


def test_sanitize_filename_special_chars():
    dirty = 'John / Doe : test * ? " < > | file'
    clean = sanitize_filename(dirty)
    for forbidden in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        assert forbidden not in clean


def test_sanitize_filename_empty():
    assert sanitize_filename("") == "certificate"
    assert sanitize_filename("   ...  ") == "certificate"


def test_sanitize_filename_length_limit():
    long_name = "A" * 300
    clean = sanitize_filename(long_name, max_length=50)
    assert len(clean) == 50


def test_participant_model():
    p = Participant(
        row_index=1,
        name="Alice Johnson",
        email="alice@example.com",
        extra_fields={"Event": "Hackathon 2026", "Role": "Speaker"}
    )
    assert p.get_field_value("name") == "Alice Johnson"
    assert p.get_field_value("email") == "alice@example.com"
    assert p.get_field_value("Event") == "Hackathon 2026"
    assert p.get_field_value("nonexistent") == ""


def test_layout_config_serialization(tmp_path):
    config = LayoutConfig(
        background_path="template.png",
        output_format="pdf",
        elements=[
            LayoutElement(name="name", font_size=50, color_hex="#FF0000"),
            LayoutElement(name="Event", font_size=30, color_hex="#00FF00")
        ]
    )
    json_file = tmp_path / "layout.json"
    config.save_json(json_file)

    loaded = LayoutConfig.load_json(json_file)
    assert loaded.background_path == "template.png"
    assert loaded.output_format == "pdf"
    assert len(loaded.elements) == 2
    assert loaded.elements[0].font_size == 50
    assert loaded.elements[1].color_hex == "#00FF00"
