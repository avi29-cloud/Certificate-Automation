"""Unit tests for sheet loader and validation."""

import pytest
import pandas as pd
from pathlib import Path
from src.certapp.core.sheet_loader import (
    load_participants_from_file,
    auto_detect_columns,
)


def test_auto_detect_columns():
    cols = ["Student Name", "E-Mail Address", "Course", "Date"]
    name_col, email_col = auto_detect_columns(cols)
    assert name_col == "Student Name"
    assert email_col == "E-Mail Address"


def test_load_participants_csv(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "Full Name,Email,Organization\n"
        "Alice Smith,alice@example.com,TechCorp\n"
        "Bob Jones,bob@invalid-email,EduInc\n"
        ",missing_name@example.com,Org\n"
        "Alice Smith,alice@example.com,TechCorp\n",
        encoding="utf-8"
    )

    participants, cols, mapping = load_participants_from_file(csv_file)
    assert len(participants) == 4
    assert cols == ["Full Name", "Email", "Organization"]
    assert mapping["name_col"] == "Full Name"
    assert mapping["email_col"] == "Email"

    # Row 1: Valid
    assert participants[0].name == "Alice Smith"
    assert participants[0].email == "alice@example.com"
    assert participants[0].validation_status == "valid"

    # Row 2: Invalid Email
    assert participants[1].name == "Bob Jones"
    assert participants[1].validation_status == "invalid_email"

    # Row 3: Missing Name
    assert participants[2].validation_status == "missing_name"

    # Row 4: Duplicate Email
    assert participants[3].validation_status == "duplicate"


def test_load_participants_excel(tmp_path):
    excel_file = tmp_path / "test.xlsx"
    df = pd.DataFrame({
        "Name": ["Charlie Brown", "Diana Prince"],
        "Mail": ["charlie@peanuts.org", "diana@amazon.org"],
        "Role": ["Speaker", "Attendee"]
    })
    df.to_excel(excel_file, index=False)

    participants, cols, mapping = load_participants_from_file(excel_file)
    assert len(participants) == 2
    assert mapping["name_col"] == "Name"
    assert mapping["email_col"] == "Mail"
    assert participants[0].name == "Charlie Brown"
    assert participants[0].extra_fields["Role"] == "Speaker"
