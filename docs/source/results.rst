Results
=======

Handlers passed to :py:meth:`Bench.run() <bench.Bench.run>` should produce a :py:class:`~bench.templates.Result` instance.
This can either be a :py:class:`~bench.templates.PlainResult` instance, or an instance of a custom type of result.
Custom types of results are defined as subclasses of the :py:class:`~bench.templates.Result` class,
and should be added to the benchmark using :py:meth:`Bench.result() <bench.Bench.result>`.
Such a subclass must implement at least the following methods:

- :py:meth:`~bench.templates.Result.encode` and :py:meth:`~bench.templates.Result.decode` - for serialization of a result instance.

Furthermore, the subclass may optionally implement the following method:

- :py:meth:`~bench.templates.Result.type_label` - to set a custom label for the type of result (by default, the name of the class).
