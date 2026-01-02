class FailedToStartIndexing(Exception):
    def __init__(self,reason:str=None):
        super().__init__(reason)


class IndexNotFound(Exception):
    def __init__(self, *, index_id: str) -> None:
        super().__init__(f"Index not found: {index_id}")
        self.index_id = index_id


class NoIndexesForProject(Exception):
    def __init__(self, *, project_id: str) -> None:
        super().__init__(f"No indexes found for project: {project_id}")
        self.project_id = project_id