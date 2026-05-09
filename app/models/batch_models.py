from dataclasses import dataclass


@dataclass
class JobStats:
    created: int = 0
    skipped: int = 0
    failed: int = 0
