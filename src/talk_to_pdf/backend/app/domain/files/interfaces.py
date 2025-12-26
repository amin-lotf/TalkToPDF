from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID
from talk_to_pdf.backend.app.domain.files import StoredFileInfo

@runtime_checkable
class FileStorage(Protocol):
    _base_dir:Path
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

    async def read_bytes(self, *, storage_path: str) -> bytes:
        """
        storage_path MUST be a relative path previously returned by save()
        """
        ...

    async def delete(self, *,storage_path: str) -> None:
        ...