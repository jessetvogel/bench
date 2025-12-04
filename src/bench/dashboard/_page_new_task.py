import json

from slash.core import Session
from slash.html import Button, Div

from bench.dashboard.utils import prompt
from bench.engine import Engine
from bench.templates import Task


class PageNewTask(Div):
    def __init__(self, engine: Engine) -> None:
        super().__init__()
        self._engine = engine
        self._setup()

    def _setup(self) -> None:
        for task_type in self._engine.bench.task_types():
            self.append(Button(task_type.name()).onclick(lambda: self._create_task(task_type)))

    def _create_task(self, task_type: type[Task]) -> None:
        Session.require().log(f"Creating task of type {task_type.name()}")

        params = task_type.params()

        def handler(values: dict[str, int | float | str]):
            Session.require().log(json.dumps(values))
            self._engine.create_task(task_type, **values)

        prompt(
            f"Create new {task_type.name()}",
            "Fill in parameters please",
            params,
            handler=handler,
        )
