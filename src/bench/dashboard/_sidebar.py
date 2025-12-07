from functools import partial
from typing import Any, Awaitable, Callable

from slash.core import Children, Elem, Session
from slash.events import ClickEvent
from slash.html import Div
from slash.layout import Column, Row
from slash.reactive import Signal

from bench.dashboard._page_new_task import PageNewTask
from bench.dashboard._page_task import PageTask
from bench.dashboard.icons import icon_oplus
from bench.engine import Engine
from bench.templates import Task


class Sidebar(Column):
    def __init__(self, engine: Engine, content: Signal[Elem]) -> None:
        super().__init__()
        self._engine = engine
        self._content = content
        self._setup()

    def _setup(self) -> None:
        self.style(
            {
                "width": "224px",
                "height": "100dvh",
                "background-color": "var(--bg)",
                "box-shadow": "var(--shadow)",
                "border-right": "1px solid var(--border)",
            }
        )

        self._dots: dict[str, Div] = {}

        # Tasks
        self._add_header("Tasks")
        for task in self._engine.cache.select_tasks():

            def handle_click(event: ClickEvent, task: Task):
                Session.require().log(f"task = {task.encode()}")
                self._content.set(PageTask(self._engine, task))

            self._add_item(task.label(), onclick=partial(handle_click, task=task))

        self._add_item(icon_oplus(), "create new task", onclick=lambda: self._content.set(PageNewTask(self._engine)))

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
                    # "color": "var(--text-muted)",
                    "font-weight": "bold",
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
