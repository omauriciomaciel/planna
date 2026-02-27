"""Popula a tabela banks com dados da BrasilAPI."""

import asyncio

import httpx
from sqlalchemy import delete

from app.database import async_session
from app.models.bank import Bank

BRASIL_API_URL = "https://brasilapi.com.br/api/banks/v1"


async def seed_banks() -> None:
    print("Buscando bancos da BrasilAPI...")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(BRASIL_API_URL)
        response.raise_for_status()
        data = response.json()

    banks = [
        Bank(
            ispb=item["ispb"],
            code=item.get("code"),
            name=item["name"] or "",
            full_name=item.get("fullName") or "",
        )
        for item in data
        if item.get("ispb")
    ]

    print(f"{len(banks)} bancos encontrados. Inserindo no banco...")

    async with async_session() as session:
        await session.execute(delete(Bank))
        session.add_all(banks)
        await session.commit()

    print("Concluído.")


if __name__ == "__main__":
    asyncio.run(seed_banks())
