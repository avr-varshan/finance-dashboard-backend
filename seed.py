import csv
import os
import random
from datetime import date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal, engine
from app.models.user import Role, User
from app.models.record import FinancialRecord, RecordType
from app.services.auth_service import get_password_hash, create_access_token, create_refresh_token

CREDENTIALS_FILE = "SEED_CREDENTIALS.md"


async def seed():
    async with AsyncSessionLocal() as session:
        user_count = (await session.execute(text("SELECT count(*) FROM users"))).scalar_one()
        if user_count > 0:
            print("Seed data already exists, skipping")
            return

        users = []
        for u in [
            ("admin@zorvyn.io", "Admin123!", "Admin User", Role.admin),
            ("analyst@zorvyn.io", "Analyst123!", "Analyst User", Role.analyst),
            ("viewer@zorvyn.io", "Viewer123!", "Viewer User", Role.viewer),
        ]:
            user = User(email=u[0], full_name=u[2], hashed_password=get_password_hash(u[1]), role=u[3])
            session.add(user)
            users.append((u[0], u[1], user))

        await session.commit()

        categories = ["Salary", "Consulting", "Rent", "Marketing", "Utilities", "Travel", "Equipment", "Insurance", "Software", "Payroll"]
        for i in range(60):
            rec_user = random.choice([u[2] for u in users if u[2].role in (Role.analyst, Role.admin)])
            rec_type = random.choice([RecordType.income, RecordType.expense])
            category = random.choice(categories)
            amount = round(random.uniform(8300, 4150000), 2) if rec_type==RecordType.income else round(random.uniform(1660, 1245000), 2)
            rec_date = date.today() - timedelta(days=random.randint(0, 180))
            notes = f"Seed record {i+1}"
            record = FinancialRecord(amount=amount, type=rec_type, category=category, date=rec_date, notes=notes, created_by=rec_user.id)
            session.add(record)

        await session.commit()

        with open(CREDENTIALS_FILE, "w") as f:
            f.write("# Seed credentials\n\n")
            f.write("| email | password | role |\n")
            f.write("|---|---|---|\n")
            for email, password, user in users:
                f.write(f"| {email} | {password} | {user.role.value} |\n")

        print("Seed complete")
        for email, password, user in users:
            access = create_access_token(user)["access_token"]
            refresh = create_refresh_token(user)["refresh_token"]
            print(f"{email}: access={access}\n refresh={refresh}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed())
