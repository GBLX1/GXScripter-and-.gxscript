from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import Qt, pyqtSignal, QEventLoop


class GXConsole(QTextEdit):
    input_submitted = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptRichText(False)
        self.setUndoRedoEnabled(False)
        self.setCursorWidth(2)
        self.prompt = "> "
        self.waiting_for_input = False
        self.input_buffer = ""
        self.history = []
        self.history_index = -1
        self._loop = None

        self._boot_text()

    def _boot_text(self):
        self.clear()
        self.insertPlainText("GXScript Console Ready\n")
        self._insert_prompt()

    def clear_output(self):
        self.waiting_for_input = False
        if self._loop is not None:
            self._loop.quit()
            self._loop = None
        self.history_index = len(self.history)
        self.input_buffer = ""
        self._boot_text()

    def write(self, text):
        self.moveCursor(self.textCursor().End)
        self.insertPlainText(text)
        self.moveCursor(self.textCursor().End)
        self.ensureCursorVisible()

    def request_input(self, question):
        self.write(str(question) + "\n")
        self.waiting_for_input = True
        self._insert_prompt()
        self.ensureCursorVisible()
        self.setFocus(Qt.OtherFocusReason)

        self._loop = QEventLoop()
        self._loop.exec_()
        self._loop = None
        return self.input_buffer

    def keyPressEvent(self, event):
        if not self.waiting_for_input:
            super().keyPressEvent(event)
            return

        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        self.setTextCursor(cursor)

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            current_line = self._current_input_line()
            self.input_buffer = current_line.strip()
            self.history.append(self.input_buffer)
            self.history_index = len(self.history)
            self.write("\n")
            self.waiting_for_input = False
            self.input_submitted.emit(self.input_buffer)
            if self._loop is not None:
                self._loop.quit()
            return

        if event.key() == Qt.Key_Backspace:
            if self._cursor_after_prompt():
                super().keyPressEvent(event)
            return

        if event.key() == Qt.Key_Up:
            if self.history:
                self.history_index = max(0, self.history_index - 1)
                self._replace_current_input(self.history[self.history_index])
            return

        if event.key() == Qt.Key_Down:
            if self.history:
                self.history_index = min(len(self.history) - 1, self.history_index + 1)
                self._replace_current_input(self.history[self.history_index])
            return

        super().keyPressEvent(event)

    def _insert_prompt(self):
        self.moveCursor(self.textCursor().End)
        self.insertPlainText(self.prompt)
        self.moveCursor(self.textCursor().End)

    def _current_input_line(self):
        text = self.toPlainText().split("\n")[-1]
        if text.startswith(self.prompt):
            return text[len(self.prompt):]
        return text

    def _replace_current_input(self, text):
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        cursor.select(cursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.insertText(self.prompt + text)

    def _cursor_after_prompt(self):
        cursor = self.textCursor()
        return cursor.positionInBlock() > len(self.prompt) 