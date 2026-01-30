# talk_to_pdf/frontend/streamlit_app/services/api.py
from __future__ import annotations

from typing import Any, Dict, Optional, List
from uuid import UUID

import httpx


class ApiError(RuntimeError):
    """Raised when an HTTP/API error occurs, with a human-readable message."""




def unwrap_error(e: Exception) -> str:
    """Extract a human-readable error message from httpx exceptions."""
    if isinstance(e, httpx.HTTPStatusError):
        # The request reached the server, but the response had an error code
        try:
            data = e.response.json()
            detail = data.get("detail") if isinstance(data, dict) else data
            return f"{e.response.status_code} {e.response.reason_phrase}: {detail}"
        except Exception:
            return f"{e.response.status_code} {e.response.reason_phrase}"

    elif isinstance(e, httpx.RequestError):
        # Connection errors, timeouts, DNS failures, etc.
        return f"Request failed: {e.__class__.__name__}: {e}"

    elif isinstance(e, httpx.TimeoutException):
        return "Request timed out."

    elif isinstance(e, httpx.ConnectError):
        return "Failed to connect to server. Is it running?"

    else:
        # Anything unexpected
        return str(e)


def handle_httpx_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Wrap any error into a consistent ApiError
            raise ApiError(unwrap_error(e)) from e

    return wrapper


