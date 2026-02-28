import sys
import os
import traceback
import faulthandler
import shutil

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QAction, QPlainTextEdit, QPushButton, QSplitter, QMessageBox
)
from PyQt5.QtCore import Qt, QEventLoop, qInstallMessageHandler, QTimer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

ROAMING = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
APP_DIR = os.path.join(ROAMING, "GXScripter")
os.makedirs(APP_DIR, exist_ok=True)

LOG_PATH = os.path.join(APP_DIR, "crash.log")

def log(msg: str):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

try:
    _log_file = open(LOG_PATH, "a", encoding="utf-8")
    faulthandler.enable(_log_file)
except Exception:
    _log_file = None

def excepthook(exctype, value, tb):
    log("\n=== UNCAUGHT EXCEPTION ===")
    log("".join(traceback.format_exception(exctype, value, tb)))
    sys.__excepthook__(exctype, value, tb)

def qt_message_handler(mode, context, message):
    log(f"[QT] {message}")

sys.excepthook = excepthook
qInstallMessageHandler(qt_message_handler)
log("\n=== APP START ===")

def resource_path(rel_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel_path)

def ensure_roaming_assets():
    folder = os.path.join(ROAMING, "GXScript_Icon")
    os.makedirs(folder, exist_ok=True)

    src_fic = resource_path(os.path.join("assets", "FIC.ico"))
    src_aic = resource_path(os.path.join("assets", "AIC.ico"))

    dst_fic = os.path.join(folder, "FIC.ico")
    dst_aic = os.path.join(folder, "AIC.ico")

    try:
        if os.path.exists(src_fic) and not os.path.exists(dst_fic):
            shutil.copyfile(src_fic, dst_fic)
        if os.path.exists(src_aic) and not os.path.exists(dst_aic):
            shutil.copyfile(src_aic, dst_aic)
    except Exception:
        pass

    return folder, dst_fic, dst_aic

from console import GXConsole
from debugger import GXDebugger
from gx_engine import GXEngine, GXRuntimeError
from python_engine import PythonEngine
from lua_engine import LuaEngine
from file_handler import FileHandler
from themes import DARK, LIGHT, apply_theme
from syntax_highlighter import GXHighlighter
from autocomplete import GXAutoComplete


