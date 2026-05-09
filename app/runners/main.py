import logging
import sys

from app.infrastructure.config import Settings
from app.infrastructure.db import create_connection
from app.runners.job_registry import build_jobs
from app.utils.logger import setup_logging


def main():
    settings = Settings.from_env()
    setup_logging(settings.log_level)
    connection = create_connection(settings)

    try:
        jobs = build_jobs(connection, settings)
        default_job_name = next(iter(jobs.keys()))
        job_name = sys.argv[1] if len(sys.argv) > 1 else default_job_name
        if job_name not in jobs:
            raise ValueError(f"Unknown job '{job_name}'. Available jobs: {', '.join(jobs.keys())}")

        job = jobs[job_name]()
        result = job.run()
        logging.getLogger("batch.main").info(
            "Job summary: job=%s created=%s skipped=%s failed=%s",
            job_name,
            result.created,
            result.skipped,
            result.failed,
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
