from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from functools import partial
from typing import Any, Awaitable, Callable, cast

from slash.basic import Axes, Checkbox, Icon
from slash.basic import Graph as SlashGraph
from slash.core import Children, Elem, Session
from slash.events import ClickEvent
from slash.html import H2, H3, HTML, Button, Code, Details, Dialog, Div, Input, Option, Pre, Select, Span, Summary
from slash.layout import Column, Panel, Row
from slash.reactive import Effect, Signal

from bench.dashboard.ansi import ansi2html
from bench.dashboard.utils import Timer, prompt, timedelta_to_str
from bench.engine import Engine, Execution
from bench.metrics import Graph, Metric, Table, Time
from bench.templates import Param, Run, Task


class Menu(Column):
    """Menu component."""

    def __init__(
        self,
        engine: Engine,
        *,
        content: Signal[Elem],
    ) -> None:
        super().__init__()
        self._engine = engine
        self._content = content

        self._executions = Signal(self._engine.executions)

        self._setup()

    def _setup(self) -> None:
        self.style(
            {
                "width": "224px",
                "height": "100dvh",
                "background-color": "var(--bg)",
                "box-shadow": "var(--shadow)",
                "border-right": "1px solid var(--border-muted)",
            }
        )

        # Tasks
        self.append(self._header("Tasks"))
        for task in self._engine.cache.select_tasks():

            def handle_click(event: ClickEvent, task: Task) -> None:
                self._click_task(task)

            self.append(self._item(task.label(), onclick=partial(handle_click, task=task)))

        self.append(
            self._item(
                "create new task",
                onclick=lambda: self._content.set(PageNewTask(self._engine)),
            )
        )

        # --------
        self.append(self._separator())

        # Info
        # self.append(self._header("Info"))
        # self.append(self._item("About"))

        # Processes
        self.append(self._processes())

        # Theme
        self.append(self._theme_buttons())

        # Timer
        self.append(Timer(self._refresh, seconds=1.0, repeat=True))

    def _header(self, *children: Children) -> Elem:
        return Div(*children).style(
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

    def _item(self, *children: Children, onclick: Callable[[], Awaitable[Any] | Any] | None = None) -> Elem:
        item = Div(*children).style(
            {
                "display": "flex",
                "align-items": "center",
                "gap": "8px",
                "height": "40px",
                "padding": "0px 8px",
                "cursor": "pointer",
            }
        )
        if onclick is not None:
            item.onclick(onclick)
        return item

    def _separator(self) -> Elem:
        return Div().style(
            {
                "height": "0px",
                "border-bottom": "1px solid var(--border)",
                "margin": "8px",
            }
        )

    def _theme_buttons(self) -> Elem:
        return Row(
            Row(Icon("sun"), "light")
            .style({"cursor": "pointer", "opacity": "0.33", "align-items": "center", "gap": "6px"})
            .onclick(lambda: Session.require().set_theme("light")),
            Row(Icon("moon"), "dark")
            .style({"cursor": "pointer", "opacity": "0.33", "align-items": "center", "gap": "6px"})
            .onclick(lambda: Session.require().set_theme("dark")),
        ).style({"margin": "auto 0px 8px 0px", "justify-content": "center", "gap": "32px"})

    def _click_task(self, task: Task) -> None:
        self._content.set(PageTask(self._engine, task))

    def _click_process(self, execution: Execution) -> None:
        self._content.set(PageProcess(self._engine, execution))

    def _processes(self) -> Elem:
        column = Column()

        def set_column() -> None:
            column.clear()

            executions = self._executions()
            if executions:
                column.append(self._header("Processes"))

            statuses: dict[str, Signal[int | None]] = {}
            for execution in executions:
                # Reactive icon
                icon = Icon("")
                status = Signal(execution.process.poll())
                Effect(lambda: icon.set_icon(self.icon_status(status())))
                statuses[execution.run.id] = status

                def handle_click(event: ClickEvent, execution: Execution) -> None:
                    self._click_process(execution)

                column.append(
                    Div(
                        icon,
                        Column(
                            Span(execution.task.label()),
                            Span(execution.method.label()),
                        ).style({"font-size": "12px"}),
                    )
                    .style(
                        {
                            "display": "flex",
                            "align-items": "center",
                            "gap": "8px",
                            "height": "40px",
                            "padding": "0px 8px",
                            "cursor": "pointer",
                        }
                    )
                    .onclick(partial(handle_click, execution=execution))
                )

            def refresh_statuses() -> None:
                for execution in self._executions():
                    statuses[execution.run.id].set(execution.process.poll())

            column.append(Timer(refresh_statuses, seconds=1.0, repeat=True))

        Effect(set_column)
        return column

    def icon_status(self, status: int | None) -> str:
        if status is None:
            return "loading"
        elif status == 0:
            return "success"
        else:
            return "error"

    def _refresh(self) -> None:
        self._executions.set(self._engine.executions)


class PageNewTask(Div):
    def __init__(self, engine: Engine) -> None:
        super().__init__()
        self._engine = engine
        self._setup()

    def _setup(self) -> None:
        for task_type in self._engine.bench.task_types:
            self.append(Button(task_type.type_name()).onclick(lambda: self._create_task(task_type)))

    def _create_task(self, task_type: type[Task]) -> None:
        params = task_type.params()

        def handler(values: dict[str, int | float | str]):
            self._engine.create_task(task_type, **values)

        prompt(
            f"Create new {task_type.type_name()}",
            "Fill in parameters please",
            params,
            handler=handler,
        )


class PageProcess(Div):
    def __init__(self, engine: Engine, execution: Execution) -> None:
        super().__init__()
        self._engine = engine
        self._execution = execution
        self._setup()

    def _setup(self) -> None:
        task = self._execution.task
        method = self._execution.method
        process = self._execution.process
        created_at = self._execution.created_at

        status = Signal(process.poll())
        stdout = Signal(process.stdout)

        stdout_html = HTML("")
        Effect(lambda: stdout_html.set_html(ansi2html(stdout())))

        status_span = Span()
        Effect(lambda: status_span.clear().append(self._process_status(status())))

        def timer_callback() -> None:
            status.set(process.poll())
            stdout.set(process.stdout)

            if status() is not None:
                timer.unmount()

        timer = Timer(timer_callback, 1.0, repeat=True)

        self.clear()
        self.append(
            H3("Process information"),
            Div(
                Span("Task").style({"font-weight": "bold"}),
                Span(task.label()),
                Span("Method").style({"font-weight": "bold"}),
                Span(method.label()),
                Span("Created at").style({"font-weight": "bold"}),
                Span(created_at.strftime("%B %d, %Y, %H:%M:%S")),
                Span("Status").style({"font-weight": "bold"}),
                status_span,
            ).style(
                {
                    "display": "grid",
                    "grid-template-columns": "repeat(2, max-content)",
                    "grid-gap": "8px 16px",
                    "margin-bottom": "16px",
                    "align-items": "start",
                }
            ),
            Div(
                Details(
                    Summary("Output").style({"font-weight": "bold"}),
                    Pre(Code(stdout_html).style({"padding": "16px"})),
                    timer,
                ).set_attr("open", "")
            ),
        )

    def _process_status(self, status: int | None) -> Elem:
        if status is None:
            return Span("Running..").style({"font-style": "italic"})
        if status == 0:
            return Span("Done").style({"font-weight": "bold", "color": "var(--green)"})
        else:
            return Span("Failed").style({"font-weight": "bold", "color": "var(--red)"})


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

        selected_groups = Signal[list[RunGroup]]([])

        checkboxes: list[Checkbox] = []

        def update_selected_groups() -> None:
            selected_groups.set([group for group, checkbox in zip(groups, checkboxes) if checkbox.checked])

        for group in groups:
            try:
                method = self._engine.cache.select_method(group.method_id)
                method_label = method.label()
            except Exception as err:
                Session.require().log(
                    f"Failed to get method with ID {group.method_id}",
                    details=Pre(Code(str(err))),
                    level="error",
                )
                method_label = "?"

            checkbox = Checkbox(
                Span(
                    Span(method_label).style(
                        {
                            "background-color": group.color,
                            "color": "var(--white)",
                            "padding": "3px 6px",
                            "border-radius": "4px",
                        }
                    ),
                    " ",
                    f"({len(group.runs)} runs)",
                )
            ).onclick(update_selected_groups)
            checkboxes.append(checkbox)

        self.append(Column(checkboxes))

        self.append(H3("Metrics"))

        metrics = self._task.metrics()

        self.append(
            Div(
                [create_metric_elem(self._engine, name, metric, selected_groups) for name, metric in metrics.items()]
            ).style({"display": "flex", "gap": "16px", "justify-content": "center", "flex-wrap": "wrap"})
        )

    def _create_experiment(self) -> None:
        DialogNewExperiment(self._engine, self._task).mount().show_modal()


def create_metric_elem(engine: Engine, name: str, metric: Metric, selected_groups: Signal[list[RunGroup]]) -> Elem:
    if isinstance(metric, Time):
        return TimeElem(engine, name, metric, selected_groups)
    if isinstance(metric, Graph):
        return GraphElem(engine, name, metric, selected_groups)
    if isinstance(metric, Table):
        return Div("Metric [Table]")

    msg = f"No visualization for metric of type '{type(metric)}'"
    raise NotImplementedError(msg)


class TimeElem(Panel):
    """Component to visualize the :py:class:`Time` metric."""

    def __init__(self, engine: Engine, name: str, time: Time, selected_groups: Signal[list[RunGroup]]) -> None:
        super().__init__()
        self._engine = engine
        self._name = name
        self._time = time
        self._selected_groups = selected_groups
        Effect(self._setup)

    def _setup(self) -> None:
        keys = self._time.keys
        groups = self._selected_groups()

        self.clear()
        self.style(
            {
                "padding": "16px",
                "display": "none" if len(groups) == 0 else None,
            }
        )
        self.append(
            Span(self._name).style(
                {
                    "font-weight": "bold",
                    "font-size": "1.125rem",
                    "margin-bottom": "16px",
                    "display": "block",
                    "text-align": "center",
                }
            ),
        )

        data = Div().style(
            {
                "display": "grid",
                "grid-template-columns": f"repeat({1 + len(keys)}, max-content)",
                "grid-gap": "8px 16px",
                "margin": "16px 0px",
                "align-items": "center",
                "justify-content": "space-around",
                "justify-items": "center",
            }
        )
        self.append(data)

        data.append(Div(""))
        for key in keys:
            data.append(Div(key).style({"font-style": "italic"}))

        for group in groups:
            timedeltas: dict[str, list[timedelta]] = {key: [] for key in keys}
            for run in group.runs:
                if run.status != "done":
                    continue
                metrics = self._engine.evaluate_run(run)
                for key in keys:
                    assert key in metrics, "expected key in metrics"
                    timedeltas[key].append(metrics[key])
            averages = {
                key: timedelta_to_str(sum(ts, start=timedelta(seconds=0)) / len(ts)) if len(ts) > 0 else "-"
                for key, ts in timedeltas.items()
            }

            data.append(
                Row(
                    Div().style(
                        {
                            "background-color": group.color,
                            "width": "24px",
                            "height": "24px",
                            "border-radius": "12px",
                        }
                    ),
                ).style({"align-items": "center", "gap": "8px"})
            )
            for key in keys:
                data.append(Div(averages[key]))


class GraphElem(Panel):
    """Component to visualize the :py:class:`Graph` metric."""

    def __init__(self, engine: Engine, name: str, graph: Graph, selected_groups: Signal[list[RunGroup]]) -> None:
        super().__init__()
        self._engine = engine
        self._name = name
        self._graph = graph
        self._selected_groups = selected_groups
        Effect(self._setup)

    def _setup(self) -> None:
        groups = self._selected_groups()

        self.clear()
        self.style(
            {
                "padding": "16px",
                "display": "none" if len(groups) == 0 else None,
            }
        )

        axes = Axes(width=512, height=384).set_grid(True)
        axes.onmount(lambda: axes.render())

        if self._graph.title is not None:
            axes.set_title(self._graph.title)
        if self._graph.xlabel is not None:
            axes.set_xlabel(self._graph.xlabel)
        if self._graph.ylabel is not None:
            axes.set_ylabel(self._graph.ylabel)

        for group in groups:
            for run in group.runs:
                if run.status != "done":
                    continue

                metrics = self._engine.evaluate_run(run)
                xs = metrics[self._graph.keys_xs]
                ys = metrics[self._graph.keys_ys]

                axes.add_plot(SlashGraph(xs, ys, color=group.color))

        self.append(axes)


@dataclass
class RunGroup:
    method_id: str
    color: str
    runs: list[Run]


COLORS = [
    "var(--blue)",
    "var(--yellow)",
    "var(--green)",
    "var(--red)",
    "var(--indigo)",
    "var(--orange)",
    "var(--purple)",
    "var(--teal)",
    "var(--pink)",
    "var(--aubergine)",
]


def group_runs(runs: list[Run]) -> list[RunGroup]:
    color_index = 0
    groups: dict[str, RunGroup] = {}
    for run in runs:
        if run.method_id not in groups:
            groups[run.method_id] = RunGroup(method_id=run.method_id, runs=[], color=COLORS[color_index % len(COLORS)])
            color_index += 1
        groups[run.method_id].runs.append(run)
    return list(groups.values())


class DialogNewExperiment(Dialog):
    def __init__(self, engine: Engine, task: Task) -> None:
        super().__init__()
        self._engine = engine
        self._task = task
        self._setup()

    def _setup(self) -> None:
        method_types = {method_type.type_name(): method_type for method_type in self._engine.bench.method_types}

        form_wrapper = Div().style({"margin-top": "16px"})

        def handle_change_method() -> None:
            method_type = method_types[select.value]
            form_wrapper.clear()
            form_wrapper.append(Form(method_type.params()))
            start.disabled = False

        def handle_click_start() -> None:
            method_type = method_types[select.value]
            form = cast(Form, form_wrapper.children[0])
            method = method_type(**{param.name: form.value(param) for param in method_type.params()})
            self.unmount()
            self._engine.launch_run(self._task, method)

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
            ).style({"justify-content": "center", "gap": "16px", "margin-top": "16px"})
        )
        start.disabled = True


INPUT_TYPE: dict[type[int | float | str], str] = {
    bool: "number",
    int: "number",
    float: "number",
    str: "text",
}


class Form(Div):
    def __init__(self, params: list[Param]) -> None:
        super().__init__()
        self._params = {param.name: param for param in params}
        self._setup()

    def _setup(self) -> None:
        # Create inputs
        self._inputs: dict[str, Input] = {}
        for name, param in self._params.items():
            self._inputs[name] = (input := Input())
            input.type = INPUT_TYPE.get(param.type, "text")
            if param.default is not None:
                input.value = str(param.default)

        # Create grid of inputs
        self.append(
            Column(
                Div(*[[Span(name), self._inputs[name]] for name in self._params]).style(
                    {
                        "display": "grid",
                        "grid-template-columns": "repeat(2, auto)",
                        "align-items": "center",
                        "gap": "8px",
                    }
                ),
            ).style({"gap": "16px"})
        )

    def value(self, param: Param) -> int | float | str:
        value = self._inputs[param.name].value
        if param.type is int:
            return int(value)
        if param.type is float:
            return float(value)
        return str(value)
