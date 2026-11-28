"""Finance SDK surface is read-only and uses the versioned finance routes."""

import unittest
from unittest.mock import AsyncMock, patch

from iam_sdk.client import IAM, _Transport


class FinanceSDKTests(unittest.IsolatedAsyncioTestCase):
    async def test_finance_read_surface(self):
        iam = IAM("http://iam.test")
        with patch.object(
            _Transport, "request", new_callable=AsyncMock, return_value={"ok": True}
        ) as request:
            self.assertTrue((await iam.finance.ledger())["ok"])
            await iam.finance.transactions()
            await iam.finance.budgets()
            await iam.finance.reconciliation()
            await iam.finance.profit_and_loss()
        paths = [call.args[1] for call in request.await_args_list]
        self.assertEqual(paths[0], "/api/v1/finance/ledger")
        self.assertIn("/api/v1/finance/transactions", paths)
        self.assertIn("/api/v1/finance/profit-and-loss", paths)
        self.assertTrue(all("POST" not in str(c) for c in request.await_args_list))


if __name__ == "__main__":
    unittest.main()
