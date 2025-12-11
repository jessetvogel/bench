import fcntl
import os
import pty
import select
import subprocess


class Process:
    def __init__(self, args: list[str]) -> None:
        # Create pseudo-terminal in which to run the process
        master_fd, slave_fd = pty.openpty()
        self._master_fd = master_fd

        # Start process, routing stdout/stderr to `slave_fd`
        self._process = subprocess.Popen(
            args,
            stdout=slave_fd,
            stderr=slave_fd,
            start_new_session=True,
        )

        # Parent process no longer needs `slave_fd`
        os.close(slave_fd)

        # Make `master_fd` non-blocking
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        # Keep track of `stdout` and `stderr`
        self._stdout = ""
        self._stderr = ""

    def poll(self) -> int | None:
        # Get status of the process
        status = self._process.poll()

        # If process is still running, only read if `select` says there is data
        if status is None:
            ready, _, _ = select.select([self._master_fd], [], [], 0.0)
            if self._master_fd not in ready:
                return status

        # Read data
        try:
            while True:
                chunk = os.read(self._master_fd, 4096)
                if not chunk:
                    break
                self._stdout += chunk.decode()
        except (OSError, BlockingIOError):
            pass

        return status

    @property
    def stdout(self) -> str:
        """Current stdout output."""
        return self._stdout

    @property
    def stderr(self) -> str:
        """Current stderr output."""
        return self._stderr
