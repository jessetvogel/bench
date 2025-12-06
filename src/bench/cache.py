from __future__ import annotations

import sqlite3
from pathlib import Path

from bench.serialization import from_json, to_json
from bench.templates import Bench, BenchError, Method, Result, Run, Task, Token
from bench.utils import hash_serializable

BENCH_CACHE = ".bench_cache"
GITIGNORE = ".gitignore"

SQL_INIT = [
    "CREATE TABLE `tasks` (`id` TEXT NOT NULL, `type` TEXT NOT NULL, `data` BLOB NOT NULL, PRIMARY KEY (`id`))",
    "CREATE TABLE `methods` (`id` TEXT NOT NULL, `type` TEXT NOT NULL, `data` BLOB NOT NULL, PRIMARY KEY (`id`))",
    "CREATE TABLE `runs` (`id` TEXT NOT NULL, `task` TEXT NOT NULL, `method` TEXT NOT NULL, `status` TEXT NOT NULL, `result` BLOB NOT NULL, PRIMARY KEY (`id`))",  # noqa: E501
]


class Cache:
    """Cache data manager."""

    def __init__(self, bench: Bench) -> None:
        self._bench = bench

        self._setup()

    def _setup(self) -> None:
        self._path = Path(".") / BENCH_CACHE

        # Check if working directory exists
        if not self._path.parent.is_dir():
            msg = f"Working directory `{self._path.parent}` does not exist"
            raise RuntimeError(msg)

        # Create cache directory
        self._path.mkdir(exist_ok=True)

        # Create .gitignore
        with (self._path / GITIGNORE).open("w") as file:
            file.write("*\n")

        # Connect to database
        self._db_connect()

    def _db_path(self) -> Path:
        """Path to database file."""
        return self._path / f"{self._bench.name}.db"  # TODO: make `bench.name` valid for filename

    def _db_connect(self) -> None:
        """Open the database corresponding to the problem."""
        db_path = self._db_path()
        db_already_exists = db_path.is_file()
        self._db = sqlite3.connect(db_path)
        if not db_already_exists:
            self._db_init()

    def _db_init(self) -> None:
        """Initialize the database."""
        cursor = self._db.cursor()
        for statement in SQL_INIT:
            cursor.execute(statement)
        self._db.commit()

    # PUBLIC API

    def insert_task(self, task: Task) -> None:
        """Insert task into database, if not already."""
        task_id = hash_serializable(task)
        cursor = self._db.cursor()
        cursor.execute("SELECT 1 FROM `tasks` WHERE `id` = ? LIMIT 1", (task_id,))
        if cursor.fetchone() is not None:
            return
        task_type = task.name()
        task_blob = to_json(task).encode()
        cursor.execute("INSERT INTO `tasks` VALUES (?, ?, ?)", (task_id, task_type, task_blob))
        self._db.commit()

    def insert_method(self, method: Method) -> None:
        """Insert method into database, if not already."""
        method_id = hash_serializable(method)
        cursor = self._db.cursor()
        cursor.execute("SELECT 1 FROM `methods` WHERE `id` = ? LIMIT 1", (method_id,))
        if cursor.fetchone() is not None:
            return
        method_type = method.name()
        method_blob = to_json(method).encode()
        cursor.execute("INSERT INTO `methods` VALUES (?, ?, ?)", (method_id, method_type, method_blob))
        self._db.commit()

    def insert_or_update_run(self, run: Run) -> None:
        """Insert run into database, or update it if already in the database."""
        result_blob = to_json(run.result).encode()
        cursor = self._db.cursor()
        cursor.execute("SELECT 1 FROM `runs` WHERE `id` = ? LIMIT 1", (run.id,))
        if cursor.fetchone() is not None:
            # Update
            cursor.execute(
                "UPDATE `runs` SET `status` = ?, `result` = ? WHERE `id` = ?",
                (run.status, result_blob, run.id),
            )
        else:
            # Insert
            cursor.execute(
                "INSERT INTO `runs` VALUES (?, ?, ?, ?, ?)",
                (run.id, run.task_id, run.method_id, run.status, result_blob),
            )
        self._db.commit()

    def select_task(self, task_id: str) -> Task:
        """Get task by id."""
        cursor = self._db.cursor()
        cursor.execute("SELECT `type`, `data` FROM `tasks` WHERE `id` = ? LIMIT 1", (task_id,))
        if (row := cursor.fetchone()) is None:
            msg = f"Could not find task with id '{task_id}'"
            raise ValueError(msg)
        task_type_name, task_blob = row
        assert isinstance(task_type_name, str)
        assert isinstance(task_blob, bytes)
        return self._parse_task(task_type_name, task_blob)

    def select_method(self, method_id: str) -> Method:
        """Get method by id."""
        cursor = self._db.cursor()
        cursor.execute("SELECT `type`, `data` FROM `methods` WHERE `id` = ? LIMIT 1", (method_id,))
        if (row := cursor.fetchone()) is None:
            msg = f"Could not find method with id '{method_id}'"
            raise ValueError(msg)
        method_type_name, method_blob = row
        assert isinstance(method_type_name, str)
        assert isinstance(method_blob, bytes)
        return self._parse_method(method_type_name, method_blob)

    def select_run(self, run_id: str) -> Run:
        """Get run by id."""
        cursor = self._db.cursor()
        cursor.execute("SELECT `task`, `method`, `status`, `result` FROM `runs` WHERE `id` = ? LIMIT 1", (run_id,))
        if (row := cursor.fetchone()) is None:
            msg = f"Could not find run with id `{run_id}`"
            raise ValueError(msg)
        task_id, method_id, status, result_blob = row
        assert isinstance(task_id, str)
        assert isinstance(method_id, str)
        assert isinstance(status, str)
        assert isinstance(result_blob, bytes)
        return self._parse_run(run_id, task_id, method_id, status, result_blob)

    def select_tasks(self) -> list[Task]:
        """Get all tasks in the database."""
        tasks: list[Task] = []
        cursor = self._db.cursor()
        cursor.execute("SELECT `type`, `data` FROM `tasks`")
        while (row := cursor.fetchone()) is not None:
            task_type_name, task_blob = row
            assert isinstance(task_type_name, str)
            assert isinstance(task_blob, bytes)
            tasks.append(self._parse_task(task_type_name, task_blob))
        return tasks

    def select_methods(self) -> list[Method]:
        """Get all methods in the database."""
        methods: list[Method] = []
        cursor = self._db.cursor()
        cursor.execute("SELECT `type`, `data` FROM `methods`")
        while (row := cursor.fetchone()) is not None:
            method_type_name, method_blob = row
            assert isinstance(method_type_name, str)
            assert isinstance(method_blob, bytes)
            methods.append(self._parse_method(method_type_name, method_blob))
        return methods

    def select_runs(self, task: Task) -> list[Run]:
        """Get all runs associated to the given task."""
        task_id = hash_serializable(task)
        runs: list[Run] = []
        cursor = self._db.cursor()
        cursor.execute("SELECT `id`, `method`, `status`, `result` FROM `runs` WHERE `task` = ?", (task_id,))
        while (row := cursor.fetchone()) is not None:
            run_id, method_id, status, result_blob = row
            assert isinstance(run_id, str)
            assert isinstance(method_id, str)
            assert isinstance(status, str)
            assert isinstance(result_blob, bytes)
            run = self._parse_run(run_id, task_id, method_id, status, result_blob)
            runs.append(run)
        return runs

    def _get_task_type(self, name: str) -> type[Task]:
        """Get task type by name."""
        if not hasattr(self, "_task_types"):
            self._task_types = {task_type.name(): task_type for task_type in self._bench.task_types()}
        if name not in self._task_types:
            msg = f"Unknown task type '{name}'"
            raise ValueError(msg)
        return self._task_types[name]

    def _get_method_type(self, name: str) -> type[Method]:
        """Get method type by name."""
        if not hasattr(self, "_method_types"):
            self._method_types = {method_type.name(): method_type for method_type in self._bench.method_types()}
        if name not in self._method_types:
            msg = f"Unknown method type '{name}'"
            raise ValueError(msg)
        return self._method_types[name]

    def _parse_task(self, task_type_name: str, task_blob: bytes) -> Task:
        task_type = self._get_task_type(task_type_name)
        return from_json(task_type, task_blob.decode())

    def _parse_method(self, method_type_name: str, method_blob: bytes) -> Method:
        method_type = self._get_method_type(method_type_name)
        return from_json(method_type, method_blob.decode())

    def _parse_run(self, run_id: str, task_id: str, method_id: str, status: str, result_blob: bytes) -> Run:
        result: None | Token | Result | BenchError
        if status == "pending":
            result = None
        elif status == "running":
            result = from_json(Token, result_blob.decode())
        elif status == "done":
            result = from_json(Result, result_blob.decode())
        elif status == "failed":
            result = from_json(BenchError, result_blob.decode())
        else:
            msg = f"Encountered status '{status}', expected 'running', 'done' or 'failed'"
            raise RuntimeError(msg)
        return Run(run_id, task_id, method_id, result)
