"""Minimal-glass main window and action editor."""
from __future__ import annotations

import os

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QSignalBlocker, Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QColor, QFont, QPainter, QRadialGradient
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QSpinBox, QToolButton, QVBoxLayout, QWidget, QGraphicsOpacityEffect, QBoxLayout,
)

from config import Config
from gui import KEY_LABELS, KEY_SUB_LABELS, MODE_MAP, REVERSE_MODE_MAP
from ui.chips import ActionChip
from ui.icons import icon
from ui.theme import DARK, ThemeTokens, interface_font_family, stylesheet_tokens, theme_for, token_color
from ui.tiles import KeyTile


ACTION_TYPES = [
    ("website", "Web link"),
    ("hotkey", "Hotkey"),
    ("launch", "Launch app"),
    ("script", "Script"),
    ("ptt", "Push-to-talk"),
    ("screenshot", "Screenshot"),
    ("screenrec", "Screen record"),
    ("volume", "Volume"),
    ("brightness", "Brightness"),
]

ACTION_SUBTITLES = {
    "website": "Web link action",
    "hotkey": "Hotkey action",
    "launch": "Launch app action",
    "script": "Script action",
    "ptt": "Push-to-talk action",
    "screenshot": "Screenshot action",
    "screenrec": "Screen record action",
    "volume": "Volume action",
    "brightness": "Brightness action",
}


