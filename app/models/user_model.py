from dataclasses import dataclass


@dataclass(frozen=True)
class UserCreateInput:
    full_name: str
    email: str
    phone: str | None
    password_hash: str


@dataclass(frozen=True)
class PayrollUser:
    id: int
    role: int


@dataclass(frozen=True)
class PayrollUserContact:
    full_name: str | None
    email: str | None
