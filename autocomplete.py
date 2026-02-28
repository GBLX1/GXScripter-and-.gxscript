from PyQt5.QtWidgets import QListWidget, QListWidgetItem
from PyQt5.QtCore import Qt, QPoint, QTimer
import re
import jedi


class CompletionPopup(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip)
        self.setFocusPolicy(Qt.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.setMaximumHeight(220)
        self.setMinimumWidth(260)
        self._on_choose = None

    def show_items(self, items, pos: QPoint, on_choose):
        self.clear()
        self._on_choose = on_choose
        for text, desc in items[:50]:
            it = QListWidgetItem(text)
            if desc:
                it.setToolTip(desc)
            self.addItem(it)
        if self.count() == 0:
            self.hide()
            return
        self.setCurrentRow(0)
        self.move(pos)
        self.show()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            if e.modifiers() & Qt.ShiftModifier:
                self.choose_current()
            else:
                self.hide()
            return
        if e.key() == Qt.Key_Tab:
            self.choose_current()
            return
        if e.key() == Qt.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(e)

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        self.choose_current()

    def choose_current(self):
        try:
            if self._on_choose is None:
                self.hide()
                return
            it = self.currentItem()
            if it is None:
                self.hide()
                return
            self._on_choose(it.text())
        finally:
            self.hide()


class GXAutoComplete:
    def __init__(self, editor):
        self.editor = editor
        self.popup = CompletionPopup(editor)

        self.base_mode = "gx"
        self.include_python = False
        self.include_lua = False

        self.timer = QTimer(editor)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._trigger_safe)

        self.gx_keywords = [
            "#include_python", "#include_lua", "#include_lua&python",
            "lua_snippet:", "py_snippet:", "--s--", "--e--",
            "repeat", "end", "if", "elif", "else",
            "say", "debugprint",
            "var.set", "var.ask", "var.inc", "var.dec",
            "var.math", "var.math_add", "var.math_sub", "var.math_mul", "var.math_div",
            "table.add", "table.remove", "table.get",
            "true", "false",
            "console.clear()"
        ]

        self.lua_keywords = [
            "function", "local", "return", "if", "elseif", "else", "then", "end",
            "for", "while", "repeat", "until", "break", "and", "or", "not", "nil",
            "true", "false", "print"
        ]

    def set_mode(self, mode: str):
        self.base_mode = (mode or "gx").lower().strip()
        self.popup.hide()

    def set_includes(self, include_python: bool, include_lua: bool):
        self.include_python = bool(include_python)
        self.include_lua = bool(include_lua)
        self.popup.hide()

    def handle_keypress(self, e) -> bool:
        try:
            if self.popup.isVisible():
                if e.key() in (
                    Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown,
                    Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab, Qt.Key_Escape
                ):
                    self.popup.keyPressEvent(e)
                    return True

            if e.key() == Qt.Key_Space and (e.modifiers() & Qt.ControlModifier):
                self.timer.start(0)
                return False

            if e.text() and (e.text().isalnum() or e.text() in "._#&:-"):
                self.timer.start(80)
            elif e.key() in (Qt.Key_Backspace, Qt.Key_Delete):
                self.timer.start(80)
            else:
                self.popup.hide()

            return False
        except Exception:
            self.popup.hide()
            return False

    def _trigger_safe(self):
        try:
            self._trigger()
        except Exception:
            self.popup.hide()

    def _trigger(self):
        cur = self.editor.textCursor()
        block_text = cur.block().text()
        col = cur.positionInBlock()
        prefix = self._prefix(block_text, col)
        if prefix is None:
            self.popup.hide()
            return

        items = []
        replace_len = len(prefix or "")

        if self.base_mode == "py":
            py_items, replace_len = self._python_completions(prefix)
            items.extend(py_items)
            items.extend(self._simple(prefix, self.gx_keywords))
            if self.include_lua:
                items.extend(self._simple(prefix, self.lua_keywords))
        elif self.base_mode == "lua":
            items.extend(self._simple(prefix, self.lua_keywords))
            if self.include_python:
                py_items, _ = self._python_completions(prefix)
                items.extend(py_items)
            items.extend(self._simple(prefix, self.gx_keywords))
        else:
            items.extend(self._simple(prefix, self.gx_keywords))
            if self.include_lua:
                items.extend(self._simple(prefix, self.lua_keywords))
            if self.include_python:
                py_items, _ = self._python_completions(prefix)
                items.extend(py_items)

        items = self._dedupe(items)

        if not items:
            self.popup.hide()
            return

        pos = self.editor.cursorRect(cur).bottomRight()
        global_pos = self.editor.mapToGlobal(pos + QPoint(0, 6))

        def choose(text):
            self._apply_completion(text, replace_len)

        self.popup.show_items(items, global_pos, choose)

    def _prefix(self, line: str, col: int):
        if col < 0:
            return None
        left = line[:col]
        m = re.search(r"[A-Za-z0-9_\.\#\&\:\-\-]+$", left)
        return m.group(0) if m else ""

    def _simple(self, prefix: str, words):
        p = prefix or ""
        low = p.lower()
        out = []
        for w in words:
            if w.lower().startswith(low) and w != p:
                out.append((w, ""))
        return out

    def _python_completions(self, prefix: str):
        code = self.editor.toPlainText()
        cur = self.editor.textCursor()
        line = cur.blockNumber() + 1
        col = cur.positionInBlock()
        try:
            script = jedi.Script(code=code, path="<editor>")
            comps = script.complete(line, col)
            items = []
            for c in comps:
                desc = c.type
                if c.module_name:
                    desc = f"{desc} ({c.module_name})"
                items.append((c.name, desc))
            return items, len(prefix or "")
        except Exception:
            return [], len(prefix or "")

    def _dedupe(self, items):
        seen = set()
        out = []
        for name, desc in items:
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append((name, desc))
        out.sort(key=lambda x: x[0].lower())
        return out

    def _apply_completion(self, text: str, replace_len: int):
        cur = self.editor.textCursor()
        if replace_len and replace_len > 0:
            cur.movePosition(cur.Left, cur.KeepAnchor, replace_len)
            cur.removeSelectedText()
        cur.insertText(text)
        self.editor.setTextCursor(cur)
        self.popup.hide()