class GlassNumpadEditor(QWidget):
    key_pressed_signal = pyqtSignal(str, dict)
    appearance_changed = pyqtSignal(str)

    def __init__(self, config: Config, ptt=None, notification_overlay=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.ptt = ptt
        self.toast = notification_overlay
        appearance_val = config.get_setting("appearance", "system")
        self.appearance: str = appearance_val if isinstance(appearance_val, str) else "system"
        if self.toast is None:
            from ui.overlays import OverlayPill
            self.toast = OverlayPill(self.appearance)
        self.theme: ThemeTokens = theme_for(self.appearance)
        self.selected_key = "numdot"
        self.current_action_type = "hotkey"
        self.buttons: dict[str, KeyTile] = {}
        self.action_buttons: dict[str, ActionChip] = {}
        self.bound_count: QLabel | None = None
        self.test_mode = False

        self.setObjectName("glassMain")
        self.setWindowTitle("KeySpark")
        self.setMinimumSize(820, 540)
        self.resize(960, 600)
        self._build_ui()
        self.key_pressed_signal.connect(self._handle_key_feedback)
        self._apply_theme()
        self.select_key(self.selected_key)
        self.set_numlock_state(False)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 28)
        root.setSpacing(18)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel("KeySpark")
        self.title.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: 700; background: transparent;")
        header.addWidget(self.title)
        header.addStretch(1)

        self.status_button = QPushButton()
        self.status_button.setObjectName("statusButton")
        self.status_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.status_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_button.clicked.connect(self._toggle_or_preview_status)
        header.addWidget(self.status_button)
        root.addLayout(header)

        self.body_layout = QHBoxLayout()
        self.body_layout.setContentsMargins(0, 10, 0, 0)
        self.body_layout.setSpacing(48)

        # Left Column: Numpad Grid + Helper text
        self.key_area = QWidget()
        self.key_area.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        key_layout = QVBoxLayout(self.key_area)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(18)

        self.key_grid = QWidget()
        self.key_grid.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        grid = QGridLayout(self.key_grid)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        key_rows = [
            [("num7", "7"), ("num8", "8"), ("num9", "9")],
            [("num4", "4"), ("num5", "5"), ("num6", "6")],
            [("num1", "1"), ("num2", "2"), ("num3", "3")],
        ]
        for row_index, row in enumerate(key_rows):
            for col_index, (pos_id, number) in enumerate(row):
                self._add_tile(grid, pos_id, number, KEY_SUB_LABELS[pos_id], row_index, col_index)
        self._add_tile(grid, "num0", "0", KEY_SUB_LABELS["num0"], 3, 0, wide=True)
        self._add_tile(grid, "numdot", ".", KEY_SUB_LABELS["numdot"], 3, 2)
        key_layout.addWidget(self.key_grid)

        self.helper_text = QLabel(
            "Press a number key to try a tile. Press NumLock, or use the status button above, to see the on and off notifications."
        )
        self.helper_text.setWordWrap(True)
        self.helper_text.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 11px; line-height: 1.45; background: transparent;")
        self.helper_text.setFixedWidth(276)
        key_layout.addWidget(self.helper_text)
        key_layout.addStretch(1)
        self.body_layout.addWidget(self.key_area, 0, Qt.AlignmentFlag.AlignTop)

        # Right Column: Action Editor
        self.editor = QWidget()
        self.editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        editor_layout = QVBoxLayout(self.editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(14)

        self.selected_title = QLabel("Key .")
        self.selected_title.setStyleSheet("color: #FFFFFF; font-size: 20px; font-weight: 700; background: transparent;")
        self.selected_subtitle = QLabel("Hotkey action")
        self.selected_subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.50); font-size: 12px; font-weight: 400; background: transparent; margin-bottom: 2px;")
        editor_layout.addWidget(self.selected_title)
        editor_layout.addWidget(self.selected_subtitle)

        # 2-Row Action Type Selectors
        chips_layout = QVBoxLayout()
        chips_layout.setSpacing(8)
        chips_layout.setContentsMargins(0, 0, 0, 0)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        for index, (action_type, label) in enumerate(ACTION_TYPES):
            chip = ActionChip(action_type, label, self.theme)
            chip.chosen.connect(self.select_action_type)
            self.action_buttons[action_type] = chip
            if index < 5:
                row1.addWidget(chip)
            else:
                row2.addWidget(chip)
        row1.addStretch(1)
        row2.addStretch(1)
        chips_layout.addLayout(row1)
        chips_layout.addLayout(row2)
        editor_layout.addLayout(chips_layout)

        # Form Fields
        self.form_content = QWidget()
        self.form_layout = QVBoxLayout(self.form_content)
        self.form_layout.setContentsMargins(0, 8, 0, 4)
        self.form_layout.setSpacing(10)

        self.name_label = QLabel("Name")
        self.name_label.setStyleSheet("color: rgba(255, 255, 255, 0.50); font-size: 12px; font-weight: 500; background: transparent;")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Lock")
        self.form_layout.addWidget(self.name_label)
        self.form_layout.addWidget(self.name_input)

        self.value_label = QLabel("Shortcut")
        self.value_label.setStyleSheet("color: rgba(255, 255, 255, 0.50); font-size: 12px; font-weight: 500; background: transparent;")
        value_row = QHBoxLayout()
        value_row.setSpacing(8)
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("Win+L")
        value_row.addWidget(self.value_input, 1)
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_file)
        self.browse_button.hide()
        value_row.addWidget(self.browse_button)
        self.form_layout.addWidget(self.value_label)
        self.form_layout.addLayout(value_row)

        self.browser_label = QLabel("Open with")
        self.browser_label.setStyleSheet("color: rgba(255, 255, 255, 0.50); font-size: 12px; font-weight: 500; background: transparent;")
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["Default Browser", "Google Chrome", "Mozilla Firefox", "Microsoft Edge", "Brave Browser"])
        self.browser_label.hide()
        self.browser_combo.hide()
        self.form_layout.addWidget(self.browser_label)
        self.form_layout.addWidget(self.browser_combo)

        self.capture_label = QLabel("Capture area")
        self.capture_label.setStyleSheet("color: rgba(255, 255, 255, 0.50); font-size: 12px; font-weight: 500; background: transparent;")
        self.capture_combo = QComboBox()
        self.capture_combo.addItems(["Full Screen", "Primary Monitor", "Active Window"])
        self.capture_label.hide()
        self.capture_combo.hide()
        self.form_layout.addWidget(self.capture_label)
        self.form_layout.addWidget(self.capture_combo)

        self.ptt_note = QLabel("Hold this key to dictate into the active text field.")
        self.ptt_note.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 11px; background: transparent;")
        self.ptt_note.hide()
        self.form_layout.addWidget(self.ptt_note)

        editor_layout.addWidget(self.form_content)

        # Bottom Buttons
        actions = QHBoxLayout()
        actions.setSpacing(16)
        self.save_button = QPushButton("Save changes")
        self.save_button.setObjectName("primaryButton")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.clicked.connect(self.save_current_action)
        actions.addWidget(self.save_button)

        self.clear_key_button = QPushButton("Clear key")
        self.clear_key_button.setObjectName("destructiveAction")
        self.clear_key_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_key_button.clicked.connect(self.reset_current_action)
        actions.addWidget(self.clear_key_button)

        actions.addStretch(1)
        editor_layout.addLayout(actions)
        editor_layout.addStretch(1)

        self.body_layout.addWidget(self.editor, 1, Qt.AlignmentFlag.AlignTop)
        root.addLayout(self.body_layout, 1)

        self._set_tab_order()

    def _add_tile(self, grid, pos_id, number, secondary, row, column, wide=False):
        tile = KeyTile(pos_id, number, secondary, self.theme, wide=wide)
        tile.set_action(self.config.get_action(pos_id))
        tile.selected.connect(self.select_key)
        self.buttons[pos_id] = tile
        grid.addWidget(tile, row, column, 1, 2 if wide else 1)

    def _set_tab_order(self):
        controls = [*self.buttons.values(), *self.action_buttons.values(), self.name_input,
                    self.value_input, self.browser_combo, self.capture_combo, self.browse_button,
                    self.save_button, self.clear_key_button]
        for first, second in zip(controls, controls[1:]):
            QWidget.setTabOrder(first, second)

    def _apply_theme(self):
        theme = self.theme
        font_family = interface_font_family()
        self.setStyleSheet(stylesheet_tokens(f"""
            QWidget#glassMain {{ background: {theme.bg}; color: {theme.text}; font-family: '{font_family}'; font-size: 12px; }}
            QWidget {{ color: {theme.text}; font-family: '{font_family}'; }}
            QLineEdit, QComboBox {{
                background: #0E1017;
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 10px 14px;
                min-height: 20px;
                font-size: 13px;
                selection-background-color: #A855F7;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid #A855F7;
            }}
            QComboBox QAbstractItemView {{
                background: #12141E;
                color: #FFFFFF;
                selection-background-color: rgba(255, 255, 255, 0.10);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }}
            QPushButton#primaryButton {{
                color: #FFFFFF;
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.20);
                border-radius: 8px;
                font-weight: 500;
                font-size: 13px;
                padding: 8px 18px;
            }}
            QPushButton#primaryButton:hover {{
                background: rgba(255, 255, 255, 0.14);
            }}
            QPushButton#flatAction {{
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.75);
                font-size: 13px;
                padding: 8px 12px;
            }}
            QPushButton#flatAction:hover {{
                color: #FFFFFF;
            }}
            QPushButton#destructiveAction {{
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.75);
                font-size: 13px;
                padding: 8px 12px;
            }}
            QPushButton#destructiveAction:hover {{
                color: #FF5555;
            }}
        """))
        for chip in self.action_buttons.values():
            chip.set_theme(theme)
        for tile in self.buttons.values():
            tile.set_theme(theme)
        self.set_numlock_state(getattr(self, "_macros_active", False), animate=False)
        self.update()

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.fillRect(self.rect(), token_color(self.theme.bg))
        painter.end()

    def resizeEvent(self, a0):
        super().resizeEvent(a0)

    def set_numlock_state(self, macros_active: bool, animate: bool = True):
        self._macros_active = macros_active
        on = self._macros_active
        dot = "●"
        state_text = "NumLock off, macros on" if on else "NumLock on, macros off"
        dot_color = self.theme.on if on else self.theme.off
        self.status_button.setText(f"{dot}  {state_text}")
        self.status_button.setStyleSheet(f"""
            QPushButton#statusButton {{
                color: {dot_color};
                background: transparent;
                border: none;
                font-size: 12px;
                font-weight: 500;
                padding: 4px 6px;
            }}
            QPushButton#statusButton:hover {{
                background: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }}
        """)
        for tile in self.buttons.values():
            tile.set_macro_active(on)

    def _toggle_or_preview_status(self):
        if self.toast:
            self.toast.show_state(self._macros_active)

    def set_key_recording(self, pos_id: str, recording: bool):
        if pos_id in self.buttons:
            self.buttons[pos_id].set_recording(recording)

    def trigger_physical_key_press(self, pos_id: str):
        action = self.config.get_action(pos_id)
        if action or self.test_mode:
            self.key_pressed_signal.emit(pos_id, action or {"type": "test", "value": "Test trigger"})

    def _handle_key_feedback(self, pos_id: str, action: dict):
        tile = self.buttons.get(pos_id)
        if tile and self.isVisible():
            tile.animateClick()
            for key, button in self.buttons.items():
                button.set_selected(key == pos_id)

    def set_appearance(self, appearance: str):
        self.appearance = appearance
        self.theme = theme_for(appearance)
        self._apply_theme()
        if self.toast and hasattr(self.toast, "set_theme"):
            self.toast.set_theme(self.theme)

    def select_key(self, pos_id: str):
        if pos_id not in self.buttons:
            return
        self.selected_key = pos_id
        for key, tile in self.buttons.items():
            tile.set_selected(key == pos_id)
        number = pos_id.replace("num", "").replace("dot", ".")
        self.selected_title.setText(f"Key {number}")
        action = self.config.get_action(pos_id)
        self.buttons[pos_id].set_action(action)
        if action:
            action_type = action.get("type", "website")
            self.select_action_type(action_type, update_fields=False)
            self.name_input.setText(action.get("desc", ""))
            value = str(action.get("value", ""))
            if action_type == "website" and "|" in value:
                browser, value = value.split("|", 1)
                browser_names = {"default": "Default Browser", "chrome": "Google Chrome", "firefox": "Mozilla Firefox", "edge": "Microsoft Edge", "brave": "Brave Browser"}
                self.browser_combo.setCurrentText(browser_names.get(browser, "Default Browser"))
            elif action_type in ("screenshot", "screenrec"):
                self.capture_combo.setCurrentText(REVERSE_MODE_MAP.get(value.split("|")[0], "Full Screen"))
            self.value_input.setText(value if action_type not in ("ptt", "screenshot", "screenrec") else "")
        else:
            self.name_input.clear()
            self.value_input.clear()
            self.browser_combo.setCurrentText("Default Browser")
            self.capture_combo.setCurrentText("Full Screen")
            self.select_action_type("hotkey", update_fields=False)

    def select_action_type(self, action_type: str, update_fields: bool = True):
        if action_type not in self.action_buttons:
            action_type = "hotkey"
        self.current_action_type = action_type
        for key, chip in self.action_buttons.items():
            blocker = QSignalBlocker(chip)
            chip.setChecked(key == action_type)
            del blocker
            chip.update()

        self.selected_subtitle.setText(ACTION_SUBTITLES.get(action_type, "Hotkey action"))

        is_web = action_type == "website"
        is_capture = action_type in ("screenshot", "screenrec")
        is_ptt = action_type == "ptt"
        is_file = action_type in ("launch", "script")

        self.value_label.setText({
            "website": "Website URL", "hotkey": "Shortcut", "launch": "Application path",
            "script": "Script path", "screenshot": "Capture area", "screenrec": "Recording area",
            "volume": "Volume command", "brightness": "Brightness command",
        }.get(action_type, "Shortcut"))
        self.value_input.setPlaceholderText({
            "website": "https://github.com", "hotkey": "Win+L", "launch": "Choose an application",
            "script": "Choose a script", "volume": "up or down", "brightness": "up or down",
        }.get(action_type, ""))
        self.value_label.setVisible(not is_capture and not is_ptt)
        self.value_input.setVisible(not is_capture and not is_ptt)
        self.browse_button.setVisible(is_file)
        self.browser_label.setVisible(is_web)
        self.browser_combo.setVisible(is_web)
        self.capture_label.setVisible(is_capture)
        self.capture_combo.setVisible(is_capture)
        self.ptt_note.setVisible(is_ptt)
        if update_fields:
            self.value_input.clear()

    def save_current_action(self):
        action_type = self.current_action_type
        if action_type == "website":
            browser_ids = {"Default Browser": "default", "Google Chrome": "chrome", "Mozilla Firefox": "firefox", "Microsoft Edge": "edge", "Brave Browser": "brave"}
            value = f"{browser_ids.get(self.browser_combo.currentText(), 'default')}|{self.value_input.text().strip()}"
        elif action_type == "ptt":
            value = "base"
        elif action_type in ("screenshot", "screenrec"):
            value = MODE_MAP.get(self.capture_combo.currentText(), "fullscreen")
        else:
            value = self.value_input.text().strip()

        action = {"type": action_type, "value": value}
        name = self.name_input.text().strip()
        if not name and action_type == "website":
            from ui.tiles import extract_website_name
            name = extract_website_name(value)
        if name:
            action["desc"] = name
        self.config.set_action(self.selected_key, action)
        self.config.save()
        self.buttons[self.selected_key].set_action(action)
        self.select_key(self.selected_key)
        if self.toast:
            self.toast.show_saved()
        if action_type == "ptt" and self.ptt:
            self.ptt.preload()

    def reset_current_action(self):
        self.config.set_action(self.selected_key, None)
        self.config.save()
        self.select_key(self.selected_key)
        if self.toast:
            self.toast.show_toast("Key cleared", f"Key {self.selected_key.replace('num', '')} is empty", duration_ms=1400)

    def clear_all_bindings(self):
        answer = QMessageBox.question(
            self, "Clear all keys?", "This removes all 11 key assignments.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Ok:
            return
        for pos_id in KEY_LABELS:
            self.config.set_action(pos_id, None)
        self.config.save()
        for tile in self.buttons.values():
            tile.set_action(None)
        self.select_key(self.selected_key)

    def browse_file(self):
        script = self.current_action_type == "script"
        file_filter = "Scripts (*.ps1 *.bat *.cmd *.py);;All Files (*.*)" if script else "Executables (*.exe);;All Files (*.*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select target file", "", file_filter)
        if path:
            self.value_input.setText(os.path.normpath(path))

    def preview_ptt(self):
        if self.toast and hasattr(self.toast, "preview_ptt"):
            self.toast.preview_ptt()

    def open_settings(self):
        dialog = SettingsDialog(self.config, self.theme, self)
        dialog.appearance_changed.connect(self.set_appearance)
        dialog.exec()

    def _set_test_mode(self, enabled: bool):
        self.test_mode = enabled
        if enabled and self.toast:
            self.toast.show_toast("Test mode", "Key feedback is enabled", duration_ms=1400)

    def _update_bound_count(self):
        if self.bound_count is not None:
            count = sum(1 for pos_id in KEY_LABELS if self.config.get_action(pos_id))
            self.bound_count.setText(f"{count} of 11 assigned")


