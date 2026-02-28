from dataclasses import dataclass
from PyQt5.QtWidgets import QFileDialog, QMessageBox


@dataclass
class FileState:
    path: str | None = None
    dirty: bool = False
    mode: str = "gx"


class FileHandler:
    def __init__(self, parent, set_title, get_text, set_text):
        self.parent = parent
        self.set_title = set_title
        self.get_text = get_text
        self.set_text = set_text
        self.state = FileState()

    def new_file(self):
        if not self._confirm_discard_or_save():
            return False
        self.state = FileState(path=None, dirty=False, mode="gx")
        self.set_text("")
        self._update_title()
        return True

    def open_file_dialog(self):
        if not self._confirm_discard_or_save():
            return None
        path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Open",
            "",
            "GXScript (*.gxscript);;Python (*.py);;Lua (*.lua);;Text (*.txt);;All Files (*.*)"
        )
        if not path:
            return None
        return self.open_path(path)

    def open_path(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="latin-1") as f:
                text = f.read()

        self.state.path = path
        self.state.dirty = False
        self.state.mode = self._detect_mode(path, text)
        self.set_text(text)
        self._update_title()
        return self.state

    def save(self):
        if self.state.path is None:
            return self.save_as()
        return self._write(self.state.path)

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Save As",
            self.state.path or "",
            "GXScript (*.gxscript);;Python (*.py);;Lua (*.lua);;Text (*.txt);;All Files (*.*)"
        )
        if not path:
            return False
        self.state.path = path
        self.state.mode = self._detect_mode(path, self.get_text())
        self._update_title()
        return self._write(path)

    def mark_dirty(self, dirty: bool = True):
        self.state.dirty = dirty
        self._update_title()

    def confirm_close(self):
        return self._confirm_discard_or_save()

    def _write(self, path: str):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.get_text())
        except Exception as e:
            QMessageBox.critical(self.parent, "Save Failed", str(e))
            return False
        self.state.dirty = False
        self._update_title()
        return True

    def _confirm_discard_or_save(self):
        if not self.state.dirty:
            return True
        box = QMessageBox(self.parent)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Unsaved changes")
        box.setText("You have unsaved changes.")
        btn_save = box.addButton("Save", QMessageBox.AcceptRole)
        btn_discard = box.addButton("Don't Save", QMessageBox.DestructRole)
        btn_cancel = box.addButton("Cancel", QMessageBox.RejectRole)
        box.setDefaultButton(btn_save)
        box.exec_()
        clicked = box.clickedButton()
        if clicked == btn_save:
            return self.save()
        if clicked == btn_discard:
            return True
        return False

    def _detect_mode(self, path: str, text: str):
        low = path.lower()
        first = ""
        for ln in text.splitlines():
            if ln.strip():
                first = ln.strip()
                break
        if first.startswith("#lua"):
            return "lua"
        if low.endswith(".py"):
            return "py"
        if low.endswith(".lua"):
            return "lua"
        if low.endswith(".gxscript"):
            return "gx"
        return "gx"

    def _update_title(self):
        name = self.state.path if self.state.path else "Untitled"
        star = "*" if self.state.dirty else ""
        mode = self.state.mode.upper()
        self.set_title(f"GXScript IDE [{mode}] - {name}{star}")