class Api:
    """
    Thin API client for the FastAPI backend.

    Assumes backend routes:
      POST /auth/register -> user JSON
      POST /auth/token    -> {"access_token": "..."}
      GET  /auth/me       -> current user JSON (requires Bearer token)
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        # base_url should already include "/api/v1"
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
        )

    def _auth_headers(self, access_token: Optional[str]) -> Dict[str, str]:
        if not access_token:
            return {}
        return {"Authorization": f"Bearer {access_token}"}

    def close(self) -> None:
        self._client.close()

    # ---------- Auth endpoints ----------

    @handle_httpx_errors
    def register_user(
        self,
        email: str,
        password: str,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call POST /auth/register with JSON body matching your RegisterUserRequest.

        Adjust keys if your pydantic model differs.
        """
        payload: Dict[str, Any] = {
            "email": email,
            "password": password,
        }
        if name is not None:
            payload["name"] = name

        resp = self._client.post("/auth/register", json=payload)
        resp.raise_for_status()
        return resp.json()

    @handle_httpx_errors
    def login(self, email: str, password: str) -> str:
        """
        Call POST /auth/token and return the access_token string.

        Adjust keys if your LoginRequest uses different field names.
        """
        payload = {
            "email": email,
            "password": password,
        }
        resp = self._client.post("/auth/token", json=payload)
        resp.raise_for_status()
        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise ApiError("Login succeeded but no access_token found in response.")
        return token

    @handle_httpx_errors
    def get_me(self, access_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Call GET /auth/me.
        - In prod: pass a valid JWT -> sent as Bearer token.
        - In dev (SKIP_AUTH=True): you can call with access_token=None, no header.
        """
        headers: Dict[str, str] = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        resp = self._client.get("/auth/me", headers=headers or None)
        resp.raise_for_status()
        return resp.json()

        # ---------- Projects endpoints ----------

    @handle_httpx_errors
    def list_projects(self, access_token: Optional[str]) -> List[Dict[str, Any]]:
        resp = self._client.get("/projects", headers=self._auth_headers(access_token) or None)
        resp.raise_for_status()
        data = resp.json()

        # Accept common envelope keys
        if isinstance(data, dict):
            raw = (
                    data.get("items")  # <-- your current backend
                    or data.get("projects")
                    or data.get("results")
                    or []
            )
        else:
            raw = data

        # Normalize
        out: List[Dict[str, Any]] = []
        for item in raw:
            if isinstance(item, dict):
                out.append(item)
            elif isinstance(item, str):
                out.append({"id": item, "name": item})
            else:
                out.append({"id": str(item), "name": str(item)})
        return out

    @handle_httpx_errors
    def get_project(self, access_token: Optional[str], project_id: str) -> Dict[str, Any]:
        resp = self._client.get(f"/projects/{project_id}", headers=self._auth_headers(access_token) or None)
        resp.raise_for_status()
        return resp.json()

    @handle_httpx_errors
    def create_project(
            self,
            access_token: Optional[str],
            *,
            name: str,
            file_name: str,
            file_bytes: bytes,
            content_type: str = "application/pdf",
    ) -> Dict[str, Any]:
        """
        POST /projects/create
        Backend expects multipart/form-data:
          - name: Form(...)
          - file: UploadFile = File(...)
        """
        files = {
            "file": (file_name, file_bytes, content_type),
        }
        data = {"name": name}
        resp = self._client.post(
            "/projects/create",
            headers=self._auth_headers(access_token) or None,
            data=data,
            files=files,
        )
        resp.raise_for_status()
        return resp.json()

    @handle_httpx_errors
    def delete_project(self, access_token: Optional[str], project_id: str) -> None:
        resp = self._client.delete(
            f"/projects/{project_id}",
            headers=self._auth_headers(access_token) or None,
        )
        resp.raise_for_status()
        return None

    @handle_httpx_errors
    def rename_project(
            self,
            access_token: Optional[str],
            project_id: str,
            *,
            name: str,
    ) -> Dict[str, Any]:
        resp = self._client.patch(
            f"/projects/{project_id}/rename",
            headers=self._auth_headers(access_token) or None,
            json={"new_name": name},
        )
        resp.raise_for_status()
        return resp.json()

    # ---------- Indexing endpoints ----------

    @handle_httpx_errors
    def start_indexing(self, access_token: Optional[str], *, project_id: str, document_id: str) -> Dict[str, Any]:
        resp = self._client.post(
            f"/indexing/projects/{project_id}/documents/{document_id}/start",
            headers=self._auth_headers(access_token) or None,
        )
        resp.raise_for_status()
        return resp.json()

    @handle_httpx_errors
    def get_latest_index_status(self, access_token: Optional[str], *, project_id: str) -> Dict[str, Any]:
        resp = self._client.get(
            f"/indexing/projects/{project_id}/latest",
            headers=self._auth_headers(access_token) or None,
        )
        resp.raise_for_status()
        return resp.json()

    @handle_httpx_errors
    def get_index_status(self, access_token: Optional[str], *, index_id: str) -> Dict[str, Any]:
        resp = self._client.get(
            f"/indexing/{index_id}",
            headers=self._auth_headers(access_token) or None,
        )
        resp.raise_for_status()
        return resp.json()

    @handle_httpx_errors
    def cancel_indexing(self, access_token: Optional[str], *, index_id: str) -> None:
        resp = self._client.post(
            f"/indexing/{index_id}/cancel",
            headers=self._auth_headers(access_token) or None,
        )
        resp.raise_for_status()
        return None

    @handle_httpx_errors
    def query_project(
            self,
            access_token: Optional[str],
            *,
            project_id: str | UUID,
            chat_id: str | UUID,
            query: str,
            top_k: int = 10,
            top_n: int = 5,
            rerank_timeout_s: float = 0.6,
    ) -> Dict[str, Any]:
        """
        POST /query
        Body matches QueryRequest:
          - project_id: UUID
          - chat_id: UUID
          - query: str
          - top_k: int
          - top_n: int
          - rerank_timeout_s: float

        Returns ReplyResponse as dict:
          { "query": "...", "answer": "...", "context": {...} }
        """
        payload = {
            "project_id": str(project_id),
            "chat_id": str(chat_id),
            "query": query,
            "top_k": int(top_k),
            "top_n": int(top_n),
            "rerank_timeout_s": float(rerank_timeout_s),
        }

        resp = self._client.post(
            "/query",
            headers=self._auth_headers(access_token) or None,
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    # ---------- Chat endpoints ----------

    @handle_httpx_errors
    def create_chat(
        self,
        access_token: Optional[str],
        *,
        project_id: str | UUID,
        title: str,
    ) -> Dict[str, Any]:
        """
        POST /chats
        Body: { "project_id": UUID, "title": str }
        Returns ChatResponse as dict
        """
        payload = {
            "project_id": str(project_id),
            "title": title,
        }
        resp = self._client.post(
            "/chats",
            headers=self._auth_headers(access_token) or None,
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    @handle_httpx_errors
    def list_chats(
        self,
        access_token: Optional[str],
        *,
        project_id: str | UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        GET /projects/{project_id}/chats?limit=X&offset=Y
        Returns ListChatsResponse as dict: { "items": [...] }
        """
        resp = self._client.get(
            f"/projects/{project_id}/chats",
            headers=self._auth_headers(access_token) or None,
            params={"limit": limit, "offset": offset},
        )
        resp.raise_for_status()
        return resp.json()

    @handle_httpx_errors
    def get_chat(
        self,
        access_token: Optional[str],
        *,
        chat_id: str | UUID,
    ) -> Dict[str, Any]:
        """
        GET /chats/{chat_id}
        Returns ChatResponse as dict
        """
        resp = self._client.get(
            f"/chats/{chat_id}",
            headers=self._auth_headers(access_token) or None,
        )
        resp.raise_for_status()
        return resp.json()

    @handle_httpx_errors
    def delete_chat(
        self,
        access_token: Optional[str],
        *,
        chat_id: str | UUID,
    ) -> None:
        """
        DELETE /chats/{chat_id}
        Returns None (204 status)
        """
        resp = self._client.delete(
            f"/chats/{chat_id}",
            headers=self._auth_headers(access_token) or None,
        )
        resp.raise_for_status()
        return None

    @handle_httpx_errors
    def get_chat_messages(
        self,
        access_token: Optional[str],
        *,
        chat_id: str | UUID,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        GET /chats/{chat_id}/messages?limit=X
        Returns ListMessagesResponse as dict: { "items": [...] }
        """
        resp = self._client.get(
            f"/chats/{chat_id}/messages",
            headers=self._auth_headers(access_token) or None,
            params={"limit": limit},
        )
        resp.raise_for_status()
        return resp.json()