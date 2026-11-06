"""Painted, accessible numpad key tiles."""
from __future__ import annotations

import os

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, pyqtSignal
from PyQt6.QtCore import pyqtProperty  # type: ignore[attr-defined]
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QPushButton

from ui.glass import paint_glass_surface
from ui.icons import icon_pixmap
from ui.theme import DARK, ThemeTokens, mono_font_family, token_color


ACTION_LABELS = {
    "website": "Website", "hotkey": "Hotkey", "launch": "Application",
    "script": "Script", "ptt": "Speech to text", "screenshot": "Screenshot",
    "screenrec": "Screen recording",
}

KNOWN_WEBSITES = {
    "mail.google.com": "Gmail",
    "gemini.google.com": "Gemini",
    "docs.google.com": "Google Docs",
    "drive.google.com": "Google Drive",
    "calendar.google.com": "Google Calendar",
    "maps.google.com": "Google Maps",
    "console.cloud.google.com": "Google Cloud",
    "music.youtube.com": "YouTube Music",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "chatgpt.com": "ChatGPT",
    "chat.openai.com": "ChatGPT",
    "claude.ai": "Claude",
    "instagram.com": "Instagram",
    "github.com": "GitHub",
    "gitlab.com": "GitLab",
    "reddit.com": "Reddit",
    "twitter.com": "Twitter",
    "x.com": "X",
    "spotify.com": "Spotify",
    "discord.com": "Discord",
    "discord.gg": "Discord",
    "twitch.tv": "Twitch",
    "netflix.com": "Netflix",
    "linkedin.com": "LinkedIn",
    "facebook.com": "Facebook",
    "amazon.com": "Amazon",
    "whatsapp.com": "WhatsApp",
    "telegram.org": "Telegram",
    "t.me": "Telegram",
    "figma.com": "Figma",
    "notion.so": "Notion",
    "slack.com": "Slack",
    "stackoverflow.com": "Stack Overflow",
    "news.ycombinator.com": "Hacker News",
    "wikipedia.org": "Wikipedia",
    "portal.azure.com": "Azure",
    "console.aws.amazon.com": "AWS",
    "supabase.com": "Supabase",
}


def extract_website_name(val: str) -> str:
    """Extract a human-friendly website name from a URL or browser|URL string."""
    if "|" in val:
        _, val = val.split("|", 1)
    val = val.strip()
    if not val:
        return "Website"
    if not val.startswith(("http://", "https://")):
        val = "https://" + val
    try:
        import urllib.parse
        parsed = urllib.parse.urlparse(val)
        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if host in KNOWN_WEBSITES:
            return KNOWN_WEBSITES[host]
        for k, name in KNOWN_WEBSITES.items():
            if host.endswith("." + k):
                return name
        host = host.split(":")[0]
        parts = host.split(".")
        if len(parts) >= 2:
            if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "net", "edu", "gov"):
                name_part = parts[-3]
            else:
                name_part = parts[-2]
            return name_part.replace("-", " ").replace("_", " ").title()
        return host.title() or "Website"
    except Exception:
        return "Website"


