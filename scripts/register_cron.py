import subprocess
import os
import pathlib
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.constants.jobs import JOB_SCHEDULES

APP_NAME = "BATCH_APP"

BEGIN_MARKER = f"# BEGIN {APP_NAME}"
END_MARKER = f"# END {APP_NAME}"

CRON_HEADER = [
    "SHELL=/bin/sh",
    "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
]

CRON_ENV_KEYS = [
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_FROM_EMAIL",
    "SMTP_FROM_NAME",
    "LOG_LEVEL",
]


def get_current_crontab() -> str:
    result = subprocess.run(
        ["crontab", "-l"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return ""

    return result.stdout


def remove_old_block(crontab_text: str) -> str:
    lines = crontab_text.splitlines()
    new_lines = []
    inside_block = False

    for line in lines:
        if line.strip() == BEGIN_MARKER:
            inside_block = True
            continue

        if line.strip() == END_MARKER:
            inside_block = False
            continue

        if not inside_block:
            new_lines.append(line)

    return "\n".join(new_lines).strip()


def build_cron_block() -> str:
    cron_env = [f"{key}={os.getenv(key, '')}" for key in CRON_ENV_KEYS]
    cron_jobs = [
        f"{cron_expr} cd /app && /usr/local/bin/python3 scripts/run_job.py {job_name} --trigger cron >> /proc/1/fd/1 2>> /proc/1/fd/2"
        for cron_expr, job_name in JOB_SCHEDULES
    ]
    lines = [
        BEGIN_MARKER,
        *CRON_HEADER,
        *cron_env,
        *cron_jobs,
        END_MARKER,
    ]
    return "\n".join(lines)


def update_crontab(new_crontab: str):
    subprocess.run(
        ["crontab", "-"],
        input=new_crontab + "\n",
        text=True,
        check=True,
    )


def main():
    current_cron = get_current_crontab()
    cron_without_old_block = remove_old_block(current_cron)
    new_block = build_cron_block()

    if cron_without_old_block:
        new_cron = cron_without_old_block + "\n\n" + new_block
    else:
        new_cron = new_block

    update_crontab(new_cron)
    print("Cron schedule updated successfully.")


if __name__ == "__main__":
    main()
