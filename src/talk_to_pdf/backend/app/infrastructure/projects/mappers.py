from talk_to_pdf.backend.app.domain.projects import Project, ProjectName
from talk_to_pdf.backend.app.domain.projects.entities import ProjectDocument
from talk_to_pdf.backend.app.infrastructure.db.models.project import ProjectModel, ProjectDocumentModel


def project_document_model_to_domain(m: ProjectDocumentModel) -> ProjectDocument:
    return ProjectDocument(
        id=m.id,
        project_id=m.project_id,
        original_filename=m.original_filename,
        storage_path=m.storage_path,
        content_type=m.content_type,
        size_bytes=m.size_bytes,
        uploaded_at=m.uploaded_at,
    )


def create_project_domain_from_models(pm: ProjectModel, dm: ProjectDocumentModel) -> Project:
    doc = project_document_model_to_domain(dm)
    return Project(
        id=pm.id,
        name=ProjectName(pm.name),
        owner_id=pm.owner_id,
        primary_document=doc,
        created_at=pm.created_at,
    )


def project_document_domain_to_model(d: ProjectDocument) -> ProjectDocumentModel:
    return ProjectDocumentModel(
        id=d.id,
        project_id=d.project_id,
        original_filename=d.original_filename,
        storage_path=d.storage_path,
        content_type=d.content_type,
        size_bytes=d.size_bytes,
        uploaded_at=d.uploaded_at,
    )


def project_domain_to_model(p: Project) -> ProjectModel:
    if p.primary_document is None:
        raise ValueError("Project.primary_document is required to persist a Project")
    return ProjectModel(
        id=p.id,
        name=p.name.value,
        owner_id=p.owner_id,
        created_at=p.created_at,
        primary_document_id=p.primary_document.id,
    )
