from __future__ import annotations


from .dto import ProjectDTO, CreateProjectInputDTO, ProjectDocumentDTO
from talk_to_pdf.backend.app.domain.projects.entities import Project, ProjectDocument
from ...domain.files import StoredFileInfo
from ...domain.projects import ProjectName


def project_document_domain_to_dto(doc: ProjectDocument) -> ProjectDocumentDTO:
    return ProjectDocumentDTO(
        id=doc.id,
        original_filename=doc.original_filename,
        storage_path=doc.storage_path,
        content_type=doc.content_type,
        size_bytes=doc.size_bytes,
        uploaded_at=doc.uploaded_at,
    )

def project_domain_to_output_dto(project: Project) -> ProjectDTO:
    doc_dto = project_document_domain_to_dto(project.primary_document)
    return ProjectDTO(
        id=project.id,
        name=str(project.name),
        owner_id=project.owner_id,
        created_at=project.created_at,
        primary_document=doc_dto,
    )

def project_input_dto_to_domain(data:CreateProjectInputDTO)->Project:
    return Project(
        name=ProjectName(data.name),
        owner_id=data.owner_id,

    )




def build_project_with_main_document(
    project: Project,
    stored: StoredFileInfo,
) -> Project:
    document = ProjectDocument(
        project_id=project.id,  # repo / infra will wire this up
        original_filename=stored.original_filename,
        storage_path=stored.storage_path,
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
    )
    project = project.attach_main_document(document)
    return project
