Introduction
============

The :py:mod:`bench` package provides an easy and fast way to set up a benchmark. It handles the data
management side of the benchmark, and provides a user-friendly dashboard for running the benchmark and
viewing the results.

A benchmark consist of various types of *tasks* and various types of *methods* to perform these tasks.
This information, and more, is stored in a :py:class:`~bench.Bench` instance, which represents the benchmark.
One can define a new type of task by creating a Python class that derives from :py:class:`~bench.templates.Task` class.
Similarly, a new class of methods is created as a Python class deriving from the :py:class:`~bench.templates.Method` class.
These classes can then be added to a :py:class:`~bench.Bench` instance using :py:meth:`Bench.task() <bench.Bench.task>` and :py:meth:`Bench.method() <bench.Bench.method>`.

Next, the :py:meth:`Bench.run() <bench.Bench.run>` decorator is used to set a callback function that executes a given task with a given method.
Such a callback function should return a :py:class:`~bench.templates.Result` instance (e.g., a :py:class:`~bench.templates.PlainResult` or an instance of a user-defined result type that was added using :py:meth:`Bench.result() <bench.Bench.result>`). The result instance is automatically stored in a local database, and it should contain all the relevant raw results of the execution.

Raw results can be converted into insightful metrics by adding methods to the :py:class:`~bench.templates.Task` subclass,
which are decorated by a :py:class:`~bench.templates.Metric` instance.

>>> # TODO: insert diagram with all concepts related by the relevant functions

**Example**

Open a new file ``my_benchmark.py`` and create a :py:class:`~bench.Bench` instance. Implement your own task type :py:class:`MyTask`, method type :py:class:`MyMethod` and result type :py:class:`MyResult`, and add them to the :py:class:`~bench.Bench` instance. Finally, implement a function :py:meth:`run` to execute an instance of your task using an instance of your method.

.. code-block:: python

    from bench import Bench
    from bench.templates import Task, Method, Result

    bench = Bench("My benchmark")

    @bench.task
    class MyTask(Task): ...

    @bench.method
    class MyMethod(Method): ...

    @bench.result
    class MyResult(Result): ...

    @bench.run
    def run(task: MyTask, method: MyMethod) -> MyResult:
        # < your logic >
        return MyResult(...)

Run the command ``bench-dashboard my_benchmark.py`` to start the benchmark dashboard.
