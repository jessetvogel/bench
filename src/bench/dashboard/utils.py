from collections.abc import Callable, Collection
from dataclasses import dataclass
from datetime import timedelta

from slash.core import Elem, Session
from slash.events import ClickEvent, SupportsOnClick
from slash.js import JSFunction

from bench.templates import Run


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
