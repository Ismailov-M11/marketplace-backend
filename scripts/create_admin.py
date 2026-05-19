"""
Script to create the first super admin user.
Usage: python scripts/create_admin.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    email = input("Email: ").strip()
    full_name = input("Full name: ").strip()
    password = input("Password: ").strip()

    from app.core.database import AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.admin_user import AdminUser

    async with AsyncSessionLocal() as session:
        user = AdminUser(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role="super_admin",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print(f"✅ Super admin created: {email}")


if __name__ == "__main__":
    asyncio.run(main())
