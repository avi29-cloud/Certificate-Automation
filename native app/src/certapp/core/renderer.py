"""Rendering engine for raster (Pillow) and vector (PyMuPDF) certificate output."""

import os
from pathlib import Path
from typing import Tuple, List, Dict, Optional, Any
from PIL import Image, ImageDraw, ImageFont, ImageColor
import pymupdf as fitz

from src.certapp.core.models import LayoutConfig, LayoutElement, Participant
from src.certapp.core.layout import LayoutManager
from src.certapp.core.utils import find_system_fonts, get_fonts_dir


class RendererError(Exception):
    """Exception raised for errors during certificate rendering."""
    pass


class BaseRenderer:
    """Base interface for certificate renderers."""

    def render_participant(
        self,
        participant: Participant,
        config: LayoutConfig,
        output_path: str | Path
    ) -> str:
        raise NotImplementedError()


class PillowRenderer(BaseRenderer):
    """Raster & High-DPI certificate renderer using Pillow."""

    def __init__(self):
        self._font_cache: Dict[Tuple[str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}
        self._system_fonts = find_system_fonts()

    def _resolve_font_path(self, font_path_setting: Optional[str]) -> Optional[str]:
        if not font_path_setting:
            return None

        # Check exact path
        p = Path(font_path_setting)
        if p.is_file():
            return str(p)

        # Check in bundled fonts
        bundled = get_fonts_dir() / font_path_setting
        if bundled.is_file():
            return str(bundled)

        # Check in system fonts map
        if font_path_setting in self._system_fonts:
            return self._system_fonts[font_path_setting]

        for k, v in self._system_fonts.items():
            if font_path_setting.lower() in k.lower():
                return v

        return None

    def _get_font(self, font_path_setting: Optional[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        key = (font_path_setting or "default", size)
        if key in self._font_cache:
            return self._font_cache[key]

        font_path = self._resolve_font_path(font_path_setting)
        font = None

        if font_path:
            try:
                font = ImageFont.truetype(font_path, size)
            except Exception:
                font = None

        if font is None:
            # Try bundled font fallback
            bundled_fonts = list(get_fonts_dir().glob("*.ttf")) + list(get_fonts_dir().glob("*.otf"))
            if bundled_fonts:
                try:
                    font = ImageFont.truetype(str(bundled_fonts[0]), size)
                except Exception:
                    font = None

        if font is None:
            # Default Pillow font
            font = ImageFont.load_default()

        self._font_cache[key] = font
        return font

    def _calculate_auto_shrink_font(
        self,
        text: str,
        element: LayoutElement,
        canvas_width: int,
        draw: ImageDraw.ImageDraw
    ) -> Tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, Tuple[int, int]]:
        max_allowed_width = int(canvas_width * element.max_width_frac)
        current_size = element.font_size
        min_size = max(8, element.min_font_size)

        while current_size >= min_size:
            font = self._get_font(element.font_path, current_size)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            if text_w <= max_allowed_width or current_size == min_size:
                return font, (text_w, text_h)

            current_size -= 2

        font = self._get_font(element.font_path, min_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        return font, (bbox[2] - bbox[0], bbox[3] - bbox[1])

    def render_participant(
        self,
        participant: Participant,
        config: LayoutConfig,
        output_path: str | Path
    ) -> str:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        bg_path = Path(config.background_path)
        if not bg_path.exists():
            raise RendererError(f"Background template not found: {config.background_path}")

        # Load background image
        if bg_path.suffix.lower() == ".pdf":
            doc = fitz.open(bg_path)
            if len(doc) == 0:
                raise RendererError("PDF background is empty.")
            page = doc[0]
            pix = page.get_pixmap(dpi=config.dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
        else:
            img = Image.open(bg_path).convert("RGB")

        width, height = img.size
        draw = ImageDraw.Draw(img)

        # Render each layout element
        for elem in config.elements:
            text = elem.template_pattern.format(
                name=participant.name,
                email=participant.email,
                **participant.extra_fields
            )
            if not text.strip():
                continue

            font, (text_w, text_h) = self._calculate_auto_shrink_font(text, elem, width, draw)
            px, py = LayoutManager.frac_to_pixel(elem.x_frac, elem.y_frac, width, height)

            # Alignment anchor x
            x = LayoutManager.calculate_text_anchor(px, text_w, elem.alignment)
            # Center y on anchor point
            y = py - (text_h // 2)

            # Parse color
            try:
                rgb_color = ImageColor.getrgb(elem.color_hex)
            except Exception:
                rgb_color = (0, 0, 0)

            draw.text((x, y), text, fill=rgb_color, font=font)

        # Save output
        out_ext = output_path.suffix.lower()
        if out_ext == ".pdf":
            img.save(output_path, "PDF", resolution=config.dpi)
        else:
            img.save(output_path, "PNG", dpi=(config.dpi, config.dpi))

        return str(output_path)


class PyMuPDFRenderer(BaseRenderer):
    """Vector PDF certificate renderer using PyMuPDF (fitz)."""

    def render_participant(
        self,
        participant: Participant,
        config: LayoutConfig,
        output_path: str | Path
    ) -> str:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        bg_path = Path(config.background_path)
        if not bg_path.exists():
            raise RendererError(f"Background template not found: {config.background_path}")

        # If background is not a PDF, fallback to Pillow renderer for raster export or conversion
        if bg_path.suffix.lower() != ".pdf":
            pillow_renderer = PillowRenderer()
            return pillow_renderer.render_participant(participant, config, output_path)

        doc = fitz.open(bg_path)
        page = doc[0]
        page_rect = page.rect
        width, height = page_rect.width, page_rect.height

        for elem in config.elements:
            text = elem.template_pattern.format(
                name=participant.name,
                email=participant.email,
                **participant.extra_fields
            )
            if not text.strip():
                continue

            px, py = LayoutManager.frac_to_pixel(elem.x_frac, elem.y_frac, int(width), int(height))
            max_w = width * elem.max_width_frac

            # Determine color in float RGB (0.0 - 1.0)
            try:
                rgb = ImageColor.getrgb(elem.color_hex)
                color_vec = (rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
            except Exception:
                color_vec = (0.0, 0.0, 0.0)

            # Auto shrink font size calculation
            fontsize = float(elem.font_size)
            min_fontsize = float(elem.min_font_size)
            
            # Estimate text width (fitz text length)
            fontname = "helv"  # Standard built-in font fallback
            while fontsize >= min_fontsize:
                text_len = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)
                if text_len <= max_w or fontsize <= min_fontsize:
                    break
                fontsize -= 1.0

            text_len = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)
            x = LayoutManager.calculate_text_anchor(px, int(text_len), elem.alignment)

            # Insert vector text
            point = fitz.Point(x, py + (fontsize / 3.0))
            page.insert_text(
                point,
                text,
                fontsize=fontsize,
                fontname=fontname,
                color=color_vec
            )

        doc.save(str(output_path))
        doc.close()
        return str(output_path)


def get_renderer(background_path: str | Path, output_format: str = "pdf") -> BaseRenderer:
    """Factory function to get appropriate renderer."""
    bg_p = Path(background_path)
    if bg_p.suffix.lower() == ".pdf" and output_format.lower() == "pdf":
        return PyMuPDFRenderer()
    return PillowRenderer()
