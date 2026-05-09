from dataclasses import dataclass


@dataclass(frozen=True)
class UserCreateInput:
    full_name: str
    email: str
    phone: str | None
    password_hash: str
