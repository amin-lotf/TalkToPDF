from dataclasses import dataclass
import re


@dataclass(frozen=True)
class UserEmail:
    value: str

    def __post_init__(self)->None:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", self.value):
            raise ValueError("Invalid email address")

    def __str__(self) -> str:
        return self.value