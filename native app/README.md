# CertApp - Certificate Automation Desktop Application

A modern desktop application built with Python 3 and PySide6 (Qt) for automated certificate generation and email dispatch.

## Features

- **Multi-Format Data Ingestion**: Load participant lists from `.csv`, `.tsv`, `.xlsx`, or `.xls` files with automatic encoding detection.
- **Smart Header Auto-Detection**: Automatically identifies Name and Email columns using keyword matching with fallback manual remapping dialog.
- **Interactive Visual Editor**: `QGraphicsView` canvas with drag-to-place text placement markers, live sample name preview, zoom, and pan.
- **High-DPI Raster & Vector Engine**:
  - Pillow renderer for PNG/JPG/PDF output with automatic font-size shrinking to fit width limits.
  - PyMuPDF (`fitz`) renderer for vector PDF output.
- **State Persistence & Resume**: Automatic `manifest.csv` tracking to safely resume interrupted batch operations without duplicating effort.
- **Secure Email Dispatch**:
  - Direct integration with OS Keyring (KWallet / SecretService / macOS Keychain / Windows Credential Manager) for secure SMTP credential storage.
  - Email subject and body template formatting with tags (`{name}`, `{email}`).
  - Exponential backoff retries and connection pacing.
  - PDF / PNG attachment embedding.
- **Live Logging Console & Progress Tracking**: Real-time colored event log and progress bars for background operations.

## Project Architecture

```
certapp/
├── main.py                    # Application Entry Point
├── pyproject.toml             # Project Package Metadata & Configuration
├── requirements.txt           # Dependency Requirements
├── assets/
│   ├── fonts/                 # Bundled Open-Source TTF/OTF Fonts
│   └── sample/                # Sample CSV + Sample Certificate Image Template
├── src/certapp/
│   ├── core/                  # Pure Logic Core Engine
│   │   ├── models.py          # Data Dataclasses (Participant, LayoutConfig, etc.)
│   │   ├── sheet_loader.py    # CSV/XLSX Parser & Column Auto-Detection
│   │   ├── layout.py          # Layout Manager & Fractional Coordinates
│   │   ├── renderer.py        # Pillow & PyMuPDF Rendering Engine
│   │   ├── generator.py       # Batch Certificate Generator
│   │   ├── mailer.py          # SMTP Mailer with Retries & Attachment Support
│   │   ├── state_store.py     # ManifestStore CSV Persistence
│   │   ├── settings.py        # SettingsManager & OS Keyring Integration
│   │   └── utils.py           # Filename Sanitization & Path Helpers
│   └── gui/                   # PySide6 Qt GUI Interface
│       ├── main_window.py     # Main Window Desktop Shell
│       ├── workers.py         # QThread Background Generation & Send Workers
│       ├── widgets/           # DropZone, Canvas Preview, Style Panel, Data Table, Log Console
│       └── dialogs/           # SMTP Config, Column Mapping, Confirm Send Modals
└── tests/                     # pytest Suite
```

## Getting Started

### Prerequisites

- Python 3.11+

### Installation

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Or source .venv/bin/activate.fish for Fish shell

# Install dependencies and editable package
pip install -e .
```

### Running the Application

```bash
python3 main.py
```

### Running the Test Suite

```bash
pytest
```
