"""Data models for Certificate Automation Application."""

from dataclasses import dataclass, field, asdict
import json
from typing import List, Dict, Optional, Any
from pathlib import Path


@dataclass
class Participant:
    """Represents a row/participant loaded from sheet data."""
    row_index: int
    name: str
    email: str
    extra_fields: Dict[str, str] = field(default_factory=dict)
    validation_status: str = "valid"  # valid, invalid_email, duplicate, missing_name
    validation_message: str = ""
    certificate_path: Optional[str] = None
    generation_status: str = "pending"  # pending, generated, failed
    send_status: str = "pending"  # pending, sent, failed, skipped
    error_message: Optional[str] = None

    def get_field_value(self, key: str) -> str:
        """Helper to get field value by key (name, email, or extra_fields)."""
        k_lower = key.lower().strip("{} ")
        if k_lower in ("name", "full_name", "fullname"):
            return self.name
        if k_lower in ("email", "mail", "e-mail"):
            return self.email
        # check extra fields case-insensitively
        for ek, ev in self.extra_fields.items():
            if ek.lower().strip() == k_lower:
                return ev
        return ""


@dataclass
class LayoutElement:
    """Represents a text element layout on the certificate."""
    name: str = "name"
    x_frac: float = 0.5
    y_frac: float = 0.5
    font_path: Optional[str] = None
    font_size: int = 40
    min_font_size: int = 16
    max_width_frac: float = 0.8
    color_hex: str = "#000000"
    alignment: str = "center"  # center, left, right
    is_bold: bool = False
    is_italic: bool = False
    template_pattern: str = "{name}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LayoutElement":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LayoutConfig:
    """Represents full layout configuration including text elements and template background."""
    elements: List[LayoutElement] = field(default_factory=list)
    background_path: str = ""
    output_format: str = "pdf"  # "pdf" or "png"
    dpi: int = 300

    def __post_init__(self):
        if not self.elements:
            self.elements = [LayoutElement(name="name", template_pattern="{name}")]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "background_path": self.background_path,
            "output_format": self.output_format,
            "dpi": self.dpi,
            "elements": [elem.to_dict() for elem in self.elements],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LayoutConfig":
        elements_data = data.get("elements", [])
        elements = [LayoutElement.from_dict(e) for e in elements_data]
        return cls(
            background_path=data.get("background_path", ""),
            output_format=data.get("output_format", "pdf"),
            dpi=data.get("dpi", 300),
            elements=elements if elements else [LayoutElement()],
        )

    def save_json(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_json(cls, path: str | Path) -> "LayoutConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class GenerationResult:
    """Result of certificate generation for a single participant."""
    participant: Participant
    success: bool
    output_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SendResult:
    """Result of sending an email to a single participant."""
    participant: Participant
    success: bool
    timestamp: str = ""
    error: Optional[str] = None


@dataclass
class JobProgress:
    """Progress snapshot for batch jobs."""
    total: int = 0
    completed: int = 0
    current_item: str = ""
    status: str = "idle"
    errors: int = 0
