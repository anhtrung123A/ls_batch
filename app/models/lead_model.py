from dataclasses import dataclass


@dataclass(frozen=True)
class Lead:
    id: int
    full_name: str
    phone: str | None
    email: str | None
