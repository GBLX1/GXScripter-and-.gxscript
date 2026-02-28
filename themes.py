from dataclasses import dataclass


@dataclass
class Theme:
    name: str
    window_bg: str
    panel_bg: str
    editor_bg: str
    editor_fg: str
    console_bg: str
    console_fg: str
    debugger_bg: str
    debugger_fg: str
    caret: str
    accent: str
    selection_bg: str


DARK = Theme(
    name="dark",
    window_bg="#121212",
    panel_bg="#1a1a1a",
    editor_bg="#0f0f0f",
    editor_fg="#e8e8e8",
    console_bg="#0b0b0b",
    console_fg="#9aff9a",
    debugger_bg="#0b0b0b",
    debugger_fg="#e8e8e8",
    caret="#ffffff",
    accent="#3daee9",
    selection_bg="#264f78",
)

LIGHT = Theme(
    name="light",
    window_bg="#f2f2f2",
    panel_bg="#ffffff",
    editor_bg="#ffffff",
    editor_fg="#111111",
    console_bg="#ffffff",
    console_fg="#111111",
    debugger_bg="#ffffff",
    debugger_fg="#111111",
    caret="#111111",
    accent="#0b57d0",
    selection_bg="#cce4ff",
)


def apply_theme(theme: Theme, window, editor, console, debugger):
    window.setStyleSheet(f"""
        QWidget {{
            background: {theme.window_bg};
            color: {theme.editor_fg};
            font-size: 12px;
        }}
        QMenuBar {{
            background: {theme.panel_bg};
        }}
        QMenuBar::item:selected {{
            background: {theme.selection_bg};
        }}
        QMenu {{
            background: {theme.panel_bg};
        }}
        QMenu::item:selected {{
            background: {theme.selection_bg};
        }}
        QPushButton {{
            background: {theme.panel_bg};
            border: 1px solid {theme.selection_bg};
            padding: 6px 10px;
            border-radius: 6px;
        }}
        QPushButton:hover {{
            border: 1px solid {theme.accent};
        }}
        QPushButton:checked {{
            background: {theme.selection_bg};
        }}
        QPlainTextEdit {{
            border: 1px solid {theme.selection_bg};
            border-radius: 6px;
        }}
        QTextEdit {{
            border: 1px solid {theme.selection_bg};
            border-radius: 6px;
        }}
    """)

    editor.setStyleSheet(f"""
        QPlainTextEdit {{
            background: {theme.editor_bg};
            color: {theme.editor_fg};
            selection-background-color: {theme.selection_bg};
        }}
    """)
    console.setStyleSheet(f"""
        QTextEdit {{
            background: {theme.console_bg};
            color: {theme.console_fg};
            selection-background-color: {theme.selection_bg};
        }}
    """)
    debugger.view.setStyleSheet(f"""
        QPlainTextEdit {{
            background: {theme.debugger_bg};
            color: {theme.debugger_fg};
            selection-background-color: {theme.selection_bg};
        }}
    """)