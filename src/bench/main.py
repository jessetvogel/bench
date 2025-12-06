import argparse
from pathlib import Path
from typing import cast

from bench.dashboard import Dashboard
from bench.engine import create_engine_from_module
from bench.logging import get_logger


def main_dashboard() -> None:
    logger = get_logger("bench")

    # Parse arguments
    parser = argparse.ArgumentParser(
        prog="bench-dashboard",
        description="Start BENCH dashboard",
    )
    parser.add_argument("path", type=str, help="Path to Python file containing `Bench` class")
    args = parser.parse_args()
    path = Path(cast(str, args.path))

    # Create Engine instance
    try:
        engine = create_engine_from_module(path)
    except Exception as err:
        logger.error(f"{err}")

    # Start dashboard
    Dashboard(engine).run()


def main_run() -> None:
    logger = get_logger("bench")

    # Parse arguments
    parser = argparse.ArgumentParser(
        prog="bench-dashboard",
        description="Start BENCH run",
    )
    parser.add_argument("path", type=str, help="Path to Python file containing `Bench` class")
    parser.add_argument("run_id", type=str, help="Run ID")
    args = parser.parse_args()
    path = Path(cast(str, args.path))
    run_id = cast(str, args.run_id)

    # Create Engine instance
    try:
        engine = create_engine_from_module(path)
    except Exception as err:
        logger.error(f"{err}")

    # Start run
    engine.execute_run(run_id)
