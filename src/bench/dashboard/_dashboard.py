from slash import App
from slash.core import Elem, Session
from slash.html import Div
from slash.layout import Row
from slash.reactive import Effect, Signal

from bench.dashboard._page_new_task import PageNewTask
from bench.dashboard._sidebar import Sidebar
from bench.engine import Engine


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
        Session.require().set_title(f"{self._engine.bench.name} dashboard")

        # Create content and sidebar
        content = Div().style({"flex-grow": "1", "padding": "0px 8px 0px 16px"})

        signal_content = Signal[Elem](PageNewTask(self._engine))
        Effect(lambda: content.clear().append(signal_content()))

        sidebar = Sidebar(self._engine, signal_content)

        return Row(sidebar, content)
