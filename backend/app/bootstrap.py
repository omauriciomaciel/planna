import argparse
import asyncio

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Household, HouseholdMember, User


async def bootstrap(household_name: str, people: list[tuple[str, str]]) -> None:
    async with SessionLocal.begin() as db:
        household = await db.scalar(select(Household).where(Household.name == household_name))
        if household is None:
            household = Household(name=household_name)
            db.add(household)
            await db.flush()

        for index, (name, email) in enumerate(people):
            user = await db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(name=name, email=email)
                db.add(user)
                await db.flush()
            membership = await db.get(HouseholdMember, (household.id, user.id))
            if membership is None:
                db.add(
                    HouseholdMember(
                        household_id=household.id,
                        user_id=user.id,
                        role="owner" if index == 0 else "member",
                    )
                )


def parse_people(values: list[str]) -> list[tuple[str, str]]:
    people: list[tuple[str, str]] = []
    for value in values:
        try:
            name, email = value.split(":", 1)
            normalized = validate_email(email.strip(), check_deliverability=False).normalized
        except (ValueError, EmailNotValidError) as error:
            raise ValueError("use NOME:EMAIL com um e-mail válido para cada membro") from error
        if not name.strip():
            raise ValueError("o nome do membro não pode ficar vazio")
        people.append((name.strip(), normalized))
    return people


def main() -> None:
    parser = argparse.ArgumentParser(description="Cadastra o household e seus membros autorizados.")
    parser.add_argument("household")
    parser.add_argument("people", nargs="+", metavar="NOME:EMAIL")
    args = parser.parse_args()
    try:
        people = parse_people(args.people)
    except ValueError as error:
        parser.error(str(error))
    asyncio.run(bootstrap(args.household, people))


if __name__ == "__main__":
    main()
