"""Utility functions for Certificate Automation Application."""

import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional


FORBIDDEN_FILENAME_CHARS = re.compile(r'[/\\:*?"<>|\x00-\x1f]')


def sanitize_filename(name: str, replacement: str = "_", max_length: int = 200) -> str:
    """
    Sanitizes a string to be a safe filename across Windows, macOS, and Linux.

    - Replaces forbidden OS characters: / \\ : * ? " < > | and control characters.
    - Normalizes unicode characters (NFKC).
    - Strips leading/trailing dots and spaces.
    - Truncates to max_length.
    - Returns 'certificate' if input results in empty string.
    """
    if not name:
        return "certificate"

    # Normalize unicode
    cleaned = unicodedata.normalize("NFKC", str(name))

    # Replace forbidden chars with replacement
    cleaned = FORBIDDEN_FILENAME_CHARS.sub(replacement, cleaned)

    # Replace multiple spaces or replacements
    cleaned = re.sub(r'[\s_]+', '_', cleaned)

    # Strip leading/trailing dots, hyphens, underscores, spaces
    cleaned = cleaned.strip(". -_")

    if not cleaned:
        cleaned = "certificate"

    # Limit length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(". -_")

    return cleaned or "certificate"


def get_project_root() -> Path:
    """Returns the root directory of the project."""
    # Assuming utils.py is in src/certapp/core/
    current_file = Path(__file__).resolve()
    # Go up 3 levels: core -> certapp -> src -> root
    root = current_file.parents[3]
    if (root / "pyproject.toml").exists() or (root / "assets").exists():
        return root
    # Fallback to current working directory
    return Path.cwd()


def get_assets_dir() -> Path:
    """Returns assets directory path."""
    return get_project_root() / "assets"


def get_fonts_dir() -> Path:
    """Returns bundled fonts directory path."""
    return get_assets_dir() / "fonts"


def get_sample_dir() -> Path:
    """Returns sample assets directory path."""
    return get_assets_dir() / "sample"


def get_app_dir() -> Path:
    """Returns platform specific user app data directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    
    app_dir = base / "certapp"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def find_system_fonts() -> Dict[str, str]:
    """
    Scans standard system font directories and bundled fonts folder to return a mapping
    of font family/display name -> font file absolute path.
    """
    font_map: Dict[str, str] = {}
    search_dirs: List[Path] = [get_fonts_dir()]

    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", "C:\\Windows")
        search_dirs.append(Path(windir) / "Fonts")
    elif sys.platform == "darwin":
        search_dirs.extend([
            Path("/Library/Fonts"),
            Path("/System/Library/Fonts"),
            Path.home() / "Library/Fonts"
        ])
    else:
        # Linux font paths
        search_dirs.extend([
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            Path.home() / ".local/share/fonts",
            Path.home() / ".fonts"
        ])

    font_extensions = {".ttf", ".otf", ".woff", ".woff2", ".ttc"}

    for s_dir in search_dirs:
        if not s_dir.exists():
            continue
        try:
            for root, _, files in os.walk(s_dir):
                for f in files:
                    ext = Path(f).suffix.lower()
                    if ext in font_extensions:
                        font_path = Path(root) / f
                        # Friendly display name
                        display_name = font_path.stem.replace("-", " ").replace("_", " ")
                        if display_name not in font_map:
                            font_map[display_name] = str(font_path)
        except Exception:
            continue

    return font_map
