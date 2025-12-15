from typing import Protocol, runtime_checkable
from uuid import UUID
from talk_to_pdf.backend.app.domain.files import StoredFileInfo

@runtime_checkable
class FileStorage(Protocol):
    async def save(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> StoredFileInfo:
        ...

    async def delete(self, path: str) -> None:
        ...