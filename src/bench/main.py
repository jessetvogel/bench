import argparse
from pathlib import Path
from typing import cast

from bench.dashboard import Dashboard
from bench.engine import Engine
from bench.logging import get_logger


def main_dashboard() -> int:
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
    return 0


def main_run() -> int:
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

    # Validate input
    if num_runs <= 0:
        logger.error("Number of runs must be a positive integer")
        return 1

    if not path.is_file():
        logger.error(f"Path `{path}` does not exist")
        return 1

    try:
        # Create engine
        engine = Engine(path)
        # Get task and method by ID
        task = engine.cache.select_task(task_id)
        method = engine.cache.select_method(method_id)
    except Exception as err:
        logger.error(str(err))
        return 1

    # Execute runs
    for it in range(num_runs):
        logger.info(f"Executing run {it + 1}/{num_runs} ..")
        run = engine.execute_run(task, method)
        # If run failed, stop
        if run.status == "failed":
            return 1

    # Done
    logger.info("Done!")
    return 0
