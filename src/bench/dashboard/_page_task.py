from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from slash.basic import Checkbox
from slash.core import Session
from slash.html import H2, H3, Button, Code, Dialog, Div, Option, Pre, Select, Span
from slash.layout import Column, Row

from bench.dashboard.utils import Form
from bench.engine import Engine
from bench.serialization import to_json
from bench.templates import Run, Task


class PageTask(Div):
    def __init__(self, engine: Engine, task: Task) -> None:
        super().__init__()
        self._engine = engine
        self._task = task
        self._setup()

    def _setup(self) -> None:
        self.append(H2(self._task.label()))
        self.append(Button("Create experiment").onclick(self._create_experiment))

        self.append(H3("Compare methods"))

        runs = self._engine.cache.select_runs(self._task)

        groups = group_runs(runs)

        checkboxes: list[Checkbox] = []
        for group in groups:
            method = self._engine.cache.select_method(group.method_id)
            checkbox = Checkbox(Span(method.type_name(), " ", f"({len(group.runs)} runs)"))
            checkboxes.append(checkbox)

        self.append(Column(checkboxes))

        self.append(H3("Compare methods"))

    def _create_experiment(self) -> None:
        DialogNewExperiment(self._engine, self._task).mount().show_modal()


@dataclass
class RunGroup:
    method_id: str
    runs: list[Run]


def group_runs(runs: list[Run]) -> list[RunGroup]:
    groups: dict[str, RunGroup] = {}
    for run in runs:
        if run.method_id not in groups:
            groups[run.method_id] = RunGroup(method_id=run.method_id, runs=[])
        groups[run.method_id].runs.append(run)
    return list(groups.values())


class DialogNewExperiment(Dialog):
    def __init__(self, engine: Engine, task: Task) -> None:
        super().__init__()
        self._engine = engine
        self._task = task
        self._setup()

    def _setup(self) -> None:
        method_types = {method_type.type_name(): method_type for method_type in self._engine.bench.method_types()}

        form_wrapper = Div().style({"margin-top": "16px"})

        def handle_change_method() -> None:
            method_type = method_types[select.value]
            form_wrapper.clear()
            form_wrapper.append(Form(method_type.params()))
            start.disabled = None  # TODO: SHOULD SUPPORT `False`

        def handle_click_start() -> None:
            method_type = method_types[select.value]
            Session.require().log(method_type.type_name())

            form = cast(Form, form_wrapper.children[0])
            method = method_type(**{param.name: form.value(param) for param in method_type.params()})

            Session.require().log(  # TODO: REMOVE THIS
                "Create experiment",
                level="debug",
                details=Div(Span(method_type.type_name()), Pre(Code(to_json(method)))),
            )

            self.unmount()

            self._engine.create_run(self._task, method)

        self.append(H3(f"Create experiment for {self._task.type_name()}"))
        self.append(
            Row(
                Span("Select method"),
                select := Select(
                    [Option("-", disabled=True, hidden=True)] + [Option(name) for name in method_types]
                ).onchange(handle_change_method),
            ).style({"align-items": "center", "gap": "16px", "font-weight": "bold"})
        )
        self.append(form_wrapper)
        self.append(
            Row(
                start := Button("Start").onclick(handle_click_start),
                Button("Cancel").onclick(lambda: self.unmount()),
            ).style({"justify-content": "center", "gap": "16px"})
        )
        start.disabled = True
