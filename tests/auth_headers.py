"""Attach a scoped API credential to live-stack acceptance requests.

Set IAM_API_KEY before running the level1-5 acceptance scripts. Public routes
are unaffected because the header is simply present but unused there.
"""

import os

import httpx


def install_auth_headers() -> bool:
    key = os.environ.get("IAM_API_KEY", "").strip()
    if not key:
        return False

    import httpx._api

    original_request = httpx._api.request

    def authenticated_request(method, url, **kwargs):
        headers = dict(kwargs.pop("headers", None) or {})
        headers.setdefault("Authorization", f"Bearer {key}")
        return original_request(method, url, headers=headers, **kwargs)

    # httpx.get/post call httpx._api.request, not the package-level re-export.
    httpx._api.request = authenticated_request
    httpx.request = authenticated_request
    return True
