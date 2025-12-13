
class ProjectNotFound(Exception):
    def __init__(self, project_id: str):
        super().__init__(f"Project with id {project_id} not found.")


class ProjectAlreadyHasDocumentError(Exception):
    def __init__(self, project_id: str):
        super().__init__(
            f"Project with id {project_id} already has a document attached."
        )