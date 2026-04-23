from __future__ import annotations

from typing import Literal

from textual.app import App
from textual.binding import Binding

ThemeName = Literal["modern", "stealth"]

COMMON_CSS = """
Screen {
    layout: vertical;
    background: #0b1020;
    color: #f4f7fb;
}

#app-title {
    dock: top;
    height: 1;
    content-align: center middle;
    text-style: bold;
    background: #13203b;
    color: #f7fbff;
}

#app-body {
    height: 1fr;
    layout: horizontal;
}

.panel {
    border: round #5b7cbe;
    padding: 0 1;
    margin: 0 1 1 1;
    background: #111a31;
}

.primary-panel { width: 2fr; }
.side-panel { width: 1fr; min-width: 24; }

#help-panel {
    dock: bottom;
    height: auto;
    margin: 0 1;
    border: round #6f86b2;
    padding: 0 1;
    background: #101826;
    color: #d6e1f4;
}

#status-bar {
    dock: bottom;
    height: 1;
    padding: 0 1;
    background: #16233f;
    color: #f0f5ff;
}

.theme-stealth { background: black; color: white; }
.theme-stealth #app-title { background: black; color: white; text-style: none; }
.theme-stealth .panel { border: none; background: black; color: white; padding: 0; margin: 0 1 1 1; }
.theme-stealth #help-panel { border: none; background: black; color: white; padding: 0 1; }
.theme-stealth #status-bar { background: black; color: white; }
"""


class ThemedApp(App[int]):
    BINDINGS = [
        Binding("t", "toggle_theme", "Theme"),
        Binding("question_mark", "toggle_help", "Help"),
        Binding("q", "quit_app", "Quit"),
    ]

    theme_mode: ThemeName = "modern"
    help_text = "t theme  ? help  q quit"

    def __init__(self, *, theme: ThemeName = "modern") -> None:
        super().__init__()
        self.theme_mode = theme
        self.help_visible = False

    def on_mount(self) -> None:
        self.set_theme_mode(self.theme_mode)
        self._set_help_visible(False)

    def set_theme_mode(self, theme: ThemeName) -> None:
        self.theme_mode = theme
        self.remove_class("theme-modern")
        self.remove_class("theme-stealth")
        self.add_class(f"theme-{theme}")
        self.update_status(f"Theme: {theme}")

    def update_status(self, message: str) -> None:
        try:
            self.query_one("#status-bar").update(message)
        except Exception:
            return

    def update_help(self, help_text: str | None = None) -> None:
        try:
            self.query_one("#help-panel").update(help_text or self.help_text)
        except Exception:
            return

    def _set_help_visible(self, visible: bool) -> None:
        self.help_visible = visible
        try:
            widget = self.query_one("#help-panel")
        except Exception:
            return
        widget.display = visible
        if visible:
            self.update_help()

    def action_toggle_theme(self) -> None:
        self.set_theme_mode("stealth" if self.theme_mode == "modern" else "modern")

    def action_toggle_help(self) -> None:
        self._set_help_visible(not self.help_visible)
        self.update_status("Help shown." if self.help_visible else "Help hidden.")

    def action_quit_app(self) -> None:
        self.exit(0)
