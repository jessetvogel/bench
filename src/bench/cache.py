from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Generic

from bench.serialization import from_json, serializable_id, to_json
from bench.templates import METHOD, RESULT, TASK, Bench, BenchError, Run, Token

BENCH_CACHE = ".bench_cache"
GITIGNORE = ".gitignore"

SQL_INIT = [
    "CREATE TABLE `tasks` (`id` TEXT NOT NULL, `data` BLOB NOT NULL, PRIMARY KEY (`id`))",
    "CREATE TABLE `methods` (`id` TEXT NOT NULL, `data` BLOB NOT NULL, PRIMARY KEY (`id`))",
    "CREATE TABLE `runs` (`id` INTEGER NOT NULL, `task` TEXT NOT NULL, `method` TEXT NOT NULL, `status` TEXT NOT NULL, `result` BLOB NOT NULL, PRIMARY KEY (`id`))",  # noqa: E501
]


class Cache(Generic[TASK, METHOD, RESULT]):
    """Cache data manager."""

    def __init__(self, bench: Bench[TASK, METHOD, RESULT]) -> None:
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

    def insert_task(self, task: TASK) -> None:
        """Insert task into database."""
        task_id = serializable_id(task)
        task_blob = to_json(task).encode()

        cursor = self._db.cursor()
        cursor.execute("INSERT INTO `tasks` VALUES (?, ?)", (task_id, task_blob))
        self._db.commit()

    def insert_method(self, method: METHOD) -> None:
        """Insert method into database."""
        method_id = serializable_id(method)
        method_blob = to_json(method).encode()

        cursor = self._db.cursor()
        cursor.execute("INSERT INTO `methods` VALUES (?, ?)", (method_id, method_blob))
        self._db.commit()

    def insert_or_update_run(self, run: Run[RESULT]) -> None:
        """Insert run into database, or update it if already in the database."""
        result_blob = to_json(run.result).encode()

        cursor = self._db.cursor()
        cursor.execute("SELECT 1 FROM `runs` WHERE `id` = ? LIMIT 1", (run.id,))
        if cursor.fetchone() is None:
            # Insert
            cursor.execute(
                "INSERT INTO `runs` VALUES (?, ?, ?, ?, ?)",
                (run.id, run.task_id, run.method_id, run.status, result_blob),
            )
        else:
            # Update
            cursor.execute(
                "UPDATE `runs` SET `status` = ?, `result` = ? WHERE `id` = ?",
                (run.status, result_blob, run.id),
            )
        self._db.commit()

    def select_tasks(self) -> list[TASK]:
        """Return all tasks that are present in the cache."""
        tasks: list[TASK] = []
        cursor = self._db.cursor()
        cursor.execute("SELECT `data` FROM `tasks`")
        while (row := cursor.fetchone()) is not None:
            # TODO: WRAP IN TRY EXCEPT AND PRINT WARNING IF FAILS
            assert isinstance(blob := row[0], bytes)
            task = from_json(self._bench.task_type, blob.decode())
            tasks.append(task)
        return tasks

    def select_methods(self) -> list[METHOD]:
        """Return all methods that are present in the cache."""
        methods: list[METHOD] = []
        cursor = self._db.cursor()
        cursor.execute("SELECT `data` FROM `methods`")
        while (row := cursor.fetchone()) is not None:
            # TODO: WRAP IN TRY EXCEPT AND PRINT WARNING IF FAILS
            assert isinstance(blob := row[0], bytes)
            method = from_json(self._bench.method_type, blob.decode())
            methods.append(method)
        return methods

    def select_runs(self, task: TASK) -> list[Run[RESULT]]:
        task_id = serializable_id(task)

        runs: list[Run[RESULT]] = []
        cursor = self._db.cursor()
        cursor.execute("SELECT `id`, `method`, `status`, `result` FROM `runs` WHERE `task` = ?", (task_id,))
        while (row := cursor.fetchone()) is not None:
            run_id, method_id, status, result_blob = row
            assert isinstance(run_id, int)
            assert isinstance(method_id, str)
            assert isinstance(status, str)
            assert isinstance(result_blob, bytes)

            result: Token | RESULT | BenchError
            if status == "running":
                result = from_json(Token, result_blob.decode())
            elif status == "done":
                result = from_json(self._bench.result_type, result_blob.decode())
            elif status == "failed":
                result = from_json(BenchError, result_blob.decode())
            else:
                msg = f"Encountered status '{status}', expected 'running', 'done' or 'failed'"
                raise RuntimeError(msg)

            runs.append(Run(run_id, task_id, method_id, result))

        return runs
