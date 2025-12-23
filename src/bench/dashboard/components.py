from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from datetime import timedelta
from functools import partial
from typing import Any, Awaitable, Callable, cast

import numpy as np
from slash.basic import Axes, Checkbox, Icon, Tooltip, confirm
from slash.basic import DataTable as SlashDataTable
from slash.basic import FillBetween as SlashFillBetween
from slash.basic import Graph as SlashGraph
from slash.basic import Plot as SlashPlot
from slash.core import Children, Elem, Session
from slash.events import ClickEvent
from slash.html import H3, HTML, Button, Code, Details, Dialog, Div, Input, Option, P, Pre, Select, Span, Summary
from slash.layout import Column, Panel, Row
from slash.reactive import Effect, Signal

from bench.dashboard.ansi import ansi2html
from bench.dashboard.utils import Timer, prompt, timedelta_to_str
from bench.engine import Engine, Execution
from bench.logging import get_logger
from bench.metrics import Graph, Metric, Table, Time
from bench.templates import Param, Run, Task

FORM_STYLE = {
    "display": "grid",
    "grid-template-columns": "auto 160px",
    "align-items": "center",
    "gap": "8px",
    "min-width": "384px",
}

_LOGGER = get_logger("bench")


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
                "height": "calc(100dvh - 16px)",
                "margin": "8px",
                "padding": "8px",
                "border-radius": "8px",
                "box-sizing": "border-box",
                "background-color": "var(--bg)",
                "box-shadow": "var(--shadow)",
                "border": "1px solid var(--border-muted)",
            }
        )

        # Tasks
        self.append(
            self._header("Tasks", mini_button("+").onclick(lambda: self._content.set(PageNewTask(self._engine)))).style(
                {"justify-content": "space-between", "padding-right": "0px"}
            )
        )
        for task in self._engine.cache.select_tasks():

            def handle_click(event: ClickEvent, task: Task) -> None:
                self._click_task(task)

            self.append(self._item(task.label(), onclick=partial(handle_click, task=task)))

        # --------
        # self.append(self._separator())

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
                statuses[execution.id] = status

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
                    statuses[execution.id].set(execution.process.poll())

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
    """Page element for creating a new task."""

    def __init__(self, engine: Engine) -> None:
        super().__init__()
        self._engine = engine
        self._setup()

    def _setup(self) -> None:
        self.append(
            H3("Create new task"),
            P("Create a new task from one of the following types of tasks."),
            Div(
                *[
                    [
                        Button(task_type.type_label()).onclick(lambda _, t=task_type: self._create_task(t)),
                        Span(task_type.type_description()),
                    ]
                    for task_type in self._engine.bench.task_types
                ]
            ).style(
                {
                    "display": "grid",
                    "grid-template-columns": "repeat(2, max-content)",
                    "align-items": "center",
                    "gap": "8px 16px",
                }
            ),
        )

    def _create_task(self, task_type: type[Task]) -> None:
        params = task_type.params()

        def handler(values: dict[str, int | float | str]):
            try:
                self._engine.create_task(task_type, **values)
            except Exception:
                _LOGGER.exception(
                    "Failed to create task of type '%s' due to the following exception:",
                    task_type.__name__,
                )
                Session.require().log(
                    f"Failed to create task of type '{task_type.__name__}'",
                    details="See the console for details.",
                    level="error",
                )

        prompt(
            f"Create new {task_type.type_label()}",
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
        # Task label
        self.append(H3(self._task.label()))
        # Task description
        self.append(P(self._task.description()))
        # Dialog and button for new run
        self.append(dialog_new_run := DialogNewRun(self._engine, self._task))
        self.append(Button("New run").onclick(lambda: dialog_new_run.show_modal()))

        # Method selection
        self.append(
            Row(
                H3("Compare methods"),
                button_trash := mini_button(
                    Icon("trash").style({"opacity": "0.8", "--icon-size": "20px"}),
                ).onclick(self._delete_selected_runs),
            ).style({"align-items": "center", "gap": "16px"})
        )

        runs = self._engine.cache.select_runs(self._task)

        groups = group_runs(runs)

        self._selected_groups = Signal[list[RunGroup]]([])

        # Disable delete button when no groups are selected
        Effect(lambda: button_trash.set_disabled(not self._selected_groups()))

        # Create one checkbox row per group
        checkboxes: list[Checkbox] = []

        def update_selected_groups() -> None:
            self._selected_groups.set([group for group, checkbox in zip(groups, checkboxes) if checkbox.checked])

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

            # Description of the method parameters
            method_params_description = ", ".join(
                [f"{param.name} = {getattr(method, param.name, '?')}" for param in method.params()]
            )

            # Checkbox row of the form:
            # [x] <method label> <num runs> <method params description>
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
                    Span(f"({len(group.runs_done)} runs)").style({"color": "var(--gray)"}),
                    " ",
                    Span(method_params_description).style({"color": "var(--gray)", "font-size": "12px"}),
                )
            ).onclick(update_selected_groups)
            checkboxes.append(checkbox)

        self.append(Column(checkboxes))

        metrics = self._task.metrics()

        self.append(header_metrics := H3("Metrics"))
        Effect(lambda: header_metrics.style({"display": None if self._selected_groups() else "none"}))
        self.append(
            Div([create_metric_elem(self._engine, metric, self._selected_groups) for metric in metrics]).style(
                {"display": "flex", "gap": "16px", "flex-wrap": "wrap", "align-items": "flex-start"},
            )
        )

    async def _delete_selected_runs(self) -> None:
        # TODO: Clean up this method .. Contains duplicate code I think
        selected_groups = self._selected_groups()
        msg = Column(
            Span("Are you sure you want to delete the following runs?").style({"font-weight": "bold"}),
            Span("This action is irreversible."),
            [
                Span(
                    Span(self._engine.cache.select_method(group.method_id).label()).style(
                        {
                            "background-color": group.color,
                            "color": "var(--white)",
                            "padding": "3px 6px",
                            "border-radius": "4px",
                        }
                    ),
                    " ",
                    Span(f"({len(group.runs_done)} runs)").style({"color": "var(--gray)"}),
                )
                for group in selected_groups
            ],
        ).style({"gap": "12px"})
        if await confirm(msg):
            runs = [run for group in selected_groups for run in group.runs]
            self._engine.delete_runs(runs)
            # TODO: refresh?


