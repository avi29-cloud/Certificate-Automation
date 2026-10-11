"""Data Ingestion and Validation module for CSV / XLSX files."""

import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
import pandas as pd

from src.certapp.core.models import Participant

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

NAME_KEYWORDS = [
    "full name", "fullname", "name", "participant name", "student name", 
    "first name", "display name", "recipient", "participant", "student"
]

EMAIL_KEYWORDS = [
    "email address", "e-mail address", "email", "e-mail", "mail", 
    "contact email", "user email", "recipient email"
]


def auto_detect_columns(columns: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Auto-detects the Name and Email columns from a list of header strings.
    Returns (name_col, email_col).
    """
    cols_lower = {c.strip().lower(): c for c in columns}

    detected_name: Optional[str] = None
    detected_email: Optional[str] = None

    # Check exact keyword matches first
    for kw in NAME_KEYWORDS:
        if kw in cols_lower:
            detected_name = cols_lower[kw]
            break

    # Substring match if exact match not found
    if not detected_name:
        for kw in NAME_KEYWORDS:
            for col_lower, original_col in cols_lower.items():
                if kw in col_lower:
                    detected_name = original_col
                    break
            if detected_name:
                break

    for kw in EMAIL_KEYWORDS:
        if kw in cols_lower:
            detected_email = cols_lower[kw]
            break

    if not detected_email:
        for kw in EMAIL_KEYWORDS:
            for col_lower, original_col in cols_lower.items():
                if kw in col_lower:
                    detected_email = original_col
                    break
            if detected_email:
                break

    return detected_name, detected_email


def load_dataframe(file_path: Path) -> pd.DataFrame:
    """Reads a CSV or Excel file into a pandas DataFrame with encoding fallbacks."""
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(file_path)
    elif suffix in (".csv", ".tsv", ".txt"):
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        sep = "\t" if suffix == ".tsv" else ","
        
        for enc in encodings:
            try:
                # Try reading with sep auto-detect if standard fails
                df = pd.read_csv(file_path, encoding=enc, sep=sep)
                if len(df.columns) == 1 and "," in str(df.columns[0]):
                    df = pd.read_csv(file_path, encoding=enc, sep=",")
                return df
            except (UnicodeDecodeError, Exception):
                continue
        
        # Fallback to python engine
        return pd.read_csv(file_path, encoding="latin-1", engine="python")
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Supported formats: .csv, .xlsx, .xls, .tsv")


def load_participants_from_file(
    file_path: str | Path,
    name_col: Optional[str] = None,
    email_col: Optional[str] = None,
) -> Tuple[List[Participant], List[str], Dict[str, str]]:
    """
    Parses a CSV or Excel file, validates rows, detects columns, and returns:
    - List of Participant objects
    - List of all raw column names
    - Dict mapping ('name_col', 'email_col') -> detected actual column names
    """
    path = Path(file_path)
    df = load_dataframe(path)

    # Clean column names (strip whitespace)
    df.columns = [str(col).strip() for col in df.columns]
    raw_columns = list(df.columns)

    auto_name, auto_email = auto_detect_columns(raw_columns)

    actual_name_col = name_col if (name_col and name_col in raw_columns) else auto_name
    actual_email_col = email_col if (email_col and email_col in raw_columns) else auto_email

    column_mapping = {
        "name_col": actual_name_col or "",
        "email_col": actual_email_col or "",
    }

    participants: List[Participant] = []
    seen_emails: set = set()

    for idx, row in df.iterrows():
        row_num = idx + 1  # 1-indexed for user readability

        # Extract name
        raw_name = ""
        if actual_name_col and actual_name_col in row and pd.notna(row[actual_name_col]):
            raw_name = str(row[actual_name_col]).strip()

        # Extract email
        raw_email = ""
        if actual_email_col and actual_email_col in row and pd.notna(row[actual_email_col]):
            raw_email = str(row[actual_email_col]).strip().lower()

        # Extra fields dictionary
        extra_fields = {}
        for col in raw_columns:
            if col not in (actual_name_col, actual_email_col):
                val = row[col]
                extra_fields[col] = str(val).strip() if pd.notna(val) else ""

        # Validation logic
        status = "valid"
        msg = ""

        if not raw_name:
            status = "missing_name"
            msg = "Participant name is missing or empty."
        elif not raw_email:
            status = "invalid_email"
            msg = "Email address is missing."
        elif not EMAIL_REGEX.match(raw_email):
            status = "invalid_email"
            msg = f"Invalid email format: '{raw_email}'"
        elif raw_email in seen_emails:
            status = "duplicate"
            msg = f"Duplicate email detected: '{raw_email}'"
        else:
            seen_emails.add(raw_email)

        p = Participant(
            row_index=row_num,
            name=raw_name,
            email=raw_email,
            extra_fields=extra_fields,
            validation_status=status,
            validation_message=msg,
        )
        participants.append(p)

    return participants, raw_columns, column_mapping
