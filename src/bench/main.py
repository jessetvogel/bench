import argparse
import cProfile
import secrets
from pathlib import Path
from typing import cast

from bench.dashboard import Dashboard
from bench.engine import Engine
from bench.logging import get_logger
from bench.templates import Run


def main_dashboard() -> None:
    # logger = get_logger("bench")

    # Parse arguments
    parser = argparse.ArgumentParser(
        prog="bench-dashboard",
        description="Start BENCH dashboard",
    )
    parser.add_argument("path", type=str, help="Path to Python file containing `Bench` class")
    args = parser.parse_args()
    path = Path(cast(str, args.path))

    # try:
    # Create engine
    engine = Engine(path)
    # Start dashboard
    Dashboard(engine).run()
    # except Exception as err:
    # logger.error(f"({type(err).__name__}) {err}")
    # sys.exit(1)


def main_run() -> None:
    logger = get_logger("bench")

    # Parse arguments
    parser = argparse.ArgumentParser(
        prog="bench-run",
        description="Start bench run",
    )
    parser.add_argument("path", help="path to Python file containing `Bench` class", type=str)
    parser.add_argument("task_id", help="id of task to perform", type=str)
    parser.add_argument("method_id", help="id of method to use", type=str)
    parser.add_argument("-n", help="number of runs (default is 1)", type=int, default=1)
    parser.add_argument("-v", "--verbose", help="print verbose output", action="store_true")

    args = parser.parse_args()
    path = Path(args.path)
    task_id: str = args.task_id
    method_id: str = args.method_id
    num_runs: int = args.n
    # verbose: bool = args.verbose

    # TODO: validate input

    profiler = cProfile.Profile()
    profiler.enable()

    # try:
    # Create engine
    engine = Engine(path)

    for it in range(num_runs):
        # Create new run
        run = Run(
            id=secrets.token_hex(8),
            task_id=task_id,
            method_id=method_id,
            result=None,
        )

        # Execute run
        logger.info(f"Executing run {it + 1}/{num_runs} (ID {run.id})..")
        engine.execute_run(run)

        # Insert result into cache
        engine.cache.insert_or_update_run(run)

    # Done
    logger.info("Done!")
    # except Exception as err:
    #     logger.error(f"({type(err).__name__}) {err}")
    #     sys.exit(1)

    profiler.disable()
    profiler.dump_stats("profile_results.stats")