class SettingsDialog(QDialog):
    appearance_changed = pyqtSignal(str)

    def __init__(self, config: Config, theme: ThemeTokens, parent=None):
        super().__init__(parent)
        self.config = config
        self.theme = theme
        self.setWindowTitle("KeySpark settings")
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        title = QLabel("Appearance & notifications")
        title.setStyleSheet(stylesheet_tokens(f"font-size: 16px; font-weight: 600; color: {theme.text};"))
        layout.addWidget(title)

        layout.addWidget(QLabel("Window theme"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Glass", "glass")
        self.theme_combo.addItem("Classic", "neo")
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(config.get_setting("theme", "glass"))))
        self.theme_combo.currentIndexChanged.connect(self._save_theme)
        layout.addWidget(self.theme_combo)
        self.restart_note = QLabel("Classic theme takes effect when the app is restarted.")
        self.restart_note.setObjectName("helperText")
        layout.addWidget(self.restart_note)

        layout.addWidget(QLabel("Light or dark appearance"))
        self.appearance_combo = QComboBox()
        for value, label in (("system", "Follow Windows"), ("dark", "Dark"), ("light", "Light")):
            self.appearance_combo.addItem(label, value)
        self.appearance_combo.setCurrentIndex(max(0, self.appearance_combo.findData(config.get_setting("appearance", "system"))))
        self.appearance_combo.currentIndexChanged.connect(self._save_appearance)
        layout.addWidget(self.appearance_combo)

        self.notify_toggle = QCheckBox("Show a notice when NumLock changes")
        self.notify_toggle.setChecked(bool(config.get_setting("notify_on_toggle", True)))
        self.notify_toggle.toggled.connect(lambda value: self._save_option("notify_on_toggle", value))
        layout.addWidget(self.notify_toggle)
        self.sound_toggle = QCheckBox("Play a sound with NumLock notices")
        self.sound_toggle.setChecked(bool(config.get_setting("notify_sound", False)))
        self.sound_toggle.toggled.connect(lambda value: self._save_option("notify_sound", value))
        layout.addWidget(self.sound_toggle)
        layout.addStretch(1)
        close = QPushButton("Done")
        close.setObjectName("primaryButton")
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
        self.setStyleSheet(stylesheet_tokens(f"QDialog {{ background: {theme.bg}; color: {theme.text}; }} QLabel#helperText {{ color: {theme.text_dim}; font-size: 11px; }}"))

    def _save_theme(self):
        self.config.set_setting("theme", self.theme_combo.currentData())
        self.config.save()

    def _save_appearance(self):
        appearance = self.appearance_combo.currentData()
        self.config.set_setting("appearance", appearance)
        self.config.save()
        self.appearance_changed.emit(appearance)

    def _save_option(self, key: str, value: bool):
        self.config.set_setting(key, value)
        self.config.save()
