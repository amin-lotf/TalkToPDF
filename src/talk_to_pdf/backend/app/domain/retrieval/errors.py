class InvalidRetrieval(Exception):
    def __init__(self, reason:str) -> None:
        super().__init__(reason)

class IndexNotFoundOrForbidden(Exception):
    def __init__(self) -> None:
        super().__init__(f"Index not found")

class IndexNotReady(Exception):
    def __init__(self, *, index_id: str) -> None:
        super().__init__(f"Index {index_id} is not ready yet.")
        self.index_id = index_id

class InvalidQuery(Exception):
    def __init__(self,reason:str=None):
        super().__init__(reason)