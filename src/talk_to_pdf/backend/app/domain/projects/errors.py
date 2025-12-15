
class ProjectNotFound(Exception):
    def __init__(self, project_id: str):
        super().__init__(f"Project with id {project_id} not found.")


class FailedToCreateProject(Exception):
    def __init__(self, project_name: str):
        super().__init__(
            f"Failed to create project with name {project_name}"
        )