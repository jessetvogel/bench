import subprocess
from pathlib import Path


class Process:
    def __init__(self, args: list[str], *, path_stdout: Path) -> None:
        # Open subprocess and write stdout/stderr to file
        self._path_stdout = path_stdout
        self._file_stdout = self._path_stdout.open("w")
        self._process = subprocess.Popen(
            args,
            stdout=self._file_stdout,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        # Keep track of status and stdout
        self._status: int | None = None
        self._stdout = ""

    @property
    def stdout(self) -> str:
        return self._stdout

    def poll(self) -> int | None:
        # If process was already closed, return the status
        if self._status is not None:
            return self._status
        # Update `self._stdout` with contents of the temporary file
        with self._path_stdout.open("r") as file:
            self._stdout = file.read()
        # Poll the status of the process
        self._status = self._process.poll()
        # If process just closed, also close the temporary file
        if self._status is not None:
            self._file_stdout.close()
        return self._status

    def kill(self) -> None:
        self._process.kill()
