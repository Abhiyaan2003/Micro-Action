import sys
import os
import ctypes
from PyQt6.QtWidgets import (
    QApplication, QWidget, QGridLayout, QPushButton,
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit, QLabel,
    QFileDialog, QDialogButtonBox, QFrame, QCheckBox, QTabWidget,
    QStackedWidget, QSpinBox, QScrollArea, QGraphicsDropShadowEffect, QToolButton
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QColor, QFontMetrics, QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer
from config import get_resource_path

def get_hugeicon(name: str, color: str = "#94a3b8", size: int = 16) -> QIcon:
    """
    Renders a Hugeicon SVG file from assets/hugeicons/{name}.svg with custom color and size into a QIcon.
    """
    svg_path = get_resource_path(os.path.join("assets", "hugeicons", f"{name}.svg"))
    if not os.path.exists(svg_path):
        return QIcon()
    
    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        
        svg_content = svg_content.replace('currentColor', color)
        renderer = QSvgRenderer(svg_content.encode("utf-8"))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)
    except Exception:
        return QIcon()

def get_hugeicon_pixmap(name: str, color: str = "#94a3b8", size: int = 16) -> QPixmap:
    """
    Renders a Hugeicon SVG file into a QPixmap.
    """
    svg_path = get_resource_path(os.path.join("assets", "hugeicons", f"{name}.svg"))
    if not os.path.exists(svg_path):
        return QPixmap()
    
    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        
        svg_content = svg_content.replace('currentColor', color)
        renderer = QSvgRenderer(svg_content.encode("utf-8"))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap
    except Exception:
        return QPixmap()


def _styled_label(text: str, style: str) -> QLabel:
    """Construct a QLabel and apply its stylesheet with Qt's supported API."""
    label = QLabel(text)
    label.setStyleSheet(style)
    return label

# Map of position IDs to human-readable names for the GUI
KEY_LABELS = {
    "num7": "7 / Home",
    "num8": "8 / \u2191",
    "num9": "9 / PgUp",
    "num4": "4 / \u2190",
    "num5": "5 / Clear",
    "num6": "6 / \u2192",
    "num1": "1 / End",
    "num2": "2 / \u2193",
    "num3": "3 / PgDn",
    "num0": "0 / Insert",
    "numdot": ". / Delete",
}

# Keycap Sub-legend map
KEY_SUB_LABELS = {
    "num7": "Home",
    "num8": "Up",
    "num9": "PgUp",
    "num4": "Left",
    "num5": "Clear",
    "num6": "Right",
    "num1": "End",
    "num2": "Down",
    "num3": "PgDn",
    "num0": "Insert",
    "numdot": "Delete",
}

# Direction: Micro Action is a physical keymap, so the keycaps themselves are the
# workspace. A graphite instrument face, one cyan selection edge and precise,
# readable labels make the NumLock-controlled mapping legible without neon tiles.
# The first view answers “what does each physical key do?”; selecting a cap opens
# its real action editor beside the map. The keypad silhouette stays the signature.
#
# Data-terminal palette: cool charcoal surfaces, high-contrast text, cyan reserved
# for selection and focus, and green only for the real active hook state.
BG_MAIN       = "#1a2028"   # Graphite application canvas
BG_PANEL      = "#111820"   # Recessed work surface
BG_CARD       = "#0b1016"   # Keycaps and input surface
BG_CARD_HOVER = "#1a242e"   # Interactive hover surface
BORDER_COLOR  = "#2b3743"   # Quiet structural edge
BORDER_FOCUS  = "#68d2dc"   # Micro Action cyan

ACCENT_BLUE        = "#68d2dc"   # Single selection and focus accent
ACCENT_BLUE_HOVER  = "#8ce0e7"
ACCENT_GREEN       = "#62c49b"   # Real hook / connected state
ACCENT_RED         = "#e07b83"   # Destructive action

TEXT_MAIN     = "#f1f4f7"   # Primary text
TEXT_MUTED    = "#b4c0cb"   # Secondary text, contrast-safe on graphite
TEXT_DIM      = "#929fac"   # Helper text

# Human-readable display names for action types
ACTION_DISPLAY_NAMES = {
    "website":    "Open Website",
    "hotkey":     "Send Hotkey",
    "launch":     "Launch App",
    "script":     "Run Script",
    "ptt":        "Speech to Text",
    "screenshot": "Take Screenshot",
    "screenrec":  "Screen Record",
}
REVERSE_DISPLAY_NAMES = {v: k for k, v in ACTION_DISPLAY_NAMES.items()}

# Maps for capture mode display
MODE_MAP = {
    "Full Screen": "fullscreen",
    "Primary Monitor": "primary",
    "Active Window": "active_window",
}
REVERSE_MODE_MAP = {v: k for k, v in MODE_MAP.items()}


