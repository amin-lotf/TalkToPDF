from __future__ import annotations

from pathlib import Path
from uuid import UUID
from typing import Dict
from dataclasses import dataclass

from talk_to_pdf.backend.app.domain.files import StoredFileInfo


class FakeFileStorage:
    """
    In-memory fake implementation of FileStorage for unit tests.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        # base_dir exists only to satisfy the Protocol shape
        self._base_dir = base_dir or Path("/fake")

        # storage_path -> bytes
        self._files: Dict[str, bytes] = {}

        # storage_path -> StoredFileInfo
        self._meta: Dict[str, StoredFileInfo] = {}

    async def save(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> StoredFileInfo:
        # deterministic & realistic relative path
        storage_path = f"{owner_id}/{project_id}/{filename}"
        info = StoredFileInfo(
            original_filename=filename,
            stored_filename=filename,
            storage_path=storage_path,
            size_bytes=len(content),
            content_type=content_type,
        )
        self._files[storage_path] = content
        self._meta[storage_path] = info

        return info

    async def read_bytes(self, *, storage_path: str) -> bytes:
        try:
            return self._files[storage_path]
        except KeyError:
            raise FileNotFoundError(storage_path)

    async def delete(self, *, storage_path: str) -> None:
        self._files.pop(storage_path, None)
        self._meta.pop(storage_path, None)

    # ---------- test helpers (intentional) ----------

    def exists(self, storage_path: str) -> bool:
        return storage_path in self._files

    def count(self) -> int:
        return len(self._files)

    def clear(self) -> None:
        self._files.clear()
        self._meta.clear()
