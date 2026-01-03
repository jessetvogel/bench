Methods
=======

Types of methods are defined as subclasses of the :py:class:`~bench.templates.Method` class. Such a subclass must implement at least the following methods:

- :py:meth:`~bench.templates.Method.encode` and :py:meth:`~bench.templates.Method.decode` - for serialization of a method instance.

Furthermore, the subclass may optionally implement any of the following methods:

- :py:meth:`~bench.templates.Method.type_label` - to set a custom label for the type of methods (by default, the name of the class).
- :py:meth:`~bench.templates.Method.type_description` - to set a custom description for the type of methods (by default, empty).
- :py:meth:`~bench.templates.Method.type_constructor` - to set a custom constructor for the method (by default, the class itself).
- :py:meth:`~bench.templates.Method.type_params` - to manually declare the parameters of the constructor for the method. By default, these parameters are automatically inferred from the constructor. Manual declaration of the parameters can be useful, for instance, when the `options` field of a :py:class:`~bench.templates.Param` needs to be computed dynamically.
- :py:meth:`~bench.templates.Method.label` - to set a custom label for a method instance.
- :py:meth:`~bench.templates.Method.description` - to set a custom description for a method instance.
