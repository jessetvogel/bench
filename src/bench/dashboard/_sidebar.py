from functools import partial
from typing import Any, Awaitable, Callable

from slash.core import Children, Elem, Session
from slash.html import Div
from slash.layout import Column, Row


class Sidebar(Column):
    def __init__(self, set_content: Callable[[Elem], None]) -> None:
        super().__init__()
        self._set_content = set_content
        self._setup()

    def _setup(self) -> None:
        self.style(
            {
                "width": "224px",
                "height": "calc(100dvh - 16px)",
                "margin": "8px",
                "background-color": "var(--bg)",
                "box-shadow": "var(--shadow)",
                "border": "1px solid var(--border)",
                "border-radius": "16px",
            }
        )

        self._dots: dict[str, Div] = {}

        # Tasks
        self._add_header("Tasks")
        for task in ["Task 1", "Task 2"]:
            self._add_item(task, onclick=partial(self._click_task, task))

        # --------
        self._add_separator()

        # Info
        self._add_header("Info")
        self._add_item("About")

        # Theme
        self._add_theme_buttons()

    def _add_header(self, *children: Children) -> None:
        self.append(
            Div(*children).style(
                {
                    "display": "flex",
                    "align-items": "center",
                    "gap": "8px",
                    "height": "40px",
                    "line-height": "40px",
                    "padding": "0px 8px",
                    "color": "var(--text-muted)",
                    "font-variant": "small-caps",
                    "letter-spacing": "1px",
                }
            )
        )

    def _add_item(self, *children: Children, onclick: Callable[[], Awaitable[Any] | Any] | None = None) -> None:
        self.append(
            item := Div(*children).style(
                {
                    "display": "flex",
                    "align-items": "center",
                    "gap": "8px",
                    "height": "40px",
                    "line-height": "40px",
                    "padding": "0px 8px",
                    "cursor": "pointer",
                }
            )
        )
        if onclick is not None:
            item.onclick(onclick)

    def _add_separator(self) -> None:
        self.append(
            Div().style(
                {
                    "height": "0px",
                    "border-bottom": "1px solid var(--border)",
                    "margin": "8px",
                }
            )
        )

    def _add_theme_buttons(self) -> None:
        self.append(
            Row(
                Row("light")
                .style({"cursor": "pointer", "opacity": "0.33", "align-items": "center", "gap": "8px"})
                .onclick(lambda: Session.require().set_theme("light")),
                Row("dark")
                .style({"cursor": "pointer", "opacity": "0.33", "align-items": "center", "gap": "8px"})
                .onclick(lambda: Session.require().set_theme("dark")),
            ).style({"margin": "auto 0px 8px 0px", "justify-content": "center", "gap": "32px"})
        )

    def _click_task(self, task: str) -> None:
        # self._set_content(BenchmarkPage(benchmark))
        pass
