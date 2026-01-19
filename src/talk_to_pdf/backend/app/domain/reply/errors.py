class ChatNotFoundOrForbidden(Exception):
    def __init__(self) -> None:
        super().__init__(f"Index not found")