Tasks
=====

Types of tasks are defined as subclasses of the :py:class:`~bench.templates.Task` class,
and should be added to the benchmark using :py:meth:`Bench.task() <bench.Bench.task>`.
Such a subclass must implement at least the following methods:

- :py:meth:`~bench.templates.Task.encode` and :py:meth:`~bench.templates.Task.decode` - for serialization of a task instance.

Furthermore, the subclass may optionally implement any of the following methods:

- :py:meth:`~bench.templates.Task.type_label` - to set a custom label for the type of task (by default, the name of the class).
- :py:meth:`~bench.templates.Task.type_description` - to set a custom description for the type of task (by default, empty).
- :py:meth:`~bench.templates.Task.type_constructor` - to set a custom constructor for the task (by default, the class itself).
- :py:meth:`~bench.templates.Task.type_params` - to manually declare the parameters of the constructor for the task. By default, these parameters are automatically inferred from the constructor. Manual declaration of the parameters can be useful, for instance, when the `options` field of a :py:class:`~bench.templates.Param` needs to be computed dynamically.
- :py:meth:`~bench.templates.Task.label` - to set a custom label for a task instance.
- :py:meth:`~bench.templates.Task.description` - to set a custom description for a task instance.

Finally, a task subclass may implement any number of `metric` methods. This is explained in the section :ref:`metrics`.
