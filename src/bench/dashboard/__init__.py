from pathlib import Path
from typing import cast

from slash import App
from slash.core import Elem, Session
from slash.html import Div
from slash.layout import Row
from slash.reactive import Effect, Signal

import bench
from bench._engine import Engine
from bench.dashboard.components import Menu, PageNewTask

PATH_ASSETS = Path(cast(str, bench.__file__)).resolve().parent / "assets"


class Dashboard:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def run(self) -> None:
        # Launch app
        app = App()
        app.add_route("/", self._home)
        app.run()

    def _home(self) -> Elem:
        # Set document title
        session = Session.require()
        session.set_title(f"{self._engine.bench.name} dashboard")
        session.set_favicon(PATH_ASSETS / "favicon.png")

        # Create content and menu
        content_elem = Div().style(
            {
                "flex-grow": "1",
                "padding": "8px 8px 8px 8px",
                "max-height": "100dvh",
                "overflow-y": "auto",
                "box-sizing": "border-box",
            }
        )

        content = Signal[Elem](Div())
        Effect(lambda: content_elem.clear().append(content()))

        menu = Menu(
            self._engine,
            content=content,
        ).style({"flex-shrink": "0"})

        content.set(PageNewTask(self._engine, menu))

        return Row(menu, content_elem)
