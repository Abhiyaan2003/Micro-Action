"""Minimal-glass main window and action editor."""
from __future__ import annotations

import os

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QSignalBlocker, Qt, pyqtSignal
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
from ui.theme import DARK, ThemeTokens, interface_font_family, theme_for
from ui.tiles import KeyTile


ACTION_TYPES = [
    ("website", "Web"), ("hotkey", "Hotkey"), ("launch", "Application"),
    ("script", "Script"), ("ptt", "Push-to-talk"), ("screenshot", "Screenshot"),
    ("screenrec", "Record"),
]


class GlassNumpadEditor(QWidget):
    key_pressed_signal = pyqtSignal(str, dict)
    appearance_changed = pyqtSignal(str)

    def __init__(self, config: Config, ptt=None, notification_overlay=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.ptt = ptt
        self.toast = notification_overlay
        if self.toast is None:
            from ui.overlays import OverlayPill
            self.toast = OverlayPill(config.get_setting("appearance", "system"))
        self.appearance = config.get_setting("appearance", "system")
        self.theme: ThemeTokens = theme_for(self.appearance)
        self.selected_key = "num5"
        self.current_action_type = "website"
        self.buttons: dict[str, KeyTile] = {}
        self.action_buttons: dict[str, ActionChip] = {}
        self.test_mode = False

        self.setObjectName("glassMain")
        self.setWindowTitle("Micro Action")
        self.setMinimumSize(720, 640)
        self.resize(1040, 760)
        self._build_ui()
        self.key_pressed_signal.connect(self._handle_key_feedback)
        self._apply_theme()
        self.select_key(self.selected_key)
        self.set_numlock_state(False)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(18)

        header = QHBoxLayout()
        header.setSpacing(12)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        self.title = QLabel("Micro Action")
        self.title.setObjectName("appTitle")
        self.subtitle = QLabel("A key map for the numpad you already own")
        self.subtitle.setObjectName("appSubtitle")
        title_stack.addWidget(self.title)
        title_stack.addWidget(self.subtitle)
        header.addLayout(title_stack)
        header.addStretch(1)

        self.status_button = QPushButton()
        self.status_button.setObjectName("statusButton")
        self.status_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.status_button.setCursor(Qt.CursorShape.ArrowCursor)
        self.status_button.setMinimumHeight(34)
        self.status_button.setAccessibleName("Current NumLock mode; status only")
        header.addWidget(self.status_button)

        self.settings_button = QToolButton()
        self.settings_button.setText("Settings")
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.clicked.connect(self.open_settings)
        header.addWidget(self.settings_button)
        root.addLayout(header)

        self.body_layout = QHBoxLayout()
        self.body_layout.setSpacing(40)
        self.key_area = QWidget()
        self.key_area.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        key_layout = QVBoxLayout(self.key_area)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(12)

        map_header = QHBoxLayout()
        map_titles = QVBoxLayout()
        map_titles.setSpacing(2)
        self.map_title = QLabel("Key map")
        self.map_title.setObjectName("sectionTitle")
        self.map_hint = QLabel("Select a key to edit its action")
        self.map_hint.setObjectName("helperText")
        map_titles.addWidget(self.map_title)
        map_titles.addWidget(self.map_hint)
        map_header.addLayout(map_titles)
        map_header.addStretch(1)
        self.bound_count = QLabel("0 of 11 assigned")
        self.bound_count.setObjectName("helperText")
        map_header.addWidget(self.bound_count, 0, Qt.AlignmentFlag.AlignVCenter)
        key_layout.addLayout(map_header)

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

        self.grid_effect = QGraphicsOpacityEffect(self.key_grid)
        self.grid_effect.setOpacity(1.0)
        self.key_grid.setGraphicsEffect(self.grid_effect)
        self._grid_fade = QPropertyAnimation(self.grid_effect, b"opacity", self)
        self._grid_fade.setDuration(250)
        self._grid_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        key_layout.addWidget(self.key_grid)

        self.key_footer = QHBoxLayout()
        self.key_footer.setSpacing(14)
        self.clear_all_button = QPushButton("Clear all")
        self.clear_all_button.setObjectName("destructiveText")
        self.clear_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_all_button.clicked.connect(self.clear_all_bindings)
        self.key_footer.addWidget(self.clear_all_button)
        self.key_footer.addStretch(1)
        self.test_toggle = QCheckBox("Test mode")
        self.test_toggle.setToolTip("Show key feedback while editing")
        self.test_toggle.toggled.connect(self._set_test_mode)
        self.key_footer.addWidget(self.test_toggle)
        key_layout.addLayout(self.key_footer)
        self.body_layout.addWidget(self.key_area, 0, Qt.AlignmentFlag.AlignTop)

        self.editor = QFrame()
        self.editor.setObjectName("editorPanel")
        self.editor.setMaximumWidth(420)
        self.editor.setMinimumWidth(340)
        self.editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        editor_layout = QVBoxLayout(self.editor)
        editor_layout.setContentsMargins(20, 18, 20, 18)
        editor_layout.setSpacing(12)

        self.selected_title = QLabel("Key 5")
        self.selected_title.setObjectName("sectionTitle")
        self.selected_subtitle = QLabel("Numpad 5 · Clear")
        self.selected_subtitle.setObjectName("helperText")
        editor_layout.addWidget(self.selected_title)
        editor_layout.addWidget(self.selected_subtitle)

        self.chip_grid = QGridLayout()
        self.chip_grid.setHorizontalSpacing(6)
        self.chip_grid.setVerticalSpacing(4)
        for index, (action_type, label) in enumerate(ACTION_TYPES):
            chip = ActionChip(action_type, label, self.theme)
            chip.chosen.connect(self.select_action_type)
            self.action_buttons[action_type] = chip
            self.chip_grid.addWidget(chip, index // 3, index % 3)
        editor_layout.addLayout(self.chip_grid)

        self.form_scroll = QScrollArea()
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.form_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.form_content = QWidget()
        self.form_layout = QVBoxLayout(self.form_content)
        self.form_layout.setContentsMargins(0, 4, 4, 4)
        self.form_layout.setSpacing(10)

        self.name_label = QLabel("Name")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Open editor")
        self.form_layout.addWidget(self.name_label)
        self.form_layout.addWidget(self.name_input)

        self.value_label = QLabel("Website URL")
        value_row = QHBoxLayout()
        value_row.setSpacing(8)
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("example.com")
        value_row.addWidget(self.value_input, 1)
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_file)
        value_row.addWidget(self.browse_button)
        self.form_layout.addWidget(self.value_label)
        self.form_layout.addLayout(value_row)

        self.browser_label = QLabel("Open with")
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["Default Browser", "Google Chrome", "Mozilla Firefox", "Microsoft Edge", "Brave Browser"])
        self.form_layout.addWidget(self.browser_label)
        self.form_layout.addWidget(self.browser_combo)

        self.capture_label = QLabel("Capture area")
        self.capture_combo = QComboBox()
        self.capture_combo.addItems(["Full Screen", "Primary Monitor", "Active Window"])
        self.form_layout.addWidget(self.capture_label)
        self.form_layout.addWidget(self.capture_combo)

        self.ptt_note = QLabel("Hold this key to dictate into the active text field.")
        self.ptt_note.setObjectName("helperText")
        self.form_layout.addWidget(self.ptt_note)
        self.form_layout.addStretch(1)

        self.form_scroll.setWidget(self.form_content)
        editor_layout.addWidget(self.form_scroll, 1)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.save_button = QPushButton("Save changes")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self.save_current_action)
        actions.addWidget(self.save_button)
        self.preview_ptt_button = QPushButton("Preview voice")
        self.preview_ptt_button.clicked.connect(self.preview_ptt)
        actions.addWidget(self.preview_ptt_button)
        self.clear_key_button = QPushButton("Clear key")
        self.clear_key_button.setObjectName("destructiveText")
        self.clear_key_button.clicked.connect(self.reset_current_action)
        actions.addWidget(self.clear_key_button)
        editor_layout.addLayout(actions)
        self.body_layout.addWidget(self.editor, 1, Qt.AlignmentFlag.AlignTop)
        self.body_layout.addStretch(1)
        root.addLayout(self.body_layout, 1)

        self._set_tab_order()

    def _add_tile(self, grid, pos_id, number, secondary, row, column, wide=False):
        tile = KeyTile(pos_id, number, secondary, self.theme, wide=wide)
        tile.selected.connect(self.select_key)
        self.buttons[pos_id] = tile
        grid.addWidget(tile, row, column, 1, 2 if wide else 1)

    def _set_tab_order(self):
        controls = [*self.buttons.values(), *self.action_buttons.values(), self.name_input,
                    self.value_input, self.browser_combo, self.capture_combo, self.browse_button,
                    self.save_button, self.preview_ptt_button, self.clear_key_button]
        for first, second in zip(controls, controls[1:]):
            QWidget.setTabOrder(first, second)

    def _apply_theme(self):
        theme = self.theme
        font_family = interface_font_family()
        self.setStyleSheet(f"""
            QWidget#glassMain {{ background: {theme.bg}; color: {theme.text}; font-family: '{font_family}'; font-size: 12px; }}
            QWidget {{ color: {theme.text}; }}
            QLabel#appTitle {{ color: {theme.text}; font-size: 18px; font-weight: 600; }}
            QLabel#appSubtitle, QLabel#helperText {{ color: {theme.text_dim}; font-size: 11px; }}
            QLabel#sectionTitle {{ color: {theme.text}; font-size: 15px; font-weight: 600; }}
            QFrame#editorPanel {{ background: {'#171A22' if theme.name == 'dark' else '#F7F8FC'}; border: none; border-radius: 20px; }}
            QLineEdit, QComboBox, QSpinBox {{ background: {theme.inset}; color: {theme.text}; border: none; border-radius: 10px; padding: 10px 12px; min-height: 20px; selection-background-color: {theme.actions['website']}; }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-bottom: 2px solid {theme.actions.get(self.current_action_type, theme.on)}; }}
            QComboBox QAbstractItemView {{ background: {'#1A1D27' if theme.name == 'dark' else '#F3F5FA'}; color: {theme.text}; selection-background-color: {theme.glass_hover}; border: 1px solid {theme.rim}; }}
            QPushButton {{ background: transparent; color: {theme.text_dim}; border: none; border-radius: 10px; padding: 8px 12px; min-height: 20px; }}
            QPushButton:hover {{ background: {theme.glass_hover}; color: {theme.text}; }}
            QPushButton:focus {{ outline: 2px solid {theme.actions.get(self.current_action_type, theme.off)}; }}
            QPushButton#primaryButton {{ color: {theme.text}; background: {theme.glass_hover}; border: 1px solid {theme.rim}; border-radius: 10px; font-weight: 600; }}
            QPushButton#primaryButton:hover {{ background: {theme.rim}; }}
            QPushButton#destructiveText {{ color: {theme.text_dim}; }}
            QPushButton#destructiveText:hover {{ color: {theme.danger}; background: {theme.glass}; }}
            QCheckBox {{ color: {theme.text_dim}; spacing: 7px; }}
            QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {theme.rim}; border-radius: 4px; background: {theme.inset}; }}
            QCheckBox::indicator:checked {{ background: {theme.on}; border-color: {theme.on}; }}
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ width: 6px; background: transparent; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {theme.rim}; border-radius: 3px; min-height: 24px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QPushButton#statusButton {{ color: {theme.text_dim}; background: {theme.pill}; border: 1px solid {theme.rim}; border-radius: 17px; padding: 4px 12px; }}
        """)
        for chip in self.action_buttons.values():
            chip.set_theme(theme)
        for tile in self.buttons.values():
            tile.set_theme(theme)
        self.set_numlock_state(getattr(self, "_macros_active", False), animate=False)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(self.theme.bg))
        center = self.rect().topLeft()
        radius = max(self.width(), self.height()) * 0.64
        glow = QRadialGradient(center, radius)
        glow.setColorAt(0.0, QColor(self.theme.bg_glow))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), glow)
        painter.end()

    def resizeEvent(self, event):
        narrow = self.width() < 760
        self.body_layout.setDirection(QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight)
        if narrow:
            self.key_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            self.editor.setMaximumWidth(420)
        else:
            self.key_area.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        super().resizeEvent(event)

    def set_numlock_state(self, macros_active: bool, animate: bool = True):
        self._macros_active = bool(macros_active)
        on = self._macros_active
        title = "NumLock off · macros on" if on else "NumLock on · macros off"
        self.status_button.setText(("●  " if on else "●  ") + title)
        self.status_button.setStyleSheet(
            f"QPushButton#statusButton {{ color: {self.theme.on if on else self.theme.off}; background: {self.theme.pill}; border: 1px solid {self.theme.rim}; border-radius: 17px; padding: 4px 12px; }}"
        )
        self.status_button.setToolTip("NumLock off activates mapped actions. NumLock on types numbers.")
        target = 1.0 if on else 0.4
        self._grid_fade.stop()
        if animate:
            self._grid_fade.setStartValue(self.grid_effect.opacity())
            self._grid_fade.setEndValue(target)
            self._grid_fade.start()
        else:
            self.grid_effect.setOpacity(target)
        for tile in self.buttons.values():
            tile.set_macro_active(on)

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
        self.selected_subtitle.setText(f"Numpad {number} · {KEY_SUB_LABELS.get(pos_id, '')}")
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
            self.select_action_type("website", update_fields=False)
        self._update_bound_count()

    def select_action_type(self, action_type: str, update_fields: bool = True):
        if action_type not in self.action_buttons:
            action_type = "website"
        self.current_action_type = action_type
        for key, chip in self.action_buttons.items():
            blocker = QSignalBlocker(chip)
            chip.setChecked(key == action_type)
            del blocker
            chip.update()

        is_web = action_type == "website"
        is_capture = action_type in ("screenshot", "screenrec")
        is_ptt = action_type == "ptt"
        is_file = action_type in ("launch", "script")
        self.value_label.setText({
            "website": "Website URL", "hotkey": "Keyboard shortcut", "launch": "Application path",
            "script": "Script path", "screenshot": "Capture scope", "screenrec": "Recording scope",
        }.get(action_type, "Value"))
        self.value_input.setPlaceholderText({
            "website": "example.com", "hotkey": "ctrl+shift+t", "launch": "Choose an application",
            "script": "Choose a script", "screenshot": "", "screenrec": "",
        }.get(action_type, "Enter a value"))
        self.value_label.setVisible(not is_capture and not is_ptt)
        self.value_input.setVisible(not is_capture and not is_ptt)
        self.browse_button.setVisible(is_file)
        self.browser_label.setVisible(is_web)
        self.browser_combo.setVisible(is_web)
        self.capture_label.setVisible(is_capture)
        self.capture_combo.setVisible(is_capture)
        self.ptt_note.setVisible(is_ptt)
        self.preview_ptt_button.setVisible(is_ptt)
        if update_fields:
            self.value_input.clear()
        self._apply_theme()

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
        if name:
            action["desc"] = name
        self.config.set_action(self.selected_key, action)
        self.config.save()
        self.buttons[self.selected_key].set_action(action)
        self._update_bound_count()
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
            QMessageBox.StandardButton.Clear | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Clear:
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
        count = sum(1 for pos_id in KEY_LABELS if self.config.get_action(pos_id))
        self.bound_count.setText(f"{count} of 11 assigned")


class SettingsDialog(QDialog):
    appearance_changed = pyqtSignal(str)

    def __init__(self, config: Config, theme: ThemeTokens, parent=None):
        super().__init__(parent)
        self.config = config
        self.theme = theme
        self.setWindowTitle("Micro Action settings")
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        title = QLabel("Appearance & notifications")
        title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {theme.text};")
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
        self.setStyleSheet(f"QDialog {{ background: {theme.bg}; color: {theme.text}; }} QLabel#helperText {{ color: {theme.text_dim}; font-size: 11px; }}")

    def _save_theme(self):
        self.config.set_setting("theme", self.theme_combo.currentData())
        self.config.save()

    def _save_appearance(self):
        appearance = self.appearance_combo.currentData()
        self.config.set_setting("appearance", appearance)
        self.config.save()
        self.appearance_changed.emit(appearance)

    def _save_option(self, key: str, value: bool):
        self.config.set_setting(key, bool(value))
        self.config.save()
