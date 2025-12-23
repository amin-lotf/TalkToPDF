from __future__ import annotations

from talk_to_pdf.backend.app.application.users.interfaces import PasswordHasher


class FakePasswordHasher(PasswordHasher):
    def hash(self, raw_password: str) -> str:
        # deterministic for tests
        return f"hashed::{raw_password}"

    def verify(self, plain: str, hashed: str) -> bool:
        return hashed == self.hash(plain)
