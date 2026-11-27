"""Constitutional gate is enforced on real protected routes."""

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.api.routes.reflection import PrincipleUpdateRequest, update_principle


class FakeDB:
    pass


class ConstitutionalWiringTests(unittest.IsolatedAsyncioTestCase):
    async def test_principle_change_requires_signed_authorization(self):
        with patch(
            "app.services.creatorapproval_service.CreatorApprovalService.check_authorization",
            new_callable=AsyncMock,
            return_value={"authorized": False},
        ):
            with self.assertRaises(HTTPException) as caught:
                await update_principle(
                    "p1",
                    PrincipleUpdateRequest(principle_statement="changed"),
                    FakeDB(),
                )
        self.assertEqual(caught.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
