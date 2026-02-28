import re
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont


class GXHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.mode = "gx"

        self.fmt_keyword = QTextCharFormat()
        self.fmt_keyword.setForeground(QColor("#4FC3F7"))
        self.fmt_keyword.setFontWeight(QFont.Bold)

        self.fmt_string = QTextCharFormat()
        self.fmt_string.setForeground(QColor("#C3E88D"))

        self.fmt_number = QTextCharFormat()
        self.fmt_number.setForeground(QColor("#F78C6C"))

        self.fmt_comment = QTextCharFormat()
        self.fmt_comment.setForeground(QColor("#7f7f7f"))
        self.fmt_comment.setFontItalic(True)

        self.fmt_op = QTextCharFormat()
        self.fmt_op.setForeground(QColor("#FFD54F"))

        self.fmt_builtin = QTextCharFormat()
        self.fmt_builtin.setForeground(QColor("#B39DDB"))
        self.fmt_builtin.setFontWeight(QFont.Bold)

        self.gx_keywords = [
            "repeat", "end", "if", "elif", "else",
            "say", "debugprint",
            "var.set", "var.ask", "var.inc", "var.dec",
            "var.math", "var.math_add", "var.math_sub", "var.math_mul", "var.math_div",
            "table.add", "table.remove", "table.get",
            "true", "false"
        ]

        self.py_keywords = [
            "def", "class", "return", "if", "elif", "else", "for", "while", "break",
            "continue", "import", "from", "as", "try", "except", "finally", "with",
            "lambda", "pass", "raise", "yield", "global", "nonlocal", "assert",
            "True", "False", "None"
        ]

        self.lua_keywords = [
            "function", "local", "return", "if", "elseif", "else", "then", "end",
            "for", "while", "repeat", "until", "break", "and", "or", "not", "nil",
            "true", "false"
        ]

        self.re_string = re.compile(r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'')
        self.re_number = re.compile(r"\b\d+(\.\d+)?\b")
        self.re_comment_py = re.compile(r"#.*$")
        self.re_comment_lua = re.compile(r"--.*$")
        self.re_ops = re.compile(r"(\+|\-|\*{1,2}|/|==|!=|<=|>=|<|>|\(|\)|=|,|\[|\]|\{|\})")

    def set_mode(self, mode: str):
        mode = (mode or "gx").lower().strip()
        if mode == self.mode:
            return
        self.mode = mode
        self.rehighlight()

    def highlightBlock(self, text):
        if self.mode == "py":
            self._highlight_python(text)
        elif self.mode == "lua":
            self._highlight_lua(text)
        else:
            self._highlight_gx(text)

    def _apply_words(self, text, words, fmt):
        for w in words:
            for m in re.finditer(rf"(?<![\w\.]){re.escape(w)}(?![\w\.])", text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)

    def _apply_regex(self, text, regex, fmt):
        for m in regex.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), fmt)

    def _highlight_common(self, text):
        self._apply_regex(text, self.re_string, self.fmt_string)
        self._apply_regex(text, self.re_number, self.fmt_number)
        self._apply_regex(text, self.re_ops, self.fmt_op)

    def _highlight_gx(self, text):
        self._highlight_common(text)
        self._apply_words(text, self.gx_keywords, self.fmt_keyword)

    def _highlight_python(self, text):
        self._highlight_common(text)
        self._apply_regex(text, self.re_comment_py, self.fmt_comment)
        self._apply_words(text, self.py_keywords, self.fmt_keyword)
        self._apply_words(text, ["print", "range", "len", "int", "float", "str", "list", "dict"], self.fmt_builtin)

    def _highlight_lua(self, text):
        self._highlight_common(text)
        self._apply_regex(text, self.re_comment_lua, self.fmt_comment)
        self._apply_words(text, self.lua_keywords, self.fmt_keyword)
        self._apply_words(text, ["print"], self.fmt_builtin)