class KeyTile(QPushButton):
    selected = pyqtSignal(str)

    def __init__(self, pos_id: str, number: str, secondary: str, theme: ThemeTokens = DARK, wide: bool = False, parent=None):
        super().__init__(parent)
        self.pos_id = pos_id
        self.number = number
        self.secondary = secondary
        self.theme = theme
        self._glass_cache = QPixmap()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.action: dict | None = None
        self.label = "Empty"
        self.value = ""
        self._hover_progress = 0.0
        self._press_progress = 0.0
        self._active_glow = 0.0
        self._selected = False
        self._macro_active = True
        self._hover_animation = self._animation(b"hoverProgress", 0.0, 1.0, 120, QEasingCurve.Type.OutCubic)
        self._press_animation = self._animation(b"pressProgress", 0.0, 1.0, 90, QEasingCurve.Type.OutQuad)
        self._release_animation = self._animation(b"pressProgress", 1.0, 0.0, 200, QEasingCurve.Type.OutBack)
        self._pulse_animation = self._animation(b"activeGlow", 0.15, 1.0, 700, QEasingCurve.Type.InOutSine)
        self._pulse_animation.setLoopCount(-1)

        self.setFixedSize(176 if wide else 84, 84)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.clicked.connect(lambda: self.selected.emit(self.pos_id))
        self.pressed.connect(self._pressed)
        self.released.connect(self._released)
        self.setAccessibleName(f"Key {number}")
        self.setToolTip(f"Key {number} · {secondary}\nEmpty")

    def _animation(self, property_name: bytes, start, end, duration: int, easing: QEasingCurve.Type):
        animation = QPropertyAnimation(self, property_name, self)
        animation.setDuration(duration)
        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.setEasingCurve(easing)
        return animation

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, value):
        self._hover_progress = float(value)
        self.update()

    hoverProgress = pyqtProperty(float, get_hover_progress, set_hover_progress)

    def get_press_progress(self):
        return self._press_progress

    def set_press_progress(self, value):
        self._press_progress = float(value)
        self.update()

    pressProgress = pyqtProperty(float, get_press_progress, set_press_progress)

    def get_active_glow(self):
        return self._active_glow

    def set_active_glow(self, value):
        self._active_glow = float(value)
        self.update()

    activeGlow = pyqtProperty(float, get_active_glow, set_active_glow)

    def set_action(self, action: dict | None):
        self.action = action
        if action:
            action_type = action.get("type", "")
            desc = (action.get("desc") or "").strip()
            if not desc or desc.lower() == "website":
                if action_type == "website":
                    desc = extract_website_name(action.get("value", ""))
                else:
                    desc = ACTION_LABELS.get(action_type, "Action")
            self.label = desc
            self.value = self._value_summary(action_type, action.get("value", ""), bool(action.get("desc")))
            name = f"Key {self.number}, {self.label}"
            if self.value:
                name += f", {self.value}"
            self.setAccessibleName(name)
            self.setToolTip(f"Key {self.number} · {self.secondary}\n{self.label}" + (f"\n{self.value}" if self.value else ""))
        else:
            self.label = "Empty"
            self.value = ""
            self.setAccessibleName(f"Key {self.number}, Empty")
            self.setToolTip(f"Key {self.number} · {self.secondary}\nEmpty")
        self.update()

    @staticmethod
    def _value_summary(action_type: str, value: str, has_name: bool) -> str:
        if action_type == "website":
            if "|" in value:
                _, value = value.split("|", 1)
            return value.replace("https://", "").replace("http://", "").replace("www.", "")
        if action_type in ("launch", "script"):
            return os.path.basename(value)
        if action_type == "hotkey":
            return value or "Shortcut"
        if action_type == "ptt":
            return "Hold to speak"
        if action_type in ("screenshot", "screenrec"):
            return value.split("|")[0].replace("_", " ").title() or "Full screen"
        return value

    def set_selected(self, selected: bool):
        if self._selected == selected:
            return
        self._selected = selected
        self.update()

    def set_macro_active(self, active: bool):
        self._macro_active = active
        self.update()

    def set_recording(self, recording: bool):
        if recording:
            self._pulse_animation.start()
        else:
            self._pulse_animation.stop()
            self._active_glow = 0.0
        self.update()

    def enterEvent(self, event):
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(1.0)
        self._hover_animation.start()
        super().enterEvent(event)

    def leaveEvent(self, a0):
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(0.0)
        self._hover_animation.start()
        super().leaveEvent(a0)

    def _pressed(self):
        self._release_animation.stop()
        self._press_animation.start()

    def _released(self):
        self._press_animation.stop()
        self._release_animation.setStartValue(self._press_progress)
        self._release_animation.start()

    def set_theme(self, theme: ThemeTokens):
        self.theme = theme
        self.update()

    def _get_icon_name(self) -> str:
        if not self.action:
            return "add"
        t = self.action.get("type", "")
        desc = (self.action.get("desc") or "").lower()
        val = str(self.action.get("value", "")).lower()
        full_text = f"{desc} {val}"
        if "github" in full_text:
            return "github"
        if "youtube" in full_text or "youtu.be" in full_text:
            return "youtube"
        if "chatgpt" in full_text or "openai" in full_text:
            return "chatgpt"
        if "google" in full_text or "gemini" in full_text:
            return "google"
        if "discord" in full_text:
            return "discord"
        if "reddit" in full_text:
            return "reddit"
        if "spotify" in full_text:
            return "spotify"
        if "twitter" in full_text or "x.com" in full_text:
            return "twitter"
        if "twitch" in full_text:
            return "twitch"
        if "vscode" in full_text or "vs code" in full_text or "code" in desc:
            return "vscode"
        if "deploy" in full_text or "terminal" in full_text:
            return "deploy"
        if "dictate" in full_text or t == "ptt":
            return "ptt"
        if "capture" in full_text or t == "screenshot":
            return "screenshot"
        if "record" in full_text or t == "screenrec":
            return "screenrec"
        if "volume down" in full_text or (t == "volume" and ("down" in val or "down" in desc or "-" in val)):
            return "volume-down"
        if "volume up" in full_text or t == "volume":
            return "volume-up"
        if "brightness" in full_text or t == "brightness":
            return "brightness"
        if "lock" in full_text or (t == "hotkey" and "win+l" in val):
            return "hotkey"
        if "paste" in full_text:
            return "hotkey"
        if t == "website":
            return "link"
        if t == "hotkey":
            return "hotkey"
        if t == "launch":
            return "launch"
        if t == "script":
            return "script"
        return t or "link"

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale = 1.0 - self._press_progress * 0.03
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(scale, scale)
        painter.translate(-self.width() / 2, -self.height() / 2)

        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        radius = 14.0

        # Background and border
        if self._selected:
            painter.setPen(QPen(QColor("#A855F7"), 1.5))
            painter.setBrush(QColor(168, 85, 247, 20))
        elif self._hover_progress > 0.05:
            painter.setPen(QPen(QColor(255, 255, 255, 38), 1.0))
            painter.setBrush(QColor(255, 255, 255, 14))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 20), 1.0))
            painter.setBrush(QColor(255, 255, 255, 9))
        painter.drawRoundedRect(rect, radius, radius)

        # Key number in top right
        top_font = QFont(self.font())
        top_font.setPointSize(9)
        top_font.setWeight(QFont.Weight.Normal)
        painter.setFont(top_font)
        painter.setPen(QColor(255, 255, 255, 95))
        painter.drawText(QRectF(rect.right() - 22, 7, 16, 14), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.number)

        # Accent and colors
        if self._selected:
            icon_color = "#C084FC"
            text_color = QColor("#FFFFFF")
        elif self.action:
            icon_color = "rgba(255,255,255,0.85)"
            text_color = QColor(255, 255, 255, 215)
        else:
            icon_color = "rgba(255,255,255,0.30)"
            text_color = QColor(255, 255, 255, 75)

        if not self._macro_active:
            icon_color = "rgba(255,255,255,0.40)"
            text_color = QColor(255, 255, 255, 100)

        # Center icon
        icon_name = self._get_icon_name()
        glyph = icon_pixmap(icon_name, icon_color, 24)
        if glyph.isNull() and not self.action:
            glyph = self._plus_icon(icon_color)
        if not glyph.isNull():
            cx = int(rect.center().x())
            painter.drawPixmap(cx - int(glyph.width() / 2), 20, glyph)

        # Centered label below icon
        font = QFont(self.font())
        font.setPointSize(9)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(text_color)
        display_label = self.label if self.action else ""
        label_rect = QRectF(6, 52, rect.width() - 12, 18)
        elided = painter.fontMetrics().elidedText(display_label, Qt.TextElideMode.ElideRight, int(label_rect.width()))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, elided)

        painter.end()

    def _plus_icon(self, color: str) -> QPixmap:
        from PyQt6.QtGui import QPainter, QPen
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(token_color(color), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(12, 6, 12, 18)
        painter.drawLine(6, 12, 18, 12)
        painter.end()
        return pixmap
