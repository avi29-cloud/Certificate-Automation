"""Visual Click-to-Place Certificate Template Preview Canvas with keyboard zoom."""

from pathlib import Path
from typing import Optional
import pymupdf as fitz
from PySide6.QtCore import Signal, Qt, QPointF
from PySide6.QtGui import (
    QPixmap, QImage, QColor, QFont, QKeySequence, QWheelEvent,
    QPainter, QShortcut
)
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsTextItem, QGraphicsItem, QVBoxLayout, QWidget,
    QHBoxLayout, QPushButton, QLabel,
    QGraphicsRectItem
)

from src.certapp.core.models import LayoutElement, LayoutConfig
from src.certapp.core.layout import LayoutManager


class DraggableTextMarker(QGraphicsTextItem):
    """Movable draggable text marker on the canvas."""

    position_changed = None  # Set by parent canvas

    def __init__(self, text: str = "Sample Name", parent=None):
        super().__init__(text, parent)
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.OpenHandCursor)

        self.element_data = LayoutElement()
        self.canvas_width = 800
        self.canvas_height = 600
        self._suppress_notify = False

        self.setDefaultTextColor(QColor("#003366"))
        self.setFont(QFont("Sans", 24, QFont.Weight.Bold))

    def sync_from_element(self, elem: LayoutElement, sample_text: str = "Sample Name"):
        """Update visual from element data without triggering position feedback."""
        self._suppress_notify = True
        self.element_data = elem
        self.setPlainText(sample_text)

        qfont = QFont()
        if elem.font_path:
            qfont.setFamily(Path(elem.font_path).stem)
        else:
            qfont.setFamily("Sans")
        qfont.setPointSize(max(10, elem.font_size // 3))
        qfont.setBold(elem.is_bold)
        qfont.setItalic(elem.is_italic)
        self.setFont(qfont)

        try:
            self.setDefaultTextColor(QColor(elem.color_hex))
        except Exception:
            self.setDefaultTextColor(QColor("#000000"))

        px, py = LayoutManager.frac_to_pixel(
            elem.x_frac, elem.y_frac, self.canvas_width, self.canvas_height
        )
        bbox = self.boundingRect()
        w, h = bbox.width(), bbox.height()

        if elem.alignment == "center":
            x = px - w / 2.0
        elif elem.alignment == "right":
            x = px - w
        else:
            x = float(px)
        y = py - h / 2.0
        self.setPos(x, y)
        self._suppress_notify = False

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene() and not self._suppress_notify:
            new_pos = value
            bbox = self.boundingRect()
            w, h = bbox.width(), bbox.height()

            if self.element_data.alignment == "center":
                cx = new_pos.x() + w / 2.0
            elif self.element_data.alignment == "right":
                cx = new_pos.x() + w
            else:
                cx = new_pos.x()
            cy = new_pos.y() + h / 2.0

            x_frac, y_frac = LayoutManager.pixel_to_frac(
                int(round(cx)), int(round(cy)), self.canvas_width, self.canvas_height
            )
            self.element_data.x_frac = x_frac
            self.element_data.y_frac = y_frac

            if self.position_changed:
                self.position_changed(self.element_data)

        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)


class ZoomableGraphicsView(QGraphicsView):
    """QGraphicsView with mouse-wheel zoom and keyboard shortcuts."""

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._zoom_factor = 1.0

    def wheelEvent(self, event: QWheelEvent):
        """Ctrl+Wheel = zoom, plain wheel = scroll."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def zoom_in(self):
        self._zoom_factor *= 1.15
        self.scale(1.15, 1.15)

    def zoom_out(self):
        self._zoom_factor /= 1.15
        self.scale(1.0 / 1.15, 1.0 / 1.15)

    def reset_zoom(self):
        self.resetTransform()
        self._zoom_factor = 1.0


class TemplatePreviewCanvas(QWidget):
    """Certificate template canvas with draggable text markers and zoom."""

    layout_changed = Signal(LayoutConfig)
    marker_selected = Signal(LayoutElement)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = LayoutConfig()
        self.sample_name = "Jane Alexander Doe"

        self._gfx_scene = QGraphicsScene(self)
        self.view = ZoomableGraphicsView(self._gfx_scene, self)
        self.pixmap_item: Optional[QGraphicsPixmapItem] = None
        self.marker_items: list[DraggableTextMarker] = []

        self.canvas_width = 800
        self.canvas_height = 600

        self.init_ui()
        self.setup_shortcuts()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Toolbar
        tb = QHBoxLayout()
        tb.setContentsMargins(6, 6, 6, 6)

        self.lbl_info = QLabel("Drag text marker to reposition • Ctrl+Scroll or +/- to zoom")
        self.lbl_info.setStyleSheet("color: #AAAAAA; font-size: 11px;")

        btn_style = """
            QPushButton {
                background-color: #2D3047; color: #EEE;
                border: 1px solid #4A4D6B; border-radius: 4px;
                padding: 4px 10px; font-size: 11px;
            }
            QPushButton:hover { background-color: #3A86FF; }
        """
        self.btn_zoom_in = QPushButton("Zoom In (+)")
        self.btn_zoom_out = QPushButton("Zoom Out (−)")
        self.btn_fit = QPushButton("Fit")
        self.btn_reset = QPushButton("1:1")
        for b in (self.btn_zoom_in, self.btn_zoom_out, self.btn_fit, self.btn_reset):
            b.setStyleSheet(btn_style)

        self.btn_zoom_in.clicked.connect(self.view.zoom_in)
        self.btn_zoom_out.clicked.connect(self.view.zoom_out)
        self.btn_fit.clicked.connect(self.fit_to_view)
        self.btn_reset.clicked.connect(self.view.reset_zoom)

        tb.addWidget(self.lbl_info)
        tb.addStretch()
        tb.addWidget(self.btn_zoom_in)
        tb.addWidget(self.btn_zoom_out)
        tb.addWidget(self.btn_fit)
        tb.addWidget(self.btn_reset)

        self.view.setStyleSheet("background-color: #12131C; border: 1px solid #2E3148;")

        layout.addLayout(tb)
        layout.addWidget(self.view)

    def setup_shortcuts(self):
        """Keyboard shortcuts for zoom."""
        QShortcut(QKeySequence("Ctrl+="), self, activated=self.view.zoom_in)
        QShortcut(QKeySequence("Ctrl++"), self, activated=self.view.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, activated=self.view.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, activated=self.fit_to_view)
        QShortcut(QKeySequence("+"), self, activated=self.view.zoom_in)
        QShortcut(QKeySequence("-"), self, activated=self.view.zoom_out)
        QShortcut(QKeySequence("="), self, activated=self.view.zoom_in)

    def set_template(self, template_path: str):
        p = Path(template_path)
        if not p.exists():
            return

        self.config.background_path = str(p)

        if p.suffix.lower() == ".pdf":
            doc = fitz.open(p)
            if len(doc) > 0:
                page = doc[0]
                pix = page.get_pixmap(dpi=150)
                qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
            else:
                return
            doc.close()
        else:
            pixmap = QPixmap(str(p))

        if pixmap.isNull():
            return

        self._gfx_scene.clear()
        self.marker_items.clear()

        self.canvas_width = pixmap.width()
        self.canvas_height = pixmap.height()

        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self._gfx_scene.addItem(self.pixmap_item)
        self._gfx_scene.setSceneRect(0, 0, self.canvas_width, self.canvas_height)

        self.rebuild_markers()
        self.fit_to_view()

    def rebuild_markers(self):
        for item in self.marker_items:
            if item.scene() == self._gfx_scene:
                self._gfx_scene.removeItem(item)
        self.marker_items.clear()

        for elem in self.config.elements:
            marker = DraggableTextMarker()
            marker.canvas_width = self.canvas_width
            marker.canvas_height = self.canvas_height
            marker.position_changed = self._on_marker_moved
            marker.sync_from_element(elem, self.sample_name)
            self._gfx_scene.addItem(marker)
            self.marker_items.append(marker)

    def update_layout_config(self, new_config: LayoutConfig, sample_name: Optional[str] = None):
        bg = self.config.background_path
        self.config = new_config
        if bg and not self.config.background_path:
            self.config.background_path = bg
        if sample_name is not None:
            self.sample_name = sample_name
        self.rebuild_markers()

    def _on_marker_moved(self, updated_element: LayoutElement):
        self.layout_changed.emit(self.config)

    def fit_to_view(self):
        if self.pixmap_item:
            self.view.fitInView(self._gfx_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