class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.autocomplete = None

    def keyPressEvent(self, e):
        try:
            if e.key() in (Qt.Key_Return, Qt.Key_Enter):
                cur = self.textCursor()
                block_text = cur.block().text()
                before = block_text[:cur.positionInBlock()]
                base_indent = self._leading_ws(block_text)

                extra = ""
                if self._starts_block(before.strip()):
                    extra = "    "

                super().keyPressEvent(e)
                cur = self.textCursor()
                cur.insertText(base_indent + extra)
                self.setTextCursor(cur)
                return

            if self.autocomplete is not None:
                if self.autocomplete.handle_keypress(e):
                    return

            super().keyPressEvent(e)

        except Exception:
            log("\n=== EXCEPTION IN CodeEditor.keyPressEvent ===")
            log(traceback.format_exc())
            raise

    def _leading_ws(self, s: str) -> str:
        i = 0
        while i < len(s) and s[i] in (" ", "\t"):
            i += 1
        return s[:i]

    def _starts_block(self, line: str) -> bool:
        if not line:
            return False
        lw = line.lower()
        if lw.startswith(("if ", "elif ", "else", "repeat", "lua_snippet:", "py_snippet:")):
            return True
        if line.endswith(":"):
            return True
        if lw.endswith(" then"):
            return True
        if lw.startswith(("function", "for ", "while ", "repeat", "do")):
            return True
        return False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.input_loop = QEventLoop()
        self.theme = DARK

        self.roaming_dir, self.fic_path, self.aic_path = ensure_roaming_assets()

        self.editor = CodeEditor()
        self.console = GXConsole()
        self.debugger = GXDebugger()

        self.highlighter = GXHighlighter(self.editor.document())
        self.autocomplete = GXAutoComplete(self.editor)
        self.editor.autocomplete = self.autocomplete

        self.editor.textChanged.connect(self._on_text_changed)

        self.file_handler = FileHandler(
            parent=self,
            set_title=self.setWindowTitle,
            get_text=self.editor.toPlainText,
            set_text=self._set_editor_text
        )

        self.py_engine = PythonEngine(
            console_write=self.console.write,
            debugger_write=self._debug_write_adapter,
            input_request=self.console.request_input
        )

        self.lua_engine = LuaEngine(
            console_write=self.console.write,
            debugger_write=self._debug_write_adapter,
            input_request=self.console.request_input
        )

        self.gx_engine = GXEngine(
            console_write=self.console.write,
            debugger_write=self._debug_write_adapter,
            input_request=self.console.request_input,
            run_python_block=self._run_python_block_from_gx,
            run_lua_block=self._run_lua_block_from_gx
        )

        self._build_ui()
        self._build_menu()
        self._apply_theme(self.theme)
        self.file_handler._update_title()
        self._sync_mode()

        QTimer.singleShot(0, self._apply_default_split_sizes)

        if len(sys.argv) > 1:
            self.file_handler.open_path(sys.argv[1])
            self._sync_mode()

    def _apply_default_split_sizes(self):
        if hasattr(self, "main_split"):
            self.main_split.setSizes([860, 340])
        if hasattr(self, "left_split"):
            self.left_split.setSizes([430, 170])

    def _run_python_block_from_gx(self, code, start_line):
        self.py_engine.execute(
            code,
            filename=self.file_handler.state.path or "<python>",
            extra_globals=self.gx_engine.vars
        )

    def _run_lua_block_from_gx(self, code, start_line):
        self.lua_engine.inject_globals(self.gx_engine.vars)
        self.lua_engine.execute(code, filename=self.file_handler.state.path or "<lua>")
        self.lua_engine.sync_back(self.gx_engine.vars)

    def _build_ui(self):
        run_btn = QPushButton("Run (F5)")
        run_btn.clicked.connect(self.run_current)

        open_btn = QPushButton("Open")
        open_btn.clicked.connect(self.file_handler.open_file_dialog)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.file_handler.save)

        topbar = QHBoxLayout()
        topbar.setContentsMargins(10, 10, 10, 6)
        topbar.setSpacing(10)
        topbar.setAlignment(Qt.AlignLeft)
        topbar.addWidget(open_btn)
        topbar.addWidget(save_btn)
        topbar.addWidget(run_btn)
        topbar.addStretch(1)

        top = QWidget()
        top.setLayout(topbar)

        self.left_split = QSplitter(Qt.Vertical)
        self.left_split.setChildrenCollapsible(False)
        self.left_split.setHandleWidth(6)
        self.left_split.addWidget(self.editor)
        self.left_split.addWidget(self.console)

        self.main_split = QSplitter(Qt.Horizontal)
        self.main_split.setChildrenCollapsible(False)
        self.main_split.setHandleWidth(6)
        self.main_split.addWidget(self.left_split)
        self.main_split.addWidget(self.debugger)

        self.left_split.setStretchFactor(0, 4)
        self.left_split.setStretchFactor(1, 1)
        self.main_split.setStretchFactor(0, 4)
        self.main_split.setStretchFactor(1, 2)

        root = QVBoxLayout()
        root.setContentsMargins(10, 6, 10, 10)
        root.setSpacing(10)
        root.addWidget(top)
        root.addWidget(self.main_split)

        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)
        self.resize(1200, 700)

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        act_new = QAction("New", self)
        act_open = QAction("Open...", self)
        act_save = QAction("Save", self)
        act_save_as = QAction("Save As...", self)
        act_exit = QAction("Exit", self)

        act_new.triggered.connect(self.file_handler.new_file)
        act_open.triggered.connect(self.file_handler.open_file_dialog)
        act_save.triggered.connect(self.file_handler.save)
        act_save_as.triggered.connect(self.file_handler.save_as)
        act_exit.triggered.connect(self.close)

        file_menu.addAction(act_new)
        file_menu.addAction(act_open)
        file_menu.addSeparator()
        file_menu.addAction(act_save)
        file_menu.addAction(act_save_as)
        file_menu.addSeparator()
        file_menu.addAction(act_exit)

        run_menu = menubar.addMenu("Run")
        act_run = QAction("Run (F5)", self)
        act_run.triggered.connect(self.run_current)
        run_menu.addAction(act_run)

        view_menu = menubar.addMenu("View")
        self.act_dark = QAction("Dark Mode", self, checkable=True)
        self.act_light = QAction("Light Mode", self, checkable=True)
        self.act_dark.setChecked(True)
        self.act_light.setChecked(False)
        self.act_dark.triggered.connect(self._set_dark)
        self.act_light.triggered.connect(self._set_light)
        view_menu.addAction(self.act_dark)
        view_menu.addAction(self.act_light)

        tools_menu = menubar.addMenu("Tools")
        act_reg = QAction("Register .gxscript association", self)
        act_reg.triggered.connect(self.register_gxscript_association)
        tools_menu.addAction(act_reg)

    def _apply_theme(self, theme):
        apply_theme(theme, self, self.editor, self.console, self.debugger)

    def _set_dark(self):
        self.act_dark.setChecked(True)
        self.act_light.setChecked(False)
        self.theme = DARK
        self._apply_theme(self.theme)

    def _set_light(self):
        self.act_light.setChecked(True)
        self.act_dark.setChecked(False)
        self.theme = LIGHT
        self._apply_theme(self.theme)

    def _set_editor_text(self, text):
        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)
        self.file_handler.mark_dirty(False)
        self._sync_mode()

    def _on_text_changed(self):
        try:
            self.file_handler.mark_dirty(True)
            self._sync_mode()
        except Exception:
            log("\n=== EXCEPTION IN _on_text_changed ===")
            log(traceback.format_exc())
            raise

    def _has_directive_anywhere(self, text, directive):
        for ln in text.splitlines():
            s = ln.strip()
            if s and s.startswith(directive):
                return True
        return False

    def _sync_mode(self):
        base_mode = self.file_handler.state.mode
        text = self.editor.toPlainText()

        include_py = self._has_directive_anywhere(text, "#include_python") or self._has_directive_anywhere(text, "#include_lua&python")
        include_lua = self._has_directive_anywhere(text, "#include_lua") or self._has_directive_anywhere(text, "#include_lua&python")

        if base_mode != self.highlighter.mode:
            self.highlighter.set_mode(base_mode)

        self.autocomplete.set_mode(base_mode)
        self.autocomplete.set_includes(include_py, include_lua)

    def _debug_write_adapter(self, message, level="info", line=None, source="GX"):
        msg = message if isinstance(message, str) else str(message)
        self.debugger.write(msg, level=level, line=line, source=source)

    def run_current(self):
        code = self.editor.toPlainText()
        self.console.write("\n")
        self._sync_mode()

        base_mode = self.file_handler.state.mode

        if base_mode == "lua":
            self.lua_engine.execute(code, filename=self.file_handler.state.path or "<lua>")
            return

        if base_mode == "py":
            self.py_engine.execute(code, filename=self.file_handler.state.path or "<python>")
            return

        try:
            self.gx_engine.execute(code)
        except GXRuntimeError as e:
            self.debugger.write(str(e), level="error", line=e.line, source="GX")

    def register_gxscript_association(self):
        try:
            import winreg
            import ctypes

            exe_path = sys.executable
            fic = self.fic_path

            classes_root = r"Software\Classes"
            ext_key = classes_root + r"\.gxscript"
            prog_id = "GXScripter.gxscript"
            prog_key = classes_root + "\\" + prog_id

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, ext_key) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, prog_id)

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, prog_key) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "GXScript File")

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, prog_key + r"\DefaultIcon") as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, fic)

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, prog_key + r"\shell\open\command") as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f"\"{exe_path}\" \"%1\"")

            try:
                ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
            except Exception:
                pass

            QMessageBox.information(
                self,
                "Registered",
                "Successfully registered .gxscript to open with GXScripter.\nYou may need to restart Explorer to see icon changes."
            )
        except Exception as e:
            QMessageBox.critical(self, "Register failed", str(e))

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F5:
            self.run_current()
            return
        super().keyPressEvent(e)

    def closeEvent(self, e):
        if self.file_handler.confirm_close():
            e.accept()
        else:
            e.ignore()


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()