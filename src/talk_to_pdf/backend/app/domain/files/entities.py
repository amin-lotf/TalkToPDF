from dataclasses import dataclass


@dataclass
class StoredFileInfo:
    original_filename: str
    stored_filename: str
    storage_path: str
    size_bytes: int
    content_type: str