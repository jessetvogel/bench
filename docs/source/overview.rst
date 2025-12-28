Overview
========

The :py:mod:`bench` package provides an easy and fast way to set up a benchmark. It handles the data
management side of the benchmark, and provides a user-friendly dashboard for running the benchmark and
viewing the results.

A benchmark consist of various types of *tasks* and various types of *methods* to perform these tasks.
This information, and more, is stored in a :py:class:`Bench` instance, which represents the benchmark.
One can define a new type of task by creating a Python class that derives from :py:class:`~bench.templates.Task` class.
Similarly, a new class of methods is created as a Python class deriving from the :py:class:`~bench.templates.Method` class.
These classes can then be added to a :py:class:`Bench` instance using the :py:meth:`~bench.Bench.add_task_types` and :py:meth:`~bench.Bench.add_method_types` methods.

Next, the :py:meth:`~bench.Bench.set_run` method is used to set a callback function that executes a given task with a given method.
Such a callback function should return a :py:class:`~bench.templates.Result` instance (or an instance of a user-defined result type that was added using :py:meth:`~bench.Bench.add_result_types`). The result instance is automatically stored in a local database, and it should contain all the relevant raw results of the execution.
How the raw results are converted into insightful metrics is determined by the :py:meth:`~bench.templates.Task.analyze` method of the particular :py:class:`~bench.templates.Task` instance.

>>> # TODO: insert diagram with all concepts related by the relevant functions

**Example**

Open a new file ``my_benchmark.py`` and create a :py:class:`Bench` instance. Implement your own task type :py:class:`MyTask` and method type :py:class:`MyMethod`, and add them to the :py:class:`Bench` instance. Finally, implement a function for how to execute an instance of your task using an instance of your method.

.. code-block:: python

    from bench import Bench
    from bench.templates import Result

    from my_package import MyTask, MyMethod

    bench = Bench("My benchmark")

    bench.add_task_types(MyTask)
    bench.add_method_types(MyMethod)

    # Function for how to execute task using method
    @bench.set_run
    def run(task: MyTask, method: MyMethod) -> Result:
        # < your logic >
        return Result(...)

Run the command ``bench-dashboard my_benchmark.py`` to start the benchmark dashboard.
