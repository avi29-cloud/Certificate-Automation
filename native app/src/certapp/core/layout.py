"""Layout manager handling coordinate translations and presets."""

from typing import Tuple, Dict, Any
from pathlib import Path
from src.certapp.core.models import LayoutConfig, LayoutElement


class LayoutManager:
    """Manages coordinate mapping and layout configuration."""

    def __init__(self, config: LayoutConfig | None = None):
        self.config = config or LayoutConfig()

    @staticmethod
    def frac_to_pixel(
        x_frac: float, y_frac: float, width: int, height: int
    ) -> Tuple[int, int]:
        """Converts fractional coordinates (0.0 to 1.0) to pixel (x, y)."""
        px = int(round(x_frac * width))
        py = int(round(y_frac * height))
        return px, py

    @staticmethod
    def pixel_to_frac(
        px: int, py: int, width: int, height: int
    ) -> Tuple[float, float]:
        """Converts pixel coordinates (x, y) to fractional coordinates (0.0 to 1.0)."""
        if width <= 0 or height <= 0:
            return 0.5, 0.5
        x_frac = max(0.0, min(1.0, px / float(width)))
        y_frac = max(0.0, min(1.0, py / float(height)))
        return x_frac, y_frac

    @staticmethod
    def calculate_text_anchor(
        x_px: int, text_width: int, alignment: str = "center"
    ) -> int:
        """Calculates left x position based on alignment anchor."""
        align = alignment.lower().strip()
        if align == "center":
            return x_px - (text_width // 2)
        elif align == "right":
            return x_px - text_width
        else:  # left
            return x_px
