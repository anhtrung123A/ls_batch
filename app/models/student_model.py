from dataclasses import dataclass


@dataclass(frozen=True)
class Student:
    id: int
    student_code: str
