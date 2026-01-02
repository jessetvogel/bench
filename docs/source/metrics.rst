Metrics
=======

To add metrics to a task, simply add a method to the :py:class:`~bench.templates.Task` subclass that is decorated by a :py:class:`~bench.templates.Metric` instance,
such as in the following example.

.. code-block:: python

    from datetime import timedelta

    from bench.templates import Task, Result
    from bench.metrics import Time

    class MyTask(Task):

        ...

        @Time("Time metrics")
        def time(self, result: Result) -> dict[str, timedelta]:
            return {
                "total time": timedelta(...),
                "init time": timedelta(...),
                "solve time": timedelta(...),
            }


The following :py:class:`~bench.templates.Metric` types are available in the :py:mod:`bench.metrics` module:

- The :py:class:`~bench.metrics.Time` metric is used for time information. The method should return a dictionary of type :py:const:`dict[str, timedelta]`, as in the above example.

- The :py:class:`~bench.metrics.Table` metric is used for tabular data. The method should return a dictionary of type :py:const:`dict[str, Any]`.

- The :py:class:`~bench.metrics.Graph` metric is used for 2D plots. The method should return a tuple of type :py:const:`tuple[list[float], list[float]]` containing a list of x-coordinates and a list of y-coordinates.
