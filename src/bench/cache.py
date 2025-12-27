from __future__ import annotations

import sqlite3
from pathlib import Path

from bench import Bench
from bench.logging import RESET, WHITE, get_logger
from bench.serialization import from_json, to_json
from bench.templates import BenchError, Method, Result, Run, Task, Token
from bench.utils import hash_serializable

BENCH_CACHE = ".bench_cache"
GITIGNORE = ".gitignore"

SQL_INIT = [
    "CREATE TABLE `tasks` (`id` TEXT NOT NULL, `type` TEXT NOT NULL, `data` BLOB NOT NULL, PRIMARY KEY (`id`))",
    "CREATE TABLE `methods` (`id` TEXT NOT NULL, `type` TEXT NOT NULL, `data` BLOB NOT NULL, PRIMARY KEY (`id`))",
    "CREATE TABLE `runs` (`id` TEXT NOT NULL, `task` TEXT NOT NULL, `method` TEXT NOT NULL, `status` TEXT NOT NULL, `type` TEXT NOT NULL, `result` BLOB NOT NULL, PRIMARY KEY (`id`))",  # noqa: E501
]


class Cache:
    """Cache data manager."""

    def __init__(self, bench: Bench) -> None:
        self._bench = bench
        self._logger = get_logger("bench")
        self._tasks: dict[str, Task] = {}
        self._methods: dict[str, Method] = {}
        self._runs: dict[str, Run] = {}
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
        self._tasks[task_id] = task
        cursor = self._db.cursor()
        cursor.execute("SELECT 1 FROM `tasks` WHERE `id` = ? LIMIT 1", (task_id,))
        if cursor.fetchone() is not None:
            return
        task_type = task.type_label()
        task_blob = to_json(task).encode()
        cursor.execute("INSERT INTO `tasks` VALUES (?, ?, ?)", (task_id, task_type, task_blob))
        self._db.commit()

    def insert_method(self, method: Method) -> None:
        """Insert method into database, if not already."""
        method_id = hash_serializable(method)
        self._methods[method_id] = method
        cursor = self._db.cursor()
        cursor.execute("SELECT 1 FROM `methods` WHERE `id` = ? LIMIT 1", (method_id,))
        if cursor.fetchone() is not None:
            return
        method_type = method.type_label()
        method_blob = to_json(method).encode()
        cursor.execute("INSERT INTO `methods` VALUES (?, ?, ?)", (method_id, method_type, method_blob))
        self._db.commit()

    def insert_or_update_run(self, run: Run) -> None:
        """Insert run into database, or update it if already in the database."""
        result_blob = to_json(run.result).encode()
        result_type_name = run.result.type_label() if isinstance(run.result, Result) else ""
        cursor = self._db.cursor()
        cursor.execute("SELECT 1 FROM `runs` WHERE `id` = ? LIMIT 1", (run.id,))
        if cursor.fetchone() is not None:
            # Update
            cursor.execute(
                "UPDATE `runs` SET `status` = ?, `type` = ?, `result` = ? WHERE `id` = ?",
                (run.status, result_type_name, result_blob, run.id),
            )
        else:
            # Insert
            cursor.execute(
                "INSERT INTO `runs` VALUES (?, ?, ?, ?, ?, ?)",
                (run.id, run.task_id, run.method_id, run.status, result_type_name, result_blob),
            )
        self._db.commit()

    def select_task(self, task_id: str) -> Task:
        """Get task by id.

        Raises an exception no task can be found with the given ID.
        Raises an exception when the task cannot be deserialized properly.
        """
        if task_id in self._tasks:
            return self._tasks[task_id]
        cursor = self._db.cursor()
        cursor.execute("SELECT `type`, `data` FROM `tasks` WHERE `id` = ? LIMIT 1", (task_id,))
        if (row := cursor.fetchone()) is None:
            msg = f"Could not find task with ID '{task_id}'"
            raise ValueError(msg)
        task_type_name, task_blob = row
        assert isinstance(task_type_name, str)
        assert isinstance(task_blob, bytes)
        task = self._parse_task(task_type_name, task_blob)
        self._tasks[task_id] = task
        return task

    def select_method(self, method_id: str) -> Method:
        """Get method by id.

        Raises an exception no method can be found with the given ID.
        Raises an exception when the method cannot be deserialized properly.
        """
        if method_id in self._methods:
            return self._methods[method_id]
        cursor = self._db.cursor()
        cursor.execute("SELECT `type`, `data` FROM `methods` WHERE `id` = ? LIMIT 1", (method_id,))
        if (row := cursor.fetchone()) is None:
            msg = f"Could not find method with ID '{method_id}'"
            raise ValueError(msg)
        method_type_name, method_blob = row
        assert isinstance(method_type_name, str)
        assert isinstance(method_blob, bytes)
        method = self._parse_method(method_type_name, method_blob)
        self._methods[method_id] = method
        return method

    def select_run(self, run_id: str) -> Run:
        """Get run by ID."""
        cursor = self._db.cursor()
        cursor.execute(
            "SELECT `task`, `method`, `status`, `type`, `result` FROM `runs` WHERE `id` = ? LIMIT 1", (run_id,)
        )
        if (row := cursor.fetchone()) is None:
            msg = f"Could not find run with ID `{run_id}`"
            raise ValueError(msg)
        task_id, method_id, status, result_type_name, result_blob = row
        assert isinstance(task_id, str)
        assert isinstance(method_id, str)
        assert isinstance(status, str)
        assert isinstance(result_type_name, str)
        assert isinstance(result_blob, bytes)
        return self._parse_run(run_id, task_id, method_id, status, result_type_name, result_blob)

    def select_tasks(self) -> list[Task]:
        """Returns a list of all tasks in the database.

        For each task that cannot be deserialized properly, an error is logged.
        """
        tasks: list[Task] = []
        cursor = self._db.cursor()
        cursor.execute("SELECT `type`, `data` FROM `tasks`")
        while (row := cursor.fetchone()) is not None:
            task_type_name, task_blob = row
            assert isinstance(task_type_name, str)
            assert isinstance(task_blob, bytes)
            try:
                task = self._parse_task(task_type_name, task_blob)
                tasks.append(task)
            except Exception:
                msg = (
                    f"Failed to deserialize task of type '{task_type_name}':\n"  # .
                    f"{WHITE}{task_blob.decode()}{RESET}"
                )
                self._logger.exception(msg)
        return tasks

    def select_methods(self) -> list[Method]:
        """Returns a list of all methods in the database.

        For each method that cannot be deserialized properly, an error is logged.
        """
        methods: list[Method] = []
        cursor = self._db.cursor()
        cursor.execute("SELECT `type`, `data` FROM `methods`")
        while (row := cursor.fetchone()) is not None:
            method_type_name, method_blob = row
            assert isinstance(method_type_name, str)
            assert isinstance(method_blob, bytes)
            try:
                method = self._parse_method(method_type_name, method_blob)
            except Exception as err:
                msg = f"Failed to deserialize method of type '{method_type_name}' ({err}):\n\n{method_blob.decode()}"
                self._logger.error(msg)
            methods.append(method)
        return methods

    def select_runs(self, task: Task) -> list[Run]:
        """Returns a list of all runs associated with the given task.

        For each run that cannot be deserialized properly, an error is logged.
        """
        task_id = hash_serializable(task)
        runs: list[Run] = []
        cursor = self._db.cursor()
        cursor.execute("SELECT `id`, `method`, `status`, `type`, `result` FROM `runs` WHERE `task` = ?", (task_id,))
        while (row := cursor.fetchone()) is not None:
            run_id, method_id, status, result_type_name, result_blob = row
            assert isinstance(run_id, str)
            assert isinstance(method_id, str)
            assert isinstance(status, str)
            assert isinstance(result_type_name, str)
            assert isinstance(result_blob, bytes)
            if run_id in self._runs:
                run = self._runs[run_id]
            else:
                try:
                    run = self._parse_run(run_id, task_id, method_id, status, result_type_name, result_blob)
                except Exception as err:
                    self._logger.error(
                        f"Failed to deserialize method of type '{result_type_name}' ({err}):\n\n{result_blob.decode()}"
                    )
                if run.status != "pending":
                    self._runs[run_id] = run
            runs.append(run)
        return runs

    def delete_runs(self, runs: list[Run]) -> None:
        """Delete runs from the database."""
        cursor = self._db.cursor()
        BATCH_SIZE = 128  # delete in batches for efficiency
        for i in range(0, len(runs), BATCH_SIZE):
            run_ids = tuple(run.id for run in runs[i : i + BATCH_SIZE])
            placeholders = ",".join(["?" for _ in run_ids])
            cursor.execute(f"DELETE FROM `runs` WHERE `id` IN ({placeholders})", run_ids)
        self._db.commit()

    def _parse_task(self, task_type_name: str, task_blob: bytes) -> Task:
        task_type = self._bench.get_task_type(task_type_name)
        return from_json(task_type, task_blob.decode())

    def _parse_method(self, method_type_name: str, method_blob: bytes) -> Method:
        method_type = self._bench.get_method_type(method_type_name)
        return from_json(method_type, method_blob.decode())

    def _parse_run(
        self, run_id: str, task_id: str, method_id: str, status: str, result_type_name: str, result_blob: bytes
    ) -> Run:
        result: Result | Token | BenchError
        if status == "pending":
            result = from_json(Token, result_blob.decode())
        elif status == "done":
            result_type = self._bench.get_result_type(result_type_name)
            result = from_json(result_type, result_blob.decode())
        elif status == "failed":
            result = from_json(BenchError, result_blob.decode())
        else:
            msg = f"Encountered status '{status}', expected 'pending', 'done' or 'failed'"
            raise RuntimeError(msg)
        return Run(run_id, task_id, method_id, result)
