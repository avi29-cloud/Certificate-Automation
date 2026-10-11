"""Central application theme and styling tokens for CertApp."""

from src.certapp.core.utils import get_assets_dir

_CHECK_SVG_PATH = (get_assets_dir() / "icons" / "check.svg").as_posix()

DARK_THEME = f"""
    QMainWindow, QDialog, QWidget {{
        background-color: #181924;
        color: #E0E0E0;
        font-family: 'Inter', 'Roboto', 'DejaVu Sans', sans-serif;
    }}
    QGroupBox {{
        border: 1px solid #2E3148;
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 16px;
        font-weight: bold;
        color: #AAAAAA;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
    }}
    QProgressBar {{
        background-color: #12131C;
        border: 1px solid #2E3148;
        border-radius: 5px;
        text-align: center;
        color: #FFFFFF;
    }}
    QProgressBar::chunk {{
        background-color: #3A86FF;
        border-radius: 5px;
    }}
    QTableWidget {{
        background-color: #1A1B26;
        gridline-color: #2E3148;
        border: 1px solid #2E3148;
        border-radius: 6px;
        alternate-background-color: #1E1F29;
    }}
    QHeaderView::section {{
        background-color: #252836;
        color: #E0E0E0;
        padding: 6px;
        font-weight: bold;
        border: 1px solid #2E3148;
    }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background-color: #1E1F29;
        color: #E0E0E0;
        border: 1px solid #3A3D5C;
        border-radius: 4px;
        padding: 4px 6px;
    }}
    QComboBox::drop-down {{
        border: none;
    }}
    QSlider::groove:horizontal {{
        background: #2E3148;
        height: 6px;
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: #3A86FF;
        width: 14px;
        margin: -4px 0;
        border-radius: 7px;
    }}
    QCheckBox {{
        spacing: 8px;
        color: #E0E0E0;
    }}
    QCheckBox::indicator, QTableWidget::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid #5A5D7A;
        border-radius: 4px;
        background-color: #1E1F29;
    }}
    QCheckBox::indicator:hover, QTableWidget::indicator:hover {{
        border: 2px solid #3A86FF;
        background-color: #26293D;
    }}
    QCheckBox::indicator:checked, QTableWidget::indicator:checked {{
        border: 2px solid #3A86FF;
        background-color: #3A86FF;
        image: url("{_CHECK_SVG_PATH}");
    }}
    QCheckBox::indicator:checked:hover, QTableWidget::indicator:checked:hover {{
        border: 2px solid #2563EB;
        background-color: #2563EB;
        image: url("{_CHECK_SVG_PATH}");
    }}
    QCheckBox::indicator:disabled, QTableWidget::indicator:disabled {{
        border: 2px solid #333344;
        background-color: #161720;
    }}
    QScrollArea {{ background: transparent; }}
"""

BTN_PRIMARY = """
    QPushButton {
        background-color: #3A86FF; color: #FFF;
        font-weight: bold; font-size: 13px;
        border-radius: 6px; padding: 10px 20px;
    }
    QPushButton:hover { background-color: #2563EB; }
    QPushButton:disabled { background-color: #333; color: #777; }
"""

BTN_SUCCESS = """
    QPushButton {
        background-color: #2ECC71; color: #FFF;
        font-weight: bold; font-size: 13px;
        border-radius: 6px; padding: 10px 20px;
    }
    QPushButton:hover { background-color: #27AE60; }
    QPushButton:disabled { background-color: #333; color: #777; }
"""

BTN_DANGER = """
    QPushButton {
        background-color: #E74C3C; color: #FFF;
        font-weight: bold; font-size: 13px;
        border-radius: 6px; padding: 10px 20px;
    }
    QPushButton:disabled { background-color: #333; color: #777; }
"""

BTN_SECONDARY = """
    QPushButton {
        background-color: #2D3047; color: #FFF;
        border: 1px solid #4A4D6B; border-radius: 5px;
        padding: 8px 16px; font-weight: bold;
    }
    QPushButton:hover { background-color: #3A86FF; }
"""
