from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID, uuid4

from talk_to_pdf.backend.app.domain.files.interfaces import StoredFileInfo


class FilesystemFileStorage:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    async def save(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> StoredFileInfo:
        project_dir = self._base_dir / str(owner_id) / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        # derive safe extension
        ext = Path(filename).suffix.lower()
        if ext != ".pdf":  # enforce your rules here
            ext = ".pdf"

        stored_filename = f"{uuid4()}{ext}"
        full_path = project_dir / stored_filename

        with open(full_path, "wb") as f:
            f.write(content)

        size = full_path.stat().st_size
        rel_path = os.path.relpath(full_path, self._base_dir)

        return StoredFileInfo(
            original_filename=filename,
            stored_filename=stored_filename,
            storage_path=rel_path,
            size_bytes=size,
            content_type=content_type,
        )

    async def delete(self, path: str) -> None:
        full_path = self._base_dir / path
        if full_path.exists():
            full_path.unlink()
