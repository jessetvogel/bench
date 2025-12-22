from collections.abc import Callable
from datetime import timedelta

from slash.core import Elem, Handler, Session
from slash.events import ClickEvent, SupportsOnClick
from slash.html import Button, Dialog, Div, Input, Span
from slash.js import JSFunction
from slash.layout import Column, Row

from bench.templates import Param

INPUT_TYPE: dict[type[int | float | str], str] = {
    bool: "number",
    int: "number",
    float: "number",
    str: "text",
}


def prompt(
    title: str,
    description: str,
    params: list[Param],
    handler: Handler[dict[str, int | float | str]],
) -> None:
    # Create inputs
    inputs: dict[str, Input] = {}
    for param in params:
        inputs[param.name] = (input := Input())
        input.type = INPUT_TYPE.get(param.type, "text")
        if param.default is not None:
            input.value = str(param.default)

    dialog: Dialog

    def submit() -> None:
        dialog.close()
        values: dict[str, int | float | str] = {}
        for param in params:
            value = inputs[param.name].value
            if param.type is bool:
                values[param.name] = bool(value)
            elif param.type is int:
                values[param.name] = int(value)
            elif param.type is float:
                values[param.name] = float(value)
            else:
                values[param.name] = value
        Session.require().call_handler(handler, values)

    dialog = Dialog(
        Column(
            Div(title).style({"font-size": "1.5rem", "font-weight": "bold"}),
            Div(description),
            Div(*[[Span(param.name), inputs[param.name]] for param in params]).style(
                {
                    "display": "grid",
                    "grid-template-columns": "repeat(2, auto)",
                    "align-items": "center",
                    "gap": "8px",
                }
            ),
            Row(
                Button("Submit").onclick(submit),
                Button("Cancel").onclick(lambda: dialog.close()),
            ).style({"justify-content": "center", "gap": "16px"}),
        ).style({"gap": "16px"})
    ).style({"max-width": "512px"})

    dialog.mount()
    dialog.show_modal()


def timedelta_to_str(t: timedelta) -> str:
    """Format timedelta into read-friendly format."""
    seconds = t.total_seconds()
    if seconds < 1e-3:
        microseconds = round(seconds * 1e6)
        return f"{microseconds} µs"
    elif seconds < 1:
        milliseconds = round(seconds * 1e3)
        return f"{milliseconds} ms"
    elif seconds < 60:
        return f"{seconds:.1f} sec"
    elif seconds < 60 * 60:
        seconds = round(seconds)
        return f"{seconds // 60} min {seconds % 60} sec"
    elif seconds < 60 * 60 * 24:
        minutes = round(seconds / 60)
        return f"{minutes // 60} hrs {minutes % 60} min"
    else:
        hours = round(seconds / 60 / 60)
        return f"{hours // 24} days {hours % 24} hrs"


_JS_TIMER = JSFunction(
    ["id", "t"],
    """
setTimeout(function () {
    const elem = document.getElementById(id);
    if (elem !== null) elem.click();
}, t);
    """,
)


class Timer(Elem, SupportsOnClick):
    """Invisible element that calls a callback after some time."""

    def __init__(self, callback: Callable[[], None], seconds: float, *, repeat: bool = False) -> None:
        super().__init__("div")

        self._callback = callback
        self._seconds = seconds
        self._repeat = repeat

        self.style({"display": "none"})
        self.onclick(self._handle_click)

        self._start_timer()

    def _start_timer(self) -> None:
        Session.require().execute(_JS_TIMER, [self.id, self._seconds * 1000.0])

    def _handle_click(self, event: ClickEvent) -> None:
        self._callback()
        if self._repeat:
            self._start_timer()
