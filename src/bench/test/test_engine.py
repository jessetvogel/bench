import random
import secrets
from pathlib import Path
from typing import Any, cast

import pytest

import bench.test.main as main
from bench._engine import Engine
from bench.templates import Param


@pytest.fixture
def engine() -> Engine:
    main_file = cast(str, main.__file__)
    path = Path(main_file)
    return Engine(path)


def test_engine_loads_bench(engine: Engine) -> None:
    """Check that engine can be created from file without errors."""


def test_engine_create_task(engine: Engine) -> None:
    """Check that engine can instantiate all types of tasks."""
    for task_type in engine.bench.task_types:
        args = _create_random_arguments(task_type.type_params())
        engine.create_task(task_type, **args)


def test_engine_create_method(engine: Engine) -> None:
    """Check that engine can instantiate all types of methods."""
    for method_type in engine.bench.method_types:
        args = _create_random_arguments(method_type.type_params())
        engine.create_method(method_type, **args)


def test_engine_execute_run(engine: Engine) -> None:
    """Check that engine can execute runs with all types of tasks and all types of methods."""
    for task_type in engine.bench.task_types:
        args = _create_random_arguments(task_type.type_params())
        task = engine.create_task(task_type, **args)
        for method_type in engine.bench.method_types:
            args = _create_random_arguments(method_type.type_params())
            method = engine.create_method(method_type, **args)
            engine.execute_run(task, method)


def _create_random_arguments(params: list[Param]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for param in params:
        if param.type is bool:
            values[param.name] = random.choice([True, False])
            continue
        if param.type is int:
            values[param.name] = random.randint(-10, +10)
            continue
        if param.type is float:
            values[param.name] = random.uniform(-10.0, +10.0)
            continue
        if param.type is str:
            values[param.name] = secrets.token_hex(8)
            continue
        raise NotImplementedError(f"param.type = {param.type}")
    return values
