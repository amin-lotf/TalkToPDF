
class ProjectNotFound(Exception):
    def __init__(self, project_id: str):
        super().__init__(f"Project with id {project_id} not found.")

class DocumentNotFound(Exception):
    def __init__(self, document_id: str):
        super().__init__(f"Document with id {document_id} not found.")


class FailedToCreateProject(Exception):
    def __init__(self, project_name: str):
        super().__init__(
            f"Failed to create project with name {project_name}"
        )

class FailedToRenameProject(Exception):
    def __init__(self):
        super().__init__(
            f"Failed to rename the project"
        )

class FailedToDeleteProject(Exception):
    def __init__(self, project_name: str):
        super().__init__(
            f"Failed to delete project with name {project_name}"
        )

class FailedToDeleteProjectDocument(Exception):
    def __init__(self, project_name: str):
        super().__init__(
            f"Failed to delete the document for the project with name {project_name}"
        )