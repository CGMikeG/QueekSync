"""
Reusable Qt widgets for the QueekSync UI.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from ui_qt import theme as T


# ---------------------------------------------------------------------------
# Glass card
# ---------------------------------------------------------------------------

class GlassCard(QFrame):
    """Rounded, bordered card with the glass-dark look."""

    def __init__(self, parent: Optional[QWidget] = None, *, object_name: str = "GlassCard") -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self._hovered = False
        self._hover_enabled = False
        self._normal_border = T.BORDER
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def set_hover_border(self, enabled: bool = True) -> None:
        """Enable accent border highlight on mouse hover."""
        self._hover_enabled = enabled
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, enabled)
        self._hovered = False
        self._refresh_border()

    def _refresh_border(self) -> None:
        if self._hover_enabled and self._hovered:
            self.setProperty("hovered", True)
        else:
            self.setProperty("hovered", False)
        # Force style re-polish
        style = self.style()
        if style is not None:
            style.unpolish(self)
            style.polish(self)

    def enterEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._hover_enabled:
            self._hovered = True
            self._refresh_border()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        if self._hover_enabled:
            self._hovered = False
            self._refresh_border()
        super().leaveEvent(event)


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------

class SectionLabel(QLabel):
    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(text.upper(), parent)
        self.setObjectName("SectionTitle")


class MutedLabel(QLabel):
    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setProperty("muted", True)


class DimLabel(QLabel):
    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setProperty("dim", True)


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------

class PrimaryButton(QPushButton):
    def __init__(self, text: str, parent: Optional[QWidget] = None, command: Optional[Callable] = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("PrimaryButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if command:
            self.clicked.connect(command)


class GhostButton(QPushButton):
    def __init__(self, text: str, parent: Optional[QWidget] = None, command: Optional[Callable] = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("GhostButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if command:
            self.clicked.connect(command)


class DangerButton(QPushButton):
    def __init__(self, text: str, parent: Optional[QWidget] = None, command: Optional[Callable] = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("DangerButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if command:
            self.clicked.connect(command)


class IconButton(QPushButton):
    """Small ghost-style button for card actions (no emoji; unicode glyph ok)."""

    def __init__(self, text: str, parent: Optional[QWidget] = None, command: Optional[Callable] = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("IconButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(32, 30)
        if command:
            self.clicked.connect(command)


# ---------------------------------------------------------------------------
# Status badge
# ---------------------------------------------------------------------------

class StatusBadge(QLabel):
    def __init__(self, status: str = "never", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._status = status
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.setFont(font)
        self.setContentsMargins(8, 3, 8, 3)
        self.set_status(status)

    def _style(self) -> str:
        bg = T.STATUS_BG.get(self._status, T.STATUS_BG["never"])
        fg = T.STATUS_COLORS.get(self._status, T.STATUS_COLORS["never"])
        return f"background-color: {bg}; color: {fg}; border-radius: 10px; padding: 3px 10px;"

    def set_status(self, status: str) -> None:
        self._status = status
        label = T.STATUS_LABELS.get(status, status.capitalize())
        self.setText(f"  {label}  ")
        self.setStyleSheet(self._style())


# ---------------------------------------------------------------------------
# Separator
# ---------------------------------------------------------------------------

class HSeparator(QFrame):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background-color: {T.BORDER}; border: none;")


# ---------------------------------------------------------------------------
# Stat tile
# ---------------------------------------------------------------------------

class StatTile(GlassCard):
    def __init__(self, label: str, value: str = "0", color: str = T.ACCENT, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(150, 74)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 700;")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._value_label)

        lbl = MutedLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

    def set_value(self, value: str) -> None:
        self._value_label.setText(str(value))


# ---------------------------------------------------------------------------
# Labelled entry
# ---------------------------------------------------------------------------

class LabelledEntry(QWidget):
    """A label + QLineEdit stacked vertically."""

    def __init__(
        self,
        label: str,
        placeholder: str = "",
        show: str = "",
        tooltip: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        lbl = MutedLabel(label)
        layout.addWidget(lbl)

        self.entry = QLineEdit(self)
        self.entry.setPlaceholderText(placeholder)
        self.entry.setClearButtonEnabled(False)
        if show:
            self.entry.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.entry)

        if tooltip:
            lbl.setToolTip(tooltip)
            self.entry.setToolTip(tooltip)

    def get(self) -> str:
        return self.entry.text()

    def set(self, value: str) -> None:
        self.entry.setText(value)

    def set_entry_enabled(self, enabled: bool) -> None:
        self.entry.setEnabled(enabled)


# ---------------------------------------------------------------------------
# Log viewer
# ---------------------------------------------------------------------------

class LogViewer(QPlainTextEdit):
    """Read-only, colour-tagged log widget. Mouse wheel works natively."""

    MAX_LINES = 2000

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("LogViewer")
        self.setReadOnly(True)
        self.setMaximumBlockCount(self.MAX_LINES)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._formats: dict = {}
        for tag, color in T.LOG_COLORS.items():
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            self._formats[tag] = fmt

    def append(self, text: str, tag: str = "info") -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text + "\n", self._formats.get(tag, self._formats["info"]))
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear(self) -> None:
        super().clear()


# ---------------------------------------------------------------------------
# Progress bar (indeterminate-capable)
# ---------------------------------------------------------------------------

class ProgressBar(QProgressBar):
    def __init__(self, color: str = T.ACCENT, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setRange(0, 100)
        self.setValue(0)
        self.setTextVisible(False)
        self.setFixedHeight(6)
        self.setStyleSheet(
            f"QProgressBar {{ background-color: {T.BG_INPUT}; border: none; border-radius: 3px; }}"
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}"
        )
        self._timer: Optional[QTimer] = None
        self._indeterminate = False

    def start_indeterminate(self) -> None:
        self._indeterminate = True
        self.setRange(0, 0)  # busy indicator
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.timeout.connect(lambda: None)
        self._timer.start(100)

    def set_determinate(self, value: float) -> None:
        self.stop_indeterminate()
        self.setRange(0, 100)
        self.setValue(int(value * 100))

    def stop_indeterminate(self) -> None:
        self._indeterminate = False
        if self._timer is not None:
            self._timer.stop()
        self.setRange(0, 100)


# ---------------------------------------------------------------------------
# Colour picker
# ---------------------------------------------------------------------------

class ColourPicker(QWidget):
    COLOURS = [
        "#3b82f6", "#8b5cf6", "#14b8a6", "#22c55e",
        "#f97316", "#ef4444", "#ec4899", "#eab308",
    ]

    def __init__(
        self,
        on_select: Callable[[str], None],
        selected: str = "#3b82f6",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._on_select = on_select
        self._selected = selected
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._buttons: List[QPushButton] = []
        for colour in self.COLOURS:
            btn = QPushButton(self)
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {colour}; border-radius: 14px;"
                f" border: {'3px solid #ffffff' if colour == selected else '1px solid transparent'}; }}"
                f"QPushButton:hover {{ border: 3px solid #ffffff; }}"
            )
            btn.clicked.connect(lambda _=False, c=colour: self._pick(c))
            layout.addWidget(btn)
            self._buttons.append(btn)

    def _pick(self, colour: str) -> None:
        self._selected = colour
        for btn, c in zip(self._buttons, self.COLOURS):
            if c == colour:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {c}; border-radius: 14px;"
                    f" border: 3px solid #ffffff; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {c}; border-radius: 14px;"
                    f" border: 1px solid transparent; }}"
                )
        self._on_select(colour)

    @property
    def selected(self) -> str:
        return self._selected


# ---------------------------------------------------------------------------
# Scroll area with guaranteed keyboard scrolling
# ---------------------------------------------------------------------------

class ScrollArea(QScrollArea):
    """QScrollArea with explicit keyboard scrolling.

    Qt's default QAbstractScrollArea handles Page Up/Down, Home and End
    only when the right widget has focus, which has proven unreliable
    across versions/platforms. This subclass handles the keys itself so
    mouse-wheel AND keyboard scrolling always work.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._page_step: Optional[int] = None

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        # Native wheel scrolling, but delegate to scrollbars so it also
        # works when the mouse is over child widgets.
        delta = event.angleDelta().y()
        if delta != 0:
            bar = self.verticalScrollBar()
            step = self._page_step or max(20, bar.pageStep() // 4)
            bar.setValue(bar.value() - (1 if delta > 0 else -1) * step)
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        bar = self.verticalScrollBar()
        if bar.maximum() == 0:
            super().keyPressEvent(event)
            return

        key = event.key()
        if key == Qt.Key.Key_PageDown:
            bar.setValue(bar.value() + bar.pageStep())
            event.accept()
        elif key == Qt.Key.Key_PageUp:
            bar.setValue(bar.value() - bar.pageStep())
            event.accept()
        elif key == Qt.Key.Key_End:
            bar.setValue(bar.maximum())
            event.accept()
        elif key == Qt.Key.Key_Home:
            bar.setValue(bar.minimum())
            event.accept()
        elif key == Qt.Key.Key_Down:
            bar.setValue(bar.value() + self._line_step())
            event.accept()
        elif key == Qt.Key.Key_Up:
            bar.setValue(bar.value() - self._line_step())
            event.accept()
        else:
            super().keyPressEvent(event)

    def _line_step(self) -> int:
        return max(10, self.verticalScrollBar().singleStep())

    def _set_page_step(self, step: int) -> None:
        self._page_step = step


# ---------------------------------------------------------------------------
# Tooltip helper (Qt-native tooltips)
# ---------------------------------------------------------------------------

def attach_tooltip(widget: QWidget, text: str) -> None:
    widget.setToolTip(text)
    # Also set tooltip on all child widgets that may capture the mouse
    for child in widget.findChildren(QWidget):
        if not child.toolTip():
            child.setToolTip(text)
