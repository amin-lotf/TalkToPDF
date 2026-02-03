from __future__ import annotations

import httpx


class GrobidPdfToXmlConverter:
    """
    Minimal HTTP client for GROBID's /api/processFulltextDocument endpoint.
    """

    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.Client | None = None,
        timeout: float | httpx.Timeout = 30.0,
        endpoint: str = "/api/processFulltextDocument",
    ) -> None:
        if not base_url:
            raise ValueError("GROBID base_url must be provided")
        self._base_url = base_url.rstrip("/")
        self._client = client
        self._timeout = timeout
        self._endpoint = endpoint

    def convert(self, *, content: bytes) -> str:
        """
        Convert PDF bytes to TEI XML via GROBID.
        Raises RuntimeError on network or HTTP errors for clarity upstream.
        """
        url = f"{self._base_url}{self._endpoint}"
        client = self._client
        close_client = False

        if client is None:
            client = httpx.Client(timeout=self._timeout)
            close_client = True

        try:
            resp = client.post(
                url,
                files={"input": ("document.pdf", content, "application/pdf")},
                headers={"Accept": "application/xml, text/xml, */*;q=0.1"},
            )
        except httpx.RequestError as e:
            raise RuntimeError(f"GROBID request failed: {e}") from e
        finally:
            if close_client and client is not None:
                client.close()

        if resp.status_code != 200:
            raise RuntimeError(f"GROBID returned {resp.status_code}: {resp.text}")

        return resp.text
