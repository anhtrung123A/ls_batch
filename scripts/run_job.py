import argparse
import logging
import pathlib
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.infrastructure.config import Settings
from app.infrastructure.db import create_connection
from app.runners.job_registry import build_jobs
from app.utils.logger import setup_logging

TRIGGER_MAP = {
    "cron": 1,
    "manual": 2,
    "system": 3,
}


def parse_args():
    parser = argparse.ArgumentParser(description="Run a batch job")
    parser.add_argument("job_name", help="Job name to run")
    parser.add_argument(
        "--trigger",
        default="manual",
        choices=sorted(TRIGGER_MAP.keys()),
        help="Trigger source",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    settings = Settings.from_env()
    setup_logging(settings.log_level)
    connection = create_connection(settings)

    try:
        jobs = build_jobs(connection, settings)
        if args.job_name not in jobs:
            raise ValueError(f"Unknown job '{args.job_name}'. Available jobs: {', '.join(jobs.keys())}")

        job = jobs[args.job_name]()
        result = job.run(triggered_by=TRIGGER_MAP[args.trigger])
        logging.getLogger("batch.runner").info(
            "Job summary: job=%s trigger=%s created=%s skipped=%s failed=%s",
            args.job_name,
            args.trigger,
            result.created,
            result.skipped,
            result.failed,
        )
        print(
            f"[{args.job_name}] trigger={args.trigger} created={result.created} skipped={result.skipped} failed={result.failed}"
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
