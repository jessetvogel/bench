import argparse
from pathlib import Path
from typing import cast

from bench.dashboard import Dashboard
from bench.engine import Engine
from bench.logging import get_logger


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
        prog="bench-dashboard",
        description="Start BENCH run",
    )
    parser.add_argument("path", type=str, help="Path to Python file containing `Bench` class")
    parser.add_argument("run_ids", type=str, help="Run ID", nargs="+")
    args = parser.parse_args()
    path = Path(cast(str, args.path))
    run_ids = cast(tuple[str, ...], args.run_ids)

    # try:
    # Create engine
    engine = Engine(path)
    # Start run
    for i, run_id in enumerate(run_ids):
        logger.info(f"Executing run {i + 1}/{len(run_ids)} ({run_id}) ..")
        engine.execute_run(run_id)
    # Done
    logger.info("Done!")
    # except Exception as err:
    #     logger.error(f"({type(err).__name__}) {err}")
    #     sys.exit(1)
