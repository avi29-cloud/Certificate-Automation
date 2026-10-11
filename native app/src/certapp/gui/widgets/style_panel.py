"""Styling Panel Widget for certificate text — compact horizontal layout with font selector."""

from pathlib import Path
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QDoubleSpinBox, QSlider, QPushButton, QCheckBox,
    QColorDialog, QLineEdit, QFileDialog, QFrame
)

from src.certapp.core.models import LayoutConfig, LayoutElement
from src.certapp.core.utils import find_system_fonts


class StylePanelWidget(QWidget):
    """Compact control panel for text style — all options visible at once, horizontal layout."""

    style_changed = Signal(LayoutConfig)
    sample_text_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = LayoutConfig()
        self.font_map = find_system_fonts()
        self._block_signals = False

        self.init_ui()

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: bold; font-size: 11px; color: #3A86FF; padding: 2px 0;")
        return lbl

    def _small_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 11px; color: #BBBBBB;")
        return lbl

    def _separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #2E3148;")
        return sep

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(6)

        # ── Row 1: Sample Text + Font Family + Font Size + Min Size ──
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        # Sample Text
        row1.addWidget(self._small_label("Preview:"))
        self.txt_sample = QLineEdit("Jane Alexander Doe")
        self.txt_sample.setFixedWidth(160)
        self.txt_sample.textChanged.connect(lambda t: self.sample_text_changed.emit(t))
        row1.addWidget(self.txt_sample)

        row1.addWidget(self._separator())

        # Font Family
        row1.addWidget(self._small_label("Font:"))
        self.combo_font = QComboBox()
        self.combo_font.setMinimumWidth(180)
        self.combo_font.setMaxVisibleItems(20)
        self.combo_font.setStyleSheet("""
            QComboBox {
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                max-height: 300px;
            }
        """)
        self.combo_font.addItem("Default Sans-Serif", "")
        for name, path in sorted(self.font_map.items()):
            self.combo_font.addItem(name, path)
        self.combo_font.currentIndexChanged.connect(self._emit_style)
        row1.addWidget(self.combo_font)

        row1.addWidget(self._separator())

        # Font Size
        row1.addWidget(self._small_label("Size:"))
        self.spin_size = QSpinBox()
        self.spin_size.setRange(8, 200)
        self.spin_size.setValue(40)
        self.spin_size.setSuffix(" pt")
        self.spin_size.valueChanged.connect(self._emit_style)
        row1.addWidget(self.spin_size)

        # Min Size
        row1.addWidget(self._small_label("Min:"))
        self.spin_min_size = QSpinBox()
        self.spin_min_size.setRange(6, 100)
        self.spin_min_size.setValue(16)
        self.spin_min_size.setSuffix(" pt")
        self.spin_min_size.valueChanged.connect(self._emit_style)
        row1.addWidget(self.spin_min_size)

        row1.addStretch()
        root.addLayout(row1)

        # ── Row 2: Bold + Italic + Alignment + Color + Max Width + Position + Output Format ──
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        # Bold / Italic
        self.chk_bold = QCheckBox("Bold")
        self.chk_bold.setStyleSheet("font-size: 11px;")
        self.chk_italic = QCheckBox("Italic")
        self.chk_italic.setStyleSheet("font-size: 11px;")
        self.chk_bold.stateChanged.connect(self._emit_style)
        self.chk_italic.stateChanged.connect(self._emit_style)
        row2.addWidget(self.chk_bold)
        row2.addWidget(self.chk_italic)

        row2.addWidget(self._separator())

        # Alignment
        row2.addWidget(self._small_label("Align:"))
        self.combo_align = QComboBox()
        self.combo_align.addItems(["center", "left", "right"])
        self.combo_align.currentTextChanged.connect(self._emit_style)
        row2.addWidget(self.combo_align)

        row2.addWidget(self._separator())

        # Color
        row2.addWidget(self._small_label("Color:"))
        self.btn_color = QPushButton("#003366")
        self.btn_color.setFixedWidth(80)
        self.current_color = "#003366"
        self._update_color_btn()
        self.btn_color.clicked.connect(self._pick_color)
        row2.addWidget(self.btn_color)

        row2.addWidget(self._separator())

        # Max Width Slider
        row2.addWidget(self._small_label("Max Width:"))
        self.slider_max_w = QSlider(Qt.Orientation.Horizontal)
        self.slider_max_w.setRange(20, 100)
        self.slider_max_w.setValue(80)
        self.slider_max_w.setFixedWidth(100)
        self.lbl_max_w_val = QLabel("80%")
        self.lbl_max_w_val.setStyleSheet("font-size: 11px; color: #CCC; min-width: 30px;")
        self.slider_max_w.valueChanged.connect(lambda v: self.lbl_max_w_val.setText(f"{v}%"))
        self.slider_max_w.valueChanged.connect(self._emit_style)
        row2.addWidget(self.slider_max_w)
        row2.addWidget(self.lbl_max_w_val)

        row2.addWidget(self._separator())

        # Position X / Y
        row2.addWidget(self._small_label("X:"))
        self.spin_x = QDoubleSpinBox()
        self.spin_x.setRange(0.0, 100.0)
        self.spin_x.setValue(50.0)
        self.spin_x.setSuffix(" %")
        self.spin_x.setSingleStep(0.5)
        self.spin_x.setFixedWidth(80)
        self.spin_x.valueChanged.connect(self._emit_style)
        row2.addWidget(self.spin_x)

        row2.addWidget(self._small_label("Y:"))
        self.spin_y = QDoubleSpinBox()
        self.spin_y.setRange(0.0, 100.0)
        self.spin_y.setValue(50.0)
        self.spin_y.setSuffix(" %")
        self.spin_y.setSingleStep(0.5)
        self.spin_y.setFixedWidth(80)
        self.spin_y.valueChanged.connect(self._emit_style)
        row2.addWidget(self.spin_y)

        row2.addWidget(self._separator())

        # Output Format
        row2.addWidget(self._small_label("Format:"))
        self.combo_format = QComboBox()
        self.combo_format.addItems(["PDF", "PNG"])
        self.combo_format.currentTextChanged.connect(self._emit_style)
        row2.addWidget(self.combo_format)

        row2.addWidget(self._separator())

        # Preset buttons
        preset_style = """
            QPushButton {
                background-color: #2D3047; color: #FFF;
                border: 1px solid #4A4D6B; border-radius: 4px;
                padding: 4px 10px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background-color: #3A86FF; }
        """
        btn_save = QPushButton("💾 Save")
        btn_load = QPushButton("📂 Load")
        btn_save.setStyleSheet(preset_style)
        btn_load.setStyleSheet(preset_style)
        btn_save.clicked.connect(self._save_preset)
        btn_load.clicked.connect(self._load_preset)
        row2.addWidget(btn_save)
        row2.addWidget(btn_load)

        row2.addStretch()
        root.addLayout(row2)

    # ── helpers ──
    def _update_color_btn(self):
        self.btn_color.setText(self.current_color)
        self.btn_color.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.current_color}; color: #FFF;
                border: 1px solid #FFF; border-radius: 4px;
                font-weight: bold; padding: 4px; font-size: 11px;
            }}
        """)

    def _pick_color(self):
        col = QColorDialog.getColor(QColor(self.current_color), self, "Select Text Color")
        if col.isValid():
            self.current_color = col.name()
            self._update_color_btn()
            self._emit_style()

    def _emit_style(self):
        """Collect all controls into LayoutConfig and emit, unless blocked."""
        if self._block_signals:
            return
        cfg = self._collect_config()
        self.style_changed.emit(cfg)

    def _collect_config(self) -> LayoutConfig:
        elem = self.config.elements[0] if self.config.elements else LayoutElement()
        font_data = self.combo_font.currentData()
        elem.font_path = font_data if font_data else None
        elem.font_size = self.spin_size.value()
        elem.min_font_size = self.spin_min_size.value()
        elem.max_width_frac = self.slider_max_w.value() / 100.0
        elem.color_hex = self.current_color
        elem.alignment = self.combo_align.currentText()
        elem.is_bold = self.chk_bold.isChecked()
        elem.is_italic = self.chk_italic.isChecked()
        elem.x_frac = self.spin_x.value() / 100.0
        elem.y_frac = self.spin_y.value() / 100.0
        self.config.elements = [elem]
        self.config.output_format = self.combo_format.currentText().lower()
        return self.config

    def set_layout_config(self, cfg: LayoutConfig):
        """Populate controls from config WITHOUT emitting signals (breaks loop)."""
        self._block_signals = True
        self.config = cfg
        if cfg.elements:
            e = cfg.elements[0]
            # Sync font combo box
            self._sync_font_combo(e.font_path)
            self.spin_size.setValue(e.font_size)
            self.spin_min_size.setValue(e.min_font_size)
            self.slider_max_w.setValue(int(e.max_width_frac * 100))
            self.current_color = e.color_hex
            self._update_color_btn()
            self.combo_align.setCurrentText(e.alignment)
            self.chk_bold.setChecked(e.is_bold)
            self.chk_italic.setChecked(e.is_italic)
            self.spin_x.setValue(e.x_frac * 100.0)
            self.spin_y.setValue(e.y_frac * 100.0)
        self.combo_format.setCurrentText(cfg.output_format.upper())
        self._block_signals = False

    def _sync_font_combo(self, font_path: str | None):
        """Set the font combo box to match the given font path."""
        if not font_path:
            self.combo_font.setCurrentIndex(0)  # Default
            return
        # Search by data (path)
        for i in range(self.combo_font.count()):
            if self.combo_font.itemData(i) == font_path:
                self.combo_font.setCurrentIndex(i)
                return
        # Fallback: search by stem name
        stem = Path(font_path).stem.replace("-", " ").replace("_", " ")
        for i in range(self.combo_font.count()):
            if self.combo_font.itemText(i).lower() == stem.lower():
                self.combo_font.setCurrentIndex(i)
                return
        # Not found — keep default
        self.combo_font.setCurrentIndex(0)

    def _save_preset(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Preset", "", "JSON (*.json)")
        if path:
            self._collect_config().save_json(path)

    def _load_preset(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Preset", "", "JSON (*.json)")
        if path:
            cfg = LayoutConfig.load_json(path)
            self.set_layout_config(cfg)
            self._emit_style()