def create_metric_elem(engine: Engine, metric: Metric, selected_groups: Signal[list[RunGroup]]) -> Elem:
    if isinstance(metric, Time):
        return TimeElem(engine, metric, selected_groups)
    if isinstance(metric, Graph):
        return GraphElem(engine, metric, selected_groups)
    if isinstance(metric, Table):
        return TableElem(engine, metric, selected_groups)

    msg = f"No visualization for metric of type '{type(metric)}'"
    raise NotImplementedError(msg)


class TimeElem(Panel):
    """Component to visualize the :py:class:`Time` metric."""

    def __init__(self, engine: Engine, time: Time, selected_groups: Signal[list[RunGroup]]) -> None:
        super().__init__()
        self._engine = engine
        self._time = time
        self._selected_groups = selected_groups
        Effect(self._setup)

    def _setup(self) -> None:
        keys = self._time.keys
        groups = self._selected_groups()

        self.clear()
        self.style({"padding": "16px", "display": "none" if len(groups) == 0 else None})

        data = Div().style(
            {
                "display": "grid",
                "grid-template-columns": f"repeat({1 + len(keys)}, max-content)",
                "grid-gap": "8px 16px",
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
            for run in group.runs_done:
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

    def __init__(self, engine: Engine, graph: Graph, selected_groups: Signal[list[RunGroup]]) -> None:
        super().__init__()
        self._engine = engine
        self._graph = graph
        self._selected_groups = selected_groups
        self._setup()
        Effect(self._plot)

    def _setup(self) -> None:
        self.clear()
        self.style({"display": "flex", "flex-direction": "column", "align-items": "center"})

        self._axes = Axes(width=512, height=384).set_grid(True)
        self._axes.onmount(lambda: self._axes.render())

        if self._graph.title is not None:
            self._axes.set_title(self._graph.title)
        if self._graph.xlabel is not None:
            self._axes.set_xlabel(self._graph.xlabel)
        if self._graph.ylabel is not None:
            self._axes.set_ylabel(self._graph.ylabel)

        self.append(self._axes)

        # "Show average" and "Show standard deviation"
        if self._graph.option_mean_std:
            # Create checkbox
            def on_click_checkbox_avg() -> None:
                self._checkbox_std.set_disabled(not self._checkbox_avg.checked)
                self._plot()

            self._checkbox_avg = Checkbox("Show average").onclick(on_click_checkbox_avg)
            self._checkbox_std = Checkbox("Show standard deviation").onclick(self._plot).set_disabled(True)
            self.append(Row(self._checkbox_avg, self._checkbox_std).style({"gap": "32px"}))

    def _plot(self) -> None:
        groups = self._selected_groups()
        # Hide panels if no groups are selected
        self.style({"padding": "16px", "display": "none" if len(groups) == 0 else "flex"})
        # Clear previous plots
        self._axes.clear_plots()
        # Plot each run in each group
        for group in groups:
            # Case "[ ] Show average" is checked
            if self._graph.option_mean_std and self._checkbox_avg.checked:
                for plot in self._create_avg_std_graphs(group.runs_done, group.color):
                    self._axes.add_plot(plot)
            # Case "[ ] Show average" is not checked
            else:
                for run in group.runs_done:
                    self._axes.add_plot(self._create_graph(run, group.color))
        # Render if possible
        if self._axes.is_mounted():
            self._axes.render()

    def _create_graph(self, run: Run, color: str) -> SlashPlot:
        # Evaluate run
        metrics = self._engine.evaluate_run(run)
        # Get `xs` and `ys` and create graph
        xs = metrics[self._graph.key_xs]
        ys = metrics[self._graph.key_ys]
        return SlashGraph(xs, ys, color=color)

    def _create_avg_std_graphs(self, runs: Collection[Run], color: str) -> list[SlashPlot]:
        # If there are no runs, return an empty list of plots
        if len(runs) == 0:
            return []
        # Evaluate runs
        metrics_per_run = [self._engine.evaluate_run(run) for run in runs]
        # Collect the `xs` (should be the same for all runs) and the `ys`
        xs = metrics_per_run[0][self._graph.key_xs]
        yss: list[list[float]] = []
        for metrics in metrics_per_run:
            assert metrics[self._graph.key_xs] == xs, "all xs must be the same for avg"
            yss.append(metrics[self._graph.key_ys])
        # Create plot of the average of the `ys`
        plots: list[SlashPlot] = []
        np_yss = np.array(yss)
        ys_avg = [float(y_avg) for y_avg in np_yss.mean(axis=0)]
        plots.append(SlashGraph(xs, ys_avg, color=color))
        # Create a plot of the standard deviation of the `ys`
        if self._checkbox_std.checked:
            ys_std = [float(y_std) for y_std in np_yss.std(axis=0)]
            ys_low = [float(y - std) for y, std in zip(ys_avg, ys_std)]
            ys_high = [float(y + std) for y, std in zip(ys_avg, ys_std)]
            plots.append(SlashFillBetween(xs, ys_low, ys_high, color=color, opacity=0.2))
        return plots


class TableElem(Div):
    """Component to visualize the :py:class:`Table` metric."""

    def __init__(self, engine: Engine, table: Table, selected_groups: Signal[list[RunGroup]]) -> None:
        super().__init__()
        self._engine = engine
        self._table = table
        self._selected_groups = selected_groups
        Effect(self._setup)

    def _setup(self) -> None:
        groups = self._selected_groups()

        self.clear()
        self.style({"display": "none" if len(groups) == 0 else None})

        self.append(table := SlashDataTable(["Method"] + list(self._table.keys)))
        data: list = []
        for group in groups:
            for run in group.runs_done:
                metrics = self._engine.evaluate_run(run)
                datum = {
                    "Method": Div().style(
                        {
                            "width": "24px",
                            "height": "24px",
                            "border-radius": "100%",
                            "background-color": group.color,
                            "margin": "auto",
                        }
                    )
                }
                for key in self._table.keys:
                    datum[key] = metrics[key]
                data.append(datum)
        table.set_data(data)


@dataclass
class RunGroup:
    method_id: str
    color: str
    runs: list[Run]

    @property
    def runs_done(self) -> Collection[Run]:
        return tuple(run for run in self.runs if run.status == "done")


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


class DialogNewRun(Dialog):
    def __init__(self, engine: Engine, task: Task) -> None:
        super().__init__()
        self._engine = engine
        self._task = task
        self._setup()

    def _setup(self) -> None:
        method_types = {method_type.type_label(): method_type for method_type in self._engine.bench.method_types}

        form_wrapper = Div()

        def handle_change_method() -> None:
            method_type = method_types[select.value]
            params = method_type.params()
            form_wrapper.clear()
            if params:
                form_wrapper.append(
                    Div().style({"background-color": "var(--border-muted)", "height": "1px", "margin": "16px 0px"})
                )
            form_wrapper.append(Form(params))
            start.disabled = False

        def handle_click_start() -> None:
            self.close()
            method_type = method_types[select.value]
            form = cast(Form, form_wrapper.children[-1])
            method_kwargs = {param.name: form.value(param) for param in method_type.params()}
            num_runs = int(input_num_runs.value)

            try:
                method = self._engine.create_method(method_type, **method_kwargs)
            except Exception:
                _LOGGER.exception(
                    "Failed to create method of type '%s' due to the following exception:",
                    method_type.__name__,
                )
                Session.require().log(
                    f"Failed to create method of type '{method_type.__name__}'",
                    details="See the console for details.",
                    level="error",
                )
                return

            self._engine.launch_run(self._task, method, num_runs=num_runs)

        self.append(H3(f"New run for {self._task.label()}"))
        self.append(
            Div(
                Span("Method"),
                select := Select(
                    [Option("-", disabled=True, hidden=True)] + [Option(name) for name in method_types]
                ).onchange(handle_change_method),
                Span("Number of runs"),
                input_num_runs := Input("number", value=str(1)),
            ).style(FORM_STYLE)
        )
        self.append(form_wrapper)
        self.append(
            Row(
                start := Button("Start").onclick(handle_click_start),
                Button("Cancel").onclick(lambda: self.close()),
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
    def __init__(self, params: Collection[Param]) -> None:
        super().__init__()
        self._params = tuple(params)
        self._setup()

    def _setup(self) -> None:
        # Create inputs
        self._inputs: dict[str, Input] = {}
        for param in self._params:
            self._inputs[param.name] = (input := Input())
            input.type = INPUT_TYPE.get(param.type, "text")
            if param.default is not None:
                input.value = str(param.default)

        # Create grid of inputs
        self.append(div := Div().style(FORM_STYLE))
        for param in self._params:
            # Each parameter has a row with name and input
            label = Row(Span(param.name)).style({"align-items": "center", "gap": "4px"})
            div.append(label, self._inputs[param.name])
            # If `param` has description, add help icon with tooltip
            if param.description is not None:
                label.append(
                    icon := Icon("help").style({"color": "var(--gray)", "--icon-size": "20px"}),
                    Tooltip(param.description, target=icon),
                )

    def value(self, param: Param) -> int | float | str:
        value = self._inputs[param.name].value
        if param.type is int:
            return int(value)
        if param.type is float:
            return float(value)
        return str(value)


def mini_button(*children: Children) -> Button:
    return Button(*children).style(
        {
            "min-width": "inherit",
            "width": "36px",
            "height": "36px",
            "padding": "0px",
            "display": "flex",
            "justify-content": "center",
            "align-items": "center",
        }
    )
