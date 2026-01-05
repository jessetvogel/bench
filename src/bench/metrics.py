from datetime import timedelta
from typing import Any

from bench.serialization import PlainData
from bench.templates import Metric


class Table(Metric[dict[str, Any]]):
    """Metric for tabular information.

    Any method decorated by this metric must return a dictionary of type :py:const:`dict[str, Any]`, where
    the keys correspond to the columns of the table, and the values correspond to the cells of the table.

    Example
    -------

    .. code-block:: python

        from typing import Any

        from bench.templates import Task, Result
        from bench.metrics import Table

        class MyTask(Task):

            @Table("Table title")
            def time(self, result: Result) -> dict[str, Any]:
                return {
                    "accuracy": ...,
                    "error": ...,
                    "cost": ...,
                }

    Args:
        title: Title of the table.
    """

    def __init__(self, title: str | None = None) -> None:
        self.title = title

    @classmethod
    def encode_value(cls, value: dict[str, Any]) -> PlainData:
        return {key: str(value) for key, value in value.items()}


class Time(Metric[dict[str, timedelta]]):
    """Metric for timing information.

    Any method decorated by this metric must return a dictionary of type :py:const:`dict[str, timedelta]`.

    Example
    -------

    .. code-block:: python

        from datetime import timedelta

        from bench.templates import Task, Result
        from bench.metrics import Time

        class MyTask(Task):

            @Time("Time information")
            def time(self, result: Result) -> dict[str, timedelta]:
                return {
                    "total time": timedelta(...),
                    "init time": timedelta(...),
                    "solve time": timedelta(...),
                }

    Args:
        title: Title of the time table.
    """

    def __init__(self, title: str | None = None):
        self.title = title

    @classmethod
    def encode_value(cls, value: dict[str, timedelta]) -> PlainData:
        return {key: t.total_seconds() for key, t in value.items()}


class Graph(Metric[tuple[list[float], list[float]]]):
    """Metric for 2D graphs.

    Any method decorated by this metric must return a tuple of type :py:const:`tuple[list[float], list[float]]`
    containing a list of x-coordinates and a list of y-coordinates.

    Example
    -------

    .. code-block:: python

        from bench.templates import Task, Result
        from bench.metrics import Graph

        class MyTask(Task):

            @Graph(
                title="Error rate vs. n",
                xlabel="n",
                ylabel="Error rate (%)",
            )
            def graph(self, result: Result) -> tuple[list[float], list[float]]:
                xs = [ ... ]
                ys = [ ... ]
                return xs, ys

    Args:
        title: Title of the graph.
        xlabel: Label of the x-axis.
        ylabel: Label of the y-axis.
        option_avg_std: If `True`, add the option to show the average and standard deviation of
            multiple runs of the same method. In this case, the x-coordinates of all runs must
            coincide.
    """

    def __init__(
        self,
        title: str | None,
        *,
        xlabel: str | None = None,
        ylabel: str | None = None,
        option_avg_std: bool = False,
    ):
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.option_avg_std = option_avg_std

    @classmethod
    def encode_value(cls, value: tuple[list[float], list[float]]) -> PlainData:
        xs, ys = value
        return {"xs": xs, "ys": ys}
