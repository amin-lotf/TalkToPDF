from enum import StrEnum


class ChatRole(StrEnum):
    system = "system"
    user = "user"
    assistant = "assistant"