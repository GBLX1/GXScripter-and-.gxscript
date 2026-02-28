from dataclasses import dataclass
from datetime import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit, QLabel, QSizePolicy
from PyQt5.QtCore import Qt


@dataclass
class DebugEntry:
    ts: str
    level: str
    source: str
    line: int | None
    message: str


class GXDebugger(QWidget):
    def __init__(self):
        super().__init__()
        self.entries: list[DebugEntry] = []
        self.show_info = True
        self.show_warning = True
        self.show_error = True

        self.title = QLabel("Debugger")
        self.title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.btn_info = QPushButton("Info")
        self.btn_info.setCheckable(True)
        self.btn_info.setChecked(True)

        self.btn_warning = QPushButton("Warnings")
        self.btn_warning.setCheckable(True)
        self.btn_warning.setChecked(True)

        self.btn_error = QPushButton("Errors")
        self.btn_error.setCheckable(True)
        self.btn_error.setChecked(True)

        self.btn_clear = QPushButton("Clear")

        top = QHBoxLayout()
        top.addWidget(self.title)
        top.addWidget(self.btn_info)
        top.addWidget(self.btn_warning)
        top.addWidget(self.btn_error)
        top.addWidget(self.btn_clear)

        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QPlainTextEdit.NoWrap)

        root = QVBoxLayout()
        root.addLayout(top)
        root.addWidget(self.view)
        self.setLayout(root)

        self.btn_info.toggled.connect(self._toggle_info)
        self.btn_warning.toggled.connect(self._toggle_warning)
        self.btn_error.toggled.connect(self._toggle_error)
        self.btn_clear.clicked.connect(self.clear)

        self.setFocusPolicy(Qt.StrongFocus)

    def clear(self):
        self.entries.clear()
        self.view.setPlainText("")

    def write(self, message: str, level: str = "info", line: int | None = None, source: str = "GX"):
        level = (level or "info").lower().strip()
        if level not in ("info", "warning", "error"):
            level = "info"
        ts = datetime.now().strftime("%H:%M:%S")
        self.entries.append(DebugEntry(ts=ts, level=level, source=source, line=line, message=str(message)))
        self._render_append(self.entries[-1])

    def info(self, message: str, line: int | None = None, source: str = "GX"):
        self.write(message, "info", line, source)

    def warning(self, message: str, line: int | None = None, source: str = "GX"):
        self.write(message, "warning", line, source)

    def error(self, message: str, line: int | None = None, source: str = "GX"):
        self.write(message, "error", line, source)

    def _toggle_info(self, v: bool):
        self.show_info = v
        self._rerender()

    def _toggle_warning(self, v: bool):
        self.show_warning = v
        self._rerender()

    def _toggle_error(self, v: bool):
        self.show_error = v
        self._rerender()

    def _allowed(self, level: str) -> bool:
        if level == "info":
            return self.show_info
        if level == "warning":
            return self.show_warning
        if level == "error":
            return self.show_error
        return True

    def _fmt(self, e: DebugEntry) -> str:
        lvl = e.level.upper()
        where = f"{e.source}"
        if e.line is not None:
            where += f":{e.line}"
        return f"[{e.ts}] [{lvl}] [{where}] {e.message}"

    def _render_append(self, entry: DebugEntry):
        if not self._allowed(entry.level):
            return
        cur = self.view.toPlainText()
        line = self._fmt(entry)
        if not cur:
            self.view.setPlainText(line)
        else:
            self.view.appendPlainText(line)
        self.view.moveCursor(self.view.textCursor().End)

    def _rerender(self):
        out = []
        for e in self.entries:
            if self._allowed(e.level):
                out.append(self._fmt(e))
        self.view.setPlainText("\n".join(out))
        self.view.moveCursor(self.view.textCursor().End)