"""Attach a scoped API credential to live-stack acceptance requests.

Set IAM_API_KEY before running the level1-5 acceptance scripts. Public routes
are unaffected because the header is simply present but unused there.
"""

import os

import httpx


_installed = False


def install_auth_headers() -> bool:
    global _installed
    key = os.environ.get("IAM_API_KEY", "").strip()
    if not key:
        return False
    if _installed:
        return True

    import httpx._api

    def with_auth(kwargs: dict) -> dict:
        headers = dict(kwargs.pop("headers", None) or {})
        headers.setdefault("Authorization", f"Bearer {key}")
        kwargs["headers"] = headers
        return kwargs

    original_request = httpx._api.request

    def authenticated_request(method, url, **kwargs):
        return original_request(method, url, **with_auth(kwargs))

    # Module-level helpers (httpx.get/post) route through httpx._api.request.
    httpx._api.request = authenticated_request
    httpx.request = authenticated_request

    # Client-based scripts use Client.request, which bypasses the module API.
    original_client_request = httpx.Client.request

    def authenticated_client_request(self, method, url, **kwargs):
        return original_client_request(self, method, url, **with_auth(kwargs))

    httpx.Client.request = authenticated_client_request
    _installed = True
    return True
