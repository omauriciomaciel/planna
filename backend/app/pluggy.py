import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from app.config import settings

BASE_URL = "https://api.pluggy.ai"


class PluggyUnavailable(RuntimeError):
    pass


class PluggyClient:
    def __init__(self) -> None:
        self._api_key: str | None = None
        self._expires_at = datetime.min.replace(tzinfo=UTC)
        self._lock = asyncio.Lock()

    async def _key(self, *, refresh: bool = False) -> str:
        if not settings.pluggy_client_id or not settings.pluggy_client_secret:
            raise PluggyUnavailable("Integração Pluggy não configurada")
        if not refresh and self._api_key and datetime.now(UTC) < self._expires_at:
            return self._api_key
        async with self._lock:
            if not refresh and self._api_key and datetime.now(UTC) < self._expires_at:
                return self._api_key
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
                response = await client.post(
                    "/auth",
                    json={
                        "clientId": settings.pluggy_client_id,
                        "clientSecret": settings.pluggy_client_secret,
                    },
                )
                response.raise_for_status()
                self._api_key = response.json()["apiKey"]
                self._expires_at = datetime.now(UTC) + timedelta(minutes=110)
                return self._api_key

    async def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        for attempt in range(2):
            key = await self._key(refresh=attempt == 1)
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=60) as client:
                response = await client.request(
                    method, path, headers={"X-API-KEY": key}, **kwargs
                )
            if response.status_code != 401 or attempt:
                response.raise_for_status()
                return response.json()
        raise AssertionError("unreachable")

    async def create_connect_token(self, client_user_id: str) -> str:
        options: dict[str, Any] = {"clientUserId": client_user_id, "avoidDuplicates": True}
        if settings.pluggy_webhook_url and settings.pluggy_webhook_secret:
            separator = "&" if "?" in settings.pluggy_webhook_url else "?"
            options["webhookUrl"] = (
                f"{settings.pluggy_webhook_url}{separator}token={settings.pluggy_webhook_secret}"
            )
        data = await self.request("POST", "/connect_token", json={"options": options})
        return data["accessToken"]

    async def item(self, item_id: str) -> dict[str, Any]:
        return await self.request("GET", f"/items/{item_id}")

    async def accounts(self, item_id: str) -> list[dict[str, Any]]:
        data = await self.request("GET", "/accounts", params={"itemId": item_id})
        return data.get("results", data if isinstance(data, list) else [])

    async def transactions(self, account_id: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        params: dict[str, Any] = {"accountId": account_id}
        while True:
            data = await self.request("GET", "/v2/transactions", params=params)
            results.extend(data.get("results", []))
            next_page = data.get("next")
            if not next_page:
                return results
            after = parse_qs(urlparse(next_page).query).get("after")
            if not after:
                return results
            params["after"] = after[0]

    async def investments(self, item_id: str) -> list[dict[str, Any]]:
        data = await self.request(
            "GET", "/investments", params={"itemId": item_id, "pageSize": 500}
        )
        return data.get("results", [])

    async def loans(self, item_id: str) -> list[dict[str, Any]]:
        data = await self.request("GET", "/loans", params={"itemId": item_id, "pageSize": 500})
        return data.get("results", [])


def transaction_values(data: dict[str, Any]) -> dict[str, Any]:
    transaction_type = str(data.get("type", "DEBIT")).lower()
    amount = Decimal(str(data.get("amount", 0)))
    amount = abs(amount) if transaction_type == "credit" else -abs(amount)
    merchant = data.get("merchant") or {}
    installments = data.get("creditCardMetadata") or {}
    return {
        "date": datetime.fromisoformat(str(data["date"])),
        "amount": amount,
        "description": str(data.get("description") or "Transação")[:500],
        "merchant_name": (merchant.get("businessName") or merchant.get("name")) if merchant else None,
        "merchant_cnpj": merchant.get("cnpj") if merchant else None,
        "type": transaction_type if transaction_type in {"debit", "credit"} else "debit",
        "status": "pending" if str(data.get("status", "POSTED")).upper() == "PENDING" else "posted",
        "installment_current": installments.get("installmentNumber"),
        "installment_total": installments.get("totalInstallments"),
        "raw": data,
    }


client = PluggyClient()