class ToastNotification(QWidget):
    """
    Polished Desktop Activation Toast Notification.
    Appears at the bottom-right of the screen when a macro is triggered.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.container = QWidget(self)
        self.container.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_PANEL};
                border: 1px solid {BORDER_COLOR};
                border-left: 4px solid {ACCENT_GREEN};
                border-radius: 8px;
            }}
        """)

        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        # Checkmark Icon
        self.icon_label = QLabel()
        ic_px = get_hugeicon_pixmap("screenshot", ACCENT_GREEN, 18)
        if not ic_px.isNull():
            self.icon_label.setPixmap(ic_px)
        layout.addWidget(self.icon_label)

        # Text Info
        v_lay = QVBoxLayout()
        v_lay.setSpacing(1)
        
        self.title_lbl = QLabel("Macro Activated")
        self.title_lbl.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {TEXT_MAIN}; font-family: 'Segoe UI', sans-serif; border: none; background: transparent;")
        
        self.detail_lbl = QLabel("Numpad 5 → Action Triggered")
        self.detail_lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED}; font-family: 'Consolas', monospace; border: none; background: transparent;")
        
        v_lay.addWidget(self.title_lbl)
        v_lay.addWidget(self.detail_lbl)
        layout.addLayout(v_lay)

        # Close button
        self.close_btn = QToolButton()
        self.close_btn.setText("×")
        self.close_btn.setStyleSheet(f"""
            QToolButton {{
                color: {TEXT_MUTED};
                font-size: 16px;
                font-weight: bold;
                border: none;
                background: transparent;
            }}
            QToolButton:hover {{
                color: {TEXT_MAIN};
            }}
        """)
        self.close_btn.clicked.connect(self.hide_toast)
        layout.addWidget(self.close_btn)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.addWidget(self.container)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_toast)

    def show_toast(self, title: str, detail: str, success: bool = True, color: str | None = None):
        border_col = color if color else (ACCENT_GREEN if success else ACCENT_RED)
        self.container.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_PANEL};
                border: 1px solid {BORDER_COLOR};
                border-left: 4px solid {border_col};
                border-radius: 8px;
            }}
        """)
        
        ic_name = "hotkey" if success else "delete"
        ic_px = get_hugeicon_pixmap(ic_name, border_col, 18)
        if not ic_px.isNull():
            self.icon_label.setPixmap(ic_px)

        self.title_lbl.setText(title)
        self.title_lbl.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {border_col}; font-family: 'Segoe UI', sans-serif; border: none; background: transparent;")
        
        self.detail_lbl.setText(detail)
        self.adjustSize()

        # Position bottom-right of primary screen
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            margin = 20
            self.move(
                geom.right() - self.width() - margin,
                geom.bottom() - self.height() - 50
            )

        self.setWindowOpacity(1.0)
        super().show()
        self.raise_()
        self.timer.start(2000)

    def hide_toast(self):
        super().hide()


class ActionDialog(QDialog):
    """
    Fallback Action Configuration Dialog (preserves backwards-compatibility).
    """
    def __init__(self, pos_id: str, current_action: dict | None, parent=None):
        super().__init__(parent)
        self.pos_id = pos_id
        self.setWindowTitle(f"Configure Key — {KEY_LABELS.get(pos_id, pos_id)}")
        self.setFixedWidth(400)
        self.action = current_action.copy() if current_action else {}
        self.deleted = False

        self.setStyleSheet(f"""
            QDialog {{ background-color: {BG_PANEL}; color: {TEXT_MAIN}; }}
            QLabel {{ color: {TEXT_MUTED}; font-size: 11px; font-weight: 600; font-family: 'Segoe UI', sans-serif; }}
            QLineEdit, QComboBox {{
                background-color: {BG_CARD}; color: {TEXT_MAIN};
                border: 1px solid {BORDER_COLOR}; border-radius: 6px; padding: 6px 10px; font-size: 12px;
            }}
            QPushButton {{
                background-color: {ACCENT_BLUE}; color: #ffffff; border: none; border-radius: 6px; padding: 7px 14px; font-weight: 600;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Editing Numpad Key: {KEY_LABELS.get(pos_id, pos_id)}"))
        self.setLayout(layout)

    def get_action(self):
        return self.action if not self.deleted else None


class NumpadEditor(QWidget):
    """
    Professional Split-Panel Desktop Numpad Macro Controller.
    LEFT: Hardware Numpad Matrix Keypad
    RIGHT: Configuration & Settings Workspace
    """

    key_pressed_signal = pyqtSignal(str, dict)

    def __init__(self, config, ptt=None):
        super().__init__()
        self.config = config
        self.ptt = ptt
        self.selected_key = "num5"  # Default selected key is Numpad 5
        self.test_mode = False
        self.buttons = {}
        self.action_buttons = {}

        self.setWindowTitle("Micro Action — Physical Numpad Controller")
        self.setMinimumSize(920, 640)
        self.resize(960, 660)

        # Set window icon
        icon_path = get_resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet(f"""
            QWidget#NumpadEditor {{
                background-color: {BG_MAIN};
                color: {TEXT_MAIN};
                font-family: 'Segoe UI', 'Inter', sans-serif;
            }}
            QLabel {{
                color: {TEXT_MAIN};
            }}
        """)

        # Initialize Toast Notification
        self.toast = ToastNotification()

        # Connect internal signal for thread-safe toast invocation
        self.key_pressed_signal.connect(self._handle_key_pressed_toast)

        self.build_ui()

        # Start timer to monitor NumLock status
        self._last_numlock_state = bool(ctypes.windll.user32.GetKeyState(0x90) & 1)
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.check_numlock_status)
        self.status_timer.start(100)
        self.check_numlock_status()

    def build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 14)
        main_layout.setSpacing(12)

        # ── 1. APPLICATION HEADER BAR ──
        header_bar = QFrame()
        header_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PANEL};
                border: none;
            }}
        """)
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(12)

        # Brand Logo Icon
        logo_lbl = QLabel()
        icon_png = get_resource_path(os.path.join("assets", "icon.png"))
        if os.path.exists(icon_png):
            pixmap = QPixmap(icon_png).scaled(26, 26, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pixmap)
            logo_lbl.setStyleSheet("border: none; background: transparent;")
            header_layout.addWidget(logo_lbl)

        # Title & Subtitle
        title_v = QVBoxLayout()
        title_v.setSpacing(0)
        
        t_row = QHBoxLayout()
        t_row.setSpacing(6)
        
        app_title = QLabel("Micro Action")
        app_title.setStyleSheet(f"font-size: 17px; font-weight: 650; color: {TEXT_MAIN}; font-family: 'Segoe UI', sans-serif; border: none; background: transparent;")
        
        t_row.addWidget(app_title)
        t_row.addStretch()

        app_sub = QLabel("Your numpad, set to work")
        app_sub.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED}; border: none; background: transparent;")
        
        title_v.addLayout(t_row)
        title_v.addWidget(app_sub)
        header_layout.addLayout(title_v)

        header_layout.addStretch()

        # Engine Status Indicator (Real Hardware Status Pill)
        self.status_pill = QFrame()
        self.status_pill.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: none;
            }}
        """)
        sp_lay = QHBoxLayout(self.status_pill)
        sp_lay.setContentsMargins(10, 4, 10, 4)
        sp_lay.setSpacing(8)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 12px; border: none; background: transparent;")
        sp_lay.addWidget(self.status_dot)

        self.status_lbl = QLabel("Hook active")
        self.status_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {ACCENT_GREEN}; font-family: 'Segoe UI', sans-serif; border: none; background: transparent;")
        sp_lay.addWidget(self.status_lbl)

        self.status_sub = QLabel("· Num Lock off")
        self.status_sub.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED}; border: none; background: transparent;")
        sp_lay.addWidget(self.status_sub)

        header_layout.addWidget(self.status_pill)

        main_layout.addWidget(header_bar)

        # ── 2. TWO-PANEL MAIN WORKSPACE ──
        workspace_layout = QHBoxLayout()
        workspace_layout.setSpacing(12)

        # ──────────────────────────────────────────────────────────
        # LEFT PANEL: Physical Numpad Macro Keypad (48% width)
        # ──────────────────────────────────────────────────────────
        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")
        left_panel.setStyleSheet(f"""
            QFrame#leftPanel {{
                background-color: {BG_PANEL};
                border: none;
            }}
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(10)

        # Numpad Panel Header
        np_header = QHBoxLayout()
        np_header.setSpacing(6)

        np_title_v = QVBoxLayout()
        np_title_v.setSpacing(1)

        np_title = QLabel("Key map")
        np_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {TEXT_MAIN}; font-family: 'Segoe UI', sans-serif;")
        
        np_sub = QLabel("Choose a key to assign an action")
        np_sub.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        
        np_title_v.addWidget(np_title)
        np_title_v.addWidget(np_sub)
        np_header.addLayout(np_title_v)

        np_header.addStretch()

        self.bound_badge = QLabel("0 of 11 assigned")
        self.bound_badge.setStyleSheet(f"""
            background-color: transparent;
            color: {TEXT_MUTED};
            border: none;
            padding: 3px 0;
            font-size: 11px;
            font-weight: 600;
            font-family: 'Segoe UI', sans-serif;
        """)
        np_header.addWidget(self.bound_badge)
        left_layout.addLayout(np_header)

        # Numpad Key Matrix Grid
        grid = QGridLayout()
        grid.setSpacing(10)

        rows = [
            [("num7", "7\nHome"),   ("num8", "8\n\u2191"),   ("num9", "9\nPgUp")],
            [("num4", "4\n\u2190"),   ("num5", "5\nClear"),  ("num6", "6\n\u2192")],
            [("num1", "1\nEnd"),    ("num2", "2\n\u2193"),   ("num3", "3\nPgDn")]
        ]

        for r_idx, row in enumerate(rows):
            for c_idx, (pos_id, label) in enumerate(row):
                btn = self._create_keycap_button(pos_id, label)
                grid.addWidget(btn, r_idx, c_idx)

        # Bottom row (0 is double width)
        btn0 = self._create_keycap_button("num0", "0\nInsert")
        btndot = self._create_keycap_button("numdot", ".\nDelete")
        grid.addWidget(btn0, 3, 0, 1, 2)
        grid.addWidget(btndot, 3, 2)

        left_layout.addLayout(grid)
        left_layout.addStretch()

        # Numpad Footer Toolbar
        np_footer = QHBoxLayout()
        np_footer.setSpacing(8)

        clear_all_btn = QPushButton("Clear all")
        clear_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {ACCENT_RED};
                border: none;
                border-radius: 2px;
                font-size: 11px;
                font-weight: 600;
                padding: 6px 0;
            }}
            QPushButton:hover {{
                background-color: rgba(239, 68, 68, 0.15);
            }}
            QPushButton:pressed {{
                background-color: rgba(239, 68, 68, 0.25);
            }}
        """)
        clear_all_btn.clicked.connect(self.clear_all_bindings)
        np_footer.addWidget(clear_all_btn)

        np_footer.addStretch()

        self.test_toggle = QCheckBox("Test mode")
        self.test_toggle.setToolTip("Test key triggers without dispatching live actions")
        self.test_toggle.setStyleSheet(f"""
            QCheckBox {{
                color: {TEXT_MUTED};
                font-size: 11px;
                font-weight: 700;
                font-family: 'Consolas', monospace;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 1px solid {BORDER_COLOR};
                background-color: {BG_CARD};
            }}
            QCheckBox::indicator:checked {{
                background-color: {ACCENT_BLUE};
                border-color: {ACCENT_BLUE};
            }}
        """)
        self.test_toggle.toggled.connect(self.on_test_mode_toggled)
        np_footer.addWidget(self.test_toggle)

        left_layout.addLayout(np_footer)

        # ──────────────────────────────────────────────────────────
        # RIGHT PANEL: Configuration & Workspace (52% width)
        # ──────────────────────────────────────────────────────────
        right_panel = QFrame()
        right_panel.setObjectName("rightPanel")
        right_panel.setStyleSheet(f"""
            QFrame#rightPanel {{
                background-color: {BG_PANEL};
                border: none;
            }}
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 14, 16, 14)
        right_layout.setSpacing(12)

        # Tab Bar Navigation Header
        tab_header = QHBoxLayout()
        tab_header.setSpacing(10)

        self.btn_tab_key = QPushButton("Binding")
        self.btn_tab_key.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_key.setStyleSheet(self._tab_button_style(True))
        self.btn_tab_key.clicked.connect(lambda: self.switch_workspace_tab(0))
        tab_header.addWidget(self.btn_tab_key)

        self.btn_tab_global = QPushButton("Settings")
        self.btn_tab_global.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_global.setStyleSheet(self._tab_button_style(False))
        self.btn_tab_global.clicked.connect(lambda: self.switch_workspace_tab(1))
        tab_header.addWidget(self.btn_tab_global)

        tab_header.addStretch()
        right_layout.addLayout(tab_header)

        # Stacked Widget for Tab pages
        self.stack = QStackedWidget()

        # ── PAGE 0: Key Configuration ──
        page_config = QWidget()
        pc_layout = QVBoxLayout(page_config)
        pc_layout.setContentsMargins(0, 0, 0, 0)
        pc_layout.setSpacing(12)

        # Selected Key Summary Banner
        self.sel_banner = QFrame()
        self.sel_banner.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: none;
            }}
        """)
        sb_lay = QHBoxLayout(self.sel_banner)
        sb_lay.setContentsMargins(12, 10, 12, 10)
        sb_lay.setSpacing(12)

        # Selected key representation box
        self.sel_key_box = QWidget()
        self.sel_key_box.setFixedSize(48, 48)
        self.sel_key_box.setStyleSheet(f"background-color: {BG_CARD}; border: none; border-bottom: 1px solid {ACCENT_BLUE}; border-radius: 2px;")
        sk_v = QVBoxLayout(self.sel_key_box)
        sk_v.setContentsMargins(0, 4, 0, 4)
        sk_v.setSpacing(0)
        
        self.sel_key_num = QLabel("5")
        self.sel_key_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sel_key_num.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {TEXT_MAIN}; font-family: 'Segoe UI', sans-serif; border: none;")
        
        self.sel_key_sub = QLabel("Clear")
        self.sel_key_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sel_key_sub.setStyleSheet(f"font-size: 10px; color: {TEXT_MUTED}; font-family: 'Consolas', monospace; border: none;")
        
        sk_v.addWidget(self.sel_key_num)
        sk_v.addWidget(self.sel_key_sub)
        sb_lay.addWidget(self.sel_key_box)

        sb_text_v = QVBoxLayout()
        sb_text_v.setSpacing(2)
        self.sel_title = QLabel("Numpad 5 · Clear")
        self.sel_title.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {TEXT_MAIN}; font-family: 'Segoe UI', sans-serif;")
        
        self.sel_desc = QLabel("Choose what this key should do.")
        self.sel_desc.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        
        sb_text_v.addWidget(self.sel_title)
        sb_text_v.addWidget(self.sel_desc)
        sb_lay.addLayout(sb_text_v)
        sb_lay.addStretch()

        pc_layout.addWidget(self.sel_banner)

        # Action Type Selector Grid
        pc_layout.addWidget(_styled_label("Action type", f"font-size: 11px; font-weight: 600; color: {TEXT_MUTED}; font-family: 'Segoe UI', sans-serif;"))

        type_grid = QGridLayout()
        type_grid.setSpacing(6)

        types_list = [
            ("website", "Web", "website"),
            ("hotkey", "Hotkey", "hotkey"),
            ("launch", "Application", "launch"),
            ("script", "Script", "script"),
            ("ptt", "Speech to Text", "ptt"),
            ("screenshot", "Screenshot", "screenshot"),
            ("screenrec", "Screen Record", "screenrec"),
        ]

        for idx, (t_id, t_lbl, ic_name) in enumerate(types_list):
            abtn = QPushButton(f"  {t_lbl}")
            abtn.setCursor(Qt.CursorShape.PointingHandCursor)
            abtn.setIcon(get_hugeicon(ic_name, TEXT_MUTED, 14))
            abtn.setProperty("action_type", t_id)
            abtn.setStyleSheet(self._action_type_button_style(False))
            abtn.clicked.connect(lambda _, act_id=t_id: self.select_action_type(act_id))
            self.action_buttons[t_id] = abtn
            row = idx // 4
            col = idx % 4
            type_grid.addWidget(abtn, row, col)

        pc_layout.addLayout(type_grid)

        # Dynamic Form Input Fields
        self.form_container = QWidget()
        form_lay = QVBoxLayout(self.form_container)
        form_lay.setContentsMargins(0, 6, 0, 0)
        form_lay.setSpacing(10)

        input_style = f"""
            QLineEdit, QComboBox, QSpinBox {{
                background-color: {BG_CARD};
                color: {TEXT_MAIN};
                border: 1px solid {BORDER_COLOR};
                border-radius: 4px;
                min-height: 32px;
                padding: 5px 10px;
                font-size: 12px;
            font-family: 'Segoe UI', sans-serif;
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border-color: {BORDER_FOCUS};
                background-color: {BG_CARD_HOVER};
            }}
            QComboBox QAbstractItemView {{
                background-color: {BG_CARD};
                color: {TEXT_MAIN};
                border: 1px solid {BORDER_COLOR};
                selection-background-color: {ACCENT_BLUE};
                selection-color: #ffffff;
            }}
        """

        # Website Target / Browser
        self.lbl_target = _styled_label("Website address", f"font-size: 11px; font-weight: 600; color: {TEXT_MUTED}; font-family: 'Segoe UI', sans-serif;")
        form_lay.addWidget(self.lbl_target)

        val_h = QHBoxLayout()
        val_h.setSpacing(6)
        
        self.val_input = QLineEdit()
        self.val_input.setMinimumHeight(34)
        self.val_input.setPlaceholderText("e.g. youtube.com or Ctrl+Shift+T")
        self.val_input.setStyleSheet(input_style)
        self.val_input.textChanged.connect(self.on_form_changed)
        val_h.addWidget(self.val_input)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setMinimumHeight(34)
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_CARD};
                color: {TEXT_MAIN};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {BG_CARD_HOVER}; border-color: {BORDER_FOCUS}; }}
        """)
        self.browse_btn.clicked.connect(self.browse_file)
        val_h.addWidget(self.browse_btn)

        form_lay.addLayout(val_h)

        # Open in Browser Dropdown (Website only)
        self.lbl_browser = _styled_label("Open with", f"font-size: 11px; font-weight: 600; color: {TEXT_MUTED}; font-family: 'Segoe UI', sans-serif;")
        form_lay.addWidget(self.lbl_browser)
        
        self.browser_combo = QComboBox()
        self.browser_combo.setMinimumHeight(34)
        self.browser_combo.setStyleSheet(input_style)
        self.browser_combo.addItems(["Default Browser", "Google Chrome", "Mozilla Firefox", "Microsoft Edge", "Brave Browser"])
        self.browser_combo.currentTextChanged.connect(self.on_form_changed)
        form_lay.addWidget(self.browser_combo)

        # Capture Scope (Screenshot / Screenrec)
        self.lbl_capture = _styled_label("Capture area", f"font-size: 11px; font-weight: 600; color: {TEXT_MUTED}; font-family: 'Segoe UI', sans-serif;")
        form_lay.addWidget(self.lbl_capture)

        self.capture_combo = QComboBox()
        self.capture_combo.setMinimumHeight(34)
        self.capture_combo.setStyleSheet(input_style)
        self.capture_combo.addItems(["Full Screen", "Primary Monitor", "Active Window"])
        self.capture_combo.currentTextChanged.connect(self.on_form_changed)
        form_lay.addWidget(self.capture_combo)

        # Optional Description Label
        form_lay.addWidget(_styled_label("Description (optional)", f"font-size: 11px; font-weight: 600; color: {TEXT_MUTED}; font-family: 'Segoe UI', sans-serif;"))
        self.desc_input = QLineEdit()
        self.desc_input.setMinimumHeight(34)
        self.desc_input.setPlaceholderText("e.g. Open Dev Terminal")
        self.desc_input.setStyleSheet(input_style)
        self.desc_input.textChanged.connect(self.on_form_changed)
        form_lay.addWidget(self.desc_input)

        # Advanced Macro Options (Delay & Repeat)
        adv_h = QHBoxLayout()
        adv_h.setSpacing(12)

        cb_style = f"QCheckBox {{ color: {TEXT_MUTED}; font-size: 11px; font-weight: 600; }} QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 3px; border: 1px solid {BORDER_COLOR}; background-color: {BG_CARD}; }} QCheckBox::indicator:checked {{ background-color: {ACCENT_BLUE}; border-color: {ACCENT_BLUE}; }}"
        
        self.cb_delay = QCheckBox("Add execution delay")
        self.cb_delay.setStyleSheet(cb_style)
        
        self.spin_delay = QSpinBox()
        self.spin_delay.setRange(0, 5000)
        self.spin_delay.setSuffix(" ms")
        self.spin_delay.setValue(50)
        self.spin_delay.setMinimumHeight(34)
        self.spin_delay.setStyleSheet(input_style)
        
        adv_h.addWidget(self.cb_delay)
        adv_h.addWidget(self.spin_delay)
        adv_h.addStretch()

        form_lay.addLayout(adv_h)

        pc_layout.addWidget(self.form_container)
        pc_layout.addStretch()

        # Save / Reset Bar
        act_bar = QHBoxLayout()
        act_bar.setSpacing(10)

        self.save_btn = QPushButton("Save binding")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {TEXT_MAIN};
                color: {BG_MAIN};
                border: none;
                border-radius: 3px;
                padding: 9px 18px;
                font-size: 12px;
                font-weight: 700;
                font-family: 'Segoe UI', sans-serif;
            }}
            QPushButton:hover {{ background-color: #dce5eb; }}
            QPushButton:pressed {{ background-color: #c9d4dc; }}
            QPushButton:disabled {{ background-color: {BG_CARD}; color: {TEXT_DIM}; }}
        """)
        self.save_btn.clicked.connect(self.save_current_action)
        act_bar.addWidget(self.save_btn)

        self.reset_btn = QPushButton("Reset key")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_CARD};
                color: {TEXT_MUTED};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 9px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {BG_CARD_HOVER}; color: {TEXT_MAIN}; }}
        """)
        self.reset_btn.clicked.connect(self.reset_current_action)
        act_bar.addWidget(self.reset_btn)

        act_bar.addStretch()
        config_scroll = QScrollArea()
        config_scroll.setWidgetResizable(True)
        config_scroll.setFrameShape(QFrame.Shape.NoFrame)
        config_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        config_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        config_scroll.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }} QScrollBar:vertical {{ width: 6px; background: transparent; margin: 2px; }} QScrollBar::handle:vertical {{ background: {BORDER_COLOR}; border-radius: 3px; min-height: 24px; }} QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}")
        page_config.setStyleSheet(f"background-color: {BG_PANEL};")
        config_scroll.setWidget(page_config)

        config_page = QWidget()
        config_page_layout = QVBoxLayout(config_page)
        config_page_layout.setContentsMargins(0, 0, 0, 0)
        config_page_layout.setSpacing(8)
        config_page_layout.addWidget(config_scroll, 1)
        config_page_layout.addLayout(act_bar)
        self.stack.addWidget(config_page)

        # ── PAGE 1: Global Settings ──
        page_global = QWidget()
        pg_layout = QVBoxLayout(page_global)
        pg_layout.setContentsMargins(0, 0, 0, 0)
        pg_layout.setSpacing(14)

        pg_layout.addWidget(_styled_label("System preferences", f"font-size: 16px; font-weight: 600; color: {TEXT_MAIN}; font-family: 'Segoe UI', sans-serif;"))

        self.cb_autostart = QCheckBox("Start Micro Action automatically on Windows boot")
        self.cb_autostart.setChecked(True)
        self.cb_autostart.setStyleSheet(cb_style)
        pg_layout.addWidget(self.cb_autostart)

        self.cb_minimize_tray = QCheckBox("Minimize application to system tray when closing window")
        self.cb_minimize_tray.setChecked(True)
        self.cb_minimize_tray.setStyleSheet(cb_style)
        pg_layout.addWidget(self.cb_minimize_tray)

        self.cb_shutter_sound = QCheckBox("Play shutter audio feedback on screen capture")
        self.cb_shutter_sound.setChecked(True)
        self.cb_shutter_sound.setStyleSheet(cb_style)
        pg_layout.addWidget(self.cb_shutter_sound)

        pg_layout.addStretch()
        self.stack.addWidget(page_global)

        right_layout.addWidget(self.stack)
        workspace_layout.addWidget(left_panel, stretch=48)
        workspace_layout.addWidget(right_panel, stretch=52)

        main_layout.addLayout(workspace_layout)

        # ── 3. BOTTOM HARDWARE STATUS BAR ──
        self.status_bar_frame = QFrame()
        self.status_bar_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PANEL};
                border: none;
            }}
        """)
        sb_h = QHBoxLayout(self.status_bar_frame)
        sb_h.setContentsMargins(12, 6, 12, 6)
        sb_h.setSpacing(12)

        self.sb_device = QLabel("Keyboard hook active")
        self.sb_device.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 11px; font-weight: 600; font-family: 'Segoe UI', sans-serif;")
        sb_h.addWidget(self.sb_device)

        sb_h.addWidget(_styled_label("|", f"color: {BORDER_COLOR};"))

        self.sb_config_count = QLabel("0 of 11 keys assigned")
        self.sb_config_count.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-family: 'Segoe UI', sans-serif;")
        sb_h.addWidget(self.sb_config_count)

        sb_h.addWidget(_styled_label("|", f"color: {BORDER_COLOR};"))

        self.sb_profile = QLabel("Profile · Default")
        self.sb_profile.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-family: 'Segoe UI', sans-serif;")
        sb_h.addWidget(self.sb_profile)

        sb_h.addStretch()

        self.sb_numlock = QLabel("Macros active · Num Lock off")
        self.sb_numlock.setStyleSheet(f"background-color: transparent; color: {TEXT_MUTED}; border: none; border-bottom: 1px solid {ACCENT_BLUE}; padding: 3px 0; font-size: 11px; font-weight: 600; font-family: 'Segoe UI', sans-serif;")
        sb_h.addWidget(self.sb_numlock)

        main_layout.addWidget(self.status_bar_frame)

        # Select initial key
        self.select_key(self.selected_key)
        self.update_bound_count()

    def _tab_button_style(self, active: bool) -> str:
        color = ACCENT_BLUE if active else TEXT_MUTED
        underline = f"border-bottom: 1px solid {ACCENT_BLUE};" if active else "border-bottom: 1px solid transparent;"
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {color};
                border: none;
                {underline}
                padding: 7px 2px;
                font-size: 12px;
                font-weight: {600 if active else 500};
                font-family: 'Segoe UI', sans-serif;
            }}
            QPushButton:hover {{ color: {TEXT_MAIN}; }}
            QPushButton:focus {{ border-bottom: 1px solid {ACCENT_BLUE}; }}
        """

    def _action_type_button_style(self, active: bool) -> str:
        color = ACCENT_BLUE if active else TEXT_MUTED
        underline = f"border-bottom: 1px solid {ACCENT_BLUE};" if active else "border-bottom: 1px solid transparent;"
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {color};
                border: none;
                {underline}
                border-radius: 0;
                padding: 8px 5px;
                font-size: 11px;
                font-weight: {600 if active else 500};
                text-align: left;
            }}
            QPushButton:hover {{ color: {TEXT_MAIN}; background-color: {BG_CARD}; }}
            QPushButton:focus {{ border-bottom: 1px solid {ACCENT_BLUE}; }}
        """

    def switch_workspace_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        self.btn_tab_key.setStyleSheet(self._tab_button_style(index == 0))
        self.btn_tab_global.setStyleSheet(self._tab_button_style(index == 1))

    def show_global_settings(self):
        self.switch_workspace_tab(1)

    def _create_keycap_button(self, pos_id, label):
        btn = QPushButton()
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("key_label", label)
        btn.setAccessibleName(f"Numpad {KEY_LABELS.get(pos_id, pos_id)}")
        btn.setFixedSize(120, 88) if pos_id != "num0" else btn.setFixedSize(250, 88)
        
        self.update_button_style(btn, pos_id)
        btn.clicked.connect(lambda _, pid=pos_id: self.select_key(pid))
        self.buttons[pos_id] = btn
        return btn

    def select_key(self, pos_id: str):
        prev_key = self.selected_key
        self.selected_key = pos_id

        # Update button styles for old and new selection
        if prev_key in self.buttons:
            self.update_button_style(self.buttons[prev_key], prev_key)
        if pos_id in self.buttons:
            self.update_button_style(self.buttons[pos_id], pos_id)

        # Update Selected Key Banner
        num_str = pos_id.replace("num", "").replace("dot", ".").upper()
        sub_str = KEY_SUB_LABELS.get(pos_id, "")
        self.sel_key_num.setText(num_str)
        self.sel_key_sub.setText(sub_str)
        self.sel_title.setText(f"Numpad {num_str} · {sub_str}")

        # Load action config for this key
        action = self.config.get_action(pos_id)
        if action:
            act_type = action.get("type", "website")
            action_name = ACTION_DISPLAY_NAMES.get(act_type, "Action")
            preview = action.get("desc", "") or action.get("value", "")
            if act_type == "website" and "|" in preview:
                _, preview = preview.split("|", 1)
            elif act_type in ("launch", "script"):
                preview = os.path.basename(preview)
            elif act_type == "ptt":
                preview = "Hold to dictate"
            elif act_type in ("screenshot", "screenrec"):
                preview = REVERSE_MODE_MAP.get(preview.split("|")[0], "Full Screen")
            self.sel_desc.setText(f"{action_name} · {preview}" if preview else action_name)
            self.select_action_type(act_type, update_fields=False)
            val = action.get("value", "")
            if act_type == "website" and "|" in val:
                b_id, val = val.split("|", 1)
                b_map = {"default": "Default Browser", "chrome": "Google Chrome", "firefox": "Mozilla Firefox", "edge": "Microsoft Edge", "brave": "Brave Browser"}
                self.browser_combo.setCurrentText(b_map.get(b_id, "Default Browser"))
            self.val_input.setText(val)
            if act_type in ("screenshot", "screenrec"):
                self.capture_combo.setCurrentText(REVERSE_MODE_MAP.get(val.split("|")[0], "Full Screen"))
            self.desc_input.setText(action.get("desc", ""))
        else:
            # Default empty state
            self.sel_desc.setText("Choose what this key should do.")
            self.select_action_type("website", update_fields=False)
            self.val_input.setText("")
            self.desc_input.setText("")

    def select_action_type(self, act_type: str, update_fields: bool = True):
        self.current_action_type = act_type

        # Update type button highlights
        for t_id, btn in self.action_buttons.items():
            active = (t_id == act_type)
            btn.setStyleSheet(self._action_type_button_style(active))
            btn.setIcon(get_hugeicon(t_id, "#ffffff" if active else TEXT_MUTED, 14))

        # Show/hide relevant fields
        is_web = (act_type == "website")
        is_ptt = (act_type == "ptt")
        is_capture = act_type in ("screenshot", "screenrec")

        self.lbl_browser.setVisible(is_web)
        self.browser_combo.setVisible(is_web)

        self.lbl_capture.setVisible(is_capture)
        self.capture_combo.setVisible(is_capture)

        show_val = not is_capture and not is_ptt
        self.lbl_target.setVisible(show_val)
        self.val_input.setVisible(show_val)

        if is_web:
            self.lbl_target.setText("Website address")
            self.val_input.setPlaceholderText("e.g. youtube.com or github.com")
        elif act_type == "hotkey":
            self.lbl_target.setText("Keyboard shortcut")
            self.val_input.setPlaceholderText("e.g. ctrl+shift+t or win+d")
        else:
            self.lbl_target.setText("Action parameter or path")
            self.val_input.setPlaceholderText("Enter file path or argument...")

        self.browse_btn.setVisible(act_type in ["launch", "script"])

    def on_form_changed(self):
        # Update live feedback if needed
        pass

    def browse_file(self):
        t = getattr(self, 'current_action_type', 'launch')
        filt = "Scripts (*.ps1 *.bat *.cmd *.py);;All Files (*.*)" if t == "script" else "Executables (*.exe);;All Files (*.*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select Target File", "", filt)
        if path:
            self.val_input.setText(os.path.normpath(path))

    def save_current_action(self):
        t = getattr(self, 'current_action_type', 'website')
        if t == "website":
            b_map = {"Default Browser": "default", "Google Chrome": "chrome", "Mozilla Firefox": "firefox", "Microsoft Edge": "edge", "Brave Browser": "brave"}
            b_id = b_map.get(self.browser_combo.currentText(), "default")
            val = f"{b_id}|{self.val_input.text().strip()}"
        elif t == "ptt":
            val = "base"
        elif t in ("screenshot", "screenrec"):
            val = MODE_MAP.get(self.capture_combo.currentText(), "fullscreen")
        else:
            val = self.val_input.text().strip()

        action = {"type": t, "value": val}
        desc = self.desc_input.text().strip()
        if desc:
            action["desc"] = desc

        self.config.set_action(self.selected_key, action)
        self.config.save()

        # Refresh the keycap and its adjacent assignment summary from saved data.
        self.select_key(self.selected_key)

        # Show Save Confirmation Toast
        num_str = self.selected_key.replace("num", "").replace("dot", ".").upper()
        self.toast.show_toast(f"Numpad {num_str}", f"Saved {ACTION_DISPLAY_NAMES.get(t, t)}", success=True)
        self.update_bound_count()

        # Preload Whisper model if PTT
        if t == "ptt" and self.ptt:
            self.ptt.preload()

    def reset_current_action(self):
        self.config.set_action(self.selected_key, None)
        self.config.save()
        if self.selected_key in self.buttons:
            self.update_button_style(self.buttons[self.selected_key], self.selected_key)
        self.select_key(self.selected_key)
        self.update_bound_count()

    def clear_all_bindings(self):
        for pid in list(KEY_LABELS.keys()):
            self.config.set_action(pid, None)
        self.config.save()
        for pid, btn in self.buttons.items():
            self.update_button_style(btn, pid)
        self.select_key(self.selected_key)
        self.update_bound_count()

    def update_button_style(self, btn, pos_id):
        action = self.config.get_action(pos_id)
        label = btn.property("key_label")
        parts = label.split('\n')
        prim = parts[0]
        sub = parts[1] if len(parts) > 1 else ""
        is_selected = (pos_id == self.selected_key)

        layout = btn.layout()
        if layout is None:
            layout = QVBoxLayout(btn)
            layout.setContentsMargins(9, 7, 9, 7)
            layout.setSpacing(2)

            top_h = QHBoxLayout()
            top_h.setContentsMargins(0, 0, 0, 0)
            top_h.setSpacing(4)

            prim_label = QLabel()
            prim_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

            sub_label = QLabel()
            sub_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            sub_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

            top_h.addWidget(prim_label)
            top_h.addStretch()
            top_h.addWidget(sub_label)
            layout.addLayout(top_h)
            layout.addStretch()

            badge_box = QWidget()
            badge_box.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            b_lay = QVBoxLayout(badge_box)
            b_lay.setContentsMargins(0, 0, 0, 0)
            b_lay.setSpacing(1)

            type_label = QLabel()
            type_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            val_label = QLabel()
            val_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            type_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            val_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            b_lay.addWidget(type_label)
            b_lay.addWidget(val_label)
            layout.addWidget(badge_box)

            btn.prim_label = prim_label
            btn.sub_label = sub_label
            btn.badge_box = badge_box
            btn.type_label = type_label
            btn.val_label = val_label

        btn.prim_label.setText(prim)
        btn.sub_label.setText(sub)
        btn.setText("")
        btn.prim_label.setStyleSheet(f"font-size: 25px; font-weight: 650; color: {TEXT_MAIN}; font-family: 'Segoe UI', sans-serif; border: none; background: transparent;")
        btn.sub_label.setStyleSheet(f"font-size: 10px; color: {TEXT_MUTED}; font-family: 'Consolas', monospace; border: none; background: transparent;")

        if action:
            t = action.get("type", "")
            v = action.get("value", "")
            desc = action.get("desc", "")
            display_val = desc or v
            if t == "website":
                if "|" in display_val:
                    _, display_val = display_val.split("|", 1)
                if not desc:
                    display_val = display_val.replace("https://", "").replace("http://", "").replace("www.", "")
            elif t in ("launch", "script"):
                display_val = os.path.basename(display_val)
            elif t == "ptt":
                display_val = "Hold to dictate"
            elif t in ("screenshot", "screenrec"):
                display_val = REVERSE_MODE_MAP.get(v.split("|")[0], "Full Screen")

            compact_name = {
                "website": "Website", "hotkey": "Shortcut", "launch": "Application",
                "script": "Script", "ptt": "Speech to text", "screenshot": "Screenshot",
                "screenrec": "Screen recording",
            }.get(t, ACTION_DISPLAY_NAMES.get(t, t.title()))
            btn.type_label.setText(compact_name)
            btn.type_label.setStyleSheet(f"font-size: 10px; font-weight: 500; color: {TEXT_MUTED}; font-family: 'Segoe UI', sans-serif; border: none; background: transparent;")
            btn.val_label.setStyleSheet(f"font-size: 10px; font-weight: 600; color: {TEXT_MAIN}; font-family: 'Consolas', monospace; border: none; background: transparent;")
            metrics = QFontMetrics(btn.val_label.font())
            btn.val_label.setText(metrics.elidedText(display_val, Qt.TextElideMode.ElideMiddle, max(24, btn.width() - 20)))
            btn.setToolTip(f"Numpad {prim} / {sub}\n{compact_name}: {display_val}")
            btn.setAccessibleDescription(f"Assigned action: {compact_name}. {display_val}.")
        else:
            btn.type_label.setText("Unassigned")
            btn.type_label.setStyleSheet(f"font-size: 10px; font-weight: 500; color: {TEXT_MUTED}; font-family: 'Segoe UI', sans-serif; border: none; background: transparent;")
            btn.val_label.setText("Select to configure")
            btn.val_label.setStyleSheet(f"font-size: 10px; color: {TEXT_DIM}; font-family: 'Segoe UI', sans-serif; border: none; background: transparent;")
            btn.setToolTip(f"Numpad {prim} / {sub}\nNo action assigned. Select to configure.")
            btn.setAccessibleDescription("Unassigned. Select to configure an action.")

        # One 1px cyan edge is the entire selected-state treatment.
        selection = ACCENT_BLUE if is_selected else BORDER_COLOR
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_CARD};
                color: {TEXT_MAIN};
                border: none;
                border-bottom: 1px solid {selection};
                border-radius: 2px;
            }}
            QPushButton:hover {{
                background-color: {BG_CARD_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {BG_PANEL};
            }}
            QPushButton:focus {{ border-bottom: 1px solid {ACCENT_BLUE}; }}
        """)

    def update_bound_count(self):
        count = sum(1 for pid in KEY_LABELS if self.config.get_action(pid))
        if hasattr(self, 'bound_badge'):
            self.bound_badge.setText(f"{count} of 11 assigned")
        if hasattr(self, 'sb_config_count'):
            self.sb_config_count.setText(f"{count} of 11 keys assigned")

    def on_test_mode_toggled(self, checked: bool):
        self.test_mode = checked
        if checked:
            self.toast.show_toast("TEST MODE", "Key triggers will preview without OS mutation", success=True)

    def trigger_physical_key_press(self, pos_id: str):
        """Called when a physical keypress is captured by the Windows Keyboard Hook."""
        action = self.config.get_action(pos_id)
        if action or self.test_mode:
            # Emit signal to handle UI animation and Toast safely on Qt main thread
            self.key_pressed_signal.emit(pos_id, action or {"type": "test", "value": "Test Trigger"})

    def _handle_key_pressed_toast(self, pos_id: str, action: dict):
        try:
            # Fast keycap press animation if window is visible
            if self.isVisible() and pos_id in self.buttons:
                btn = self.buttons[pos_id]
                btn.animateClick()
        except Exception as e:
            print(f"[GUI Animation Error] {e}")

    def check_numlock_status(self):
        numlock_toggled = bool(ctypes.windll.user32.GetKeyState(0x90) & 1)
        prev = getattr(self, '_last_numlock_state', None)
        self._last_numlock_state = numlock_toggled

        if not numlock_toggled:
            self.status_dot.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 12px; border: none; background: transparent;")
            self.status_lbl.setText("Macros active")
            self.status_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {ACCENT_GREEN}; font-family: 'Segoe UI', sans-serif; border: none; background: transparent;")
            self.status_sub.setText("· Num Lock off")
            self.sb_numlock.setText("Macros active · Num Lock off")
            self.sb_numlock.setStyleSheet(f"background-color: transparent; color: {TEXT_MUTED}; border: none; border-bottom: 1px solid {ACCENT_BLUE}; padding: 3px 0; font-size: 11px; font-weight: 600; font-family: 'Segoe UI', sans-serif;")
            
            # Show toast only on actual transition
            if prev is not None and prev != numlock_toggled:
                if hasattr(self, 'toast') and self.toast:
                    self.toast.show_toast(
                        "MACROS ACTIVE",
                        "Num Lock OFF — Physical numpad macros active",
                        success=True,
                        color=ACCENT_GREEN
                    )
        else:
            self.status_dot.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; border: none; background: transparent;")
            self.status_lbl.setText("Number keys active")
            self.status_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT_MUTED}; font-family: 'Segoe UI', sans-serif; border: none; background: transparent;")
            self.status_sub.setText("· Num Lock on")
            self.sb_numlock.setText("Number keys active · Num Lock on")
            self.sb_numlock.setStyleSheet(f"background-color: transparent; color: {TEXT_MUTED}; border: none; border-bottom: 1px solid {BORDER_COLOR}; padding: 3px 0; font-size: 11px; font-weight: 600; font-family: 'Segoe UI', sans-serif;")

            # Show toast only on actual transition
            if prev is not None and prev != numlock_toggled:
                if hasattr(self, 'toast') and self.toast:
                    self.toast.show_toast(
                        "PASS-THROUGH MODE",
                        "Num Lock ON — Standard numeric keypad",
                        success=True,
                        color=TEXT_MUTED
                    )
